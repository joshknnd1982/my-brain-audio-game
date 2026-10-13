# SOUND_DESIGN: Brain

P4 S4.4, 2026-10-12. Sound gaps audit (playbook 7.8). Result: no gaps to fill; no generated sounds.

## Original sounds
- 42 wavs: the whole point of the program (WAV_EVENT_MAP.md). None missing, none unreferenced. brain7.wav is silent by design or accident; kept as is.
- No PC speaker tones, no PLAY strings, no music (CODE).
- Two Windows default beeps on exit when gamemenu.exe is not found. Exact mechanism (CODE, checked in this PC's msvbvm60.dll): Beep is rtcBeep, which calls MessageBeep(0) (MB_OK, the "default sound" of the player's Windows sound scheme), not a PC speaker tone. Clone: play the system default sound the same way and keep the two beeps 0.1 s apart (waits of 0.1 s after each). Sound ID beep_exit, replaceable under 7.7; fallback if the system sound is unavailable: a short generated 880 Hz square blip, 80 ms (GENERATED, fallback only).

## Silent events (every event with speech but no sound)
| event | original | decision |
|---|---|---|
| startup | speech only | silent; speech is the cue |
| entering main menu | speech prompt | silent |
| menu digit accepted | key spoken, 0.2 s wait | silent |
| panning mode change | mode name spoken | silent |
| playback start | " Press the space bar to stop. " then sounds | silent; the toy's own sounds are the cue |
| playback stop | sounds stop at once, prompt spoken | silent |
| invalid key | key echoed | silent |

Decision (7.8c): leave all silent. Reason: the program is itself a sound toy; added sounds would mix with the sounds being listened to, could mask speech, and change what the author made. No "Added sounds" setting is needed. The owner may ask for cues in a later session.

## Checks (Claude cannot hear)
Automatic checks of the original wavs, `work/p4_wav_checks.txt` (not committed): leading and trailing silence, DC offset, peak. Nothing needs repair. Notable (CODE, file analysis, recomputed P5): brain8 is only 3 ms (heard as a click); brain3, 13, 21, 28, 31, 42 end with 35-43 ms of silence; brain14 starts with 50 ms of silence; brain7 is 49 ms of pure silence; the largest DC offsets are brain27 and brain40 (about 6.6 percent of full scale, 8-bit), every 16-bit file is under 1.1 percent. Clone plays files unchanged (no normalizing or trimming; changing them would change the original's sound).
Listening review (owner, with the clone, in P7.6): the 42 wavs at random pitch, the four pan modes, nine slots at once, the two exit beeps.

## Built in P7 S7.2 (2026-10-12)
Generated sound in the clone: beep_exit only, a fallback behind the player's file and the Windows default sound (880 Hz square, 80 ms, peak 0.35, 2 ms edges). Automatic checks in tests/test_audio_engine.py: length 80 ms, peak 0.35 (not clipping), no click (first sample under 0.01, last under 0.05), main pitch 880 Hz within 3 percent, deterministic, exports to a loadable wav. Not yet heard by the owner: the blip plays only when the system sound cannot play; the listening review of the 42 wavs at random pitch, the pan modes and nine slots at once is S7.6.
