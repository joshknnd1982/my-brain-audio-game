"""The whole logic on the real shipped wavs, silent timed output, virtual clock. This is inspired by Jim Kitchen's Brain."""
import collections

import pytest

from brain.audio.library import SoundLibrary, shipped_sounds_dir
from brain.game import texts
from gamerig import Rig, Seeded

ESC, ENTER, DOWN = 27, 13, 40
KEY_9, KEY_A = 57, 65
TABLE = {-750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750}


def run_mode(tmp_path, downs, passes=12000, seed=11):
    lib = SoundLibrary(shipped_sounds_dir(), str(tmp_path / "player"))
    rig = Rig(lib, answers=[KEY_9, *([DOWN] * downs), ENTER, ESC, ESC], rng=Seeded(seed))
    calls = []
    real_play = rig.audio.play

    def recording(slot, pick, freq=None, pan=0):
        calls.append((slot, pick, freq, pan))
        return real_play(slot, pick, freq, pan)

    rig.audio.play = recording
    rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == passes else None
    rig.game.run()
    return rig, calls


@pytest.mark.parametrize("downs", [0, 1, 2, 3])
def test_pitch_and_pan_in_every_mode_on_the_shipped_set(tmp_path, downs):
    rig, calls = run_mode(tmp_path, downs)
    assert len(calls) > 400
    assert rig.game.slots.wav_count == 42
    for slot, pick, freq, pan in calls:
        offset = freq - pick.rate
        assert offset % 100 == 0 and offset != 0 and -2000 <= offset <= 1900
        assert 3500 <= freq <= 46000                                   # GAME_SPEC 5.3
    pans = collections.Counter(pan for *_, pan in calls)
    if downs == 0:
        assert set(pans) == {0}
    elif downs == 1:                                                    # stationary: fixed per wav
        by_wav = collections.defaultdict(set)
        for _, pick, _, pan in calls:
            by_wav[pick.sound_id].add(pan)
        assert all(len(v) == 1 for v in by_wav.values())
        assert {next(iter(by_wav["brain04"])), next(iter(by_wav["brain42"]))} == {-750, 750}
        assert next(iter(by_wav["brain01"])) == 0
    elif downs == 2:
        assert set(pans) == TABLE and min(pans.values()) > len(calls) / 11 * 0.6
    else:
        assert min(pans) >= -1000 and max(pans) <= 990 and all(p % 10 == 0 for p in pans)
        assert len(pans) > 100


def test_every_wav_gets_played_and_all_nine_slots_run(tmp_path):
    rig, calls = run_mode(tmp_path, 0)
    assert len({pick.sound_id for _, pick, _, _ in calls}) == 42
    assert {slot for slot, *_ in calls} == set(range(9))


def test_the_next_sound_starts_right_after_the_last_one_ends(tmp_path):
    """Per slot: the gap between a sound's real end and the next start is a pass or two (1 ms steps)."""
    lib = SoundLibrary(shipped_sounds_dir(), str(tmp_path / "player"))
    rig = Rig(lib, answers=[KEY_9, ENTER, ESC, ESC], rng=Seeded(4))
    starts, ends = collections.defaultdict(list), {}
    real_play = rig.audio.play

    def recording(slot, pick, freq=None, pan=0):
        seconds = real_play(slot, pick, freq, pan)
        if slot in ends:
            starts[slot].append(rig.clock() - ends[slot])
        ends[slot] = rig.clock() + seconds
        return seconds

    rig.audio.play = recording
    rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == 3000 else None
    rig.game.run()
    gaps = [g for slot in starts for g in starts[slot]]
    assert len(gaps) > 200
    assert min(gaps) >= -1e-9 and max(gaps) <= 0.0035                  # one loop pass: sleep 1 ms plus rounding
    assert max(gaps) < 0.01


def test_a_corrupt_added_wav_follows_the_failure_path_and_the_program_keeps_going(tmp_path):
    player = tmp_path / "player" / "sounds"
    player.mkdir(parents=True)
    lib = SoundLibrary(shipped_sounds_dir(), str(tmp_path / "player"))
    (tmp_path / "player" / "brain43.wav").write_bytes(b"RIFF....not a wave at all" * 3)   # damaged: size known, no sound
    lib.refresh()
    assert lib.pool_size() == 43
    rig = Rig(lib, answers=[KEY_9, ENTER, ESC, ESC], rng=Seeded(8))
    asked = []
    real_pick = lib.pick_number
    lib.pick_number = lambda number: (asked.append(number), real_pick(number))[1]
    rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == 6000 else None
    rig.game.run()
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2
    assert 43 in asked and real_pick(43).sound is None and real_pick(43).size is not None
    assert rig.game.slots.wav_count == 43
