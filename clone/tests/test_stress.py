"""Stress tests (P8 S8.3): thousands of random keys, failing speech and sound, closing the window in every state.
This is inspired by Jim Kitchen's Brain.

Everything runs the whole program (Game with the F1 to F4 functions) on the test rig. The last-resort
handler of flow.py would hide a crash behind a spoken message, so these tests fail on any logged
error ("unexpected error in the program flow", "function key N failed"), not only on an exception.
Nothing touches the player's real folders: the sound library lives in tmp_path.
"""
import logging
import random
import threading
import time

import pytest

from brain.audio.engine import Audio
from brain.audio.library import SoundLibrary, shipped_sounds_dir
from brain.audio.output import TimedOutput
from brain.data.settings import Settings
from brain.game import extra_texts as words
from brain.game import texts
from brain.game.flow import Game
from brain.game.functions import Functions
from brain.game.keys import GameQuit, KeyInput
from brain.speech.fake import FakeBackend
from brain.speech.manager import SpeechManager
from gamerig import Rig, Seeded, make_voices
from test_audio_library import make_library

ESC, ENTER, UP, DOWN, LEFT, RIGHT = 27, 13, 38, 40, 37, 39
F1, F2, F3, F4 = 112, 113, 114, 115
HOME, END, PGUP, PGDN = 36, 35, 33, 34

KEY_CHOICES = (
    [49 + i for i in range(9)] * 4 + [ENTER] * 6 + [UP, DOWN] * 4 + [F1, F2, F3, F4] * 3 + [LEFT, RIGHT] * 3
    + [HOME, END, PGUP, PGDN] + list(range(65, 91)) + [16, 17, 18, 32, 8, 9, 20, 91, 144, 0xBA, 0xDB, 96, 105, 106, 123]
)


class KeyStream:
    """An endless source of random key codes. After the budget only Escape comes, so every menu closes."""

    def __init__(self, seed, budget):
        self.random = random.Random(seed)
        self.budget = budget
        self.used = 0

    def next(self):
        self.used += 1
        if self.used > self.budget:
            return ESC
        if self.random.random() < 0.05:
            return ESC
        return self.random.choice(KEY_CHOICES)

    # the rig's ScriptedKeys asks its answer list like a list
    def __bool__(self):
        return True

    def pop(self, index=0):
        return self.next()


def errors_logged(caplog):
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


def build(tmp_path, stream, seed=1, shipped=12, voices=30):
    lib, _, _ = make_library(tmp_path, shipped_count=shipped)
    rig = Rig(lib, answers=[], rng=Seeded(seed), functions=True, voices=make_voices(*[f"Voice {i}" for i in range(voices)]),
              export_dir=str(tmp_path / "export"))
    rig.keys.answers = stream                       # the rig copies a list; the stream is asked like one
    rig.pass_hook = lambda n: rig.keys.post(stream.next()) if n % 25 == 0 else None     # a key now and then during playback
    return rig


def play_episodes(tmp_path, stream, seed, wrap=lambda rig: None, limit=400):
    """Start the program again after every exit until the key budget is used up. Returns the rigs."""
    rigs = []
    while stream.used <= stream.budget and len(rigs) < limit:
        rig = build(tmp_path, stream, seed=seed + len(rigs))
        wrap(rig)
        rigs.append(rig)
        rig.game.run()
    return rigs


# ----- thousands of random keys through the whole program -----

