# GAME_SPEC: Brain (My Brain) by Jim Kitchen

Version: 1.0, FROZEN 2026-10-12 (P5 S5.2). Consolidated in S5.1, audited and fixed in S5.2 (section 18). Later changes go to DECISIONS.md with a new spec version number. Sources: P3 S3.1 code recovery (all 9 procedures), P4 desk analysis (the original was not run, OPEN_QUESTIONS 15), P5 tests on this PC.
Evidence tags per playbook 5.3: CODE, OBSERVED, OWNER-CONFIRMED, INFERRED (with reason), GUESS, UNKNOWN. Statement numbers (stmt N) and procedures: `spec/PROCEDURE_INDEX.md`. Scratch outputs named here live in `work/` (git-ignored).

## 1. Overview
Brain ("My Brain") is a sound toy, not a game: no score, no win or loss, nothing saved (CODE: no counters, no file writes). The player picks how many sounds play at once (1 to 9) and one of four panning styles; the program then plays random short wavs from its folder, each at a random pitch, back to back in every slot, until a key is pressed (CODE). All feedback is speech from a SAPI 5 voice plus the sounds. The window has no controls and shows only its caption " My Brain  By Jim Kitchen " (CODE).

## 2. Source facts
- Files: brain.exe, brain.txt, brain1.wav to brain42.wav (44 files). Sizes, dates, SHA-256 and wav formats: `extracted/inventory.md` (CODE).
- brain.exe: 65,536 bytes, SHA-256 49889600e2b7dd690068fb259b7afe5ee2760c52ba70d9c83e46578b621b1ccf, PE32 i386 GUI, link time 2013-09-13 13:19:18 UTC (CODE).
- Toolchain: Visual Basic 6.00.8041 native code (not p-code), Microsoft Linker 6.0, VB5! header, no packer, no overlay (CODE: Detect It Easy 3.21, pefile). Runtime MSVBVM60.DLL, 102 imports.
- Project: C:\Program Files\Microsoft Visual Studio\VB98\brain.vbp; VB header project description, exe name and project name all "brain" (CODE, P5 header read); one form Form1 (start object), no module, no controls, no Declare statements (CODE).
- Speech: SAPI 5 "SpeechLib" (SAPI.DLL), one form-level `WithEvents Voice As SpVoice` (CODE, PROCEDURE_INDEX).
- Sound: DirectX 8 for Visual Basic (dx8vb.dll): DirectX8, DirectSound8 and nine DirectSoundSecondaryBuffer8 objects (CODE: class and interface IDs at 0x40288c-0x402954, creation at stmt 5-6). P2 reported no DirectX because it searched names; this program names DirectX only by class ID.
- dx8vb.dll is not installed or registered on this PC (CODE: file and registry check). INFERRED: here the original stops at startup with VB run-time error 429, because stmt 5 runs before any error handler.
- Wavs: 42, all mono; 36 are 8-bit, 6 are 16-bit; sample rates 11025 Hz (22 files), 22222 (3), 44100 (3), 5500, 11111, 11000, 22050, 8000 (2 each), 10989, 12048, 8363, 5564 (1 each); 3 to 250 ms; brain7.wav is completely silent (CODE, inventory and P4 file analysis).
- Version resource: CompanyName "Kitchens Inc", ProductName "brain", FileVersion 1.00, OriginalFilename brain.exe (CODE).

