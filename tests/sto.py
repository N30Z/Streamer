import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def get_season_episode_count(slug: str, link: str = ANIWORLD_TO) -> Dict[int, int]:
    """
    Get episode count for each season of an anime with caching.

    Args:
        slug: Anime slug from URL
        link: Base Url

    Returns:
        Dictionary mapping season numbers to episode counts
    """
    # Check cache first
    cache_key = f"seasons_{slug}"
    if cache_key in _ANIME_DATA_CACHE:
        return _ANIME_DATA_CACHE[cache_key]

    try:
        if S_TO not in link:
            base_url = f"{ANIWORLD_TO}/anime/stream/{slug}/"
        else:
            base_url = f"{S_TO}/serie/{slug}/"
        response = _make_request(base_url)
        soup = BeautifulSoup(response.content, "html.parser")

        season_meta = soup.find("meta", itemprop="numberOfSeasons")
        number_of_seasons = int(season_meta["content"]) if season_meta else 0

        episode_counts = {}
        for season in range(1, number_of_seasons + 1):
            season_url = f"{base_url}staffel-{season}"
            try:
                season_response = _make_request(season_url)
                season_soup = BeautifulSoup(season_response.content, "html.parser")
                episode_counts[season] = _parse_season_episodes(season_soup, season)
            except Exception as err:
                logging.warning("Failed to get episodes for season %d: %s", season, err)
                episode_counts[season] = 0

        # Cache the result
        print (episode_counts)


test("Dexter")
