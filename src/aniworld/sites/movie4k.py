"""
Movie4k.sx support module.

This module provides API-based access to movie4k.sx streaming site.
Unlike aniworld.to and s.to which use HTML scraping, movie4k.sx
provides a JSON API for movie data and streaming links.

The module provides:
- Movie: Core movie data and streaming logic
- MovieAnime: Adapter that wraps Movie to be compatible with the
  existing Anime/Episode action pipeline (watch, download, syncplay)
"""

import importlib
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, quote, urljoin

import requests
from bs4 import BeautifulSoup

from ..config import (
    DEFAULT_REQUEST_TIMEOUT,
    RANDOM_USER_AGENT,
    SUPPORTED_SITES,
    SITE_LANGUAGE_NAMES,
    SUPPORTED_PROVIDERS,
    MOVIE4K_SX,
)
from ..parser import arguments


# Provider name mappings from stream URLs to internal provider names
MOVIE4K_PROVIDER_MAPPING = {
    "streamtape": "Streamtape",
    "filemoon": "Filemoon",
    "doodstream": "Doodstream",
    "dood": "Doodstream",
    "vidoza": "Vidoza",
    "voe": "VOE",
}


def _extract_provider_from_url(url: str) -> Optional[str]:
    """
    Extract provider name from a streaming URL.

    Args:
        url: The streaming URL

    Returns:
        Provider name or None if not recognized
    """
    url_lower = url.lower()
    for pattern, provider in MOVIE4K_PROVIDER_MAPPING.items():
        if pattern in url_lower:
            return provider
    return None


def _title_to_slug(title: str) -> str:
    """Convert a movie title to a URL slug.

    Example: "Greenland *ENGLISH*" -> "greenland-english"
    """
    # Lowercase and replace non-alphanumeric chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return slug.strip("-")


