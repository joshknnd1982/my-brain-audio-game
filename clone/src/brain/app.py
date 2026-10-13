"""Start Brain: window, speech, game thread. This is inspired by Jim Kitchen's Brain.

Threads: the wx main thread runs the window and posts keys; the game thread runs the program
flow the way the original's Form_Load did (waits, DoEvents-style key pumping); the SAPI 5
speech thread owns the voice. Closing the window ends the game thread at its next key pump
or speech wait.
"""
from __future__ import annotations

import logging
import os
import threading

from . import VERSION
from .data.logsetup import install_exception_logging, setup_logging
from .data import paths
from .data.settingsfile import SettingsStore
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
    import wx
    from .ui.window import BrainWindow

    store = SettingsStore()
    settings = store.load()     # creates, reads or heals settings.txt; the original values when anything is wrong
    keys = KeyInput()
    app = wx.App(False)
    speech_holder: dict = {}

    def on_close():
        keys.close()
        speech = speech_holder.get("speech")
        if speech is not None:
            speech.stop()

    frame = BrainWindow(keys.post, on_close)
    frame.Show()
    frame.Raise()

    speech, started = create_speech(settings.speech)
    speech_holder["speech"] = speech
    store.note_voice_fallback(settings.speech.voice_id, started.voice_id)
    audio = Audio(SoundLibrary(), settings.audio)
    log.info("audio ready: %s, %d sounds in the pool", "device open" if audio.ok else f"silent ({audio.error})",
             audio.library.pool_size())
    if not started.ok:
        no_voices(speech, frame, started.error)
        audio.close()
        speech.close()
        return 1

    catalog = VoiceCatalog()
    catalog.load_async()    # the voice list is read in the background; the Settings menu waits for it if needed
    functions = Functions(speech, keys, audio, settings, catalog, paths.export_dir(), paths.open_folder,
                          on_change=store.save, settings_dir=store.folder)
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
            wx.CallAfter(lambda: frame and frame.Close())

    thread = threading.Thread(target=game_thread, name="game", daemon=True)
    thread.start()
    app.MainLoop()
    log.debug("main loop ended")
    keys.close()
    thread.join(2.0)
    audio.close()
    speech.close()
    log.info("Brain clone closed")
    return 0


def no_voices(speech, frame, error: str) -> None:
    """GAME_SPEC 15 and DECISIONS P5: screen reader copy, the original's box, clean exit."""
    import wx
    log.error("no SAPI 5 voice: %s", error)
    speech.screen_reader_message(texts.NO_VOICES_SPOKEN)
    wx.MessageBox(texts.NO_VOICES + "\n" + texts.CONTACT, texts.MESSAGE_TITLE, wx.OK, frame)
    frame.Destroy()
