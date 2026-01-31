"""
Simple debug script for `src/aniworld/sites/movie4k.py`.

Usage:
  python scripts/debug_movie4k.py

What it does:
- Loads the sample HTML from `tests/movie4k_test.html`.
- Mocks `requests.get` to return that HTML for any URL.
- Calls `_scrape_browse_results` to verify HTML parsing.
- Tests `_title_to_slug`, `_parse_api_results`, and `_extract_provider_from_url`.

Keep this short and tweak as needed while debugging.
"""
from pathlib import Path
import sys
import json

# Ensure package imports work when running script from repo root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Importing the package can trigger CLI parsers at import time.
# Defer importing `movie4k` until after we parse CLI args.
movie4k = None

SAMPLE_HTML_PATH = ROOT / "tests" / "movie4k_test.html"


def _ensure_movie4k_imported():
    """Import the movie4k module lazily and prevent other modules from reading CLI args."""
    global movie4k
    if movie4k is None:
        saved_argv = sys.argv[:]
        try:
            # Prevent imported modules from reading CLI args
            sys.argv[:] = [sys.argv[0]]
            import importlib
            movie4k = importlib.import_module("aniworld.sites.movie4k")
        finally:
            sys.argv[:] = saved_argv


class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        # Not used for the scrape fallback test
        raise NotImplementedError


def mock_requests_get(*args, **kwargs):
    # Return the sample HTML regardless of URL
    html = SAMPLE_HTML_PATH.read_text(encoding="utf-8")
    return MockResponse(html)


def test_slug():
    _ensure_movie4k_imported()
    print("\n== _title_to_slug tests ==")
    examples = ["Greenland *ENGLISH*", "A Movie: The Sequel!", "  Spaces  Everywhere "]
    for t in examples:
        print(f"{t!r} -> {movie4k._title_to_slug(t)}")


def test_provider_extraction():
    _ensure_movie4k_imported()
    print("\n== _extract_provider_from_url tests ==")
    urls = [
        "https://streamtape.com/e/abcd",
        "https://filemoon.sx/f/1234",
        "https://doodstream.com/d/abcd",
        "https://unknown.example.com/v/1",
    ]
    for u in urls:
        print(f"{u} -> {movie4k._extract_provider_from_url(u)}")


def test_parse_api_results():
    _ensure_movie4k_imported()
    print("\n== _parse_api_results tests ==")
    sample_list = [
        {"_id": "abc123", "title": "Test Movie", "poster_path": "/path.jpg", "storyline": "A story", "year": 2020}
    ]
    print("list input ->", movie4k._parse_api_results(sample_list))

    sample_dict = {
        "movies": sample_list
    }
    print("dict input (movies wrapper) ->", movie4k._parse_api_results(sample_dict))


def test_scrape_fallback():
    _ensure_movie4k_imported()
    print("\n== _scrape_browse_results (HTML fallback) ==")
    # Monkeypatch requests.get inside module
    import requests
    orig_get = requests.get
    try:
        requests.get = mock_requests_get
        results = movie4k._scrape_browse_results("outlander")
        print(f"Found {len(results)} results")
        for r in results[:5]:
            print(json.dumps(r, ensure_ascii=False, indent=2))
    finally:
        requests.get = orig_get


def test_is_url_and_movieobj():
    _ensure_movie4k_imported()
    print("\n== URL checks and Movie parsing ==")
    url = "https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98"
    print(f"is_movie4k_url('{url}') ->", movie4k.is_movie4k_url(url))
    m = movie4k.Movie(url=url)
    print("Parsed movie_id, slug ->", m.movie_id, m.slug)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Debug movie4k module")
    parser.add_argument("--live-search", "-s", help="Perform a live search against movie4k.sx using the provided keyword")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Number of results to print for live search")
    parser.add_argument("--test-api", action="store_true", help="Spin up the app and call /api/search to validate processed results")
    args = parser.parse_args()

    if args.live_search:
        # Warning: this will perform real network requests to movie4k.sx
        print(f"Performing live search for keyword: '{args.live_search}'")
        _ensure_movie4k_imported()
        try:
            results = movie4k.fetch_movie4k_search_results(args.live_search)
            print(f"Found {len(results)} results")
            for r in results[: args.limit]:
                print(json.dumps(r, ensure_ascii=False, indent=2))
        except Exception as e:
            print("Live search failed:", e)
        sys.exit(0)

    if args.test_api:
        print("Testing /api/search using Flask test client (movie4k only)")
        # Prevent other modules from parsing our CLI args during import
        saved_argv = sys.argv[:]
        try:
            sys.argv[:] = [sys.argv[0]]
            from aniworld.web.app import WebApp
            webapp = WebApp(host='127.0.0.1', port=0, debug=False, arguments=None)
        finally:
            sys.argv[:] = saved_argv

        client = webapp.app.test_client()
        resp = client.post('/api/search', json={'query':'outlander', 'sites':['movie4k.sx']})
        print('Status code:', resp.status_code)
        try:
            data = resp.get_json()
            print('Response:', json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            print('Failed to parse JSON response:', e)

        # Also test the episodes endpoint for a movie URL
        movie_url = 'https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98'
        resp2 = client.post('/api/episodes', json={'series_url': movie_url})
        print('\nEpisodes endpoint test for movie URL:')
        print('Status code:', resp2.status_code)
        try:
            data2 = resp2.get_json()
            print('Response:', json.dumps(data2, ensure_ascii=False, indent=2))
        except Exception as e:
            print('Failed to parse JSON response:', e)

        # Test that _group_episodes_by_series creates a MovieAnime for movie links
        from aniworld.entry import _group_episodes_by_series
        movie_test = _group_episodes_by_series([movie_url])
        print('\n_group_episodes_by_series result types:')
        print([type(x).__name__ for x in movie_test])

        # New test: ensure Episode.get_direct_link delegates to Movie for movie links
        from aniworld.models import Episode
        print('\nTesting Episode -> Movie delegation for get_direct_link:')
        ep = Episode(link=movie_url)
        # Monkeypatch Movie.get_direct_link to ensure delegation
        import aniworld.sites.movie4k as mv4k_mod
        orig_get_direct = mv4k_mod.Movie.get_direct_link
        try:
            mv4k_mod.Movie.get_direct_link = lambda self: 'http://direct.movie.example/stream'
            direct = ep.get_direct_link()
            print('Delegated direct link:', direct)
        finally:
            mv4k_mod.Movie.get_direct_link = orig_get_direct

        sys.exit(0)

    print("Debugging movie4k module (local tests)")
    test_slug()
    test_provider_extraction()
    test_parse_api_results()
    test_scrape_fallback()
    test_is_url_and_movieobj()
    print("\nDone.")
