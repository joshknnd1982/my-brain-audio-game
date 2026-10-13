"""The added functions on F1 to F4: help, speech settings, sounds menu, about. This is inspired by Jim Kitchen's Brain.

Everything runs on the test rig: fake speech, scripted keys (typed when a menu waits for one), a
virtual clock, a test sound library. Spoken texts are compared by their meaningful parts.
"""
import os

import pytest

from brain.game import extra_texts as words
from brain.game import texts
from brain.game.keys import GameQuit
from gamerig import Rig, Seeded, StubLibrary, make_pick, make_voices
from test_audio_library import make_library
from wavmaker import write

ESC, ENTER, UP, DOWN, LEFT, RIGHT = 27, 13, 38, 40, 37, 39
HOME, END, PGDN = 36, 35, 34
F1, F2, F3, F4 = 112, 113, 114, 115
KEY_1 = 49


def letters(text):
    return [ord(c.upper()) for c in text]


def stub(count=3):
    return StubLibrary({n: make_pick(n, rate=11025, frames=400) for n in range(1, count + 1)}, pool=count)


def run(answers, lib=None, **kwargs):
    rig = Rig(lib or stub(), answers=answers, functions=True, **kwargs)
    rig.game.run()
    return rig


def events(rig, kind):
    return [value for k, value in rig.fake.events if k == kind]


def has(rig, part):
    return any(part in text for text in rig.spoken)


# ----- the keys and where they work -----

def test_main_menu_keys_f1_to_f4_open_the_functions_and_the_prompt_returns_after_escape():
    rig = run([F4, ESC, ESC])
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2
    assert has(rig, words.ABOUT_LINES[2])
    assert rig.spoken[-2:] == [texts.EXITING, texts.NO_GAME_MENU]


def test_without_functions_the_f_keys_stay_invalid_keys_with_the_original_echo():
    rig = Rig(stub(), answers=[F2, ESC])
    rig.game.run()
    assert "q" in rig.spoken                    # F2 echoes the letter q, as in the original (GAME_SPEC 8.2)


def test_digits_and_arrows_keep_their_meaning_in_the_main_menu_with_functions_on():
    rig = run([KEY_1, ESC])                     # 1 then Escape in the panning menu ends the program
    assert rig.spoken[:2] == [texts.TITLE_SPOKEN, texts.MAIN_PROMPT]
    assert "1" in rig.spoken and texts.SELECT in rig.spoken


def test_panning_menu_function_key_returns_to_the_panning_menu_at_mode_one():
    rig = run([KEY_1, DOWN, F4, ESC, ESC])      # Down to mode 2, About, back, Escape ends
    after = rig.spoken[rig.spoken.index(words.ABOUT_LINES[0]):]
    assert after[after.index(texts.SELECT) + 1] == texts.MODE_NAMES[0]      # restarted at "no panning"
    assert "s" not in rig.spoken                                            # F4 gives no key echo (its character is s)


def test_a_typed_ahead_escape_still_wins_over_the_function_keys():
    rig = Rig(stub(), answers=[F4, ESC, ESC], functions=True)
    rig.keys.post(ESC)                          # typed during the title: still exits at the first prompt
    rig.game.run()
    assert not has(rig, words.ABOUT_LINES[2])   # the typed-ahead Escape won; the functions never ran


# ----- help and about -----

def test_help_reads_every_line_then_up_and_down_read_single_lines():
    rig = run([F1, DOWN, UP, UP, ESC, ESC])
    start = rig.spoken.index(words.HELP_TITLE + ".")
    assert rig.spoken[start + 1:start + 1 + len(words.HELP_LINES)] == list(words.HELP_LINES)
    tail = rig.spoken[start + 1 + len(words.HELP_LINES):]
    assert tail[1:4] == [words.HELP_LINES[1], words.HELP_LINES[0], words.HELP_LINES[2]]    # down, up, up (wraps)


