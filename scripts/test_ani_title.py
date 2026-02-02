import requests
from bs4 import BeautifulSoup

def test_episode_title_selectors(url: str):
    html = requests.get(url, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")

    tests = {
        "all episode links":
            lambda: soup.select('a[href*="/staffel-"][href*="/episode-"]'),

        "strong (title_ger) global":
            lambda: soup.find_all("strong"),

        "span (title_eng) global":
            lambda: soup.find_all("span"),

        "strong inside episode <a>":
            lambda: soup.select(
                'a[href*="/staffel-"][href*="/episode-"] strong'
            ),

        "span inside episode <a>":
            lambda: soup.select(
                'a[href*="/staffel-"][href*="/episode-"] span'
            ),
    }

    print(f"\nTesting URL: {url}\n" + "-" * 60)

    for name, fn in tests.items():
        try:
            result = fn()

            if isinstance(result, list):
                print(f"{name}: {len(result)} Treffer")
                for el in result[:5]:
                    print("  →", el.get_text(strip=True))
            else:
                print(f"{name}: {result}")
        except Exception as e:
            print(f"{name}: FEHLER → {e}")

if __name__ == "__main__":
    test_episode_title_selectors("https://aniworld.to/anime/stream/sentenced-to-be-a-hero/staffel-1")
