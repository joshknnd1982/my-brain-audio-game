"""Held Enter during " Press the space bar to stop. " on the real engines, silent (OPEN_QUESTIONS 25). Inspired by Jim Kitchen's Brain.

Runs the real Game with the real SAPI 5 voice at volume 0 and the real mixer with its channel volume
at 0 (nothing is heard), on the real clock. A second thread types what a player would: 9, Enter in
the panning menu, then twelve key-repeat Enters the moment the space bar prompt starts speaking, then
Escape twice. The spec's answer (GAME_SPEC 8.4): slot 1 starts one sound, playback stops, the main
menu prompt returns, nothing is echoed. Prints what happened and a verdict.
Usage (from clone/): python tools/held_enter_check.py <scratch folder>
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
os.environ["BRAIN_DATA_DIR"] = sys.argv[1]
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.makedirs(sys.argv[1], exist_ok=True)

from brain.audio import Audio, SoundLibrary  # noqa: E402
from brain.data.settings import Settings  # noqa: E402
from brain.game import texts  # noqa: E402
from brain.game.flow import Game  # noqa: E402
from brain.game.keys import KeyInput  # noqa: E402
from brain.speech import create_speech  # noqa: E402
from brain.speech.manager import SpeechManager  # noqa: E402

ENTER, ESC = 13, 27
settings = Settings.defaults()
settings.speech.volume = 0
speech, started = create_speech(settings.speech)
assert started.ok, started.error
audio = Audio(SoundLibrary(), settings.audio)
if hasattr(audio.output, "volume"):
    audio.output.volume = 0.0               # the real mixer, silent
keys = KeyInput()
starts = []                                 # (seconds, slot) of every sound start
real_play = audio.play
T0 = time.monotonic()


def play(slot, pick, freq=None, pan=0):
    starts.append((round(time.monotonic() - T0, 3), slot))
    return real_play(slot, pick, freq, pan)


audio.play = play
spoken = []
counts = {}
real_send = SpeechManager._send


def send(self, text):
    spoken.append((round(time.monotonic() - T0, 3), text))
    counts[text] = counts.get(text, 0) + 1
    if text == texts.MAIN_PROMPT and counts[text] == 1:
        threading.Timer(0.3, keys.post, args=(57,)).start()                       # nine sounds
    elif text == texts.MODE_NAMES[0] and counts[text] == 1:
        threading.Timer(0.4, keys.post, args=(ENTER,)).start()                    # start playback
    elif text == texts.PRESS_SPACE:
        for i in range(12):                                                       # the key repeat of a held Enter
            threading.Timer(0.15 + 0.03 * i, keys.post, args=(ENTER,)).start()
    elif text == texts.MAIN_PROMPT and counts[text] == 2:
        threading.Timer(0.5, keys.post, args=(ESC,)).start()                      # leave from the main menu
    return real_send(self, text)


SpeechManager._send = send
game = Game(speech, keys, audio, sys.argv[1], find_menu=lambda folder: None, launch_menu=lambda path: True)
audio.beeper = type("Silent", (), {"beep": lambda self: True})()
game.run()
audio.close()
speech.close()

print("spoken:")
for at, text in spoken:
    print(f"  {at:6.2f} s  {text!r}")
print("sound starts (seconds, slot):", starts)
ok = ([slot for _, slot in starts] == [0] and counts.get(texts.MAIN_PROMPT) == 2
      and not any(t in ("\r", "") for _, t in spoken))
print("VERDICT:", "as the spec says: slot 1 started once, playback stopped, the main menu came back, nothing echoed"
      if ok else "DIFFERENT FROM THE SPEC, look at the lists above")
sys.exit(0 if ok else 1)
