import importlib
import json
import logging
import re
from functools import lru_cache
import requests
import requests.models
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple, Any

class Episode:
    """
    Represents an episode of an anime series with comprehensive data management.

    This class provides a complete interface for episode data including metadata,
    provider/language management, and streaming link generation with lazy loading
    and caching for optimal performance.

    Supports multiple streaming sites:
    - ANIWORLD_TO (default)
    - S_TO

    Example:
        Episode(
            slug="loner-life-in-another-world",
            season=1,
            episode=1,
            site="aniworld.to"  # Optional, defaults to aniworld.to
        )

    Required Attributes:
        link (str) OR (slug (str) + season (int) + episode (int)):
        Either a direct link to the episode or components to construct it.

    Attributes:
        anime_title (str): The title of the anime the episode belongs to.
        title_german (str): The German title of the episode.
        title_english (str): The English title of the episode.
        season (int): The season number (0 for movies).
        episode (int): The episode number within the season.
        slug (str): URL-friendly anime identifier.
        site (str): The streaming site (ANIWORLD_TO or S_TO).
        link (str): The direct link to the episode page.
        mal_id (int): The MyAnimeList ID for the episode.
        redirect_link (str): The redirect link for streaming.
        embeded_link (str): The embedded streaming link.
        direct_link (str): The direct streaming link.
        provider (Dict[str, Dict[int, str]]): Available providers and their links.
        provider_name (List[str]): List of provider names.
        language (List[int]): List of available language codes.
        language_name (List[str]): List of available language names.
        season_episode_count (Dict[int, int]): Season to episode count mapping.
        movie_episode_count (int): Number of movie episodes.
        html (requests.models.Response): HTML response object.
        _selected_provider (str): Currently selected provider.
        _selected_language (str): Currently selected language.
    """

    def __init__(
        self,
        anime_title: Optional[str] = None,
        title_german: Optional[str] = None,
        title_english: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        slug: Optional[str] = None,
        site: str = "aniworld.to",
        link: Optional[str] = None,
        mal_id: Optional[int] = None,
        redirect_link: Optional[str] = None,
        embeded_link: Optional[str] = None,
        direct_link: Optional[str] = None,
        provider: Optional[Dict[str, Dict[int, str]]] = None,
        provider_name: Optional[List[str]] = None,
        language: Optional[List[int]] = None,
        language_name: Optional[List[str]] = None,
        season_episode_count: Optional[Dict[int, int]] = None,
        has_movies: bool = False,
        movie_episode_count: Optional[int] = None,
        html: Optional[requests.models.Response] = None,
        _selected_provider: Optional[str] = None,
        _selected_language: Optional[str] = None,
    ) -> None:
        """
        Initialize an Episode instance with comprehensive validation.

        Args:
            anime_title: Anime title
            title_german: German episode title
            title_english: English episode title
            season: Season number (0 for movies)
            episode: Episode number
            slug: Anime slug identifier
            site: Streaming site to use (ANIWORLD_TO or S_TO)
            link: Direct episode link
            mal_id: MyAnimeList ID
            redirect_link: Redirect streaming link
            embeded_link: Embedded streaming link
            direct_link: Direct streaming link
            provider: Available providers dictionary
            provider_name: List of provider names
            language: Available language codes
            language_name: Available language names
            season_episode_count: Season episode counts
            has_movies: Whether anime has movies
            movie_episode_count: Number of movies
            html: Pre-fetched HTML response
            _selected_provider: Selected provider
            _selected_language: Selected language

        Raises:
            ValueError: If neither link nor (slug + season + episode) provided
        """
        # Validate required parameters
        if not link and (not slug or season is None or episode is None):
            raise ValueError(
                "Provide either 'link' or 'slug' with 'season' and 'episode'."
            )

        # Validate site
        if site not in SUPPORTED_SITES:
            raise ValueError(
                f"Unsupported site: {site}. Supported sites: {list(SUPPORTED_SITES.keys())}"
            )

        self.site = site
        self.site_config = SUPPORTED_SITES[site]
        self.base_url = self.site_config["base_url"]
        self.stream_path = self.site_config["stream_path"]

        # Initialize core attributes
        self.anime_title = anime_title
        self.title_german = title_german
        self.title_english = title_english
        self.season = season
        self.episode = episode
        self.slug = slug
        self.link = link
        self.mal_id = mal_id

        # Initialize streaming attributes
        self.redirect_link = redirect_link
        self.embeded_link = embeded_link
        self.direct_link = direct_link

        # Initialize provider and language data
        self.provider = provider or {}
        self.provider_name = provider_name or []
        self.language = language or []
        self.language_name = language_name or []

        # Initialize metadata
        self.season_episode_count = season_episode_count or {}
        self.has_movies = has_movies
        self.movie_episode_count = movie_episode_count or 0

        # Initialize selected options with fallbacks
        self._selected_provider = _selected_provider or getattr(
            arguments, "provider", None
        )
        self._selected_language = _selected_language or getattr(
            arguments, "language", "German Sub"
        )

        # Cache for HTML and other expensive operations
        self._html_cache = html
        self._provider_cache = None
        self._language_cache = None
        self._basic_details_filled = False
        self._full_details_filled = False

        if self.link:
            self._auto_fill_basic_details()
        else:
            self.auto_fill_details()

    @property
    def html(self) -> requests.models.Response:
        """
        Lazy-loaded HTML response for the episode page.

        Returns:
            HTML response object

        Raises:
            requests.RequestException: If HTTP request fails
        """
        if self._html_cache is None:
            if not self.link:
                raise ValueError("Cannot fetch HTML without episode link")

            try:
                self._html_cache = requests.get(
                    self.link,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers={"User-Agent": RANDOM_USER_AGENT},
                )
                self._html_cache.raise_for_status()
            except requests.RequestException as err:
                logging.error(
                    "Failed to fetch episode HTML for link '%s': %s", self.link, err
                )
                raise

        return self._html_cache

    def _get_episode_titles_from_html(self) -> Tuple[str, str]:
        """
        Extract episode titles from HTML.

        Returns:
            Tuple of (german_title, english_title)
        """
        try:
            episode_soup = BeautifulSoup(self.html.content, "html.parser")

            german_title_div = episode_soup.find("span", class_="episodeGermanTitle")
            english_title_div = episode_soup.find("small", class_="episodeEnglishTitle")

            german_title = (
                german_title_div.get_text(strip=True) if german_title_div else ""
            )
            english_title = (
                english_title_div.get_text(strip=True) if english_title_div else ""
            )

            return german_title, english_title

        except Exception as err:
            logging.error("Error extracting episode titles: %s", err)
            return "", ""

    def _extract_season_from_link(self) -> int:
        """
        Extract season number from episode link.

        Returns:
            Season number (0 for movies)

        Raises:
            ValueError: If season cannot be extracted
        """
        if not self.link:
            raise ValueError("No link provided to extract season from")

        # Check if it's a movie
        if "/filme/" in self.link:
            return 0

        # Extract season from link pattern like /staffel-2/
        try:
            season_part = self.link.split("/")[-2]  # e.g., "staffel-2"
            numbers = re.findall(r"\d+", season_part)

            if numbers:
                return int(numbers[-1])

            raise ValueError(f"No valid season number found in link: {self.link}")

        except (IndexError, ValueError) as err:
            raise ValueError(
                f"Failed to extract season from link '{self.link}': {err}"
            ) from err

    def _extract_episode_from_link(self) -> int:
        """
        Extract episode number from episode link.

        Returns:
            Episode number

        Raises:
            ValueError: If episode cannot be extracted
        """
        if not self.link:
            raise ValueError("No link provided to extract episode from")

        try:
            # Remove trailing slash if present
            link = self.link.rstrip("/")

            # Extract episode from link pattern like /episode-2 or /film-1
            episode_part = link.split("/")[-1]  # e.g., "episode-2" or "film-1"
            numbers = re.findall(r"\d+", episode_part)

            if numbers:
                return int(numbers[-1])

            raise ValueError(f"No valid episode number found in link: {self.link}")

        except (IndexError, ValueError) as err:
            raise ValueError(
                f"Failed to extract episode from link '{self.link}': {err}"
            ) from err

    @lru_cache(maxsize=32)
    def _get_available_languages_from_html(self) -> List[int]:
        """
        Extract available language codes from HTML with caching.

        Language Codes:
            1: German Dub
            2: English Sub / Deutsch
            3: German Sub / English

        Returns:
            List of available language codes
        """
        try:
            # Special-case: movie4k watch pages provide languages via API
            if self.link and ("movie4k.sx" in self.link or "/watch/" in self.link):
                try:
                    from .sites.movie4k import Movie as Movie4kMovie

                    movie = Movie4kMovie(url=self.link)
                    available_names = movie.available_languages

                    site_codes = SITE_LANGUAGE_CODES.get("movie4k.sx", {})
                    lang_keys = []
                    for name in available_names:
                        key = site_codes.get(name)
                        if key is not None:
                            lang_keys.append(key)
                    if not lang_keys:
                        logging.debug("_get_available_languages_from_html: Movie4k returned no mapped language keys for %s", self.link)
                    return sorted(lang_keys)
                except Exception as err:
                    logging.warning("Failed to fetch movie4k languages for %s: %s", self.link, err)
                    # Fall through to HTML parsing as fallback

            episode_soup = BeautifulSoup(self.html.content, "html.parser")

            # s.to uses button.link-box[data-language-id] inside div#episode-links
            episode_links_div = episode_soup.find("div", id="episode-links")
            if episode_links_div:
                language_codes = set()
                for btn in episode_links_div.find_all(
                    "button", class_="link-box"
                ):
                    lang_id = btn.get("data-language-id")
                    if lang_id and lang_id.isdigit():
                        language_codes.add(int(lang_id))
                return sorted(language_codes)

            # aniworld.to uses div.changeLanguageBox > img[data-lang-key]
            change_language_box = episode_soup.find("div", class_="changeLanguageBox")

            if not change_language_box:
                logging.warning(
                    "_get_available_languages_from_html: No language selection found for episode: %s",
                    self.link,
                )
                return []

            language_codes = []
            img_tags = change_language_box.find_all("img")

            for img in img_tags:
                lang_key = img.get("data-lang-key")
                if lang_key and lang_key.isdigit():
                    language_codes.append(int(lang_key))

            return sorted(language_codes)

        except Exception as err:
            logging.error("Error extracting language codes: %s", err)
            return []

    @lru_cache(maxsize=32)
    def _get_providers_from_html(self) -> Dict[str, Dict[int, str]]:
        """
        Extract streaming providers from HTML with caching.

        Returns:
            Dictionary mapping provider names to language-URL mappings

        Example:
            {
                'VOE': {1: 'https://aniworld.to/redirect/1766412',
                        2: 'https://aniworld.to/redirect/1766405'},
                'Doodstream': {1: 'https://aniworld.to/redirect/1987922',
                               2: 'https://aniworld.to/redirect/2700342'}
            }

        Raises:
            ValueError: If no providers found
        """
        try:
            # Special-case movie4k watch pages: use the movie API instead of fragile HTML parsing
            if self.link and ("movie4k.sx" in self.link or "/watch/" in self.link):
                try:
                    from .sites.movie4k import Movie as Movie4kMovie, _extract_provider_from_url

                    movie = Movie4kMovie(url=self.link)
                    providers = {}

                    # movie4k uses its own language code mapping; use that explicitly
                    site_codes = SITE_LANGUAGE_CODES.get("movie4k.sx", {})
                    available_lang_keys = []
                    for name in movie.available_languages:
                        key = site_codes.get(name)
                        if key is not None:
                            available_lang_keys.append((key, name))

                    for stream in movie.streams:
                        # stream items from API can vary in shape; try common keys
                        stream_url = (
                            stream.get("stream")
                            or stream.get("stream_url")
                            or stream.get("url")
                            or stream.get("file")
                        )
                        if not stream_url:
                            continue

                        provider = _extract_provider_from_url(stream_url)
                        if not provider or provider not in SUPPORTED_PROVIDERS:
                            continue

                        # Determine language key for this stream
                        lang_key = None
                        # Prefer explicit numeric lang codes
                        lang_val = stream.get("lang") or stream.get("language") or stream.get("lang_code")
                        if isinstance(lang_val, int):
                            lang_key = lang_val
                        elif isinstance(lang_val, str):
                            if lang_val.isdigit():
                                lang_key = int(lang_val)
                            else:
                                # map by language name
                                lang_key = SITE_LANGUAGE_CODES.get("movie4k.sx", {}).get(lang_val)

                        # If language not provided, fall back to first available language
                        if lang_key is None and available_lang_keys:
                            lang_key = available_lang_keys[0][0]

                        if lang_key is None:
                            # Unknown language; skip this stream
                            continue

                        if provider not in providers:
                            providers[provider] = {}
                        providers[provider][lang_key] = stream_url

                    if not providers:
                        raise ValueError(
                            f"No streams available for episode: {self.link}\n"
                            "Try again later or check in the community chat."
                        )

                    logging.debug(
                        'Available providers (movie4k API) for "%s":\n%s',
                        self.anime_title,
                        json.dumps(providers, indent=2),
                    )

                    return providers

                except Exception as err:
                    logging.warning("movie4k API provider extraction failed for %s: %s", self.link, err)
                    # Fall through to HTML parsing as a fallback

            soup = BeautifulSoup(self.html.content, "html.parser")
            providers = {}

            # s.to uses button.link-box inside div#episode-links
            episode_links_div = soup.find("div", id="episode-links")
            if episode_links_div:
                for btn in episode_links_div.find_all("button", class_="link-box"):
                    provider_data = self._extract_provider_data_sto(btn)
                    if provider_data:
                        provider_name, lang_key, redirect_url = provider_data
                        if provider_name not in providers:
                            providers[provider_name] = {}
                        providers[provider_name][lang_key] = redirect_url
            else:
                # aniworld.to uses li.episodeLink* elements
                episode_links = soup.find_all(
                    "li", class_=lambda x: x and x.startswith("episodeLink")
                )

                if not episode_links:
                    raise ValueError(
                        f"No streams available for episode: {self.link}\n"
                        "Try again later or check in the community chat."
                    )

                for link in episode_links:
                    provider_data = self._extract_provider_data(link)
                    if provider_data:
                        provider_name, lang_key, redirect_url = provider_data
                        if provider_name not in providers:
                            providers[provider_name] = {}
                        providers[provider_name][lang_key] = redirect_url

            if not providers:
                raise ValueError(
                    f"No streams available for episode: {self.link}\n"
                    "Try again later or check in the community chat."
                )

            logging.debug(
                'Available providers for "%s":\n%s',
                self.anime_title,
                json.dumps(providers, indent=2),
            )

            return providers

        except Exception as err:
            logging.error("_get_providers_from_html: Error extracting providers: %s", err)
            raise

    def _extract_provider_data(self, link_element) -> Optional[Tuple[str, int, str]]:
        """
        Extract provider data from HTML element.

        Args:
            link_element: BeautifulSoup element containing provider data

        Returns:
            Tuple of (provider_name, lang_key, redirect_url) or None
        """
        try:
            # Extract provider name
            provider_name_tag = link_element.find("h4")
            provider_name = (
                provider_name_tag.get_text(strip=True) if provider_name_tag else None
            )

            # Extract redirect link
            redirect_link_tag = link_element.find("a", class_="watchEpisode")
            redirect_path = redirect_link_tag.get("href") if redirect_link_tag else None

            # Extract language key
            lang_key_str = link_element.get("data-lang-key")
            lang_key = (
                int(lang_key_str) if lang_key_str and lang_key_str.isdigit() else None
            )

            # Validate all required data is present
            if provider_name and redirect_path and lang_key:
                redirect_url = f"{self.base_url}{redirect_path}"
                return provider_name, lang_key, redirect_url

            return None

        except (ValueError, AttributeError) as err:
            logging.debug("Failed to extract provider data from element: %s", err)
            return None

    def _extract_provider_data_sto(self, button_element) -> Optional[Tuple[str, int, str]]:
        """
        Extract provider data from an s.to button.link-box element.

        Args:
            button_element: BeautifulSoup button element with data attributes

        Returns:
            Tuple of (provider_name, lang_key, redirect_url) or None
        """
        try:
            provider_name = button_element.get("data-provider-name")
            lang_id_str = button_element.get("data-language-id")
            play_url = button_element.get("data-play-url")

            lang_key = (
                int(lang_id_str) if lang_id_str and lang_id_str.isdigit() else None
            )

            if provider_name and play_url and lang_key is not None:
                redirect_url = f"{self.base_url}{play_url}"
                return provider_name, lang_key, redirect_url

            return None

        except (ValueError, AttributeError) as err:
            logging.debug("Failed to extract s.to provider data from element: %s", err)
            return None

    def _get_language_key_from_name(self, language_name: str) -> int:
        """
        Convert language name to language key using site-specific mappings.

        Args:
            language_name: Language name (e.g., "German Dub")

        Returns:
            Language key integer

        Raises:
            ValueError: If language name is invalid
        """
        # Use site-specific language codes
        site_language_codes = SITE_LANGUAGE_CODES.get(self.site)
        language_key = (
            site_language_codes.get(language_name) if site_language_codes else None
        )

        if language_key is None:
            valid_languages = (
                list(site_language_codes.keys()) if site_language_codes else []
            )
            raise ValueError(
                f"Invalid language: {language_name}. Valid options for {self.site}: {valid_languages}"
            )

        return language_key

    def _get_language_names_from_keys(self, language_keys: List[int]) -> List[str]:
        """
        Convert language keys to language names using site-specific mappings.

        Args:
            language_keys: List of language key integers

        Returns:
            List of language names

        Raises:
            ValueError: If any language key is invalid
        """
        # Use site-specific language names
        site_language_names = SITE_LANGUAGE_NAMES.get(self.site)
        language_names = []

        for key in language_keys:
            name = site_language_names.get(key) if site_language_names else None
            if name is None:
                valid_keys = (
                    list(site_language_names.keys()) if site_language_names else []
                )
                raise ValueError(
                    f"Invalid language key: {key} for site: {self.site}. Valid keys: {valid_keys}"
                )
            language_names.append(name)

        return language_names

    def _get_direct_link_from_provider(self) -> str:
        """
        Get direct streaming link from the selected provider.

        Returns:
            Direct streaming link

        Raises:
            ValueError: If provider is not supported or extraction fails
        """
        provider = self._selected_provider

        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' is currently not supported. "
                f"Supported providers: {SUPPORTED_PROVIDERS}"
            )

        if not self.embeded_link:
            raise ValueError("No embedded link available for direct link extraction")

        try:
            module = importlib.import_module(".extractors", __package__)
            func_name = f"get_direct_link_from_{provider.lower()}"

            if not hasattr(module, func_name):
                raise ValueError(f"Extractor function '{func_name}' not found")

            func = getattr(module, func_name)

            # Prepare kwargs for the extractor function
            kwargs = {f"embeded_{provider.lower()}_link": self.embeded_link}

            # Special case for Luluvdo which needs arguments
            if provider == "Luluvdo":
                kwargs["arguments"] = arguments

            direct_link = func(**kwargs)

            if not direct_link:
                raise ValueError(f"Provider '{provider}' returned empty direct link")

            return direct_link

        except Exception as err:
            logging.error(
                "Error getting direct link from provider '%s': %s", provider, err
            )
            raise ValueError(
                f"Failed to get direct link from provider '{provider}': {err}"
            ) from err

    def get_redirect_link(self) -> Optional[str]:
        """
        Get redirect link for the selected provider and language.

        Returns:
            Redirect link or None if not available
        """
        try:
            # Ensure we have provider data loaded
            self.auto_fill_details()

            lang_key = self._get_language_key_from_name(self._selected_language)

            # Check if selected provider and language combination exists
            if (
                self._selected_provider in self.provider
                and lang_key in self.provider[self._selected_provider]
            ):
                self.redirect_link = self.provider[self._selected_provider][lang_key]
                return self.redirect_link

            # Fallback: find any provider with the selected language
            for provider_name, lang_dict in self.provider.items():
                if lang_key in lang_dict:
                    logging.info(
                        "Switching provider from '%s' to '%s' for language '%s' on site '%s'",
                        self._selected_provider,
                        provider_name,
                        self._selected_language,
                        self.site,
                    )
                    self._selected_provider = provider_name
                    self.redirect_link = lang_dict[lang_key]
                    return self.redirect_link

            # No provider found with selected language
            available_langs = set()
            for lang_dict in self.provider.values():
                available_langs.update(lang_dict.keys())

            # Use site-specific language names for error message
            site_language_names = SITE_LANGUAGE_NAMES.get(self.site)
            available_lang_names = [
                site_language_names.get(key, f"Unknown({key})")
                if site_language_names
                else f"Unknown({key})"
                for key in available_langs
            ]

            logging.warning(
                "No provider found for language '%s' on site '%s'. Available languages: %s",
                self._selected_language,
                self.site,
                available_lang_names,
            )

            self.redirect_link = None
            return None

        except Exception as err:
            logging.error("Error getting redirect link: %s", err)
            self.redirect_link = None
            return None

    def get_embeded_link(self) -> Optional[str]:
        """
        Get embedded streaming link by following the redirect.

        Returns:
            Embedded link or None if unavailable
        """
        if not self.redirect_link:
            self.get_redirect_link()

        if not self.redirect_link:
            logging.warning("No redirect link available for embedded link extraction")
            return None

        try:
            response = requests.get(
                self.redirect_link,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                headers={"User-Agent": RANDOM_USER_AGENT},
                allow_redirects=True,
            )
            response.raise_for_status()

            self.embeded_link = response.url
            return self.embeded_link

        except requests.RequestException as err:
            logging.error(
                "Error getting embedded link from '%s': %s", self.redirect_link, err
            )
            self.embeded_link = None
            return None

    def get_direct_link(
        self, provider: Optional[str] = None, language: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the direct streaming link for the episode.

        Args:
            provider: Provider name to use (overrides selected provider)
            language: Language to use (overrides selected language)

        Returns:
            Direct streaming link or None if unavailable

        Example:
            episode.get_direct_link("VOE", "German Sub")
        """
        # Update selected options if provided
        if provider:
            self._selected_provider = provider

        if language:
            self._selected_language = language

        # Special-case movie4k watch links: delegate to Movie API-based flow
        try:
            if self.link and ("movie4k.sx" in self.link or "/watch/" in self.link):
                try:
                    from .sites.movie4k import Movie as Movie4kMovie

                    movie_obj = Movie4kMovie(url=self.link)

                    # Propagate selected options to the Movie object if set
                    if getattr(self, "_selected_provider", None):
                        movie_obj._selected_provider = self._selected_provider
                    if getattr(self, "_selected_language", None):
                        movie_obj._selected_language = self._selected_language

                    direct = movie_obj.get_direct_link()
                    if direct:
                        # Sync embed/direct links for downstream use
                        self.embeded_link = movie_obj.embeded_link
                        self.direct_link = movie_obj.direct_link
                        return direct
                    else:
                        logging.error("Movie4k movie get_direct_link failed for: %s", self.link)
                        return None
                except Exception as err:
                    logging.error("Movie4k delegation error for '%s': %s", self.link, err)
                    # Fall through to legacy HTML-based flow

        except Exception as err:
            logging.error("Unexpected error in movie4k delegation: %s", err)

        # Validate selected provider
        if self._selected_provider not in SUPPORTED_PROVIDERS:
            logging.error("Provider '%s' is not supported", self._selected_provider)
            return None

        try:
            # Get embedded link if not already available
            if not self.embeded_link:
                if not self.get_embeded_link():
                    logging.error("Failed to get embedded link")
                    return None

            # Get direct link from provider
            self.direct_link = self._get_direct_link_from_provider()
            return self.direct_link

        except Exception as err:
            logging.error("Error getting direct link: %s", err)
            self.direct_link = None
            return None

    def _get_preview_image_link_from_provider(self) -> str:
        """
        Get preview image link from the given provider.

        Args:
            provider: Provider name

        Returns:
            Preview image link

        Raises:
            ValueError: If provider is not supported or extraction fails
        """

        provider = self._selected_provider

        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' is currently not supported. "
                f"Supported providers: {SUPPORTED_PROVIDERS}"
            )

        if not self.embeded_link:
            raise ValueError("No embedded link available for preview image extraction")

        try:
            module = importlib.import_module(".extractors", __package__)
            func_name = f"get_preview_image_link_from_{provider.lower()}"

            if not hasattr(module, func_name):
                raise ValueError(f"Preview extractor function '{func_name}' not found")

            func = getattr(module, func_name)

            # Prepare kwargs for the extractor function
            kwargs = {f"embeded_{provider.lower()}_link": self.embeded_link}
            return func(**kwargs)

        except Exception as err:
            raise ValueError(
                f"Failed to get preview image from provider '{provider}': {err}"
            ) from err

    def get_preview_image_link(self, provider: Optional[str] = None) -> Optional[str]:
        """
        Get the preview image link for the episode.

        Args:
            provider: Provider name to use (overrides selected provider)

        Returns:
            Preview image link or None if unavailable
        """
        # Override provider if passed
        if provider:
            self._selected_provider = provider
            lang_key = next(iter(self.provider.get(provider, {})), None)
            if lang_key is not None:
                lang_name = self._get_language_names_from_keys([lang_key])[0]
                self._selected_language = lang_name

        # Validate provider
        if self._selected_provider not in SUPPORTED_PROVIDERS:
            logging.error("Provider '%s' is not supported", self._selected_provider)
            return None

        try:
            # Ensure embedded link is available
            if not self.embeded_link:
                if not self.get_embeded_link():
                    logging.error("Failed to get embedded link")
                    return None

            # Extract preview image
            preview_link = self._get_preview_image_link_from_provider()

            if not preview_link:
                logging.warning(
                    "No preview image found from provider '%s'", self._selected_provider
                )
                return None

            return preview_link

        except Exception as err:
            logging.error(
                "Error getting preview image from provider '%s': %s",
                self._selected_provider,
                err,
            )
            return None

    def _auto_fill_basic_details(self) -> None:
        """
        Fill only essential details needed for link construction without expensive operations.
        """
        if self._basic_details_filled:
            return

        try:
            # Construct link if missing but have components
            if (
                not self.link
                and self.slug
                and self.season is not None
                and self.episode is not None
            ):
                if self.season == 0:  # Movie
                    self.link = (
                        f"{self.base_url}/{self.stream_path}/{self.slug}/filme/"
                        f"film-{self.episode}"
                    )
                else:  # Regular episode
                    self.link = (
                        f"{self.base_url}/{self.stream_path}/{self.slug}/"
                        f"staffel-{self.season}/episode-{self.episode}"
                    )

            # Extract components from link if missing (no HTTP requests)
            if self.link:
                # Attempt to extract slug differently for movie4k watch links
                if not self.slug:
                    try:
                        if "movie4k.sx" in self.link or "/watch/" in self.link:
                            parts = self.link.rstrip("/").split("/")
                            if "watch" in parts:
                                idx = parts.index("watch")
                                # slug is the segment after 'watch'
                                if idx + 1 < len(parts):
                                    self.slug = parts[idx + 1]
                                else:
                                    self.slug = self.link.split("/")[-3] if len(self.link.split("/")) >= 3 else None
                            else:
                                self.slug = self.link.split("/")[-3]
                        else:
                            self.slug = self.link.split("/")[-3]
                    except IndexError:
                        logging.warning(
                            "Could not extract slug from link: %s", self.link
                        )

                # Special-case movie4k watch links: set as movie (season 0)
                if "/watch/" in self.link or "movie4k.sx" in self.link:
                    try:
                        # If link contains '/watch/', treat it as a movie
                        if self.season is None:
                            self.season = 0
                        if self.episode is None:
                            self.episode = 1
                    except Exception as err:
                        logging.warning("Failed to set movie defaults from link: %s", err)
                else:
                    if self.season is None:
                        try:
                            self.season = self._extract_season_from_link()
                        except ValueError as err:
                            logging.warning("Could not extract season: %s", err)

                    if self.episode is None:
                        try:
                            self.episode = self._extract_episode_from_link()
                        except ValueError as err:
                            logging.warning("Could not extract episode: %s", err)
            self._basic_details_filled = True

        except Exception as err:
            logging.error("Critical error in _auto_fill_basic_details: %s", err)
            self._basic_details_filled = True

    def auto_fill_details(self) -> None:
        """
        Automatically fill episode details from available information.
        This is now called lazily only when needed.
        """
        if self._full_details_filled:
            return

        try:
            # First ensure basic details are filled
            self._auto_fill_basic_details()

            # Fetch and populate metadata if link is available (expensive operations)
            if self.link:
                try:
                    # Get anime title if missing
                    if not self.anime_title:
                        self.anime_title = get_anime_title_from_html(
                            self.html, self.site
                        )

                    # Get episode titles if missing
                    if not self.title_german and not self.title_english:
                        self.title_german, self.title_english = (
                            self._get_episode_titles_from_html()
                        )

                    # Get available languages
                    if not self.language:
                        self.language = self._get_available_languages_from_html()

                    # Get language names
                    if not self.language_name and self.language:
                        self.language_name = self._get_language_names_from_keys(
                            self.language
                        )

                    # Get providers
                    if not self.provider:
                        self.provider = self._get_providers_from_html()

                    # Get provider names
                    if not self.provider_name and self.provider:
                        self.provider_name = list(self.provider.keys())

                except Exception as err:
                    logging.error("Error auto-filling episode details: %s", err)

            self._full_details_filled = True

        except Exception as err:
            logging.error("Critical error in auto_fill_details: %s", err)
            self._full_details_filled = True

    def validate_configuration(self) -> List[str]:
        """
        Validate episode configuration and return any issues.

        Returns:
            List of validation error messages
        """
        issues = []

        if not self.link and (
            not self.slug or self.season is None or self.episode is None
        ):
            issues.append("Either 'link' or 'slug + season + episode' must be provided")

        if self.site not in SUPPORTED_SITES:
            issues.append(f"Unsupported site: {self.site}")

        # Use site-specific language codes for validation
        site_language_codes = SITE_LANGUAGE_CODES.get(self.site)
        if (
            not site_language_codes
            or self._selected_language not in site_language_codes
        ):
            valid_languages = (
                list(site_language_codes.keys()) if site_language_codes else []
            )
            issues.append(
                f"Invalid selected language: {self._selected_language} for site: {self.site}. Valid options: {valid_languages}"
            )

        if (
            self._selected_provider
            and self._selected_provider not in SUPPORTED_PROVIDERS
        ):
            issues.append(f"Unsupported provider: {self._selected_provider}")

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert episode to dictionary representation.

        Returns:
            Dictionary with episode data
        """
        return {
            "anime_title": self.anime_title,
            "title_german": self.title_german,
            "title_english": self.title_english,
            "season": self.season,
            "episode": self.episode,
            "slug": self.slug,
            "site": self.site,
            "link": self.link,
            "mal_id": self.mal_id,
            "redirect_link": self.redirect_link,
            "embeded_link": self.embeded_link,
            "direct_link": self.direct_link,
            "provider_count": len(self.provider) if self.provider else 0,
            "provider_names": self.provider_name,
            "language_codes": self.language,
            "language_names": self.language_name,
            "selected_provider": self._selected_provider,
            "selected_language": self._selected_language,
            "season_episode_count": self.season_episode_count,
            "movie_episode_count": self.movie_episode_count,
        }

    def to_json(self) -> str:
        """
        Convert episode to JSON string representation.

        Returns:
            JSON string with episode data
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        """String representation of episode."""
        return (
            f"Episode(anime='{self.anime_title}', S{self.season:02d}E{self.episode:02d}, "
            f"provider='{self._selected_provider}', language='{self._selected_language}')"
        )

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (
            f"Episode(anime_title='{self.anime_title}', season={self.season}, "
            f"episode={self.episode}, slug='{self.slug}', "
            f"selected_provider='{self._selected_provider}', "
            f"selected_language='{self._selected_language}')"
        )


def test_movie4k_providers_monkeypatch(monkeypatch):
    """Ensure Episode._get_providers_from_html uses Movie API streams for movie links."""
    movie_url = "https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98"

    class DummyMovie:
        def __init__(self, url=None):
            self.url = url
            # Two streams with different providers and language names
            self.streams = [
                {"stream": "https://streamtape.com/e/abcd", "lang": "Deutsch"},
                {"stream": "https://filemoon.sx/f/1234", "lang": "English"},
            ]
            self.available_languages = ["Deutsch", "English"]

    # Monkeypatch the Movie class inside the movie4k module import location used by models
    import aniworld.sites.movie4k as mv4k_mod

    monkeypatch.setattr(mv4k_mod, "Movie", DummyMovie)

    ep = Episode(link=movie_url)

    providers = ep._get_providers_from_html()

    # Expect provider keys to be mapped to supported provider names
    assert "Streamtape" in providers or "Streamtape" in providers
    assert "Filemoon" in providers

    # Language keys should map to site codes (SITE_LANGUAGE_CODES mapping is used internally)
    # Ensure that for one provider we have at least one language mapping
    assert any(isinstance(k, int) for k in providers.get("Streamtape", {}).keys())
    assert any(isinstance(k, int) for k in providers.get("Filemoon", {}).keys())