@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_random_keys_through_every_menu_never_hit_an_error(tmp_path, caplog, seed):
    caplog.set_level(logging.INFO)
    stream = KeyStream(seed, budget=2500)
    rigs = play_episodes(tmp_path, stream, seed)
    assert stream.used > 2500                       # the whole budget went through the program
    assert not errors_logged(caplog), [r.getMessage() for r in errors_logged(caplog)][:3]
    for rig in rigs:
        assert rig.spoken[0] == texts.TITLE_SPOKEN and rig.spoken[-1] == texts.NO_GAME_MENU    # each run ended through the exit sequence
    # the keys really reached every part of the program
    said = " ".join(text for rig in rigs for text in rig.spoken)
    for part in (words.HELP_TITLE, words.ABOUT_TITLE, words.SETTINGS_TITLE, words.SOUNDS_TITLE, words.ENGINE_TITLE,
                 texts.PRESS_SPACE, texts.MODE_NAMES[3], texts.SELECT):
        assert part.strip(" .") in said, part
    assert sum(len(rig.output.played) for rig in rigs) > 200
    assert not any(words.FAILED_BACK_TO_MENU in rig.spoken or words.GIVING_UP in rig.spoken for rig in rigs)


# ----- speech failing in every way, at random -----

def flaky(backend, rng, chance):
    """Every call can raise like a dying COM object; speak can also refuse (return False)."""
    for name in ("speak", "stop", "wait_until_done", "set_rate", "set_volume", "set_pitch", "set_voice", "is_available"):
        real = getattr(backend, name)

        def wrapper(*args, _real=real, _name=name, **kwargs):
            if rng.random() < chance:
                raise RuntimeError(f"{_name}: the engine failed")
            if _name == "speak" and rng.random() < chance:
                return False
            return _real(*args, **kwargs)

        setattr(backend, name, wrapper)


def sound_failing(rig, rng, chance):
    """The mixer raising at random from every call."""
    output = rig.output
    for name in ("play", "busy", "stop", "stop_all"):
        real = getattr(output, name)

        def wrapper(*args, _real=real, _name=name, **kwargs):
            if rng.random() < chance:
                raise OSError(f"{_name}: the device went away")
            return _real(*args, **kwargs)

        setattr(output, name, wrapper)


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_sapi_and_nvda_failing_at_random_never_reach_the_game(tmp_path, caplog, seed):
    caplog.set_level(logging.WARNING)
    rng = random.Random(seed)
    stream = KeyStream(seed, budget=1200)

    def wrap(rig):
        flaky(rig.fake, rng, 0.04)                  # SAPI 5 raising and refusing
        nvda = FakeBackend(name="nvda")
        flaky(nvda, rng, 0.2)                       # NVDA coming and going, failing more often
        rig.speech.nvda = nvda
        rig.speech._mode = rng.choice(["sapi", "nvda", "jaws", "auto"])

    play_episodes(tmp_path, stream, seed, wrap)
    assert stream.used > 1200
    bad = [r for r in errors_logged(caplog) if r.name.startswith("brain.game")]
    assert not bad, [r.getMessage() for r in bad][:3]


@pytest.mark.parametrize("seed", [21, 22])
def test_the_sound_device_failing_at_random_never_reaches_the_game(tmp_path, caplog, seed):
    caplog.set_level(logging.WARNING)
    rng = random.Random(seed)
    stream = KeyStream(seed, budget=1000)
    play_episodes(tmp_path, stream, seed, lambda rig: sound_failing(rig, rng, 0.03))
    assert stream.used > 1000
    bad = [r for r in errors_logged(caplog) if r.name.startswith("brain.game")]
    assert not bad, [r.getMessage() for r in bad][:3]


def test_no_sound_device_at_all_the_game_says_so_and_plays_on(tmp_path):
    lib, _, _ = make_library(tmp_path, shipped_count=5)
    rig = Rig(lib, answers=[51, DOWN, ENTER, ESC], rng=Seeded(5))
    rig.audio.error = "no device"                   # as Audio sets it when the mixer cannot start
    rig.pass_hook = lambda n: rig.keys.post(65) if n == 200 else None
    rig.game.run()
    assert "No sound device was found, so Brain will run without sound." in rig.spoken
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2 and rig.spoken[-1] == texts.NO_GAME_MENU
    assert len(rig.output.played) > 3                # the logic ran its loop with the silent output


