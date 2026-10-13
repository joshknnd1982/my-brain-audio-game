"""The nine slots: start rule, new-sound statements, failure path (GAME_SPEC 5.3, 5.4). This is inspired by Jim Kitchen's Brain."""
import pytest

from brain.game.panning import MODE_NONE, MODE_STATIONARY
from brain.game.slots import file_bytes, pitch_offset
from brain.audio.render import channel_peak, frames_of
from gamerig import NO_FILE, Rig, Scripted, StubLibrary, make_pick


def rig_with(picks, rng_values, pool=None):
    rig = Rig(StubLibrary(picks, pool), rng=Scripted(*rng_values))
    rig.game.slots.begin_playback()
    return rig


def test_pitch_offset_ranges_and_never_zero():
    assert pitch_offset(Scripted(0.0)) == -20
    assert pitch_offset(Scripted(0.999)) == 19
    assert pitch_offset(Scripted(0.5, 0.525)) == 1          # 0.5 gives 0, so it is drawn again
    from brain.game.rnd import GameRandom
    rng = GameRandom(3)
    values = {pitch_offset(rng) for _ in range(3000)}
    assert values == set(range(-20, 0)) | set(range(1, 20))


def test_first_visit_always_starts_and_computes_the_end_time():
    # number 0.0 -> wav 1; pitch 0.75 -> r = 10 -> +1,000 Hz
    rig = rig_with({1: make_pick(1, rate=11025, frames=1000)}, [0.0, 0.75])
    slots = rig.game.slots
    assert slots.visit(0, MODE_NONE) is True
    assert slots.freq == 12025
    assert slots.size == 1000
    assert slots.q == pytest.approx(2 * 1000 / 12025)
    assert slots.end_time[0] == pytest.approx(rig.clock() + 2 * 1000 / 12025)
    assert slots.has_buffer[0]
    assert len(rig.output.played) == 1 and rig.output.played[0][0] == 0
    assert rig.audio.busy(0)
    # the real length at the new pitch is 1000 / 12025 s: half the cut-off time
    assert frames_of(rig.output.played[0][1]) / 44100 == pytest.approx(1000 / 12025, abs=0.001)


def test_number_draw_covers_the_pool():
    picks = {n: make_pick(n) for n in (1, 2, 3)}
    rig = rig_with(picks, [0.0, 0.75, 0.34, 0.75, 0.999, 0.75])
    slots = rig.game.slots
    for slot in range(3):
        slots.visit(slot, MODE_NONE)
    assert rig.game.audio.library.asked == [1, 2, 3]


def test_a_playing_slot_is_left_alone_until_its_sound_ends():
    rig = rig_with({1: make_pick(1, rate=11025, frames=1000)}, [0.0, 0.75])
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)
    played = len(rig.output.played)
    rig.clock.now += 0.05                                  # the sound takes 83 ms
    assert slots.visit(0, MODE_NONE) is False
    rig.clock.now += 0.04
    assert slots.visit(0, MODE_NONE) is True               # buffer stopped: the next sound starts
    assert len(rig.output.played) == played + 1


def test_a_slot_past_its_end_time_is_cut_off_and_restarted_even_if_playing():
    # a 2 s sound whose file is only 100 bytes: end time 2 * 100 / 12025 = 17 ms (only a bad file can do this)
    rig = rig_with({1: make_pick(1, rate=11025, frames=22050, size=100)}, [0.0, 0.75])
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)
    rig.clock.now += 0.02
    assert rig.audio.busy(0)
    assert slots.visit(0, MODE_NONE) is True


def test_shipped_style_files_are_never_cut_off_early():
    # 8-bit mono: size == frames; end time is twice the real length at any pitch (GAME_SPEC 5.4)
    rig = rig_with({1: make_pick(1, rate=11025, frames=1000)}, [0.0, 0.0])      # r = -20, lowest pitch
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)
    real = frames_of(rig.output.played[0][1]) / 44100
    assert slots.end_time[0] - rig.clock() > 1.9 * real


def test_compressed_player_files_count_their_decoded_size():
    ogg = make_pick(1, rate=44100, frames=44100, size=3000, path="brain1.ogg")
    assert file_bytes(ogg) == 88200
    wav = make_pick(1, rate=44100, frames=44100, size=88244, path="brain1.wav")
    assert file_bytes(wav) == 88244
    assert file_bytes(make_pick(1, sound=False, size=777)) == 777
    assert file_bytes(make_pick(1, sound=False, size=NO_FILE)) is None


