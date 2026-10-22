"""Windows helpers: administrator privileges and bundled-resource paths."""
import ctypes
import os
import sys


# Resource subfolders by file extension (mirrors the original layout).
_SUBFOLDERS = {
    "mp3": ("assets", "sounds"),
    "wav": ("assets", "sounds"),
    "ogg": ("assets", "sounds"),
}


def project_root() -> str:
    """Root folder holding bundled resources (PyInstaller-aware)."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    # fluxckore/core/system.py -> fluxckore/ -> repository root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(filename: str) -> str:
    """Resolve a resource path for both source runs and frozen executables."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    subfolder = os.path.join(*_SUBFOLDERS[ext]) if ext in _SUBFOLDERS else ""
    return os.path.join(project_root(), subfolder, filename)


def config_path() -> str:
    """Path of the optional config.json (language preference)."""
    return os.path.join(project_root(), "config.json")


def webview_data_path() -> str | None:
    """Fixed WebView2 profile folder under ``%LOCALAPPDATA%``.

    Without an explicit folder WebView2 creates ``Fluxckore.exe.WebView2`` next to
    the executable — that is, inside the extracted portable folder. If the user
    extracted the ZIP into a OneDrive/Dropbox folder or a read-only location,
    the browser profile is synced or locked while in use and the window
    intermittently fails to paint. A local, per-user folder avoids both.

    Returns ``None`` when no writable folder can be created, so the caller can
    let WebView2 choose its default instead of failing to start.
    """
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    path = os.path.join(base, "Fluxckore", "WebView2")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None
    return path


def frontend_path() -> str:
    """Path of the self-contained HTML/CSS/JS interface (same relative path
    in source runs and in the frozen bundle)."""
    return os.path.join(project_root(), "fluxckore", "frontend", "index.html")


def is_admin() -> bool:
    """Check whether the process runs with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> None:
    """Relaunch the application elevated (UAC) if not already admin."""
    if is_admin():
        return
    try:
        params = " ".join(sys.argv[1:])
        if getattr(sys, "frozen", False):
            # Frozen executable: relaunch the exe itself.
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                params if params else None,
                None,
                1,
            )
        else:
            # Source run: relaunch with "-m fluxckore" from the project
            # root. Running __main__.py directly would break the package
            # context (ModuleNotFoundError) and the elevated window would
            # flash and close instantly.
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f"-m fluxckore {params}".strip(),
                project_root(),
                1,
            )
        sys.exit(0)
    except Exception as e:
        print(f"Error requesting privilege elevation: {e}")
        sys.exit(1)
