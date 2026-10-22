"""Notification sounds through the Windows MCI API.

The app only needs two short MP3 files. Playing them used to require pygame,
which pulls the whole SDL stack (~30 MB of DLLs) into the bundle and can block
or fail on machines without an audio device, VMs or RDP sessions. MCI is part
of Windows: ``mciSendStringW`` opens the MP3, plays it asynchronously and
returns immediately, so no third-party dependency is needed.

Every call is best-effort: if audio is unavailable the app simply stays silent.
"""
from __future__ import annotations

import ctypes
import os
import threading

from .system import resource_path

_ALIAS = "fluxop_sound"

_winmm = ctypes.WinDLL("winmm", use_last_error=True)
_winmm.mciSendStringW.restype = ctypes.c_uint
_winmm.mciSendStringW.argtypes = (
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.c_uint,
    ctypes.c_void_p,
)


def _mci(command: str) -> int:
    """Send one MCI command, returning 0 on success."""
    try:
        return _winmm.mciSendStringW(command, None, 0, None)
    except Exception:
        return 1


class SoundPlayer:
    """Plays the bundled notification sounds with the Windows MCI API."""

    def __init__(self, resource_path_fn=resource_path):
        self._paths = {}
        self._lock = threading.Lock()

        for kind, filename in (("success", "notification.mp3"), ("danger", "danger.mp3")):
            try:
                path = resource_path_fn(filename)
                if path and os.path.exists(path):
                    self._paths[kind] = path
            except Exception:
                continue

    @property
    def available(self) -> bool:
        return bool(self._paths)

    def play(self, sound_type):
        """Play a sound without blocking the caller."""
        path = self._paths.get(sound_type)
        if not path:
            return
        threading.Thread(target=self._play_file, args=(path,), daemon=True).start()

    def _play_file(self, path: str) -> None:
        with self._lock:
            try:
                # A previous clip may still hold the alias: close it first so
                # the new one can be opened (MCI allows one open per alias).
                _mci(f"close {_ALIAS}")
                if _mci(f'open "{path}" type mpegvideo alias {_ALIAS}') == 0:
                    _mci(f"play {_ALIAS}")
            except Exception:
                pass
