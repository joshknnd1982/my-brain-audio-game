"""Scripted verification of the installer (P10 S10.3, playbook 8.2). Inspired by Jim Kitchen's Brain.

Runs the real setup file silently into a scratch folder (NOT AppData\\Local, which the Claude desktop app redirects),
current-user mode, and checks: files and registry entry, the installed exe starts and exits, settings and player sounds
survive an update over an older version (built here as 0.9.0), stale library files of the old version are removed,
a player's own file in assets\\sounds is kept, silent uninstall removes the program and keeps the settings, and
uninstall with /DELETEUSERDATA=1 removes them. The delete test touches the REAL per-user folder
(%APPDATA%\\Kitchensinc Revival\\Brain), so that folder is copied away first and put back at the end.
Usage: python verify_installer.py <report file>     (any Python 3; run from anywhere)
"""
import os
import shutil
import subprocess
import sys
import time
import winreg

GAME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RELEASE = os.path.join(GAME, "release")
SETUP = os.path.join(RELEASE, "brain-setup-1.0.0.exe")
ISCC = r"C:\Users\joshk\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
SCRATCH = os.path.join(os.path.expanduser("~"), ".kitchensinc-builds", "brain", "install-test")
APP = os.path.join(SCRATCH, "app")
OLD_SETUP = os.path.join(SCRATCH, "brain-setup-0.9.0.exe")
DATA = os.path.join(os.environ["APPDATA"], "Kitchensinc Revival")
DATA_BACKUP = os.path.join(SCRATCH, "appdata-backup")
KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{6F2B8C14-3A7D-4E95-B1C0-5D9E47A82F36}_is1"
lines = []
failed = []


def check(name, ok, detail=""):
    text = ("PASS " if ok else "FAIL ") + name + (": " + str(detail) if detail else "")
    lines.append(text)
    print(text)
    if not ok:
        failed.append(name)


