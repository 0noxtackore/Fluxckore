"""Guarantee that only one Fluxop instance runs at a time.

WebView2 keeps a user data folder locked and writes to it continuously. Two
instances sharing it (easy to trigger: the first start looks slow, so the user
double-clicks again) fight over that folder and the result is exactly the
intermittent behaviour users report: a window that never paints, a second app
that opens and closes, or a UI that stops responding.

The check uses a named mutex, which the OS releases automatically when the
process ends (even after a crash), so a stale lock can never block a launch.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

_ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = "Local\\Fluxop.SingleInstance"
_TITLE = "Fluxop"

_handle = None


def acquire() -> bool:
    """Return True when this process is the first (and only) instance."""
    global _handle
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = (
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if not handle:
            return True  # never block the app because of a mutex failure
        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        _handle = handle  # keep it alive for the whole process lifetime
        return True
    except Exception:
        return True


def focus_existing(timeout: float = 4.0) -> bool:
    """Bring the already running window to the front.

    The first instance may still be starting (its window is hidden until the
    page is ready), so retry for a few seconds before giving up.
    """
    import time

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.FindWindowW.restype = wintypes.HWND
        user32.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
        user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.SetForegroundWindow.argtypes = (wintypes.HWND,)

        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            hwnd = user32.FindWindowW(None, _TITLE)
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.25)
    except Exception:
        return False
