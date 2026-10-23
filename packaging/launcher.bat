@echo off
REM Fluxckore launcher (Windows)
REM
REM Double-click this file to start Fluxckore.
REM
REM 1) If Fluxckore.exe is missing, Windows (Smart App Control / antivirus)
REM    blocked or deleted it. Open the restore assistant instead of failing
REM    silently: it explains what happened and opens the official Windows
REM    protection history, where the file can be restored.
REM 2) The app clears the Windows "Mark of the Web" (internet zone) from all
REM    its files at startup, natively and in milliseconds. Only Fluxckore.exe
REM    itself is unblocked here so SmartScreen stays quiet on the first run:
REM    a recursive Unblock-File pass over HUNDREDS of files used to delay the
REM    launch by many seconds, which looked like a freeze.
REM 3) A hidden watcher checks, 25 s later, that the app really started. If
REM    Windows killed it before it could write anything, the same assistant
REM    is shown. If the app is running, the watcher exits silently.

setlocal
set "HERE=%~dp0"
set "EXE=%HERE%Fluxckore.exe"
set "LOG=%HERE%fluxckore-startup.log"
set "REPAIR=%HERE%Repair-Fluxckore.ps1"

if not exist "%EXE%" goto missing

powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%EXE%' -ErrorAction SilentlyContinue" >nul 2>&1
start "" "%EXE%"

if exist "%REPAIR%" start "" /b powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%REPAIR%" -Reason failed -AppDir "%HERE%" -LogPath "%LOG%"
exit /b 0

:missing
if exist "%REPAIR%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPAIR%" -Reason missing -AppDir "%HERE%" -LogPath "%LOG%"
) else (
    echo.
    echo   Windows bloqueo o elimino Fluxckore.exe.
    echo   Abre Seguridad de Windows ^> Historial de proteccion y pulsa Restaurar.
    echo.
    pause
)
exit /b 1
