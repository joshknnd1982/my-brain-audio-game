"""Self-healing resource files (playbook 7.10): every damage in turn, for settings.txt and sounds.txt.

After each damage the program must start, speak, play with the original values, and either recreate the
file or save the damaged copy; never a traceback. Then a fuzz test of random corruptions. This is
inspired by Jim Kitchen's Brain.
"""
import codecs
import ctypes
import os
import random
import stat
from ctypes import wintypes

import pytest

from brain.audio.library import SoundLibrary
from brain.audio.soundsconfig import DEFAULT_TEXT as SOUNDS_DEFAULT
from brain.audio.soundsconfig import FILE_NAME as SOUNDS_NAME
from brain.audio.soundsconfig import load_or_heal
from brain.data import healing
from brain.data.settings import Settings
from brain.data.settingsfile import FILE_NAME as SETTINGS_NAME
from brain.data.settingsfile import SettingsStore, render
from gamerig import Rig, Seeded
from wavmaker import sine, write


# ----- the two files, behind one small interface -----

def non_default_settings() -> Settings:
    s = Settings.defaults()
    s.speech.volume, s.speech.pitch, s.speech.rate, s.speech.mode = 60, 2, -2, "auto"
    s.audio.effects_volume, s.audio.pitch_spread = 50, 10
    return s


class SettingsSubject:
    file_name = SETTINGS_NAME
    valid_text = render(non_default_settings())

    def load(self, folder):
        store = SettingsStore(folder)
        settings = store.load()
        return settings, store.take_notices(), store

    def check_valid(self, settings):
        sp, au = settings.speech, settings.audio
        assert sp.rate is None or -10 <= sp.rate <= 10
        assert 0 <= sp.volume <= 100 and -10 <= sp.pitch <= 10 and sp.mode in ("sapi", "nvda", "jaws", "auto")
        assert 0 <= au.effects_volume <= 100 and 0 <= au.pitch_spread <= 20

    def is_original(self, settings):
        d = Settings.defaults()
        return settings.speech == d.speech and settings.audio == d.audio

    def keeps_value(self, settings):
        return settings.speech.volume == 60 and settings.audio.pitch_spread == 10

    def bad_line_text(self):
        return self.valid_text.replace("speech_pitch = 2", "speech_pitch = banana")

    def newer_text(self):
        return self.valid_text.replace("format 1", "format 2")

    def default_text(self):
        return render(Settings.defaults())


class SoundsSubject:
    file_name = SOUNDS_NAME
    valid_text = SOUNDS_DEFAULT + "brain5 = volume=80\nbrain7 = off\n"

    def load(self, folder):
        config, notices = load_or_heal(folder)
        return config, notices, None

    def check_valid(self, config):
        for entry in config.entries.values():
            assert 0.0 <= entry.volume <= 2.0

    def is_original(self, config):
        return config.entries == {}

    def keeps_value(self, config):
        return config.get("brain7") is not None and config.get("brain7").off

    def bad_line_text(self):
        return self.valid_text.replace("brain5 = volume=80", "brain5 = volume=banana")

    def newer_text(self):
        return self.valid_text.replace("format 1", "format 2")

    def default_text(self):
        return SOUNDS_DEFAULT


SUBJECTS = [SettingsSubject(), SoundsSubject()]
IDS = ["settings.txt", "sounds.txt"]


@pytest.fixture(params=SUBJECTS, ids=IDS)
def subject(request):
    return request.param


@pytest.fixture
def folder(tmp_path):
    path = tmp_path / "Brain data"
    path.mkdir()
    return path


def put(subject, folder, data):
    path = folder / subject.file_name
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def damaged_copies(folder, subject):
    return sorted(n for n in os.listdir(folder) if n.startswith(subject.file_name + ".damaged"))


def reread(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def assert_healed(subject, folder, expect_notice=True):
    """The file is usable now: a second start is quiet and gives the original values."""
    value, notices, _ = subject.load(str(folder))
    assert notices == [] and subject.is_original(value)


# ----- delete, delete the folder -----

def test_deleted_file_is_recreated_from_the_originals(subject, folder):
    value, notices, _ = subject.load(str(folder))                       # first start creates it
    os.remove(folder / subject.file_name)
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and notices == []
    assert reread(folder / subject.file_name) == subject.default_text().replace("\r\n", "\n")


def test_deleted_folder_is_recreated_with_its_file(subject, tmp_path):
    folder = tmp_path / "a" / "b" / "Brain data"
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and notices == [] and (folder / subject.file_name).is_file()


# ----- empty, cut in half, random bytes -----

@pytest.mark.parametrize("data", [b"", b"   \r\n\r\n"], ids=["empty", "blank lines"])
def test_empty_file_is_saved_aside_and_reset(subject, folder, data):
    path = put(subject, folder, data)
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value)
    assert len(notices) == 1 and "damaged" in notices[0] and "copy was saved" in notices[0]
    assert (folder / (subject.file_name + ".damaged1")).read_bytes() == data
    assert_healed(subject, folder)