## 3. Program flow
### 3.1 Startup (Form_Load stmt 1-49)
1. Form1 shown; caption " My Brain  By Jim Kitchen "; a Boolean form property (form interface offset 0x1d4) set to True from the text "true" (CODE). Which property is not settable without VB6.OLB; INFERRED KeyPreview; no effect either way, the form has no controls.
2. DirectX8 created; DirectSound created on the default device; cooperative level 2 (priority) on the form window; a buffer description field set to &HE0 (CODE). INFERRED: it is the flags field and means control frequency (0x20) + control pan (0x40) + control volume (0x80); reason: &HE0 is exactly that documented DSBCAPS sum and the program then changes frequency, pan and volume on every buffer. The dx8vb.dll type library was not available to name the field and the methods; method names in 5.4 are INFERRED the same way (argument use, PROCEDURE_INDEX).
3. Voice = New SpVoice (twice, CODE). Voice count = number of installed SAPI 5 voices. If 0: message box (15), then the exit sequence (3.5).
4. From stmt 16 on: On Error Resume Next for the rest of the program (CODE, verified in msvbvm60.dll).
5. Voice: the first token in the SAPI voice list (GetVoices("", "").Item(0)), not necessarily the Windows default voice (CODE). Rate: read and written back unchanged, kept as the base rate. Volume 90 (CODE).
6. Pan table set (5.5); wav count n (5.2); stationary-pan divisor x (5.5).
7. Says " My Brain  By Jim Kitchen. " and waits until spoken (CODE). Then the main menu.
Nothing else is spoken or played at startup (CODE). Clone startup attribution: 17.

### 3.2 Main menu (stmt 51-67)
1. Stop all nine sound buffers (CODE; errors for empty slots ignored).
2. Say " Press a number from one to nine, or the escape key to exit. " async (CODE).
3. getkey: wait for a key; the key stops the prompt at once (CODE).
4. Escape: exit sequence (3.5), nothing spoken first (CODE).
5. Any other key: its character LCase(Chr(KeyCode)) is spoken and the program waits until spoken (CODE; what voices say per key: 8.2).
6. choice = Val(character). If choice < 1 or > 9: back to step 1 (CODE). Otherwise: panning menu.

### 3.3 Panning menu (stmt 70-115)
1. clk, wait 0.2 s, clk (discards keys pressed during the echo, 8.4); mode = 1; say " Select. " async (CODE).
2. Announce the mode name async, queued after current speech: 1 "no panning", 2 "stationary panning", 3 "semi random panning", 4 "totally random panning" (CODE).
3. getkey (stops speech at once) (CODE).
4. Escape: exit sequence (3.5); the program ends from here, it does not return to the main menu (CODE).
5. Enter (13): playback (3.4) with the current mode (CODE).
6. Up arrow (38): mode - 1, 0 wraps to 4; wait 0.2 s; back to step 2, no " Select. " (CODE).
7. Down arrow (40): mode + 1, 5 wraps to 1; wait 0.2 s; back to step 2 (CODE).
8. Any other key: quick key echo (8.3), then a jump to stmt 72 (the 0.2 s wait of step 1, skipping its first clk), then clk, mode = 1, " Select. " again (CODE). No audible difference from a full restart of step 1.

