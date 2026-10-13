"""Silent audio checks on the real mixer and device (volume 0, nothing is heard).
This is inspired by Jim Kitchen's Brain.

Usage (from clone\\, either bitness):  python tools\\audio_selfcheck.py <scratch folder>

Measures: render time for every shipped wav at every pitch offset; how long the mixer reports each
sound busy compared with its computed length (nine slots at once, at both pitch extremes and one
mid offset); a 6-second nine-slot restart loop (gap between a sound ending and the next starting).
Writes a report to <scratch folder>\\audio_selfcheck.txt and prints the summary.
"""
import os
import random
import statistics
import struct
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from brain.audio.engine import Audio                     # noqa: E402
from brain.audio.library import SoundLibrary, shipped_sounds_dir   # noqa: E402
from brain.audio.render import render_stereo, usable_frequency      # noqa: E402
from brain.data.settings import AudioSettings            # noqa: E402


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
    audio.output.volume = 0.0                              # real device, no sound
    import pygame
    lines.append(f"mixer {pygame.mixer.get_init()}, buffer {audio.output.buffer} frames, pool {lib.pool_size()}")

    # 1. render time
    times = []
    for number in range(1, 43):
        pick = lib.pick_number(number)
        for r in range(-20, 20):
            if r == 0 or not usable_frequency(pick.rate + r * 100):
                continue
            t = time.perf_counter()
            render_stereo(pick.sound, pick.rate + r * 100, 0, 1.0)
            times.append((time.perf_counter() - t) * 1000)
    lines.append(f"render {len(times)} sound-pitch pairs: mean {statistics.mean(times):.3f} ms, max {max(times):.3f} ms")

    # 2. busy time vs computed length, nine at once
    lags = []
    for offset_kind, offset in (("low -2000", -2000), ("high +1900", 1900), ("mid +300", 300)):
        for first in range(1, 43, 9):
            picks = [lib.pick_number(n) for n in range(first, min(first + 9, 43))]
            expected = []
            start = time.perf_counter()
            for slot, pick in enumerate(picks):
                expected.append(audio.play(slot, pick, max(100, pick.rate + offset), 0))
            ended = [None] * len(picks)
            while any(e is None for e in ended) and time.perf_counter() - start < 2.0:
                now = time.perf_counter() - start
                for slot in range(len(picks)):
                    if ended[slot] is None and not audio.busy(slot):
                        ended[slot] = now
                time.sleep(0.0005)
            for slot, pick in enumerate(picks):
                if ended[slot] is not None:
                    lags.append((ended[slot] - expected[slot]) * 1000)
    lines.append(f"end-of-sound lag, nine slots at once, {len(lags)} sounds: min {min(lags):+.1f} ms, "
                 f"median {statistics.median(lags):+.1f} ms, max {max(lags):+.1f} ms (negative = reported early)")

    # 3. single slot, long sound, repeated
    single = []
    pick = lib.pick_number(36)
    for _ in range(10):
        exp = audio.play(0, pick, pick.rate - 2000, 0)
        t = time.perf_counter()
        while audio.busy(0):
            time.sleep(0.0005)
        single.append((time.perf_counter() - t - exp) * 1000)
    lines.append(f"brain36 at 3,564 Hz alone, 10 runs: lag min {min(single):+.1f}, median {statistics.median(single):+.1f}, "
                 f"max {max(single):+.1f} ms")

    # 4. restart loop
    rng = random.Random(3)
    last_end = [None] * 9
    gaps = []
    starts = 0
    end = time.perf_counter() + 6.0
    while time.perf_counter() < end:
        for slot in range(9):
            if not audio.busy(slot):
                now = time.perf_counter()
                if last_end[slot] is not None:
                    gaps.append((now - last_end[slot]) * 1000)
                pick = lib.pick_number(rng.randint(1, 42))
                freq = pick.rate + rng.choice([r for r in range(-20, 20) if r]) * 100
                last_end[slot] = now + audio.play(slot, pick, freq, rng.randint(-100, 99) * 10)
                starts += 1
        time.sleep(0.001)
    lines.append(f"nine-slot loop, 6 s: {starts} sounds started; start minus computed end: min {min(gaps):+.1f} ms, "
                 f"median {statistics.median(gaps):+.1f} ms, 95th percentile {sorted(gaps)[int(len(gaps) * .95)]:+.1f} ms, "
                 f"max {max(gaps):+.1f} ms")
    audio.close()
    report = "\n".join(lines)
    with open(os.path.join(scratch, "audio_selfcheck.txt"), "w", encoding="utf-8") as handle:
        handle.write(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", "."), "brain_audio_check")))
