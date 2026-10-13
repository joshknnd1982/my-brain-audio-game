"""Conformance tests: the clone against the frozen GAME_SPEC 1.0 (P8 S8.1). This is inspired by Jim Kitchen's Brain.

The expected values here are written from the spec's text and tables (section numbers in each test),
not read back from the code: spoken texts (STRINGS.md), the key echo table (8.2), the pitch limits
and cut-off for the 42 shipped sounds (5.3, 5.4), pan loudness (5.5), the timed transcript of a whole
session (3, 7), held keys (8.4, OPEN_QUESTIONS 25) and the shipped sounds against the originals.
"""
import hashlib
import os
import re

import pytest

from brain.audio.library import SoundLibrary, shipped_sounds_dir
from brain.audio.render import MIX_RATE, frames_of, pan_gains
from brain.data.settings import Settings
from brain.game import texts
from brain.game.keys import key_char
from brain.game.slots import SoundSlots
from gamerig import Rig, Scripted, Seeded, StubLibrary, make_pick

ESC, ENTER, UP, DOWN = 27, 13, 38, 40
F1, F2, F3, F4 = 112, 113, 114, 115
KEY_A, KEY_3 = 65, 51

HERE = os.path.dirname(__file__)
SPEC_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "spec"))
ORIGINAL_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "original"))


def library(count=3):
    return StubLibrary({n: make_pick(n, rate=11025, frames=900 + 50 * n) for n in range(1, count + 1)}, pool=count)


def transcript(rig):
    """The speech as the spec describes it: S = spoken and waited for (say), A = queued (say2), stop."""
    out = []
    events = rig.fake.events
    for i, (kind, value) in enumerate(events):
        if kind == "speak":
            waited = i + 1 < len(events) and events[i + 1][0] == "wait"
            out.append(("S:" if waited else "A:") + value)
        elif kind == "stop":
            out.append("stop")
    return out


# ----- spoken texts: STRINGS S01-S20 -----

SPEC_TEXTS = {
    "S01": (texts.CAPTION, "My Brain by Josh Kennedy, inspired by Jim Kitchen"),   # owner's title format, DECISIONS 2026-10-13
    "S04": (texts.TITLE_SPOKEN, "My Brain by Josh Kennedy, inspired by Jim Kitchen."),
    "S05": (texts.MAIN_PROMPT, " Press a number from one to nine, or the escape key to exit. "),
    "S06": (texts.SELECT, " Select. "),
    "S07": (texts.MODE_NAMES[0], "no panning"),
    "S08": (texts.MODE_NAMES[1], "stationary panning"),
    "S09": (texts.MODE_NAMES[2], "semi random panning"),
    "S10": (texts.MODE_NAMES[3], "totally random panning"),
    "S11": (texts.PRESS_SPACE, " Press the space bar to stop. "),
    "S15": (texts.CONTACT, "Please contact Jim Kitchen"),
    "S16": (texts.NO_VOICES, "Sorry but I couldn't find any voices to use"),
    "S17": (texts.GAME_MENU_EXE, "gamemenu.exe"),
    "S18": (texts.EXITING, " exiting program "),
    "S19": (texts.NO_GAME_MENU, "Sorry, but I could not find the Kitchensinc game menu program."),
}


@pytest.mark.parametrize("string_id", sorted(SPEC_TEXTS))
def test_every_original_text_is_exactly_the_specs_text(string_id):
    actual, expected = SPEC_TEXTS[string_id]
    assert actual == expected                       # leading and trailing spaces count (STRINGS.md note)


def test_the_texts_equal_the_rows_of_strings_md():
    path = os.path.join(SPEC_DIR, "STRINGS.md")
    if not os.path.exists(path):
        pytest.skip("the spec folder is not next to the clone")
    rows = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r'^\| (S\d\d) \| "(.*?)"( \(| \|)', line)
            if match:
                rows[match.group(1)] = match.group(2)
    for string_id, (actual, _expected) in SPEC_TEXTS.items():
        assert rows[string_id] == actual, string_id


def test_the_wav_name_is_brain_number_dot_wav_without_padding():
    assert texts.WAV_PREFIX + "7" + texts.WAV_SUFFIX == "brain7.wav"         # Trim(Str(number)): no leading space


# ----- the key echo table (GAME_SPEC 8.2): LCase(Chr(KeyCode)), code page 1252 -----

