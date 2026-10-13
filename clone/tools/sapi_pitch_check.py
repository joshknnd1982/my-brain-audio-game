"""Which SAPI 5 voices honor the pitch markup? Silent check (playbook 7.4). Inspired by Jim Kitchen's Brain.

Renders one sentence to memory (nothing is played) at pitch -10, 0 and +10 with
<pitch absmiddle="n"> for each chosen voice, estimates the median voice frequency of each
rendering by autocorrelation, and prints one line per voice. A voice honors pitch when -10 is
clearly lower and +10 clearly higher than 0.

Usage: python sapi_pitch_check.py [voice name part ...]   (default: voice 0, David, Zira)
"""
import sys

import numpy as np
import pythoncom
import win32com.client

SAFT22kHz16BitMono = 22
RATE = 22050
TEXT = "My Brain, by Jim Kitchen. Press a number from one to nine."


def render(voice, text):
    stream = win32com.client.Dispatch("SAPI.SpMemoryStream")
    stream.Format.Type = SAFT22kHz16BitMono
    voice.AudioOutputStream = stream
    voice.Speak(text, 8 if text.startswith("<") else 0)
    return np.frombuffer(bytes(stream.GetData()), "<i2").astype(np.float32)


def median_f0(samples):
    """Median fundamental frequency (Hz) over voiced 40 ms frames, 60-400 Hz."""
    frame, hop = int(0.04 * RATE), int(0.01 * RATE)
    loud = np.percentile(np.abs(samples), 90) * 0.3
    found = []
    for start in range(0, len(samples) - frame, hop):
        x = samples[start:start + frame]
        if np.abs(x).mean() < loud * 0.3:
            continue
        x = x - x.mean()
        ac = np.correlate(x, x, "full")[frame - 1:]
        lo, hi = RATE // 400, RATE // 60
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.4 * ac[0]:
            found.append(RATE / lag)
    return float(np.median(found)) if found else float("nan")


def main():
    pythoncom.CoInitialize()
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    tokens = voice.GetVoices("", "")
    wanted = sys.argv[1:] or ["#0", "David", "Zira"]
    picks = []
    for want in wanted:
        if want == "#0":
            picks.append(tokens.Item(0))
            continue
        for i in range(tokens.Count):
            if want.lower() in tokens.Item(i).GetDescription().lower():
                picks.append(tokens.Item(i))
                break
    for token in picks:
        voice.Voice = token
        f0 = {}
        for pitch in (-10, 0, 10):
            text = TEXT if pitch == 0 else f'<pitch absmiddle="{pitch}">{TEXT}</pitch>'
            f0[pitch] = median_f0(render(voice, text))
        honors = f0[-10] < f0[0] * 0.93 and f0[10] > f0[0] * 1.07
        print(f"{token.GetDescription()}: pitch -10 {f0[-10]:.0f} Hz, 0 {f0[0]:.0f} Hz, "
              f"+10 {f0[10]:.0f} Hz -> {'honors pitch' if honors else 'ignores pitch'}")


if __name__ == "__main__":
    main()
