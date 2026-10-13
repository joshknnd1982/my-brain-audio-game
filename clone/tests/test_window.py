"""The window turns key presses into VB KeyDown codes (hidden window, no focus taken). This is inspired by Jim Kitchen's Brain.

Key messages are posted straight to the hidden window while wx's main loop runs, so the test
never steals the keyboard from the player.
"""
import pytest

wx = pytest.importorskip("wx")
win32api = pytest.importorskip("win32api")
win32con = pytest.importorskip("win32con")

from brain.game.texts import CAPTION  # noqa: E402
from brain.ui.window import BrainWindow  # noqa: E402

KEYS = [27, 13, 9, 32, 38, 40, 37, 39, 49, 65, 112, 113, 114, 115, 121, 16, 17, 186, 96, 8, 46]


@pytest.mark.window
def test_posted_key_messages_arrive_as_virtual_key_codes():
    app = wx.App(False)
    got, closed = [], []
    frame = BrainWindow(got.append, lambda: closed.append(1))
    assert frame.GetTitle() == CAPTION
    hwnd = frame.GetHandle()

    def post():
        for vk in KEYS:
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
        win32api.PostMessage(hwnd, win32con.WM_SYSKEYDOWN, 18, 0x20000000)  # Alt alone
        wx.CallLater(300, frame.Close)

    wx.CallLater(50, post)
    wx.CallLater(5000, lambda: frame and frame.Destroy())  # safety stop
    app.MainLoop()
    assert got == KEYS + [18]
    assert closed == [1]
