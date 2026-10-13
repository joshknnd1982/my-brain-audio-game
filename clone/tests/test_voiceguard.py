"""A voice that kills the program is set aside at the next start (owner bug 2026-10-13: SmoothTalker chosen, then
Brain would not start any more). This is inspired by Jim Kitchen's Brain.
"""
import os

import pytest

import brain.app as app
from brain.data.voiceguard import CRASHED_FILE, MAX_LISTED, TRIAL_FILE, VoiceGuard, voice_label
from brain.speech.fake import FakeBackend
from brain.speech.manager import SpeechManager
from brain.speech.sapi5 import SapiStart

from test_functions import DOWN, ENTER, voice_rig
from test_sapi_render import make

VOICE = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\TokenEnums\SmoothTalker\SmoothTalker"


def test_a_trial_that_never_ended_puts_the_voice_on_the_list_and_is_reported_once(tmp_path):
    guard = VoiceGuard(str(tmp_path))
    guard.arm(VOICE)
    assert (tmp_path / TRIAL_FILE).is_file()
    restarted = VoiceGuard(str(tmp_path))            # the next start
    assert restarted.recover() == VOICE
    assert restarted.is_crashed(VOICE) and restarted.is_crashed(VOICE.lower())
    assert not (tmp_path / TRIAL_FILE).exists()
    assert VoiceGuard(str(tmp_path)).recover() is None          # reported once
    assert (tmp_path / CRASHED_FILE).read_text().split() == [VOICE]


def test_a_voice_that_spoke_or_a_normal_close_leaves_no_trial_behind(tmp_path):
    guard = VoiceGuard(str(tmp_path))
    guard.arm(VOICE)
    guard.clear()
    assert guard.recover() is None and not guard.is_crashed(VOICE)
    guard.arm(None)                                   # the default voice is never put on trial
    assert not (tmp_path / TRIAL_FILE).exists()


def test_choosing_a_set_aside_voice_again_takes_it_off_the_list(tmp_path):
    guard = VoiceGuard(str(tmp_path))
    guard.arm(VOICE)
    guard.recover()
    guard.forget(VOICE)
    assert not guard.is_crashed(VOICE) and guard.crashed() == []


def test_the_list_is_bounded_and_survives_other_voices(tmp_path):
    guard = VoiceGuard(str(tmp_path))
    for i in range(MAX_LISTED + 10):
        guard.arm(f"voice-{i}")
        guard.recover()
    assert len(guard.crashed()) == MAX_LISTED and guard.is_crashed(f"voice-{MAX_LISTED + 9}")
    assert not guard.is_crashed("voice-0")


def test_a_folder_that_cannot_be_written_never_raises(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    guard = VoiceGuard(str(blocker / "inside"))
    guard.arm(VOICE)
    guard.clear()
    assert guard.recover() is None and guard.crashed() == [] and not guard.is_crashed(VOICE)
    guard.forget(VOICE)


def test_a_label_for_the_spoken_notice():
    assert voice_label(VOICE) == "SmoothTalker"
    assert voice_label("") == "voice" and voice_label("token-3") == "token-3"


# ----- the whole program -----

def fake_speech(voice_name="Fake voice"):
    sapi = FakeBackend(name="sapi")
    manager = SpeechManager(sapi, None, "sapi")
    return manager, SapiStart(ok=True, voice_count=2, voice_id="first", voice_name=voice_name), sapi


def write_settings(folder, voice):
    (folder / "settings.txt").write_text(f"# Brain settings, format 1\nspeech_voice = {voice}\nsound_volume = 0\n", encoding="utf-8")


@pytest.mark.window
def test_after_a_crash_brain_starts_with_the_default_voice_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_DATA_DIR", str(tmp_path))
    write_settings(tmp_path, VOICE)
    (tmp_path / TRIAL_FILE).write_text(VOICE + "\n")              # the last run died while this voice was in trial
    asked = []
    manager, started, sapi = fake_speech()

    def create(speech_settings):
        asked.append(speech_settings.voice_id)
        return manager, started

    monkeypatch.setattr(app, "create_speech", create)
    import brain.ui.window as window_module
    import threading
    real = window_module.BrainWindow

    class Closing(real):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            threading.Timer(1.5, self.close).start()

    monkeypatch.setattr(window_module, "BrainWindow", Closing)
    assert app.main() == 0
    assert asked == [None]                                         # the saved voice was not opened
    assert any("The voice SmoothTalker crashed Brain last time" in text and "Fake voice" in text for text in sapi.spoken())
    assert VOICE in (tmp_path / "settings.txt").read_text()       # the saved choice is kept
    assert not (tmp_path / TRIAL_FILE).exists()                    # closed normally: no new trial left


@pytest.mark.window
def test_a_normal_start_opens_the_saved_voice_and_leaves_no_trial_after_closing(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_DATA_DIR", str(tmp_path))
    write_settings(tmp_path, "token-7")
    asked, armed = [], []
    manager, started, sapi = fake_speech()
    started = SapiStart(ok=True, voice_count=2, voice_id="token-7", voice_name="Seven")

    def create(speech_settings):
        asked.append(speech_settings.voice_id)
        armed.append((tmp_path / TRIAL_FILE).read_text().strip() if (tmp_path / TRIAL_FILE).exists() else None)
        return manager, started

    monkeypatch.setattr(app, "create_speech", create)
    import brain.ui.window as window_module
    import threading
    real = window_module.BrainWindow

    class Closing(real):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            threading.Timer(1.0, self.close).start()

    monkeypatch.setattr(window_module, "BrainWindow", Closing)
    assert app.main() == 0
    assert asked == ["token-7"] and armed == ["token-7"]           # the trial file existed while the voice was opened
    assert not (tmp_path / TRIAL_FILE).exists()


# ----- in the F2 voice list and in the SAPI backend -----

def test_choosing_a_voice_in_the_list_puts_it_on_trial_and_gives_a_set_aside_voice_another_chance(tmp_path):
    guard = VoiceGuard(str(tmp_path))
    guard.arm("token-1")
    guard.recover()                                                # token-1 crashed Brain before
    assert guard.is_crashed("token-1")
    rig = voice_rig([DOWN, ENTER], voice_guard=guard)
    assert rig.settings.speech.voice_id == "token-1"
    assert not guard.is_crashed("token-1")                         # asking for it again is another try
    assert (tmp_path / TRIAL_FILE).read_text().strip() == "token-1"


def test_the_sapi_backend_reports_the_first_speech_that_ended_once():
    b, voice, player = make()
    try:
        done = []
        b.on_healthy = lambda: done.append(1)
        b.speak("Select")
        b.wait_until_done()
        import time
        time.sleep(0.2)
        b.speak("Again")
        b.wait_until_done()
        time.sleep(0.2)
        assert done == [1]
    finally:
        b.close()
