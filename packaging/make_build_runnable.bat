@echo off
REM Make the build/ tree runnable, not only dist/.
REM
REM PyInstaller's build\fluxckore\ is an intermediate cache: its Fluxckore.exe
REM is exactly the same binary shipped in dist\Fluxckore\, but it only runs when
REM the _internal folder (Python runtime, DLLs, data) sits next to it. dist/
REM gets that automatically; build/ does not, so a bare build exe fails with the
REM classic "app depends on the _internal folder" message.
REM
REM This script links build\fluxckore\_internal to the real _internal in dist/
REM with an NTFS junction: zero extra disk usage, instant, and both directories
REM can then be executed for quick manual tests. Run it right after each
REM PyInstaller build (rebuild.bat at the repository root already does this).
REM A junction beats copying ~60 MB: --clean wipes build/ on every rebuild, so
REM a copy would waste disk and go stale, while the junction is recreated in a
REM split second.

setlocal
cd /d "%~dp0.."

if not exist "build\fluxckore\Fluxckore.exe" (
    echo No build\fluxckore\Fluxckore.exe found. Run "pyinstaller packaging\fluxckore.spec --noconfirm --clean" first.
    exit /b 2
)
if not exist "dist\Fluxckore\_internal" (
    echo No dist\Fluxckore\_internal found. Run "pyinstaller packaging\fluxckore.spec --noconfirm --clean" first.
    exit /b 2
)

if exist "build\fluxckore\_internal" (
    if exist "build\fluxckore\_internal\python312.dll" (
        echo build\fluxckore\_internal already linked and valid. Nothing to do.
        exit /b 0
    )
    rem Stale/incomplete leftovers from a previous run: drop them before linking.
    rmdir /s /q "build\fluxckore\_internal" >nul 2>&1
)

cmd /c mklink /J "build\fluxckore\_internal" "dist\Fluxckore\_internal" >nul 2>&1
if errorlevel 1 exit /b 1

echo Linked build\fluxckore\_internal -^> dist\Fluxckore\_internal.
echo Now build\fluxckore\Fluxckore.exe runs exactly like the dist copy.
