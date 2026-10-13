"""Finding and starting the Kitchensinc game menu on exit. This is inspired by Jim Kitchen's Brain.

GAME_SPEC 3.5: the original looked for gamemenu.exe with Dir, compared the name in lower case,
and started it with Shell, window style 3 (maximized, with focus). The clone looks only in
Brain's own folder (one folder for everything, DECISIONS P4 owner choice 17).
"""
from __future__ import annotations

import logging
import os
import subprocess

from .texts import GAME_MENU_EXE

log = logging.getLogger("brain.game")

SW_MAXIMIZE = 3     # Shell's window style 3


def find_game_menu(folder: str) -> str | None:
    """Full path of gamemenu.exe in folder (any letter case), or None."""
    try:
        for name in os.listdir(folder):
            if name.lower() == GAME_MENU_EXE and os.path.isfile(os.path.join(folder, name)):
                return os.path.join(folder, name)
    except OSError:
        pass
    return None


def launch_game_menu(path: str) -> bool:
    """Start the game menu maximized, from its own folder. False if Windows refused (logged)."""
    try:
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = SW_MAXIMIZE
        subprocess.Popen([path], cwd=os.path.dirname(path), startupinfo=info, close_fds=True)
        return True
    except Exception:
        log.exception("could not start %s", path)
        return False
