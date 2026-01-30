"""
Movie4k module - re-exports from sites/movie4k.py.

All movie4k.sx logic has been moved to sites/movie4k.py.
This module re-exports for backward compatibility.
"""

from .sites.movie4k import Movie, MovieAnime, is_movie4k_url

__all__ = [
    "Movie",
    "MovieAnime",
    "is_movie4k_url",
]
