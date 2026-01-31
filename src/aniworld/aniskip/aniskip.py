import re
import logging
import json
from typing import Dict, Optional, List

import requests
from bs4 import BeautifulSoup

from ..config import DEFAULT_REQUEST_TIMEOUT

# Constants
MAL_ANIME_URL = "https://myanimelist.net/anime/{}"
MAL_SEARCH_URL = "https://myanimelist.net/search/prefix.json?type=anime&keyword={}"


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


def _clean_anime_title(title: str) -> str:
    """Clean anime title for search."""
    cleaned = re.sub(r" \(\d+ episodes\)", "", title)
    return re.sub(r"\s+", "%20", cleaned)


def _find_best_match(search_results: List[Dict]) -> Optional[Dict]:
    """Find best match from search results, excluding OVAs."""
    results = [entry for entry in search_results if "OVA" not in entry.get("name", "")]
    return results[0] if results else None


def _extract_anime_id_from_url(url: str) -> Optional[str]:
    """Extract anime ID from MAL URL."""
    match = re.search(r"/anime/(\d+)", url)
    return match.group(1) if match else None


def _find_sequel_info(soup: BeautifulSoup) -> Optional[str]:
    """Find sequel anime URL from MAL page."""
    sequel_div = soup.find(
        "div", string=lambda text: text and "Sequel" in text and "(TV)" in text
    )

    if not sequel_div:
        return None

    title_div = sequel_div.find_next("div", class_="title")
    if not title_div:
        return None

    link_element = title_div.find("a")
    if not link_element:
        return None

    return link_element.get("href")


def get_mal_id_from_title(title: str, season: int) -> Optional[int]:
    """
    Get MAL ID from anime title and season.

    Args:
        title: Anime title
        season: Season number

    Returns:
        MAL anime ID or None if not found
    """
    logging.debug("Fetching MAL ID for: %s (Season %d)", title, season)

    try:
        keyword = _clean_anime_title(title)
        response = _make_request(MAL_SEARCH_URL.format(keyword))

        logging.debug("MyAnimeList response status code: %d", response.status_code)

        mal_metadata = response.json()
        categories = mal_metadata.get("categories", [])

        if not categories or not categories[0].get("items"):
            logging.error("No search results found for: %s", title)
            return None

        best_match = _find_best_match(categories[0]["items"])
        if not best_match:
            logging.error("No suitable match found for: %s", title)
            return None

        anime_id = best_match["id"]
        logging.debug(
            "Found MAL ID: %s for %s", anime_id, json.dumps(best_match, indent=4)
        )

        # Navigate to correct season
        current_id = anime_id
        for _ in range(season - 1):
            current_id = get_sequel_anime_id(current_id)
            if current_id is None:
                logging.error("Could not find season %d for anime: %s", season, title)
                return None

        return current_id

    except Exception as err:
        logging.error("Failed to get MAL ID for %s: %s", title, err)
        return None


def get_sequel_anime_id(anime_id: int) -> Optional[int]:
    """
    Get sequel anime ID from MAL.

    Args:
        anime_id: Current anime ID

    Returns:
        Sequel anime ID or None if not found
    """
    try:
        response = _make_request(MAL_ANIME_URL.format(anime_id))
        soup = BeautifulSoup(response.text, "html.parser")

        sequel_url = _find_sequel_info(soup)
        if not sequel_url:
            logging.warning("Sequel not found for anime ID: %s", anime_id)
            return None

        sequel_id = _extract_anime_id_from_url(sequel_url)
        if not sequel_id:
            logging.error("Could not extract anime ID from sequel URL: %s", sequel_url)
            return None

        return int(sequel_id)

    except Exception as err:
        logging.error("Failed to get sequel for anime ID %s: %s", anime_id, err)
        return None


if __name__ == "__main__":
    print(get_mal_id_from_title("Kaguya-sama: Love is War", season=1))
