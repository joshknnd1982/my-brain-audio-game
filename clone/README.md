# My Brain by Josh Kennedy, inspired by Jim Kitchen

This is inspired by Jim Kitchen.

Brain ("My Brain") is a sound toy for blind players, recreated from Jim Kitchen's original free program of 2013. Jim Kitchen was blind from birth and made his games free for the blind community. He died in 2015. This clone is new code written from a description of how the original behaves; it contains none of his program code.

Version 1.0.2. The program is complete, covered by conformance and stress tests, and the maintainer has listened to it with NVDA and with SAPI 5 voices. It is not signed, so Windows SmartScreen may warn when you start the installer: choose "More info", then "Run anyway".

## Install
Run `brain-setup-1.0.2.exe`. It installs for you alone by default (no administrator rights) and offers an all-users install. It picks the 64-bit or 32-bit program for your Windows. It adds a Start menu entry and, if you tick it, a desktop shortcut. To remove it, use Windows' Apps list ("My Brain") or the Start menu uninstall entry; the uninstaller removes the whole program folder (it closes My Brain first if it is running) and asks whether to delete your settings and sounds too (the default is to keep them). Put sounds of your own in the Brain folder in AppData, not in the program folder, because the program folder is removed completely. The portable zip holds both builds in folders `64-bit` and `32-bit`: unpack it anywhere and start `brain.exe`; your settings still go to `%APPDATA%\Kitchensinc Revival\Brain`.

## How it plays
Press a number from 1 to 9 to choose how many sounds play at once, pick a panning style with the Up and Down arrows, and press Enter. Random short sounds then play at random pitch until you press any key. Escape leaves the program.

## Keys
The original's keys keep their meaning: in the main menu the digits 1 to 9 and Escape, in the panning menu Up, Down, Enter and Escape, and during playback any key stops the sounds. The clone adds four keys that, in the original, only made the voice say a letter. They work in the main menu and in the panning menu:
- F1: help. Reads the keys, one line at a time (Up and Down read the lines, Escape goes back).
- F2: speech settings (below).
- F3: sounds menu (below).
- F4: about Brain and Jim Kitchen.
Changed from the original: in the main menu F1 to F4 used to say the letters p, q, r and s; in the panning menu F1 used to restart the menu silently and F2 to F4 said q, r and s. After a function you return to the menu you came from (the panning menu starts again at "no panning"). Alt+F4 still closes the window.
Inside a menu: Up and Down move through the items, Left and Right change a value, Enter does the item's action or puts a value back to its original, Home and End jump to the first and last item, F1 repeats the help line, Escape goes back (it never leaves the program from inside a menu). Every item says its value, and ", original" when it is the original value.

## Speech
- Brain speaks with a SAPI 5 voice, as the original did: the first voice in Windows' voice list, at volume 90, at that voice's own rate.
- F2 speech settings: voice (Enter opens the list of speech engines with their voice counts; its first item is all voices of all engines; Enter on an engine lists only its voices; Up and Down, Page Up and Page Down by ten, Home and End, or letter keys, see the letter-keys item; Enter chooses, Escape goes back a level and keeps the old voice), letter keys in lists (type letters to search for a name, or a letter jumps to the next name that starts with it), rate (-10 to 10), volume (0 to 100 in steps of ten), pitch (-10 to 10), output (SAPI 5 voice only, NVDA only, JAWS only, or automatic: NVDA when it runs, else JAWS when it runs, otherwise SAPI 5) and restore the original settings. They take effect at once and are saved (see Settings and files below). The last item opens the folder that holds `settings.txt`.
- Pitch works only with voices that support SAPI pitch markup. Checked on the development PC: Microsoft David and Microsoft Zira change pitch, FlexVoice2 Bill does not.
- Screen readers: NVDA through its controller client, and JAWS through its own COM interface (nothing is bundled for JAWS; it uses the JAWS installed on your PC). In the output setting, "NVDA only" and "JAWS only" use that screen reader's voice, and "automatic" uses NVDA when it runs, else JAWS when it runs, else the SAPI 5 voice. If the chosen screen reader is not running, Brain uses SAPI 5 so it is never silent. JAWS cannot tell Brain when it has finished speaking, so Brain waits a time guessed from the text length (0.15 s plus 0.035 s per character, measured on the maintainer's JAWS 2026) before a sound starts; with a much slower JAWS voice a sound may start over the end of a prompt. JAWS support was tested with a fake JAWS, with JAWS not running, and with JAWS 2026 running (64-bit and 32-bit builds).
- Brain also tells you, once, about problems that the original ignored: a damaged sounds.txt, a sound file it cannot use, a missing sound device, and a voice that crashed Brain the last time it was used (Brain then starts with the first voice and keeps your choice in settings.txt; choose the voice again in the F2 voice list to try it once more).