ECHO_TABLE = {
    33: "!", 34: '"', 39: "'", 40: "(", 45: "-", 46: ".", 91: "[", 93: "]", 96: "`", 123: "{",     # silent on both voices
    35: "#", 36: "$", 37: "%", 38: "&",                                                          # End, Home, Left, Up
    186: "º", 188: "¼", 189: "½", 190: "¾", 192: "à", 219: "û", 220: "ü", 221: "ý",              # voice dependent
    187: "»", 191: "¿", 222: "þ",
    106: "j", 107: "k", 109: "m", 110: "n", 111: "o",                                            # numpad * + - . /
}
ECHO_TABLE.update({96 + n: "abcdefghi"[n - 1] for n in range(1, 10)})                           # numpad 1-9
ECHO_TABLE.update({112 + i: "pqrstuvwxyz"[i] for i in range(11)})                               # F1-F11
ECHO_TABLE.update({code: chr(code).lower() for code in range(65, 91)})                          # letters
ECHO_TABLE.update({code: chr(code) for code in range(48, 58)})                                  # digits


@pytest.mark.parametrize("code", sorted(ECHO_TABLE))
def test_key_character_table_of_spec_8_2(code):
    assert key_char(code) == ECHO_TABLE[code]


def run_keys(answers, lib=None, **kwargs):
    rig = Rig(lib or library(), answers=answers, **kwargs)
    rig.game.run()
    return rig


def test_every_key_the_main_menu_does_not_use_is_echoed_as_its_character_then_the_prompt_repeats():
    """Codes 8..255 one by one through the real main menu (3.2 step 5)."""
    for code in range(8, 256):
        if code == ESC or 49 <= code <= 57 or 96 <= code <= 105:
            continue                                # exit, digits and numpad digits: tested below
        rig = run_keys([code, ESC])
        echo = key_char(code)
        expected = [texts.TITLE_SPOKEN, texts.MAIN_PROMPT]
        if echo:
            expected.append(echo)
        expected += [texts.MAIN_PROMPT, texts.EXITING, texts.NO_GAME_MENU]
        assert rig.spoken == expected, f"key code {code}"


def test_every_digit_key_is_echoed_and_opens_the_panning_menu():
    for code in list(range(49, 58)) + list(range(97, 106)):
        rig = run_keys([code, ESC])
        digit = str(code - 48 if code < 96 else code - 96)
        assert rig.spoken[1:5] == [texts.MAIN_PROMPT, digit, texts.SELECT, "no panning"], f"key code {code}"
        assert rig.spoken[-2:] == [texts.EXITING, texts.NO_GAME_MENU]       # Escape in the panning menu ends the program


def test_zero_is_echoed_and_does_not_open_the_panning_menu():
    for code in (48, 96):
        rig = run_keys([code, ESC])
        assert rig.spoken[1:4] == [texts.MAIN_PROMPT, "0", texts.MAIN_PROMPT]
        assert texts.SELECT not in rig.spoken


def test_every_other_key_in_the_panning_menu_is_echoed_then_the_menu_starts_over():
    """3.3 step 8 and 8.3: the character async (not for F1), then Select and the first mode again."""
    for code in range(8, 256):
        if code in (ESC, ENTER, UP, DOWN):
            continue
        rig = run_keys([49, code, ESC])
        panning = rig.spoken[rig.spoken.index(texts.SELECT):-2]
        echo = key_char(code)
        expected = [texts.SELECT, "no panning"]
        if echo and code != F1:
            expected.append(echo)
        expected += [texts.SELECT, "no panning"]
        assert panning == expected, f"key code {code}"


# ----- a whole session as a timed transcript (3.1 to 3.5, 7) -----

def timed_session(answers, key_in_playback_at=None, **kwargs):
    rig = Rig(library(), answers=answers, rng=Seeded(7), **kwargs)
    stamps = []
    real_speak = rig.fake.speak

    def speak(text):
        stamps.append(round(rig.clock() - 1000.0, 3))
        return real_speak(text)

    rig.fake.speak = speak
    if key_in_playback_at is not None:
        rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == key_in_playback_at else None
    rig.game.run()
    return rig, stamps


