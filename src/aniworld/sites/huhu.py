"""
huhu.to support module.

Provides API-based access to huhu.to streaming site for movies.
Used as a parallel source / fallback alongside movie4k.sx.

API endpoints:
  GET /web-vod/api/list?id=movie.popular.search%3D{query}  -> search
  GET /web-vod/api/links?id=movie.{tmdb_id}               -> stream links
  GET /web-vod/api/get?link={token}                        -> resolves to provider URL (redirect)

URL format: https://huhu.to/web-vod/item?id=movie.{tmdb_id}
Language codes: "de" = German Dub, "en" = English Sub
"""

import importlib
import inspect
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs, quote

import requests

from ..config import (
    DEFAULT_REQUEST_TIMEOUT,
    RANDOM_USER_AGENT,
    HUHU_TO,
)
from ..parser import get_arguments


# Maps known provider domains (from resolved redirect URLs) to internal provider names
HUHU_PROVIDER_DOMAINS: Dict[str, str] = {
    "myvidplay.com": "Doodstream",
    "dood.so": "Doodstream",
    "dood.li": "Doodstream",
    "dood.to": "Doodstream",
    "dood.yt": "Doodstream",
    "dood.cx": "Doodstream",
    "doodstream.com": "Doodstream",
    "ds2play.com": "Doodstream",
    "voe.sx": "VOE",
    "filemoon.sx": "Filemoon",
    "filemoon.to": "Filemoon",
    "moonplayer.to": "Filemoon",
    "streamtape.com": "Streamtape",
    "streamtape.to": "Streamtape",
    "vidoza.net": "Vidoza",
    "vidmoly.to": "Vidmoly",
    "vidmoly.net": "Vidmoly",
}

_HUHU_HEADERS = {
    "User-Agent": RANDOM_USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "de-DE,de;q=0.9",
    "Origin": HUHU_TO,
    "Referer": f"{HUHU_TO}/web-vod/",
    "api-key": "TC2AJpYciVIFw6POgjNpiJfsnSnw",
}


def _detect_provider_from_url(url: str) -> Optional[str]:
    """Detect provider name from a resolved video URL by matching the domain."""
    try:
        domain = urlparse(url).netloc.lower()
        # Strip www. prefix
        domain = domain.removeprefix("www.")
        return HUHU_PROVIDER_DOMAINS.get(domain)
    except Exception:
        return None


def _resolve_link_token(token: str) -> Optional[str]:
    """
    Resolve a huhu.to link token to the final provider URL.

    Calls /web-vod/api/get?link={token} and follows redirects.
    Returns the final URL after all redirects, or None on failure.
    Uses verify=False to handle provider domains with untrusted SSL certificates
    (e.g. dood.to, dood.yt).
    """
    resolve_url = f"{HUHU_TO}/web-vod/api/get?link={token}"
    try:
        resp = requests.get(
            resolve_url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers=_HUHU_HEADERS,
            allow_redirects=True,
            verify=False,
        )
        final_url = resp.url
        # If the redirect stayed on huhu.to the token is likely invalid or
        # huhu.to's upstream provider (e.g. Doodstream) is temporarily blocking
        # requests. Doodstream imposes short IP bans under high request volume;
        # waiting a few minutes usually resolves this.
        if "huhu.to" in final_url:
            logging.warning(
                "huhu.to: token '%s...' did not redirect (HTTP %s) — "
                "provider may be rate-limiting; try again in a few minutes",
                token[:20],
                resp.status_code,
            )
            return None
        logging.debug("huhu.to: token '%s...' resolved to %s", token[:20], final_url)
        return final_url
    except requests.RequestException as err:
        logging.warning("huhu.to: failed to resolve token '%s': %s", token, err)
        return None


