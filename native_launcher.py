"""
Native desktop launcher for AniWorld Downloader.

Starts the Flask web backend in a daemon thread and opens a pywebview
window pointing at it.  Designed to be compiled into a standalone .exe
via PyInstaller (--onefile --noconsole).
"""

import os
import sys
import socket
import threading
import time
import traceback
import types
import logging
import tempfile
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ---------------------------------------------------------------------------
# Crash log – with --noconsole there is no stderr, so dump errors to a file
# the user can inspect.
# ---------------------------------------------------------------------------
_LOG_FILE = os.path.join(tempfile.gettempdir(), "streamer_native.log")
logging.basicConfig(
    filename=_LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

PORT = 5000


def _show_error(message: str) -> None:
    """Show an error to the user even when running without a console."""
    logging.critical(message)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, message, "Streamer - Error", 0x10,  # MB_ICONERROR
        )
    except Exception:
        # Not on Windows or ctypes unavailable – write to stderr as fallback
        print(message, file=sys.stderr)


def _wait_for_server(host: str = "127.0.0.1", port: int = PORT, timeout: int = 30) -> bool:
    """Block until the Flask server is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def start_backend() -> None:
    """Start the Flask web interface (blocking – run in a daemon thread)."""
    try:
        from aniworld.web.app import start_web_interface

        args = types.SimpleNamespace(
            web_ui=True,
            web_port=PORT,
            web_expose=False,
            enable_web_auth=False,
            no_browser=True,
            debug=False,
            output_dir=None,
            live=False,
        )
        start_web_interface(args, port=PORT, debug=False)
    except Exception:
        logging.exception("Backend failed to start")
        _show_error(
            "The Streamer backend failed to start.\n\n"
            f"Details have been written to:\n{_LOG_FILE}"
        )


def main() -> None:
    try:
        import webview
    except ImportError:
        _show_error("pywebview is not installed.  Cannot open native window.")
        sys.exit(1)

    # Strip argv so argparse (if triggered internally) sees no flags.
    sys.argv = [sys.argv[0]]

    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    if not _wait_for_server():
        _show_error(
            "The backend did not start within 30 seconds.\n\n"
            f"Check the log file for details:\n{_LOG_FILE}"
        )
        sys.exit(1)

    webview.create_window(
        title="Streamer",
        url=f"http://127.0.0.1:{PORT}",
        width=1200,
        height=800,
    )
    webview.start()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Unhandled exception in native launcher")
        _show_error(
            f"An unexpected error occurred.\n\n"
            f"Details have been written to:\n{_LOG_FILE}"
        )
        sys.exit(1)
