@echo off
REM Fluxop launcher - Windows (source checkout)
REM
REM Double-click this file to launch Fluxop from the project folder.
REM It removes the Windows "Mark of the Web" (internet zone) from the build
REM folder first, because that mark blocks the .NET runtime used by the UI.

if exist "dist\Fluxop-app\Fluxop.exe" (
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%CD%\dist\Fluxop-app' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"
    start "" "%CD%\dist\Fluxop-app\Fluxop.exe"
) else (
    python -m fluxop
)
