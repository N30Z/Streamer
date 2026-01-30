"""
S.to site module.

Provides search functionality for s.to (series streaming).
Uses HTML scraping since s.to does not provide a JSON API for search.
"""

import logging
import re
from typing import List, Dict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from ..config import DEFAULT_REQUEST_TIMEOUT, S_TO, RANDOM_USER_AGENT


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
