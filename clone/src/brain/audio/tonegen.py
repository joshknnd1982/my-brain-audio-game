"""Generated sounds. This is inspired by Jim Kitchen's Brain.

Brain needs almost none (SOUND_DESIGN.md: every silent event stays silent). The one generated
sound is the fallback for the exit beep when the system's default sound cannot be played.
A sound is a list of segments held as data (playbook 7.8); synthesis is deterministic.
"""
from __future__ import annotations

import wave
from dataclasses import dataclass

import numpy as np

from .render import MIX_RATE
from .wavdata import Sampled


@dataclass(frozen=True)
class Segment:
    wave: str            # "square", "triangle", "sine" or "noise" (seeded)
    start_hz: float
    end_hz: float        # a sweep when different from start_hz
    ms: float
    volume: float        # 0..1; 0 makes a rest
    attack_ms: float = 2.0
    release_ms: float = 2.0   # short edges so nothing clicks


# GENERATED sounds by sound ID. beep_exit: fallback only, 880 Hz square, 80 ms (SOUND_DESIGN.md).
GENERATED_SOUNDS: dict[str, tuple[Segment, ...]] = {
    "beep_exit": (Segment("square", 880.0, 880.0, 80.0, 0.35),),
}


def synthesize(segments: tuple[Segment, ...], rate: int = MIX_RATE, seed: int = 1) -> Sampled:
    rng = np.random.default_rng(seed)
    parts = []
    phase = 0.0
    for seg in segments:
        n = max(1, int(round(rate * seg.ms / 1000.0)))
        freq = np.linspace(seg.start_hz, seg.end_hz, n)
        ph = phase + np.cumsum(freq / rate)
        phase = float(ph[-1] % 1.0)
        frac = ph % 1.0
        if seg.wave == "square":
            wav = np.where(frac < 0.5, 1.0, -1.0)
        elif seg.wave == "triangle":
            wav = 4.0 * np.abs(frac - 0.5) - 1.0
        elif seg.wave == "sine":
            wav = np.sin(2.0 * np.pi * ph)
        elif seg.wave == "noise":
            wav = rng.uniform(-1.0, 1.0, n)
        else:
            raise ValueError(f"unknown waveform {seg.wave!r}")
        env = np.ones(n)
        a = min(n // 2, int(rate * seg.attack_ms / 1000.0))
        r = min(n // 2, int(rate * seg.release_ms / 1000.0))
        if a:
            env[:a] = np.linspace(0.0, 1.0, a, endpoint=False)
        if r:
            env[n - r:] = np.linspace(1.0, 0.0, r)
        parts.append(wav * env * seg.volume)
    data = np.concatenate(parts).astype(np.float32) if parts else np.zeros(1, np.float32)
    return Sampled(np.ascontiguousarray(data.reshape(-1, 1)), rate)


def generated(sound_id: str) -> Sampled | None:
    segments = GENERATED_SOUNDS.get(sound_id)
    return synthesize(segments) if segments else None


def write_wav(path: str, sound: Sampled) -> None:
    """16-bit wav, for exporting generated sounds (Sounds menu, S7.7)."""
    pcm = np.clip(np.rint(sound.data * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as out:
        out.setnchannels(sound.channels)
        out.setsampwidth(2)
        out.setframerate(sound.rate)
        out.writeframes(pcm.tobytes())
