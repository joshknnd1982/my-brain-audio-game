"""The whole program through app.main(): no voice, and a window closed while the game runs (P8 S8.3).
This is inspired by Jim Kitchen's Brain.

The real Win32 window, the real sound mixer and the real game thread run; speech is a fake so nothing is
heard. The window shows for about a second. The player's folders are not touched (BRAIN_DATA_DIR in tmp_path).
"""
import threading
import time

import pytest

import brain.app as app  # noqa: E402
import brain.ui.window as window_module  # noqa: E402
from brain.game import texts  # noqa: E402
from brain.speech.fake import FakeBackend  # noqa: E402
from brain.speech.manager import SpeechManager  # noqa: E402
from brain.speech.sapi5 import SapiStart  # noqa: E402


def fake_speech(ok, nvda=None):
    sapi = FakeBackend(name="sapi")
    manager = SpeechManager(sapi, nvda, "sapi")
    started = SapiStart(ok=ok, voice_count=1 if ok else 0, voice_id="v", voice_name="Fake voice", error="" if ok else "no voices")
    return manager, started, sapi


@pytest.mark.window
def test_no_sapi_voice_shows_the_originals_box_tells_nvda_and_exits_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_DATA_DIR", str(tmp_path))
    nvda = FakeBackend(name="nvda")
    manager, started, _ = fake_speech(False, nvda)
    monkeypatch.setattr(app, "create_speech", lambda settings: (manager, started))
    boxes = []
    monkeypatch.setattr(window_module.BrainWindow, "message_box", lambda self, text, title: boxes.append((text, title)))
    assert app.main() == 1                                                    # GAME_SPEC 15: the box, then a clean exit
    assert nvda.spoken() == [texts.NO_VOICES_SPOKEN]                          # the screen reader hears the same words
    assert boxes[0][0] == texts.NO_VOICES + "\n" + texts.CONTACT and boxes[0][1] == texts.MESSAGE_TITLE


@pytest.mark.window
def test_closing_the_window_while_the_game_talks_ends_the_program_within_two_seconds(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_DATA_DIR", str(tmp_path))
    manager, started, sapi = fake_speech(True)
    sapi.seconds_per_char = 0.2                                               # the title alone would take five seconds
    monkeypatch.setattr(app, "create_speech", lambda settings: (manager, started))
    closed_at = []
    real_window = window_module.BrainWindow

    class ClosingWindow(real_window):
        """The player closes the window one second after it opens."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            threading.Timer(1.0, self.close_now).start()

        def close_now(self):
            closed_at.append(time.monotonic())
            self.close()

    monkeypatch.setattr(window_module, "BrainWindow", ClosingWindow)
    assert app.main() == 0
    assert closed_at and time.monotonic() - closed_at[0] < 2.5                # the game thread unwound, audio and speech closed
    assert sapi.spoken()[0] == texts.TITLE_SPOKEN                             # it really was in the middle of the title
