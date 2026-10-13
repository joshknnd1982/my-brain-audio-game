"""The nine sound slots: when a slot starts its next sound, and what starting one does. This is inspired by Jim Kitchen's Brain.

GAME_SPEC 5.4. The original ran this code once per slot inside Form_Load, with On Error Resume Next:
a statement that fails is skipped and its variable keeps the old value. The four variables number,
size, freq and q are shared by all nine slots, so a failed statement can leave a value another
slot set. This module repeats the statements in the same order and keeps that behavior, because
the failure path (a missing, empty or damaged wav) depends on it.

Slots are 0..8 here (the spec's 1..9). end_time and the buffer flag stay for the whole run: the
original never reset them between playbacks.
"""
from __future__ import annotations

import logging
from typing import Callable

from ..audio.engine import Audio
from ..audio.library import Pick, SoundLibrary
from .panning import PanState
from .rnd import GameRandom

log = logging.getLogger("brain.game")

SLOT_COUNT = 9
PITCH_STEP_HZ = 100      # r * 100 Hz (GAME_SPEC 5.3)


def pitch_offset(rng: GameRandom, spread: int = 20) -> int:
    """r: a whole number from -20 to 19, never 0 (GAME_SPEC 5.3).

    spread is the Sounds menu's pitch variation (clone addition): r runs from -spread to spread - 1.
    20 is the original; 0 means no change, and then no random number is drawn."""
    if spread <= 0:
        return 0
    while True:
        r = int(rng.next() * 2 * spread) - spread
        if r != 0:
            return r


def file_bytes(pick: Pick) -> int | None:
    """What the original's FileLen would have read: the file's size in bytes.

    The cut-off formula assumes about one byte per sample, which holds for wavs. For ogg, flac and
    mp3 (player files the original could not play) the file is much smaller than the sound, so
    the size of the decoded sound stands in; that keeps the cut-off from ever ending a sound early."""
    if pick.size is None or pick.sound is None:
        return pick.size
    if pick.path and pick.path.lower().endswith(".wav"):
        return pick.size
    return max(pick.size, pick.sound.frames * pick.sound.channels * 2)


class SoundSlots:
    def __init__(self, audio: Audio, library: SoundLibrary, pans: PanState, rng: GameRandom,
                 clock: Callable[[], float]):
        self.audio = audio
        self.library = library
        self.pans = pans
        self.rng = rng
        self.clock = clock
        # per slot (kept across playbacks)
        self.end_time: list[float | None] = [None] * SLOT_COUNT     # None = Empty: the first pass always starts
        self.has_buffer = [False] * SLOT_COUNT                      # False: GetStatus fails (nothing was created)
        # shared by all slots (None = Empty)
        self.number: int | None = None
        self.size: int | None = None
        self.freq: float | None = None
        self.q: float | None = None
        self.wav_count = 1                                          # n, set at every playback start

    def begin_playback(self) -> None:
        """Playback start: rescan the sound files, recount (DECISIONS P5), set the pan divisor."""
        self.audio.refresh()
        self.wav_count = max(1, self.library.pool_size())
        self.pans.start_playback(self.wav_count)

    def visit(self, slot: int, mode: int) -> bool:
        """One slot's turn in the loop. Returns True when it started a new sound."""
        end = self.end_time[slot]
        if end is None or self.clock() > end:
            pass                                   # step 1: past the end time, start a new sound
        elif self.has_buffer[slot]:
            if self.audio.busy(slot):              # step 2: GetStatus says playing, leave it
                return False
        else:
            return False                           # GetStatus failed on the empty buffer: skip branch
        self._start_sound(slot, mode)
        return True

    def _start_sound(self, slot: int, mode: int) -> None:
        """Step 3, one statement at a time (GAME_SPEC 5.4)."""
        self.audio.stop(slot)                      # stop and release the old buffer
        self.has_buffer[slot] = False
        self.number = int(self.wav_count * self.rng.next()) + 1
        pick = self.library.pick_number(self.number)
        size = file_bytes(pick)
        if size is not None:                       # FileLen failed: the old size stays
            self.size = size
        self.has_buffer[slot] = pick.sound is not None      # CreateSoundBufferFromFile
        rate = pick.rate
        if rate is not None:                       # GetFrequency failed: the old freq stays
            self.freq = rate
        r = pitch_offset(self.rng, self.audio.settings.pitch_spread)
        self.freq = (self.freq or 0) + r * PITCH_STEP_HZ
        if self.freq != 0:                         # division by zero: q stays
            self.q = (self.size or 0) / self.freq
        self.q = (self.q or 0) * 2
        self.end_time[slot] = self.clock() + self.q
        pan = self.pans.pan_for(mode, self.number)
        if pick.sound is not None:
            self.audio.play(slot, pick, int(self.freq), pan)
        else:
            log.debug("slot %d: wav %d has no sound, silent until its end time", slot + 1, self.number)
