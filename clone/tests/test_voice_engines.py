"""The voice choice by engine, first-letter navigation, and the settings that go with them. This is inspired by Jim Kitchen's Brain."""
import pytest

from brain.data import settingsfile
from brain.data.settings import Settings
from brain.game import extra_texts as words
from brain.speech.voices import (ENGINE_FALLBACK, VoiceInfo, engine_of, enumerate_voices, first_letter_index,
                                 group_by_engine)
from gamerig import Rig, StubLibrary, make_pick

ESC, ENTER, UP, DOWN, LEFT, RIGHT = 27, 13, 38, 40, 37, 39
HOME, END, PGDN = 36, 35, 34
F1, F2 = 112, 113


def letters(text):
    return [ord(c.upper()) for c in text]


ENGINES = {"Bestspeech": ["Fred", "Alfred", "Wilma"], "DoubleTalk": ["Perfect Paul", "Beautiful Betty"],
           "Microsoft": ["Microsoft David Desktop", "Microsoft Mark", "Microsoft Zira Desktop"]}


def engine_voices():
    voices = []
    for engine, names in ENGINES.items():
        for name in names:
            voices.append(VoiceInfo(len(voices), f"token-{len(voices)}", name, engine))
    return voices


def run(answers, voices=None, **kwargs):
    lib = StubLibrary({1: make_pick(1, rate=11025, frames=400)}, pool=1)
    rig = Rig(lib, answers=answers, functions=True, voices=voices if voices is not None else engine_voices(), **kwargs)
    rig.game.run()
    return rig


def settings_run(steps, **kwargs):
    return run([F2] + steps + [ESC, ESC], **kwargs)


def has(rig, part):
    return any(part in text for text in rig.spoken)


def events(rig, kind):
    return [value for k, value in rig.fake.events if k == kind]


# ----- the engine list -----

def test_the_engine_list_starts_with_all_voices_then_the_engines_alphabetically_with_counts():
    rig = settings_run([ENTER, DOWN, DOWN, DOWN, DOWN, ESC])
    assert has(rig, "Choose a speech engine. 4 items. Press F1 for help. Bestspeech, 3 voices")   # opens on the current voice's engine
    said = rig.spoken
    assert "DoubleTalk, 2 voices" in said and "Microsoft, 3 voices" in said
    assert "All voices of all engines, 8 voices" in said


def test_an_engine_lists_only_its_own_voices():
    rig = settings_run([ENTER, DOWN, ENTER, DOWN, END, ESC, ESC, ESC])                 # Bestspeech, DoubleTalk, its voices
    assert has(rig, "Voices of DoubleTalk. 2 items.")
    assert "Perfect Paul, current voice" not in rig.spoken
    assert "Beautiful Betty" in rig.spoken
    assert "Microsoft Mark" not in rig.spoken and "Fred" not in rig.spoken


def test_escape_in_an_engine_goes_back_to_the_engine_list_on_the_same_engine():
    rig = settings_run([ENTER, DOWN, ENTER, ESC, ESC, ESC])
    assert rig.spoken.count("Choose a speech engine. 4 items. Press F1 for help. Bestspeech, 3 voices, ") == 0
    assert rig.spoken.count("Choose a speech engine. 4 items. Press F1 for help. Bestspeech, 3 voices") == 1
    assert "DoubleTalk, 2 voices" in rig.spoken                    # the list came back at the engine just left
    assert rig.settings.speech.voice_id is None


def test_choosing_a_voice_in_an_engine_sets_and_saves_it():
    rig = settings_run([ENTER, DOWN, ENTER, DOWN, ENTER])
    assert rig.settings.speech.voice_id == "token-4"
    assert events(rig, "voice") == ["token-4"]
    assert has(rig, "Voice set to Beautiful Betty.")


def test_all_voices_shows_every_voice_of_every_engine():
    rig = settings_run([ENTER, HOME, ENTER, PGDN, ESC, ESC, ESC])
    assert has(rig, "All voices of all engines. 8 items.")
    assert "Microsoft Zira Desktop" in rig.spoken                  # the last of eight, reached by Page Down (ten, clamped)


def test_the_first_voice_of_all_voices_keeps_no_saved_voice():
    rig = settings_run([ENTER, HOME, ENTER, DOWN, UP, ENTER])
    assert rig.settings.speech.voice_id is None and events(rig, "voice") == [None]


def test_the_engine_list_has_type_ahead_too():
    rig = settings_run([ENTER] + letters("micro") + [ESC, ESC])
    assert has(rig, "Microsoft, 3 voices")


def test_voices_without_an_engine_go_under_other_voices():
    plain = [VoiceInfo(0, "t0", "One"), VoiceInfo(1, "t1", "Two")]
    rig = settings_run([ENTER, ESC, ESC], voices=plain)
    assert has(rig, f"{ENGINE_FALLBACK}, 2 voices")


# ----- first-letter navigation -----

def test_the_setting_toggles_and_is_saved_and_restored():
    rig = settings_run([DOWN] * 5 + [RIGHT])
    assert rig.settings.speech.list_letters == "first"
    assert has(rig, "Letter keys in lists: a letter jumps to the next name with that first letter.")
    rig = settings_run([DOWN] * 5 + [RIGHT, LEFT])
    assert rig.settings.speech.list_letters == "type"
    assert has(rig, "Letter keys in lists: type letters to search for a name, original.")
    rig = settings_run([DOWN] * 5 + [RIGHT, ENTER])                  # Enter on the item restores the original
    assert rig.settings.speech.list_letters == "type"
    assert rig.changes == 2


