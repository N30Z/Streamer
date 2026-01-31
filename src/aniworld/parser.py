import argparse
import importlib
import json
import logging
import random
import sys
from functools import lru_cache
from typing import List, Optional

import requests

from .extractors.provider.hanime import get_direct_link_from_hanime
from . import config


class CaseInsensitiveChoices:
    """Case-insensitive argument choice validator for argparse."""

    def __init__(self, choices: List[str]) -> None:
        self.choices = choices
        self.normalized = {c.lower(): c for c in choices}

    def __call__(self, value: str) -> str:
        key = value.lower()
        if key in self.normalized:
            return self.normalized[key]
        raise argparse.ArgumentTypeError(
            f"invalid choice: {value} (choose from {', '.join(self.choices)})"
        )


@lru_cache(maxsize=128)
def get_random_anime_slug(genre: str) -> Optional[str]:
    """Fetch a random anime slug from the specified genre."""
    if not genre:
        genre = "all"

    url = f"{config.ANIWORLD_TO}/ajax/randomGeneratorSeries"
    data = {"productionStart": "all", "productionEnd": "all", "genres[]": genre}
    headers = {"User-Agent": config.RANDOM_USER_AGENT}

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=config.DEFAULT_REQUEST_TIMEOUT
        )
        response.raise_for_status()

        anime_list = response.json()
        if not anime_list:
            logging.warning("No anime found for genre: %s", genre)
            return None

        random_anime = random.choice(anime_list)
        return random_anime.get("link")

    except requests.RequestException as err:
        logging.error("Network request failed for genre '%s': %s", genre, err)
    except (json.JSONDecodeError, KeyError, TypeError) as err:
        logging.error("Error processing response data for genre '%s': %s", genre, err)

    return None


def _add_general_arguments(parser: argparse.ArgumentParser) -> None:
    """Add general command-line arguments to the parser."""
    general_opts = parser.add_argument_group("General Options")
    general_opts.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode for detailed logs.",
    )
    general_opts.add_argument(
        "-v", "--version", action="store_true", help="Display version information."
    )


def _add_episode_arguments(parser: argparse.ArgumentParser) -> None:
    """Add episode-related command-line arguments to the parser."""
    episode_opts = parser.add_argument_group("Episode Options")
    episode_opts.add_argument(
        "-e", "--episode", type=str, nargs="+", help="Specify one or more episode URLs."
    )
    episode_opts.add_argument(
        "-f", "--episode-file", type=str, help="Provide a file containing episode URLs."
    )
    episode_opts.add_argument(
        "-pl",
        "--provider-link",
        type=str,
        nargs="+",
        help="Specify one or more provider episode urls.",
    )


def _add_action_arguments(parser: argparse.ArgumentParser) -> None:
    """Add action-related command-line arguments to the parser."""
    action_opts = parser.add_argument_group("Action Options")
    action_opts.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=config.DEFAULT_DOWNLOAD_PATH,
        help="Set the download directory (e.g., /path/to/downloads).",
    )
    action_opts.add_argument(
        "-L",
        "--language",
        type=CaseInsensitiveChoices(
            ["German Dub", "English Sub", "German Sub", "English Dub"]
        ),
        default=config.DEFAULT_LANGUAGE,
        help="Specify the language for download.",
    )
    action_opts.add_argument(
        "-p",
        "--provider",
        type=CaseInsensitiveChoices(config.SUPPORTED_PROVIDERS),
        help="Specify the preferred provider.",
    )


def _add_web_ui_arguments(parser: argparse.ArgumentParser) -> None:
    """Add Web UI related command-line arguments to the parser."""
    web_opts = parser.add_argument_group("Web UI Options")
    web_opts.add_argument(
        "-w",
        "--web-ui",
        action="store_true",
        help="Start Flask web interface instead of CLI.",
    )
    web_opts.add_argument(
        "-wP",
        "--web-port",
        type=int,
        default=5000,
        help="Specify the port for the Flask web interface (default: 5000).",
    )
    web_opts.add_argument(
        "-wA",
        "--enable-web-auth",
        action="store_true",
        help="Enable authentication for web interface with user management.",
    )
    web_opts.add_argument(
        "-wN",
        "--no-browser",
        action="store_true",
        help="Disable automatic browser opening when starting web interface.",
    )
    web_opts.add_argument(
        "-wE",
        "--web-expose",
        action="store_true",
        help="Bind web interface to 0.0.0.0 instead of localhost for external access.",
    )
    web_opts.add_argument(
        "--live",
        action="store_true",
        help="Enable live reload (auto browser refresh) when running the web UI. Requires 'livereload' package and is only active when specified.",
    )


