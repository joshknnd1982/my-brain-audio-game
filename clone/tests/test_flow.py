"""Program flow with fake speech, scripted keys and a virtual clock (GAME_SPEC 3, 8.4). This is inspired by Jim Kitchen's Brain."""
import pytest

from brain.game import texts
from brain.game.keys import GameQuit
from gamerig import Rig, Seeded, StubLibrary, make_pick

ESC, ENTER, UP, DOWN, F1 = 27, 13, 38, 40, 112
KEY_A, KEY_X, KEY_3 = 65, 88, 51
NUMPAD5 = 101


def library(count=3):
    return StubLibrary({n: make_pick(n, rate=11025, frames=900 + 50 * n) for n in range(1, count + 1)}, pool=count)


def run(answers, **kwargs):
    rig = Rig(kwargs.pop("lib", None) or library(), answers=answers, **kwargs)
    rig.game.run()
    return rig


def at_exit(rig):
    return rig.spoken[-2:]


# ----- startup and exit -----

def test_startup_speech_then_main_prompt_then_escape_exits_without_a_game_menu():
    rig = run([ESC])
    assert rig.spoken == [texts.TITLE_SPOKEN, texts.MAIN_PROMPT, texts.EXITING, texts.NO_GAME_MENU]


def test_two_exit_beeps_a_tenth_of_a_second_apart_then_the_wait_before_the_end():
    rig = run([ESC])
    assert len(rig.beeper.at) == 2
    assert rig.beeper.at[1] - rig.beeper.at[0] == pytest.approx(0.1, abs=0.003)
    assert rig.clock() - rig.beeper.at[1] == pytest.approx(0.1 + 0.2, abs=0.005)    # 0.1 s after the beep, then 0.2 s


def test_exit_starts_the_game_menu_when_it_is_there_and_says_nothing():
    rig = run([ESC], menu="C:/x/gamemenu.exe")
    assert rig.launched == ["C:/x/gamemenu.exe"]
    assert rig.spoken == [texts.TITLE_SPOKEN, texts.MAIN_PROMPT]
    assert rig.beeper.at == []


def test_escape_typed_during_the_startup_title_exits_from_the_first_prompt():
    rig = Rig(library(), answers=[])
    rig.keys.post(ESC)                                      # typed while the waiting title speaks (GAME_SPEC 8.4)
    rig.game.run()
    assert rig.spoken[:2] == [texts.TITLE_SPOKEN, texts.MAIN_PROMPT]
    assert texts.EXITING in rig.spoken


def test_another_key_typed_during_the_title_gives_an_empty_echo_and_the_prompt_again():
    rig = Rig(library(), answers=[ESC])
    rig.keys.post(KEY_A)
    rig.game.run()
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2        # the typed-ahead key restarted it, nothing was echoed
    assert "a" not in rig.spoken


def test_closing_the_window_ends_the_game_thread():
    rig = Rig(library(), answers=[])
    rig.keys.close()
    with pytest.raises(GameQuit):
        rig.game.run()


# ----- main menu -----

def test_invalid_keys_are_echoed_and_the_prompt_repeats():
    rig = run([KEY_A, 48, ESC])                             # "a", "0"
    assert rig.spoken[1:] == [texts.MAIN_PROMPT, "a", texts.MAIN_PROMPT, "0", texts.MAIN_PROMPT,
                              texts.EXITING, texts.NO_GAME_MENU]


def test_a_digit_is_echoed_and_opens_the_panning_menu():
    rig = run([KEY_3, ESC])
    assert rig.spoken[1:5] == [texts.MAIN_PROMPT, "3", texts.SELECT, "no panning"]
    assert rig.spoken[5:] == [texts.EXITING, texts.NO_GAME_MENU]    # Escape in the panning menu ends the program


def test_numpad_digits_are_accepted_and_echoed_as_digits():
    rig = run([NUMPAD5, ESC])
    assert rig.spoken[2:5] == ["5", texts.SELECT, "no panning"]