def run(args, timeout=300):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def install(setup, log):
    return run([setup, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", f"/DIR={APP}", f"/LOG={log}"])


def uninstall(extra=()):
    exe = os.path.join(APP, "unins000.exe")
    return run([exe, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", *extra])


def registry_version():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            return winreg.QueryValueEx(key, "DisplayVersion")[0]
    except OSError:
        return None


def count(folder):
    return sum(len(files) for _, _, files in os.walk(folder)) if os.path.isdir(folder) else 0


def start_and_close(exe, data_dir, seconds=7):
    """Start the exe with a scratch data folder, wait, close its window politely, return the exit code."""
    env = dict(os.environ, BRAIN_DATA_DIR=data_dir)
    proc = subprocess.Popen([exe], env=env, cwd=os.path.dirname(exe))
    time.sleep(seconds)
    alive = proc.poll() is None
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    return alive


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "installer_verify_report.txt"
    os.makedirs(SCRATCH, exist_ok=True)
    if os.path.exists(APP):
        shutil.rmtree(APP)
    if os.path.isdir(DATA):
        if os.path.exists(DATA_BACKUP):
            shutil.rmtree(DATA_BACKUP)
        shutil.copytree(DATA, DATA_BACKUP)
    check("setup file exists", os.path.exists(SETUP), f"{os.path.getsize(SETUP)} bytes")

    # older version for the update test (same AppId, version 0.9.0, written beside the real one, not in release/)
    build = run([ISCC, f"/DAppVersion=0.9.0", f"/O{SCRATCH}", os.path.join(RELEASE, "installer.iss")], timeout=600)
    check("older setup 0.9.0 compiled for the update test", build.returncode == 0 and os.path.exists(OLD_SETUP))

    try:
        # 1. fresh install of the OLD version, plant stale and custom files
        result = install(OLD_SETUP, os.path.join(SCRATCH, "install_old.log"))
        check("old version installs silently", result.returncode == 0 and os.path.exists(os.path.join(APP, "brain.exe")), result.returncode)
        check("registry says 0.9.0", registry_version() == "0.9.0", registry_version())
        stale = os.path.join(APP, "_internal", "stale_from_old_version.dll")
        open(stale, "w").write("old")
        mine = os.path.join(APP, "assets", "sounds", "my_own_sound.wav")
        open(mine, "w").write("player file")

        # 2. update over it with the real setup
        result = install(SETUP, os.path.join(SCRATCH, "install_new.log"))
        check("1.0.0 installs over 0.9.0", result.returncode == 0, result.returncode)
        check("registry says 1.0.0", registry_version() == "1.0.0", registry_version())
        check("stale library file of the old version is removed", not os.path.exists(stale))
        check("a player's own file in assets\\sounds is kept", os.path.exists(mine))
        check("42 shipped wavs and the license are installed",
              len([f for f in os.listdir(os.path.join(APP, "assets", "sounds")) if f.startswith("brain")]) == 42
              and os.path.exists(os.path.join(APP, "LICENSE.txt")) and os.path.exists(os.path.join(APP, "THIRD_PARTY_NOTICES.txt")))
        check("README.txt and uninstaller installed", os.path.exists(os.path.join(APP, "README.txt")) and os.path.exists(os.path.join(APP, "unins000.exe")))
        bits = "64-bit" if os.path.exists(os.path.join(APP, "_internal", "brain", "speech", "nvda_client", "x64")) else "32-bit"
        check("this 64-bit Windows got the 64-bit build", bits == "64-bit", bits)
        start_menu = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "My Brain")
        check("Start menu entries made", os.path.exists(os.path.join(start_menu, "My Brain.lnk")) and os.path.exists(os.path.join(start_menu, "Uninstall My Brain.lnk")))

        # 3. the installed exe runs, with a fresh empty data folder: files are created
        fresh = os.path.join(SCRATCH, "fresh-data")
        shutil.rmtree(fresh, ignore_errors=True)
        alive = start_and_close(os.path.join(APP, "brain.exe"), fresh)
        check("installed exe starts and keeps running", alive)
        check("a missing settings folder is recreated with sounds.txt and a log",
              os.path.exists(os.path.join(fresh, "sounds", "sounds.txt")) and os.path.exists(os.path.join(fresh, "logs", "brain.log")))
        log_text = open(os.path.join(fresh, "logs", "brain.log"), encoding="utf-8", errors="replace").read()
        check("no warnings or errors in the installed exe's log", " ERROR " not in log_text and "Traceback" not in log_text)
        check("installed exe says version 1.0.0", "Brain clone 1.0.0 starting" in log_text)

        # 4. silent uninstall keeps settings
        marker = os.path.join(DATA, "Brain", "settings.txt")
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        if not os.path.exists(marker):
            open(marker, "w").write("# Brain settings, format 1\n")
        before = count(DATA)
        result = uninstall()
        time.sleep(2)
        check("silent uninstall succeeds", result.returncode == 0, result.returncode)
        check("program files removed", not os.path.exists(os.path.join(APP, "brain.exe")) and not os.path.exists(os.path.join(APP, "_internal")))
        check("registry entry removed", registry_version() is None)
        check("player's own file in assets\\sounds survives uninstall (not ours to delete)", os.path.exists(mine))
        check("settings kept by a silent uninstall", os.path.exists(marker) and count(DATA) == before, f"{before} files")

        # 5. reinstall, uninstall with /DELETEUSERDATA=1 deletes the settings folder
        install(SETUP, os.path.join(SCRATCH, "install_again.log"))
        result = uninstall(["/DELETEUSERDATA=1"])
        time.sleep(2)
        check("uninstall with /DELETEUSERDATA=1 succeeds", result.returncode == 0, result.returncode)
        check("settings folder deleted by it", not os.path.isdir(os.path.join(DATA, "Brain")))
    finally:
        if os.path.exists(os.path.join(APP, "unins000.exe")):
            uninstall()
        shutil.rmtree(APP, ignore_errors=True)
        if os.path.isdir(DATA_BACKUP):
            shutil.rmtree(DATA, ignore_errors=True)
            shutil.copytree(DATA_BACKUP, DATA)
        lines.append(f"real per-user folder restored from the copy ({count(DATA)} files)")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("ALL PASS" if not failed else "FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
