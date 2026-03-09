import logging
from typing import Optional, Callable
from functools import wraps

COMMON_STREAM_PATTERNS = [".m3u8", ".mp4", "/hls/", "/dash/", "manifest", "playlist"]


def playwright_fallback(
    embed_url: str,
    extra_patterns: Optional[list] = None,
    timeout: int = 20,
) -> Optional[str]:
    """Intercept stream URL by loading embed page in a headless Chromium browser.

    Requires: pip install playwright && playwright install chromium
    Returns None gracefully if playwright is not installed.
    """
    patterns = COMMON_STREAM_PATTERNS + (extra_patterns or [])
    try:
        from ..browser_interceptor import intercept_url
        return intercept_url(embed_url, match=patterns, timeout=timeout)
    except ImportError:
        logging.debug("playwright not installed – browser fallback skipped")
        return None
    except Exception as exc:
        logging.debug("playwright_fallback error for %s: %s", embed_url, exc)
        return None


def with_fallbacks(playwright_patterns: Optional[list] = None):
    """Decorator that adds two fallback layers to a provider extractor function.

    Fallback chain:
      1. Primary: provider-specific requests-based extraction (the decorated function)
      2. Playwright: headless Chromium intercepts the first matching network request
      3. Native yt-dlp: embed URL is returned directly so yt-dlp uses its own extractors

    Usage::

        @with_fallbacks()
        def get_direct_link_from_myprovider(embed_url: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(embed_url: str, *args, **kwargs) -> str:
            # ── Primary: provider-specific extraction ──────────────────────
            try:
                result = func(embed_url, *args, **kwargs)
                if result:
                    return result
            except Exception as exc:
                logging.warning("%s failed (%s), trying fallbacks", func.__name__, exc)

            # ── Fallback 1: Playwright browser intercept ───────────────────
            result = playwright_fallback(embed_url, extra_patterns=playwright_patterns)
            if result:
                logging.info("%s: playwright fallback succeeded", func.__name__)
                return result

            # ── Fallback 2: Native yt-dlp (pass embed URL directly) ────────
            logging.info(
                "%s: returning embed URL for native yt-dlp: %s",
                func.__name__, embed_url,
            )
            return embed_url

        return wrapper
    return decorator