def test_pan_follows_the_mode():
    # 42 wavs; the pick for number 4 under stationary panning goes to index 1 = -750: left full, right 10^(-750/2000)
    rig = rig_with({4: make_pick(4, rate=11025, frames=2000)}, [0.08, 0.75], pool=42)
    rig.game.slots.visit(0, MODE_STATIONARY)
    pcm = rig.output.played[0][1]
    left, right = channel_peak(pcm, 0), channel_peak(pcm, 1)
    assert right / left == pytest.approx(10 ** (-750 / 2000), abs=0.01)


def test_failed_wav_keeps_the_slot_silent_until_its_end_time():
    # a damaged file: size known, no sound. Failure path: freq starts Empty (0) and gets + r * 100
    broken = make_pick(1, sound=False, size=500)
    rig = rig_with({1: broken}, [0.0, 0.75])
    slots = rig.game.slots
    assert slots.visit(0, MODE_NONE) is True
    assert not rig.output.played and not slots.has_buffer[0]
    assert slots.freq == 1000 and slots.size == 500
    assert slots.q == pytest.approx(2 * 500 / 1000)
    end = slots.end_time[0]
    assert end == pytest.approx(rig.clock() + 1.0)
    rig.clock.now += 0.9
    assert slots.visit(0, MODE_NONE) is False              # GetStatus fails: the skip branch
    rig.clock.now += 0.2
    assert slots.visit(0, MODE_NONE) is True               # past the end time: tries again


def test_failure_walks_the_shared_frequency_and_keeps_the_old_size_for_a_missing_file():
    good = make_pick(1, rate=11025, frames=1000)
    missing = make_pick(2, sound=False, size=NO_FILE)        # no file at all: FileLen fails too
    rig = rig_with({1: good, 2: missing}, [0.0, 0.75, 0.5, 0.75], pool=2)
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)                              # wav 1, freq 12,025, size 1,000
    slots.visit(1, MODE_NONE)                              # wav 2 missing: size and freq stay, freq + 1,000
    assert slots.number == 2
    assert slots.size == 1000
    assert slots.freq == 12025 + 1000
    assert slots.q == pytest.approx(2 * 1000 / 13025)
    assert not slots.has_buffer[1]


def test_zero_frequency_keeps_q_but_the_next_statement_still_doubles_it():
    broken = make_pick(1, sound=False, size=500)
    # first: r = +10 gives freq 1,000 and q = 1.0; second: r = -10 gives freq 0: no division, q = 1.0 * 2
    rig = rig_with({1: broken}, [0.0, 0.75, 0.0, 0.25])
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)
    assert slots.freq == 1000 and slots.q == pytest.approx(1.0)
    slots.visit(1, MODE_NONE)
    assert slots.freq == 0
    assert slots.q == pytest.approx(2.0)
    assert slots.end_time[1] == pytest.approx(rig.clock() + 2.0)


def test_negative_frequency_gives_an_end_time_in_the_past():
    broken = make_pick(1, sound=False, size=500)
    rig = rig_with({1: broken}, [0.0, 0.75, 0.0, 0.0])    # freq 1,000, then r = -20: freq -1,000
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)
    slots.visit(1, MODE_NONE)
    assert slots.freq == -1000
    assert slots.q < 0
    assert slots.end_time[1] < rig.clock()
    assert slots.visit(1, MODE_NONE) is True               # restarts at once: no silence at all


def test_end_time_and_buffer_survive_a_new_playback():
    broken = make_pick(1, sound=False, size=500)
    rig = rig_with({1: broken}, [0.0, 0.75])
    slots = rig.game.slots
    slots.visit(0, MODE_NONE)
    end = slots.end_time[0]
    slots.begin_playback()
    assert slots.end_time[0] == end and slots.has_buffer[0] is False
    assert rig.game.audio.library.refreshes >= 2


def test_begin_playback_counts_the_pool_and_never_below_one():
    rig = Rig(StubLibrary({}, pool=0), rng=Scripted(0.5))
    rig.game.slots.begin_playback()
    assert rig.game.slots.wav_count == 1
    rig.game.audio.library.pool = 43
    rig.game.slots.begin_playback()
    assert rig.game.slots.wav_count == 43
    assert rig.game.pans.divisor == pytest.approx(3.6, abs=0.01)


def test_pitch_variation_setting_narrows_or_removes_the_pitch_change():
    from brain.game.rnd import GameRandom
    rng = GameRandom(5)
    assert {pitch_offset(rng, 4) for _ in range(2000)} == {-4, -3, -2, -1, 1, 2, 3}
    assert pitch_offset(Scripted(0.0), 0) == 0          # no random number is drawn, nothing can loop
    scripted = Scripted(0.5)
    pitch_offset(scripted, 0)
    assert scripted.draws == 0
    assert pitch_offset(Scripted(0.0), 20) == -20 and pitch_offset(Scripted(0.999), 20) == 19   # the original
