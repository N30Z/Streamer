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
    get_season_episode_count as aniworld_get_season_episode_count,
    get_movie_episode_count as aniworld_get_movie_episode_count,
)
from .s_to import (
    fetch_sto_search_results,
    get_season_episode_count as sto_get_season_episode_count,
    get_movie_episode_count as sto_get_movie_episode_count,
)
from .movie4k import Movie, MovieAnime, is_movie4k_url, fetch_movie4k_search_results

__all__ = [
    "search_anime",
    "fetch_anime_list",
    "fetch_popular_and_new_anime",
    "extract_anime_from_carousel",
    "aniworld_get_season_episode_count",
    "aniworld_get_movie_episode_count",
    "fetch_sto_search_results",
    "sto_get_season_episode_count",
    "sto_get_movie_episode_count",
    "Movie",
    "MovieAnime",
    "is_movie4k_url",
    "fetch_movie4k_search_results",
]
