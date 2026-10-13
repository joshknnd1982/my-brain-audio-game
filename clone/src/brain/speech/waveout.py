"""A small Windows audio output that stops at once. This is inspired by Jim Kitchen's Brain.

Used by the SAPI 5 backend's rendered mode (DECISIONS 2026-10-13, speech latency): SAPI makes the
speech into memory and this plays it through winmm waveOut. With SAPI's own audio output the
call that stops speech (purge) blocked for up to 700 ms on some voices (FlexVoice2 Bill), because
the engine was still writing to the device; here stopping is waveOutReset, which returns at once.

One output, 16-bit mono at a fixed rate. write() queues a block behind what is playing, busy()
says whether anything is still playing, reset() drops everything. No callbacks: busy() looks at
the DONE flag of each block, so there is no code running on a foreign thread.
"""
from __future__ import annotations

import ctypes
import logging
import threading
import time
from ctypes import wintypes

log = logging.getLogger(__name__)

WAVE_MAPPER = 0xFFFFFFFF
WAVE_FORMAT_PCM = 1
CALLBACK_NULL = 0
WHDR_DONE = 0x1
MMSYSERR_NOERROR = 0


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [("wFormatTag", wintypes.WORD), ("nChannels", wintypes.WORD),
                ("nSamplesPerSec", wintypes.DWORD), ("nAvgBytesPerSec", wintypes.DWORD),
                ("nBlockAlign", wintypes.WORD), ("wBitsPerSample", wintypes.WORD), ("cbSize", wintypes.WORD)]


class WAVEHDR(ctypes.Structure):
    pass


WAVEHDR._fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD),
                    ("dwBytesRecorded", wintypes.DWORD), ("dwUser", ctypes.c_void_p),
                    ("dwFlags", wintypes.DWORD), ("dwLoops", wintypes.DWORD),
                    ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_void_p)]


class WaveOutError(OSError):
    pass


def _winmm():
    lib = ctypes.WinDLL("winmm")
    handle = ctypes.c_void_p
    hdr_ptr = ctypes.POINTER(WAVEHDR)
    lib.waveOutOpen.argtypes = [ctypes.POINTER(handle), wintypes.UINT, ctypes.POINTER(WAVEFORMATEX),
                                ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
    lib.waveOutOpen.restype = wintypes.UINT
    for name in ("waveOutPrepareHeader", "waveOutUnprepareHeader", "waveOutWrite"):
        fn = getattr(lib, name)
        fn.argtypes = [handle, hdr_ptr, wintypes.UINT]
        fn.restype = wintypes.UINT
    for name in ("waveOutReset", "waveOutClose"):
        fn = getattr(lib, name)
        fn.argtypes = [handle]
        fn.restype = wintypes.UINT
    return lib


STUCK_SECONDS = 2.0     # a block still not reported done this long after it should have ended: the device is stuck


class WaveOut:
    """16-bit mono PCM output. Raises WaveOutError from the constructor when no device opens."""

    _library = staticmethod(_winmm)      # tests replace it

    def __init__(self, rate: int = 44100, clock=time.monotonic):
        self.rate = rate
        self._clock = clock
        self._expected_end = 0.0         # when everything queued should have finished playing
        self._lib = self._library()
        self._lock = threading.Lock()
        self._blocks: list[tuple[WAVEHDR, ctypes.Array]] = []
        self._closed = False
        fmt = WAVEFORMATEX(WAVE_FORMAT_PCM, 1, rate, rate * 2, 2, 16, 0)
        self._handle = ctypes.c_void_p()
        result = self._lib.waveOutOpen(ctypes.byref(self._handle), WAVE_MAPPER, ctypes.byref(fmt),
                                       None, None, CALLBACK_NULL)
        if result != MMSYSERR_NOERROR:
            raise WaveOutError(f"waveOutOpen failed with code {result}")

    def write(self, pcm: bytes) -> bool:
        """Queue 16-bit mono samples behind what is playing. False when the device refuses."""
        if not pcm:
            return True
        with self._lock:
            if self._closed:
                return False
            self._collect()
            data = ctypes.create_string_buffer(bytes(pcm), len(pcm))
            hdr = WAVEHDR(ctypes.cast(data, ctypes.c_void_p), len(pcm), 0, None, 0, 0, None, None)
            size = ctypes.sizeof(hdr)
            if self._lib.waveOutPrepareHeader(self._handle, ctypes.byref(hdr), size) != MMSYSERR_NOERROR:
                return False
            if self._lib.waveOutWrite(self._handle, ctypes.byref(hdr), size) != MMSYSERR_NOERROR:
                self._lib.waveOutUnprepareHeader(self._handle, ctypes.byref(hdr), size)
                return False
            self._blocks.append((hdr, data))
            self._expected_end = max(self._clock(), self._expected_end) + len(pcm) / (2.0 * self.rate)
            return True

    def busy(self) -> bool:
        """True while a block is playing. A device that never reports a block done (another program holding it,
        a driver stall) would make the game wait for speech forever: after STUCK_SECONDS past the time the audio
        should have ended, the blocks are dropped and the player says it is idle."""
        with self._lock:
            self._collect()
            if self._blocks and not self._closed and self._clock() > self._expected_end + STUCK_SECONDS:
                log.warning("the audio device did not finish speech %.1f s after it should have; dropping it",
                            self._clock() - self._expected_end)
                self._lib.waveOutReset(self._handle)
                self._collect()
                for hdr, _data in self._blocks:     # a stuck block must not stay prepared
                    self._lib.waveOutUnprepareHeader(self._handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
                self._blocks = []
                self._expected_end = 0.0
            return bool(self._blocks)

    def reset(self) -> None:
        """Stop playing at once and drop everything queued."""
        with self._lock:
            if self._closed:
                return
            self._lib.waveOutReset(self._handle)
            self._collect()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._lib.waveOutReset(self._handle)
            self._collect()
            self._closed = True
            self._lib.waveOutClose(self._handle)

    def _collect(self) -> None:
        """Release the blocks the device has finished with (lock held)."""
        keep = []
        for hdr, data in self._blocks:
            if hdr.dwFlags & WHDR_DONE:
                self._lib.waveOutUnprepareHeader(self._handle, ctypes.byref(hdr), ctypes.sizeof(hdr))
            else:
                keep.append((hdr, data))
        self._blocks = keep