def test_golden_session_three_sounds_semi_random_a_key_then_escape():
    rig, stamps = timed_session([KEY_3, DOWN, DOWN, ENTER, ESC], key_in_playback_at=40)
    assert transcript(rig) == [
        "S:" + texts.TITLE_SPOKEN,
        "A:" + texts.MAIN_PROMPT, "stop",                                   # the digit stops the prompt
        "S:3",                                                              # the echo waits
        "A:" + texts.SELECT, "A:no panning", "stop",
        "A:stationary panning", "stop",                                     # Down: no Select again
        "A:semi random panning", "stop",
        "S:" + texts.PRESS_SPACE,                                           # Enter: waits, then the sounds
        "A:" + texts.MAIN_PROMPT, "stop",                                   # a key in playback: main menu
        "S:" + texts.EXITING, "S:" + texts.NO_GAME_MENU,                    # Escape: exit with the two beeps between
    ]
    assert len(rig.beeper.at) == 2
    # the order of the sounds the logic started: the first pass starts slots 1, 2 and 3 in that order (3.4, 5.4)
    assert [slot for slot, _ in rig.output.played][:3] == [0, 1, 2]
    assert {slot for slot, _ in rig.output.played} == {0, 1, 2}             # never a fourth slot
    # timing (7): 0.2 s after the digit before Select, 0.2 s after each Down before the next mode name
    assert stamps[3] - stamps[2] == pytest.approx(0.2, abs=0.003)           # digit echo -> Select
    assert stamps[5] - stamps[4] == pytest.approx(0.2, abs=0.003)           # first Down -> "stationary panning"
    assert stamps[6] - stamps[5] == pytest.approx(0.2, abs=0.003)           # second Down -> "semi random panning"
    # the playback loop runs for the 40 passes the test lets go by, at 1 ms per pass
    assert 0.03 <= stamps[8] - stamps[7] <= 0.08                             # space bar prompt -> main prompt


def test_golden_exit_with_and_without_the_game_menu():
    rig, _ = timed_session([ESC])
    assert transcript(rig) == ["S:" + texts.TITLE_SPOKEN, "A:" + texts.MAIN_PROMPT, "stop",
                               "S:" + texts.EXITING, "S:" + texts.NO_GAME_MENU]
    assert rig.beeper.at[1] - rig.beeper.at[0] == pytest.approx(0.1, abs=0.003)
    rig, _ = timed_session([ESC], menu="C:/games/gamemenu.exe")
    assert transcript(rig) == ["S:" + texts.TITLE_SPOKEN, "A:" + texts.MAIN_PROMPT, "stop"]
    assert rig.launched == ["C:/games/gamemenu.exe"] and rig.beeper.at == []


def test_up_from_the_first_mode_wraps_to_the_fourth_and_down_wraps_back():
    rig, _ = timed_session([KEY_3, UP, DOWN, ESC])
    modes = [t for t in transcript(rig) if t.startswith("A:") and t[2:] in texts.MODE_NAMES]
    assert [m[2:] for m in modes] == [texts.MODE_NAMES[i] for i in (0, 3, 0)]


# ----- held keys (8.4, OPEN_QUESTIONS 25) -----

def test_a_held_enter_during_the_space_bar_prompt_starts_one_sound_then_the_main_menu_waits_quietly():
    rig = Rig(library(), answers=[57, ENTER, ESC], rng=Seeded())
    real_speak = rig.fake.speak

    def speak(text):
        if text == texts.PRESS_SPACE:
            for _ in range(12):                      # the key repeat of a held Enter, typed during the waiting speech
                rig.keys.post(ENTER)
        return real_speak(text)

    rig.fake.speak = speak
    rig.game.run()
    assert [slot for slot, _ in rig.output.played] == [0]                    # slot 1 starts once, slots 2 to 9 never
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2
    assert rig.spoken[-3:] == [texts.MAIN_PROMPT, texts.EXITING, texts.NO_GAME_MENU]   # nothing echoed, nothing queued


def test_key_repeat_that_arrives_before_the_playback_starts_changes_nothing_either():
    rig = Rig(library(), answers=[57, ENTER, ESC], rng=Seeded())
    real_playback = rig.game.playback

    def playback(choice, mode):
        for _ in range(12):
            rig.keys.post(ENTER)
        real_playback(choice, mode)

    rig.game.playback = playback
    rig.game.run()
    assert [slot for slot, _ in rig.output.played] == [0]
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2


# ----- pitch, cut-off, pan on the 42 shipped sounds (5.3, 5.4, 5.5) -----

@pytest.fixture(scope="module")
def shipped():
    lib = SoundLibrary(shipped_sounds_dir(), None)
    assert lib.pool_size() == 42                     # 5.2 and the spec: the wav set has 42 files
    return lib