def test_every_main_menu_return_stops_the_nine_slots():
    rig = Rig(library(), answers=[ESC])
    rig.audio.output.play(4, bytes(44100 * 4))
    assert rig.audio.busy(4)
    rig.game.run()
    assert not rig.audio.busy(4)


# ----- panning menu -----

def modes_spoken(rig):
    start = rig.spoken.index(texts.SELECT)
    return [s for s in rig.spoken[start:] if s in texts.MODE_NAMES]


def test_down_walks_the_modes_and_wraps_to_the_first():
    rig = run([KEY_3, DOWN, DOWN, DOWN, DOWN, ESC])
    assert modes_spoken(rig) == ["no panning", "stationary panning", "semi random panning",
                                 "totally random panning", "no panning"]


def test_up_wraps_to_the_last_mode_and_walks_back():
    rig = run([KEY_3, UP, UP, ESC])
    assert modes_spoken(rig) == ["no panning", "totally random panning", "semi random panning"]


def test_select_is_spoken_only_at_the_start_of_the_menu():
    rig = run([KEY_3, DOWN, ESC])
    assert rig.spoken.count(texts.SELECT) == 1


def test_another_key_in_the_panning_menu_is_echoed_and_starts_again_at_mode_one():
    rig = run([KEY_3, DOWN, KEY_X, ESC])
    after = rig.spoken[rig.spoken.index("stationary panning"):]
    assert after[:4] == ["stationary panning", "x", texts.SELECT, "no panning"]
    assert ("stop", "") in rig.fake.events                    # the echo stops the announcement first


def test_f1_in_the_panning_menu_is_not_echoed_but_still_restarts():
    rig = run([KEY_3, F1, ESC])
    after = rig.spoken[rig.spoken.index("no panning"):]
    assert after[:3] == ["no panning", texts.SELECT, "no panning"]


def test_a_key_during_the_wait_after_down_is_lost():
    rig = Rig(library(), answers=[KEY_3, DOWN, ESC])
    real_dy = rig.keys.dy

    def dy(seconds):
        if seconds == 0.2 and rig.keys.waits == 2:           # the wait after the Down press
            rig.keys.post(DOWN)                              # a second Down inside the 0.2 s
        real_dy(seconds)

    rig.keys.dy = dy
    rig.game.run()
    assert modes_spoken(rig) == ["no panning", "stationary panning"]    # the second Down was wiped by clk


def test_a_key_typed_during_the_wait_after_the_digit_is_lost():
    rig = Rig(library(), answers=[KEY_3, ESC])
    real_dy = rig.keys.dy

    def dy(seconds):
        if rig.keys.waits == 1:
            rig.keys.post(DOWN)
        real_dy(seconds)

    rig.keys.dy = dy
    rig.game.run()
    assert modes_spoken(rig) == ["no panning"]


def test_escape_in_the_panning_menu_ends_the_program_without_the_main_menu():
    rig = run([KEY_3, ESC])
    assert rig.spoken.count(texts.MAIN_PROMPT) == 1


# ----- playback -----

def play_for(passes, choice_key=KEY_3, mode_keys=(), lib=None, rng=None, then=(ESC, ESC)):
    """Start playback and press a key at the given pass number; then main menu answers."""
    rig = Rig(lib or library(), answers=[choice_key, *mode_keys, ENTER, *then], rng=rng or Seeded())
    rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == passes else None
    rig.game.run()
    return rig


def test_playback_start_says_the_space_bar_prompt_then_plays_and_a_key_returns_to_the_main_menu():
    rig = play_for(60)
    after_enter = rig.spoken[rig.spoken.index("no panning") + 1:]
    assert after_enter[:2] == [texts.PRESS_SPACE, texts.MAIN_PROMPT]
    assert rig.game.rng.reseeds == 1
    assert rig.game.audio.library.refreshes >= 1
    assert len(rig.output.played) >= 3                        # at least the three slots' first sounds


