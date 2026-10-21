@echo off
REM Fluxop launcher - Windows
REM Double-click this file to launch Fluxop.
REM Uses the PyInstaller bundle (dist\Fluxop-app\Fluxop.exe) if it exists,
REM otherwise falls back to running from source with Python.

if exist "dist\Fluxop-app\Fluxop.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%CD%\dist\Fluxop-app' -Recurse -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"
    start "" "%CD%\dist\Fluxop-app\Fluxop.exe"
) else (
    python -m fluxop
)