### 3.4 Playback (stmt 118-485)
1. Pan table entry 6 reset to 0 (undoes mode 4's last random value) (CODE).
2. clk; say " Press the space bar to stop. " and wait (CODE).
3. Randomize Timer (CODE).
4. Loop: DoEvents (stmt 123), then slot 1, then slots 2 to choice, then repeat (CODE). Each slot as in 5.4; every slot visit ends with DoEvents (stmt 161 for slot 1) (CODE).
5. Right after a slot starts a new sound, if the key code text is not empty: back to the main menu (3.2), which stops all sounds (CODE: stmt 157). Any key stops playback, not only space; Escape here only returns to the main menu (CODE). Keys are recorded at every DoEvents but acted on only after the next sound start (CODE); delay: 10.4.

### 3.5 Exit sequence (stmt 527-556)
1. Release all nine buffers (CODE).
2. g = LCase(Dir("gamemenu.exe")), searched in the current folder, not the program folder (CODE).
3. If g is not "gamemenu.exe": say " exiting program " and wait (CODE).
4. Release DirectX, DirectSound and the voice (Voice = Nothing) (CODE).
5. If found: Shell "gamemenu.exe" with window style 3 (maximized, focus), then End. Nothing spoken (CODE).
6. If not found: Beep, wait 0.1 s, Beep, wait 0.1 s; then the program tries to say "Sorry, but I could not find the Kitchensinc game menu program." but the voice is already released, so under On Error Resume Next nothing is spoken (CODE: order of stmt 543 and 552; INFERRED: a WithEvents variable cannot auto-create, so the call fails silently). Wait 0.2 s, End (CODE).
Heard: " exiting program ", two beeps, silence. Clone speaks the message (17, owner decision).
Details without audible effect (CODE): stmt 545 and 554 set Voice = Nothing again; stmt 540 clears an unused local. Shell's process creation searches the program's own folder before the current folder (INFERRED from Windows CreateProcess rules), so with two different gamemenu.exe files the one started may not be the one Dir found; the clone looks only next to Brain (17).

## 4. Menus
- Main menu: keys 1-9 on the main keyboard row (choice), Escape (exit). Shift with a digit still gives the digit (Shift unused, CODE), but the Shift key's own KeyDown arrives first and counts as an invalid key (silent echo, prompt restarts) (CODE plus 8.1). Numpad digits do not work: KeyDown codes 96-105 give "`" and "a" to "i", Val = 0 (CODE formula; key codes from Windows).
- Panning menu: Up and Down arrows (cycle 4 modes, wrap), Enter (start), Escape (end program), other keys (echo, restart at mode 1).
- Playback: any key returns to the main menu.
- No visible menus or controls (CODE).

## 5. Mechanics
### 5.1 Slots
Nine sound slots, one DirectSound buffer each; choice (1-9) = number of active slots (CODE).
### 5.2 Wav pool
n = 1 + number of further matches after the first Dir("brain*.wav") result, so n = number of files matching brain*.wav in the current folder, or 1 if none (CODE; none case INFERRED from Resume Next). Counted once at startup (CODE). Wavs are picked by number 1..n and loaded from App.Path & "\brain" & number & ".wav" (CODE). The readme asks for consecutive numbering; a gap or a non-numbered match (for example "brainx.wav") makes some picks fail silently (15).
### 5.3 Pitch
For each new sound: freq = the wav's own sample rate (GetFrequency) + r * 100 Hz, r = Int(Rnd * 40) - 20, a whole number -20..19, redrawn while 0 (CODE, stmt 144-145). For the shipped set: 3,500 Hz (5500 - 2000) to 46,000 Hz (44100 + 1900), inside DirectSound's 100-200,000 Hz, so SetFrequency never fails (CODE plus documented limits). Pitch factor 0.636 to 1.345, never 1. Real length after pitch: 2.8 ms (brain8 at 46,000 Hz) to 324 ms (brain36 at 3,564 Hz) (computed, P4).
### 5.4 One slot k per loop pass (stmt 124-161 for k = 1)
1. If Timer > endTime(k): stop and release the slot's buffer, start a new sound (step 3). endTime starts Empty (0), so the first pass always starts a sound (CODE). endTime is never reset between playbacks; a later playback still starts new sounds at once because the time spent in the menus exceeds the longest end-time lead (about 0.67 s for the shipped set) (INFERRED from the formula).
2. Else if the buffer is playing (stmt 129, GetStatus = 1): skip to step 5. Else: stop, release, start a new sound (CODE).
3. New sound, one statement each: number = Int(n * Rnd) + 1; name = "brain" & Trim(Str(number)) & ".wav"; size = FileLen(name) (current folder, whole file in bytes); buffer = CreateSoundBufferFromFile(App.Path & "\" & name, description); SetCurrentPosition 0 and SetVolume 0 (full); freq = GetFrequency (stmt 142); r drawn (5.3); freq = freq + r * 100 (stmt 149); q = size / freq (stmt 150); q = q * 2 (stmt 151); SetFrequency(freq) (stmt 152); endTime(k) = Timer + q (stmt 153); pan index (GoSub, 5.5); SetPan(pan table(index)); Play(0), one shot (CODE). number, size, freq and q are single variables shared by all nine slots (CODE: the nine slot copies differ only in buffer, index and threshold).
4. If the key code text is not empty: main menu (CODE, stmt 157).
5. DoEvents; if choice < k + 1: back to the loop top; else the next slot (CODE).
Failure path (bad, empty or missing wav, CODE: statement table plus Resume Next): every failing statement is skipped and its variable keeps its previous value. No buffer is made, so nothing plays. freq keeps the last value any slot got from GetFrequency and still gets + r * 100, so repeated failures walk it by r * 100 each time (before any success it starts Empty, 0). A missing file also keeps the previous size. If freq is 0, q keeps its previous value (division error). endTime(k) = Timer + 2 * size / freq from these values. On the next passes GetStatus fails on the empty buffer and Resume Next continues at statement table entry 130 (0x405e98), the skip branch, so the slot stays silent until Timer > endTime(k), then tries another number. The silence is usually about one or two sound lengths, none if freq went negative, and can be long (seconds) if freq is small, for example when the very first pick of the run fails.
Cut-off: over all 42 files at both pitch extremes endTime is at least 2.04 times the real length (8-bit just over 2x, 16-bit over 4x), so it never ends a sound early; each slot starts its next sound when the buffer reports stopped (computed, P4). The same formula holds for any added PCM file (INFERRED). Within a slot the old buffer is stopped and released before the next starts, so a slot never overlaps itself; different slots may play the same wav at once (CODE).
### 5.5 Panning (GoSub stmt 491-516)
Pan table (DirectSound pan, hundredths of a dB, negative = left): index 1..11 = -750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750; index 0 and 12 never set (Empty, used as 0 = center) (CODE).
- Mode 1 no panning: index 6 (center) (CODE).
- Mode 2 stationary: index = Int(number / x). Startup: x = 1, then repeat x = x + 0.1 until Int(n / x) <= 11, in doubles (CODE). For 42 wavs x = 3.5000000000000018 (computed twice, P3 and P4): wavs 1-3 index 0 (center, a quirk), 4-7 index 1, 8-10 index 2, 11-14 index 3, 15-17 index 4, 18-21 index 5, 22-24 index 6, 25-28 index 7, 29-31 index 8, 32-35 index 9, 36-38 index 10, 39-42 index 11 (per-wav table in WAV_EVENT_MAP). By count (exact doubles, computed P5): x = 1.1 for every n up to 13 (the first value tested is 1.1); n = 14: 1.2000000000000002; 22: 1.9000000000000008; 41 and 42: 3.500000000000002; 43: 3.6000000000000023; 59: 4.999999999999999; 60: 5.099999999999999. Number 1 always gets index 0 (center). With n up to 12 the top index is 10, so +750 is unused; index 11 appears from n = 13 (computed). These are P8 test cases.
- Mode 3 semi random: index = Int(Rnd * 11) + 1, redrawn while equal to any of the last three indexes picked in this mode; history shared by all slots and kept for the whole run (CODE: three Form_Load locals, never reset).
- Mode 4 totally random: index 6, with pan table(6) = (Int(Rnd * 200) - 100) * 10, so -1000 to +990 in steps of 10 (CODE).
- Loudness: DirectSound pan p attenuates the opposite channel by |p|/100 dB and leaves the near channel at full level (documented). Modes 2 and 3 differ by at most 7.5 dB between the ears, mode 4 by at most 10 dB. Clone: for p > 0 left gain 10^(-p/2000), right gain 1; mirror for p < 0.

## 6. Randomness and seeding (5.5)
Randomize Timer at each playback start (CODE, stmt 121), so each Enter re-seeds from the clock. Rnd calls per new sound, in order: wav number; pitch (repeated while r = 0); pan in modes 3 (repeated while in the last three) and 4 (CODE). The clone uses its own generator with the same uniform ranges: wav number over 1..n; pitch offset over the 39 values -20..-1 and 1..19; mode 3 over the 11 positions not among the last 3 used; mode 4 over 200 values. Exact sequences cannot be compared (clock seed); tests check ranges and distributions. VB6 Rnd algorithm for reference: next = (prev * 1140671485 + 12820163) mod 2^24.

## 7. Timing
- dy waits (busy loop with DoEvents): 0.2 s after a valid digit (between the two clk calls) and after each Up or Down; 0.1 s after each exit beep; 0.2 s before End when gamemenu.exe is missing (CODE).
- Waiting speech (say): title at startup, main menu key echo, " Press the space bar to stop. ", " exiting program " (CODE). All other speech async (CODE).
- Playback loop: no fixed tick, runs flat out with DoEvents (CODE; INFERRED: one CPU core fully used). Gap between sounds in a slot: one loop pass.
- Key response in playback: up to one sound length with one slot (up to 324 ms), shorter with more slots (INFERRED from 5.4).
- Timer wraps at midnight: a wait crossing midnight never ends and end times stop working (INFERRED from VB Timer behavior). Not copied (17).

## 8. Input
### 8.1 Key capture
Form_KeyDown stores the key code text CStr(KeyCode) and the key character LCase(Chr(KeyCode)); Shift is unused; it never speaks (CODE). Every key that raises KeyDown counts, including Shift, Ctrl and Alt alone (INFERRED: VB raises KeyDown for them). Keys are read only by polling: getkey (clk, then DoEvents until the key code text is not empty, then stop speech) and the playback check (CODE). clk sets the key code text to "", DoEvents, sets the key character to "", DoEvents, in that order (CODE). Held keys repeat KeyDown; the last one processed wins (INFERRED). Alt alone and F10 also put a Windows form with a system menu into menu mode on release, so the next arrow key or Enter may go to the system menu instead of KeyDown (INFERRED from standard Windows behavior; the original was not run). The clone treats Alt and F10 as plain keys and does not copy the system-menu side effect (DECISIONS). Chr uses the Windows ANSI code page (1252 on English Windows) (CODE: Form_KeyDown calls rtcBstrFromAnsi, then rtcLowerCaseBstr; INFERRED for other locales).
### 8.2 Main menu key echo: what is spoken
The voice gets LCase(Chr(KeyCode)) with Speak flags 0 (CODE). P5 test on this PC (`games/tools/sapi_key_echo.ps1`, 32-bit SAPI, output `work/p5_key_echo.tsv`), voice 0 FlexVoice2 Bill and Microsoft David Desktop:
- Silent on both voices: Backspace, Tab, Enter, Shift, Ctrl, Alt, Pause, Caps Lock, Space, Page Up ("!"), Page Down ('"'), Right arrow ("'"), Down arrow ("("), Insert ("-"), Delete ("."), Windows ("["), Applications ("]"), Numpad 0 ("`"), F12 ("{"), Num Lock, Scroll Lock, Equals ("»"), Slash ("¿"), Quote ("þ") (test).
- Spoken on both voices: digits, letters; End "#" (David: "hash"), Home "$" ("dollar"), Left arrow "%" ("percent"), Up arrow "&" ("and"); Numpad 1-9 as letters a-i; Numpad * + - . / as j k m n o; F1-F11 as letters p-z (test; words recognized by the Windows recognizer for David; FlexVoice speaks them, recognizer could not name them).
- Voice-dependent: Semicolon "º", Comma "¼", Minus "½", Period "¾", Grave "à", brackets and backslash "û" "ü" "ý": silent on FlexVoice, spoken by David ("degree", "one fourth", "one half", "three fourths", "ah", "you", "you", "why") (test).
The clone sends the same characters (code page 1252 mapping) to the same SAPI voice with the same flags, so the result is the same as the original's on any voice (CODE plus test; OPEN_QUESTIONS 24 answered).
### 8.3 Quick key echo (saykey, panning menu other keys)
Rate = base rate + 5, stop speech, speak the character async unless the key is F1 (112), then rate = base rate at once (CODE). Tests (P3 64-bit and P5 32-bit SAPI, voice 0, a ten-word sentence): 32-bit normal rate 3.73 s, rate +5 then reset at once 3.69 s, rate +5 throughout 2.14 s. The reset applies almost at once, so the echo sounds at about the normal rate (INFERRED from the tests, OPEN_QUESTIONS 16). Rate out of range: SAPI accepted Rate = 11, 15 and -11 without an error (P5 test, 32-bit, voice 0), so saykey never fails and always echoes, whatever the base rate (test). Clone: speak the echo at the base rate; the clone's rate setting stays within -10..10.
### 8.4 Keys pressed during waiting speech
P5 test: SAPI waiting speech (Speak flags 0, 32-bit, STA, volume 0) does not dispatch window messages while it speaks; a posted message ran only after Speak returned (test, without an event sink; INFERRED the same with Brain's WithEvents voice). So a key pressed during waiting speech is processed at the next DoEvents (INFERRED from the test plus CODE order):
- During the startup title: the main menu prompt starts, then getkey's clk processes the key: the key code text is set, then the key character is cleared. getkey returns at once and cuts the prompt. Escape: exit. Any other key: an empty echo (nothing spoken), Val("") = 0, prompt again.
- During the main menu echo: a valid digit goes to the panning menu, whose clk, 0.2 s wait, clk discard the key. An invalid one restarts the main menu, where the key acts as above (Escape exits; others restart the prompt silently).
- During " Press the space bar to stop. ": clk ran before the speech, so the key is processed at stmt 123 with both fields set; slot 1 starts its first sound and playback stops at once at stmt 157 (OPEN_QUESTIONS 25).
- During " exiting program ": no key is read again.
Keys during the 0.2 s waits (CODE: dy runs DoEvents, then getkey's clk clears): a key pressed during the wait after Up or Down, or after a valid digit, is recorded and then wiped, so it is lost. Two Down presses within 0.2 s move only one step.
The 8.4 test ran without an event sink while Brain's voice is WithEvents; the conclusion stays INFERRED and is checked against the clone's behavior in P8, not against the original (not run).
Clone: keep a key code field and a key character field, cleared in the original order, buffer keys typed during waiting speech and deliver them after it ends, and keep the 0.2 s waits with the same discard, so all these cases come out the same (DECISIONS, P8 tests).
### 8.5 Other input edge cases
- Ctrl or Alt with a digit also arrives as KeyDown 49-57 (INFERRED); the modifier's own KeyDown arrives first (8.1). Clone accepts digits whatever the modifiers.
- Window not focused: keys reach only the focused form, sounds keep playing (INFERRED).
- A second copy of Brain: no check (CODE); both play (INFERRED).

## 9. Text and speech
Exact texts and their events: `spec/STRINGS.md` (S01-S20). All speech goes through the SAPI 5 voice from 3.1, never the screen reader (CODE: no screen reader API). Waiting and async speech: 7. The caption may be read by the screen reader when the window gets focus (INFERRED).

## 10. Sound
### 10.1 Wavs
Every wav: `spec/WAV_EVENT_MAP.md`. No wav has its own event; all are one random pool (CODE). No unreferenced wav, no missing referenced wav (CODE). DirectSound buffers, flags &HE0, full volume, per-sound pitch (5.3) and pan (5.5), one shot, up to nine at once (CODE). What each wav sounds like is not needed for the logic; the owner hears them in the clone (P7.6).
### 10.2 File notes (P4 analysis)
brain7 is 49 ms of pure silence; brain8 is only 3 ms (heard as a click); brain3, 13, 21, 28, 31, 42 end with 35-43 ms of silence; brain14 starts with 50 ms of silence; the largest DC offsets are brain27 and brain40 (about 6.6 percent of full scale, 8-bit); every 16-bit file is under 1.1 percent (CODE, `work/p4_wav_checks.txt`, recomputed P5). The clone plays files unchanged.
### 10.3 Beeps
Beep is rtcBeep, which calls MessageBeep(0), the Windows default sound, not a PC speaker tone (CODE: this PC's msvbvm60.dll). Twice, 0.1 s apart, only on exit when gamemenu.exe is missing (CODE).
### 10.4 No music, no PC speaker tones, no gaps
No music, no SOUND or PLAY tones (CODE). Every silent event and its decision (all stay silent): `spec/SOUND_DESIGN.md`.

## 11. Data and customizable content
- Wav set: brain1.wav .. brainN.wav in the program folder; brain.txt invites players to replace or add wavs (CODE, readme). No upper limit in code; stationary panning spreads any count over the positions (5.5).
- Fixed tables: pan table, four mode names, nine slots, pitch range (CODE).
- Inventory per 7.9: `spec/CUSTOMIZABLE_CONTENT.md`: one list (the sound set); constants as settings; no names.

## 12. Files
- Reads: brain*.wav (Dir and FileLen in the current folder; loading from the program folder); gamemenu.exe presence (current folder) (CODE).
- Writes: nothing (CODE: no Open, no registry, no INI).
- Missing, empty or damaged wav: no message; the slot gets no buffer and stays silent until its end time computed from stale values, then tries another number (failure path in 5.4, CODE); the loop never hangs. With every wav bad the loop runs silently until a key (CODE plus Resume Next). The corrupt-wave message is never shown (15).
- brain.txt and gamemenu.exe are never opened (CODE).

## 13. Accessories and helpers
- brain.txt: readme by Jim Kitchen (his email address, phone number and town are left out of this public document: he died in 2015): keep wavs numbered consecutively 1..42, brain.exe may sit in any folder with its own wav set, send him cool sound sets, nobrain.bat removes the program (nobrain.bat is missing from this copy; not needed, OPEN_QUESTIONS 5).
- gamemenu.exe: the Kitchensinc game menu, started on exit if present (3.5). Not part of this folder.
- dx8vb.dll and SAPI 5: system components the original needs (2).

## 14. Loops, conditions, procedures
All 9 procedures done: `spec/PROCEDURE_INDEX.md` (procedure table, Form_Load statement map, runtime facts, DirectX methods). Main loops: main menu (3.2), panning menu (3.3), playback (3.4, 5.4), getkey and dy waits (7, 8.1).

## 15. Errors and edge cases
- No SAPI 5 voices: message box, OK only: "Sorry but I couldn't find any voices to use", Chr(13), "Please contact Jim Kitchen"; title App.Title = "brain" (CODE: VB header strings; App.Title fallback to the project name INFERRED); then the exit sequence with no error handler active, so a speech failure there ends with a VB run-time error box (INFERRED). Clone: speaks the same text through the screen reader if one is running, shows the same message box (title "Brain"), and exits cleanly with no error box; tested in P8.3 (DECISIONS).
- dx8vb.dll missing or no sound device: unhandled VB run-time error at startup, program ends (INFERRED; stmt 5-7 run before On Error).
- Corrupt-wave message box ("Sorry but one or more of the wave files seem to be corrupt", Chr(13), "Please contact Jim Kitchen"): present but unreachable (CODE).
- All errors after stmt 16 are skipped silently (CODE).
- Current folder different from the program folder: count, FileLen and the gamemenu check use the current folder, loading uses the program folder; sounds may be cut off at once or the count may be wrong (INFERRED). Clone uses one folder (17).
- Invalid main menu keys: echoed (8.2), prompt repeats; digit 0 spoken "0", prompt repeats (CODE). Numpad digits invalid (4).
- Escape during playback returns to the main menu; a second Escape exits (CODE).
- Keys during waiting speech: 8.4. Midnight: 7.

## 16. Child games and links
No child games. On exit Brain starts gamemenu.exe (the Kitchensinc game menu) if it is in the current folder; that menu is its own project (rule 0.2), not cloned here.

## 17. Clone notes
Must stay exact: all spoken texts, their order and waiting or async behavior; keys per state; the four modes with their pan rules and values; the pitch rule; nine slots; voice volume 90 and the first SAPI voice by default; the 0.2 s and 0.1 s waits; the two exit beeps; the key code and key character fields and their clear order (8.4); the key echo characters (8.2, code page 1252).
Owner decisions (OPEN_QUESTIONS 17, DECISIONS.md): speak "Sorry, but I could not find the Kitchensinc game menu program." after " exiting program " and the two beeps; bad wavs stay silent (log only); numpad digits accepted in the main menu; a clock that never resets (no midnight hang); first SAPI voice at volume 90 by default, with voice and rate settings; one folder for counting, checking and loading wavs; start gamemenu.exe on exit if it is next to Brain. The original wavs ship with the clone (Jim Kitchen's permission, DECISIONS.md).
Claude decisions (DECISIONS.md): no generated sounds; exit beep = system default sound (sound ID beep_exit, played twice) with a generated blip only as fallback; wav pool brain1..brainN, N = highest consecutive number present, draws only from existing files; a pick that fails to load follows the original's failure path exactly (5.4: shared variables, stale end time), logged once per file; pitch range, voice, rate (-10..10), volume as settings; no editable wording file in v1; keys checked at least every 10 ms in playback and the loop sleeps 1-2 ms per pass (same function, no full CPU; gap at most 2 ms); a key in playback stops sounds within 10 ms instead of after the next sound start, but a key typed ahead during " Press the space bar to stop. " still lets slot 1's first sound start before stopping (8.4); pan gains as 5.5; the cut-off is kept exactly as 5.4 (with real end of sound as the normal trigger); quick echo at the base rate; keys during waiting speech and the 0.2 s waits handled as 8.4; Alt and F10 plain keys; no-voices case as 15; wav count rechecked at start and after a sound-folder reload.
Added functions (About, settings for voice, rate, volume and pitch range, sound-folder reload): keys and menus are designed in P7.4 under one rule: digits 1-9, Escape, Enter, Up and Down keep their original meaning in every state, and new functions use only keys that in the original merely gave an invalid echo (for example F-keys in the main menu); each such change of a key's meaning is listed in the README and DECISIONS (accepted-default, P7.4 finalizes, P8 playtest confirms).
Required additions: attribution per rule 0.5 (startup speech once, About item, readme, source headers), with the note on Jim Kitchen.

## 18. Checklist results (5.4)
Audit S5.2, 2026-10-12: fresh reviewer (a subagent that had not seen the work), read-only, against the disassembly. 18 spot checks: 17 confirmed, 1 wrong (bad-wav path, fixed in 5.4). 16 defects found, all fixed in S5.2 (2 blockers, 7 should-fix, 7 minor). Remaining GUESS or UNKNOWN tags: none.
- Strings tied to events, menus, choices: answered, STRINGS S01-S20, 9.
- Wavs tied to events, unreferenced files: answered, 10.1 and WAV_EVENT_MAP (one random pool; none unreferenced, none missing).
- PC speaker tones, beeps, music: answered, 10.3-10.4 (two MessageBeep(0); no music, no tones).
- Silent events and their decision: answered, SOUND_DESIGN (all stay silent).
- Menus and choices with exact keys: answered, 3.2, 3.3, 4, 8.
- Loops, conditions, procedures done: answered, PROCEDURE_INDEX (9 of 9 done), 14.
- Mechanics, formulas, constants, tables, random behavior: answered, 5 and 6.
- Maps, levels, rosters, tables: not applicable (a sound toy with no game data); fixed tables in 5.5 and 11.
- Customizable lists with original limits: answered, 11 and CUSTOMIZABLE_CONTENT L1, C1-C6.
- Files, data files, formats: answered, 12 (reads wavs only, writes nothing).
- Text files and everything else in the folder: answered, 2 and 13 (brain.txt; nobrain.bat missing and not needed).
- Accessories and helpers: answered, 13.
- Events and their order: answered, 3.
- Timing: answered, 7 and 8.4.
- Error and bad-input behavior: answered, 8, 15.
- Own files missing, empty, corrupt: answered, 5.4 failure path, 12 (no recreation, no defaults, no message).
- Startup and shutdown, what is spoken or played: answered, 3.1, 3.5.
- Child games: answered, 16 (none; gamemenu.exe is its own project).
Remaining INFERRED items with weak or untestable evidence, each with its default and test: KeyPreview as the property set from "true" (no effect either way); App.Title "brain" (the clone uses "Brain"); every key raises KeyDown, Alt and F10 menu mode (clone: plain keys, P8); waiting speech does not pump messages with a WithEvents voice (clone follows 8.4, P8); DirectSound flags and method names (strong, 3.1).

## 19. Open questions
`spec/OPEN_QUESTIONS.md`. Summary: 25 items; 21 answered, 3 accepted-default (22, 23, 25 confirmed in P8), 1 owner-needed but not blocking (18: where the saved copy of Jim Kitchen's permission email is kept; needed before P11 publishes the wavs).
