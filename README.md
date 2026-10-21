<p align="center">
  <img src="assets/readme-banner.png" alt="FluxOptimizer" width="440">
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

FluxOptimizer is a Windows system maintenance suite built with Python and a self-contained HTML/CSS interface rendered by pywebview (Edge WebView2). It provides real-time system monitoring, selectable temporary-file cleanup, memory optimization and registry maintenance through a single dark-themed desktop application.

There is **one edition** of FluxOptimizer. Features evolve in place — no PRO/Beta/Enterprise splits, no parallel codebases.

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
git clone https://github.com/0noxtackore/FluxOptimizer.git
cd FluxOptimizer
pip install -r requirements.txt
python -m fluxoptimizer
```

## Build the executable

```powershell
pip install -r requirements.txt pyinstaller
pyinstaller packaging/fluxoptimizer.spec --noconfirm
```

Output: `dist/FluxOptimizer/FluxOptimizer.exe` (onedir bundle).

To build the Windows installer (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php)):

```powershell
ISCC.exe /DAppVersion=2.1.0 packaging\FluxOptimizer.iss
```

## Project structure

```
FluxOptimizer/
├── fluxoptimizer/          # The application package
│   ├── app.py              # pywebview backend & orchestration
│   ├── i18n.py             # Translation manager (104 languages)
│   ├── core/               # System monitoring & maintenance logic
│   └── frontend/           # Self-contained HTML/CSS/JS interface
├── assets/                 # Sounds
├── locales/                # translations.json
├── packaging/              # PyInstaller spec, version generator, Inno Setup script
└── .github/workflows/      # Tag-driven CI (build + sign + release)
```

## Releases & versioning

FluxOptimizer uses **SemVer** (`MAJOR.MINOR.PATCH`). The version lives in `fluxoptimizer/__init__.py`.

Releases are **tag-driven**: pushing a tag like `v2.1.0` triggers the CI workflow, which builds the executable, signs it, builds the installer and publishes a GitHub Release. There are no scheduled rebuilds — a new binary only exists when there is a real change.

## Code signing (removes the SmartScreen warning)

Unsigned executables are flagged by Windows SmartScreen/Smart App Control. FluxOptimizer is signed via [SignPath](https://signpath.io), which is **free for open-source projects**:

1. Install the [SignPath GitHub app](https://signpath.org/github) on this repository
2. In SignPath, create a project `FluxOptimizer` with a signing policy `release-signing`
3. Add the repository secrets `SIGNPATH_API_TOKEN` and `SIGNPATH_ORGANIZATION_ID` (GitHub → Settings → Secrets → Actions)

The CI workflow signs every release build automatically when these secrets are present.

## License

[MIT License](LICENSE) — Copyright (c) 2026 FluxOptimizer Team.

---

<p align="center">
  <strong>Made with precision. Optimized for performance.</strong>
</p>
