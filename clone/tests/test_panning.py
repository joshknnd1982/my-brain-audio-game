"""Pan table, divisor and the four panning modes (GAME_SPEC 5.5). This is inspired by Jim Kitchen's Brain."""
import collections

import pytest

from brain.game.panning import (CENTER_INDEX, MODE_NONE, MODE_SEMI_RANDOM, MODE_STATIONARY, MODE_TOTAL_RANDOM,
                                PAN_STEPS, PanState, stationary_divisor)


class Scripted:
    """A Rnd that returns the given numbers in order."""

    def __init__(self, *values):
        self.values = list(values)

    def next(self):
        return self.values.pop(0)


# index per wav number 1..42 for x = 3.5000000000000018 (GAME_SPEC 5.5, WAV_EVENT_MAP)
INDEX_RANGES = {0: (1, 3), 1: (4, 7), 2: (8, 10), 3: (11, 14), 4: (15, 17), 5: (18, 21), 6: (22, 24),
                7: (25, 28), 8: (29, 31), 9: (32, 35), 10: (36, 38), 11: (39, 42)}


def test_pan_table_values():
    pans = PanState(Scripted())
    assert pans.table[0] == 0 and pans.table[12] == 0           # never set: Empty reads as center
    assert pans.table[1:12] == [-750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750]
    assert tuple(pans.table[1:12]) == PAN_STEPS


@pytest.mark.parametrize("count, divisor", [
    (1, 1.1), (13, 1.1), (14, 1.2000000000000002), (22, 1.9000000000000008),
    (41, 3.500000000000002), (42, 3.5000000000000018), (43, 3.6000000000000023),
    (59, 4.999999999999999), (60, 5.099999999999999)])
def test_stationary_divisor_matches_the_spec_values(count, divisor):
    assert stationary_divisor(count) == pytest.approx(divisor, abs=1e-12)
    assert int(count / stationary_divisor(count)) <= 11


def test_stationary_divisor_is_the_first_x_that_fits():
    for count in range(1, 200):
        x = stationary_divisor(count)
        assert int(count / x) <= 11
        assert x == 1.1 or int(count / (x - 0.1)) > 11


def test_stationary_positions_for_the_shipped_42():
    pans = PanState(Scripted())
    pans.start_playback(42)
    for index, (low, high) in INDEX_RANGES.items():
        for number in range(low, high + 1):
            assert pans.index_for(MODE_STATIONARY, number) == index, number
    assert pans.pan_for(MODE_STATIONARY, 1) == 0                 # the quirk: wav 1 is centered
    assert pans.pan_for(MODE_STATIONARY, 4) == -750
    assert pans.pan_for(MODE_STATIONARY, 42) == 750


def test_stationary_top_index_with_few_wavs():
    pans = PanState(Scripted())
    pans.start_playback(12)
    assert max(pans.index_for(MODE_STATIONARY, n) for n in range(1, 13)) == 10   # +750 unused (GAME_SPEC 5.5)
    pans.start_playback(13)
    assert max(pans.index_for(MODE_STATIONARY, n) for n in range(1, 14)) == 11


def test_no_panning_is_always_center_and_draws_nothing():
    pans = PanState(Scripted())                                  # a draw would raise IndexError
    for number in range(1, 43):
        assert pans.pan_for(MODE_NONE, number) == 0


def test_semi_random_skips_the_last_three_positions():
    # draws: 0.0 -> index 1; 0.0 again is in history -> redrawn; 0.5 -> index 6
    pans = PanState(Scripted(0.0, 0.0, 0.5))
    assert pans.index_for(MODE_SEMI_RANDOM, 1) == 1
    assert pans.index_for(MODE_SEMI_RANDOM, 1) == 6
    # Rnd * 11 picks the position; 0.999 gives 11
    pans = PanState(Scripted(0.999))
    assert pans.index_for(MODE_SEMI_RANDOM, 1) == 11


def test_semi_random_history_holds_three_then_forgets():
    pans = PanState(Scripted(0.0, 0.1, 0.2, 0.3, 0.0))
    got = [pans.index_for(MODE_SEMI_RANDOM, 1) for _ in range(4)]
    assert got == [1, 2, 3, 4]                                    # int(0.1 * 11) + 1 = 2, 0.2 -> 3, 0.3 -> 4
    assert pans.index_for(MODE_SEMI_RANDOM, 1) == 1               # 1 left the history of 2, 3, 4


def test_semi_random_statistics(tmp_path):
    from brain.game.rnd import GameRandom
    pans = PanState(GameRandom(5))
    picks = [pans.index_for(MODE_SEMI_RANDOM, 1) for _ in range(20000)]
    for i in range(3, len(picks)):
        assert picks[i] not in picks[i - 3:i]
    counts = collections.Counter(picks)
    assert set(counts) == set(range(1, 12))
    assert min(counts.values()) > 20000 / 11 * 0.85


def test_total_random_writes_the_center_entry():
    pans = PanState(Scripted(0.0, 0.999, 0.5))
    assert pans.pan_for(MODE_TOTAL_RANDOM, 1) == -1000            # (0 - 100) * 10
    assert pans.table[CENTER_INDEX] == -1000
    assert pans.pan_for(MODE_TOTAL_RANDOM, 1) == (int(0.999 * 200) - 100) * 10 == 990
    assert pans.pan_for(MODE_TOTAL_RANDOM, 1) == 0                # int(100) - 100


def test_total_random_range_and_steps():
    from brain.game.rnd import GameRandom
    pans = PanState(GameRandom(9))
    values = {pans.pan_for(MODE_TOTAL_RANDOM, 1) for _ in range(5000)}
    assert min(values) >= -1000 and max(values) <= 990
    assert all(v % 10 == 0 for v in values)
    assert len(values) > 150


def test_playback_start_puts_the_center_entry_back():
    pans = PanState(Scripted(0.0))
    pans.pan_for(MODE_TOTAL_RANDOM, 1)
    assert pans.table[CENTER_INDEX] == -1000
    pans.start_playback(42)
    assert pans.table[CENTER_INDEX] == 0
    assert pans.pan_for(MODE_NONE, 1) == 0
