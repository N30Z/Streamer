"""
veev.to video extractor.

Extraction flow:
  1. Fetch the embed page with requests to get file_code, real_fc (LZW token),
     and the cmd=gi API endpoint parameters.
  2. Call  POST /dl?op=player_api&cmd=gi  to get the signed stream URL
     (returned inside dv[0].s, but also resolvable via network intercept).
  3. If the requests path fails (bot-protection, decode error, etc.),
     fall back to a headless Playwright browser that intercepts the first
     network request to veevcdn.co/px/ — the direct MP4 stream URL.

The stream URL format (no auth required, CORS *):
    https://prx-{geo}-{id}.veevcdn.co/px/{token}?osr={cdn_origin}
"""

import logging
import re
from typing import Optional

import requests

from ... import config
from ..browser_interceptor import intercept_url as _browser_intercept

log = logging.getLogger(__name__)

# Embed URL:  https://veev.to/e/{file_code}[?rback=1]
_FILE_CODE_RE = re.compile(r"/e/([A-Za-z0-9]+)")

# The real fc token is the LAST assignment to window._vvto[...]:
#   window._vvto[__xx]="30104Ăā200-8ĉ<vid_id>-155..."
_REAL_FC_RE = re.compile(r'window\._vvto\[[^\]]+\]\s*=\s*"([^"]+)"')

# Direct proxy stream URL (captured from network / decoded from dv[0].s)
_STREAM_RE = re.compile(
    r"https://prx-[A-Za-z0-9]+-\d+\.veevcdn\.co/px/[A-Za-z0-9_\-]+\?osr=[^\s\"'<>]+"
)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Encoding": "gzip, deflate",   # NOT brotli — requests can't decode it
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


def _lzw_decompress(s: str) -> str:
    """LZW decompress a veev.to token string (Unicode codepoints > 255 = dict indices)."""
    k = list(s)
    if not k:
        return ""
    D: dict[int, str] = {}
    C = k[0]
    M = C
    U = [C]
    y = 256
    for G in range(1, len(k)):
        Y = ord(k[G])
        I = k[G] if Y < 256 else D.get(Y, M + C)
        U.append(I)
        C = I[0]
        D[y] = M + C
        y += 1
        M = I
    return "".join(U)


def _fetch_embed(embed_url: str) -> Optional[tuple[str, str, str]]:
    """
    Fetch the embed page and return (file_code, ch, query_suffix) or None.

    *ch* is the LZW-decoded real_fc value used as the &ch= parameter in
    the cmd=gi API call.  *query_suffix* is the raw query string from the
    embed URL (e.g. "rback=1") forwarded to the API.
    """
    s = requests.Session()
    s.headers.update(_BROWSER_HEADERS)
    try:
        resp = s.get(embed_url, timeout=config.DEFAULT_REQUEST_TIMEOUT,
                     allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.debug("veev: embed page fetch failed: %s", exc)
        return None

    html = resp.text
    fc_m = _REAL_FC_RE.search(html)
    if not fc_m:
        log.debug("veev: real_fc not found in embed page")
        return None

    file_code_m = _FILE_CODE_RE.search(embed_url)
    file_code = file_code_m.group(1) if file_code_m else ""
    ch = _lzw_decompress(fc_m.group(1))
    qs = embed_url.split("?", 1)[1] if "?" in embed_url else ""
    return file_code, ch, qs


def _cmd_gi(embed_url: str, file_code: str, ch: str, qs: str) -> Optional[str]:
    """
    Call the veev.to player API (POST /dl, cmd=gi) and extract the stream URL.

    The API returns the signed proxy URL inside dv[0].s (LZW-encoded), but
    we also match it from the raw response text using the known URL pattern.
    """
    s = requests.Session()
    s.headers.update({
        **_BROWSER_HEADERS,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": embed_url,
        "Origin": "https://veev.to",
    })

    # Step 1: prime server session
    try:
        s.get("https://veev.to/dl?op=player_api&cmd=gvnp",
              timeout=config.DEFAULT_REQUEST_TIMEOUT)
    except requests.RequestException:
        pass

    # Step 2: cmd=gi — POST (confirmed from browser network inspection)
    params = (
        f"op=player_api&cmd=gi"
        f"&file_code={file_code}"
        f"&r="
        f"&ch={ch}"
        + (f"&{qs}" if qs else "")
        + "&ie=1"
    )
    try:
        resp = s.post(
            "https://veev.to/dl",
            data=params,
            headers={**s.headers,
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=config.DEFAULT_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.debug("veev: cmd=gi failed: %s", exc)
        return None

    # Try to find the proxy stream URL directly in the response text
    m = _STREAM_RE.search(resp.text)
    if m:
        return m.group(0)

    log.debug("veev: stream URL not found in cmd=gi response (dv decode needed)")
    return None


def get_direct_link_from_veev(embeded_veev_link: str) -> str:
    """
    Extract a direct MP4 stream URL from a veev.to embed URL.

    Tries a lightweight requests-based path first; falls back to a headless
    Playwright browser that intercepts the actual stream request.

    Args:
        embeded_veev_link: Full embed URL, e.g.
            https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1

    Returns:
        Direct proxy stream URL:
            https://prx-{geo}-{id}.veevcdn.co/px/{token}?osr={cdn}

    Raises:
        ValueError: If no stream URL could be extracted.
    """
    # ── Fast path: requests + cmd=gi API ─────────────────────────────────────
    embed_data = _fetch_embed(embeded_veev_link)
    if embed_data:
        file_code, ch, qs = embed_data
        stream_url = _cmd_gi(embeded_veev_link, file_code, ch, qs)
        if stream_url:
            log.debug("veev: stream URL via API: %s", stream_url)
            return stream_url

    # ── Fallback: Playwright browser intercept ────────────────────────────────
    log.debug("veev: falling back to browser intercept for %s", embeded_veev_link)
    stream_url = _browser_intercept(
        embeded_veev_link,
        match=["veevcdn.co/px/"],
        timeout=25,
        referrer="https://veev.to/",
    )
    if stream_url:
        return stream_url

    raise ValueError(
        f"veev.to: could not extract stream URL from {embeded_veev_link}\n"
        "Ensure playwright is installed: pip install playwright && playwright install chromium"
    )
