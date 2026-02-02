import requests
from bs4 import BeautifulSoup

def test_episode_title_selectors(url: str):
    html = requests.get(url, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")

    tests = {
        "soup.find(strong, class_)":
            lambda: soup.find("strong", class_="episode-title-ger"),

        "soup.select_one(.episode-title-ger)":
            lambda: soup.select_one("strong.episode-title-ger"),

        "soup.select(.episode-title-ger)":
            lambda: soup.select("strong.episode-title-ger"),
        "soup.select(.episode-title-eng)":
            lambda: soup.select("span.episode-title-eng"),

        "any episode-title-ger in text":
            lambda: "episode-title-ger" in soup.text,
    }

    print(f"\nTesting URL: {url}\n" + "-" * 50)

    for name, fn in tests.items():
        try:
            result = fn()
            if isinstance(result, list):
                print(f"{name}: {len(result)} Treffer")
                for el in result:
                    print("  →", el.get_text(strip=True))
            elif result:
                print(f"{name}: GEFUNDEN → {result.get_text(strip=True)}")
            else:
                print(f"{name}: NICHTS")
        except Exception as e:
            print(f"{name}: FEHLER → {e}")

if __name__ == "__main__":
    test_episode_title_selectors("https://s.to/serie/fallout/staffel-1")
