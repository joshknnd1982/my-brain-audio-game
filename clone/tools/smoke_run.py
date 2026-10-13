"""Smoke run of the real Brain program with the voice at volume 0. Inspired by Jim Kitchen's Brain.

Starts brain.app.main() as the player would (window, SAPI 5 thread, game thread), presses Escape
by itself as soon as the main menu waits for a key (the exit sequence follows: spoken text, two silent beeps), and reports what was said and how long it
took. The window shows for a few seconds; nothing is heard.
Usage (from clone/): python tools/smoke_run.py <scratch folder for the log>
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
os.environ["BRAIN_DATA_DIR"] = sys.argv[1]
os.makedirs(sys.argv[1], exist_ok=True)
with open(os.path.join(sys.argv[1], "settings.txt"), "w", encoding="utf-8") as handle:     # the real settings file: voice at volume 0
    handle.write("# Brain settings, format 1\nspeech_volume = 0\n")

import brain.app as app  # noqa: E402
from brain.audio.engine import SystemBeeper  # noqa: E402
from brain.game.keys import KeyInput  # noqa: E402
from brain.speech.manager import SpeechManager  # noqa: E402

spoken = []
original_send = SpeechManager._send


def recording_send(self, text):
    spoken.append((round(time.monotonic() - START, 2), text))
    return original_send(self, text)


class AutoEscape(KeyInput):
    def getkey(self, speech):
        self.post(27)
        super().getkey(speech)


SystemBeeper.beep = lambda self: True          # the exit beeps must stay silent in a smoke run
SpeechManager._send = recording_send
app.KeyInput = AutoEscape
START = time.monotonic()
code = app.main()
print(f"exit code {code}, {time.monotonic() - START:.2f} s")
for at, text in spoken:
    print(f"  {at:5.2f} s  {text!r}")
with open(os.path.join(sys.argv[1], "settings.txt"), encoding="utf-8") as saved:
    print("settings.txt still there:", [l.strip() for l in saved if l.strip() and not l.startswith("#")])
with open(os.path.join(sys.argv[1], "logs", "brain.log"), encoding="utf-8") as log:
    print("log:", *[line.split(" ", 3)[-1].rstrip() for line in log], sep="\n  ")
