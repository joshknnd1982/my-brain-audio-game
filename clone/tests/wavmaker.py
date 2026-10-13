"""Builds small wav files for the audio tests. This is inspired by Jim Kitchen's Brain."""
import struct

import numpy as np


def wav_bytes(samples, rate=11025, bits=16, channels=1, fmt_tag=1, extensible=False,
              data_size=None, extra_chunk=False, truncate=0):
    """samples: float array in -1..1, shape (frames,) or (frames, channels)."""
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if fmt_tag == 3:
        body = arr.astype("<f4" if bits == 32 else "<f8").tobytes()
    elif bits == 8:
        body = np.clip(np.rint(arr * 128 + 128), 0, 255).astype(np.uint8).tobytes()
    elif bits == 16:
        body = np.clip(np.rint(arr * 32767), -32768, 32767).astype("<i2").tobytes()
    elif bits == 24:
        ints = np.clip(np.rint(arr * (2**23 - 1)), -2**23, 2**23 - 1).astype(np.int32).reshape(-1)
        body = b"".join(struct.pack("<i", int(v))[:3] for v in ints)
    elif bits == 32:
        body = np.clip(np.rint(arr * (2**31 - 1)), -2**31, 2**31 - 1).astype("<i4").tobytes()
    else:
        raise ValueError(bits)
    if truncate:
        body = body[:-truncate]
    block = channels * bits // 8
    if extensible:
        fmt = struct.pack("<HHIIHHHHIH14s", 0xFFFE, channels, rate, rate * block, block, bits,
                          22, bits, 0, fmt_tag, b"\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71")
    else:
        fmt = struct.pack("<HHIIHH", fmt_tag, channels, rate, rate * block, block, bits)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if extra_chunk:
        chunks += b"LIST" + struct.pack("<I", 5) + b"abcde" + b"\x00"   # odd size, padded
    size = len(body) if data_size is None else data_size
    chunks += b"data" + struct.pack("<I", size) + body
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


def sine(freq, seconds, rate, amp=0.5):
    t = np.arange(int(rate * seconds)) / rate
    return amp * np.sin(2 * np.pi * freq * t)


def write(path, *args, **kwargs):
    with open(path, "wb") as handle:
        handle.write(wav_bytes(*args, **kwargs))
    return str(path)
