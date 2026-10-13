# PROCEDURE_INDEX: Brain

P3 S3.1, 2026-10-12. All 9 procedures of brain.exe read. Status per procedure: unread, partial, done.
Sources: Ghidra 12.1.4 headless export (`work/ghidra_out/`, not committed: decompiled output is reference only, never clone code, section 10), condensed listing made with `games/tools/vb6_asm_condense.py`, VB6 tables read with Python (pefile, capstone).
Behavior is described in plain words here and in `GAME_SPEC.md`; no decompiled code is copied.

## How the procedures were found (CODE)
- Form1 method table (vtable) at 0x40226c, 9 entries, in this order: clk, say, say2, stopspeech, dy, saykey, 0x403a80, 0x403980, 0x403b40. Each entry points to a 13-byte thunk at 0x4024af + 13 * n that jumps to the procedure.
- Form1 event table starts at 0x4022b4. Only two slots are filled: slot 6 -> thunk 0x402517 -> 0x403b40, slot 15 -> thunk 0x4024fd -> 0x403980.
- Calls between procedures go through the form's own interface: offset 0x734 clk, 0x738 say, 0x73c say2, 0x740 stopspeech, 0x744 dy, 0x748 saykey, 0x74c getkey; 0x758 get Voice, 0x760 set Voice (CODE: vtable order plus call sites).
- The method name table lists "getkey" but no address; 0x403a80 is getkey by behavior (clears the key, waits for a key, stops speech) and by its call offset 0x74c (INFERRED, strong).
- Voice is a form-level `WithEvents` SpVoice variable: its accessors call the runtime's GetMemEvent, PutMemEvent, SetMemEvent (ord319-321) (CODE). A WithEvents variable cannot auto-create itself, so after it is set to Nothing every speech call fails (INFERRED from VB6 rules).

## Form-level variables (CODE: offsets inside the form object, "Me")
- +0x34 key code text: the last KeyDown KeyCode as a decimal string ("27", "13", "49"), empty when no key is waiting.
- +0x38 key character: LCase(Chr(KeyCode)), for example "1", "a", "&" for the up arrow (38).
- +0x40 speech rate (Variant), read from the voice at startup.
- +0x50 voice index (Variant), always 0.
- +0x60 voice count minus 1 (Variant); written, never used after the zero check.
- +0x70 DirectX8 object, +0x74 DirectSound8 object.
- +0x78, 0x7c, 0x80, 0x84, 0x88, 0x8c, 0x90, 0x94, 0x98: nine DirectSound secondary buffers, one per playback slot 1-9.
- +0x9c buffer description (DSBUFFERDESC) passed to every buffer creation; +0xa0 set to &HE0 at startup (INFERRED: the lFlags field = control frequency 0x20 + control pan 0x40 + control volume 0x80).

## Procedures

| address | name | role | status |
|---|---|---|---|
| 0x403380 | clk | clears key code text and key character (both to ""), DoEvents after each | done |
| 0x403400 | say(text) | Voice.Speak text, flags 0 (waits until spoken) | done |
| 0x4034d0 | say2(text) | Voice.Speak text, flags 1 (async, returns at once, queues after current speech) | done |
| 0x4035a0 | stopspeech | Voice.Speak "", flags 2 (purge: stops speech at once) | done |
| 0x403670 | dy(seconds) | busy wait: start = Timer, then DoEvents until Timer > start + seconds | done |
| 0x403770 | saykey | quick key echo: Voice.Rate = rate + 5, stop speech, if key code is not "112" (F1) speak the key character async, then Voice.Rate = rate | done |
| 0x403a80 | getkey | clk, then DoEvents until key code text is not empty, then stopspeech | done |
| 0x403980 | Form_KeyDown(KeyCode, Shift) | key code text = CStr(KeyCode); key character = LCase(Chr(KeyCode)); Shift unused; never speaks | done |
| 0x403b40 | Form_Load | the whole program: setup, main menu, panning menu, playback loop, exit; 558 statements | done |

Event names: 0x403980 takes three arguments (returns with `ret 0xc`: Me, KeyCode, Shift) and stores a key code, so it is Form_KeyDown (CODE: argument count; INFERRED: name, since KeyPress has one argument and only KeyDown and KeyUp have two). It compares against 112 (F1) and lowercases Chr(KeyCode), which only makes sense for KeyDown codes (letters arrive upper case). 0x403b40 takes no arguments (`ret 4`), fills event slot 6, and shows the form, sets the caption and creates all objects, so it is Form_Load (CODE: no arguments; INFERRED: name).

## Form_Load statement map (0x403b40)
Statement numbers are the VB statement counter the compiler writes before each source line (CODE). The procedure's statement address table (558 entries) is saved in `extracted/resources/stmt_table_403b40.txt`; it decides where On Error Resume Next continues.

