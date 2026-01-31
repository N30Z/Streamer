import logging
from typing import Optional

# Set of characters not allowed in filenames on most filesystems
INVALID_PATH_CHARS = set(r'<>:"/\\|?*')


def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters from a filename.
    Used to ensure compatibility across different OS filesystems.
    """
    return "".join(char for char in filename if char not in INVALID_PATH_CHARS)


def get_direct_link(episode, episode_title: str) -> Optional[str]:
    """
    Try to get a direct link for the episode.
    Log a warning and return None if it fails.
    """
    try:
        return episode.get_direct_link()
    except Exception as err:
        logging.warning(
            'Something went wrong with "%s".\nError while trying to find a direct link: %s',
            episode_title,
            err,
        )
        return None
