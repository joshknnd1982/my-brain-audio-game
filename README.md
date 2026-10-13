# My Brain by Josh Kennedy, inspired by Jim Kitchen

This is inspired by Jim Kitchen.

Jim Kitchen was blind from birth and made many free audio games for the blind community. He died in 2015. "Brain" is one of his sound toys. This project is a new Windows version of it, written from a description of how his program behaves; it contains none of his program code. It plays his original 42 sound files.

## What it is
Press a number from 1 to 9 to choose how many sounds play at once, pick a panning style with the Up and Down arrows, and press Enter. Random short sounds then play at random pitch until you press any key. Escape leaves the program. Everything is spoken; nothing needs sight.

## Download and install
Get the files from the [Releases page](https://github.com/joshknnd1982/my-brain-audio-game/releases).
- `brain-setup-1.0.0.exe`: the installer. One file for 64-bit and 32-bit Windows 10 or 11. It installs for you alone by default (no administrator rights needed) and offers an all-users install. It adds a Start menu entry and, if you tick it, a desktop shortcut. Uninstall it from Windows' Apps list; it asks whether to delete your settings too (the default is to keep them).
- `brain-portable-1.0.0.zip`: no installation. Unpack it anywhere and run `brain.exe` from the `64-bit` folder (or `32-bit` on 32-bit Windows).
- `checksums.txt`: SHA-256 of both files.

The files are not code-signed, because signing costs money. Windows SmartScreen may warn when you start the installer: choose "More info", then "Run anyway".

## Keys
The original's keys keep their meaning: in the main menu the digits 1 to 9 and Escape; in the panning menu Up, Down, Enter and Escape; during playback any key stops the sounds. Added keys, in the main menu and the panning menu: F1 help, F2 speech settings, F3 sounds, F4 about. Inside a menu: Up and Down move, Left and Right change a value, Enter does the item's action or restores its original value, Home and End jump, Escape goes back.

## Speech: NVDA, JAWS and SAPI 5
- The default is what the original did: the first Windows SAPI 5 voice. F2 lets you choose any installed voice (a list of engines, then voices, with type-ahead or first-letter jumping), the rate, volume and pitch.
- NVDA is supported through its controller client. JAWS is supported through its own COM interface; nothing of either is needed to run the game, and if the chosen screen reader is not running the SAPI 5 voice is used so Brain is never silent.
- F2 "speech output": SAPI 5 voice only (default), NVDA only, JAWS only, or automatic (NVDA if it runs, else JAWS if it runs, else SAPI 5).
- Tested: SAPI 5 voices and NVDA by the maintainer; JAWS 2026 (64-bit and 32-bit builds) by the maintainer, including a latency check while arrowing through the menus. JAWS cannot tell Brain when it has finished speaking, so Brain waits a time guessed from the text length before a sound starts.

## Your sounds, your settings
Everything is in `%APPDATA%\Kitchensinc Revival\Brain` (F2's last item opens it): `settings.txt` (speech and sound settings), a `sounds` folder with `sounds.txt` and any sound files of your own (`brain5.wav` replaces sound 5; `brain43.wav` and up add sounds; ogg, flac and mp3 work too; F3 can listen to, reload, check and restore sounds), and `logs`. Damaged or missing files are repaired with the original values, with a spoken notice. The full description is in [clone/README.md](clone/README.md), which also ships as `README.txt` beside the program.

## About the sound files
The 42 wav files are Jim Kitchen's originals. Jim Kitchen gave the maintainer permission to use his wav files, but the original email is lost and a later phone call was not recorded, so that permission cannot be shown to anyone. The files are included on the maintainer's own responsibility. If a rights holder asks for them to be removed, they will be removed. The program's own code is a new work (below).

## Build from source
Needs Python 3.14 (64-bit and 32-bit for both builds), Inno Setup 6 for the installer, and the packages in `clone/requirements.txt`.
1. `clone\tools\setup_envs.ps1` makes the two Python environments in `%USERPROFILE%\.kitchensinc-venvs`.
2. Tests, from `clone`: `python -m pytest -q` in each environment (about 630 tests; the real-engine tests run SAPI 5 at volume 0 and never make NVDA or JAWS speak).
3. `clone\tools\build.ps1` builds both `brain.exe` folders with PyInstaller, then `release\installer.iss` (Inno Setup compiler) and `clone\tools\make_portable.py` make the installer and the zip. `clone\tools\verify_installer.py` installs, updates and uninstalls it silently in a scratch folder.
4. `spec/` holds the written description of the original program's behavior (`GAME_SPEC.md`), its decisions and open questions.

## License
The new code, tests and documents are under the MIT License (`LICENSE`), copyright Josh Kennedy. The sound files are Jim Kitchen's and are not covered by it (see `SOUNDS_NOTICE.txt`). Third-party parts: `clone/THIRD_PARTY_NOTICES.txt`.

## Credits
Jim Kitchen, for the original Brain and his free games. Code and maintenance: Josh Kennedy, https://github.com/joshknnd1982. NVDA controller client: NV Access.
