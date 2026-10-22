@echo off
REM Fluxckore launcher (Windows)
REM
REM Double-click this file to start Fluxckore.
REM
REM The app clears the Windows "Mark of the Web" (internet zone) from all of
REM its files at startup, natively and in milliseconds. Only Fluxckore.exe itself
REM is unblocked here so SmartScreen stays quiet on the first run: doing a
REM recursive PowerShell Unblock-File pass over the whole folder (HUNDREDS of
REM files) delayed the launch by many seconds, which looked like a freeze.

powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0Fluxckore.exe' -ErrorAction SilentlyContinue" >nul 2>&1
start "" "%~dp0Fluxckore.exe"
