"""Finding and starting gamemenu.exe (GAME_SPEC 3.5). This is inspired by Jim Kitchen's Brain."""
import subprocess

from brain.game import gamemenu


def test_find_game_menu_any_letter_case(tmp_path):
    assert gamemenu.find_game_menu(str(tmp_path)) is None
    (tmp_path / "GameMenu.EXE").write_bytes(b"x")
    found = gamemenu.find_game_menu(str(tmp_path))
    assert found is not None and found.lower().endswith("gamemenu.exe")


def test_a_folder_named_gamemenu_exe_does_not_count(tmp_path):
    (tmp_path / "gamemenu.exe").mkdir()
    assert gamemenu.find_game_menu(str(tmp_path)) is None


def test_missing_folder_is_none():
    assert gamemenu.find_game_menu("Z:/does/not/exist") is None


def test_launch_starts_it_maximized_from_its_own_folder(tmp_path, monkeypatch):
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    path = str(tmp_path / "gamemenu.exe")
    assert gamemenu.launch_game_menu(path) is True
    args, kwargs = calls[0]
    assert args == [path] and kwargs["cwd"] == str(tmp_path)
    assert kwargs["startupinfo"].wShowWindow == 3
    assert kwargs["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW


def test_launch_failure_is_reported_not_raised(tmp_path):
    assert gamemenu.launch_game_menu(str(tmp_path / "nothing.exe")) is False