def first_letter_rig(steps):
    # letters on, then the voice choice: Home (all voices), Enter, then the steps
    return settings_run([DOWN] * 5 + [RIGHT] + [UP] * 5 + [ENTER, HOME, ENTER] + steps + [ESC, ESC, ESC])


def test_a_letter_jumps_to_the_next_name_that_starts_with_it_and_wraps():
    rig = first_letter_rig(letters("m"))
    assert "Microsoft David Desktop" in rig.spoken                      # the first M after Fred
    rig = first_letter_rig(letters("mm"))
    assert rig.spoken.count("Microsoft Mark") == 1                     # the same letter again: the next M
    rig = first_letter_rig(letters("mmmm"))
    assert rig.spoken.count("Microsoft David Desktop") == 2            # three M names, the fourth press wraps to the first
    rig = first_letter_rig(letters("w"))
    assert "Wilma" in rig.spoken
    rig = first_letter_rig(letters("f"))                                # "Fred" is the current item: the next F is Fred again (wrap)
    assert rig.spoken.count("Fred, current voice") == 1               # said again by the jump (the opening line is longer)


def test_a_letter_with_no_name_keeps_the_place_and_repeats_it():
    rig = first_letter_rig(letters("q"))
    assert rig.spoken.count("Fred, current voice") == 1               # no jump, the item is said again


def test_first_letter_mode_also_works_in_the_engine_list():
    rig = settings_run([DOWN] * 5 + [RIGHT] + [UP] * 5 + [ENTER] + letters("m") + [ESC, ESC])
    assert "Microsoft, 3 voices" in rig.spoken


def test_in_type_mode_letters_still_search_by_what_is_typed():
    rig = settings_run([ENTER, HOME, ENTER] + letters("mic") + [ESC, ESC, ESC])
    assert "Microsoft David Desktop" in rig.spoken


def test_the_list_help_describes_the_letter_mode_in_use():
    assert "jumps to the next name that starts with it" in words.list_help("first")
    assert "Typing letters jumps to a name that begins with them" in words.list_help("type")


# ----- the pieces -----

def test_first_letter_index_pure():
    names = ["Anna", "Bob", "Beth", "Zed", "bella"]
    assert first_letter_index(names, "b", 0) == 1
    assert first_letter_index(names, "b", 1) == 2
    assert first_letter_index(names, "b", 4) == 1            # wraps; case does not matter
    assert first_letter_index(names, "a", 0) == 0            # only Anna: back to itself
    assert first_letter_index(names, "x", 0) is None
    assert first_letter_index(["(Zed)", "Yes"], "z", 1) == 0     # punctuation before the first letter is skipped


def test_engine_of_the_registry_path_or_the_vendor():
    class Token:
        def __init__(self, vendor=None):
            self.vendor = vendor

        def GetAttribute(self, name):
            if self.vendor is None:
                raise OSError("no attribute")
            return self.vendor

    enum_id = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\TokenEnums\\Bestspeech\\Fred"
    token_id = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\FlexVoice2_Bill"
    assert engine_of(Token("ignored"), enum_id) == "Bestspeech"
    assert engine_of(Token("Mindmaker"), token_id) == "Mindmaker"
    assert engine_of(Token(), token_id) == ENGINE_FALLBACK
    assert engine_of(Token(), "plain-id") == ENGINE_FALLBACK


def test_enumerate_voices_fills_in_the_engine():
    class Token:
        def __init__(self, i, token_id, vendor):
            self.Id, self._v = token_id, vendor

        def GetDescription(self):
            return "Voice " + self.Id[-1]

        def GetAttribute(self, name):
            return self._v

    class Tokens:
        Count = 2

        def Item(self, i):
            return [Token(0, "HKEY\\Speech\\Voices\\TokenEnums\\Orpheus\\1", ""),
                    Token(1, "HKEY\\Speech\\Voices\\Tokens\\2", "Acme")][i]

    voices, broken = enumerate_voices(lambda: Tokens())
    assert [v.engine for v in voices] == ["Orpheus", "Acme"] and broken == 0


def test_group_by_engine_sorts_engines_and_keeps_voice_order():
    groups = group_by_engine(engine_voices())
    assert [e for e, _ in groups] == ["Bestspeech", "DoubleTalk", "Microsoft"]
    assert [v.name for v in groups[0][1]] == ["Fred", "Alfred", "Wilma"]


# ----- the settings file -----

def test_list_letters_is_saved_in_the_settings_file_and_read_back():
    settings = Settings.defaults()
    settings.speech.list_letters = "first"
    text = settingsfile.render(settings)
    assert "list_letters = first" in text
    back, problems = settingsfile.parse(text)
    assert back.speech.list_letters == "first" and not problems


def test_a_bad_list_letters_value_is_skipped_and_stays_original():
    back, problems = settingsfile.parse("# Brain settings, format 1\nlist_letters = sideways\nspeech_volume = 50\n")
    assert back.speech.list_letters == "type" and back.speech.volume == 50
    assert any("list_letters" in p for p in problems)
