"""
AniWorld-Downloader main entry point.
"""

import sys
import logging
from typing import NoReturn

from .entry import aniworld
from .config import VERSION, IS_NEWEST_VERSION


def set_terminal_title() -> None:
    """Set the terminal window title with version and update status."""
    title = f"AniWorld-Downloader v.{VERSION}"
    if not IS_NEWEST_VERSION:
        title += " (Update Available)"

    if sys.platform == "win32":
        # Use Windows API for setting console title
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except (AttributeError, OSError):
            # Fallback to ANSI escape sequence (works in Windows Terminal)
            print(f"\033]0;{title}\007", end="", flush=True)
    else:
        # ANSI escape sequence for Unix-like systems
        print(f"\033]0;{title}\007", end="", flush=True)


def main() -> NoReturn:
    """
    Main entry point for the AniWorld-Downloader application.

    Sets up the terminal title and launches the main application.
    Handles graceful shutdown on keyboard interrupt.
    """
    try:
        set_terminal_title()
        aniworld()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as err:
        logging.error("Unexpected error: %s", err, exc_info=True)
        print(f"\nAn unexpected error occurred: {err}", file=sys.stderr)
        print("Please check the logs for more details.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