def test_about_names_jim_kitchen_and_says_he_died_in_2015():
    rig = run([F4, ESC, ESC])
    text = " ".join(rig.spoken)
    assert "inspired by Jim Kitchen" in text and "blind from birth" in text and "2015" in text


# ----- speech settings -----

def settings_rig(steps, **kwargs):
    return run([F2] + steps + [ESC, ESC], **kwargs)


def test_settings_menu_opens_on_the_voice_item_and_lists_eight_items():
    rig = settings_rig([])
    assert has(rig, "Speech settings. 8 items.")
    assert has(rig, "Voice:")


def test_rate_changes_by_one_from_the_voice_rate_and_stops_at_the_ends():
    rig = settings_rig([DOWN, RIGHT, RIGHT, LEFT])
    assert events(rig, "rate") == [1, 2, 1]
    assert rig.settings.speech.rate == 1
    rig = settings_rig([DOWN] + [RIGHT] * 12)
    assert rig.settings.speech.rate == 10
    rig = settings_rig([DOWN] + [LEFT] * 12)
    assert rig.settings.speech.rate == -10


def test_enter_restores_a_value_to_its_original():
    rig = settings_rig([DOWN, RIGHT, ENTER])
    assert rig.settings.speech.rate is None and events(rig, "rate") == [1, None]
    assert has(rig, "Speech rate: 0, original.")


def test_speech_volume_steps_of_ten_between_zero_and_a_hundred():
    rig = settings_rig([DOWN, DOWN, RIGHT, RIGHT, LEFT, LEFT, LEFT])
    assert events(rig, "volume") == [100, 100, 90, 80, 70]
    assert has(rig, "Speech volume: 70 percent.") and has(rig, "Speech volume: 100 percent.")
    rig = settings_rig([DOWN, DOWN] + [LEFT] * 12)
    assert rig.settings.speech.volume == 0
    rig = settings_rig([DOWN, DOWN, LEFT, ENTER])
    assert rig.settings.speech.volume == 90


def test_pitch_goes_from_minus_ten_to_ten_and_the_help_says_not_every_voice_supports_it():
    rig = settings_rig([DOWN] * 3 + [RIGHT] * 2 + [LEFT] * 14)
    assert rig.settings.speech.pitch == -10
    assert "Not every voice supports it." in words.SETTINGS_HELP
    assert not has(rig, "Not every voice supports it.")      # not spoken at every arrow key: the item stays short
    assert events(rig, "pitch")[:2] == [1, 2]


def test_speech_output_cycles_and_warns_when_the_screen_reader_is_not_running():
    rig = settings_rig([DOWN] * 4 + [RIGHT, RIGHT, RIGHT, LEFT])
    assert rig.settings.speech.mode == "jaws"
    assert rig.speech.mode == "jaws"
    assert has(rig, "Speech output: NVDA only. NVDA is not running now, so the SAPI 5 voice is used.")
    assert has(rig, "Speech output: JAWS only. JAWS is not running now, so the SAPI 5 voice is used.")
    assert has(rig, "Speech output: automatic. NVDA and JAWS are not running now, so the SAPI 5 voice is used.")
    assert has(rig, "Speech output: SAPI 5 voice only, original.")


def test_output_label_warns_only_about_what_the_mode_needs():
    label = words.output_label
    assert label("auto", False, False, jaws_running=True) == "Speech output: automatic."
    assert label("auto", True, False, jaws_running=False) == "Speech output: automatic."
    assert label("jaws", True, False, jaws_running=True) == "Speech output: JAWS only."
    assert label("nvda", False, False, jaws_running=True).endswith(words.NVDA_NOT_RUNNING)
    assert label("sapi", False, True) == "Speech output: SAPI 5 voice only, original."


