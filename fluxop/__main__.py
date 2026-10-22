"""Allow running with ``python -m fluxop`` (also the PyInstaller entry point)."""
import os
import sys


def _native_error(text: str) -> None:
    """Show a message box: the frozen build is windowed, with no console."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "Fluxop", 0x10)
    except Exception:
        pass


def _configure_webview2() -> None:
    """Avoid blank/frozen WebView2 windows on machines with broken drivers.

    WebView2 renders the interface with GPU compositing by default; on some
    Windows installations that produces a white window that never paints.
    Software rendering is slower but always paints. Users can override the
    flags with ``FLUXOP_WEBVIEW_ARGS`` (e.g. an empty value re-enables the
    GPU).
    """
    if "FLUXOP_WEBVIEW_ARGS" in os.environ:
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = os.environ[
            "FLUXOP_WEBVIEW_ARGS"
        ]
        return
    os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--disable-gpu")


if __name__ == "__main__":
    # Bootstrap logger: available before pywebview/pythonnet are imported and
    # even when the app crashes, which is the only way to diagnose a windowed
    # build that never shows a window.
    try:
        from fluxop.core import startup_log
    except Exception:  # pragma: no cover - broken installation
        startup_log = None

    def _log(message: str) -> None:
        if startup_log is not None:
            startup_log.log(message)

    def _log_exc(prefix: str) -> None:
        if startup_log is not None:
            startup_log.log_exception(prefix)

    def _detail_path() -> str:
        if startup_log is not None:
            return startup_log.export_desktop_copy()
        return "fluxop-startup.log"

    _log("launcher: starting")
    _configure_webview2()
    _log(
        "launcher: webview2 args="
        + os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
    )

    # Remove the Windows "Mark of the Web" from the app files BEFORE
    # pywebview/pythonnet are imported: the .NET runtime refuses to load
    # managed DLLs that carry that mark, which broke the frozen build.
    # This runs automatically, so users never need to type a command.
    try:
        from fluxop.core.unblock import unblock_app_files

        removed = unblock_app_files()
        _log(f"launcher: unblock done ({removed} file(s))")
    except Exception:
        _log_exc("launcher: unblock failed")

    try:
        _log("launcher: importing fluxop.app")
        from fluxop.app import main

        _log("launcher: import ok, entering main()")
        main()
    except SystemExit:
        raise
    except Exception:
        _log_exc("CRITICAL: unhandled exception during startup")
        _native_error(
            "Fluxop no pudo iniciarse.\n\n"
            f"El detalle se guardó en:\n{_detail_path()}\n\n"
            "Envíame ese archivo para poder diagnosticarlo."
        )
        sys.exit(1)
