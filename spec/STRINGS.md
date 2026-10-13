# STRINGS: Brain

Source: `extracted/strings/utf16.txt` and `ascii.txt` (all strings, with offsets and VAs). Program text is UTF-16 (VB6 Unicode). Spaces inside the quotes are part of the text. Events from P3 S3.1 code recovery (statement numbers: `spec/PROCEDURE_INDEX.md`). "waits" = say (speech finishes before the program goes on); "async" = say2 (queued, program goes on at once).

| ID | exact text | offset (VA) | event | variables | tag |
|---|---|---|---|---|---|
| S01 | "My Brain by Josh Kennedy, inspired by Jim Kitchen" (clone title since 2026-10-13, owner's format; the original caption was " My Brain  By Jim Kitchen " with a leading space, two spaces after Brain and a trailing space) | 0x2844 (0x402844) | window caption, set at startup (stmt 3); not spoken by the program | none | CODE |
| S02 | "true" | 0x2880 | converted to Boolean True and assigned to a form property at startup (stmt 4; probably KeyPreview); not spoken | none | CODE, property INFERRED |
| S03 | "brain*.wav" | 0x2900 | Dir pattern that counts the wavs at startup (stmt 35) | none | CODE |
| S04 | "My Brain by Josh Kennedy, inspired by Jim Kitchen." (clone title since 2026-10-13, owner's format; the original said " My Brain  By Jim Kitchen. "; it now also carries the attribution, so the separate "This is inspired by Jim Kitchen." at startup is gone) | 0x291c | spoken once at startup, waits (stmt 49) | none | CODE |
| S05 | " Press a number from one to nine, or the escape key to exit. " | 0x2968 | main menu prompt, async, every time the main menu is entered (stmt 60) | none | CODE |
| S06 | " Select. " | 0x29f4 | panning menu start, async (stmt 75), followed by the mode name | none | CODE |
| S07 | "no panning" | 0x2a0c | panning menu, mode 1 announce, async (stmt 79) | none | CODE |
| S08 | "stationary panning" | 0x2a28 | mode 2 announce, async (stmt 81) | none | CODE |
| S09 | "semi random panning" | 0x2a54 | mode 3 announce, async (stmt 83) | none | CODE |
| S10 | "totally random panning" | 0x2a80 | mode 4 announce, async (stmt 85) | none | CODE |
| S11 | " Press the space bar to stop. " | 0x2ad8 | after Enter in the panning menu, waits, then playback starts (stmt 120) | none | CODE |
| S12 | "brain" | 0x2b1c | wav name prefix: "brain" & Trim(Str(number)) & ".wav" (stmt 137 and the same in each slot) | number 1..n | CODE |
| S13 | ".wav" | 0x2b2c | wav name suffix | none | CODE |
| S14 | "Sorry but one or more of the wave files seem to be corrupt" | 0x2b84 | message box text, unreachable code (stmt 518); never shown | none | CODE |
| S15 | "Please contact Jim Kitchen" | 0x2c00 | second line (after Chr(13)) of both message boxes (stmt 519, 524) | none | CODE |
| S16 | "Sorry but I couldn't find any voices to use" | 0x2c3c | message box when no SAPI 5 voice is installed (stmt 523-525), OK button only, then exit | none | CODE |
| S17 | "gamemenu.exe" | 0x2c98 | exit: Dir check in the current folder, compared in lower case, Shell with window style 3 if found (stmt 536-546) | none | CODE |
| S18 | " exiting program " | 0x2cb8 | exit, waits, only when gamemenu.exe is not found (stmt 538) | none | CODE |
| S19 | "Sorry, but I could not find the Kitchensinc game menu program." | 0x2ce0 | exit when gamemenu.exe is missing, after two beeps (stmt 552); the voice is already released, so it is never actually spoken | none | CODE, silence INFERRED |
| S20 | the pressed key's character, LCase(Chr(KeyCode)) | built at run time (Form_KeyDown) | main menu: every key except Escape, waits (stmt 65); panning menu: other keys, quick echo at rate + 5, async, not for F1 (saykey) | KeyCode | CODE |

Key code texts compared (CODE): "27" Escape, "13" Enter, "38" Up arrow, "40" Down arrow, "112" F1 (UTF-16 at 0x29e8, 0x2ab4, 0x2ac0, 0x2acc, 0x2838).

Message box details (CODE): prompt = text & Chr(13) & "Please contact Jim Kitchen", buttons 0 (OK only), title, help file and context omitted, so the title is App.Title (INFERRED: "brain", the project and exe name). The box's result is stored into a key variable and not used.

Identifiers and metadata (not spoken, CODE): form name "Form1", project "brain" (C:\Program Files\Microsoft Visual Studio\VB98\brain.vbp), COM object "Voice" from SAPI.DLL "SpeechLib", procedure names clk, say, say2, stopspeech, dy, saykey, getkey, library "VISDATA.EXE" (VB data manager reference, left over, not used for play).
Version resource (CODE): CompanyName "Kitchens Inc", ProductName "brain", FileVersion 1.00, OriginalFilename brain.exe.
brain.txt (readme) text is in `original/brain.txt` and must be kept in the clone's readme with the attribution (section 13 of the spec).

## Clone additions (not in the original), P7 S7.4

These texts exist only in the clone. They are spoken by the same voice as the original's texts, in `clone/src/brain/game/extra_texts.py`; the original's own texts stay in `texts.py` and above. Wording is Claude's (EVIDENCE: none needed, new function), and P8.2 may change it.

| ID | Text (summary) | Event |
|----|----------------|-------|
| S21 | "This is inspired by Jim Kitchen." (DECISIONS P7 S7.1) | startup, once per launch, after the title, waits |
| S22 | "No sound device was found, so Brain will run without sound." | startup, only when no sound device opened, waits |
| S23 | the library's notices, e.g. "sounds.txt was damaged and has been reset to the original settings. A copy was saved." and "A sound file could not be used and was skipped, details are in the log." | startup (waits), playback start (waits), during playback (async) |
| S24 | Help (F1): title, three lines on keys, a help line | F1 in the main or panning menu |
| S25 | About (F4): version, "This is inspired by Jim Kitchen.", blind from birth, free for the blind community, died in 2015, new code that plays his original sounds | F4 |
| S26 | Speech settings (F2): voice, rate, volume, pitch, output, restore; every item's label includes its value and ", original" when it is the original value | F2 |
| S27 | Voice list: "Choose a voice. N items. ...", voice names, ", current voice", "Voice set to NAME. This is how Brain will speak." | Voice item |
| S28 | Sounds (F3): sound volume, pitch variation, listen to the sounds, reload, check, open folder, save generated sounds, restore; results such as "42 sounds found.", "No problems found in the sound files." or "N problems found, details are in the log." | F3 |
| S29 | Sound names in the listening list: "Sound 5", ", your file", ", switched off", ", no usable file", "Exit beep" | listening list |
| S30 | "Something went wrong, details are in the log." | a function failed unexpectedly |

Menu help line (every function menu, F1 inside it): "Up and Down move through the items. Left and Right change a value. Enter does the item's action or restores a value to its original. Escape goes back."

### Added in P7 S7.5 and S7.7

| ID | Text (summary) | Event |
|----|----------------|-------|
| S31 | settings.txt notices: "settings.txt was damaged and has been reset to the original settings. A copy was saved.", "N problems found in settings.txt, details are in the log.", "settings.txt is in use by another program, so Brain uses the original settings this time.", "Brain could not save its settings file, so changes last only until Brain closes. The file belongs in the Brain folder inside Kitchensinc Revival in your AppData Roaming folder.", "The voice saved in the settings was not found, so the first voice is used." | startup (waits), after a function (async) |
| S32 | sounds.txt notices added: "sounds.txt is in use by another program, so Brain uses the original sound settings this time.", "sounds.txt could not be written, so Brain uses the original sound settings. It belongs in the sounds folder ..." | startup, playback start |
| S33 | Sounds menu items 9 and 10: "Restore one sound to the original.", "Restore all sounds to the original."; list "Restore one sound. N items ..."; results "Sound N is back to the original. Your file was moved to the removed sounds folder.", "Sound N was already the original.", the confirmation "This puts every sound back to the original. ... Press Enter to do it, or any other key to cancel.", "Nothing was changed.", "All sounds are back to the original. The old sounds.txt was kept as sounds.txt.before-reset. N of your sound files were moved to the removed sounds folder." | F3 |
| S34 | Speech settings item 7: "Open the folder with the settings file." then "Opening the folder. The file is settings.txt." | F2 |
| S35 | "Something went wrong, details are in the log. Back to the main menu." and "Brain keeps running into the same problem and has to close. Details are in the log." | the last-resort handler |
| S36 | Speech output item values (F2): "SAPI 5 voice only", "NVDA only", "JAWS only", "automatic"; warnings after the value when the engine is not running: "NVDA is not running now, so the SAPI 5 voice is used.", "JAWS is not running now, so the SAPI 5 voice is used.", "NVDA and JAWS are not running now, so the SAPI 5 voice is used." (automatic: only when neither runs) | F2 output item (P10 JAWS) |
| S37 | Voice crash notice (spoken once at start): "The voice <name> crashed Brain last time, so Brain uses <voice> for now. Choose it again in the voice list to try it again." | the saved voice was set aside by the crash guard (data/voiceguard.py) |