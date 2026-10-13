"""Silent check of the real playback loop on the real mixer (volume 0, fake speech, nothing is heard).
This is inspired by Jim Kitchen's Brain.

Usage (from clone\\, either bitness):  python tools\\playback_selfcheck.py <scratch folder>

For 1, 3 and 9 slots and each panning mode it runs Game.playback for about 3 seconds with the real
clock and the real mixer, presses a key from another thread at a random time, and reports: how long
playback took to return after the key (the clone's promise is 10 ms), whether any slot was still busy
after the main menu's stop, the gap between a sound's end and the next start in the same slot, and the
share of one CPU core the loop used. Report goes to <scratch folder>\\playback_selfcheck.txt.
"""
import collections
import os
import random
import statistics
import struct
import sys
import threading
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from brain.audio.engine import Audio                              # noqa: E402
from brain.audio.library import SoundLibrary, shipped_sounds_dir   # noqa: E402
from brain.data.settings import AudioSettings                     # noqa: E402
from brain.game.flow import Game                                  # noqa: E402
from brain.game.keys import KeyInput                              # noqa: E402
from brain.speech.fake import FakeBackend                         # noqa: E402
from brain.speech.manager import SpeechManager                    # noqa: E402


class NoBeep:
    def beep(self):
        return False


def main(scratch: str) -> int:
    os.makedirs(scratch, exist_ok=True)
    os.environ["BRAIN_DATA_DIR"] = os.path.join(scratch, "userdata")
    lines = [f"Python {sys.version.split()[0]} {struct.calcsize('P') * 8}-bit"]
    lib = SoundLibrary(shipped_sounds_dir(), None)
    audio = Audio(lib, AudioSettings(), beeper=NoBeep())
    if not audio.ok:
        print("no sound device:", audio.error)
        return 1
    audio.output.volume = 0.0
    keys = KeyInput()
    game = Game(SpeechManager(FakeBackend(), None), keys, audio, scratch)
    gaps, latencies, busy_after, cpu_shares, starts = [], [], [], [], collections.Counter()
    ends = {}
    real_play = audio.play

    def recording(slot, pick, freq=None, pan=0):
        now = time.perf_counter()
        if slot in ends:
            gaps.append((now - ends[slot]) * 1000)
        seconds = real_play(slot, pick, freq, pan)
        ends[slot] = now + seconds
        starts[slot] += 1
        return seconds

    audio.play = recording
    rng = random.Random(1)
    for choice in (1, 3, 9):
        for mode in (1, 2, 3, 4):
            ends.clear()
            delay = 2.0 + rng.random()
            pressed = {}

            def press():
                pressed["at"] = time.perf_counter()
                keys.post(65)

            timer = threading.Timer(delay, press)
            cpu0, wall0 = time.process_time(), time.perf_counter()
            timer.start()
            game.playback(choice, mode)
            done = time.perf_counter()
            cpu_shares.append((time.process_time() - cpu0) / (done - wall0))
            latencies.append((done - pressed["at"]) * 1000)
            keys.clk()
            audio.stop_all()
            busy_after.append(sum(audio.busy(s) for s in range(9)))
            timer.join()
    lines.append(f"key to return: mean {statistics.mean(latencies):.1f} ms, max {max(latencies):.1f} ms over {len(latencies)} runs")
    lines.append(f"slots busy after the stop: {sum(busy_after)} (expected 0)")
    lines.append(f"gap sound end to next start: n {len(gaps)}, median {statistics.median(gaps):.1f} ms, "
                 f"min {min(gaps):.1f} ms, max {max(gaps):.1f} ms, 95th percentile {sorted(gaps)[int(len(gaps) * 0.95)]:.1f} ms")
    lines.append(f"cpu share of the loop: mean {statistics.mean(cpu_shares) * 100:.0f} percent, max {max(cpu_shares) * 100:.0f} percent")
    lines.append(f"sounds started per slot: {dict(sorted(starts.items()))}")
    text = "\n".join(lines)
    with open(os.path.join(scratch, "playback_selfcheck.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    audio.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
