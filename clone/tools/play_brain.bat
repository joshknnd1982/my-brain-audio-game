@echo off
rem Starts the Brain clone from source (64-bit) for listening tests. Inspired by Jim Kitchen's Brain.
rem No console window: pythonw. The log is in %APPDATA%\Kitchensinc Revival\Brain\logs\brain.log
cd /d "%~dp0..\src"
start "" "%USERPROFILE%\.kitchensinc-venvs\brain-64\Scripts\pythonw.exe" -m brain
