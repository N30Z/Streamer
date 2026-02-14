import logging
import os
import pathlib
import platform
import tempfile
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from packaging.version import Version, InvalidVersion
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import requests
from fake_useragent import UserAgent



#########################################################################################
# Global Constants
#########################################################################################

ANIWORLD_TO = "https://aniworld.to"
S_TO = "https://s.to"
MOVIE4K_SX = "https://movie4k.sx"

# Supported streaming sites with their URL patterns
SUPPORTED_SITES = {
    "aniworld.to": {"base_url": ANIWORLD_TO, "stream_path": "anime/stream"},
    "s.to": {"base_url": S_TO, "stream_path": "serie"},
    "movie4k.sx": {"base_url": MOVIE4K_SX, "stream_path": "watch", "type": "movie"},
}

# Language code mappings for consistent handling
LANGUAGE_CODES_ANIWORLD = {
    "German Dub": 1,
    "English Sub": 2,
    "German Sub": 3,
}
LANGUAGE_NAMES_ANIWORLD = {v: k for k, v in LANGUAGE_CODES_ANIWORLD.items()}

LANGUAGE_CODES_STO = {
    "German Dub": 1,
    "English Dub": 2,
    "German Sub": 3,
}
LANGUAGE_NAMES_STO = {v: k for k, v in LANGUAGE_CODES_STO.items()}

# movie4k.sx uses different language codes
LANGUAGE_CODES_MOVIE4K = {
    "Deutsch": 2,
    "English": 3,
}
LANGUAGE_NAMES_MOVIE4K = {v: k for k, v in LANGUAGE_CODES_MOVIE4K.items()}

# Site-specific language mappings
SITE_LANGUAGE_CODES = {
    "aniworld.to": LANGUAGE_CODES_ANIWORLD,
    "s.to": LANGUAGE_CODES_STO,
    "movie4k.sx": LANGUAGE_CODES_MOVIE4K,
}

SITE_LANGUAGE_NAMES = {
    "aniworld.to": LANGUAGE_NAMES_ANIWORLD,
    "s.to": LANGUAGE_NAMES_STO,
    "movie4k.sx": LANGUAGE_NAMES_MOVIE4K,
}

#########################################################################################
# Logging Configuration
#########################################################################################

log_file_path = os.path.join(tempfile.gettempdir(), "aniworld.log")


class CriticalErrorHandler(logging.Handler):
    """A custom logging handler that raises SystemExit on CRITICAL log records."""

    def emit(self, record):
        if record.levelno == logging.CRITICAL:
            raise SystemExit(record.getMessage())


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(name)s:%(funcName)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode="w", encoding="utf-8"),
        CriticalErrorHandler(),
    ],
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(
    logging.Formatter("%(levelname)s:%(name)s:%(funcName)s: %(message)s")
)
# Handle Unicode gracefully on Windows console
if hasattr(console_handler.stream, 'reconfigure'):
    try:
        console_handler.stream.reconfigure(errors='replace')
    except Exception:
        pass  # Ignore if reconfigure fails
logging.getLogger().addHandler(console_handler)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("charset_normalizer").setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("bs4.dammit").setLevel(logging.ERROR)

urllib3.disable_warnings(InsecureRequestWarning)

#########################################################################################
# Default Configuration Constants
#########################################################################################

DEFAULT_REQUEST_TIMEOUT = 30

try:
    VERSION = version("aniworld")
except PackageNotFoundError:
    VERSION = ""


@lru_cache(maxsize=1)
def get_latest_github_version():
    """Get latest GitHub version with caching to avoid repeated API calls"""
    try:
        url = "https://api.github.com/repos/phoenixthrush/AniWorld-Downloader/releases/latest"
        response = requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
        return (
            response.json().get("tag_name", "") if response.status_code == 200 else ""
        )
    except requests.RequestException as err:
        logging.error("Error fetching latest release: %s", err)
        return ""


