"""Start Brain: window, speech, game thread. This is inspired by Jim Kitchen's Brain.

Threads: the main thread runs the window and posts keys; the game thread runs the program
flow the way the original's Form_Load did (waits, DoEvents-style key pumping); the SAPI 5
speech thread owns the voice. Closing the window ends the game thread at its next key pump
or speech wait.
"""
from __future__ import annotations

import dataclasses
import logging
import os
import threading

from . import VERSION
from .data.lifecycle import arm_exit_deadline, leave_program_folder
from .data.logsetup import install_exception_logging, setup_logging
from .data import paths
from .data.settingsfile import SettingsStore
from .data.voiceguard import VoiceGuard, voice_label
from .game import texts
from .game.flow import Game
from .audio import Audio, SoundLibrary
from .game.functions import Functions
from .game.keys import GameQuit, KeyInput
from .speech import create_speech
from .speech.voices import VoiceCatalog

log = logging.getLogger("brain")


def main() -> int:
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # no pygame banner (P6 note)
    log_path = setup_logging(logging.DEBUG if os.environ.get("BRAIN_DEBUG") else logging.INFO)
    install_exception_logging()
    log.info("Brain clone %s starting; log %s", VERSION, log_path)
    leave_program_folder(paths.program_dir(), paths.user_data_dir())   # never hold the program folder open (data/lifecycle.py)
    from .ui.window import BrainWindow

    store = SettingsStore()
    settings = store.load()     # creates, reads or heals settings.txt; the original values when anything is wrong
    keys = KeyInput()
    speech_holder: dict = {}
    deadlines: list = []                    # timers that end the process if closing hangs; cancelled when main() returns

    def on_close():
        deadlines.append(arm_exit_deadline())   # an orderly close that hangs must not leave the process behind
        keys.close()
        speech = speech_holder.get("speech")
        if speech is not None:
            speech.stop()

    frame = BrainWindow(keys.post, on_close)
    frame.show()

    guard = VoiceGuard(paths.user_data_dir())
    guard.recover()                         # a voice that took the last run down is set aside (data/voiceguard.py)
    saved_voice = settings.speech.voice_id
    skipped = bool(saved_voice) and guard.is_crashed(saved_voice)
    speech_settings = dataclasses.replace(settings.speech, voice_id=None) if skipped else settings.speech
    guard.arm(speech_settings.voice_id)     # removed again after the voice has spoken, or when Brain closes normally
    speech, started = create_speech(speech_settings)
    speech_holder["speech"] = speech
    speech.watch_voice_health(guard.clear)
    if skipped:
        store.note_voice_crashed(voice_label(saved_voice), started.voice_name)
    else:
        store.note_voice_fallback(settings.speech.voice_id, started.voice_id)
    audio = Audio(SoundLibrary(), settings.audio)
    log.info("audio ready: %s, %d sounds in the pool", "device open" if audio.ok else f"silent ({audio.error})",
             audio.library.pool_size())
    if not started.ok:
        guard.clear()                       # no voice at all is not a crash
        for timer in deadlines:
            timer.cancel()
        no_voices(speech, frame, started.error)
        audio.close()
        speech.close()
        return 1

    catalog = VoiceCatalog()
    catalog.load_async()    # the voice list is read in the background; the Settings menu waits for it if needed
    functions = Functions(speech, keys, audio, settings, catalog, paths.export_dir(), paths.open_folder,
                          on_change=store.save, settings_dir=store.folder, voice_guard=guard)
    store.voice_name = functions.voice_name     # the note above the saved voice in settings.txt

    def game_thread():
        try:
            Game(speech, keys, audio, paths.program_dir(), functions=functions, notice_sources=(store,)).run()
        except GameQuit:
            pass
        except Exception:
            log.exception("unexpected error in the game thread")
        finally:
            log.debug("game thread ended")
            frame.close()                   # thread-safe: posts WM_CLOSE to the window

    thread = threading.Thread(target=game_thread, name="game", daemon=True)
    thread.start()
    frame.run()
    log.debug("main loop ended")
    keys.close()
    thread.join(2.0)
    audio.close()
    speech.close()
    guard.clear()                           # closed normally: whatever voice was in use did not crash
    for timer in deadlines:
        timer.cancel()                      # main() ends: the entry point ends the process (data/lifecycle.finish)
    log.info("Brain clone closed")
    return 0


def no_voices(speech, frame, error: str) -> None:
    """GAME_SPEC 15 and DECISIONS P5: screen reader copy, the original's box, clean exit."""
    log.error("no SAPI 5 voice: %s", error)
    speech.screen_reader_message(texts.NO_VOICES_SPOKEN)
    frame.message_box(texts.NO_VOICES + "\n" + texts.CONTACT, texts.MESSAGE_TITLE)
    frame.destroy()