def test_no_speech_engine_at_all_the_whole_session_runs_silently(tmp_path):
    lib, _, _ = make_library(tmp_path, shipped_count=5)
    rig = Rig(lib, answers=[51, DOWN, ENTER, F4, ESC, ESC], rng=Seeded(5), functions=True)
    rig.speech.sapi = None
    rig.speech.nvda = None
    rig.pass_hook = lambda n: rig.keys.post(65) if n == 100 else None
    rig.game.run()
    assert rig.output.played and rig.fake.spoken() == []


# ----- the window closed in every state -----

CLOSE_SCRIPT = ([49 + 2, DOWN, UP, 65, ENTER]                                   # sounds in panning mode 4 ... playback
                + [F1, DOWN, ESC] + [F4, ESC]                                   # help and about
                + [F2, ENTER, DOWN, ENTER, RIGHT, LEFT, DOWN, RIGHT, ENTER, ESC, ESC]    # speech settings, voice list
                + [F3, DOWN, RIGHT, ENTER, DOWN, DOWN, ENTER, ENTER, ESC, ESC]            # sounds menu
                + [49 + 6, ENTER] + [ESC] * 12)


def close_at(tmp_path, step, caplog):
    lib, _, _ = make_library(tmp_path / f"c{step}", shipped_count=6)
    rig = Rig(lib, answers=list(CLOSE_SCRIPT), rng=Seeded(step), functions=True,
              voices=make_voices("Voice a", "Voice b", "Voice c"), export_dir=str(tmp_path / f"c{step}" / "export"))
    rig.pass_hook = lambda n: rig.keys.post(65) if n % 30 == 0 else None
    count = [0]
    real_pump, real_read = rig.keys.pump, rig.keys.read_key

    def tick():
        count[0] += 1
        if count[0] == step:
            rig.keys.close()                        # the window's close handler

    def pump():
        tick()
        real_pump()

    def read_key():
        tick()
        return real_read()

    rig.keys.pump, rig.keys.read_key = pump, read_key
    try:
        rig.game.run()
    except GameQuit:
        return True, rig
    return False, rig


