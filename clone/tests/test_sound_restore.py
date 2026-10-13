"""Restoring one sound or all sounds to the original (playbook 7.7, 7.10). This is inspired by Jim Kitchen's Brain."""
import os

from brain.audio.restore import BACKUP_SUFFIX, REMOVED_FOLDER, restore_all_sounds, restore_sound
from brain.audio.soundsconfig import DEFAULT_TEXT, FILE_NAME, drop_entry
from brain.game import extra_texts as words
from test_audio_library import make_library
from test_functions import DOWN, END, ENTER, ESC, F3, UP, run
from wavmaker import sine, write


def setup_player(tmp_path, shipped_count=3):
    lib, shipped, player = make_library(tmp_path, shipped_count)
    write(player / "brain2.wav", sine(900, 0.05, 22050), rate=22050)
    write(player / "brain05.ogg", sine(500, 0.05, 22050), rate=22050)      # no sound 5 shipped: an added sound
    write(player / "brain4.wav", sine(400, 0.05, 22050), rate=22050)
    write(player / "My Bell.wav", sine(700, 0.05, 22050), rate=22050)
    (player / FILE_NAME).write_text(DEFAULT_TEXT + "brain3 = file=My Bell.wav; volume=70\nBRAIN2 = volume=90\nbrain7 = off\n",
                                    encoding="utf-8")
    lib.refresh()
    return lib, shipped, player


def test_drop_entry_removes_only_that_sounds_lines_and_keeps_the_notes(tmp_path):
    lib, _, player = setup_player(tmp_path)
    assert drop_entry(str(player), "brain02") is True
    text = (player / FILE_NAME).read_text(encoding="utf-8")
    assert "BRAIN2" not in text and "brain3 = file=My Bell.wav" in text and "brain7 = off" in text
    assert "# Brain sounds, format 1" in text and "# brain5 = file=my best bell.wav; volume=80" in text    # notes stay
    assert drop_entry(str(player), "brain02") is False


def test_restore_one_removes_its_line_and_moves_its_own_named_files_aside(tmp_path):
    lib, _, player = setup_player(tmp_path)
    assert lib.pick_number(2).source == "player"
    result = restore_sound(str(player), "brain2")
    lib.refresh()
    assert result.entry_removed and result.moved == ["brain2.wav"] and not result.failed
    assert lib.pick_number(2).source == "original"
    assert (player / REMOVED_FOLDER / "brain2.wav").is_file() and not (player / "brain2.wav").exists()
    assert (player / "brain4.wav").is_file()                              # other sounds untouched
    assert lib.pick_number(3).source == "player" and lib.pick_number(3).volume == 0.7


def test_restore_one_with_the_file_entry_leaves_the_named_file_where_it_is(tmp_path):
    lib, _, player = setup_player(tmp_path)
    result = restore_sound(str(player), "brain03")
    lib.refresh()
    assert result.entry_removed and result.moved == []
    assert (player / "My Bell.wav").is_file() and lib.pick_number(3).source == "original"


def test_restore_one_handles_padded_and_other_types_and_changes_nothing_when_already_original(tmp_path):
    lib, _, player = setup_player(tmp_path)
    result = restore_sound(str(player), "brain5")
    assert result.moved == ["brain05.ogg"]
    again = restore_sound(str(player), "brain5")
    assert not again.changed and not again.failed


def test_moving_aside_never_overwrites_an_earlier_removed_file(tmp_path):
    lib, _, player = setup_player(tmp_path)
    restore_sound(str(player), "brain2")
    write(player / "brain2.wav", sine(1200, 0.05, 22050), rate=22050)
    restore_sound(str(player), "brain2")
    assert sorted(os.listdir(player / REMOVED_FOLDER)) == ["brain2 (2).wav", "brain2.wav"]


def test_restore_all_rewrites_sounds_txt_keeps_a_backup_and_moves_every_own_named_file(tmp_path):
    lib, _, player = setup_player(tmp_path)
    old = (player / FILE_NAME).read_text(encoding="utf-8")
    result = restore_all_sounds(str(player))
    lib.refresh()
    assert result.entry_removed and sorted(result.moved) == ["brain05.ogg", "brain2.wav", "brain4.wav"]
    assert (player / FILE_NAME).read_text(encoding="utf-8").replace("\r\n", "\n") == DEFAULT_TEXT
    assert (player / (FILE_NAME + BACKUP_SUFFIX)).read_text(encoding="utf-8") == old
    assert (player / "My Bell.wav").is_file()                              # freely named files are left
    assert lib.pool_size() == 3 and all(lib.pick_number(n).source == "original" for n in (1, 2, 3))


def test_restore_all_works_without_a_sounds_txt_or_folder(tmp_path):
    folder = tmp_path / "nothing yet"
    result = restore_all_sounds(str(folder))
    assert result.entry_removed and (folder / FILE_NAME).is_file()


# ----- in the Sounds menu (F3): items 9 and 10 -----

def test_menu_restore_one_puts_the_chosen_sound_back_and_says_where_the_file_went(tmp_path):
    lib, _, player = setup_player(tmp_path)
    # End, Up = item 9; open the list; Down to sound 2; Enter; Escape (list, menu, main menu)
    rig = run([F3, END, UP, ENTER, DOWN, ENTER, ESC, ESC, ESC], lib=lib)
    assert any(words.RESTORE_ONE_ITEM in t for t in rig.spoken)
    assert any(t.startswith("Sound 2 is back to the original. Your file was moved to the removed sounds folder.") for t in rig.spoken)
    assert (player / REMOVED_FOLDER / "brain2.wav").is_file()


def test_menu_restore_all_needs_a_second_enter(tmp_path):
    lib, _, player = setup_player(tmp_path)
    rig = run([F3, END, ENTER, 65, ESC, ESC], lib=lib)                     # last item, Enter, then another key: cancel
    assert words.CONFIRM_RESTORE_ALL in rig.spoken and words.NOTHING_CHANGED in rig.spoken
    assert (player / "brain2.wav").is_file()
    lib, _, player = setup_player(tmp_path / "again")
    rig = run([F3, END, ENTER, ENTER, ESC, ESC], lib=lib)
    assert (player / "brain2.wav").exists() is False and (player / REMOVED_FOLDER / "brain2.wav").is_file()
    assert any(t.startswith("All sounds are back to the original.") and "3 of your sound files were moved" in t for t in rig.spoken)


def test_menu_items_are_the_last_two_and_the_old_ones_keep_their_place(tmp_path):
    lib, _, _ = setup_player(tmp_path)
    rig = run([F3, ESC, ESC], lib=lib)
    assert any("Sounds. 10 items." in t for t in rig.spoken)
