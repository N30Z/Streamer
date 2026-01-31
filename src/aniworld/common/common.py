import logging
import re
from typing import Dict, List, Set, Tuple

import requests

from ..config import (
    DEFAULT_REQUEST_TIMEOUT,
    ANIWORLD_TO,
    S_TO,
)

# Global cache for season/movie counts to avoid duplicate requests
_ANIME_DATA_CACHE = {}


def _make_request(
    url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT
) -> requests.Response:
    """Make HTTP request with error handling."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as err:
        logging.error("Request failed for %s: %s", url, err)
        raise


def get_season_episode_count(slug: str, link: str = ANIWORLD_TO) -> Dict[int, int]:
    """
    Get episode count for each season with caching.
    Dispatches to the correct site module based on the link.

    Args:
        slug: Anime/series slug from URL
        link: Base URL or episode link used to detect the site

    Returns:
        Dictionary mapping season numbers to episode counts
    """
    cache_key = f"seasons_{slug}"
    if cache_key in _ANIME_DATA_CACHE:
        return _ANIME_DATA_CACHE[cache_key]

    if S_TO in link:
        from ..sites.s_to import get_season_episode_count as _sto_get
        result = _sto_get(slug)
    else:
        from ..sites.aniworld import get_season_episode_count as _aw_get
        result = _aw_get(slug)

    _ANIME_DATA_CACHE[cache_key] = result
    return result


def get_movie_episode_count(slug: str, link: str = ANIWORLD_TO) -> int:
    """
    Get movie count with caching.
    Dispatches to the correct site module based on the link.

    Args:
        slug: Anime/series slug from URL
        link: Base URL or episode link used to detect the site

    Returns:
        Number of movies available
    """
    cache_key = f"movies_{slug}"
    if cache_key in _ANIME_DATA_CACHE:
        return _ANIME_DATA_CACHE[cache_key]

    if S_TO in link:
        from ..sites.s_to import get_movie_episode_count as _sto_get
        result = _sto_get(slug)
    else:
        from ..sites.aniworld import get_movie_episode_count as _aw_get
        result = _aw_get(slug)

    _ANIME_DATA_CACHE[cache_key] = result
    return result


def _natural_sort_key(link_url: str) -> List:
    """Natural sort key for URLs."""
    return [
        int(text) if text.isdigit() else text for text in re.split(r"(\d+)", link_url)
    ]


def _process_base_url(
    base_url: str, arguments, slug_cache: Dict[str, Tuple[Dict[int, int], int]]
) -> Set[str]:
    """Process a single base URL to generate episode links."""
    unique_links = set()
    parts = base_url.split("/")

    if not (
        "episode" not in base_url and "film-" not in base_url or arguments.keep_watching
    ):
        unique_links.add(base_url)
        return unique_links

    try:
        series_slug_index = parts.index("stream") + 1
        series_slug = parts[series_slug_index]

        if series_slug in slug_cache:
            seasons_info, movies_info = slug_cache[series_slug]
        else:
            seasons_info = get_season_episode_count(slug=series_slug, link=base_url)
            movies_info = get_movie_episode_count(slug=series_slug, link=base_url)
            slug_cache[series_slug] = (seasons_info, movies_info)

    except (ValueError, IndexError) as err:
        logging.warning("Failed to parse URL %s: %s", base_url, err)
        unique_links.add(base_url)
        return unique_links

    # Remove trailing slash
    if base_url.endswith("/"):
        base_url = base_url[:-1]

    # Handle keep_watching mode
    if arguments.keep_watching:
        unique_links.update(_process_keep_watching(base_url, seasons_info, movies_info))
    else:
        unique_links.update(
            _process_full_series(base_url, parts, seasons_info, movies_info)
        )

    return unique_links


def _process_keep_watching(
    base_url: str, seasons_info: Dict[int, int], movies_info: int
) -> Set[str]:
    """Process keep_watching mode for URL generation."""
    unique_links = set()

    season_start = 1
    episode_start = 1
    movie_start = 1

    season_match = re.search(r"staffel-(\d+)", base_url)
    episode_match = re.search(r"episode-(\d+)", base_url)
    movie_match = re.search(r"film-(\d+)", base_url)

    if season_match:
        season_start = int(season_match.group(1))
    if episode_match:
        episode_start = int(episode_match.group(1))
    if movie_match:
        movie_start = int(movie_match.group(1))

    raw_url = "/".join(base_url.split("/")[:6])

    if "film" not in base_url:
        for season in range(season_start, len(seasons_info) + 1):
            season_url = f"{raw_url}/staffel-{season}/"
            for episode in range(episode_start, seasons_info[season] + 1):
                unique_links.add(f"{season_url}episode-{episode}")
            episode_start = 1
    else:
        for episode in range(movie_start, movies_info + 1):
            unique_links.add(f"{raw_url}/filme/film-{episode}")

    return unique_links


def _process_full_series(
    base_url: str, parts: List[str], seasons_info: Dict[int, int], movies_info: int
) -> Set[str]:
    """Process full series URL generation."""
    unique_links = set()

    # Handle different URL patterns
    if (
        "staffel" not in base_url
        and "episode" not in base_url
        and "film" not in base_url
    ):
        # Full series
        for season, episodes in seasons_info.items():
            season_url = f"{base_url}/staffel-{season}/"
            for episode in range(1, episodes + 1):
                unique_links.add(f"{season_url}episode-{episode}")
    elif "staffel" in base_url and "episode" not in base_url:
        # Specific season
        try:
            season = int(parts[-1].split("-")[-1])
            if season in seasons_info:
                for episode in range(1, seasons_info[season] + 1):
                    unique_links.add(f"{base_url}/episode-{episode}")
        except (ValueError, IndexError):
            unique_links.add(base_url)
    elif "filme" in base_url and "film-" not in base_url:
        # All movies
        for episode in range(1, movies_info + 1):
            unique_links.add(f"{base_url}/film-{episode}")
    else:
        # Specific episode/movie
        unique_links.add(base_url)

    return unique_links


def generate_links(urls: List[str], arguments) -> List[str]:
    """
    Generate episode/movie links from base URLs.

    Args:
        urls: List of base URLs
        arguments: Command line arguments

    Returns:
        Sorted list of episode/movie URLs
    """
    unique_links = set()
    slug_cache = {}

    for base_url in urls:
        try:
            links = _process_base_url(base_url, arguments, slug_cache)
            unique_links.update(links)
        except Exception as err:
            logging.error("Failed to process URL %s: %s", base_url, err)
            unique_links.add(base_url)

    return sorted(unique_links, key=_natural_sort_key)


if __name__ == "__main__":
    pass
