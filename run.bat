@echo off
REM Fluxckore launcher - Windows (source checkout)
REM
REM Double-click this file to launch Fluxckore from the project folder.
REM Only the executable is unblocked here (the app clears the rest of its own
REM files natively at startup); a recursive Unblock-File pass over the whole
REM build folder delayed the launch by many seconds.

if exist "dist\Fluxckore-app\Fluxckore.exe" (
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%CD%\dist\Fluxckore-app\Fluxckore.exe' -ErrorAction SilentlyContinue" >nul 2>&1
    start "" "%CD%\dist\Fluxckore-app\Fluxckore.exe"
) else (
    python -m fluxckore
)