def fetch_huhu_search_results(keyword: str) -> List[Dict[str, Any]]:
    """
    Search huhu.to for movies matching *keyword*.

    Returns a list of dicts compatible with the existing search result format:
      name, link (full URL), cover, description, productionYear
    """
    try:
        search_id = f"movie.popular.search={keyword}"
        url = f"{HUHU_TO}/web-vod/api/list?id={quote(search_id, safe='')}"
        resp = requests.get(
            url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers=_HUHU_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as err:
        logging.warning("huhu.to search failed for '%s': %s", keyword, err)
        return []
    except (ValueError, KeyError) as err:
        logging.warning("huhu.to search: unexpected response for '%s': %s", keyword, err)
        return []

    results = []
    for item in data.get("data", []):
        item_id = item.get("id", "")
        if not item_id:
            continue
        link = f"{HUHU_TO}/web-vod/item?id={item_id}"
        release_date = item.get("releaseDate", "")
        year = release_date[:4] if release_date else ""
        results.append({
            "name": item.get("name") or item.get("originalName", "Unknown"),
            "link": link,
            "cover": item.get("poster", ""),
            "description": item.get("description", ""),
            "productionYear": year,
        })

    logging.debug("huhu.to search returned %d results for '%s'", len(results), keyword)
    return results


class HuhuMovie:
    """
    Represents a single movie from huhu.to.

    Implements the Episode-compatible interface (season=0, episode=1,
    get_direct_link()) so it can be used directly in the download pipeline
    via HuhuMovieAnime.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        movie_id: Optional[str] = None,
        title: Optional[str] = None,
        _selected_language: Optional[str] = None,
    ) -> None:
        if not url and not movie_id:
            raise ValueError("Provide either 'url' or 'movie_id'.")

        self.site = "huhu.to"
        self.base_url = HUHU_TO

        if url:
            self.movie_id = self._parse_url(url)
        else:
            self.movie_id = movie_id

        # Canonical URL and slug
        self.link = f"{HUHU_TO}/web-vod/item?id={self.movie_id}"
        self.slug = self.movie_id.replace(".", "_") if self.movie_id else "unknown"

        # Caches
        self._links_cache: Optional[List[Dict]] = None
        self._title = title
        self._overview: Optional[str] = None
        self._year: Optional[str] = None
        self._cover: Optional[str] = None

        arguments = get_arguments()
        self._selected_language = _selected_language or getattr(
            arguments, "language", "German Dub"
        )

        # Episode-compatible attributes for the action pipeline
        self.season = 0
        self.episode = 1
        self.season_episode_count: Dict[int, int] = {0: 1}
        self.movie_episode_count: int = 1

        self.embeded_link: Optional[str] = None
        self.direct_link: Optional[str] = None

    @staticmethod
    def _parse_url(url: str) -> str:
        """Extract movie_id (e.g. 'movie.911430') from a huhu.to item URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        movie_id = params.get("id", [None])[0]
        if not movie_id:
            raise ValueError(f"Cannot extract movie ID from URL: {url}")
        return movie_id

    def _fetch_links(self) -> List[Dict]:
        """Fetch and cache the list of stream link objects for this movie."""
        if self._links_cache is None:
            api_url = f"{HUHU_TO}/web-vod/api/links?id={self.movie_id}"
            try:
                resp = requests.get(
                    api_url,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers=_HUHU_HEADERS,
                )
                resp.raise_for_status()
                self._links_cache = resp.json()
            except requests.RequestException as err:
                logging.error("huhu.to: failed to fetch links for '%s': %s", self.movie_id, err)
                self._links_cache = []
        return self._links_cache

    @property
    def title(self) -> str:
        if self._title:
            return self._title
        # Try to get metadata from search results (not stored here), fall back to ID
        return self.movie_id or "Unknown"

    @property
    def overview(self) -> str:
        return self._overview or ""

    @property
    def year(self) -> Optional[str]:
        return self._year

    @property
    def cover(self) -> str:
        return self._cover or ""

    @property
    def available_languages(self) -> List[str]:
        """Return available language names based on the link list."""
        links = self._fetch_links()
        langs = {link.get("language") for link in links}
        result = []
        if "de" in langs:
            result.append("German Dub")
        if "en" in langs:
            result.append("English Sub")
        return result

    @property
    def provider_names(self) -> List[str]:
        """huhu.to uses opaque server names; return empty to skip provider UI."""
        return []

    def get_direct_link(self) -> Optional[str]:
        """
        Resolve the best available stream link for this movie.

        Uses a two-pass strategy:
        1. Resolve all tokens; skip Doodstream in the first pass (frequently
           blocked by Cloudflare / temporary IP bans on dood.video).
        2. Fall back to Doodstream tokens only if every other provider failed.
        """
        links = self._fetch_links()
        if not links:
            raise ValueError(f"huhu.to: no links found for '{self.movie_id}'")

        # Map language preference to huhu language code
        lang_pref = self._selected_language or "German Dub"
        lang_code = "en" if "english" in lang_pref.lower() else "de"

        # Prefer the requested language; fall back to all links
        filtered = [l for l in links if l.get("language") == lang_code]
        if not filtered:
            filtered = links

        server_names = [lo.get("name", "?") for lo in filtered]
        logging.warning(
            "huhu.to: trying %d token(s) for '%s' (servers: %s)",
            len(filtered), self.movie_id, ", ".join(server_names),
        )

        def _try_extractor(final_url: str, provider: str, server: str) -> Optional[str]:
            """Run the provider extractor; return direct URL or None."""
            try:
                module = importlib.import_module(".extractors", "aniworld")
                func_name = f"get_direct_link_from_{provider.lower()}"
                if not hasattr(module, func_name):
                    logging.warning(
                        "huhu.to: no extractor '%s' found, skipping server '%s'",
                        func_name, server,
                    )
                    return None
                func = getattr(module, func_name)
                kwargs: Dict[str, Any] = {f"embeded_{provider.lower()}_link": final_url}
                sig = inspect.signature(func)
                if "referer" in sig.parameters:
                    kwargs["referer"] = self.link
                direct = func(**kwargs)
                if direct:
                    logging.warning(
                        "huhu.to: server '%s' (%s) extraction succeeded", server, provider
                    )
                    return direct
            except Exception as ext_err:
                logging.warning(
                    "huhu.to: extractor '%s' failed for server '%s': %s",
                    provider, server, ext_err,
                )
            return None

        # First pass: resolve tokens and try non-Doodstream providers.
        # Doodstream is queued for the second pass because dood.video hosts
        # are frequently unreachable (IP bans, Cloudflare blocks).
        doodstream_queue: List[Dict[str, str]] = []

        for link_obj in filtered:
            token = link_obj.get("url", "")
            server_name = link_obj.get("name", "?")
            if not token:
                continue

            try:
                final_url = _resolve_link_token(token)
                if not final_url:
                    logging.warning(
                        "huhu.to: server '%s' token did not resolve, skipping", server_name
                    )
                    continue

                provider = _detect_provider_from_url(final_url)
                logging.warning(
                    "huhu.to: server '%s' resolved to %s (provider: %s)",
                    server_name, final_url, provider or "unknown",
                )

                if provider == "Doodstream":
                    doodstream_queue.append({"url": final_url, "server": server_name})
                    continue

                if provider:
                    direct = _try_extractor(final_url, provider, server_name)
                    if direct:
                        self.embeded_link = final_url
                        self.direct_link = direct
                        return direct
                    logging.warning(
                        "huhu.to: server '%s' (%s) yielded no result, trying next",
                        server_name, provider,
                    )
                    continue

                # Unknown provider – let yt-dlp try directly
                logging.warning(
                    "huhu.to: unknown provider for server '%s', passing to yt-dlp: %s",
                    server_name, final_url,
                )
                self.embeded_link = final_url
                self.direct_link = final_url
                return final_url

            except Exception as err:
                logging.warning(
                    "huhu.to: server '%s' token failed: %s", server_name, err
                )
                continue

        # Second pass: Doodstream fallbacks (last resort)
        if doodstream_queue:
            logging.warning(
                "huhu.to: trying %d Doodstream fallback token(s) for '%s'",
                len(doodstream_queue), self.movie_id,
            )
            for item in doodstream_queue:
                final_url = item["url"]
                server_name = item["server"]
                direct = _try_extractor(final_url, "Doodstream", server_name)
                if direct:
                    self.embeded_link = final_url
                    self.direct_link = direct
                    return direct

        raise ValueError(f"huhu.to: no working link found for '{self.movie_id}'")


class HuhuMovieAnime:
    """
    Adapter that wraps a HuhuMovie to be compatible with the Anime interface.

    Makes HuhuMovie iterable as a single-item list, adds the title/slug/site
    attributes expected by the action pipeline (watch, download, syncplay).
    """

    def __init__(self, movie: HuhuMovie) -> None:
        self.movie = movie
        self.site = movie.site
        self.slug = movie.slug
        self.episode_list = [movie]

        arguments = get_arguments()
        self.action = getattr(arguments, "action", "Watch")
        self.provider = None  # huhu.to doesn't expose named providers
        self.language = movie._selected_language
        self.aniskip = False
        self.output_directory = getattr(arguments, "output_dir", "")

        self._title_cache: Optional[str] = None

    @property
    def title(self) -> str:
        if self._title_cache is None:
            year = self.movie.year
            if year:
                self._title_cache = f"{self.movie.title} ({year})"
            else:
                self._title_cache = self.movie.title
        return self._title_cache

    def __iter__(self):
        return iter(self.episode_list)

    def __getitem__(self, index):
        return self.episode_list[index]

    def __len__(self):
        return len(self.episode_list)

    def __str__(self):
        return f"HuhuMovieAnime(title='{self.title}')"


def is_huhu_url(url: str) -> bool:
    """Check if a URL belongs to huhu.to."""
    return "huhu.to" in url
