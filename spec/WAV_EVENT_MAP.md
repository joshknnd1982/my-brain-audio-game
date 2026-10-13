# WAV_EVENT_MAP: Brain

Status: final for GAME_SPEC 1.0 (P5 S5.2, 2026-10-12). Events from P3 code recovery, file facts re-checked in P4. What each wav sounds like is not needed for the logic (no wav has its own event); the owner hears them in the clone (P7.6).

Clone location and IDs (P7 S7.2): the 42 wavs ship byte-identical in `clone/assets/sounds/brain1.wav .. brain42.wav`; sound ID brainNN = wav number NN (brain01 .. brain42); a player's file with the same number in the per-user sounds folder replaces it (DECISIONS P7 S7.2).

How wavs are used (CODE, `spec/GAME_SPEC.md` 5.2-5.5): no wav is tied to an event. During playback every active slot (1 to 9 at once, the digit chosen in the main menu) picks a random number 1..n, n = number of files matching brain*.wav, and plays "brain" & number & ".wav" from the program folder through a DirectSound buffer: one shot, full volume, pitch = the file's own sample rate + r * 100 Hz (r = -20..19, never 0), pan from the chosen mode. A slot starts its next random wav as soon as the last one ends (or at its cut-off time). The same wav can play in several slots at once (CODE: no check).

Playback mechanism (corrects P2): DirectX 8 for Visual Basic (dx8vb.dll) DirectSound, not SAPI (CODE, PROCEDURE_INDEX). Buffer flags &HE0: frequency, pan and volume control (INFERRED meaning). Panning is real DirectSound pan in hundredths of a dB.

Pan per mode (CODE): no panning = 0 (center); stationary = fixed per wav number (last column below, for the original 42 files; x = 3.5000000000000018); semi random = one of the 11 table values -750..750, not one of the last three positions used; totally random = (Int(Rnd * 200) - 100) * 10, -1000..990.

