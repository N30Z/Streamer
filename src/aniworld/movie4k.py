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
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import requests

from .config import (
    DEFAULT_REQUEST_TIMEOUT,
    RANDOM_USER_AGENT,
    SUPPORTED_SITES,
    SITE_LANGUAGE_NAMES,
    SUPPORTED_PROVIDERS,
    MOVIE4K_SX,
)
from .parser import arguments


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

            module = importlib.import_module(".extractors", __package__)
            func_name = f"get_direct_link_from_{provider.lower()}"

            if not hasattr(module, func_name):
                raise ValueError(f"Extractor function '{func_name}' not found")

            func = getattr(module, func_name)
            kwargs = {f"embeded_{provider.lower()}_link": self.embeded_link}

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
