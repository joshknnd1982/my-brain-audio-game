"""The program flow: startup speech, main menu, panning menu, playback, exit. This is inspired by Jim Kitchen's Brain.

GAME_SPEC 3. The original did all of this inside Form_Load as one long routine with jumps; here
each part is a method, in the same order and with the same waits. There is no window, sound card
or screen reader code in this module: it talks to a SpeechManager, a KeyInput and an Audio, so
the tests run it with fakes. App code (app.py) wires the real ones.

Keys and waits keep the original's two fields and clear order (GAME_SPEC 8.1, 8.4). One change
for the player, recorded in DECISIONS P5: the playback loop looks at the keys every pass (it
sleeps 1 ms per pass), so a key stops the sounds within a few milliseconds instead of after the
next sound start. A key typed ahead during " Press the space bar to stop. " still lets slot 1
start its first sound before playback stops, as in the original (GAME_SPEC 8.4).
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from ..audio.engine import Audio
from . import extra_texts, texts
from .gamemenu import find_game_menu, launch_game_menu
from .keys import KEY_DOWN, KEY_ENTER, KEY_ESCAPE, KEY_F1, KEY_UP, GameQuit, KeyInput
from .panning import MODE_COUNT, MODE_NONE, PanState
from .rnd import GameRandom
from .slots import SoundSlots

log = logging.getLogger("brain.game")

WAIT_AFTER_CHOICE = 0.2     # dy after a valid digit, and after each Up or Down (GAME_SPEC 7)
WAIT_AFTER_BEEP = 0.1
WAIT_BEFORE_END = 0.2
PASS_SLEEP = 0.001          # playback loop sleep per pass (DECISIONS P4)
MAX_CHOICE = 9
MAX_ERRORS_IN_A_ROW = 5     # last-resort handler: after this many failures without one good round Brain closes
NUMPAD_0, NUMPAD_9 = 96, 105    # owner decision 17: numpad digits count in the main menu


def val(text: str) -> int:
    """VB's Val for the one character the main menu passes it: a digit gives its value, anything else 0."""
    return int(text) if len(text) == 1 and text in "0123456789" else 0


