"""Minimal native splash window shown while the interface starts.

WebView2 takes several seconds to come up (longer on a cold, unsigned bundle
that antivirus is scanning). The main window is hidden until the page is
ready, so this small Win32 window gives immediate feedback without pulling in
tkinter, .NET or a second webview.

Everything is best-effort: if the window cannot be created the app simply
starts without a splash.
"""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

_WS_POPUP = 0x80000000
_WS_VISIBLE = 0x10000000
_WS_EX_TOPMOST = 0x00000008
_WS_EX_TOOLWINDOW = 0x00000080
_SS_CENTER = 0x00000001
_SS_CENTERIMAGE = 0x00000200
_WM_SETFONT = 0x0030
_PM_REMOVE = 0x0001
_FW_NORMAL = 400
_DEFAULT_CHARSET = 1
_CLEARTYPE_QUALITY = 5

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

_user32.CreateWindowExW.restype = wintypes.HWND
_user32.CreateWindowExW.argtypes = (
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
)
_user32.GetSystemMetrics.restype = ctypes.c_int
_user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
_user32.SendMessageW.restype = ctypes.c_void_p
_user32.SendMessageW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
_user32.IsWindow.restype = wintypes.BOOL
_user32.IsWindow.argtypes = (wintypes.HWND,)
_user32.PeekMessageW.argtypes = (
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
)
_user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
_user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
_user32.DestroyWindow.argtypes = (wintypes.HWND,)

_gdi32.CreateFontW.restype = wintypes.HFONT
_gdi32.CreateFontW.argtypes = (
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPCWSTR,
)
_gdi32.DeleteObject.argtypes = (wintypes.HGDIOBJ,)


class Splash:
    """Small always-on-top window with a "loading" message."""

    def __init__(self, text: str = "Fluxop  -  cargando la interfaz...", width: int = 460, height: int = 120):
        self._text = text
        self._width = width
        self._height = height
        self._stop = threading.Event()
        self._hwnd = None
        self._font = None

    def start(self) -> "Splash":
        threading.Thread(target=self._run, daemon=True, name="fluxop-splash").start()
        return self

    def close(self) -> None:
        """Ask the splash to close (it destroys its window within ~20 ms)."""
        self._stop.set()

    # ------------------------------------------------------------------
    def _run(self) -> None:
        if not self._create():
            self._destroy()
            return
        try:
            message = wintypes.MSG()
            while not self._stop.is_set() and _user32.IsWindow(self._hwnd):
                while _user32.PeekMessageW(
                    ctypes.byref(message), None, 0, 0, _PM_REMOVE
                ):
                    _user32.TranslateMessage(ctypes.byref(message))
                    _user32.DispatchMessageW(ctypes.byref(message))
                time.sleep(0.02)
        except Exception:
            pass
        finally:
            self._destroy()

    def _create(self) -> bool:
        try:
            screen_width = _user32.GetSystemMetrics(0)
            screen_height = _user32.GetSystemMetrics(1)
            x = max(0, (screen_width - self._width) // 2)
            y = max(0, (screen_height - self._height) // 2)

            hwnd = _user32.CreateWindowExW(
                _WS_EX_TOPMOST | _WS_EX_TOOLWINDOW,
                "STATIC",
                self._text,
                _WS_POPUP | _WS_VISIBLE | _SS_CENTER | _SS_CENTERIMAGE,
                x,
                y,
                self._width,
                self._height,
                None,
                None,
                None,
                None,
            )
            if not hwnd:
                return False
            self._hwnd = hwnd

            # The font is cosmetic: never abandon the window if it fails.
            try:
                font = _gdi32.CreateFontW(
                    -20, 0, 0, 0, _FW_NORMAL, 0, 0, 0,
                    _DEFAULT_CHARSET, 0, 0, _CLEARTYPE_QUALITY, 0,
                    "Segoe UI",
                )
                if font:
                    self._font = font
                    _user32.SendMessageW(
                        hwnd, _WM_SETFONT, wintypes.WPARAM(font), wintypes.LPARAM(1)
                    )
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _destroy(self) -> None:
        try:
            if self._hwnd:
                _user32.DestroyWindow(self._hwnd)
                self._hwnd = None
        except Exception:
            pass
        try:
            if self._font:
                _gdi32.DeleteObject(self._font)
                self._font = None
        except Exception:
            pass
