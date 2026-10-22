"""Remove the "Mark of the Web" (Zone.Identifier) from the application files.

Windows marks every file downloaded from the internet with a
``Zone.Identifier`` alternate data stream.  The .NET runtime that pywebview
needs refuses to load managed DLLs carrying that mark, so a frozen build
downloaded from a release crashed with::

    RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize ...

The mark is removed here, at startup, *before* pywebview/pythonnet are
imported, so users never have to run a command themselves: double-clicking
``Fluxckore.exe`` is enough.

Everything is best-effort and never raises: if the streams cannot be removed
the app simply behaves as before.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from ctypes import wintypes

# --- Win32 constants ---------------------------------------------------------
_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_DELETE = 0x00010000
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_DISPOSITION_INFO = 4
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _FileDispositionInfo(ctypes.Structure):
    """Payload of the FileDispositionInfo information class."""

    _fields_ = [("DeleteFile", wintypes.BOOLEAN)]


def _kernel32():
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _open_zone_stream(path: str, access: int):
    """Open the ``Zone.Identifier`` stream of ``path``; ``None`` if absent."""
    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(
        path + ":Zone.Identifier",
        access,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle is None or handle == _INVALID_HANDLE_VALUE:
        return None
    return handle


def _has_zone_mark(path: str) -> bool:
    """True when the file carries an internet zone mark."""
    handle = _open_zone_stream(path, _GENERIC_READ)
    if handle is None:
        return False
    try:
        _kernel32().CloseHandle(handle)
        return True
    except Exception:
        return False


def _remove_zone_stream(path: str) -> bool:
    """Delete the ``Zone.Identifier`` stream of a single file.

    The handle refers to the *stream*, so the disposition removes the zone
    mark only - the file itself is left untouched.
    """
    handle = _open_zone_stream(path, _GENERIC_READ | _GENERIC_WRITE | _DELETE)
    if handle is None:
        return False
    kernel32 = _kernel32()
    try:
        info = _FileDispositionInfo(True)
        return bool(
            kernel32.SetFileInformationByHandle(
                handle,
                _FILE_DISPOSITION_INFO,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
        )
    except Exception:
        return False
    finally:
        try:
            kernel32.CloseHandle(handle)
        except Exception:
            pass


def _powershell_fallback(root: str) -> int:
    """Last resort: ask PowerShell to unblock the folder (built-in cmdlet)."""
    try:
        script = (
            "Get-ChildItem -LiteralPath '{0}' -Recurse -File -ErrorAction "
            "SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"
        ).format(root)
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            check=False,
            capture_output=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return 1
    except Exception:
        return 0


def _app_dir() -> str | None:
    """Folder that holds the executable (frozen build) or ``None``."""
    if not getattr(sys, "frozen", False):
        return None
    return os.path.dirname(os.path.abspath(sys.executable))


def _iter_files(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            yield os.path.join(dirpath, name)


def unblock_app_files() -> int:
    """Remove the internet zone mark from every file of the app folder.

    Returns the number of files that were unblocked. Never raises.
    """
    root = _app_dir()
    if not root or not os.path.isdir(root):
        return 0

    removed = 0
    marked_left = False
    for path in _iter_files(root):
        if _remove_zone_stream(path):
            removed += 1
        elif not marked_left and _has_zone_mark(path):
            marked_left = True

    if removed:
        print(f"[unblock] Internet zone mark removed from {removed} file(s).")
    elif marked_left:
        # The native call did not work on this system: try the built-in
        # PowerShell cmdlet once.
        if _powershell_fallback(root):
            print("[unblock] Internet zone mark removed (PowerShell fallback).")
    return removed
