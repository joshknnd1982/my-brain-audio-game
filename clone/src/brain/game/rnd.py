"""The program's random source. This is inspired by Jim Kitchen's Brain.

GAME_SPEC 6: the original used VB's Rnd, a number from 0 up to but not including 1, and called
Randomize Timer at each playback start. The clone keeps the same ranges and the same calls in
the same order, with its own generator (exact sequences cannot match, the original seeded from
the clock). The logic only ever calls next() and reseed(), so tests can script the numbers.
"""
from __future__ import annotations

import random


class GameRandom:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def next(self) -> float:
        """VB's Rnd: 0 <= x < 1."""
        return self._rng.random()

    def reseed(self) -> None:
        """VB's Randomize Timer: seed from the clock (the operating system's entropy here)."""
        self._rng = random.Random()