def _add_miscellaneous_arguments(parser: argparse.ArgumentParser) -> None:
    """Add miscellaneous command-line arguments to the parser."""
    misc_opts = parser.add_argument_group("Miscellaneous Options")
    misc_opts.add_argument(
        "-s",
        "--slug",
        type=str,
        help="Specify a search slug (e.g., demon-slayer-kimetsu-no-yaiba).",
    )
    misc_opts.add_argument(
        "-K",
        "--keep-watching",
        action="store_true",
        help="Automatically continue to the next episodes after the selected one.",
    )
    misc_opts.add_argument(
        "-r",
        "--random-anime",
        type=str,
        nargs="*",
        help='Play a random anime (default genre is "all", e.g., Drama).\n'
        f'All genres can be found here: "{config.ANIWORLD_TO}/random"',
    )
    misc_opts.add_argument(
        "-D",
        "--only-direct-link",
        action="store_true",
        help="Output only the direct streaming link.",
    )
    misc_opts.add_argument(
        "-C",
        "--only-command",
        action="store_true",
        help="Output only the execution command.",
    )


def _handle_version() -> None:
    """Handle version information display."""
    print(f"AniWorld-Downloader v.{config.VERSION}")
    if not config.IS_NEWEST_VERSION:
        print(
            f"Your version is outdated. "
            f"Please update to the latest version (v.{config.LATEST_VERSION})."
        )
    else:
        print("You are on the latest version.")
    sys.exit(0)


def _handle_provider_links(args: argparse.Namespace) -> None:
    """Handle provider link processing."""
    if not args.provider_link:
        return

    invalid_links = [link for link in args.provider_link if not link.startswith("http")]
    if invalid_links:
        logging.error("Invalid provider episode URLs: %s", ", ".join(invalid_links))
        sys.exit(1)

    hanime_links = [
        link
        for link in args.provider_link
        if link.startswith("https://hanime.tv/videos/")
    ]

    if hanime_links:
        for link in hanime_links:
            try:
                direct_link = get_direct_link_from_hanime(link)
                if direct_link:
                    print(f"-> {link}")
                    print(f'"{direct_link}"')
                    print("-" * 40)
                else:
                    logging.error(
                        "Could not extract direct link from hanime URL: %s", link
                    )
            except Exception as err:
                logging.error("Error processing hanime link '%s': %s", link, err)

        args.provider_link = [
            link
            for link in args.provider_link
            if not link.startswith("https://hanime.tv/videos/")
        ]

    if not args.provider_link:
        sys.exit(0)

    if not args.provider:
        logging.error("Provider must be specified when using provider links.")
        sys.exit(1)

    if args.provider in config.SUPPORTED_PROVIDERS:
        try:
            module = importlib.import_module(".extractors", __package__)
            func = getattr(module, f"get_direct_link_from_{args.provider.lower()}")

            for provider_episode in args.provider_link:
                direct_link = func(provider_episode)
                print(f"-> {provider_episode}")
                print(f'"{direct_link}"')
                print("-" * 40)
        except KeyboardInterrupt:
            pass
        except Exception as err:
            logging.error("Error processing provider links: %s", err)
            sys.exit(1)

    sys.exit(0)


def _handle_hanime_episodes(args: argparse.Namespace) -> None:
    """Handle hanime.tv URLs in episode arguments by moving them to provider links."""
    if not args.episode:
        return

    hanime_episodes = [
        ep for ep in args.episode if ep.startswith("https://hanime.tv/videos/")
    ]

    if not hanime_episodes:
        return

    args.episode = [
        ep for ep in args.episode if not ep.startswith("https://hanime.tv/videos/")
    ]

    if not args.provider_link:
        args.provider_link = []
    args.provider_link.extend(hanime_episodes)


def _handle_debug_mode() -> None:
    """Handle debug mode setup."""
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug("=============================================")
    logging.debug("   Welcome to AniWorld Downloader v.%s!   ", config.VERSION)
    logging.debug("=============================================\n")


def _setup_default_provider(args: argparse.Namespace) -> None:
    """Set up default provider if none specified."""
    if args.provider is None:
        config.USES_DEFAULT_PROVIDER = True
        args.provider = config.DEFAULT_PROVIDER
    args.action = "Download"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the AniWorld-Downloader."""
    parser = argparse.ArgumentParser(
        description="AniWorld Downloader - download anime, series and movies "
        "from aniworld.to, s.to and movie4k.sx via web interface or CLI."
    )

    _add_general_arguments(parser)
    _add_episode_arguments(parser)
    _add_action_arguments(parser)
    _add_web_ui_arguments(parser)
    _add_miscellaneous_arguments(parser)

    args = parser.parse_args()

    if args.version:
        _handle_version()

    _handle_hanime_episodes(args)
    _handle_provider_links(args)

    if args.random_anime is not None:
        genre = args.random_anime[0] if args.random_anime else "all"
        args.slug = get_random_anime_slug(genre)

    _setup_default_provider(args)

    if args.debug:
        _handle_debug_mode()

    return args


arguments = parse_arguments()

if __name__ == "__main__":
    pass