def test_restore_the_original_speech_settings_resets_everything_and_the_voice():
    rig = settings_rig([DOWN, RIGHT, DOWN, LEFT, DOWN, RIGHT, DOWN, RIGHT, DOWN, RIGHT, DOWN, ENTER])
    sp = rig.settings.speech
    assert (sp.rate, sp.volume, sp.pitch, sp.mode, sp.voice_id, sp.list_letters) == (None, 90, 0, "sapi", None, "type")
    assert has(rig, words.SPEECH_RESTORED)
    assert events(rig, "voice")[-1] is None


def test_every_change_calls_the_on_change_hook_for_saving():
    rig = settings_rig([DOWN, RIGHT, DOWN, LEFT])
    assert rig.changes == 2


def test_menu_wraps_and_home_end_jump_and_other_keys_repeat_the_item():
    rig = settings_rig([UP, END, HOME, 65])
    labels = [t for t in rig.spoken if t.startswith(("Open the folder with", "Voice:"))]
    assert labels[:2] == [words.SETTINGS_FOLDER_ITEM, words.SETTINGS_FOLDER_ITEM]     # Up wraps to the last item
    assert labels[2].startswith("Voice:") and labels[3] == labels[2]


def test_f1_in_a_menu_speaks_the_help_line():
    rig = settings_rig([F1])
    assert words.SETTINGS_HELP in rig.spoken


# ----- the voice list -----

VOICES = ("Microsoft David Desktop", "Microsoft Zira Desktop", "Microsoft Mark", "Zoltan Voice", "Anna")


def voice_rig(steps, **kwargs):
    """Into the voice choice and straight to the list of all voices (Home on the engine list, Enter)."""
    return settings_rig([ENTER, HOME, ENTER] + steps, voices=make_voices(*VOICES), **kwargs)


def test_choosing_a_voice_sets_it_speaks_a_sample_and_saves_the_token_id():
    rig = voice_rig([DOWN, ENTER])
    assert rig.settings.speech.voice_id == "token-1"
    assert events(rig, "voice") == ["token-1"]
    assert has(rig, "Voice set to Microsoft Zira Desktop. This is how Brain will speak.")


def test_choosing_the_first_voice_keeps_no_saved_voice():
    rig = voice_rig([DOWN, UP, ENTER])
    assert rig.settings.speech.voice_id is None and events(rig, "voice") == [None]


def test_escape_in_the_voice_list_changes_nothing():
    rig = voice_rig([DOWN, ESC])
    assert rig.settings.speech.voice_id is None and events(rig, "voice") == []


def test_voice_list_opens_on_the_current_voice_and_marks_it():
    rig = voice_rig([ESC, ESC])
    assert has(rig, "All voices of all engines. 5 items. Press F1 for help. Microsoft David Desktop, current voice")


def test_voice_list_type_ahead_jumps_to_a_name_and_restarts_after_a_pause():
    rig = voice_rig(letters("zo") + [ESC])
    assert has(rig, "Zoltan Voice")
    rig = voice_rig(letters("zo") + letters("an") + [ESC])                          # "zoan" matches nothing
    assert rig.spoken[-1] != "Anna" and "Anna" not in rig.spoken
    rig = voice_rig(letters("zo") + [("wait", 2.0)] + letters("an") + [ESC])        # a pause starts a new word
    assert "Anna" in rig.spoken
    rig = voice_rig(letters("mic") + [ESC])
    assert has(rig, "Microsoft David Desktop, current voice")                       # first match from the top


def test_voice_list_page_keys_home_and_end():
    names = [f"Voice {n}" for n in range(30)]
    rig = settings_rig([ENTER, HOME, ENTER, PGDN, PGDN, END, HOME, ESC, ESC], voices=make_voices(*names))
    seen = [t for t in rig.spoken if t.startswith("Voice ") and t[6:8].strip(",").isdigit()]
    assert seen == ["Voice 10", "Voice 20", "Voice 29", "Voice 0, current voice"]


def test_empty_voice_list_says_so_and_the_menu_goes_on():
    rig = settings_rig([ENTER], voices=[])
    assert words.NO_VOICES_LISTED in rig.spoken


