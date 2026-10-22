# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Fluxop (single edition, onedir).
# Run from the repository root:
#     pyinstaller packaging/fluxop.spec --noconfirm
# Relative paths are resolved against this spec file's directory.

import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent

# Make sure the Windows version resource exists and matches fluxop.__version__.
version_file = SPEC_DIR / "version_info.txt"
subprocess.run([sys.executable, str(SPEC_DIR / "make_version_info.py")], check=True)

a = Analysis(
    [str(ROOT / "fluxop" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "fluxop" / "frontend"), "fluxop/frontend"),
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
        "System",
        "System.Windows.Forms",
        "System.Drawing",
        "System.Threading",
        "System.Collections",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # pygame is not used any more (sounds go through the Windows MCI API):
    # excluding it keeps the SDL DLLs (~21 MB) out of the portable bundle,
    # which makes the ZIP smaller and the first launch faster.
    # cryptography is only imported by pywebview when it is asked to generate
    # an HTTPS certificate (``webview.start(ssl=True)``), which this app never
    # does: excluding it removes another ~15 MB (Rust extension + OpenSSL).
    excludes=["matplotlib", "numpy", "tkinter", "pygame", "PIL", "cryptography"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Fluxop",
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
    uac_admin=True,
    icon=[str(SPEC_DIR / "fluxop.ico")],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Fluxop",
)
