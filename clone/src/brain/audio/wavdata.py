"""Reading sound files into float samples. This is inspired by Jim Kitchen's Brain.

Any rate, depth, channel count (1 or 2) and length is accepted (playbook 7.7); empty, cut-off,
unreadable or very long files raise SoundLoadError so the caller can fall back to the next
choice in the resolution chain. Wav files are parsed here (PCM 8/16/24/32 bit, float,
WAVE_FORMAT_EXTENSIBLE); other wav codecs and ogg, flac and mp3 go through pygame's decoder,
which hands back the mixer's own rate (44,100 Hz), so for those files the pitch step of
GAME_SPEC 5.3 is relative to 44,100 Hz instead of the file's own rate.
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass

import numpy as np

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_SECONDS = 30.0            # "very long" files fall back (7.7); the shipped wavs are at most 250 ms
MAX_RATE = 384_000
DECODER_EXTENSIONS = (".wav", ".ogg", ".flac", ".mp3")   # lookup order for player files


class SoundLoadError(Exception):
    """A sound file cannot be used; the message is a plain reason for the log."""


@dataclass(frozen=True)
class Sampled:
    """Decoded sound: float32 samples in -1..1, shape (frames, channels), channels 1 or 2."""
    data: np.ndarray
    rate: int

    @property
    def frames(self) -> int:
        return int(self.data.shape[0])

    @property
    def channels(self) -> int:
        return int(self.data.shape[1])

    @property
    def seconds(self) -> float:
        return self.frames / self.rate

    def silenced(self) -> "Sampled":
        """Same length and rate, no sound (a sound switched off keeps its place in the pool)."""
        return Sampled(np.zeros_like(self.data), self.rate)


def load_sound_file(path: str) -> Sampled:
    """Decode one file. Raises SoundLoadError, never anything else."""
    try:
        size = os.path.getsize(path)
        if size > MAX_FILE_BYTES:
            raise SoundLoadError(f"file is {size // (1024 * 1024)} MB, over the {MAX_FILE_BYTES // (1024 * 1024)} MB limit")
        ext = os.path.splitext(path)[1].lower()
        if ext == ".wav":
            with open(path, "rb") as handle:
                raw = handle.read()
            try:
                sound = parse_wav(raw)
            except _UnsupportedCodec as codec:
                sound = _decode_with_pygame(path, str(codec))
        elif ext in DECODER_EXTENSIONS:
            sound = _decode_with_pygame(path, ext)
        else:
            raise SoundLoadError(f"file type {ext or '(none)'} is not supported")
        _check_usable(sound)
        return sound
    except SoundLoadError:
        raise
    except Exception as exc:  # decoder bugs must never reach the game
        raise SoundLoadError(f"{type(exc).__name__}: {exc}") from exc


def _check_usable(sound: Sampled) -> None:
    if sound.frames == 0:
        raise SoundLoadError("the file holds no sound")
    if sound.seconds > MAX_SECONDS:
        raise SoundLoadError(f"the sound is {sound.seconds:.0f} s long, over the {MAX_SECONDS:.0f} s limit")


class _UnsupportedCodec(Exception):
    pass


def parse_wav(raw: bytes) -> Sampled:
    """Parse a RIFF wave file. Raises SoundLoadError for damage, _UnsupportedCodec for other codecs."""
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise SoundLoadError("not a RIFF wave file")
    fmt = None
    data = None
    pos = 12
    while pos + 8 <= len(raw):
        chunk_id = raw[pos:pos + 4]
        (chunk_size,) = struct.unpack_from("<I", raw, pos + 4)
        body = pos + 8
        available = len(raw) - body
        if chunk_id == b"data":
            # A stream-style or cut-off header: use what is there.
            data = raw[body:body + min(chunk_size, available)]
            if fmt is not None:
                break
        elif chunk_id == b"fmt ":
            if chunk_size < 16 or available < 16:
                raise SoundLoadError("the format block is cut off")
            fmt = raw[body:body + min(chunk_size, available)]
        pos = body + chunk_size + (chunk_size & 1)
        if chunk_size > available:
            break
    if fmt is None:
        raise SoundLoadError("no format block")
    if data is None:
        raise SoundLoadError("no sound data block")
    tag, channels, rate, _, block_align, bits = struct.unpack_from("<HHIIHH", fmt, 0)
    if tag == 0xFFFE and len(fmt) >= 26:       # WAVE_FORMAT_EXTENSIBLE: the real tag starts the GUID
        (tag,) = struct.unpack_from("<H", fmt, 24)
    if channels not in (1, 2):
        raise SoundLoadError(f"{channels} channels are not supported (1 or 2)")
    if not 1 <= rate <= MAX_RATE:
        raise SoundLoadError(f"sample rate {rate} Hz is not usable")
    if tag == 1 and bits in (8, 16, 24, 32):
        width = bits // 8
    elif tag == 3 and bits in (32, 64):
        width = bits // 8
    else:
        raise _UnsupportedCodec(f"wav format {tag}, {bits} bit")
    frame_bytes = width * channels
    frames = len(data) // frame_bytes
    if frames == 0:
        raise SoundLoadError("the file holds no sound")
    chunk = data[:frames * frame_bytes]
    if tag == 3:
        samples = np.frombuffer(chunk, "<f4" if bits == 32 else "<f8").astype(np.float32)
        samples = np.clip(np.nan_to_num(samples), -1.0, 1.0)
    elif bits == 8:
        samples = (np.frombuffer(chunk, np.uint8).astype(np.float32) - 128.0) / 128.0
    elif bits == 16:
        samples = np.frombuffer(chunk, "<i2").astype(np.float32) / 32768.0
    elif bits == 24:
        b = np.frombuffer(chunk, np.uint8).reshape(-1, 3).astype(np.int32)
        value = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        value = np.where(value >= 1 << 23, value - (1 << 24), value)
        samples = value.astype(np.float32) / float(1 << 23)
    else:
        samples = np.frombuffer(chunk, "<i4").astype(np.float32) / float(1 << 31)
    return Sampled(np.ascontiguousarray(samples.reshape(frames, channels)), int(rate))


def _decode_with_pygame(path: str, what: str) -> Sampled:
    """Use the mixer's decoder (ogg, flac, mp3, other wav codecs). Needs the mixer running."""
    import pygame
    if not pygame.mixer.get_init():
        raise SoundLoadError(f"{what} needs the sound system, which is not running")
    try:
        sound = pygame.mixer.Sound(path)
        pcm = pygame.sndarray.array(sound)
    except pygame.error as exc:
        raise SoundLoadError(f"cannot decode {what}: {exc}") from exc
    rate = pygame.mixer.get_init()[0]
    if pcm.ndim == 1:
        pcm = pcm.reshape(-1, 1)
    samples = pcm.astype(np.float32) / 32768.0
    if samples.shape[1] == 2 and np.array_equal(pcm[:, 0], pcm[:, 1]):
        samples = samples[:, :1]              # a mono file the mixer doubled
    return Sampled(np.ascontiguousarray(samples), int(rate))