def _parse_api_results(data: Any) -> List[Dict]:
    """
    Parse movie4k.sx API response into a list of result dicts.

    Handles both list responses and dict responses with nested arrays.
    The browse API returns ``{"pager": {...}, "movies": [...]}``.
    Individual movie objects may or may not contain a ``slug`` field;
    when missing, it is derived from the title.
    """
    movies = []
    items = []

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Try common response wrapper keys
        for key in ("movies", "results", "data", "items"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        if not items:
            # Maybe the dict itself is a single movie
            if "_id" in data:
                items = [data]
    else:
        return movies

    for movie in items:
        movie_id = movie.get("_id", "")
        title = movie.get("title", "")
        if not movie_id:
            continue

        slug = movie.get("slug", "") or _title_to_slug(title)
        if not slug:
            continue

        poster = movie.get("poster_path", "")
        cover = (
            f"https://image.tmdb.org/t/p/w220_and_h330_face{poster}"
            if poster
            else ""
        )
        movies.append({
            "name": title,
            "link": f"{MOVIE4K_SX}/watch/{slug}/{movie_id}",
            "description": movie.get("storyline", movie.get("overview", "")),
            "cover": cover,
            "productionYear": movie.get("year", ""),
        })

    return movies


def _scrape_browse_results(keyword: str) -> List[Dict]:
    """
    Scrape movie4k.sx HTML browse/search page as a fallback.

    Tries the /browse page with keyword parameter and parses
    the HTML for movie entries.
    """
    search_url = f"{MOVIE4K_SX}/browse?keyword={quote(keyword)}&type=movies"
    print("Scraping movie4k.sx HTML browse page:", search_url)
    try:
        response = requests.get(
            search_url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers={"User-Agent": RANDOM_USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as err:
        logging.warning("movie4k.sx HTML browse request failed: %s", err)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    seen_slugs = set()

    # Look for links matching /watch/{slug}/{id} pattern
    watch_links = soup.find_all("a", href=re.compile(r"/watch/[^/]+/[a-f0-9]+"))

    for link in watch_links:
        href = link.get("href", "")
        if not href:
            continue

        # Parse /watch/{slug}/{movie_id}
        parts = href.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "watch":
            continue

        slug = parts[1]
        movie_id = parts[2]

        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # Extract title from link text or parent context
        name = ""
        parent = link.find_parent(["div", "article", "li"])
        if parent:
            h_tag = parent.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if h_tag:
                name = h_tag.get_text(strip=True)
        if not name:
            name = link.get("title", "")
        if not name:
            name = link.get_text(strip=True)
        if not name:
            name = slug.replace("-", " ").title()

        # Extract cover image
        cover = ""
        img_context = parent if parent else link
        img = img_context.find("img")
        if img:
            cover = img.get("data-src") or img.get("src") or ""
            if cover and cover.startswith("/"):
                cover = MOVIE4K_SX + cover

        # Extract year if present
        year = ""
        if parent:
            year_el = parent.find("span", class_="year") or parent.find(
                class_="productionYear"
            )
            if year_el:
                year = year_el.get_text(strip=True)
            else:
                # Try to find year in text like "(2024)"
                text = parent.get_text()
                year_match = re.search(r"\((\d{4})\)", text)
                if year_match:
                    year = year_match.group(1)

        # Extract description
        description = ""
        if parent:
            desc_el = parent.find("p") or parent.find(class_="description")
            if desc_el:
                description = desc_el.get_text(strip=True)

        results.append({
            "name": name,
            "link": f"{MOVIE4K_SX}/watch/{slug}/{movie_id}",
            "description": description,
            "cover": cover,
            "productionYear": year,
        })

    return results


def fetch_popular_and_new_movie4k() -> Dict[str, List[Dict[str, str]]]:
    """
    Fetch popular (trending) and new movies from movie4k.sx.

    Uses the movie4k.sx JSON browse API with order_by parameters
    to get trending and newest movies.

    Returns:
        Dictionary with 'popular' and 'new' keys containing lists of movie data
    """
    result = {"popular": [], "new": []}

    # Fetch trending/popular movies
    for order_by, key in [("trending", "popular"), ("Neu", "new")]:
        api_url = (
            f"{MOVIE4K_SX}/data/browse/"
            f"?order_by={order_by}&type=movies&lang=2"
        )
        try:
            resp = requests.get(
                api_url,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                headers={
                    "User-Agent": RANDOM_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            items = []
            if isinstance(data, dict):
                for k in ("movies", "results", "data", "items"):
                    if k in data and isinstance(data[k], list):
                        items = data[k]
                        break
            elif isinstance(data, list):
                items = data

            for movie in items:
                title = movie.get("title", "")
                if not title:
                    continue

                poster = movie.get("poster_path", "")
                cover = (
                    f"https://image.tmdb.org/t/p/w220_and_h330_face{poster}"
                    if poster
                    else ""
                )

                if cover:
                    result[key].append({"name": title, "cover": cover})

        except (requests.RequestException, ValueError, KeyError) as err:
            logging.warning(
                "movie4k.sx browse API failed for %s: %s", order_by, err
            )

    return result


def fetch_movie4k_search_results(keyword: str) -> List[Dict]:
    """
    Search movie4k.sx for movies/series matching keyword.

    Tries the JSON API first (with and without language filter),
    then falls back to HTML scraping if the API returns no results.

    Args:
        keyword: The search term

    Returns:
        List of result dicts with keys: name, link, description, cover, productionYear
    """
    results = []

    # Try JSON API without language filter first (broader results)
    for api_url in [
        f"{MOVIE4K_SX}/data/browse/?keyword={quote(keyword)}&type=movies",
        f"{MOVIE4K_SX}/data/browse/?keyword={quote(keyword)}&lang=2&type=movies",
    ]:
        try:
            resp = requests.get(
                api_url,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                headers={
                    "User-Agent": RANDOM_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            results = _parse_api_results(data)
            if results:
                logging.debug(
                    "movie4k.sx API returned %d results from %s", len(results), api_url
                )
                return results
            logging.debug("movie4k.sx API returned empty results from %s", api_url)
        except requests.RequestException as err:
            logging.warning("movie4k.sx API request failed (%s): %s", api_url, err)
        except (ValueError, KeyError) as err:
            logging.warning("movie4k.sx API response parse error: %s", err)

    # Fallback: scrape the HTML browse page
    logging.info("movie4k.sx API returned no results, trying HTML scrape fallback")
    results = _scrape_browse_results(keyword)
    if results:
        logging.debug("movie4k.sx HTML scrape returned %d results", len(results))
    else:
        logging.warning("movie4k.sx: no results found for keyword '%s'", keyword)

    return results


class Movie:
    """
    Represents a movie from movie4k.sx with API-based data management.

    This class provides access to movie data and streaming links via
    the movie4k.sx JSON API instead of HTML scraping.

    Example:
        movie = Movie(url="https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98")
        movie = Movie(movie_id="6195193258607cdfb9fa2e98")
    """

    def __init__(
        self,
        url: Optional[str] = None,
        movie_id: Optional[str] = None,
        title: Optional[str] = None,
        slug: Optional[str] = None,
        _selected_provider: Optional[str] = None,
        _selected_language: Optional[str] = None,
    ) -> None:
        if not url and not movie_id:
            raise ValueError("Provide either 'url' or 'movie_id'.")

        self.site = "movie4k.sx"
        self.site_config = SUPPORTED_SITES[self.site]
        self.base_url = self.site_config["base_url"]

        if url:
            self.movie_id, self.slug = self._parse_url(url)
        else:
            self.movie_id = movie_id
            self.slug = slug

        self._api_data_cache: Optional[Dict[str, Any]] = None
        self._lang_list_cache: Optional[List[Dict]] = None

        self._title = title
        self._year: Optional[int] = None
        self._streams: Optional[List[Dict]] = None
        self._overview: Optional[str] = None
        self._runtime: Optional[str] = None
        self._rating: Optional[str] = None
        self._genres: Optional[str] = None

        self._selected_provider = _selected_provider or getattr(
            arguments, "provider", None
        )
        self._selected_language = _selected_language or getattr(
            arguments, "language", "Deutsch"
        )

        self.embeded_link: Optional[str] = None
        self.direct_link: Optional[str] = None

        self.link = f"{self.base_url}/watch/{self.slug}/{self.movie_id}"

        # Episode-compatible attributes for the action pipeline
        self.season = 0
        self.episode = 1
        self.season_episode_count: Dict[int, int] = {0: 1}
        self.movie_episode_count: int = 1

    def _parse_url(self, url: str) -> tuple:
        """Parse movie4k.sx URL to extract movie_id and slug."""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")

            # Expected: /watch/{slug}/{movie_id}
            if len(path_parts) >= 3 and path_parts[0] == "watch":
                return path_parts[2], path_parts[1]

            raise ValueError(f"Invalid movie4k.sx URL format: {url}")
        except Exception as err:
            raise ValueError(f"Failed to parse movie4k.sx URL '{url}': {err}") from err

    def _fetch_api_data(self) -> Dict[str, Any]:
        """Fetch movie data from movie4k.sx API."""
        if self._api_data_cache is not None:
            return self._api_data_cache

        api_url = f"{self.base_url}/data/watch/?_id={self.movie_id}"
        response = requests.get(
            api_url,
            timeout=DEFAULT_REQUEST_TIMEOUT,
            headers={
                "User-Agent": RANDOM_USER_AGENT,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        self._api_data_cache = response.json()
        return self._api_data_cache

    def _fetch_lang_list(self) -> List[Dict]:
        """Fetch available languages for the movie."""
        if self._lang_list_cache is not None:
            return self._lang_list_cache

        try:
            api_url = f"{self.base_url}/data/langList/?_id={self.movie_id}"
            response = requests.get(
                api_url,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                headers={
                    "User-Agent": RANDOM_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            self._lang_list_cache = response.json()
            return self._lang_list_cache
        except requests.RequestException as err:
            logging.error("Failed to fetch movie4k.sx language list: %s", err)
            return []

    @property
    def title(self) -> str:
        if self._title is None:
            data = self._fetch_api_data()
            self._title = data.get("title", f"Unknown ({self.slug})")
        return self._title

    @property
    def year(self) -> int:
        if self._year is None:
            data = self._fetch_api_data()
            self._year = data.get("year", 0)
        return self._year

    @property
    def overview(self) -> str:
        if self._overview is None:
            data = self._fetch_api_data()
            self._overview = data.get("storyline") or data.get("overview", "")
        return self._overview

    @property
    def runtime(self) -> str:
        if self._runtime is None:
            data = self._fetch_api_data()
            self._runtime = data.get("runtime", "")
        return self._runtime

    @property
    def rating(self) -> str:
        if self._rating is None:
            data = self._fetch_api_data()
            self._rating = data.get("rating", "")
        return self._rating

    @property
    def genres(self) -> str:
        if self._genres is None:
            data = self._fetch_api_data()
            self._genres = data.get("genres", "")
        return self._genres

    @property
    def streams(self) -> List[Dict]:
        if self._streams is None:
            data = self._fetch_api_data()
            self._streams = data.get("streams", [])
        return self._streams

    @property
    def available_languages(self) -> List[str]:
        lang_list = self._fetch_lang_list()
        site_lang_names = SITE_LANGUAGE_NAMES.get(self.site, {})
        languages = []
        for lang_entry in lang_list:
            lang_code = lang_entry.get("lang")
            lang_name = site_lang_names.get(lang_code, f"Unknown({lang_code})")
            if lang_name not in languages:
                languages.append(lang_name)
        return languages

    @property
    def providers(self) -> Dict[str, List[str]]:
        """Get available providers mapped to their stream URLs."""
        provider_streams: Dict[str, List[str]] = {}
        for stream in self.streams:
            stream_url = stream.get("stream", "")
            if not stream_url:
                continue
            provider = _extract_provider_from_url(stream_url)
            if provider and provider in SUPPORTED_PROVIDERS:
                if provider not in provider_streams:
                    provider_streams[provider] = []
                provider_streams[provider].append(stream_url)
        return provider_streams

    @property
    def provider_names(self) -> List[str]:
        return list(self.providers.keys())

    def get_stream_url(self, provider: Optional[str] = None) -> Optional[str]:
        """Get a stream URL for the specified or first available provider."""
        if provider:
            self._selected_provider = provider

        providers = self.providers

        # Try selected provider first
        if self._selected_provider and self._selected_provider in providers:
            urls = providers[self._selected_provider]
            if urls:
                self.embeded_link = urls[0]
                return self.embeded_link

        # Fallback to first available supported provider
        for prov_name in SUPPORTED_PROVIDERS:
            if prov_name in providers and providers[prov_name]:
                logging.info(
                    "Provider '%s' not available, using '%s'",
                    self._selected_provider,
                    prov_name,
                )
                self._selected_provider = prov_name
                self.embeded_link = providers[prov_name][0]
                return self.embeded_link

        logging.warning("No supported provider found for movie: %s", self.title)
        return None

    def _resolve_stream_url_for_movie(self, stream_url: str, referer: Optional[str] = None) -> str:
        """Resolve movie4k stream redirects (HEAD/GET) and return final URL.

        This helper is scoped to movie4k and attempts to follow server redirects
        (via HEAD first, falling back to GET) up to a small limit. It also handles
        protocol-relative Location headers ("//..."). On network errors it
        returns the original stream_url as a safe fallback.
        """
        headers = {"User-Agent": RANDOM_USER_AGENT}
        if referer:
            headers["Referer"] = referer
        url = stream_url
        for _ in range(5):
            try:
                resp = requests.head(url, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT, allow_redirects=False)
                # Follow HTTP redirects manually if Location header provided
                if resp.status_code in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                    location = resp.headers["Location"]
                    if location.startswith("//"):
                        location = "https:" + location
                    url = urljoin(url, location)
                    continue

                # If HEAD didn't reveal a redirect, perform GET with allow_redirects=True
                resp_get = requests.get(url, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT, allow_redirects=True)
                final = getattr(resp_get, "url", None)
                if final and final != url:
                    return final
                return url
            except requests.RequestException:
                # On request failure return the original URL to avoid failing the whole flow
                return stream_url
        return url

    def get_direct_link(self) -> Optional[str]:
        """
        Get the direct streaming link for the movie.

        Compatible with Episode.get_direct_link() interface.
        """
        try:
            if not self.embeded_link:
                if not self.get_stream_url():
                    logging.error("Failed to get stream URL for '%s'", self.title)
                    return None

            provider = self._selected_provider

            if provider not in SUPPORTED_PROVIDERS:
                raise ValueError(
                    f"Provider '{provider}' is not supported. "
                    f"Supported: {SUPPORTED_PROVIDERS}"
                )

            module = importlib.import_module(".extractors", "aniworld")
            func_name = f"get_direct_link_from_{provider.lower()}"

            if not hasattr(module, func_name):
                raise ValueError(f"Extractor function '{func_name}' not found")

            func = getattr(module, func_name)
            kwargs = {f"embeded_{provider.lower()}_link": self.embeded_link}

            # Movie4k-specific: resolve redirects (if any) and normalize provider URL
            try:
                resolved = self._resolve_stream_url_for_movie(self.embeded_link, referer=self.link)
                if resolved and resolved != self.embeded_link:
                    resolved_provider = _extract_provider_from_url(resolved)
                    if resolved_provider and resolved_provider in SUPPORTED_PROVIDERS:
                        provider = resolved_provider
                        self._selected_provider = provider
                        self.embeded_link = resolved
                        kwargs = {f"embeded_{provider.lower()}_link": self.embeded_link}
            except Exception:
                pass

            # Provide referer (the movie page URL) to providers that need it
            kwargs["referer"] = self.link

            if provider == "Luluvdo":
                kwargs["arguments"] = arguments

            self.direct_link = func(**kwargs)

            if not self.direct_link:
                raise ValueError(f"Provider '{provider}' returned empty direct link")

            return self.direct_link

        except Exception as err:
            logging.error("Error getting direct link: %s", err)
            raise

    def __str__(self) -> str:
        return f"Movie(title='{self.title}', year={self.year})"

    def __repr__(self) -> str:
        return (
            f"Movie(movie_id='{self.movie_id}', title='{self.title}', "
            f"slug='{self.slug}', providers={self.provider_names})"
        )


class MovieAnime:
    """
    Adapter that wraps a Movie to be compatible with the Anime interface.

    The existing action pipeline (watch, download, syncplay) expects
    Anime objects that:
    - Have title, slug, site, action, provider, language, aniskip attributes
    - Are iterable (yield Episode-like objects)
    - Episode objects have season, episode, slug, get_direct_link(), etc.

    Movie already implements the Episode-compatible interface (season=0,
    episode=1, get_direct_link()). This adapter adds the Anime-level
    attributes and makes the Movie iterable as a single-item list.

    Example:
        movie = Movie(url="https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98")
        anime = MovieAnime(movie)
        execute(anime_list=[anime])
    """

    def __init__(self, movie: Movie) -> None:
        self.movie = movie
        self.site = movie.site
        self.slug = movie.slug
        self.episode_list = [movie]

        self.action = getattr(arguments, "action", "Watch")
        self.provider = movie._selected_provider
        self.language = movie._selected_language
        self.aniskip = False
        self.output_directory = getattr(arguments, "output_dir", "")

        self._title_cache = None

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
        return f"MovieAnime(title='{self.title}', provider='{self.provider}')"


def is_movie4k_url(url: str) -> bool:
    """Check if a URL is a movie4k.sx URL."""
    return "movie4k" in url
