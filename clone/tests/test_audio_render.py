"""Pitch and pan rendering. This is inspired by Jim Kitchen's Brain."""
import os

import numpy as np
import pytest

from brain.audio.render import (MIX_RATE, output_frames, pan_gains, render_stereo, resample,
                                usable_frequency)
from brain.audio.wavdata import Sampled, load_sound_file
from brain.data import paths

SHIPPED = os.path.join(paths.program_dir(), "assets", "sounds")


def tone(freq, seconds, rate, amp=0.5):
    t = np.arange(int(rate * seconds)) / rate
    return Sampled((amp * np.sin(2 * np.pi * freq * t)).astype(np.float32).reshape(-1, 1), rate)


def dominant_hz(pcm_channel):
    spectrum = np.abs(np.fft.rfft(pcm_channel * np.hanning(len(pcm_channel))))
    return np.argmax(spectrum) * MIX_RATE / len(pcm_channel)


def test_pan_gains_attenuate_only_the_far_channel_by_pan_over_100_db():
    assert pan_gains(0) == (1.0, 1.0)
    left, right = pan_gains(750)                     # GAME_SPEC 5.5 / DECISIONS P5
    assert right == 1.0 and left == pytest.approx(10 ** (-7.5 / 20))
    left, right = pan_gains(-750)
    assert left == 1.0 and right == pytest.approx(10 ** (-7.5 / 20))
    assert pan_gains(-1000)[1] == pytest.approx(10 ** (-10 / 20))   # mode 4 extreme: 10 dB
    assert pan_gains(99999) == pan_gains(10000)                      # clamped to DirectSound's range
    assert pan_gains(10000)[0] == pytest.approx(1e-5)                # full right: left is 100 dB down


def test_pan_table_gains_are_the_documented_decibel_steps():
    table = [-750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750]
    for p in table:
        near, far = sorted(pan_gains(p), reverse=True)
        assert near == 1.0
        assert 20 * np.log10(far) == pytest.approx(-abs(p) / 100)


def test_usable_frequency_range_is_directsounds():
    assert not usable_frequency(99) and usable_frequency(100)
    assert usable_frequency(200_000) and not usable_frequency(200_001)
    assert not usable_frequency(0) and not usable_frequency(-500)


def test_real_lengths_at_the_pitch_extremes_match_the_spec():
    """GAME_SPEC 5.3: real length 2.8 ms (brain8 at 46,000 Hz) to 324 ms (brain36 at 3,564 Hz)."""
    b8 = load_sound_file(os.path.join(SHIPPED, "brain8.wav"))
    b36 = load_sound_file(os.path.join(SHIPPED, "brain36.wav"))
    assert b8.rate == 44100 and b36.rate == 5564
    assert output_frames(b8.frames, b8.rate + 1900) / MIX_RATE == pytest.approx(0.0028, abs=0.0003)
    assert output_frames(b36.frames, b36.rate - 2000) / MIX_RATE == pytest.approx(0.324, abs=0.001)


def test_pitch_changes_by_the_frequency_ratio():
    source = tone(1000, 0.2, 11025)
    for new_freq in (11025 - 2000, 11025 + 1900):
        pcm = render_stereo(source, new_freq, 0, 1.0)
        assert dominant_hz(pcm[:, 0].astype(np.float64)) == pytest.approx(1000 * new_freq / 11025, rel=0.02)


def test_length_scales_inversely_with_frequency():
    source = tone(500, 0.1, 22050)
    assert output_frames(source.frames, 22050) == pytest.approx(0.1 * MIX_RATE, abs=2)
    assert resample(source, 22050 * 2).shape[0] == pytest.approx(0.05 * MIX_RATE, abs=2)
    assert resample(source, 11025).shape[0] == pytest.approx(0.2 * MIX_RATE, abs=2)


def test_level_is_kept_at_full_volume_and_scales_with_volume():
    source = tone(500, 0.1, 22050, amp=0.5)
    full = render_stereo(source, 22050 - 100, 0, 1.0)
    assert 16000 < np.abs(full).max() <= 16384
    half = render_stereo(source, 22050 - 100, 0, 0.5)
    assert np.abs(half).max() == pytest.approx(np.abs(full).max() / 2, abs=2)
    assert not render_stereo(source, 22050, 0, 0.0).any()


def test_loud_boost_clips_without_wrapping():
    source = tone(500, 0.05, 22050, amp=0.9)
    boosted = render_stereo(source, 22050, 0, 2.0)
    assert boosted.max() == 32767 and boosted.min() == -32768
    assert np.abs(np.diff(boosted[:, 0].astype(np.int32))).max() < 20000     # no wrap-around jumps


def test_pan_shows_in_channel_levels():
    source = tone(500, 0.1, 22050)
    pcm = render_stereo(source, 22050 - 100, 600, 1.0)         # right: left is 6 dB down
    left, right = np.abs(pcm[:, 0]).max(), np.abs(pcm[:, 1]).max()
    assert left / right == pytest.approx(10 ** (-6 / 20), rel=0.02)
    pcm = render_stereo(source, 22050 - 100, -1000, 1.0)
    assert np.abs(pcm[:, 1]).max() / np.abs(pcm[:, 0]).max() == pytest.approx(10 ** (-10 / 20), rel=0.02)


def test_stereo_source_pans_as_balance():
    data = np.stack([np.full(2000, 0.5), np.full(2000, -0.5)], axis=1).astype(np.float32)
    pcm = render_stereo(Sampled(data, 22050), 22050, 0, 1.0)
    assert pcm[100, 0] > 0 > pcm[100, 1]


def test_single_frame_and_extreme_frequencies_do_not_fail():
    one = Sampled(np.array([[0.5]], np.float32), 8000)
    assert render_stereo(one, 8000, 0, 1.0).shape[0] >= 1
    assert render_stereo(tone(500, 0.01, 8000), 100, 0, 1.0).shape[0] > 0
    assert render_stereo(tone(500, 0.01, 8000), 200_000, 0, 1.0).shape[0] > 0


def test_every_shipped_wav_renders_at_both_extremes_without_gaining_level():
    for number in range(1, 43):
        sound = load_sound_file(os.path.join(SHIPPED, f"brain{number}.wav"))
        for freq in (sound.rate - 2000, sound.rate + 1900):
            if not usable_frequency(freq):
                continue
            pcm = render_stereo(sound, freq, 0, 1.0)
            assert pcm.dtype == np.int16 and pcm.shape[1] == 2
            assert np.abs(pcm).max() <= round(np.abs(sound.data).max() * 32767) + 1, (number, freq)
