"""The clone's added functions: help, speech settings, sounds menu, about (F1 to F4). This is inspired by Jim Kitchen's Brain.

DECISIONS P7 S7.4 and GAME_SPEC 17: the original's keys keep their meaning in every state; the new
functions sit on F1 to F4, which in the original only gave an invalid-key echo in the main and
panning menus. The menus change the live Settings and tell the speech and audio layers; saving
them is S7.5 (the on_change hook). Nothing here touches the game logic's state.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Callable

from ..audio.library import sound_id
from ..audio.restore import restore_all_sounds, restore_sound
from ..audio.tonegen import GENERATED_SOUNDS, generated, write_wav
from ..data import paths
from ..data.settings import AudioSettings, Settings, SpeechSettings
from ..speech.manager import MODES
from ..speech.voices import ENGINE_FALLBACK, first_letter_index, group_by_engine
from ..speech.voices import search as search_voices
from . import extra_texts as words
from .keys import KEY_ENTER, KEY_F1, KEY_F2, KEY_F3, KEY_F4, GameQuit
from .spoken_menu import Item, ListPicker, SpokenMenu, TextPages

log = logging.getLogger("brain.game")

FUNCTION_KEYS = (KEY_F1, KEY_F2, KEY_F3, KEY_F4)
RATE_RANGE = (-10, 10)
PITCH_RANGE = (-10, 10)
VOLUME_STEP = 10
SPREAD_STEP = 2
SPREAD_MAX = 20


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class Functions:
    def __init__(self, speech, keys, audio, settings: Settings, catalog, export_dir: str,
                 open_folder: Callable[[str], bool], on_change: Callable[[], None] = lambda: None,
                 clock: Callable[[], float] = time.monotonic, settings_dir: str | None = None, voice_guard=None):
        self.speech = speech
        self.voice_guard = voice_guard      # data/voiceguard.py: records a voice while it is being tried
        self.keys = keys
        self.audio = audio
        self.settings = settings
        self.catalog = catalog
        self.export_dir = export_dir
        self.open_folder = open_folder
        self.on_change = on_change
        self.clock = clock
        self.settings_dir = settings_dir
        self._speech_original = SpeechSettings()
        self._audio_original = AudioSettings()

    def handles(self, key_code: int) -> bool:
        return key_code in FUNCTION_KEYS

    def run(self, key_code: int) -> None:
        """Run the function on this key until the player presses Escape in it. Never raises, except GameQuit."""
        try:
            if key_code == KEY_F1:
                TextPages(self.speech, self.keys, words.HELP_TITLE, words.HELP_LINES).run()
            elif key_code == KEY_F2:
                self.settings_menu()
            elif key_code == KEY_F3:
                self.sounds_menu()
            elif key_code == KEY_F4:
                TextPages(self.speech, self.keys, words.ABOUT_TITLE, words.ABOUT_LINES).run()
        except GameQuit:
            raise
        except Exception:
            log.exception("function key %d failed", key_code)
            self.speech.stop()
            self.speech.say_async(words.FAILED)

    # ----- speech settings (F2) -----

    def settings_menu(self) -> None:
        sp, original = self.settings.speech, self._speech_original

        def rate() -> int:
            return sp.rate if sp.rate is not None else self.speech.base_rate

        def change_rate(step: int) -> None:
            sp.rate = clamp(rate() + step, *RATE_RANGE)
            self.speech.set_rate(sp.rate)
            self.on_change()

        def reset_rate() -> None:
            sp.rate = original.rate
            self.speech.set_rate(sp.rate)
            self.on_change()

        def change_volume(step: int) -> None:
            sp.volume = clamp(sp.volume + step * VOLUME_STEP, 0, 100)
            self.speech.set_volume(sp.volume)
            self.on_change()

        def reset_volume() -> None:
            sp.volume = original.volume
            self.speech.set_volume(sp.volume)
            self.on_change()

        def change_pitch(step: int) -> None:
            sp.pitch = clamp(sp.pitch + step, *PITCH_RANGE)
            self.speech.set_pitch(sp.pitch)
            self.on_change()

        def reset_pitch() -> None:
            sp.pitch = original.pitch
            self.speech.set_pitch(sp.pitch)
            self.on_change()

        def change_mode(step: int) -> None:
            sp.mode = MODES[(MODES.index(sp.mode) + step) % len(MODES)]
            self.speech.mode = sp.mode
            self.on_change()

        def reset_mode() -> None:
            sp.mode = original.mode
            self.speech.mode = sp.mode
            self.on_change()

        def change_letters(step: int) -> None:
            modes = words.LETTER_MODES
            sp.list_letters = modes[(modes.index(sp.list_letters) + step) % len(modes)]
            self.on_change()

        def reset_letters() -> None:
            sp.list_letters = original.list_letters
            self.on_change()

        def restore_all() -> str:
            for reset in (reset_rate, reset_volume, reset_pitch, reset_mode, reset_letters):
                reset()
            sp.voice_id = original.voice_id
            self.speech.set_voice(None)
            return words.SPEECH_RESTORED + " " + words.voice_label(self.voice_name())

        items = [
            Item(lambda: words.voice_label(self.voice_name()), enter=self.choose_voice),
            Item(lambda: words.rate_label(rate(), sp.rate is None), enter=lambda: reset_rate(), change=change_rate),
            Item(lambda: words.percent_label("Speech volume", sp.volume, sp.volume == original.volume),
                 enter=lambda: reset_volume(), change=change_volume),
            Item(lambda: words.pitch_label(sp.pitch, sp.pitch == original.pitch),
                 enter=lambda: reset_pitch(), change=change_pitch),
            Item(lambda: words.output_label(sp.mode, self.speech.nvda_running(), sp.mode == original.mode,
                                         self.speech.jaws_running()),
                 enter=lambda: reset_mode(), change=change_mode),
            Item(lambda: words.letters_label(sp.list_letters, sp.list_letters == original.list_letters),
                 enter=reset_letters, change=change_letters),
            Item(lambda: words.RESTORE_SPEECH, enter=restore_all),
            Item(lambda: words.SETTINGS_FOLDER_ITEM, enter=self.open_settings_folder),
        ]
        SpokenMenu(self.speech, self.keys, words.SETTINGS_TITLE, items, help_text=words.SETTINGS_HELP).run()

    def open_settings_folder(self) -> str:
        folder = self.settings_dir or paths.user_data_dir()
        return words.SETTINGS_FOLDER_OPENING if self.open_folder(folder) else words.FOLDER_FAILED

    def voice_name(self) -> str:
        """The name of the voice in use: from the saved choice if it is in the list, else what the engine reports."""
        voice_id = self.settings.speech.voice_id
        if voice_id:
            for voice in self.catalog.voices(timeout=2.0):
                if voice.voice_id == voice_id:
                    return voice.name
        return self.speech.voice_name

    def choose_voice(self) -> str | None:
        """Engines first (the voice list can have thousands of voices), then the voices of one engine; the first
        item of the engine list shows every voice of every engine at once."""
        voices = self.catalog.voices(timeout=5.0)
        if not voices:
            return words.NO_VOICES_LISTED if self.catalog.loaded else words.VOICE_LIST_LOADING
        sp = self.settings.speech
        current = sp.voice_id or self.speech.voice_id
        in_use = next((v for v in voices if v.voice_id == current), voices[0])
        groups = group_by_engine(voices)
        plain = ["All voices of all engines"] + [engine for engine, _ in groups]
        spoken = [words.all_voices_item(len(voices))] + [words.engine_item(e, len(vs)) for e, vs in groups]
        start = 1 + next((i for i, (e, _) in enumerate(groups) if e == (in_use.engine or ENGINE_FALLBACK)), 0)
        while True:
            def find_engine(text: str) -> int | None:
                needle = text.strip().casefold()
                hits = [i for i, n in enumerate(plain) if n.casefold().startswith(needle)]
                hits += [i for i, n in enumerate(plain) if needle in n.casefold() and i not in hits]
                return hits[0] if hits else None

            picked = ListPicker(self.speech, self.keys, words.ENGINE_TITLE, len(spoken), lambda i: spoken[i], start=start,
                                search=find_engine, clock=self.clock, help_text=words.ENGINE_HELP,
                                first_letter=lambda c, at: first_letter_index(plain, c, at),
                                letter_mode=lambda: sp.list_letters).run()
            if picked is None:
                return None
            if picked == 0:
                subset, title = voices, words.ALL_VOICES_TITLE
            else:
                engine, subset = groups[picked - 1]
                title = words.engine_voices_title(engine)
            voice = self._pick_voice(subset, title, in_use.voice_id)
            if voice is None:           # Escape in the voice list: back to the engines
                start = picked
                continue
            # the engine's first voice is the original's choice: keep "no saved voice" for it
            sp.voice_id = None if voice.index == 0 else voice.voice_id
            if self.voice_guard is not None and sp.voice_id:
                self.voice_guard.forget(sp.voice_id)          # choosing a set-aside voice again is asking for another try
                self.voice_guard.arm(sp.voice_id)             # cleared after it has spoken; a crash leaves it for the next start
                self.speech.watch_voice_health(self.voice_guard.clear)
            self.speech.set_voice(sp.voice_id)
            self.on_change()
            return words.voice_chosen(voice.name) + " " + words.VOICE_SAMPLE

    def _pick_voice(self, subset, title: str, current: str):
        """A list of voices read one name at a time; returns the chosen VoiceInfo or None on Escape."""
        sp = self.settings.speech
        names = [v.name for v in subset]
        at = next((i for i, v in enumerate(subset) if v.voice_id == current), 0)

        def name(i: int) -> str:
            return names[i] + (", " + words.CURRENT_VOICE if subset[i].voice_id == current else "")

        def find(text: str) -> int | None:
            found = search_voices(subset, text) if text.strip() else []
            return subset.index(found[0]) if found else None

        chosen = ListPicker(self.speech, self.keys, title, len(subset), name, start=at, search=find, clock=self.clock,
                            first_letter=lambda c, cur: first_letter_index(names, c, cur),
                            letter_mode=lambda: sp.list_letters, help_text=words.list_help(sp.list_letters)).run()
        return None if chosen is None else subset[chosen]

    # ----- sounds menu (F3) -----

    def sounds_menu(self) -> None:
        au, original = self.settings.audio, self._audio_original
        library = self.audio.library

        def change_volume(step: int) -> None:
            au.effects_volume = clamp(au.effects_volume + step * VOLUME_STEP, 0, 100)
            self.on_change()
            self.sample()

        def reset_volume() -> None:
            au.effects_volume = original.effects_volume
            self.on_change()
            self.sample()

        def change_spread(step: int) -> None:
            au.pitch_spread = clamp(au.pitch_spread + step * SPREAD_STEP, 0, SPREAD_MAX)
            self.on_change()

        def reset_spread() -> None:
            au.pitch_spread = original.pitch_spread
            self.on_change()

        def change_start(step: int) -> None:
            au.start_early = not au.start_early
            self.on_change()

        def reset_start() -> None:
            au.start_early = original.start_early
            self.on_change()

        def reload() -> str:
            self.audio.refresh()
            notices = library.take_notices()
            return " ".join([words.reloaded(library.pool_size())] + notices)

        def check() -> str:
            problems = library.check_all()
            library.take_notices()          # the count below says it; details are in the log
            for problem in problems:
                log.info("sound check: %s", problem)
            return words.checked(len(problems))

        def open_sounds_folder() -> str:
            library.refresh()                # makes sure the folder and sounds.txt exist
            return words.opening_folder() if self.open_folder(library.player_dir) else words.FOLDER_FAILED

        def restore_all() -> str:
            reset_volume()
            reset_spread()
            reset_start()
            return words.SOUNDS_RESTORED

        items = [
            Item(lambda: words.volume_label(au.effects_volume, au.effects_volume == original.effects_volume),
                 enter=lambda: reset_volume(), change=change_volume),
            Item(lambda: words.spread_label(au.pitch_spread, au.pitch_spread == original.pitch_spread),
                 enter=lambda: reset_spread(), change=change_spread),
            Item(lambda: words.PREVIEW_ITEM, enter=self.preview_sounds),
            Item(lambda: words.RELOAD_ITEM, enter=reload),
            Item(lambda: words.CHECK_ITEM, enter=check),
            Item(lambda: words.FOLDER_ITEM, enter=open_sounds_folder),
            Item(lambda: words.EXPORT_ITEM, enter=self.export_generated),
            Item(lambda: words.RESTORE_SOUNDS, enter=restore_all),
            Item(lambda: words.RESTORE_ONE_ITEM, enter=self.restore_one_sound),
            Item(lambda: words.RESTORE_ALL_ITEM, enter=self.restore_all_sounds),
            Item(lambda: words.start_label(au.start_early, au.start_early == original.start_early),
                 enter=lambda: reset_start(), change=change_start),
        ]
        SpokenMenu(self.speech, self.keys, words.SOUNDS_TITLE, items).run()

    def sample(self) -> None:
        """Let the player hear the sound volume: sound 1 once at its own rate."""
        self.audio.preview(sound_id(1))

    def preview_sounds(self) -> str | None:
        """Sounds one by one: the numbered sounds the program would pick from, then the exit beep."""
        library = self.audio.library
        library.refresh()
        count = max(1, library.pool_size())

        def wanted(i: int) -> str:
            return "beep_exit" if i == count else sound_id(i + 1)

        def name(i: int) -> str:
            return words.sound_name(None if i == count else i + 1, library.pick(wanted(i)).source)

        def play(i: int) -> str | None:
            self.audio.stop_preview()
            self.audio.preview(wanted(i))
            return None

        try:
            ListPicker(self.speech, self.keys, words.PREVIEW_TITLE, count + 1, name, on_enter=play,
                       close_on_enter=False, help_text=words.PREVIEW_HELP, clock=self.clock).run()
        finally:
            self.audio.stop_preview()
        return None

    def restore_one_sound(self) -> str | None:
        """A list of the sounds; Enter puts the chosen one back to the original (playbook 7.7, 7.10)."""
        library = self.audio.library
        library.refresh()
        count = max(1, library.pool_size())

        def wanted(i: int) -> str:
            return "beep_exit" if i == count else sound_id(i + 1)

        def name(i: int) -> str:
            return words.sound_name(None if i == count else i + 1, library.pick(wanted(i)).source)

        def restore(i: int) -> str:
            result = restore_sound(library.player_dir, wanted(i))
            library.refresh()
            return words.restored_one(None if i == count else i + 1, result) + " " + name(i)

        ListPicker(self.speech, self.keys, words.RESTORE_ONE_TITLE, count + 1, name, on_enter=restore,
                   close_on_enter=False, help_text=words.RESTORE_ONE_HELP, clock=self.clock).run()
        return None

    def restore_all_sounds(self) -> str:
        """Every sound back to the original, after one confirming Enter (it moves the player's own files)."""
        self.speech.stop()
        self.speech.say_async(words.CONFIRM_RESTORE_ALL)
        if self.keys.read_key() != KEY_ENTER:
            return words.NOTHING_CHANGED
        library = self.audio.library
        result = restore_all_sounds(library.player_dir)
        library.refresh()
        return words.restored_all(result)

    def export_generated(self) -> str:
        try:
            os.makedirs(self.export_dir, exist_ok=True)
            count = 0
            for key in GENERATED_SOUNDS:
                sound = generated(key)
                if sound is not None:
                    write_wav(os.path.join(self.export_dir, key + ".wav"), sound)
                    count += 1
            return words.exported(count)
        except OSError:
            log.exception("could not save the generated sounds to %s", self.export_dir)
            return words.EXPORT_FAILED