## Sounds: replacing and adding
Brain ships Jim Kitchen's 42 original wav files (`assets\sounds`, included on the maintainer's own responsibility: Jim Kitchen gave the maintainer permission to use his wav files, but the original email is lost and a phone call was not recorded; a rights holder can ask for them to be removed and they will be). Your own sounds live in `%APPDATA%\Kitchensinc Revival\Brain\sounds`, which Brain creates on first start. A sound in that folder is used instead of the shipped one; nothing else needs to change.
- To replace sound number 5, put a file named `brain5.wav` in that folder. `brain05.wav` also works, and so do `.ogg`, `.flac` and `.mp3`. Any sample rate, 8, 16, 24 or 32 bits, mono or stereo. Damaged, empty or very long (over 30 seconds) files are skipped and the shipped sound is used; Brain says so once and writes details to the log.
- To add sounds, name them `brain43.wav`, `brain44.wav` and so on. Like Jim Kitchen's readme says, keep the numbers consecutive: if `brain43` is missing, `brain44` is not used. Brain notices new files each time playback starts.
- Old Brain sound sets work as they are: copy their `brain1.wav` ... `brainN.wav` into the folder. For ogg, flac and mp3 files the pitch steps are relative to 44,100 Hz, because the decoder resamples them; wav files keep their own rate, as in the original.
- The exit beep (played twice when Brain ends without the Kitchensinc game menu) is the Windows default sound. Put `beep_exit.wav` in the folder to replace it.
- `sounds.txt` in the same folder has plain-word notes and lets you point a sound at another file, lower or raise its volume, or switch it off (it then stays silent but keeps its place). Example lines: `brain5 = file=my best bell.wav; volume=80` and `brain7 = off`. A damaged `sounds.txt` is saved as `sounds.txt.damaged1` and replaced by a fresh one.
- F3 sounds menu: sound volume (0 to 100 percent in steps of ten, original 100; each change plays a sample), pitch variation (0 to 20 in steps of two, original 20; 0 plays every sound at its own pitch), listen to the sounds one by one (Up and Down, Enter plays; sounds that come from your own files or are switched off are named so), reload the sounds from the folder, check the sound files (says how many problems; details go to the log), open the sounds folder, save the generated sounds as wav files (the exit blip goes to `exported sounds` next to the sounds folder) restore the original sound settings, restore one sound to the original (a list; Enter on a sound puts it back) and restore all sounds to the original (asks for a second Enter first), and, as the last item, when the sounds start: after the spoken prompt "Press the space bar to stop" (original, the default) or right away (the first sound begins as soon as you press Enter in the panning menu, while the prompt is still spoken; with a slow voice that saves a couple of seconds). Sound volume, pitch variation and the start setting are saved.

## Settings and files
Everything Brain keeps for you is in `%APPDATA%\Kitchensinc Revival\Brain` (the last item of the F2 menu opens it):
- `settings.txt`: the speech voice, rate, volume, pitch, output and letter keys in lists, the sound volume, the pitch variation and when the sounds start (`sound_start = after_prompt` or `right_away`). Brain writes it whenever you change something in F2 or F3, and reads it at the start. Plain lines, `name = value`, with notes at the top; you may edit it in Notepad while Brain is closed (Brain rewrites the whole file the next time you change a setting, so notes you add are not kept). A line Brain cannot understand is skipped, that setting stays original, and Brain says "N problems found in settings.txt, details are in the log". The original values are: first voice in the Windows list, voice rate unchanged, speech volume 90, pitch 0, SAPI 5 only, sound volume 100, pitch variation 20, sounds start after the prompt.
- `sounds` folder with `sounds.txt` (see above) and `logs\brain.log`.
- If Brain finds a file empty, cut off, binary, too large (over 1 MB), in an unknown newer format or all nonsense, it saves a copy next to it (`settings.txt.damaged1`, up to three kept), makes a new one with the original values and says once: "settings.txt was damaged and has been reset to the original settings. A copy was saved." A missing file or folder is simply made again. Files saved by Notepad as UTF-8, UTF-8 with BOM, UTF-16 with BOM or the Windows code page are all read.
- A file that another program is holding open is left alone: Brain uses the original values for that run, says so, and saves nothing over it. If the folder or file cannot be written (read-only, no permission), Brain keeps playing from memory and says once where the file belongs.
- If the voice saved in `settings.txt` is no longer installed, Brain uses the first voice, says so, and keeps the saved choice in the file (installing the voice again brings it back).
- Restore commands (F3): "Restore one sound to the original" removes that sound's line from `sounds.txt` and moves the sound files you named for it (`brain5.wav` and so on) into `sounds\removed sounds`, nothing is deleted. "Restore all sounds" keeps your old `sounds.txt` once as `sounds.txt.before-reset`, writes a fresh one and moves every sound file named `brainN.*` or `beep_exit.*` into `removed sounds`, the added `brain43` and up included. Files with other names, such as one pointed at by a `file=` line, stay where they are. To get a file back, move it out of `removed sounds`.
- If something unexpected goes wrong while Brain runs, it writes the details to the log, says "Something went wrong, details are in the log. Back to the main menu." and carries on at the main menu. If the same thing goes wrong five times in a row Brain says so and closes.

