import traceback
import logging
import sys
from typing import List

from .models import Anime, Episode, SUPPORTED_SITES
from .movie4k import Movie, MovieAnime, is_movie4k_url
from .parser import get_arguments

from .search import search_anime
from .execute import execute
from .common import generate_links



def _detect_site_from_url(url: str) -> str:
    """Detect the streaming site from a URL."""
    for site, config in SUPPORTED_SITES.items():
        base_url = config["base_url"]
        if url.startswith(base_url):
            return site
    return "aniworld.to"


def _extract_series_slug(url: str) -> str:
    """Extract the series slug from an episode URL using site-specific stream paths."""
    parts = url.split("/")

    for config in SUPPORTED_SITES.values():
        base_url = config["base_url"]
        if not url.startswith(base_url):
            continue

        stream_segments = config["stream_path"].split("/")
        last_segment = stream_segments[-1]

        try:
            idx = parts.index(last_segment)
            return parts[idx + 1]
        except (ValueError, IndexError):
            return None

    return None


def _read_episode_file(episode_file: str) -> List[str]:
    """Read episode URLs from a file."""
    try:
        with open(episode_file, "r", encoding="UTF-8") as file:
            urls = [line.strip() for line in file if line.strip().startswith("http")]
            return urls
    except FileNotFoundError:
        logging.error("The specified episode file does not exist: %s", episode_file)
        sys.exit(1)
    except IOError as err:
        logging.error("Error reading the episode file: %s", err)
        sys.exit(1)


def _collect_episode_links() -> List[str]:
    """Collect episode links from arguments and files."""
    links = []
    arguments = get_arguments()

    if arguments.episode_file:
        urls = _read_episode_file(arguments.episode_file)
        links.extend(urls)

    if arguments.episode:
        links.extend(arguments.episode)

    links = [link.rstrip("/") for link in links]

    movie4k_links = [link for link in links if is_movie4k_url(link)]
    series_links = [link for link in links if not is_movie4k_url(link)]

    processed_links = generate_links(series_links, arguments) if series_links else []

    return processed_links + movie4k_links


def _group_episodes_by_series(links: List[str]) -> List[Anime]:
    """Group episodes by series and create Anime objects.

    Special-cases: movie4k.sx watch URLs are treated as movies and returned as
    `MovieAnime` wrappers rather than regular `Anime` objects so the download
    pipeline uses the Movie API instead of HTML scraping.
    """
    if not links:
        return []

    anime_list = []
    episode_list = []
    current_anime = None

    for link in links:
        if not link:
            continue

        # If this is a movie4k link, flush any current grouped episodes and
        # append a MovieAnime directly.
        if is_movie4k_url(link):
            # Flush any pending series episodes
            if episode_list:
                episode_site = (
                    episode_list[0].site if episode_list else "aniworld.to"
                )
                anime_list.append(Anime(episode_list=episode_list, site=episode_site))
                episode_list = []
                current_anime = None

            try:
                movie = Movie(url=link)
                anime_list.append(MovieAnime(movie))
            except Exception as err:
                logging.error("Failed to create Movie from '%s': %s", link, err)
            continue

        series_slug = _extract_series_slug(link)
        if series_slug is None:
            logging.warning("Invalid episode link format: %s", link)
            continue

        site = _detect_site_from_url(link)

        if series_slug != current_anime:
            if episode_list:
                episode_site = (
                    episode_list[0].site if episode_list else "aniworld.to"
                )
                anime_list.append(Anime(episode_list=episode_list, site=episode_site))
                episode_list = []
            current_anime = series_slug

        episode_list.append(Episode(link=link, site=site))

    if episode_list:
        episode_site = episode_list[0].site if episode_list else "aniworld.to"
        anime_list.append(Anime(episode_list=episode_list, site=episode_site))

    return anime_list


def _handle_episode_mode() -> None:
    arguments = get_arguments()
    """Handle episode/file mode execution."""
    links = _collect_episode_links()

    if not links:
        slug = arguments.slug or search_anime()
        episode = Episode(slug=slug)
        anime_list = [Anime(episode_list=[episode])]
    else:
        movie4k_links = [link for link in links if is_movie4k_url(link)]
        series_links = [link for link in links if not is_movie4k_url(link)]

        anime_list = []

        for link in movie4k_links:
            try:
                movie = Movie(url=link)
                anime_list.append(MovieAnime(movie))
            except Exception as err:
                logging.error("Failed to create Movie from '%s': %s", link, err)

        if series_links:
            anime_list.extend(_group_episodes_by_series(series_links))

    execute(anime_list=anime_list)


def _handle_runtime_error(e: Exception) -> None:
    arguments = get_arguments()
    """Handle runtime errors with proper formatting."""
    if arguments.debug:
        traceback.print_exc()
    else:
        print(f"Error: {e}")
        print("\nFor more detailed information, use --debug and try again.")


def aniworld() -> None:
    arguments = get_arguments()
    """
    Main entry point for the AniWorld downloader.

    Execution modes:
    1. Web UI mode (default) - starts Flask web interface
    2. Episode/file mode - downloads specific episodes via CLI
    """
    try:
        # Ensure FFmpeg is available (download if missing)
        from .ffmpeg_downloader import ensure_ffmpeg
        try:
            ensure_ffmpeg()
        except Exception as ffmpeg_err:
            logging.warning("FFmpeg auto-download failed: %s", ffmpeg_err)

        # Handle web UI mode
        if arguments.web_ui:
            from .web.app import start_web_interface

            start_web_interface(
                arguments, port=arguments.web_port, debug=arguments.debug
            )
            return

        # Handle episode/file mode
        if arguments.episode or arguments.episode_file:
            _handle_episode_mode()
            return

        # Default: start web UI
        from .web.app import start_web_interface

        start_web_interface(
            arguments, port=arguments.web_port, debug=arguments.debug
        )

    except KeyboardInterrupt:
        pass
    except Exception as err:
        _handle_runtime_error(err)


if __name__ == "__main__":
    aniworld()
