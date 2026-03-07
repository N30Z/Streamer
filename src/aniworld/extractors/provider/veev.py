"""
veev.to video extractor.

Extraction flow:
  1. Fetch the /e/{id} embed page with browser-like headers (session keeps cookies
     to pass bot-protection challenges).
  2. Try to find the CDN streaming URL directly in the page HTML (fast path).
  3. Parse the __VEEVPLAYER__ JS config for fc token(s) and apiUri.
  4. Use those tokens to call the veev.to API and get the signed CDN URL.
"""

import json
import logging
import re
from typing import Optional

import requests

from ... import config

# CDN URL pattern — matches both veev.to and veevcdn.co CDN nodes
CDN_PATTERN = re.compile(
    r"https://s-[A-Za-z0-9]+-\d+\.veev(?:cdn\.co|\.to)/[A-Za-z0-9_\-]{20,}"
)

# fc values embedded in JS objects: { ..., fc: "...", ... }
FC_PATTERN = re.compile(r"""['\"]?fc['\"]?\s*:\s*['"]([^'"]{10,})['"]""")

# The REAL api key: the page overwrites window._vvto.fc at the very end
# e.g.  window._vvto[__pqrsww]="30104Ăā200-8ĉ<vid_id>-155..."
REAL_FC_PATTERN = re.compile(r'window\._vvto\[[^\]]+\]\s*=\s*"([^"]+)"')

# apiUri lives in the __VEEVPLAYER__ config object
API_URI_PATTERN = re.compile(r"""apiUri\s*:\s*['"]([^'"]+)['"]""")

# Fallback: generic m3u8 / mp4 URL in the page source
HLS_PATTERN = re.compile(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*")
MP4_PATTERN = re.compile(r"https?://[^\s'\"<>]+\.mp4[^\s'\"<>]*")

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "iframe",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
}

_API_HEADERS = {
    "User-Agent": _BROWSER_HEADERS["User-Agent"],
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.5",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}


def _extract_fc_tokens(html: str) -> list[str]:
    return FC_PATTERN.findall(html)


def _find_cdn_in_json_resp(data: dict) -> Optional[str]:
    """Recursively search a JSON dict for a CDN URL."""
    for key in ("url", "file", "stream", "source", "src", "hls", "link"):
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    # Some APIs return a nested 'data' object
    if isinstance(data.get("data"), dict):
        return _find_cdn_in_json_resp(data["data"])
    return None


def _api_probe(
    session: requests.Session,
    embed_url: str,
    vid_id: str,
    fc_tokens: list[str],
    api_uri: str,
) -> Optional[str]:
    """Try the known veev.to API patterns with the extracted fc tokens.

    fc_tokens[0] is the real_fc (final override value) when available,
    followed by the two values extracted from the JS objects:
      fc_tokens[1] = short slug (video identifier, e.g. 'Gujal00_loving...')
      fc_tokens[2] = long token (intermediate key)
    """
    base = api_uri.rstrip("/")
    # Token roles (positions may vary — cover all combinations)
    real_fc  = fc_tokens[0] if fc_tokens else ""
    fc_short = fc_tokens[1] if len(fc_tokens) > 1 else real_fc
    fc_long  = fc_tokens[2] if len(fc_tokens) > 2 else real_fc

    hdrs = {**_API_HEADERS, "Referer": embed_url, "Origin": "https://veev.to"}

    candidates = [
        # Primary: real fc as key, short slug as video id
        ("GET",  f"{base}/api/video/{fc_short}?key={real_fc}", None),
        ("GET",  f"{base}/api/video/{fc_short}?k={real_fc}", None),
        # vid_id (URL path fragment) as identifier
        ("GET",  f"{base}/api/video/{vid_id}?key={real_fc}", None),
        # POST variants
        ("POST", f"{base}/api/source/{vid_id}",
         {"r": embed_url, "d": "veev.to", "key": real_fc}),
        ("POST", f"{base}/api/source/{fc_short}",
         {"r": embed_url, "d": "veev.to", "key": real_fc}),
        # Fallbacks with the long intermediate token
        ("GET",  f"{base}/api/video/{fc_short}?key={fc_long}", None),
        ("GET",  f"{base}/api/video/{fc_short}", None),
        ("GET",  f"{base}/api/embed/{vid_id}?key={real_fc}", None),
    ]

    for method, url, body in candidates:
        try:
            if method == "POST":
                resp = session.post(url, json=body, headers=hdrs,
                                    timeout=config.DEFAULT_REQUEST_TIMEOUT)
            else:
                resp = session.get(url, headers=hdrs,
                                   timeout=config.DEFAULT_REQUEST_TIMEOUT)

            if resp.status_code != 200:
                continue

            # Direct CDN URL in response body (not JSON)
            cdn = CDN_PATTERN.search(resp.text)
            if cdn:
                return cdn.group(0)

            try:
                data = resp.json()
                found = _find_cdn_in_json_resp(data)
                if found:
                    return found
            except (ValueError, KeyError):
                pass

        except requests.RequestException as exc:
            logging.debug("veev API %s %s → %s", method, url, exc)

    return None


def _make_session():
    """Return a session that can bypass bot protection if cloudscraper is available."""
    try:
        import cloudscraper  # type: ignore
        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except ImportError:
        s = requests.Session()
        s.headers.update(_BROWSER_HEADERS)
        return s


def get_direct_link_from_veev(embeded_veev_link: str) -> str:
    """
    Extract a direct (CDN) streaming URL from a veev.to embed URL.

    Args:
        embeded_veev_link: Full embed URL, e.g.
            https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1

    Returns:
        Direct streaming URL (M3U8 or MP4).

    Raises:
        ValueError: If no streaming URL could be extracted.
    """
    session = _make_session()

    try:
        resp = session.get(
            embeded_veev_link,
            timeout=config.DEFAULT_REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(f"Failed to fetch veev.to embed page: {exc}") from exc

    html = resp.text

    # ── Fast path: CDN URL is already present in the page ─────────────────
    cdn_match = CDN_PATTERN.search(html)
    if cdn_match:
        logging.debug("veev: CDN URL found directly in page source")
        return cdn_match.group(0)

    hls_match = HLS_PATTERN.search(html)
    if hls_match:
        return hls_match.group(0)

    mp4_match = MP4_PATTERN.search(html)
    if mp4_match:
        return mp4_match.group(0)

    # ── Slow path: hit the API ─────────────────────────────────────────────
    # The page injects three fc values; the LAST assignment to window._vvto.fc
    # is the actual signed API key used by the player.
    real_fc_match = REAL_FC_PATTERN.search(html)
    real_fc = real_fc_match.group(1) if real_fc_match else None

    fc_tokens = _extract_fc_tokens(html)
    api_uri_match = API_URI_PATTERN.search(html)
    raw_uri = api_uri_match.group(1) if api_uri_match else ""
    api_uri = raw_uri if raw_uri else "https://veev.to"

    vid_id = embeded_veev_link.split("/")[-1].split("?")[0]

    # Build token list: real_fc goes first so it's tried as the primary key
    tokens = []
    if real_fc:
        tokens.append(real_fc)
    tokens.extend(fc_tokens)

    if tokens:
        result = _api_probe(session, embeded_veev_link, vid_id, tokens, api_uri)
        if result:
            return result

    raise ValueError(
        f"No streaming URL found for veev.to embed: {embeded_veev_link}\n"
        "The page may have changed its structure or the bot-protection blocked the request.\n"
        "Try a different provider or report this issue."
    )