| statements | address range | what it does | status |
|---|---|---|---|
| 1-4 | 0x403b95-0x403d97 | two local arrays (pan table 0..12, end times 0..10); Form1.Show; Caption " My Brain  By Jim Kitchen "; a Boolean form property set from "true" | done |
| 5-8 | 0x403d97-0x403f59 | New DirectX8; DirectSoundCreate(""); SetCooperativeLevel(Form1.hWnd, 2 = priority); buffer flags &HE0 | done |
| 9-12 | 0x403f59-0x4041fa | Set Voice = New SpVoice (twice); count = Voice.GetVoices("", "").Count; if 0 -> no-voices error (523) | done |
| 15-22 | 0x4041fa-0x404770 | count - 1; On Error Resume Next; voice index 0, rate 0; Voice.Voice = first voice token; rate = Voice.Rate; Voice.Rate = rate; Voice.Volume = 90 | done |
| 23-33 | 0x404770-0x404bb1 | pan table 1..11 = -750, -600, -450, -300, -150, 0, 150, 300, 450, 600, 750 | done |
| 34-41 | 0x404bb1-0x404cd7 | count wav files: n = 1, Dir("brain*.wav"), then n + 1 for each further Dir() match | done |
| 44-48 | 0x404cd7-0x404dc7 | stationary-pan divisor: x = 1; repeat x = x + 0.1 until Int(n / x) <= 11 | done |
| 49 | 0x404dc7 | say " My Brain  By Jim Kitchen. " (waits) | done |
| 51-67 | 0x404e3d-0x40538b | MAIN MENU: stop all 9 buffers; say2 menu prompt; getkey; Escape -> exit; say key character (waits); choice = Val(key character); if choice < 1 or > 9 -> main menu again | done |
| 70-115 | 0x40538b-0x405bb9 | PANNING MENU: clk, dy 0.2, clk, mode = 1, say2 " Select. "; announce mode (say2); getkey; Escape -> exit; Enter -> play; Up -> previous mode (wraps 1 to 4), dy 0.2, announce; Down -> next mode (wraps 4 to 1), dy 0.2, announce; other key -> saykey, restart panning menu at mode 1 | done |
| 118-123 | 0x405bb9-0x405d27 | PLAY START: pan table(6) = 0; clk; say " Press the space bar to stop. " (waits); Randomize Timer; loop top: DoEvents | done |
| 124-161 | 0x405d27-0x406783 | slot 1 (buffer +0x78, end time 1), see GAME_SPEC 5.4 | done |
| 162-485 | 0x406783-0x40be9b | slots 2-9, same code as slot 1 with their own buffer and end time; slot k runs only when choice >= k (CODE: normalized diff of all nine slots, only buffer, index and threshold differ) | done |
| 491-516 | 0x40be9b-0x40c276 | GoSub pan selection by mode, returns pan index (local L74), see GAME_SPEC 5.5 | done |
| 517-520 | 0x40c276-0x40c3bf | corrupt-wave message box, then exit. Unreachable: no jump leads here and the procedure has no On Error GoTo label (CODE) | done (dead code) |
| 523-525 | 0x40c3bf-0x40c4e9 | no-voices message box: "Sorry but I couldn't find any voices to use" + Chr(13) + "Please contact Jim Kitchen", OK only; falls into exit | done |
| 527-556 | 0x40c4e9-0x40ccbd | EXIT: release buffers; look for gamemenu.exe; speak or launch; beeps; End, see GAME_SPEC 3.5 | done |
| 557 | 0x40ccbd | after End (not reached): App object call, cleanup | done |

## Runtime facts verified in msvbvm60.dll (CODE, this PC's C:\Windows\SysWOW64\msvbvm60.dll)
- __vbaOnError stores its argument in the procedure's error-mode slot. The exception handler treats -1 as "continue at statement table entry N+1" (Resume Next), -2 as "entry N" (Resume), and a positive value as an index into the procedure's label table. Brain passes -1 and its label table pointer is 0, so Form_Load runs under On Error Resume Next from statement 16 to the end.
- VB comparison helpers (__vbaVarTstGt and so on) take the left operand as the first value pushed (CODE: checked in dy, where only that order makes the delay work).

## DirectX 8 for Visual Basic methods used (by vtable offset)
dx8vb.dll is not installed on this PC, so the type library could not be read. Names below come from argument use (INFERRED unless marked).
- DirectX8 +0xc DirectSoundCreate(guid string "") -> DirectSound8.
- DirectSound8 +0x18 CreateSoundBufferFromFile(path, desc) -> buffer (path argument is App.Path & "\" & wav name: CODE); +0x28 SetCooperativeLevel(hWnd, 2).
- Buffer (DirectSoundSecondaryBuffer8, IID 9F76FB01-...): +0x2c GetFrequency (result + random offset is written back with +0x50); +0x30 GetStatus (compared with 1 = playing); +0x40 Play(0) (last call before the key check); +0x44 (0) and +0x48 (0) right after creation: SetCurrentPosition 0 and SetVolume 0 (full volume), in an order that cannot change behavior; +0x4c SetPan(pan table value); +0x50 SetFrequency; +0x54 Stop.
- Interface IDs in the file (CODE, registry lookup and known values): DirectX8 class E7FF1300-96A5-11D3-AC85-00C04FC2C602, interface E7FF1301-...; DirectSound8 9F76FB00-8E92-11D1-8808-00C04FC2C603; secondary buffer 9F76FB01-...; SpVoice class 96749377-3391-11D2-9EE3-00C04F797396; ISpeechVoice 269316D8-...; ISpeechObjectTokens 9285B776-....
