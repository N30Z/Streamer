"""
Generic headless-browser URL interceptor using Playwright.

Loads a page in a headless browser and captures the first network request
whose URL matches one of the given patterns.  The browser is closed
immediately after — the heavy lifting (actual download) is done by
yt-dlp / requests as usual.

Usage (any provider):
    from ..browser_interceptor import intercept_url

    stream_url = intercept_url(
        "https://example.com/embed/ABC",
        match=["cdn.example.com/stream/", ".m3u8"],
        timeout=20,
    )

Playwright must be installed:
    pip install playwright
    playwright install chromium
"""

import logging
import threading
from typing import Optional

log = logging.getLogger(__name__)


def intercept_url(
    page_url: str,
    match: list[str],
    *,
    timeout: int = 20,
    referrer: Optional[str] = None,
    wait_for: str = "networkidle",
    extra_headers: Optional[dict] = None,
) -> Optional[str]:
    """
    Launch a headless Chromium browser, load *page_url*, and return the first
    outgoing request URL that contains any substring in *match*.

    Args:
        page_url:      The embed / player page to open.
        match:         List of URL substrings to watch for (e.g. ["/px/", ".m3u8"]).
        timeout:       Seconds to wait for a matching request (default 20).
        referrer:      Optional HTTP Referer header for the initial page load.
        wait_for:      Playwright wait condition – "networkidle" (default),
                       "load", "domcontentloaded", or "commit".
        extra_headers: Additional request headers for the page load.

    Returns:
        The first matching URL, or None if nothing was captured within *timeout*.

    Raises:
        ImportError: If playwright is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as exc:
        raise ImportError(
            "playwright is required for browser-based extraction.\n"
            "Install it with:  pip install playwright && playwright install chromium"
        ) from exc

    found: list[str] = []
    lock = threading.Event()

    def _on_request(request) -> None:
        url = request.url
        if any(pat in url for pat in match):
            if not found:
                found.append(url)
                lock.set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            extra_http_headers=extra_headers or {},
        )
        page = context.new_page()
        page.on("request", _on_request)

        try:
            nav_opts = {"timeout": timeout * 1000, "wait_until": wait_for}
            if referrer:
                nav_opts["referer"] = referrer
            page.goto(page_url, **nav_opts)
        except PWTimeout:
            log.debug("browser_interceptor: page load timed out for %s", page_url)
        except Exception as exc:  # pylint: disable=broad-except
            log.debug("browser_interceptor: navigation error: %s", exc)

        # If the page loaded but the request came in slightly after networkidle,
        # give it a short extra wait.
        if not found:
            lock.wait(timeout=5)

        browser.close()

    if found:
        log.debug("browser_interceptor: captured %s", found[0])
        return found[0]

    log.debug("browser_interceptor: no matching request for patterns %s", match)
    return None
