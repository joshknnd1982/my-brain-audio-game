"""NVDA speech backend through the NVDA controller client DLL. This is inspired by Jim Kitchen's Brain.

NVDA Controller Client 2026.2 (LGPL 2.1, NV Access, shipped unmodified in nvda_client/):
x86/nvdaControllerClient.dll for 32-bit builds, x64/ for 64-bit. Functions used (nvdaController.h):
testIfRunning, speakText, cancelSpeech, brailleMessage, and from API 2.0 (NVDA 2024.1+)
speakSsml and the SSML mark callback. All return 0 on success, a Windows error code otherwise.

Waiting speech: NVDA has no "speech finished" call. The text is sent as SSML with a mark at the
end, and the wait ends when NVDA reports that mark, or after a time estimated from the text
length. Never call speakSsml with asynchronous=False: on the owner's PC that call blocked for
301 seconds when the SSML held no spoken text (S7.1 test).
Anything failing (DLL missing, NVDA not running or closing) makes is_available() False; the
manager then falls back to SAPI 5 silently (playbook 7.3).
"""
from __future__ import annotations

import ctypes
import itertools
import logging
import os
import struct
import sys
import threading
import time
from xml.sax.saxutils import escape

from .backend import SpeechBackend

log = logging.getLogger(__name__)

SYMBOL_LEVEL_UNCHANGED = -1
SPEECH_PRIORITY_NORMAL = 0
RPC_S_UNKNOWN_IF = 1717  # NVDA older than 2024.1: API 2.0 functions missing


def dll_path() -> str:
    """The controller DLL matching this process's bitness, from the source tree or a frozen build."""
    arch = "x64" if struct.calcsize("P") == 8 else "x86"
    base = getattr(sys, "_MEIPASS", None)
    root = os.path.join(base, "brain", "speech") if base else os.path.dirname(__file__)
    return os.path.join(root, "nvda_client", arch, "nvdaControllerClient.dll")


def estimated_seconds(text: str) -> float:
    """Upper guess for how long NVDA takes to say text, used only when no end mark arrives."""
    return min(30.0, 0.5 + 0.09 * len(text.strip()))


_MarkCallback = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_wchar_p)


class NvdaBackend(SpeechBackend):
    name = "NVDA"

    def __init__(self, path: str | None = None, loader=ctypes.WinDLL, clock=time.monotonic):
        self._path = path or dll_path()
        self._loader = loader
        self._clock = clock
        self._dll = None
        self._load_failed = False
        self._lock = threading.Lock()
        self._marks = itertools.count(1)
        self._mark_cv = threading.Condition()
        self._last_mark = 0          # number of the last end mark NVDA reported
        self._pending_mark = 0       # number of the last end mark sent
        self._deadline = 0.0         # estimated end of everything queued
        self._ssml_ok = True
        self._callback = _MarkCallback(self._on_mark)  # keep a reference while the DLL may call it

    # ----- DLL ----------------------------------------------------------------------
    def _load(self):
        if self._dll is not None or self._load_failed:
            return self._dll
        with self._lock:
            if self._dll is None and not self._load_failed:
                try:
                    dll = self._loader(self._path)
                    dll.nvdaController_testIfRunning.restype = ctypes.c_ulong
                    dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                    dll.nvdaController_speakText.restype = ctypes.c_ulong
                    dll.nvdaController_cancelSpeech.restype = ctypes.c_ulong
                    dll.nvdaController_brailleMessage.argtypes = [ctypes.c_wchar_p]
                    dll.nvdaController_brailleMessage.restype = ctypes.c_ulong
                    try:
                        dll.nvdaController_speakSsml.argtypes = [ctypes.c_wchar_p, ctypes.c_int,
                                                                 ctypes.c_int, ctypes.c_bool]
                        dll.nvdaController_speakSsml.restype = ctypes.c_ulong
                        dll.nvdaController_setOnSsmlMarkReachedCallback.argtypes = [_MarkCallback]
                        dll.nvdaController_setOnSsmlMarkReachedCallback.restype = ctypes.c_ulong
                        dll.nvdaController_setOnSsmlMarkReachedCallback(self._callback)
                    except (AttributeError, OSError):
                        self._ssml_ok = False
                    self._dll = dll
                    log.info("NVDA controller client loaded from %s", self._path)
                except Exception as exc:
                    self._load_failed = True
                    log.warning("NVDA controller client not usable (%s): %s", self._path, exc)
        return self._dll

    def _call(self, name: str, *args) -> int:
        dll = self._load()
        if dll is None:
            return -1
        try:
            return int(getattr(dll, name)(*args))
        except Exception as exc:
            log.warning("NVDA %s failed: %s", name, exc)
            return -1

    # ----- SpeechBackend -----------------------------------------------------------
    def is_available(self) -> bool:
        return self._call("nvdaController_testIfRunning") == 0

    def speak(self, text: str) -> bool:
        number = next(self._marks)
        sent = False
        if self._ssml_ok:
            ssml = f'<speak>{escape(text)}<mark name="brain{number}"/></speak>'
            code = self._call("nvdaController_speakSsml", ssml, SYMBOL_LEVEL_UNCHANGED,
                              SPEECH_PRIORITY_NORMAL, True)
            if code == RPC_S_UNKNOWN_IF:
                self._ssml_ok = False  # older NVDA: plain text from now on
            sent = code == 0
        if not sent:
            sent = self._call("nvdaController_speakText", text) == 0
            if sent:
                number = 0  # no mark will come for plain text
        if sent:
            with self._mark_cv:
                start = max(self._clock(), self._deadline)
                self._deadline = start + estimated_seconds(text)
                self._pending_mark = number
        return sent

    def stop(self) -> None:
        self._call("nvdaController_cancelSpeech")
        with self._mark_cv:
            self._deadline = 0.0
            self._pending_mark = 0
            self._mark_cv.notify_all()

    def wait_until_done(self, abort: threading.Event | None = None) -> None:
        with self._mark_cv:
            while True:
                if abort is not None and abort.is_set():
                    return
                if self._pending_mark and self._last_mark >= self._pending_mark:
                    return
                left = self._deadline - self._clock()
                if left <= 0:
                    return
                self._mark_cv.wait(min(left, 0.02))

    def braille(self, message: str) -> None:
        self._call("nvdaController_brailleMessage", message)

    def close(self) -> None:
        if self._dll is not None and self._ssml_ok:
            try:
                self._dll.nvdaController_setOnSsmlMarkReachedCallback(_MarkCallback())
            except Exception:
                pass

    # ----- callback from NVDA's RPC thread --------------------------------------------
    def _on_mark(self, name) -> int:
        try:
            if name and name.startswith("brain"):
                with self._mark_cv:
                    self._last_mark = max(self._last_mark, int(name[5:]))
                    self._mark_cv.notify_all()
        except Exception:
            pass
        return 0
