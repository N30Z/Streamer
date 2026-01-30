import requests
from bs4 import BeautifulSoup

S_TO = "https://s.to"

def debug_series(slug: str):
    url = f"{S_TO}/serie/{slug}/"
    r = requests.get(url, timeout=15)
    print("STATUS:", r.status_code)
    print("FINAL URL:", r.url)

    soup = BeautifulSoup(r.text, "html.parser")

    # --- META TAG ---
    meta = soup.find("meta", itemprop="numberOfSeasons")
    print("META numberOfSeasons:", meta)

    if meta:
        print("META content:", meta.get("content"))

    # --- PRINT SEASON NAV AREA ---
    print("\n---- FIRST 2000 CHARS OF HTML ----")
    print(r.text[:2000])

    # --- TRY TO FIND SEASON LINKS ---
    print("\n---- POSSIBLE SEASON LINKS ----")
    for a in soup.find_all("a", href=True):
        if "staffel" in a["href"]:
            print(a["href"], a.text.strip())


def debug_season(slug: str, season: int):
    url = f"{S_TO}/serie/{slug}/staffel-{season}"
    r = requests.get(url, timeout=15)
    print("STATUS:", r.status_code)
    print("FINAL URL:", r.url)

    soup = BeautifulSoup(r.text, "html.parser")

    print("\n---- FIRST 2000 CHARS OF HTML ----")
    print(r.text[:2000])

    print("\n---- POSSIBLE EPISODE LINKS ----")
    for a in soup.find_all("a", href=True):
        if "episode" in a["href"] or "folge" in a["href"]:
            print(a["href"], a.text.strip())


# Example usage
debug_series("breaking-bad")
debug_season("breaking-bad", 1)