def test_file_cut_in_half_still_starts_with_valid_values(subject, folder):
    data = subject.valid_text.encode("utf-8")
    for cut in (len(data) // 2, len(data) - 3, 40, 5, 1):
        put(subject, folder, data[:cut])
        value, notices, _ = subject.load(str(folder))
        subject.check_valid(value)
        value, notices, _ = subject.load(str(folder))                   # whatever the first start did, the next is calm
        subject.check_valid(value)
        assert not [n for n in notices if "damaged" in n]
        assert len(damaged_copies(folder, subject)) <= 3


def test_random_bytes_are_saved_aside_and_reset(subject, folder):
    data = random.Random(7).randbytes(400)
    put(subject, folder, data)
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and len(notices) == 1 and "damaged" in notices[0]
    assert (folder / (subject.file_name + ".damaged1")).read_bytes() == data
    assert_healed(subject, folder)


# ----- other encodings, line endings -----

@pytest.mark.parametrize("encode", [
    lambda t: codecs.BOM_UTF16_LE + t.encode("utf-16-le"),
    lambda t: codecs.BOM_UTF16_BE + t.encode("utf-16-be"),
    lambda t: codecs.BOM_UTF8 + t.encode("utf-8"),
    lambda t: t.encode("cp1252"),
    lambda t: t.replace("\n", "\r\n").encode("utf-8"),
    lambda t: t.replace("\n", "\r").encode("utf-8"),
    lambda t: ("  " + t.replace("\n", "  \n\n\t")).encode("utf-8"),
], ids=["utf16le", "utf16be", "utf8bom", "cp1252", "crlf", "cr", "spaces and tabs"])
def test_other_encodings_and_line_endings_are_read_as_they_are(subject, folder, encode):
    put(subject, folder, encode(subject.valid_text))
    value, notices, _ = subject.load(str(folder))
    assert notices == [] and subject.keeps_value(value)
    assert damaged_copies(folder, subject) == []


def test_utf16_without_a_bom_counts_as_damage(subject, folder):
    put(subject, folder, subject.valid_text.encode("utf-16-le"))
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and "damaged" in notices[0]
    assert len(damaged_copies(folder, subject)) == 1


def test_odd_length_utf16_with_a_bom_counts_as_damage(subject, folder):
    put(subject, folder, codecs.BOM_UTF16_LE + subject.valid_text.encode("utf-16-le") + b"\x41")
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and "damaged" in notices[0]


# ----- huge -----

def test_huge_junk_file_is_reset_and_never_read_whole(subject, folder):
    put(subject, folder, b"junk junk junk\n" * 200_000)               # 3 MB
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and "damaged" in notices[0]
    assert len(damaged_copies(folder, subject)) == 1
    assert_healed(subject, folder)


def test_huge_file_of_valid_lines_is_still_too_large(subject, folder):
    put(subject, folder, subject.valid_text + "# padding\n" * 200_000)
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and "damaged" in notices[0]


def test_enormous_file_is_moved_not_copied(subject, folder, monkeypatch):
    monkeypatch.setattr(healing, "MOVE_INSTEAD_OF_COPY_BYTES", 1000)
    path = put(subject, folder, b"x" * 5000)
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and "damaged" in notices[0]
    assert (folder / (subject.file_name + ".damaged1")).stat().st_size == 5000
    assert_healed(subject, folder)


# ----- newer format version, bad line in the middle -----

def test_newer_format_version_is_saved_aside_and_reset(subject, folder):
    put(subject, folder, subject.newer_text())
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and "damaged" in notices[0]
    assert "format 2" in (folder / (subject.file_name + ".damaged1")).read_text(encoding="utf-8")


def test_bad_line_in_the_middle_is_skipped_and_the_rest_kept(subject, folder):
    path = put(subject, folder, subject.bad_line_text())
    value, notices, _ = subject.load(str(folder))
    assert notices == [f"1 problem found in {subject.file_name}, details are in the log."]
    assert subject.keeps_value(value) and damaged_copies(folder, subject) == []
    assert "banana" in reread(path)                                    # the player's file is not rewritten behind their back


# ----- read-only, locked -----

def make_read_only(path):
    os.chmod(path, stat.S_IREAD)


def make_writable(path):
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def test_read_only_valid_file_is_read_and_left_alone(subject, folder):
    path = put(subject, folder, subject.valid_text)
    make_read_only(path)
    try:
        value, notices, store = subject.load(str(folder))
        assert notices == [] and subject.keeps_value(value)
        if store is not None:                                          # settings: a later save cannot happen, said once
            assert store.save() is False
            assert len(store.take_notices()) == 1 and store.save() is False and store.take_notices() == []
        assert path.read_bytes() == subject.valid_text.encode("utf-8")
    finally:
        make_writable(path)


def test_read_only_damaged_file_runs_from_the_originals_and_says_where_the_file_belongs(subject, folder):
    path = put(subject, folder, b"")
    make_read_only(path)
    try:
        value, notices, _ = subject.load(str(folder))
        assert subject.is_original(value)
        assert len(notices) == 1 and "could not" in notices[0] and "AppData" in notices[0]
        assert path.read_bytes() == b""
    finally:
        make_writable(path)


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateFileW.restype = wintypes.HANDLE
_kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
INVALID = wintypes.HANDLE(-1).value


class Held:
    """Open a file with no sharing, as another program holding it would."""

    def __init__(self, path):
        self.path = str(path)

    def __enter__(self):
        self.handle = _kernel32.CreateFileW(self.path, 0x80000000 | 0x40000000, 0, None, 3, 0x80, None)
        assert self.handle != INVALID, ctypes.get_last_error()
        return self

    def __exit__(self, *exc):
        _kernel32.CloseHandle(self.handle)


def test_file_held_by_another_program_is_not_touched_and_originals_run(subject, folder):
    path = put(subject, folder, subject.valid_text)
    with Held(path):
        value, notices, store = subject.load(str(folder))
        assert subject.is_original(value)
        assert len(notices) == 1 and "in use by another program" in notices[0]
        if store is not None:
            store.settings.speech.volume = 5
            assert store.save() is False                              # nothing is written over a file we could not read
    assert path.read_bytes() == subject.valid_text.encode("utf-8")
    value, notices, _ = subject.load(str(folder))                     # released: read normally again
    assert notices == [] and subject.keeps_value(value)


def test_file_that_is_released_during_the_retries_is_read(subject, folder, monkeypatch):
    path = put(subject, folder, subject.valid_text)
    held = Held(path).__enter__()
    real_sleep = healing.time.sleep

    def release_then_sleep(seconds):
        if held.handle is not None:
            _kernel32.CloseHandle(held.handle)
            held.handle = None
        real_sleep(0)

    monkeypatch.setattr(healing.time, "sleep", release_then_sleep)
    value, notices, _ = subject.load(str(folder))
    assert notices == [] and subject.keeps_value(value)


def test_a_directory_where_the_file_belongs_does_not_crash(subject, folder):
    (folder / subject.file_name).mkdir()
    value, notices, _ = subject.load(str(folder))
    assert subject.is_original(value) and len(notices) == 1


def test_folder_that_cannot_be_made_runs_from_the_originals(subject, tmp_path):
    blocker = tmp_path / "blocked"
    blocker.write_text("a file")
    value, notices, _ = subject.load(str(blocker / "Brain"))
    assert subject.is_original(value) and len(notices) == 1


# ----- fuzz -----

def corrupt(rng: random.Random, data: bytes) -> bytes:
    kind = rng.randrange(9)
    n = len(data)
    if kind == 0:
        return data[:rng.randrange(n + 1)]
    if kind == 1:
        out = bytearray(data)
        for _ in range(rng.randint(1, 20)):
            out[rng.randrange(n)] = rng.randrange(256)
        return bytes(out)
    if kind == 2:
        at = rng.randrange(n + 1)
        return data[:at] + rng.randbytes(rng.randint(1, 60)) + data[at:]
    if kind == 3:
        a = rng.randrange(n)
        return data[:a] + data[a + rng.randint(1, 80):]
    if kind == 4:
        a = rng.randrange(n)
        return data + data[a:a + rng.randint(1, 200)]
    if kind == 5:
        return rng.randbytes(rng.randint(0, 500))
    if kind == 6:
        lines = data.split(b"\n")
        rng.shuffle(lines)
        return b"\n".join(lines)
    if kind == 7:
        text = data.decode("utf-8", "replace")
        return rng.choice([codecs.BOM_UTF16_LE + text.encode("utf-16-le"), text.encode("utf-16-le"),
                           text.encode("utf-16-be"), codecs.BOM_UTF8 + data])
    junk = [b"= = =", b"brain5 = ", b"speech_volume", b"; ; ;", b"\x00", b"\xff\xfe", b"# Brain settings, format 99",
            b"speech_rate = 99999999999999999999", b"brain9999999999 = off", b"brain3 = file=" + b"a" * 5000]
    lines = data.split(b"\n")
    lines.insert(rng.randrange(len(lines) + 1), rng.choice(junk))
    return b"\n".join(lines)


def test_fuzz_hundreds_of_random_corruptions_never_crash_and_always_heal(subject, tmp_path):
    rng = random.Random(20261012)
    base = subject.valid_text.encode("utf-8")
    for i in range(300):
        folder = tmp_path / f"case{i}"
        folder.mkdir()
        data = base
        for _ in range(rng.randint(1, 3)):
            data = corrupt(rng, data) if data else rng.randbytes(5)
        (folder / subject.file_name).write_bytes(data)
        value, notices, _ = subject.load(str(folder))                  # must not raise
        subject.check_valid(value)
        assert len(damaged_copies(folder, subject)) <= 3
        value, notices, _ = subject.load(str(folder))                  # the second start is calm: no damage again
        subject.check_valid(value)
        assert not [n for n in notices if "damaged" in n], (i, data[:80], notices)
        again = subject.load(str(folder))[1]
        assert again == notices                                        # and stable: the same file gives the same report


# ----- the whole program starts and plays from a damaged state -----

DAMAGES = {
    "deleted": None,
    "empty": b"",
    "random": random.Random(3).randbytes(300),
    "huge": b"junk\n" * 400_000,
    "utf16": codecs.BOM_UTF16_LE + "brain5 = off\n".encode("utf-16-le"),
}


@pytest.mark.parametrize("damage", list(DAMAGES))
def test_the_program_starts_speaks_and_plays_with_a_damaged_sounds_file(tmp_path, damage):
    shipped, player = tmp_path / "shipped", tmp_path / "player"
    shipped.mkdir()
    player.mkdir()
    for number in range(1, 4):
        write(shipped / f"brain{number}.wav", sine(200 * number, 0.02, 11025), rate=11025)
    if DAMAGES[damage] is not None:
        (player / SOUNDS_NAME).write_bytes(DAMAGES[damage])
    lib = SoundLibrary(str(shipped), str(player))
    rig = Rig(lib, answers=[49, 13, 27, 27], rng=Seeded(5))          # "1", Enter (play), a key, Escape
    rig.pass_hook = lambda n: rig.keys.post(65) if n == 200 else None
    rig.game.run()
    assert rig.spoken[0] and any("Press the space bar" in t for t in rig.spoken)
    assert len(rig.output.played) > 0
    assert (player / SOUNDS_NAME).is_file()
    if damage in ("empty", "random", "huge"):
        assert any("damaged" in t for t in rig.spoken)                  # said once, at the start


def test_the_program_starts_with_damaged_settings_through_the_store_and_game(tmp_path):
    folder = tmp_path / "Brain"
    folder.mkdir()
    (folder / SETTINGS_NAME).write_bytes(random.Random(9).randbytes(200))
    store = SettingsStore(str(folder))
    settings = store.load()
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    write(shipped / "brain1.wav", sine(300, 0.02, 11025), rate=11025)
    lib = SoundLibrary(str(shipped), str(tmp_path / "player"))
    rig = Rig(lib, answers=[49, 13, 27], rng=Seeded(5))
    rig.game.notice_sources = (lib, store)
    rig.pass_hook = lambda n: rig.keys.post(65) if n == 100 else None
    rig.game.run()
    assert settings.speech.volume == 90                                # the original values
    damaged_said = [t for t in rig.spoken if t.startswith("settings.txt was damaged")]
    assert len(damaged_said) == 1 and len(rig.output.played) > 0