| ID | kind | file | bytes | format | event | code location | loop | confidence |
|---|---|---|---|---|---|---|---|---|
| brain01 | ORIGINAL-WAV | brain1.wav | 1000 | 11025 Hz, 8-bit, mono, 80 ms | random pool of every playback slot; stationary pan index 0 = 0 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain02 | ORIGINAL-WAV | brain2.wav | 245 | 11025 Hz, 8-bit, mono, 18 ms | random pool of every playback slot; stationary pan index 0 = 0 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain03 | ORIGINAL-WAV | brain3.wav | 1358 | 22222 Hz, 8-bit, mono, 59 ms | random pool of every playback slot; stationary pan index 0 = 0 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain04 | ORIGINAL-WAV | brain4.wav | 352 | 5500 Hz, 8-bit, mono, 56 ms | random pool of every playback slot; stationary pan index 1 = -750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain05 | ORIGINAL-WAV | brain5.wav | 1398 | 22222 Hz, 8-bit, mono, 61 ms | random pool of every playback slot; stationary pan index 1 = -750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain06 | ORIGINAL-WAV | brain6.wav | 800 | 22222 Hz, 8-bit, mono, 34 ms | random pool of every playback slot; stationary pan index 1 = -750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain07 | ORIGINAL-WAV | brain7.wav | 588 | 10989 Hz, 8-bit, mono, 49 ms | random pool of every playback slot; stationary pan index 1 = -750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE; silent file |
| brain08 | ORIGINAL-WAV | brain8.wav | 356 | 44100 Hz, 16-bit, mono, 3 ms | random pool of every playback slot; stationary pan index 2 = -600 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain09 | ORIGINAL-WAV | brain9.wav | 1520 | 11025 Hz, 8-bit, mono, 125 ms | random pool of every playback slot; stationary pan index 2 = -600 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain10 | ORIGINAL-WAV | brain10.wav | 1046 | 11025 Hz, 8-bit, mono, 82 ms | random pool of every playback slot; stationary pan index 2 = -600 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain11 | ORIGINAL-WAV | brain11.wav | 1290 | 11025 Hz, 8-bit, mono, 104 ms | random pool of every playback slot; stationary pan index 3 = -450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain12 | ORIGINAL-WAV | brain12.wav | 1226 | 11025 Hz, 8-bit, mono, 99 ms | random pool of every playback slot; stationary pan index 3 = -450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain13 | ORIGINAL-WAV | brain13.wav | 1388 | 12048 Hz, 8-bit, mono, 112 ms | random pool of every playback slot; stationary pan index 3 = -450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain14 | ORIGINAL-WAV | brain14.wav | 886 | 11025 Hz, 8-bit, mono, 70 ms | random pool of every playback slot; stationary pan index 3 = -450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain15 | ORIGINAL-WAV | brain15.wav | 200 | 11025 Hz, 8-bit, mono, 14 ms | random pool of every playback slot; stationary pan index 4 = -300 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain16 | ORIGINAL-WAV | brain16.wav | 464 | 11111 Hz, 8-bit, mono, 38 ms | random pool of every playback slot; stationary pan index 4 = -300 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain17 | ORIGINAL-WAV | brain17.wav | 404 | 11025 Hz, 8-bit, mono, 33 ms | random pool of every playback slot; stationary pan index 4 = -300 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain18 | ORIGINAL-WAV | brain18.wav | 860 | 11025 Hz, 8-bit, mono, 69 ms | random pool of every playback slot; stationary pan index 5 = -150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain19 | ORIGINAL-WAV | brain19.wav | 2346 | 11025 Hz, 8-bit, mono, 202 ms | random pool of every playback slot; stationary pan index 5 = -150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain20 | ORIGINAL-WAV | brain20.wav | 2876 | 11025 Hz, 8-bit, mono, 250 ms | random pool of every playback slot; stationary pan index 5 = -150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain21 | ORIGINAL-WAV | brain21.wav | 10804 | 44100 Hz, 16-bit, mono, 121 ms | random pool of every playback slot; stationary pan index 5 = -150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain22 | ORIGINAL-WAV | brain22.wav | 7814 | 44100 Hz, 16-bit, mono, 87 ms | random pool of every playback slot; stationary pan index 6 = 0 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain23 | ORIGINAL-WAV | brain23.wav | 2326 | 11000 Hz, 8-bit, mono, 201 ms | random pool of every playback slot; stationary pan index 6 = 0 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain24 | ORIGINAL-WAV | brain24.wav | 2100 | 8363 Hz, 8-bit, mono, 237 ms | random pool of every playback slot; stationary pan index 6 = 0 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain25 | ORIGINAL-WAV | brain25.wav | 2322 | 22050 Hz, 8-bit, mono, 100 ms | random pool of every playback slot; stationary pan index 7 = 150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain26 | ORIGINAL-WAV | brain26.wav | 800 | 11000 Hz, 8-bit, mono, 69 ms | random pool of every playback slot; stationary pan index 7 = 150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain27 | ORIGINAL-WAV | brain27.wav | 676 | 11025 Hz, 8-bit, mono, 57 ms | random pool of every playback slot; stationary pan index 7 = 150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain28 | ORIGINAL-WAV | brain28.wav | 1130 | 11025 Hz, 8-bit, mono, 98 ms | random pool of every playback slot; stationary pan index 7 = 150 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain29 | ORIGINAL-WAV | brain29.wav | 2272 | 11025 Hz, 8-bit, mono, 202 ms | random pool of every playback slot; stationary pan index 8 = 300 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain30 | ORIGINAL-WAV | brain30.wav | 780 | 22050 Hz, 16-bit, mono, 15 ms | random pool of every playback slot; stationary pan index 8 = 300 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain31 | ORIGINAL-WAV | brain31.wav | 1090 | 11111 Hz, 8-bit, mono, 94 ms | random pool of every playback slot; stationary pan index 8 = 300 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain32 | ORIGINAL-WAV | brain32.wav | 1404 | 11025 Hz, 8-bit, mono, 123 ms | random pool of every playback slot; stationary pan index 9 = 450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain33 | ORIGINAL-WAV | brain33.wav | 1492 | 11025 Hz, 8-bit, mono, 125 ms | random pool of every playback slot; stationary pan index 9 = 450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain34 | ORIGINAL-WAV | brain34.wav | 2464 | 11025 Hz, 8-bit, mono, 211 ms | random pool of every playback slot; stationary pan index 9 = 450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain35 | ORIGINAL-WAV | brain35.wav | 1180 | 11025 Hz, 8-bit, mono, 103 ms | random pool of every playback slot; stationary pan index 9 = 450 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain36 | ORIGINAL-WAV | brain36.wav | 1200 | 5564 Hz, 8-bit, mono, 208 ms | random pool of every playback slot; stationary pan index 10 = 600 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain37 | ORIGINAL-WAV | brain37.wav | 1012 | 8000 Hz, 16-bit, mono, 60 ms | random pool of every playback slot; stationary pan index 10 = 600 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain38 | ORIGINAL-WAV | brain38.wav | 650 | 8000 Hz, 16-bit, mono, 38 ms | random pool of every playback slot; stationary pan index 10 = 600 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain39 | ORIGINAL-WAV | brain39.wav | 790 | 5500 Hz, 8-bit, mono, 121 ms | random pool of every playback slot; stationary pan index 11 = 750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain40 | ORIGINAL-WAV | brain40.wav | 260 | 11025 Hz, 8-bit, mono, 20 ms | random pool of every playback slot; stationary pan index 11 = 750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain41 | ORIGINAL-WAV | brain41.wav | 2324 | 11025 Hz, 8-bit, mono, 200 ms | random pool of every playback slot; stationary pan index 11 = 750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |
| brain42 | ORIGINAL-WAV | brain42.wav | 1848 | 11025 Hz, 8-bit, mono, 159 ms | random pool of every playback slot; stationary pan index 11 = 750 | Form_Load slot code, stmt 135-156 (slot 1) and copies | one-shot | file facts CODE; use CODE |

