"""
Search module - re-exports from site-specific modules.

All site-specific search logic has been moved to the sites/ package:
- sites/aniworld.py: AniWorld.to search and homepage parsing
- sites/s_to.py: S.to search
- sites/movie4k.py: Movie4k.sx support

This module re-exports all public functions for backward compatibility.
"""

from .sites.aniworld import (
    search_anime,
    fetch_anime_list,
    fetch_popular_and_new_anime,
    extract_anime_from_carousel,
    show_menu,
)
from .sites.s_to import fetch_sto_search_results, fetch_popular_and_new_sto
from .sites.movie4k import fetch_movie4k_search_results, fetch_popular_and_new_movie4k

__all__ = [
    "search_anime",
    "fetch_anime_list",
    "fetch_popular_and_new_anime",
    "extract_anime_from_carousel",
    "show_menu",
    "fetch_sto_search_results",
    "fetch_popular_and_new_sto",
    "fetch_movie4k_search_results",
    "fetch_popular_and_new_movie4k",
]

if __name__ == "__main__":
    print(search_anime())