class Game:
    def __init__(self, speech, keys: KeyInput, audio: Audio, program_folder: str,
                 rng: GameRandom | None = None, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 find_menu: Callable[[str], str | None] = find_game_menu,
                 launch_menu: Callable[[str], bool] = launch_game_menu, functions=None, notice_sources=()):
        self.speech = speech
        self.keys = keys
        self.audio = audio
        self.program_folder = program_folder
        self.rng = rng if rng is not None else GameRandom()
        self.clock = clock
        self.sleep = sleep
        self.find_menu = find_menu
        self.launch_menu = launch_menu
        self.functions = functions      # F1 to F4 (game/functions.py); None leaves those keys as invalid keys
        # objects with take_notices(): the sound library always, the settings file too (clone additions)
        self.notice_sources = (audio.library, *notice_sources)
        self.pans = PanState(self.rng)
        self.slots = SoundSlots(audio, audio.library, self.pans, self.rng, clock)

    # ----- speech helpers: the original's say, say2, stopspeech, saykey -----

    def say(self, text: str) -> None:
        """Speak and wait (the original's say). Empty text says nothing, as an empty Speak did."""
        if text:
            self.speech.say(text, self.keys.quit)

    def say_async(self, text: str) -> None:
        if text:
            self.speech.say_async(text)

    def quick_echo(self) -> None:
        """saykey: stop speech, speak the key character async unless the key is F1.

        The original raised the rate by 5 and reset it at once; the clone speaks at the base rate
        (GAME_SPEC 8.3)."""
        self.speech.stop()
        if self.keys.code_text != str(KEY_F1):
            self.say_async(self.keys.char)

    # ----- the program -----

    def run(self) -> None:
        """Startup, then main menu, panning menu and playback until the player exits."""
        self.say(texts.TITLE_SPOKEN)
        if not self.audio.ok:
            self.say(extra_texts.NO_SOUND_DEVICE)
        self.speak_notices(wait=True)
        errors = 0
        while True:
            try:
                choice = self.main_menu()
                if choice is None or not self.panning_menu(choice):
                    break
                errors = 0
            except GameQuit:
                raise
            except Exception:
                # last-resort handler (playbook 7.10): log, say so, back to the main menu; never exit silently
                errors += 1
                log.exception("unexpected error in the program flow (%d in a row)", errors)
                self.recover()
                if errors >= MAX_ERRORS_IN_A_ROW:
                    self.say(extra_texts.GIVING_UP)
                    break
        try:
            self.exit_sequence()
        except GameQuit:
            raise
        except Exception:
            log.exception("unexpected error while leaving the program")

    def recover(self) -> None:
        """After an unexpected error: quiet the sounds and the voice, tell the player, carry on at the main menu."""
        for step in (self.audio.stop_all, self.speech.stop):
            try:
                step()
            except Exception:
                log.exception("could not quiet %s", getattr(step, "__name__", "step"))
        try:
            self.keys.clk()
            self.say_async(extra_texts.FAILED_BACK_TO_MENU)
        except Exception:
            log.exception("could not speak the error message")

    def speak_notices(self, wait: bool = False) -> None:
        """Short warnings the sound library and the settings file collected (damaged file, unusable sound): clone additions."""
        for source in self.notice_sources:
            for notice in source.take_notices():
                if wait:
                    self.say(notice)
                else:
                    self.say_async(notice)

    def run_function(self, key_code: int) -> bool:
        """F1 to F4 in the main or panning menu (DECISIONS P7 S7.4). True when the key was one of them."""
        if self.functions is None or not self.functions.handles(key_code):
            return False
        self.functions.run(key_code)
        self.speak_notices()                    # e.g. the settings file could not be saved
        return True

    def main_menu(self) -> int | None:
        """GAME_SPEC 3.2. Returns the number of sounds (1-9), or None when the player pressed Escape."""
        while True:
            self.audio.stop_all()
            self.say_async(texts.MAIN_PROMPT)
            self.keys.getkey(self.speech)
            if self.keys.code_text == str(KEY_ESCAPE):
                return None
            if self.keys.code_text.isdigit() and self.run_function(int(self.keys.code_text)):
                continue                        # back to the prompt, as after any invalid key
            char = self.main_menu_character()
            self.say(char)
            choice = val(char)
            if 1 <= choice <= MAX_CHOICE:
                return choice

    def main_menu_character(self) -> str:
        """The key's character as the main menu echoes and reads it; numpad digits count as digits."""
        char = self.keys.char
        code = int(self.keys.code_text) if self.keys.code_text.isdigit() else 0
        if char != "" and NUMPAD_0 <= code <= NUMPAD_9:
            return str(code - NUMPAD_0)
        return char

    def panning_menu(self, choice: int) -> bool:
        """GAME_SPEC 3.3. Returns True to go back to the main menu, False when Escape ends the program."""
        keys = self.keys
        keys.clk()
        mode = MODE_NONE
        restart = True
        while True:
            if restart:                         # statement 72: wait, discard keys, start again at mode 1
                keys.dy(WAIT_AFTER_CHOICE)
                keys.clk()
                mode = MODE_NONE
                self.say_async(texts.SELECT)
                restart = False
            self.say_async(texts.MODE_NAMES[mode - 1])
            keys.getkey(self.speech)
            code = keys.code_text
            if code == str(KEY_ESCAPE):
                return False
            if code == str(KEY_ENTER):
                self.playback(choice, mode)
                return True
            if code == str(KEY_UP):
                mode = MODE_COUNT if mode == 1 else mode - 1
                keys.dy(WAIT_AFTER_CHOICE)
            elif code == str(KEY_DOWN):
                mode = 1 if mode == MODE_COUNT else mode + 1
                keys.dy(WAIT_AFTER_CHOICE)
            elif code.isdigit() and self.run_function(int(code)):
                restart = True                  # as after an invalid key, without the echo
            else:
                self.quick_echo()
                restart = True

    def playback(self, choice: int, mode: int) -> None:
        """GAME_SPEC 3.4. Returns when a key was pressed; the main menu then stops all sounds."""
        keys, slots = self.keys, self.slots
        slots.begin_playback()
        self.speak_notices(wait=True)
        keys.clk()
        self.say(texts.PRESS_SPACE)
        self.rng.reseed()                       # Randomize Timer
        passes = 0
        while True:
            keys.pump()                         # statement 123
            if passes and keys.code_text != "":
                return
            self.speak_notices()                # a file that failed to load during this pass (clone addition)
            for slot in range(choice):
                slots.visit(slot, mode)
                if keys.code_text != "":        # checked after the visit: a typed-ahead key still lets slot 1 start
                    return
                keys.pump()                     # end of the slot's turn
                if keys.code_text != "":
                    return
            passes += 1
            self.sleep(PASS_SLEEP)

    def exit_sequence(self) -> None:
        """GAME_SPEC 3.5."""
        self.audio.stop_all()
        menu = self.find_menu(self.program_folder)
        if menu is not None:
            if not self.launch_menu(menu):      # the original's Shell failed silently too
                log.error("the game menu %s did not start", menu)
            return
        self.say(texts.EXITING)
        for _ in range(2):
            self.audio.beep_exit()
            self.keys.dy(WAIT_AFTER_BEEP)
        self.say(texts.NO_GAME_MENU)            # owner decision 17: the original's never reached the ear
        self.keys.dy(WAIT_BEFORE_END)
