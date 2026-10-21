<p align="center">
  <img src="assets/readme-banner.png" alt="Fluxop" width="716">
</p>
<p align="center">
  <strong>System Maintenance & Optimization Suite for Windows</strong><br>
  One app. One codebase. Windows 10/11 (x64).
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
</p>

---

## Overview

Fluxop is a Windows system maintenance suite built with Python and a self-contained HTML/CSS interface rendered by pywebview (Edge WebView2). It provides real-time system monitoring, selectable temporary-file cleanup, memory optimization and registry maintenance through a single dark-themed desktop application.

There is **one edition** of Fluxop. Features evolve in place — no PRO/Beta/Enterprise splits, no parallel codebases.

## Features

- **Real-time monitoring** — CPU load, RAM usage and temp-file size with animated charts and trend lines
- **One-click maintenance** — temp files, browser caches, DNS cache, system caches, thumbnails, recycle bin
- **Memory optimization** — working-set trimming for idle processes
- **Registry maintenance** — basic registry cleanup
- **104 languages** — automatic detection from Windows UI language, system locale or keyboard layout
- **Admin auto-elevation** — requests administrator privileges when needed

## Requirements

- Windows 10/11 (x64)
- Python 3.10+ (only to run from source)

## Run from source

```powershell
git clone https://github.com/0noxtackore/Fluxop.git
cd Fluxop
pip install -r requirements.txt
python -m fluxop
```

## Build the executable

```powershell
pip install -r requirements.txt pyinstaller
pyinstaller packaging/fluxop.spec --noconfirm
```

Output: `dist/Fluxop/Fluxop.exe` (onedir bundle).

To build the Windows installer locally (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php)) — **not published to GitHub Releases**, which ship the portable ZIP only:

```powershell
ISCC.exe /DAppVersion=8.0.2 packaging\Fluxop.iss
```

## Project structure

```
Fluxop/
├── fluxop/                 # The application package
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

Fluxop uses **SemVer** (`MAJOR.MINOR.PATCH`). The version lives in `fluxop/__init__.py`.

Releases are **tag-driven**: pushing a tag like `v8.0.2` triggers the CI workflow, which builds the executable and publishes a GitHub Release with the portable ZIP. There are no scheduled rebuilds — a new binary only exists when there is a real change.

## Releases & distribution

GitHub Releases contain **only a portable ZIP** (`Fluxop-<version>-portable.zip`) — no `.exe` installer is attached.

This is intentional: the executable is **unsigned**, so Microsoft Defender / SmartScreen shows execution warnings until a code-signing license is purchased. Shipping only the ZIP keeps the release surface free of `.exe` assets that trigger those warnings/errors.

To install: download the ZIP, extract it and run `Fluxop.exe` from the `Fluxop-app/` folder (onedir layout: `Fluxop.exe` + `_internal/`). Requires admin privileges for some maintenance tasks (auto-elevation is built in).

## Code signing

Releases ship **unsigned**. Windows SmartScreen may flag the executable until it builds download reputation. This is expected for a new project and does not affect functionality.

## Troubleshooting: `Failed to resolve Python.Runtime.Loader.Initialize`

If `Fluxop.exe` crashes immediately on startup with:

```
RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize from ...\pythonnet\runtime\Python.Runtime.dll
```

the cause is almost always the **Mark of the Web (MOTW)** flag on the downloaded files, or a missing .NET runtime. Fix:

```powershell
Unblock-File -Path C:\Users\PC\Downloads\Fluxop-8.0.2-portable -Recurse
```

(or right-click the `Fluxop-app` folder → Properties → check *Unblock* → Apply).

`run.bat` performs this automatically before launching. After unblocking, run `Fluxop.exe` again and it should start.

## License

[MIT License](LICENSE) — Copyright (c) 2026 Fluxop Team.

---

<p align="center">
  <strong>Made with precision. Optimized for performance.</strong>
</p>
