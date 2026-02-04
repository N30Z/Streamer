"""
Native desktop launcher for AniWorld Downloader.

Starts the Flask web backend in a daemon thread and opens a pywebview
window pointing at it.  Designed to be compiled into a standalone .exe
via PyInstaller (--onefile --noconsole).
"""

import os
import sys
import threading
import time
import types
import logging

# ---------------------------------------------------------------------------
# PyInstaller helper: when running from a --onefile bundle the unpacked
# temporary directory (_MEIPASS) must be on sys.path so that ``import
# aniworld`` resolves correctly.
# ---------------------------------------------------------------------------
_BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_BUNDLE_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _BUNDLE_DIR not in sys.path:
    sys.path.insert(0, _BUNDLE_DIR)

import webview  # noqa: E402  (must come after path fixup)

PORT = 5000


def _wait_for_server(host: str = "127.0.0.1", port: int = PORT, timeout: int = 30) -> bool:
    """Block until the Flask server is accepting connections (or *timeout* seconds elapse)."""
    import socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def start_backend() -> None:
    """Start the Flask web interface in the current thread (blocking)."""
    try:
        from aniworld.web.app import start_web_interface

        # Build a minimal namespace that looks like argparse output so that
        # start_web_interface behaves correctly without touching sys.argv.
        args = types.SimpleNamespace(
            web_ui=True,
            web_port=PORT,
            web_expose=False,
            enable_web_auth=False,
            no_browser=True,       # pywebview provides the window
            debug=False,
            output_dir=None,
            live=False,
        )
        start_web_interface(args, port=PORT, debug=False)
    except Exception:
        logging.exception("Backend failed to start")


def main() -> None:
    # Silence argv so argparse (if it still gets invoked somewhere) sees
    # nothing beyond the program name.
    sys.argv = [sys.argv[0]]

    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    if not _wait_for_server():
        print("ERROR: Backend did not start in time.", file=sys.stderr)
        sys.exit(1)

    webview.create_window(
        title="Streamer",
        url=f"http://127.0.0.1:{PORT}",
        width=1200,
        height=800,
    )
    webview.start()


if __name__ == "__main__":
    main()
