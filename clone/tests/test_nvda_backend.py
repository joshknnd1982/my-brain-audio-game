"""NVDA backend with a fake controller DLL (never speaks). This is inspired by Jim Kitchen's Brain."""
import re
import threading
import time

from brain.speech.nvda import RPC_S_UNKNOWN_IF, NvdaBackend, estimated_seconds


class Func:
    def __init__(self, impl):
        self.impl = impl
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.impl(*args)


class FakeDll:
    def __init__(self, running=True, ssml_code=0, send_marks=True):
        self.running = running
        self.ssml_code = ssml_code
        self.send_marks = send_marks
        self.callback = None
        self.calls = []
        self.nvdaController_testIfRunning = Func(lambda: 0 if self.running else 1753)
        self.nvdaController_speakText = Func(self._speak_text)
        self.nvdaController_cancelSpeech = Func(lambda: self.calls.append(("cancel",)) or 0)
        self.nvdaController_brailleMessage = Func(lambda m: self.calls.append(("braille", m)) or 0)
        self.nvdaController_speakSsml = Func(self._speak_ssml)
        self.nvdaController_setOnSsmlMarkReachedCallback = Func(self._set_cb)

    def _set_cb(self, cb):
        self.callback = cb
        return 0

    def _speak_text(self, text):
        self.calls.append(("text", text))
        return 0 if self.running else 1753

    def _speak_ssml(self, ssml, symbols, priority, asynchronous):
        self.calls.append(("ssml", ssml, asynchronous))
        if self.ssml_code:
            return self.ssml_code
        mark = re.search(r'<mark name="([^"]+)"/>', ssml).group(1)
        if self.send_marks:  # NVDA reports the end mark 50 ms later, from another thread
            threading.Timer(0.05, self.callback, args=(mark,)).start()
        return 0


def make(dll):
    return NvdaBackend(path="fake.dll", loader=lambda path: dll)


def test_missing_dll_means_unavailable_and_silent():
    def fail(path):
        raise OSError("not found")
    backend = NvdaBackend(path="missing.dll", loader=fail)
    assert not backend.is_available()
    assert not backend.speak("x")
    backend.stop()
    backend.wait_until_done()


def test_not_running_means_unavailable():
    assert not make(FakeDll(running=False)).is_available()
    assert make(FakeDll()).is_available()


def test_speak_sends_async_ssml_with_escaped_text_and_end_mark():
    dll = FakeDll()
    backend = make(dll)
    assert backend.speak("a & b <c>")
    kind, ssml, asynchronous = dll.calls[-1]
    assert kind == "ssml" and asynchronous is True        # never the blocking form
    assert ssml.startswith("<speak>a &amp; b &lt;c&gt;<mark name=\"brain")


def test_wait_ends_at_the_end_mark():
    backend = make(FakeDll())
    backend.speak("a sentence that would be estimated at several seconds long " * 3)
    start = time.monotonic()
    backend.wait_until_done()
    took = time.monotonic() - start
    assert 0.03 < took < 0.5


def test_wait_without_marks_uses_the_estimate():
    backend = make(FakeDll(send_marks=False))
    backend.speak("hi")
    start = time.monotonic()
    backend.wait_until_done()
    assert abs((time.monotonic() - start) - estimated_seconds("hi")) < 0.1


def test_old_nvda_falls_back_to_speak_text():
    dll = FakeDll(ssml_code=RPC_S_UNKNOWN_IF)
    backend = make(dll)
    assert backend.speak("hello")
    assert dll.calls[-1] == ("text", "hello")
    backend.speak("again")
    assert dll.calls[-1] == ("text", "again")    # SSML not retried


def test_stop_cancels_and_ends_waits():
    dll = FakeDll(send_marks=False)
    backend = make(dll)
    backend.speak("x" * 200)
    threading.Timer(0.05, backend.stop).start()
    start = time.monotonic()
    backend.wait_until_done()
    assert time.monotonic() - start < 0.5
    assert ("cancel",) in dll.calls


def test_abort_ends_wait():
    backend = make(FakeDll(send_marks=False))
    backend.speak("x" * 200)
    abort = threading.Event()
    abort.set()
    start = time.monotonic()
    backend.wait_until_done(abort)
    assert time.monotonic() - start < 0.1


def test_braille():
    dll = FakeDll()
    make(dll).braille("Brain")
    assert ("braille", "Brain") in dll.calls