Unreferenced files: none. Every file brain1.wav .. brainN.wav is reachable by number (CODE). brain7.wav is silent: it is picked like any other and gives a short silent turn in its slot (CODE: no special case); whether it was meant as a pause is not needed for the clone (play it as it is).

Non-wav sounds (CODE):

| ID | kind | file | bytes | format | event | code location | loop | confidence |
|---|---|---|---|---|---|---|---|---|
| beep_exit (1st) | ORIGINAL-TONE | none (Windows default sound, rtcBeep = MessageBeep(0)) | - | system sound | exit when gamemenu.exe is not in the current folder, right after " exiting program " | Form_Load stmt 548 | one-shot | CODE |
| beep_exit (2nd) | ORIGINAL-TONE | same sound ID, played again | - | system sound | 0.1 s after the first | Form_Load stmt 550 | one-shot | CODE |
One sound ID, beep_exit, is played twice (as in SOUND_DESIGN, CUSTOMIZABLE_CONTENT C6 and GAME_SPEC 17).

Silent events (for S4.4): startup, menu changes, mode changes, playback start and stop have speech but no sound (CODE).

P4 confirmation (2026-10-12): every row above re-checked against `work/p4_wav_checks.txt`; stationary pan column recomputed and equal. Wav facts for the clone: playback frequency 3,500-46,000 Hz, real length 2.8-324 ms (GAME_SPEC 5.3 and 5.4). Exit beeps are MessageBeep(0), not PC speaker tones (kind: ORIGINAL-TONE retained as the label for "non-wav original sound"). Sound gaps: none (SOUND_DESIGN.md).
