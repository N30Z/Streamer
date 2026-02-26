import requests

BASE_URL = "https://movie4k.sx"
TMDB_IMG = "https://image.tmdb.org/t/p/w92"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://movie4k.sx/browse?c=movie&m=filter&order_by=Neu&lang=&type=movies&genre=&country=&cast=&year=&networks=&rating=&votes=&yrf=&yrt=&keyword=&view=",
    "Origin": "https://movie4k.sx",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def make_session() -> requests.Session:
    """Create a session pre-warmed with cookies from the browse page."""
    session = requests.Session()
    session.headers.update(HEADERS)
    warm_url = (
        "https://movie4k.sx/browse?c=movie&m=filter&order_by=Neu"
        "&lang=&type=movies&genre=&country=&cast=&year="
        "&networks=&rating=&votes=&yrf=&yrt=&keyword=&view="
    )
    print(f"[SESSION] Warming up — GET {warm_url}")
    resp = session.get(warm_url, timeout=30)
    print(f"[SESSION] Status: {resp.status_code}  Cookies: {dict(session.cookies)}")
    return session


def fetch_movie4k_browse(order_by: str, page: int = 1, limit: int = 20, session: requests.Session | None = None) -> list[dict]:
    """Fetch movies from movie4k.sx /data/browse/ JSON API.

    Args:
        order_by: 'Trending' for popular, 'Neu' for new
        page:     Page number (1-based)
        limit:    Results per page

    Returns:
        List of dicts with keys: _id, title, year, rating, genres, poster, backdrop, url
    """
    # Match exact parameter order observed in browser DevTools
    api_url = (
        f"{BASE_URL}/data/browse/"
        f"?lang=2&keyword=&year=&networks=&rating=&votes="
        f"&genre=&country=&cast=&directors="
        f"&type=movies&order_by={order_by}&page={page}&limit={limit}"
    )
    print(f"[DEBUG] GET {api_url}")

    requester = session or requests
    response = requester.get(api_url, timeout=30)
    print(f"[DEBUG] Status: {response.status_code}  Cookies: {dict(response.cookies)}")
    print(f"[DEBUG] Content-Type: {response.headers.get('Content-Type', 'n/a')}")
    print(f"[DEBUG] Content-Length header: {response.headers.get('Content-Length', 'n/a')}")
    print(f"[DEBUG] Actual body length: {len(response.content)} bytes")
    print(f"[DEBUG] Body (first 500): {response.text[:500]!r}")
    response.raise_for_status()

    if not response.content:
        print("[DEBUG] ERROR: Empty body — server is blocking the request")
        return []

    data = response.json()
    print(f"[DEBUG] Raw JSON keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")
    print(f"[DEBUG] Raw JSON (first 500 chars): {str(data)[:500]}")

    pager = data.get("pager", {})
    print(
        f"[DEBUG] Page {pager.get('currentPage')}/{pager.get('totalPages')} "
        f"— totalItems: {pager.get('totalItems')}"
    )

    raw_movies = data.get("movies", [])
    print(f"[DEBUG] Movies in response: {len(raw_movies)}")

    movies = []
    for m in raw_movies:
        # genres can be a list (sometimes with cast mixed in) or a plain string
        genres_raw = m.get("genres", "")
        if isinstance(genres_raw, list):
            genres = ", ".join(g for g in genres_raw if g and not g.startswith(" "))
        else:
            genres = genres_raw

        poster_path = m.get("poster_path", "")
        backdrop_path = m.get("backdrop_path", "")
        movie_id = m.get("_id", "")

        movies.append({
            "_id": movie_id,
            "title": m.get("title", ""),
            "year": m.get("year", ""),
            "rating": m.get("rating", ""),
            "genres": genres,
            "poster": TMDB_IMG + poster_path if poster_path else "",
            "backdrop": TMDB_IMG + backdrop_path if backdrop_path else "",
            "url": f"{BASE_URL}/watch/{movie_id}" if movie_id else "",
        })

    return movies


if __name__ == "__main__":
    sess = make_session()

    # Probe which order_by values the API accepts
    for probe in ("Trending", "Neu", "Popular", "trending", "neu"):
        url = (
            f"{BASE_URL}/data/browse/"
            f"?lang=2&keyword=&year=&networks=&rating=&votes="
            f"&genre=&country=&cast=&directors="
            f"&type=movies&order_by={probe}&page=1&limit=1"
        )
        try:
            r = sess.get(url, timeout=10)
            data = r.json() if r.ok else {}
            count = len(data.get("movies", []))
            print(f"[PROBE] order_by={probe!r:12s} -> HTTP {r.status_code}, movies={count}")
        except requests.exceptions.Timeout:
            print(f"[PROBE] order_by={probe!r:12s} -> TIMEOUT")
        except Exception as e:
            print(f"[PROBE] order_by={probe!r:12s} -> ERROR: {e}")

    print()
    print("=== TRENDING (Popular) ===")
    popular = fetch_movie4k_browse("Trending", session=sess)
    for m in popular:
        print(f"  [{m['year']}] {m['title']} | {m['genres']} | rating: {m['rating']}")
        print(f"         url:     {m['url']}")
        print(f"         poster:  {m['poster']}")

    print(f"\nTotal: {len(popular)}\n")

    print("=== NEU (New) ===")
    new = fetch_movie4k_browse("Neu", session=sess)
    for m in new:
        print(f"  [{m['year']}] {m['title']} | {m['genres']} | rating: {m['rating']}")
        print(f"         url:     {m['url']}")
        print(f"         poster:  {m['poster']}")

    print(f"\nTotal: {len(new)}")
