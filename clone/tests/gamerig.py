"""Test rig for the game logic: virtual clock, scripted keys and random numbers, fake library. This is inspired by Jim Kitchen's Brain."""
import re
from array import array

from brain.audio.engine import Audio
from brain.audio.library import Pick
from brain.audio.output import TimedOutput
from brain.audio.wavdata import Sampled
from brain.data.settings import Settings
from brain.game.functions import Functions
from brain.speech.voices import VoiceInfo
from brain.game.flow import Game
from brain.game.keys import MODIFIER_KEYS, GameQuit, KeyInput
from brain.speech.fake import FakeBackend
from brain.speech.manager import SpeechManager


class Clock:
    """Virtual time: sleeping advances it, nothing really waits."""

    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Scripted:
    """A Rnd that returns the given numbers in order, then repeats the last one."""

    def __init__(self, *values):
        self.values = list(values)
        self.reseeds = 0
        self.draws = 0

    def next(self):
        self.draws += 1
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]

    def reseed(self):
        self.reseeds += 1


NO_FILE = "no file"


def make_pick(number, rate=11025, frames=1000, size=None, path="brain.wav", sound=True, source="original"):
    """A Pick as the library would answer: sound None is the original's failed buffer."""
    data = Sampled(array("h", [3277] * frames).tobytes(), rate, 1) if sound else None      # 0.1 of full scale
    size = frames if size is None else (None if size == NO_FILE else size)
    return Pick(f"brain{number:02d}", data, size, source, path)


class StubLibrary:
    def __init__(self, picks=None, pool=None):
        self.picks = dict(picks or {})
        self.pool = pool if pool is not None else len(self.picks)
        self.refreshes = 0
        self.asked: list[int] = []

    def refresh(self):
        self.refreshes += 1

    def pool_size(self):
        return self.pool

    def pick_number(self, number):
        self.asked.append(number)
        return self.picks.get(number, Pick(f"brain{number:02d}", None, None, "none"))

    def pick(self, wanted_id):
        match = re.match(r"^brain0*(\d+)$", wanted_id)
        if match and int(match.group(1)) in self.picks:
            return self.picks[int(match.group(1))]
        return Pick(wanted_id, None, None, "none")

    def take_notices(self):
        return []


class FakeBeeper:
    def __init__(self, clock):
        self.clock = clock
        self.at: list[float] = []

    def beep(self):
        self.at.append(self.clock())
        return True


class ScriptedKeys(KeyInput):
    """Keys on a virtual clock. `answers` are typed when a getkey waits, one per wait."""

    def __init__(self, clock, answers=()):
        super().__init__(clock=clock, sleep=clock.sleep)
        self.answers = list(answers)
        self.waits = 0
        self.read = []

    def getkey(self, speech):
        self.clk()
        self.waits += 1
        if self.code_text == "" and self.answers:
            self.post(self.answers.pop(0))
        for _ in range(200000):
            if self.code_text != "":
                break
            self._sleep(0.001)
            self.pump()
        else:
            raise AssertionError("the game waits for a key that the test never presses")
        speech.stop()


    def read_key(self):
        """Menus of the added functions: an answer is typed when the menu waits; ("wait", s) lets time pass."""
        while True:
            if self.quit.is_set():
                raise GameQuit()
            if self._posted.empty():
                if not self.answers:
                    raise AssertionError("the menu waits for a key that the test never presses")
                answer = self.answers.pop(0)
                if isinstance(answer, tuple):
                    self._sleep(answer[1])
                    continue
                self.post(answer)
                if answer in MODIFIER_KEYS:         # read_key skips these and would then wait for a key nobody types
                    self._posted.get_nowait()
                    continue
            code = super().read_key()
            self.read.append(code)
            return code


class FakeCatalog:
    """The voice list: ready at once."""

    def __init__(self, voices):
        self._voices = voices
        self.loaded = True
        self.broken = 0

    def voices(self, timeout=None):
        return list(self._voices)


def make_voices(*names):
    return [VoiceInfo(i, f"token-{i}", name) for i, name in enumerate(names)]


class Rig:
    def __init__(self, library, answers=(), rng=None, menu=None, speech_per_char=0.0, folder="nowhere",
                 functions=False, voices=None, export_dir="nowhere-export", voice_guard=None):
        self.clock = Clock()
        self.fake = FakeBackend(seconds_per_char=speech_per_char)
        self.speech = SpeechManager(self.fake, None)
        self.keys = ScriptedKeys(self.clock, answers)
        self.output = TimedOutput(self.clock)
        self.beeper = FakeBeeper(self.clock)
        self.settings = Settings.defaults()
        self.audio = Audio(library, self.settings.audio, output=self.output, beeper=self.beeper)
        self.rng = rng or Scripted(0.5)
        self.launched: list[str] = []
        self.pass_hook = None            # called with the pass number on every playback pass
        self.passes = 0

        def sleep(seconds):
            self.passes += 1
            if self.pass_hook:
                self.pass_hook(self.passes)
            self.clock.sleep(seconds)

        self.opened: list[str] = []
        self.changes = 0
        self.catalog = FakeCatalog(voices if voices is not None else [])
        self.functions = None
        if functions:
            self.functions = Functions(self.speech, self.keys, self.audio, self.settings, self.catalog, export_dir,
                                       open_folder=lambda path: self.opened.append(path) or True,
                                       on_change=self.count_change, clock=self.clock, voice_guard=voice_guard)
        self.game = Game(self.speech, self.keys, self.audio, folder, rng=self.rng, clock=self.clock,
                         sleep=sleep, find_menu=lambda f: menu,
                         launch_menu=lambda path: self.launched.append(path) or True, functions=self.functions)

    def count_change(self):
        self.changes += 1

    @property
    def spoken(self):
        return self.fake.spoken()


from brain.game.rnd import GameRandom  # noqa: E402


class Seeded(GameRandom):
    """A real generator with a fixed seed; reseed() only counts, so runs repeat."""

    def __init__(self, seed=1):
        super().__init__(seed)
        self.reseeds = 0

    def reseed(self):
        self.reseeds += 1