def test_closing_the_window_at_any_point_ends_the_game_cleanly(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    steps = range(1, 4000)                          # every key pump and menu key of the whole script, one by one
    closed = 0
    states = set()
    for step in steps:
        quit_, rig = close_at(tmp_path, step, caplog)
        closed += quit_
        states.add(rig.spoken[-1] if rig.spoken else "")
        if not quit_:
            break                                   # the close point is past the end of the whole session
    assert closed > 1000                            # the sweep really closed it in many different states
    assert len(states) >= 15                        # ... and the last thing said differed in at least 15 of them
    assert not errors_logged(caplog), [r.getMessage() for r in errors_logged(caplog)][:3]


def test_closing_the_window_during_long_speech_ends_the_game_thread_quickly(tmp_path):
    rig = Rig(make_library(tmp_path)[0], answers=[], speech_per_char=0.5)       # about 14 s of title
    ended = []

    def game():
        try:
            rig.game.run()
        except GameQuit:
            ended.append("quit")

    thread = threading.Thread(target=game, daemon=True)
    thread.start()
    time.sleep(0.2)
    start = time.monotonic()
    rig.keys.close()
    thread.join(5)
    assert ended == ["quit"] and time.monotonic() - start < 1.5


# ----- real threads: a second thread typing thousands of keys while the real game runs -----

def test_three_thousand_keys_from_another_thread_into_the_real_clock_game(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    lib, _, _ = make_library(tmp_path, shipped_count=12)
    keys = KeyInput()
    fake = FakeBackend()
    speech = SpeechManager(fake, None)
    settings = Settings.defaults()
    audio = Audio(lib, settings.audio, output=TimedOutput(), beeper=type("B", (), {"beep": lambda self: True})())
    catalog = type("C", (), {"loaded": True, "voices": lambda self, timeout=None: make_voices("A", "B", "C")})()
    functions = Functions(speech, keys, audio, settings, catalog, str(tmp_path / "export"), lambda p: True)
    failures = []
    stop_feeding = threading.Event()
    runner_done = threading.Event()
    rng = random.Random(99)

    def feeder():
        for _ in range(3000):
            keys.post(rng.choice([c for c in KEY_CHOICES if c != ESC]) if rng.random() > 0.01 else ESC)
            time.sleep(rng.choice([0, 0.0005, 0.001, 0.002]))
        stop_feeding.set()
        # Escape keeps coming until the program has ended: the game throws away keys typed ahead at several
        # points (the original's clk, GAME_SPEC 8.4), so a short burst can fall inside such a window (P9 flake, 1 in 10).
        give_up = time.monotonic() + 100
        while not runner_done.is_set() and time.monotonic() < give_up:
            keys.post(ESC)
            time.sleep(0.01)

    def runner():
        try:
            while True:
                Game(speech, keys, audio, str(tmp_path), find_menu=lambda f: None, launch_menu=lambda p: True,
                     functions=functions).run()
                if stop_feeding.is_set():
                    break
        except BaseException as exc:                # noqa: B902 (the test wants to see anything)
            failures.append(exc)
        finally:
            runner_done.set()

    threads = [threading.Thread(target=feeder), threading.Thread(target=runner)]
    for t in threads:
        t.daemon = True
        t.start()
    for t in threads:
        t.join(120)
    assert not any(t.is_alive() for t in threads), "the game or the typist hung"
    assert not failures, failures
    assert not errors_logged(caplog), [r.getMessage() for r in errors_logged(caplog)][:3]
    assert fake.spoken().count(texts.TITLE_SPOKEN) >= 1


# ----- thousands of voices at program level -----

def test_five_thousand_voices_choose_the_last_and_one_by_typing(tmp_path):
    voices = make_voices(*[f"Voice {i}" for i in range(5000)])
    lib, _, _ = make_library(tmp_path, shipped_count=3)
    start = time.perf_counter()
    rig = Rig(lib, answers=[F2, ENTER, HOME, ENTER, END, ENTER, ESC, ESC], functions=True, voices=voices)
    rig.game.run()
    assert rig.settings.speech.voice_id == "token-4999"
    letters = [ord(c.upper()) if c.isalpha() else ord(c) for c in "voice 4321"]
    rig = Rig(lib, answers=[F2, ENTER, HOME, ENTER] + letters + [ENTER, ESC, ESC], functions=True, voices=voices)
    rig.game.run()
    assert rig.settings.speech.voice_id == "token-4321"
    assert time.perf_counter() - start < 10


# ----- a long run on the shipped sounds (virtual clock) -----

def test_twenty_virtual_seconds_on_nine_slots_with_the_real_sounds(tmp_path):
    lib = SoundLibrary(shipped_sounds_dir(), None)
    rig = Rig(lib, answers=[57, DOWN, DOWN, ENTER, ESC], rng=Seeded(31))
    overlaps = []
    real_play = rig.audio.play

    def play(slot, pick, freq=None, pan=0):
        if rig.output.busy(slot):                   # a slot cut off its own sound: the spec says this never happens
            overlaps.append((slot, pick.sound_id))
        return real_play(slot, pick, freq, pan)

    rig.audio.play = play
    pressed = []

    def key_after_twenty_seconds(_pass):
        if rig.clock() - 1000.0 > 20 and not pressed:
            pressed.append(1)
            rig.keys.post(65)

    rig.pass_hook = key_after_twenty_seconds
    rig.game.run()
    plays = rig.output.played
    assert not overlaps
    assert {slot for slot, _ in plays} == set(range(9))
    assert len(plays) > 1500                        # nine slots of 3 ms to 324 ms sounds over 20 s
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2