## Jim Kitchen's original readme (brain.txt)
> Thank you for checking out my Brain By Jim Kitchen
>
> If you choose to add, delete or replace some of the wave files, you should be sure to keep them numbered consecutively. They are now numbered from brain1.wav to brain42.wav. You can also put the brain.exe program in any folder so that you can then make an entirely new set of wave files for it. If you make up a set of wave files that sound cool, I would appreciate you sending them to me so that I could listen to them.
>
> To remove the Brain program run the nobrain.bat file

In this clone the installer's uninstaller replaces nobrain.bat. Jim Kitchen's original email address and phone number are left out here: he died in 2015 and they are no longer his.

## Running from source (developers)
Environments: `clone\tools\setup_envs.ps1` creates 64-bit and 32-bit Python 3.14 environments in `%USERPROFILE%\.kitchensinc-venvs`.

From the `clone` folder:
- Run: `C:\Users\joshk\.kitchensinc-venvs\brain-64\Scripts\python.exe -m brain` with `src` on the Python path (`set PYTHONPATH=src`), or double-click `tools\play_brain.bat` (64-bit) or `tools\play_brain_32.bat` (32-bit); they open no console window.
- Tests: `C:\Users\joshk\.kitchensinc-venvs\brain-64\Scripts\python.exe -m pytest -q` (same with `brain-32`). Real-engine tests run SAPI 5 at volume 0 and never make NVDA speak.
- Conformance tests (`tests\test_conformance.py`) check the clone against the frozen game description. Stress tests (`tests\test_stress.py`, `tests\test_app_startup.py`) throw thousands of random keys, failing speech and sound, closed windows and 5,000 voices at it.
- Silent check of a held Enter on the real voice and mixer: `python tools\held_enter_check.py <scratch folder>`.
- Silent smoke run of the real program: `python tools\smoke_run.py <scratch folder>`.
- Silent timing check of the real mixer and sound device (volume 0, nothing is heard): `python tools\audio_selfcheck.py <scratch folder>`. Tests that use the mixer run on SDL's silent dummy driver.
- Silent run through the F1 to F4 menus with the real voice list and mixer (volume 0, scripted keys, nothing opens, writes a real `settings.txt` into the scratch folder): `python tools\menu_smoke.py <scratch folder>`.
- Silent check of the playback loop on the real mixer (key response, gaps between sounds, CPU use; volume 0): `python tools\playback_selfcheck.py <scratch folder>`.
- Check of the JAWS backend against a running JAWS (JAWS speaks about 15 seconds): `python tools\jaws_check.py <report file>`; without JAWS running it only reports that and says nothing. The JAWS tests in `tests	est_jaws.py` use a fake JAWS and never speak.
- Real JAWS speech duration by speakers loopback (JAWS speaks about 25 seconds, needs a quiet PC): `<python with soundcard, numpy, pywin32> tools\jaws_duration_check.py <report file>`.
- Which voices honor pitch: `python tools\sapi_pitch_check.py [voice name part ...]` (renders to memory, nothing is heard).
- Build (P9): `powershell -ExecutionPolicy Bypass -File tools\build.ps1` makes `brain.exe` folders (PyInstaller onedir) for 64-bit and 32-bit in `%USERPROFILE%\.kitchensinc-builds\brain\<bits>\dist\brain`, from a copy of `src` (the build cannot see the source tree or the original files). Then `python tools\record_build.py` writes versions and SHA-256 hashes into `..\release\`.
- Test of a built exe (starts it, types keys, listens to the speakers by loopback, checks the exit): `<python with soundcard, numpy, pywin32> tools\exe_smoke.py <brain.exe> <64 or 32> <scratch folder> [sound volume]`; `tools\bundled_dll_check.py` loads the bundled NVDA DLL with the matching Python.
- Debug log: set `BRAIN_DEBUG=1`; the log is in `%APPDATA%\Kitchensinc Revival\Brain\logs\brain.log`.

## Third-party parts
- NVDA Controller Client 2026.2 by NV Access Limited, LGPL 2.1, unmodified: `src\brain\speech\nvda_client\x86\nvdaControllerClient.dll` (SHA-256 96295979a25ab1c8ddc9b6aaffdd81ed72c9504880850d49e99f1db96055a7d0) and `x64\nvdaControllerClient.dll` (SHA-256 598b7ec3dc469814f571275929f676ce73834c469fbdb359a06fd4db4e0fc866). License: `src\brain\speech\nvda_client\license.txt`. Source: https://download.nvaccess.org/releases/2026.2/nvda_2026.2_controllerClient.zip
- Python libraries: see `requirements.txt`.

## License
The new code, tests and documents: MIT License, copyright Josh Kennedy (file `LICENSE`). The 42 sound files are Jim Kitchen's originals and are not covered by it (see `LICENSE`). Third-party parts: `THIRD_PARTY_NOTICES.txt`.
