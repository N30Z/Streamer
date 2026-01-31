import re
import logging
from typing import Optional

import requests

from ...config import RANDOM_USER_AGENT, DEFAULT_REQUEST_TIMEOUT


def _make_request(url: str) -> requests.Response:
    try:
        resp = requests.get(
            url, headers={"User-Agent": RANDOM_USER_AGENT}, timeout=DEFAULT_REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp
    except requests.RequestException as err:
        logging.error("Streamtape request failed for %s: %s", url, err)
        raise


def _extract_direct_from_html(html: str, source_url: str) -> Optional[str]:
    """Try to find a direct media URL in Streamtape HTML content."""
    # Quick fail for obvious removed messages
    if re.search(r"video not found|video was deleted|not found", html, re.I):
        raise ValueError("Streamtape video not found or removed")

    # Common patterns: <source src="...mp4"> or file: "...mp4" or "url":"...mp4"
    patterns = [
        r'<source[^>]+src="(https?://[^"]+\.(?:mp4|mkv|webm))"',
        r'file\s*:\s*"(https?://[^"]+\.(?:mp4|mkv|webm))"',
        r'"url"\s*:\s*"(https?://[^"]+\.(?:mp4|mkv|webm))"',
        # Fallback: any non-space, non-quote URL ending with a known video extension
        r'(https?://[^\s"\']+\.(?:mp4|mkv|webm))',
    ]

    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            url = m.group(1)
            # Clean escaped sequences
            url = url.replace('\\/', '/')
            return url

    return None


def get_direct_link_from_streamtape(embeded_streamtape_link: str) -> str:
    """Extract direct link from Streamtape embed or video URL.

    Supports /e/ (embed) and /v/ (video) URL patterns.
    """
    if not embeded_streamtape_link:
        raise ValueError("Streamtape URL cannot be empty")

    logging.info("Extracting direct link from Streamtape: %s", embeded_streamtape_link)

    # Normalize embed -> video page if necessary
    url = embeded_streamtape_link

    try:
        resp = _make_request(url)
        html = resp.text

        direct = _extract_direct_from_html(html, url)
        if direct:
            logging.info("Streamtape direct link found: %s", direct)
            return direct

        # If not found, try to follow XHR or JSON endpoints referenced in page
        # Look for a JS-config reference to an API endpoint
        api_match = re.search(r'"(https?://(?:www\.)?streamtape\.com/api/[^"\']+)"', html)
        if api_match:
            api_url = api_match.group(1)
            logging.debug("Found streamtape API url: %s", api_url)
            api_resp = _make_request(api_url)
            # Try to pull URLs from JSON-ish text
            direct = _extract_direct_from_html(api_resp.text, api_url)
            if direct:
                return direct

        raise ValueError("No direct media URL found in Streamtape content")

    except Exception as err:
        logging.error("get_direct_link_from_streamtape: Failed to extract direct link: %s", err)
        raise

