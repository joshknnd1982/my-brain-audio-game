# CUSTOMIZABLE_CONTENT: Brain

P4 S4.5, 2026-10-12. Inventory per playbook 7.9. Brain has no names, teams, rosters or stats. Its only data is the wav set and a few fixed constants (CODE, GAME_SPEC 11).

## Lists

### L1 Sound set (the only real customizable list)
- Where it appears: the random pool of every playback slot (GAME_SPEC 5.2).
- Entries: 42 in the original (IDs brain01 .. brain42, files brain1.wav .. brain42.wav). Original name = file name; there is no display name (CODE).
- Stored: data files in the program folder, read by number; hard-coded name pattern "brain" + number + ".wav" (CODE).
- Original limits: count n comes from Dir("brain*.wav"), no upper limit in code; numbers must be consecutive 1..n or some picks fail silently; any wav format DirectSound can load; the author's readme asks users to add or replace wavs (CODE, brain.txt, OWNER permission DECISIONS.md).
- Per-entry attributes: none stored. Facts of the shipped files (rate, bits, length) are in WAV_EVENT_MAP.md, not editable data.
- Clone: sounds follow 7.7. IDs brain01..brain42 with the player's sounds folder overriding the shipped wav; added files brain43, brain44 ... extend the pool (count rule, see DECISIONS 2026-10-12 P4). No names file is needed. Evidence: CODE.

## Fixed constants (settings, not lists)
| ID | what | original value | where | customizable? |
|---|---|---|---|---|
| C1 | slots | 1 to 9, chosen by digit | main menu | chosen each time, no file |
| C2 | pitch offset | whole number -20..19 times 100 Hz, never 0 | code | recommend setting "pitch range" (default -20..19), accepted-default: yes in settings, off the list of editable data |
| C3 | pan table | 11 steps -750..750 (hundredths of dB), mode 4 range -1000..990 | code | no; part of the mode definitions, kept exact |
| C4 | voice, rate, volume | first SAPI voice, base rate unchanged, volume 90 | code | yes, settings (OPEN_QUESTIONS 17e): voice, rate, volume |
| C5 | mode names and prompts | 4 mode names, 4 prompts (STRINGS.md) | code | recommend no editable text file in v1: wording is the original's identity; spoken-as overrides only if a voice mispronounces (accepted-default, revisit in P7.7) |
| C6 | exit beep | Windows default beep (MessageBeep 0) twice, 0.1 s apart | code | yes as sound ID beep_exit via the sounds folder (7.7) |

## Self-healing (7.10): what the original did
- The original reads only wavs. It writes no files (CODE). Missing or damaged wav: silent slot, no message (CODE).
- Clone: built-in originals are the 42 shipped wavs and the constants. Player files (sounds folder, settings) are overlays; a missing or bad one falls back to the shipped original, never silence from damage, never a crash. Where the original stayed silent (a bad wav the player added), the clone logs and stays silent for that pick but never blocks others (OPEN_QUESTIONS 17b).

## Owner decisions needed
None. C2 and C5 are accepted defaults (DECISIONS.md), changeable by the owner at any time.

## Built in P7 S7.5 and S7.7 (2026-10-12)
- Settings (C2 pitch range, C4 voice, rate, volume, output, effects volume) are saved in settings.txt; the sound set (L1) uses the sounds folder, sounds.txt and the restore commands in the Sounds menu (one sound, all sounds). C5 stays closed: no editable wording file in v1.
- Self-healing for every player-reachable file (settings.txt, sounds.txt, the sounds folder) is tested (tests/test_self_healing.py, DECISIONS P7 S7.5 and S7.7).
