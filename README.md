<p align="center">
  <img src="assets/images/logo_solid.jpg" alt="Fluxckore" width="716">
</p>
<p align="center">
  <strong>System Maintenance & Optimization Suite for Windows</strong><br>
  One app. One codebase. Windows 10/11 (x64). Not supported on Windows 7/8.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge&logo=apache" alt="Apache 2.0">
  <img src="https://img.shields.io/badge/License-Oracle%20UPL-blue?style=for-the-badge&logo=oracle" alt="Oracle UPL">
</p>

---

## Overview

Fluxckore (formerly Fluxop) is a Windows system maintenance suite built with Python and a self-contained HTML/CSS interface rendered by pywebview (Edge WebView2). It provides real-time system monitoring, selectable temporary-file cleanup, memory optimization and registry maintenance through a single dark-themed desktop application.

There is **one edition** of Fluxckore. Features evolve in place — no PRO/Beta/Enterprise splits, no parallel codebases.

## Features

- **Real-time monitoring** — CPU load, RAM usage and temp-file size with animated charts and trend lines
- **One-click maintenance** — temp files, browser caches, DNS cache, system caches, thumbnails, recycle bin
- **Memory optimization** — working-set trimming for idle processes
- **Registry maintenance** — basic registry cleanup
- **104 languages** — automatic detection from Windows UI language, system locale or keyboard layout
- **Admin auto-elevation** — the window opens without asking for permission; Windows asks once, only when a cleanup starts, and only for the cleanup itself

## Requirements

- Windows 10/11 (x64)
- Python 3.10+ (only to run from source)

## Run from source

```powershell
git clone https://github.com/0noxtackore/Fluxckore.git fluxckore
cd fluxckore
pip install -r requirements.txt
python -m fluxckore
```

## Build the executable

```powershell
pip install -r requirements.txt pyinstaller
pyinstaller packaging/fluxckore.spec --noconfirm
```

Output: `dist/Fluxckore/Fluxckore.exe` (onedir bundle).

To build the Windows installer locally (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php)) — **not published to GitHub Releases**, which ship the portable ZIP only:

```powershell
ISCC.exe /DAppVersion=0.17.0 packaging\Fluxckore.iss
```

## Project structure

```
Fluxckore/
├── fluxckore/                 # The application package
│   ├── app.py              # pywebview backend & orchestration
│   ├── i18n.py             # Translation manager (104 languages)
│   ├── core/               # System monitoring & maintenance logic
│   └── frontend/           # Self-contained HTML/CSS/JS interface
├── assets/                 # README banner, sounds
├── locales/                # translations.json
├── packaging/              # PyInstaller spec, version generator, Inno Setup script
└── .github/workflows/      # Tag-driven CI (build + release)
```

## Releases & versioning

Fluxckore uses **SemVer** (`MAJOR.MINOR.PATCH`). The version lives in `fluxckore/__init__.py`.

Releases are **tag-driven**: pushing a tag like `v0.17.0` triggers the CI workflow (see `.github/workflows/build.yml`), which builds both `onedir` (`Fluxckore.exe` + `_internal/`) and the single-file `.exe`, then attaches both to a GitHub Release. There are no scheduled rebuilds — new binaries only exist when there is a real change.

## Releases & distribution

GitHub Releases contain **both portable and single-file assets** (`v0.17.0` is current):

- `Fluxckore-v0.17.0.exe` — single-file executable (self-contained, no `_internal` folder required).
- `Fluxckore-v0.17.0-Windows-x64.zip` — portable `onedir` bundle with `_internal/`, launchers, frontend and sounds.

Both assets include `LICENSE-APACHE.txt` (Apache 2.0) and `LICENSE-ORACLE.txt` (Oracle UPL), both in English. The executable is unsigned; Windows SmartScreen may ask once until download reputation builds.

This is intentional: the executable is **unsigned**, so Microsoft Defender / SmartScreen shows execution warnings until a code-signing license is purchased. Shipping only the ZIP keeps the release surface free of `.exe` assets that trigger those warnings/errors.

To install: download the ZIP, extract it and run `Run-Fluxckore.bat` (or `Fluxckore.exe` directly - it removes the Windows download mark automatically). Layout: `Fluxckore.exe` + `_internal/`.

The app itself runs **without administrator rights**, so it opens immediately and without a UAC prompt. When you press the start button, Windows asks for permission once and a hidden elevated worker does the system-level cleanup; the window stays open and shows its progress.

The bundle is intentionally small: no pygame/SDL, no numpy, no GUI toolkit (the interface is HTML rendered by WebView2), and sounds use the Windows MCI API directly. Only one instance can run at a time (a second launch brings the open window to the front), and each run gets a private WebView2 profile under `%LOCALAPPDATA%\Fluxckore\browser` instead of the extracted folder — a profile inside a OneDrive/Dropbox folder gets synced while in use and makes the window fail to paint intermittently.

The main window opens immediately with a dark background (no splash screen and no "loading" text), so a slow cold start (antivirus scanning an unsigned bundle) never shows a frozen white window. If the interface cannot start, Fluxckore explains why in a message box instead of staying blank.

## Code signing

Releases ship **unsigned**. Windows SmartScreen may flag the executable until it builds download reputation. This is expected for a new project and does not affect functionality.

## Troubleshooting: `Failed to resolve Python.Runtime.Loader.Initialize`

If `Fluxckore.exe` crashes immediately on startup with:

```
RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize from ...\pythonnet\runtime\Python.Runtime.dll
```

the cause is the **Mark of the Web (MOTW)**: Windows marks files downloaded from the internet with a zone that blocks the .NET runtime used by the interface.

**No command line is required** — Fluxckore removes that mark automatically:

- `Fluxckore.exe` clears the zone mark of its own files at startup, before loading pywebview/pythonnet.
- The ZIP also ships `Run-Fluxckore.bat`: double-click it and it unblocks `Fluxckore.exe` (so SmartScreen stays quiet) and starts the app instantly. The rest of the files are unblocked natively by the app itself, in milliseconds — there is no slow PowerShell pass over the folder any more.

Both paths work out of the box for end users.

## Troubleshooting: blank window / "no responde"

Fluxckore needs the **Microsoft Edge WebView2 Runtime** (preinstalled on Windows 11 and on virtually every Windows 10). If it is missing, the app now says so in a message box instead of showing a white window. Installer: <https://developer.microsoft.com/microsoft-edge/webview2/>.

Every launch writes a timestamped log of each startup phase:

- Startup log (`fluxckore-startup.log`) is written to `%LOCALAPPDATA%\Fluxckore\` (visible, known location), falling back to the executable folder only if unreadable.
- `fluxckore.log` (WebView2 stderr) uses the same folder.

If the window still does not open, send the diagnostic file: Fluxckore copies the log to your **Desktop** as `Fluxckore-DIAGNOSTICO.txt` when startup fails, and the error message tells you so. That file shows the exact phase where the launch stopped.

Useful environment overrides (no commands needed for normal use):

| Variable | Effect |
| --- | --- |
| `FLUXCKORE_WEBVIEW_ARGS` | Extra WebView2/Chromium flags (empty value re-enables GPU rendering). |
| `FLUXCKORE_SKIP_WEBVIEW_CHECK=1` | Skip the WebView2 runtime check. |

## License

[Apache License 2.0](LICENSE-APACHE.txt) · [Oracle Universal Permissive License v1.0](LICENSE-ORACLE.txt) — Copyright (c) 2026 Fluxckore Team.

---

<p align="center">
  <strong>Made with precision. Optimized for performance.</strong>
</p>
