@echo off
REM Fluxckore rebuild - Windows
REM
REM Runs the full PyInstaller pipeline and leaves BOTH build trees runnable:
REM   dist\Fluxckore\Fluxckore.exe     <- final product (ship this folder/ZIP)
REM   build\fluxckore\Fluxckore.exe    <- same binary, linked to _internal
REM                                       for quick local tests
REM
REM The intermediate build\fluxckore\ cache alone is NOT executable: the exe
REM there has no _internal folder next to it and Windows refuses to start it.
REM packaging\make_build_runnable.bat fixes that with an NTFS junction to the
REM real _internal in dist, so you can launch either copy after a rebuild.

setlocal
cd /d "%~dp0"

echo === Building Fluxckore (pyinstaller packaging\fluxckore.spec) ===
python -m PyInstaller packaging\fluxckore.spec --noconfirm --clean
if errorlevel 1 goto :failed

echo === Linking build\fluxckore\_internal to dist\Fluxckore\_internal ===
call packaging\make_build_runnable.bat
if errorlevel 1 goto :failed

echo.
echo Build complete:
echo   dist\Fluxckore\Fluxckore.exe           (distribute - portable + ZIP)
echo   build\fluxckore\Fluxckore.exe          (linked copy for quick tests)
exit /b 0

:failed
echo.
echo Build FAILED with code %ERRORLEVEL%
exit /b %ERRORLEVEL%
