"""The pan table and the four panning modes. This is inspired by Jim Kitchen's Brain.

GAME_SPEC 5.5. Pan values are DirectSound pan in hundredths of a dB, negative = left. The table
has index 0 to 12; the original set only 1 to 11 (index 0 and 12 stay Empty, which SetPan reads
as 0, center). Mode 4 rewrites index 6 each time, so the playback start puts it back to 0.
"""
from __future__ import annotations

from .rnd import GameRandom

MODE_NONE, MODE_STATIONARY, MODE_SEMI_RANDOM, MODE_TOTAL_RANDOM = 1, 2, 3, 4
MODE_COUNT = 4
CENTER_INDEX = 6
POSITIONS = 11
HISTORY = 3          # semi random mode skips the last three positions used

PAN_STEPS = (-750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750)   # table index 1..11


def stationary_divisor(wav_count: int) -> float:
    """The original's x: start at 1, then repeat x = x + 0.1 until Int(n / x) <= 11 (doubles, as VB)."""
    x = 1.0
    while True:
        x = x + 0.1
        if int(wav_count / x) <= POSITIONS:
            return x


class PanState:
    """The pan table, the divisor and the semi random history, which lives for the whole run."""

    def __init__(self, rng: GameRandom):
        self.rng = rng
        self.table = [0] * 13
        self.table[1:12] = PAN_STEPS
        self.divisor = stationary_divisor(1)
        self._history: list[int] = []            # most recent last, at most three

    def start_playback(self, wav_count: int) -> None:
        """Playback start: undo mode 4's last random value; the wav count may have changed."""
        self.table[CENTER_INDEX] = 0
        self.divisor = stationary_divisor(wav_count)

    def index_for(self, mode: int, wav_number: int) -> int:
        """The pan table index for a new sound (the original's GoSub). Draws random numbers."""
        if mode == MODE_STATIONARY:
            return int(wav_number / self.divisor)
        if mode == MODE_SEMI_RANDOM:
            while True:
                index = int(self.rng.next() * POSITIONS) + 1
                if index not in self._history:
                    break
            self._history.append(index)
            del self._history[:-HISTORY]
            return index
        if mode == MODE_TOTAL_RANDOM:
            self.table[CENTER_INDEX] = (int(self.rng.next() * 200) - 100) * 10
            return CENTER_INDEX
        return CENTER_INDEX                      # mode 1, and anything unknown: center

    def pan_for(self, mode: int, wav_number: int) -> int:
        """The SetPan value for a new sound."""
        return self.table[self.index_for(mode, wav_number)]