# ----- sounds menu -----

def sounds_rig(steps, lib=None, **kwargs):
    return run([F3] + steps + [ESC, ESC], lib=lib, **kwargs)


def test_sound_volume_changes_in_tens_and_plays_a_sample_each_time():
    rig = sounds_rig([RIGHT, LEFT, LEFT])
    assert rig.settings.audio.effects_volume == 80
    assert has(rig, "Sound volume: 80 percent.")
    assert len(rig.output.played) == 3 and all(slot == 9 for slot, _ in rig.output.played)


def test_sound_volume_enter_restores_the_original_and_scales_the_samples():
    rig = sounds_rig([LEFT] * 5 + [ENTER])
    assert rig.settings.audio.effects_volume == 100
    quiet, full = rig.output.played[4][1], rig.output.played[5][1]
    assert abs(quiet).max() < abs(full).max()


def test_pitch_variation_steps_of_two_from_zero_to_twenty():
    rig = sounds_rig([DOWN, LEFT, LEFT, ENTER, RIGHT])
    assert rig.settings.audio.pitch_spread == 20
    assert has(rig, "Pitch variation: 18 of 20.") and has(rig, "Pitch variation: 16 of 20.")
    assert rig.changes == 4
    rig = sounds_rig([DOWN] + [LEFT] * 12)
    assert rig.settings.audio.pitch_spread == 0
    assert has(rig, "Pitch variation: none, every sound plays at its own pitch.")


def test_preview_lists_the_sounds_and_plays_one_on_enter_without_speech_overlap():
    rig = sounds_rig([DOWN, DOWN, ENTER, ENTER, DOWN, ENTER, DOWN, DOWN, ENTER, ESC])
    assert has(rig, "Listen to the sounds. 4 items.") and has(rig, "Sound 3") and has(rig, "Exit beep")
    assert len(rig.output.played) == 2 and rig.output.played[0][0] == 9  # sounds 1 and 2 on the tenth channel
    assert len(rig.beeper.at) == 1 + 2      # the preview of the exit beep (Windows default sound) plus the two at exit


def test_preview_marks_player_files_and_switched_off_sounds(tmp_path):
    lib, shipped, player = make_library(tmp_path)
    write(player / "brain2.wav", [0.1] * 50, rate=8000)
    (player / "sounds.txt").write_text("# Brain sounds, format 1\nbrain3 = off\n", encoding="utf-8")
    lib.refresh()
    rig = sounds_rig([DOWN, DOWN, ENTER, DOWN, DOWN, ESC], lib=lib)
    assert has(rig, "Sound 2, your file") and has(rig, "Sound 3, switched off")


def test_reload_says_how_many_sounds_are_found_and_sees_new_files(tmp_path):
    lib, shipped, player = make_library(tmp_path, shipped_count=3)
    rig = Rig(lib, answers=[F3] + [DOWN] * 3 + [ENTER, ESC, ESC], functions=True)
    write(player / "brain4.wav", [0.1] * 30, rate=8000)                  # added while the program runs
    rig.game.run()
    assert has(rig, "4 sounds found.")


def test_check_reports_problems_by_count_and_details_go_to_the_log(tmp_path):
    lib, shipped, player = make_library(tmp_path)
    rig = sounds_rig([DOWN] * 4 + [ENTER], lib=lib)
    assert has(rig, "No problems found in the sound files.")
    lib2, _, player2 = make_library(tmp_path / "b")
    (player2 / "brain2.wav").write_bytes(b"not a wave file")
    lib2.refresh()
    rig = sounds_rig([DOWN] * 4 + [ENTER], lib=lib2)
    assert has(rig, "1 problem found, details are in the log.")


def test_open_folder_asks_the_system_to_open_the_players_sounds_folder(tmp_path):
    lib, shipped, player = make_library(tmp_path)
    rig = sounds_rig([DOWN] * 5 + [ENTER], lib=lib)
    assert rig.opened == [str(player)] and has(rig, words.opening_folder())
    assert os.path.isdir(player)


