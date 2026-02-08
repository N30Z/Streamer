"""
Auto-download FFmpeg if not found on the system.

Downloads pre-built static FFmpeg binaries from GitHub (BtbN/FFmpeg-Builds)
and stores them in the application data directory.
"""

import logging
import os
import platform
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Optional


# Download URLs for pre-built FFmpeg binaries
_FFMPEG_URLS = {
    ("Windows", "AMD64"): "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    ("Windows", "x86"): "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    ("Linux", "x86_64"): "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
    ("Linux", "aarch64"): "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz",
}


def _get_ffmpeg_dir() -> Path:
    """Get the directory where FFmpeg should be stored."""
    if os.path.exists("/.dockerenv"):
        base = Path("/app/data")
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "aniworld"
    else:
        base = Path.home() / ".local" / "share" / "aniworld"

    ffmpeg_dir = base / "ffmpeg"
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    return ffmpeg_dir


def _get_binary_names() -> list:
    """Get the platform-specific binary names for ffmpeg and ffprobe."""
    ext = ".exe" if os.name == "nt" else ""
    return [f"ffmpeg{ext}", f"ffprobe{ext}"]


def _check_pyinstaller_bundle() -> Optional[str]:
    """Check for FFmpeg in PyInstaller bundle directories."""
    if not getattr(sys, 'frozen', False):
        return None

    bundle_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    for name in ['ffmpeg.exe', 'ffmpeg']:
        if (bundle_dir / name).exists():
            return str(bundle_dir)

    exe_dir = Path(sys.executable).parent
    for name in ['ffmpeg.exe', 'ffmpeg']:
        if (exe_dir / name).exists():
            return str(exe_dir)

    return None


def find_ffmpeg() -> Optional[str]:
    """Find FFmpeg on the system.

    Checks in order:
    1. PyInstaller bundle directories
    2. System PATH
    3. App data directory (auto-downloaded location)

    Returns:
        Path to the directory containing ffmpeg, or None if not found.
    """
    # 1. PyInstaller bundle
    bundled = _check_pyinstaller_bundle()
    if bundled:
        return bundled

    # 2. System PATH
    if shutil.which('ffmpeg'):
        return None  # Let yt-dlp find it in PATH

    # 3. App data directory
    ffmpeg_dir = _get_ffmpeg_dir()
    ffmpeg_binary = _get_binary_names()[0]  # ffmpeg or ffmpeg.exe
    if (ffmpeg_dir / ffmpeg_binary).exists():
        return str(ffmpeg_dir)

    return None


def _get_download_url() -> Optional[str]:
    """Get the FFmpeg download URL for the current platform."""
    system = platform.system()
    machine = platform.machine()

    url = _FFMPEG_URLS.get((system, machine))
    if url:
        return url

    logging.warning(
        "No FFmpeg download available for %s/%s. Please install FFmpeg manually.",
        system, machine
    )
    return None


def _extract_zip(archive_path: Path, ffmpeg_dir: Path) -> list:
    """Extract ffmpeg and ffprobe from a zip archive."""
    extracted = []
    binary_names = _get_binary_names()
    with zipfile.ZipFile(archive_path, 'r') as zf:
        for member in zf.namelist():
            for binary_name in binary_names:
                if member.endswith(f'bin/{binary_name}'):
                    path = zf.extract(member, ffmpeg_dir)
                    extracted.append(Path(path))
    return extracted


def _extract_tar(archive_path: Path, ffmpeg_dir: Path) -> list:
    """Extract ffmpeg and ffprobe from a tar archive."""
    import tarfile

    extracted = []
    binary_names = _get_binary_names()
    with tarfile.open(archive_path, 'r:xz') as tf:
        for member in tf.getmembers():
            for binary_name in binary_names:
                if member.name.endswith(f'bin/{binary_name}'):
                    tf.extract(member, ffmpeg_dir)
                    extracted.append(ffmpeg_dir / member.name)
    return extracted


def download_ffmpeg() -> Optional[str]:
    """Download FFmpeg binary for the current platform.

    Returns:
        Path to the directory containing the downloaded ffmpeg, or None on failure.
    """
    import requests

    url = _get_download_url()
    if not url:
        return None

    ffmpeg_dir = _get_ffmpeg_dir()

    # Determine archive type
    is_zip = url.endswith('.zip')
    archive_ext = '.zip' if is_zip else '.tar.xz'
    archive_path = ffmpeg_dir / f'ffmpeg_download{archive_ext}'

    try:
        logging.info("Downloading FFmpeg from %s ...", url)

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        # Download with progress logging
        total = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(archive_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0 and downloaded % (10 * 1024 * 1024) < 8192:
                    pct = int(downloaded * 100 / total)
                    logging.info("FFmpeg download progress: %d%%", pct)

        logging.info("Extracting FFmpeg...")

        # Extract ffmpeg and ffprobe binaries
        if is_zip:
            extracted_paths = _extract_zip(archive_path, ffmpeg_dir)
        else:
            extracted_paths = _extract_tar(archive_path, ffmpeg_dir)

        if not extracted_paths:
            logging.error("Failed to find FFmpeg binaries in downloaded archive.")
            return None

        # Move binaries to the ffmpeg directory root
        for extracted_path in extracted_paths:
            final_path = ffmpeg_dir / extracted_path.name
            if extracted_path != final_path:
                shutil.move(str(extracted_path), str(final_path))
            # Make executable on Unix
            if os.name != "nt":
                final_path.chmod(0o755)

        # Clean up archive and leftover extracted directories
        archive_path.unlink(missing_ok=True)
        for item in ffmpeg_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)

        logging.info("FFmpeg installed successfully at %s", ffmpeg_dir)
        return str(ffmpeg_dir)

    except Exception as err:
        logging.warning("Failed to download FFmpeg: %s", err)
        # Clean up partial downloads
        archive_path.unlink(missing_ok=True)
        return None


def ensure_ffmpeg() -> Optional[str]:
    """Ensure FFmpeg is available, downloading it if necessary.

    Returns:
        Path to the directory containing ffmpeg, or None if unavailable.
    """
    location = find_ffmpeg()
    if location is not None:
        return location

    # ffmpeg not found anywhere - check if it's in PATH (find_ffmpeg returns None for PATH)
    if shutil.which('ffmpeg'):
        return None  # It's in PATH, yt-dlp will find it

    logging.info("FFmpeg not found. Attempting automatic download...")
    return download_ffmpeg()
