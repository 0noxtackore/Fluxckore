@echo off
REM Fluxop launcher (Windows)
REM
REM Double-click this file to start Fluxop.
REM It removes the "Mark of the Web" (the internet zone that Windows adds to
REM downloaded files) before launching, because that mark blocks the .NET
REM runtime used by the interface. No command line knowledge is required.

powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%~dp0' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"
start "" "%~dp0Fluxop.exe"
