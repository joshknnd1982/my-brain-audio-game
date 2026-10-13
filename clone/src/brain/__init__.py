"""Brain clone: a sound toy. This is inspired by Jim Kitchen's Brain ("My Brain").

Jim Kitchen, blind from birth, made his games free for the blind community; he died in 2015.
This is new code written from the behavior described in spec/GAME_SPEC.md (no original code).

Packages:
  game    pure logic and the key fields (no window, no sound card needed)
  speech  SAPI 5 and NVDA speech behind one manager
  audio   wav playback, pitch and pan (P7 S7.2)
  ui      the Win32 window that receives keys
  data    per-user paths, settings, logging
"""

VERSION = "1.0.2"
TITLE = "Brain"