def test_only_the_chosen_number_of_slots_play():
    rig = play_for(30, choice_key=50)                         # "2"
    assert {slot for slot, _ in rig.output.played} == {0, 1}


def test_all_nine_slots_play_with_nine():
    rig = play_for(30, choice_key=57)
    assert {slot for slot, _ in rig.output.played} == set(range(9))


def test_playback_stops_every_sound_within_one_pass_of_a_key_and_starts_nothing_new():
    rig = Rig(library(), answers=[57, ENTER, ESC, ESC], rng=Seeded(7))
    seen = {}

    def hook(n):
        if n == 200:
            seen["before"] = len(rig.output.played)
            seen["pass"] = n
            rig.keys.post(KEY_A)
        if "pass" in seen and n > seen["pass"]:
            seen["after_pass"] = n

    rig.pass_hook = hook
    rig.game.run()
    assert seen["before"] > 9
    assert "after_pass" not in seen                           # the loop ended in the pass that saw the key
    assert len(rig.output.played) == seen["before"]
    assert not any(rig.audio.busy(s) for s in range(9))


def test_slots_restart_as_soon_as_their_sound_ends():
    rig = play_for(300, choice_key=49)                        # "1": one slot, 300 passes of 1 ms
    # sounds last 40-70 ms at their pitch: about 300 ms / 55 ms = 5 or 6 starts, with 1 ms gaps
    assert 4 <= len(rig.output.played) <= 8
    assert {slot for slot, _ in rig.output.played} == {0}


def test_a_slot_never_overlaps_its_own_sound_with_the_shipped_style_files():
    rig = Rig(library(), answers=[57, ENTER, ESC, ESC], rng=Seeded(3))
    real_play = rig.audio.play
    overlaps = []

    def checked(slot, pick, freq=None, pan=0):
        if rig.audio.busy(slot):                              # a new sound while the old one still plays
            overlaps.append(slot)
        return real_play(slot, pick, freq, pan)

    rig.audio.play = checked
    rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == 400 else None
    rig.game.run()
    assert not overlaps and len(rig.output.played) > 30


def test_escape_in_playback_goes_back_to_the_main_menu_and_a_second_escape_exits():
    rig = Rig(library(), answers=[KEY_3, ENTER, ESC], rng=Seeded())
    rig.pass_hook = lambda n: rig.keys.post(ESC) if n == 20 else None
    rig.game.run()
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2
    assert rig.spoken[-2:] == [texts.EXITING, texts.NO_GAME_MENU]


def test_a_key_typed_during_the_space_bar_prompt_lets_slot_one_start_then_stops():
    rig = Rig(library(), answers=[57, ENTER, ESC], rng=Seeded())
    real_speak = rig.fake.speak

    def speak(text):
        if text == texts.PRESS_SPACE:
            rig.keys.post(KEY_A)                              # typed during the waiting speech (GAME_SPEC 8.4)
        return real_speak(text)

    rig.fake.speak = speak
    rig.game.run()
    assert [slot for slot, _ in rig.output.played] == [0]     # slot 1 only, none of slots 2 to 9
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2


def test_modes_reach_the_sound_through_the_pan_table():
    # stationary panning with 3 wavs: divisor 1.1, index = Int(number / 1.1): 0, 1, 2
    rig = play_for(10, choice_key=49, mode_keys=[DOWN], lib=library(3))
    assert rig.game.pans.divisor == pytest.approx(1.1)
    assert modes_spoken(rig)[:2] == ["no panning", "stationary panning"]
    assert len(rig.output.played) >= 1


def test_wav_count_is_read_again_at_every_playback():
    lib = library(3)
    rig = Rig(lib, answers=[KEY_3, ENTER, KEY_3, ENTER, ESC, ESC], rng=Seeded())
    pressed = []

    def hook(n):
        if n % 10 == 0:
            if len(pressed) == 0:
                lib.picks[4] = make_pick(4)
                lib.pool = 4                                   # a player adds brain4 during the first playback
            rig.keys.post(KEY_A)
            pressed.append(n)

    rig.pass_hook = hook
    rig.game.run()
    assert rig.game.slots.wav_count == 4