def is_newest_version():
    """
    Checks if the current version of the application is the newest available on GitHub.

    Returns:
        tuple:
            - latest (Version or None): The latest version found on GitHub, or None if unavailable.
            - is_newest (bool): True if the current version is up-to-date or newer, False otherwise.

    Notes:
        - If the current version is not set or cannot be determined, returns (None, False).
        - Handles invalid version formats and network errors gracefully, logging them as errors.
    """
    if not VERSION:
        return None, False

    try:
        current = Version(VERSION.lstrip("v").lstrip("."))
        latest_str = get_latest_github_version().lstrip("v").lstrip(".")
        if not latest_str:
            return None, False
        latest = Version(latest_str)
        return latest, current >= latest
    except InvalidVersion as err:
        logging.error("Invalid version format: %s", err)
    except requests.RequestException as err:
        logging.error("Network error while fetching latest version: %s", err)

    return None, False


try:
    LATEST_VERSION, IS_NEWEST_VERSION = is_newest_version()
except (TypeError, ValueError):  # GitHub API Rate Limit (60/h) #52 or other errors
    LATEST_VERSION = None
    IS_NEWEST_VERSION = True

PLATFORM_SYSTEM = platform.system()

# Cache platform check for efficiency
_IS_WINDOWS = PLATFORM_SYSTEM == "Windows"

SUPPORTED_PROVIDERS = (
    "LoadX",
    "VOE",
    "Vidmoly",
    "Filemoon",
    "Luluvdo",
    "Doodstream",
    "Vidoza",
    "SpeedFiles",
    "Streamtape",
)

#########################################################################################


# User Agents - Lazy initialization to avoid UserAgent() call on import
@lru_cache(maxsize=1)
def get_random_user_agent():
    """Get random user agent with caching to avoid repeated UserAgent() calls"""
    ua = UserAgent(os=["Windows", "Mac OS X"])
    return ua.random


# Backward compatibility - keep RANDOM_USER_AGENT as a constant
RANDOM_USER_AGENT = get_random_user_agent()

LULUVDO_USER_AGENT = (
    "Mozilla/5.0 (Android 15; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0"
)

# Use lazy getter for user agents in headers


def _get_provider_headers_d():
    return {
        "Vidmoly": ['Referer: "https://vidmoly.net"'],
        "Doodstream": ['Referer: "https://dood.li/"'],
        "VOE": [f"User-Agent: {RANDOM_USER_AGENT}"],
        "LoadX": ["Accept: */*"],
        "Filemoon": [
            f"User-Agent: {RANDOM_USER_AGENT}",
            'Referer: "https://filemoon.to"',
        ],
        "Luluvdo": [
            f"User-Agent: {LULUVDO_USER_AGENT}",
            "Accept-Language: de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            'Origin: "https://luluvdo.com"',
            'Referer: "https://luluvdo.com/"',
        ],
    }


def get_provider_headers_d():
    """Return provider headers used when downloading"""
    return _get_provider_headers_d()


PROVIDER_HEADERS_D = get_provider_headers_d()


USES_DEFAULT_PROVIDER = False

DEFAULT_ACTION = "Download"
DEFAULT_DOWNLOAD_PATH = pathlib.Path.home() / "Downloads"
DEFAULT_KEEP_WATCHING = False
DEFAULT_LANGUAGE = "German Sub"
DEFAULT_ONLY_COMMAND = False
DEFAULT_ONLY_DIRECT_LINK = False
DEFAULT_PROVIDER = "VOE"
# Number of concurrent parallel downloads in web interface
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 5
# Seconds to wait per provider when auto-selecting
DEFAULT_PROVIDER_TIMEOUT = 5

# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
INVALID_PATH_CHARS = ("<", ">", ":", '"', "/", "\\", "|", "?", "*", "&")

#########################################################################################

if __name__ == "__main__":
    pass
