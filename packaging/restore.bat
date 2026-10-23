@echo off
REM If Fluxckore does not open, or Windows says it cannot run / blocked it,
REM double-click this file. It opens a small assistant that explains what
REM happened and takes you to the Windows protection history, where the
REM blocked file can be restored.

setlocal
set "HERE=%~dp0"
set "REPAIR=%HERE%Repair-Fluxckore.ps1"

if not exist "%REPAIR%" (
    echo.
    echo   No se encontro Repair-Fluxckore.ps1 en esta carpeta.
    echo   Vuelve a extraer el ZIP completo de Fluxckore.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%REPAIR%" -Reason manual -AppDir "%HERE%" -LogPath "%HERE%fluxckore-startup.log"
exit /b 0