def test_a_broken_wav_keeps_the_program_running_and_silent_in_its_slot():
    picks = {1: make_pick(1, sound=False, size=600), 2: make_pick(2, rate=11025, frames=900)}
    rig = play_for(200, choice_key=49, lib=StubLibrary(picks, pool=2), rng=Seeded(2))
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2           # playback ended normally on the key


def test_nothing_loads_at_all_and_playback_still_ends_on_a_key():
    rig = play_for(100, choice_key=57, lib=StubLibrary({}, pool=0), rng=Seeded(2))
    assert rig.output.played == []
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2


# ----- the last-resort handler (playbook 7.10) and notices from other sources -----

from brain.game import extra_texts  # noqa: E402


class FailsOnce(StubLibrary):
    """The first sound request raises: an unexpected error deep inside playback."""

    def __init__(self, *args, times=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.times = times

    def pick_number(self, number):
        if self.times > 0:
            self.times -= 1
            raise RuntimeError("the sound layer broke")
        return super().pick_number(number)


def test_an_unexpected_error_is_spoken_and_the_program_returns_to_the_main_menu_and_goes_on(caplog):
    lib = FailsOnce({n: make_pick(n, rate=11025, frames=900) for n in (1, 2, 3)}, pool=3)
    rig = Rig(lib, answers=[49, ENTER, 49, ENTER, ESC], rng=Seeded(2))
    rig.pass_hook = lambda n: rig.keys.post(KEY_A) if n == 30 else None
    rig.game.run()
    assert extra_texts.FAILED_BACK_TO_MENU in rig.spoken
    assert rig.spoken.index(extra_texts.FAILED_BACK_TO_MENU) < len(rig.spoken) - 3
    assert rig.spoken.count(texts.MAIN_PROMPT) >= 2             # the main menu came back
    assert len(rig.output.played) > 0                           # and the second try played sounds
    assert "the sound layer broke" in caplog.text


def test_after_five_errors_in_a_row_it_says_so_and_ends_without_a_traceback():
    lib = FailsOnce({1: make_pick(1)}, pool=1, times=99)
    answers = [49, ENTER, 49, ENTER, 49, ENTER, 49, ENTER, 49, ENTER, 49, ENTER]
    rig = Rig(lib, answers=answers, rng=Seeded(2))
    rig.game.run()
    assert rig.spoken.count(extra_texts.FAILED_BACK_TO_MENU) == 5
    assert extra_texts.GIVING_UP in rig.spoken
    assert rig.spoken[-2:] == [texts.EXITING, texts.NO_GAME_MENU]


def test_an_error_while_leaving_is_logged_and_never_escapes(caplog):
    rig = Rig(library(), answers=[ESC])
    rig.game.find_menu = lambda folder: (_ for _ in ()).throw(RuntimeError("no folder"))
    rig.game.run()
    assert "unexpected error while leaving" in caplog.text


def test_window_closing_still_unwinds_through_the_handler():
    rig = Rig(library(), answers=[])
    rig.keys.quit.set()
    with pytest.raises(GameQuit):
        rig.game.run()


class Notes:
    def __init__(self, *notes):
        self.notes = list(notes)

    def take_notices(self):
        notes, self.notes = self.notes, []
        return notes


def test_notices_from_other_sources_are_spoken_at_the_start_once():
    rig = Rig(library(), answers=[ESC])
    rig.game.notice_sources = (rig.game.audio.library, Notes("settings.txt was damaged and has been reset."))
    rig.game.run()
    assert rig.spoken.count("settings.txt was damaged and has been reset.") == 1
    assert rig.spoken.index("settings.txt was damaged and has been reset.") < rig.spoken.index(texts.MAIN_PROMPT)
