"""The game window: no controls, only a caption, and every key goes to the game. This is inspired by Jim Kitchen's Brain.

The frame has no child controls, so it keeps the keyboard focus itself and gets WM_KEYDOWN and
WM_SYSKEYDOWN for every key, like the original's Form1 (GAME_SPEC 8.1). wx's raw key code on
Windows is the virtual-key code VB's Form_KeyDown received. Keys are not passed on, so no
default handler acts on them, with two exceptions:
- Alt+F4 is passed on, so Windows still closes the window.
- Releasing Alt or F10 is swallowed, so Windows does not enter system-menu mode and later arrow
  keys still reach the game (DECISIONS P5: Alt and F10 are plain keys).
(S7.1 test: wx's char hook event fires only for the focused window, so key-down is used; it can
be tested by posting key messages to a hidden window without taking the keyboard.)
"""
from __future__ import annotations

import wx

from ..game.texts import CAPTION

VK_MENU = 18   # Alt
VK_F4 = 115
VK_F10 = 121


class BrainWindow(wx.Frame):
    def __init__(self, on_key, on_close):
        super().__init__(None, title=CAPTION, size=(420, 160))
        self._on_key = on_key
        self._on_close = on_close
        self.Bind(wx.EVT_KEY_DOWN, self._key_down)
        self.Bind(wx.EVT_KEY_UP, self._key_up)
        self.Bind(wx.EVT_CLOSE, self._close)

    def _key_down(self, event: wx.KeyEvent) -> None:
        code = event.GetRawKeyCode()
        if code == VK_F4 and event.AltDown():
            event.Skip()  # let Windows turn Alt+F4 into a close; the game does not see it (F4 is About)
            return
        self._on_key(code)

    def _key_up(self, event: wx.KeyEvent) -> None:
        if event.GetRawKeyCode() not in (VK_MENU, VK_F10):
            event.Skip()

    def _close(self, event: wx.CloseEvent) -> None:
        self._on_close()
        self.Destroy()
