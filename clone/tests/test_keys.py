"""Key fields and waits (GAME_SPEC 8.1, 8.4). This is inspired by Jim Kitchen's Brain."""
import pytest

from brain.game.keys import GameQuit, KeyInput, key_char
from brain.speech.fake import FakeBackend
from brain.speech.manager import SpeechManager


@pytest.mark.parametrize("code, char", [
    (49, "1"), (57, "9"), (65, "a"), (90, "z"),
    (38, "&"), (36, "$"), (35, "#"), (37, "%"),      # Up, Home, End, Left (GAME_SPEC 8.2)
    (112, "p"), (122, "z"), (123, "{"),               # F1, F11, F12
    (96, "`"), (97, "a"), (105, "i"),                 # numpad 0, 1, 9
    (186, "º"), (188, "¼"), (189, "½"), (190, "¾"),   # code page 1252 punctuation keys
    (192, "à"), (219, "û"), (220, "ü"), (221, "ý"),
    (187, "»"), (191, "¿"), (222, "þ"),
    (13, "\r"), (27, "\x1b"), (32, " "), (16, "\x10"),
    (0x81, "\x81"),                                   # undefined in 1252: same code point
])
def test_key_char_is_lcase_chr_cp1252(code, char):
    assert key_char(code) == char


def test_pump_processes_posted_keys_in_order_last_wins():
    keys = KeyInput()
    keys.post(65)
    keys.post(38)
    assert keys.code_text == ""          # nothing happens until DoEvents
    keys.pump()
    assert (keys.code_text, keys.char) == ("38", "&")


def test_clk_clears_code_then_pumps_then_clears_char():
    # A key waiting in the queue during clk: the code survives, the character is cleared
    # (the typed-ahead case of GAME_SPEC 8.4: Escape still exits, other keys echo nothing).
    keys = KeyInput()
    keys.post(27)
    keys.clk()
    assert (keys.code_text, keys.char) == ("27", "")


def test_keys_during_dy_are_wiped_by_the_next_clk():
    clock = [0.0]
    keys = KeyInput(clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    keys.post(40)                          # Down pressed during the 0.2 s wait
    keys.dy(0.2)
    assert keys.code_text == "40"
    keys.clk()
    assert (keys.code_text, keys.char) == ("", "")
    assert clock[0] > 0.2


def test_dy_waits_more_than_the_time():
    clock = [10.0]
    keys = KeyInput(clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    keys.dy(0.1)
    assert clock[0] > 10.1


def test_getkey_waits_for_a_key_then_stops_speech():
    fake = FakeBackend()
    speech = SpeechManager(fake, None)
    keys = KeyInput(sleep=lambda s: keys.post(13))
    keys.getkey(speech)
    assert keys.code_text == "13"
    assert fake.events[-1] == ("stop", "")


def test_key_typed_during_waiting_speech_is_delivered_after_it():
    fake = FakeBackend(seconds_per_char=0.002)
    speech = SpeechManager(fake, None)
    keys = KeyInput()
    keys.post(49)                    # typed while the title is spoken
    speech.say("a long sentence")    # waiting speech never pumps keys
    assert keys.code_text == ""
    keys.pump()
    assert keys.code_text == "49"


def test_closing_the_window_raises_game_quit_at_the_next_pump():
    keys = KeyInput()
    keys.close()
    with pytest.raises(GameQuit):
        keys.pump()


# ----- read_key and typed_character: the menus of the added functions (DECISIONS P7 S7.4) -----

def test_read_key_returns_every_key_in_the_order_typed_and_fills_the_original_fields():
    from brain.game.keys import typed_character  # noqa: F401  (imported with the rest below)
    keys = KeyInput()
    for code in (40, 40, 13):
        keys.post(code)
    assert [keys.read_key(), keys.read_key(), keys.read_key()] == [40, 40, 13]
    assert (keys.code_text, keys.char) == ("13", "\r")


def test_read_key_skips_shift_ctrl_alt_on_their_own():
    keys = KeyInput()
    for code in (16, 17, 18, 20, 91, 65):
        keys.post(code)
    assert keys.read_key() == 65


def test_read_key_raises_when_the_window_closes():
    keys = KeyInput()
    keys.close()
    with pytest.raises(GameQuit):
        keys.read_key()


@pytest.mark.parametrize("code, char", [(65, "a"), (90, "z"), (48, "0"), (57, "9"), (96, "0"), (105, "9"),
                                        (32, " "), (13, ""), (112, ""), (38, ""), (186, "")])
def test_typed_character_for_type_ahead(code, char):
    from brain.game.keys import typed_character
    assert typed_character(code) == char
