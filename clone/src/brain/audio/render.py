"""Pitch and pan rendering. This is inspired by Jim Kitchen's Brain.

The original set DirectSound's buffer frequency and pan (GAME_SPEC 5.3, 5.5). Here a sound is
resampled (linear interpolation, as a software mixer does) to the length it has when its buffer
plays at the new frequency, mixed at a fixed 44,100 Hz, and pan becomes left and right gains.
"""
from __future__ import annotations

import numpy as np

from .wavdata import Sampled

MIX_RATE = 44_100
MIN_FREQ = 100            # DirectSound's documented SetFrequency limits (GAME_SPEC 5.3);
MAX_FREQ = 200_000        # outside them the original's call failed and the pitch stayed unchanged
MAX_PAN = 10_000


def pan_gains(pan: int) -> tuple[float, float]:
    """DirectSound pan (hundredths of a dB, negative = left): only the far channel is attenuated
    by |pan|/100 dB (DECISIONS P5)."""
    p = max(-MAX_PAN, min(MAX_PAN, int(pan)))
    far = 10.0 ** (-abs(p) / 2000.0)
    return (far, 1.0) if p > 0 else (1.0, far)


def usable_frequency(freq: int) -> bool:
    return MIN_FREQ <= freq <= MAX_FREQ


def output_frames(frames: int, freq: int) -> int:
    """Mixer frames the sound takes when its buffer plays at freq."""
    return max(1, int(round(frames * MIX_RATE / freq)))


def resample(sound: Sampled, freq: int) -> np.ndarray:
    """float32 (m, channels) at MIX_RATE, as if the buffer ran at freq."""
    n = sound.frames
    m = output_frames(n, freq)
    pos = np.minimum(np.arange(m, dtype=np.float64) * (freq / MIX_RATE), n - 1)
    x = np.arange(n, dtype=np.float64)
    out = np.empty((m, sound.channels), np.float32)
    for c in range(sound.channels):
        out[:, c] = np.interp(pos, x, sound.data[:, c])
    return out


def render_stereo(sound: Sampled, freq: int, pan: int, volume: float) -> np.ndarray:
    """int16 (m, 2) ready for the mixer. volume is a linear gain (1.0 = the file unchanged)."""
    pitched = resample(sound, freq)
    left_gain, right_gain = pan_gains(pan)
    if pitched.shape[1] == 1:
        left = right = pitched[:, 0]
    else:
        left, right = pitched[:, 0], pitched[:, 1]
    pcm = np.empty((pitched.shape[0], 2), np.int16)
    scale = 32767.0 * max(0.0, volume)
    pcm[:, 0] = np.clip(np.rint(left * (left_gain * scale)), -32768, 32767)
    pcm[:, 1] = np.clip(np.rint(right * (right_gain * scale)), -32768, 32767)
    return pcm