def test_save_generated_sounds_writes_the_exit_blip_as_a_wav(tmp_path):
    export = tmp_path / "exported"
    rig = sounds_rig([DOWN] * 6 + [ENTER], export_dir=str(export))
    assert (export / "beep_exit.wav").stat().st_size > 1000
    assert has(rig, "1 generated sound saved as wav files")


def test_save_generated_sounds_reports_a_folder_that_cannot_be_made(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    rig = sounds_rig([DOWN] * 6 + [ENTER], export_dir=str(blocker / "sub"))
    assert words.EXPORT_FAILED in rig.spoken


def test_restore_the_original_sound_settings():
    rig = sounds_rig([LEFT, DOWN, LEFT] + [DOWN] * 6 + [ENTER])
    assert (rig.settings.audio.effects_volume, rig.settings.audio.pitch_spread) == (100, 20)
    assert words.SOUNDS_RESTORED in rig.spoken


# ----- the pitch variation reaches the playback -----

def test_pitch_variation_zero_plays_every_sound_at_its_own_rate():
    rig = Rig(stub(1), answers=[F3, DOWN] + [LEFT] * 10 + [ESC, KEY_1, ENTER, ESC], functions=True)
    rig.pass_hook = lambda n: n == 6 and rig.keys.post(ESC)
    rig.game.run()
    assert rig.settings.audio.pitch_spread == 0
    assert rig.game.slots.freq == 11025                 # no r * 100 Hz was added


# ----- notices -----

def test_a_damaged_sounds_file_is_announced_at_startup_after_the_attribution(tmp_path):
    lib, shipped, player = make_library(tmp_path)
    (player / "sounds.txt").write_bytes(b"\x00\x01\x02\x03" * 30)
    lib.refresh()
    rig = run([ESC], lib=lib)
    notice = "sounds.txt was damaged and has been reset to the original settings. A copy was saved."
    assert rig.spoken[:3] == [texts.TITLE_SPOKEN, notice, texts.MAIN_PROMPT]


def test_no_sound_device_is_announced_once_at_startup():
    rig = Rig(stub(), answers=[ESC], functions=True)
    rig.audio.error = "no device"
    rig.game.run()
    assert rig.spoken[:2] == [texts.TITLE_SPOKEN, words.NO_SOUND_DEVICE]


def test_a_sound_that_fails_during_playback_is_announced_then_playback_goes_on(tmp_path):
    lib, shipped, player = make_library(tmp_path, shipped_count=1)
    (player / "brain1.wav").write_bytes(b"RIFFjunk")
    rig = Rig(lib, answers=[KEY_1, ENTER, ESC], functions=True, rng=Seeded(1))
    rig.pass_hook = lambda n: n == 4 and rig.keys.post(ESC)
    rig.game.run()
    assert "A sound file could not be used and was skipped, details are in the log." in rig.spoken


# ----- robustness -----

def test_closing_the_window_inside_a_menu_ends_the_game_thread_cleanly():
    rig = Rig(stub(), answers=[F2], functions=True)
    rig.keys.close()
    with pytest.raises(GameQuit):
        rig.game.run()


def test_an_error_inside_a_function_is_spoken_and_the_program_goes_on(monkeypatch):
    def boom(self):
        raise RuntimeError("test")

    monkeypatch.setattr("brain.game.functions.Functions.settings_menu", boom)
    rig = run([F2, ESC])
    assert words.FAILED in rig.spoken
    assert rig.spoken.count(texts.MAIN_PROMPT) == 2 and rig.spoken[-1] == texts.NO_GAME_MENU


# ----- saving (S7.5) -----

def test_menu_changes_are_saved_to_settings_txt_and_come_back(tmp_path):
    from brain.data.settingsfile import SettingsStore
    store = SettingsStore(str(tmp_path / "Brain"))
    store.load()
    rig = Rig(stub(), answers=[F2, DOWN, DOWN, LEFT, LEFT, ESC, F3, RIGHT, LEFT, LEFT, ESC, ESC], functions=True)
    rig.settings.speech = store.settings.speech          # the rig's Functions works on the store's settings
    rig.settings.audio = store.settings.audio
    rig.functions.settings = store.settings
    rig.functions.on_change = store.save
    rig.game.run()
    again = SettingsStore(str(tmp_path / "Brain")).load()
    assert again.speech.volume == 70 and again.audio.effects_volume == 80


def test_a_failed_save_is_said_once_after_the_menu_and_the_menu_goes_on(tmp_path):
    from brain.data.settingsfile import UNWRITABLE_NOTICE, SettingsStore
    blocker = tmp_path / "Brain"
    blocker.write_text("in the way")
    store = SettingsStore(str(blocker))
    store.load()                       # the first failure is noted here, once per run, and spoken at the start
    rig = Rig(stub(), answers=[F2, DOWN, DOWN, LEFT, LEFT, ESC, F3, RIGHT, LEFT, ESC, ESC], functions=True)
    rig.functions.settings = store.settings
    rig.functions.on_change = store.save
    rig.game.notice_sources = (rig.game.audio.library, store)
    rig.game.run()
    assert rig.spoken.count(UNWRITABLE_NOTICE) == 1                      # not again after each change
    assert rig.spoken.index(UNWRITABLE_NOTICE) < rig.spoken.index(texts.MAIN_PROMPT)
    assert store.settings.speech.volume == 70


def test_settings_menu_has_an_item_that_opens_the_folder_with_settings_txt(tmp_path):
    rig = Rig(stub(), answers=[F2, END, ENTER, ESC, ESC], functions=True)
    rig.functions.settings_dir = str(tmp_path)
    rig.game.run()
    assert rig.opened == [str(tmp_path)] and words.SETTINGS_FOLDER_OPENING in rig.spoken


# ----- F3 last item: sounds start right away (latency) -----

def waited_after_press_space(rig):
    spoken = [i for i, (kind, text) in enumerate(rig.fake.events) if kind == "speak" and texts.PRESS_SPACE in text]
    assert spoken, "the playback prompt was never spoken"
    after = rig.fake.events[spoken[0] + 1:spoken[0] + 2]
    return after == [("wait", "")]


def test_sounds_wait_for_the_spoken_prompt_unless_the_player_chooses_right_away():
    rig = Rig(stub(1), answers=[KEY_1, ENTER, ESC], functions=True, rng=Seeded(1))
    rig.pass_hook = lambda n: n == 6 and rig.keys.post(ESC)
    rig.game.run()
    assert waited_after_press_space(rig)                       # original: say waits for the prompt
    rig = Rig(stub(1), answers=[F3, END, RIGHT, ESC, KEY_1, ENTER, ESC], functions=True, rng=Seeded(1))
    rig.pass_hook = lambda n: n == 6 and rig.keys.post(ESC)
    rig.game.run()
    assert rig.settings.audio.start_early is True
    assert has(rig, "Sounds start: right away, while the prompt is spoken.")
    assert not waited_after_press_space(rig)                   # the prompt is queued, the first sound starts at once


def test_sounds_start_item_is_restored_by_enter_and_by_restore_the_original_sound_settings():
    rig = Rig(stub(1), answers=[F3, END, RIGHT, ENTER, ESC, ESC], functions=True)
    rig.game.run()
    assert rig.settings.audio.start_early is False and has(rig, "Sounds start: after the spoken prompt, original.")
    rig = Rig(stub(1), answers=[F3, END, RIGHT, HOME, DOWN, DOWN, DOWN, DOWN, DOWN, DOWN, DOWN, ENTER, ESC, ESC], functions=True)
    rig.game.run()
    assert rig.settings.audio.start_early is False
