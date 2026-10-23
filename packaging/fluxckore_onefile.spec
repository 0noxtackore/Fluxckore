# -*- mode: python ; coding: utf-8 -*-
# One-file PyInstaller spec for Fluxckore.
# Produces a single self-contained Fluxckore.exe: everything (Python runtime,
# DLLs, WebView2 loader, .NET bridge, frontend, sounds) is packed inside the
# executable, so it runs anywhere without the _internal folder that the onedir
# build (packaging/fluxckore.spec) always requires. Startup is slower because
# Windows extracts the bundle to %TEMP%\_MEIxxxxx on each launch; that is the
# known trade-off of one-file mode and why the portable ZIP (onedir) remains
# the recommended download. This exe exists as the "just click it" option.
# Run from the repository root:
#     pyinstaller packaging/fluxckore_onefile.spec --noconfirm --clean

import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent

# Make sure the Windows version resource exists and matches fluxckore.__version__.
version_file = SPEC_DIR / "version_info.txt"
subprocess.run([sys.executable, str(SPEC_DIR / "make_version_info.py")], check=True)

a = Analysis(
    [str(ROOT / "fluxckore" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "fluxckore" / "frontend"), "fluxckore/frontend"),
        (str(ROOT / "locales" / "translations.json"), "locales"),
        (str(ROOT / "assets" / "sounds" / "notification.mp3"), "assets/sounds"),
        (str(ROOT / "assets" / "sounds" / "danger.mp3"), "assets/sounds"),
    ],
    hiddenimports=[
        "psutil",
        "winreg",
        "webview",
        "webview.platforms.edgechromium",
        "clr",
        "pythonnet",
        "clr_loader",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Mirrors the onedir spec: see its comments for what stays out of the
    # bundle and why (SDL DLLs, Rust crypto module...).
    excludes=["matplotlib", "numpy", "tkinter", "pygame", "PIL", "cryptography"],
    noarchive=False,
)
pyz = PYZ(a.pure)

# One-file EXE: binaries and datas go INSIDE the exe (exclude_binaries=False,
# no COLLECT step). Same version resource, icon (logo-app bolt) and windowed,
# unprivileged settings as the onedir build.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Fluxckore-onefile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_file),
    # The window must run unprivileged: elevated WebView2 is unreliable (it can
    # start but never paint) and it forces a UAC prompt on every launch. The
    # cleaning elevates only its own hidden worker, see core/headless.py.
    uac_admin=False,
    icon=[str(SPEC_DIR / "fluxckore.ico")],
)
