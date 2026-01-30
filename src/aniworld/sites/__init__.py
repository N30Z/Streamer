"""
Site-specific modules for streaming site search and data fetching.

Each module encapsulates the logic for a specific streaming site:
- aniworld: AniWorld.to (anime streaming)
- s_to: S.to (series streaming)
- movie4k: Movie4k.sx (movie streaming)
"""

from .aniworld import (
    search_anime,
    fetch_anime_list,
    fetch_popular_and_new_anime,
    extract_anime_from_carousel,
)
from .s_to import fetch_sto_search_results
from .movie4k import Movie, MovieAnime, is_movie4k_url

__all__ = [
    "search_anime",
    "fetch_anime_list",
    "fetch_popular_and_new_anime",
    "extract_anime_from_carousel",
    "fetch_sto_search_results",
    "Movie",
    "MovieAnime",
    "is_movie4k_url",
]
