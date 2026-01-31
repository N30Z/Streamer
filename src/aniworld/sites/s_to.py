"""
S.to site module.

Provides search functionality and episode/season counting for s.to
(series streaming). Uses HTML scraping since s.to does not provide
a JSON API.
"""
import re
import logging
import re
from typing import List, Dict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from ..config import DEFAULT_REQUEST_TIMEOUT, S_TO, RANDOM_USER_AGENT


def _make_request(url: str) -> requests.Response:
    """Make HTTP request with error handling."""
    response = requests.get(
        url,
        timeout=DEFAULT_REQUEST_TIMEOUT,
        headers={"User-Agent": RANDOM_USER_AGENT},
    )
    response.raise_for_status()
    return response


def fetch_sto_search_results(keyword: str) -> List[Dict]:
    """
    Fetch and parse search results from s.to HTML search page.

    The s.to /suche?term= endpoint returns HTML, not JSON,
    so we scrape the results from the page.

    Args:
        keyword: The search term

    Returns:
        List[Dict]: List of anime/series dictionaries with keys:
            name, link, description, cover, productionYear
    """
    search_url = f"{S_TO}/suche?term={quote(keyword)}"
    try:
        response = requests.get(
            search_url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers={"User-Agent": RANDOM_USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as err:
        logging.error("Failed to fetch s.to search page: %s", err)
        raise ValueError("Could not fetch s.to search results") from err

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    # s.to search results are in:
    # div.search-results.search-results-list > div:nth-child(1) > div.row.g-3
    # The div.row.g-3 is the direct container holding only the result items
    result_container = soup.select_one("div.search-results-list > div > div.row.g-3")

    if not result_container:
        logging.warning("fetch_sto_search_results: could not find div.row.g-3 result container")
        return results

    # Only look for /serie/ links inside the result container
    items = result_container.find_all("a", href=re.compile(r"/serie/[^/]+"))

    seen_slugs = set()
    for item in items:
        href = item.get("href", "")
        if not href or "/serie/" not in href:
            continue

        # Extract slug from href like /serie/fallout
        slug = href.rstrip("/").split("/serie/")[-1]
        # Skip if slug contains sub-paths (staffel/episode links)
        if "/" in slug or not slug:
            continue
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # Walk up to the parent column (direct child of div.row.g-3)
        col = item.find_parent("div", class_=re.compile(r"col"))
        # Fallback to any parent div if no col found
        if not col:
            col = item.parent

        # Extract title from the link or its parent context
        name = ""
        if col:
            h_tag = col.find(["h6", "h3", "h4", "h5", "h2"])
            if h_tag:
                name = h_tag.get_text(strip=True)
        if not name:
            name = item.get("title", "")
        if not name:
            name = item.get_text(strip=True)
        if not name:
            name = slug.replace("-", " ").title()

        # Extract cover image from the column or link
        cover = ""
        img_context = col if col else item
        img = img_context.find("img")
        if img:
            cover = img.get("data-src") or img.get("src") or ""
            if cover and cover.startswith("/"):
                cover = S_TO + cover

        # Extract year if present
        year = ""
        year_context = col if col else item
        year_el = year_context.find("span", class_="year") or year_context.find(class_="productionYear")
        if year_el:
            year = year_el.get_text(strip=True)

        # Extract description if present
        description = ""
        desc_context = col if col else item
        desc_el = desc_context.find("p") or desc_context.find(class_="description")
        if desc_el:
            description = desc_el.get_text(strip=True)

        results.append({
            "name": name,
            "link": slug,
            "description": description,
            "cover": cover,
            "productionYear": year,
        })

    return results


# ---------------------------------------------------------------------------
# Season / Episode counting for s.to
# ---------------------------------------------------------------------------

def _parse_season_episodes(soup: BeautifulSoup, season: int) -> int:
    """Parse episode count for a specific season from s.to HTML."""
    episode_links = soup.find_all("a", href=True)
    unique_links = set(
        link["href"]
        for link in episode_links
        if f"staffel-{season}/episode-" in link["href"]
    )
    return len(unique_links)


def get_season_episode_count(slug: str) -> Dict[int, int]:
    base_url = f"{S_TO}/serie/{slug}/"
    response = _make_request(base_url)
    soup = BeautifulSoup(response.content, "html.parser")

    # -------- FIND SEASONS --------
    season_numbers = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # match /staffel-<number> but NOT /episode
        m = re.search(r"/staffel-(\d+)$", href)
        if m:   
            season_num = int(m.group(1))

            # optional: ignore season 0 (movies/specials)
            if season_num > 0:
                season_numbers.add(season_num)

    episode_counts: Dict[int, int] = {}

    # -------- FOR EACH SEASON --------
    for season in sorted(season_numbers):
        season_url = f"{base_url}staffel-{season}"
        try:
            season_response = _make_request(season_url)
            season_soup = BeautifulSoup(season_response.content, "html.parser")

            episode_links = set()

            for a in season_soup.find_all("a", href=True):
                href = a["href"]

                # match /staffel-X/episode-Y
                if f"/staffel-{season}/episode-" in href:
                    episode_links.add(href)

            episode_counts[season] = len(episode_links)

        except Exception as err:
            logging.warning("Failed to get episodes for season %d: %s", season, err)
            episode_counts[season] = 0

    return episode_counts


def fetch_popular_and_new_sto() -> Dict[str, List[Dict[str, str]]]:
    """
    Fetch popular and new series from s.to homepage.

    Scrapes the s.to homepage for "Beliebt" and "Neue" sections,
    similar to how aniworld.to homepage parsing works.

    Returns:
        Dictionary with 'popular' and 'new' keys containing lists of series data
    """
    try:
        response = _make_request(S_TO)

        soup = BeautifulSoup(response.text, "html.parser")

        result = {"popular": [], "new": []}

        # Extract popular series section
        popular_section = soup.find(
            "h2", string=lambda text: text and "beliebt" in text.lower()
        )
        if popular_section:
            popular_carousel = popular_section.find_parent().find_next_sibling(
                "div", class_="previews"
            )
            if popular_carousel:
                result["popular"] = _extract_series_from_carousel(popular_carousel)

        # Extract new series section
        new_section = soup.find(
            "h2",
            string=lambda text: text
            and "neue" in text.lower()
            and "serie" in text.lower(),
        )
        if new_section:
            new_carousel = new_section.find_parent().find_next_sibling(
                "div", class_="previews"
            )
            if new_carousel:
                result["new"] = _extract_series_from_carousel(new_carousel)

        return result

    except requests.RequestException as err:
        logging.error("Failed to fetch s.to homepage: %s", err)
        raise ValueError("Could not fetch s.to homepage data") from err


def _extract_series_from_carousel(carousel_div) -> List[Dict[str, str]]:
    """
    Extract series data from a carousel div section on s.to.

    Args:
        carousel_div: BeautifulSoup element containing the carousel

    Returns:
        List of dictionaries with 'name' and 'cover' keys
    """
    series_list = []

    cover_items = carousel_div.find_all("div", class_="coverListItem")

    for item in cover_items:
        try:
            name = None
            h3_tag = item.find("h3")
            if h3_tag:
                name = h3_tag.get_text(strip=True)
                name = name.split(" \u2022")[0].strip()

            if not name:
                link = item.find("a")
                if link and link.get("title"):
                    title_text = link.get("title")
                    name = (
                        title_text.split(" alle Folgen")[0]
                        .split(" jetzt online")[0]
                        .strip()
                    )

            cover = None
            img_tag = item.find("img")
            if img_tag:
                cover = img_tag.get("data-src") or img_tag.get("src")
                if cover and cover.startswith("/"):
                    cover = S_TO + cover

            if name and cover:
                series_list.append({"name": name, "cover": cover})

        except Exception:
            continue

    return series_list


def get_movie_episode_count(slug: str) -> int:
    """
    Get movie count for a series on s.to.

    Args:
        slug: Series slug from URL

    Returns:
        Number of movies available
    """
    try:
        movie_page_url = f"{S_TO}/serie/{slug}/filme"
        response = _make_request(movie_page_url)
        soup = BeautifulSoup(response.content, "html.parser")

        movie_index = 1
        while True:
            expected_subpath = f"{slug}/filme/film-{movie_index}"
            matching_links = [
                link["href"]
                for link in soup.find_all("a", href=True)
                if expected_subpath in link["href"]
            ]
            if matching_links:
                movie_index += 1
            else:
                break

        return movie_index - 1

    except Exception as err:
        logging.error("Failed to get movie count for %s on s.to: %s", slug, err)
        return 0
