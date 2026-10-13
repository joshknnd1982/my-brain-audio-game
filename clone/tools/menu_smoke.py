"""Silent run of the real Brain program through the F1 to F4 menus. Inspired by Jim Kitchen's Brain.

Starts brain.app.main() as the player would (window, real SAPI 5 voice list of this PC, real mixer),
and types a fixed list of keys by itself: help, the speech settings with a real voice choice and
a rate change, the sounds menu with a preview, check, reload, open-folder (patched, nothing opens) and
export, About, then Escape. The voice is at volume 0 and the mixer channel volume is 0, so nothing is
heard. Prints what was said and how long the voice list took.
Usage (from clone/): python tools/menu_smoke.py <scratch folder>
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
from brain.audio import output as audio_output  # noqa: E402
from brain.audio.engine import SystemBeeper  # noqa: E402
from brain.data import paths  # noqa: E402
from brain.game.keys import KeyInput  # noqa: E402
from brain.speech.manager import SpeechManager  # noqa: E402

ESC, ENTER, UP, DOWN, LEFT, RIGHT = 27, 13, 38, 40, 37, 39
HOME = 36
F1, F2, F3, F4 = 112, 113, 114, 115
END = 35


def typed(text):
    return [ord(c.upper()) for c in text]


SCRIPT = ([F1, DOWN, ESC]                                     # help, one line, back
          + [F2, ENTER, HOME, ENTER] + typed("microsoft da") + [ENTER]      # engine list, all voices, type-ahead, choose
          + [DOWN, RIGHT, RIGHT, ENTER,                       # rate +2, then back to the original
             DOWN, LEFT, DOWN, RIGHT, DOWN, END, ENTER, ESC]  # volume, pitch, output mode (not changed: NVDA would speak), open settings folder
          + [F3, DOWN, LEFT, UP, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT, LEFT]   # volume 0 (silent), pitch variation
          + [DOWN, DOWN, ENTER, ENTER, DOWN, ENTER, END, ENTER, ESC]         # preview list: sound 1, 2, exit beep
          + [DOWN, ENTER, DOWN, ENTER, DOWN, ENTER, DOWN, ENTER]                           # reload, check, folder, export
          + [DOWN, DOWN, ENTER, ENTER, ESC, ESC]                # restore one (sound 1: already original), back, leave the menu
          + [F4, DOWN, ESC]                                    # about
          + [ESC])                                             # leave the main menu

spoken = []
original_send = SpeechManager._send


def recording_send(self, text):
    spoken.append((round(time.monotonic() - START, 2), text))
    return original_send(self, text)


class Typist(KeyInput):
    def getkey(self, speech):
        self.clk()
        if self.code_text == "" and SCRIPT:
            self.post(SCRIPT.pop(0))
        super().getkey(speech)

    def read_key(self):
        if self._posted.empty() and SCRIPT:
            self.post(SCRIPT.pop(0))
        return super().read_key()


opened = []


class SilentOutput(audio_output.PygameOutput):
    def __init__(self, buffer=256):
        super().__init__(buffer)
        self.volume = 0.0               # a real mixer, real timing, no sound


SystemBeeper.beep = lambda self: True
SpeechManager._send = recording_send
app.KeyInput = Typist
app.paths.open_folder = lambda path: opened.append(path) or True
audio_output.PygameOutput = SilentOutput
import brain.audio.engine as engine  # noqa: E402
engine.PygameOutput = SilentOutput
START = time.monotonic()
code = app.main()
print(f"exit code {code}, {time.monotonic() - START:.2f} s, keys left in the script: {len(SCRIPT)}")
for at, text in spoken:
    print(f"  {at:6.2f} s  {text[:150]!r}")
print("folder opened:", opened)
with open(os.path.join(sys.argv[1], "settings.txt"), encoding="utf-8") as saved:
    print("settings.txt after the run:", [l.strip() for l in saved if l.strip() and not l.startswith("#")])
print("exported:", sorted(os.listdir(paths.export_dir())) if os.path.isdir(paths.export_dir()) else "nothing")