def test_pitch_limits_of_the_shipped_set(shipped):
    rates = [shipped.pick_number(n).rate for n in range(1, 43)]
    freqs = [rate + r * 100 for rate in rates for r in range(-20, 20) if r != 0]
    assert min(freqs) == 3500 and max(freqs) == 46000                        # 5.3
    assert all(100 <= f <= 200000 for f in freqs)                            # inside DirectSound's limits: SetFrequency never fails
    factors = [(rate + r * 100) / rate for rate in rates for r in range(-20, 20) if r != 0]
    assert round(min(factors), 3) == 0.636 and round(max(factors), 3) == 1.345
    assert 1.0 not in factors                                                # the pitch never stays as recorded
    lengths = [shipped.pick_number(n).sound.frames / (shipped.pick_number(n).rate + r * 100)
               for n in range(1, 43) for r in range(-20, 20) if r != 0]
    assert round(min(lengths) * 1000, 1) == 2.8 and round(max(lengths) * 1000) == 324     # 5.3: 2.8 ms to 324 ms


def test_the_cut_off_never_ends_a_shipped_sound_early(shipped):
    """5.4: endTime(k) - start >= 2.04 times the real length, for every wav at every pitch."""
    worst = 99.0
    for number in range(1, 43):
        for r in range(-20, 20):
            if r == 0:
                continue
            lib = StubLibrary({number: shipped.pick_number(number)}, pool=number)
            # draws: wav number, then the pitch offset (Int(x * 40) - 20 = r), then pan draws for mode 1: none
            rig = Rig(lib, answers=[], rng=Scripted((number - 0.5) / number, (r + 20 + 0.5) / 40))
            rig.game.slots.wav_count = number
            rig.game.slots._start_sound(0, 1)
            played = rig.output.played
            assert len(played) == 1
            real = frames_of(played[0][1]) / MIX_RATE
            lead = rig.game.slots.end_time[0] - rig.clock()
            worst = min(worst, lead / real)
    assert worst >= 2.04 - 0.01                                              # the mixer rounds length to a whole frame


def test_pan_loudness_follows_the_directsound_rule(shipped):
    """5.5: the opposite channel is attenuated by |pan|/100 dB, the near one stays at full level."""
    for pan in (-1000, -750, -300, -150, 150, 300, 750, 990):
        left, right = pan_gains(pan)
        far = 10 ** (-abs(pan) / 2000)
        assert (left, right) == ((far, 1.0) if pan > 0 else (1.0, far))
    assert pan_gains(0) == (1.0, 1.0)
    assert round(20 * __import__("math").log10(pan_gains(750)[0]), 2) == -7.5      # at most 7.5 dB between the ears
    assert round(20 * __import__("math").log10(pan_gains(-1000)[1]), 2) == -10.0   # mode 4: at most 10 dB


def test_every_shipped_wav_is_byte_for_byte_an_original():
    if not os.path.isdir(ORIGINAL_DIR):
        pytest.skip("original folder not present")
    count = 0
    for name in sorted(os.listdir(shipped_sounds_dir())):
        if not name.lower().endswith(".wav"):
            continue
        with open(os.path.join(shipped_sounds_dir(), name), "rb") as handle:
            shipped_hash = hashlib.sha256(handle.read()).hexdigest()
        with open(os.path.join(ORIGINAL_DIR, name), "rb") as handle:
            assert shipped_hash == hashlib.sha256(handle.read()).hexdigest(), name
        count += 1
    assert count == 42


# ----- defaults the spec fixes (3.1, 17) -----

def test_the_defaults_are_the_originals():
    s = Settings.defaults()
    assert s.speech.volume == 90                     # 3.1 step 5
    assert s.speech.voice_id is None and s.speech.rate is None and s.speech.mode == "sapi"   # first SAPI voice, its own rate
    assert s.audio.pitch_spread == 20 and s.audio.effects_volume == 100                        # 5.3: r in -20..19, full volume


def test_the_pan_table_and_mode_four_range_of_5_5():
    rig = Rig(library(), answers=[], rng=Seeded(3))
    assert rig.game.pans.table[1:12] == [-750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750]
    seen = set()
    for _ in range(4000):
        seen.add(rig.game.pans.pan_for(4, 1))
    assert min(seen) >= -1000 and max(seen) <= 990 and all(v % 10 == 0 for v in seen)
    assert len(seen) > 150                           # 200 possible values, all reachable
