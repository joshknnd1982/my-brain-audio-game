# Build Brain (PyInstaller, onedir, windowed) for 64-bit and 32-bit. This is inspired by Jim Kitchen's Brain.
# Usage: powershell -ExecutionPolicy Bypass -File clone\tools\build.ps1 [-Bits "64,32"]
# Builds from a COPY of clone\src in a scratch folder, so the build cannot see the source tree or the
# original files (playbook 8.1: catches files that are missing from the bundle).
# Output: %USERPROFILE%\.kitchensinc-builds\brain\<bits>\dist\brain\  (brain.exe, _internal\, assets\sounds\ beside the exe)
param([string]$Bits = "64,32")
$ErrorActionPreference = "Stop"
$clone = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$game = Split-Path -Parent $clone
# Outside OneDrive on purpose: a build folder holds thousands of files, and OneDrive syncing them slowed
# the test run (P9). Finished files (zip, checksums, build info) go to release\ in the game folder.
$buildRoot = Join-Path $env:USERPROFILE ".kitchensinc-builds\brain"
$venvs = Join-Path $env:USERPROFILE ".kitchensinc-venvs"

foreach ($b in ($Bits -split ",")) {
    $py = Join-Path $venvs "brain-$b\Scripts\python.exe"
    if (-not (Test-Path $py)) { throw "missing environment $py (run clone\tools\setup_envs.ps1)" }
    $root = Join-Path $buildRoot "$b"
    if (Test-Path $root) { Remove-Item -Recurse -Force $root }
    $srcCopy = Join-Path $root "src"
    New-Item -ItemType Directory -Force $srcCopy | Out-Null
    Copy-Item -Recurse (Join-Path $clone "src\brain") $srcCopy
    Get-ChildItem -Recurse -Directory -Filter "__pycache__" $srcCopy | Remove-Item -Recurse -Force
    Copy-Item (Join-Path $clone "tools\brain_entry.py") $root

    Push-Location $root
    try {
        & $py -I -m PyInstaller --noconfirm --clean --windowed --onedir `
            --name brain --distpath dist --workpath work --specpath spec `
            --paths src `
            --add-data "$srcCopy\brain\speech\nvda_client;brain\speech\nvda_client" `
            --hidden-import win32com.client --hidden-import pythoncom --hidden-import pywintypes `
            --hidden-import win32timezone `
            --exclude-module tkinter --exclude-module pytest `
            brain_entry.py
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $b-bit" }
    } finally { Pop-Location }

    # Sounds and attribution beside the exe: the player sees and can replace them (playbook 7.7).
    $out = Join-Path $root "dist\brain"
    $sounds = Join-Path $out "assets\sounds"
    New-Item -ItemType Directory -Force $sounds | Out-Null
    Copy-Item (Join-Path $clone "assets\sounds\*") $sounds
    Copy-Item (Join-Path $clone "README.md") (Join-Path $out "README.txt")
    Copy-Item (Join-Path $game "LICENSE") (Join-Path $out "LICENSE.txt")
    Copy-Item (Join-Path $game "SOUNDS_NOTICE.txt") $out
    Copy-Item (Join-Path $clone "THIRD_PARTY_NOTICES.txt") $out
    Write-Host "built $b-bit: $out"
}
