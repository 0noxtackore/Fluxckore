@echo off
REM Fluxop launcher - Windows (source checkout)
REM
REM Double-click this file to launch Fluxop from the project folder.
REM Only the executable is unblocked here (the app clears the rest of its own
REM files natively at startup); a recursive Unblock-File pass over the whole
REM build folder delayed the launch by many seconds.

if exist "dist\Fluxop-app\Fluxop.exe" (
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%CD%\dist\Fluxop-app\Fluxop.exe' -ErrorAction SilentlyContinue" >nul 2>&1
    start "" "%CD%\dist\Fluxop-app\Fluxop.exe"
) else (
    python -m fluxop
)
