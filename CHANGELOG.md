# Changelog

## 1.0.0 (2026-10-13)
First complete version of My Brain by Josh Kennedy, inspired by Jim Kitchen.
- All of the original's behavior: 1 to 9 simultaneous sounds, four panning modes, random wavs at random pitch, keys, speech prompts, exit.
- Added: F1 help, F2 speech settings (any SAPI 5 voice, rate, volume, pitch, output), F3 sounds (volume, pitch variation, listen, reload, check, restore), F4 about; settings and sound files in `%APPDATA%\Kitchensinc Revival\Brain` with self-healing.
- Speech through SAPI 5, NVDA and JAWS. JAWS: fast interruption while arrowing through menus (a flushed SayString; JAWS 2026's StopSpeech does nothing).
- Installer (Inno Setup, 64-bit and 32-bit in one setup) and portable zip.
