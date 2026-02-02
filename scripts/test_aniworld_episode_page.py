import requests
from bs4 import BeautifulSoup

def test_episode_page_title(url: str = "https://aniworld.to/anime/stream/one-piece/staffel-1/episode-1"):
    """Check if episode titles are available on the episode page itself"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        print(f"Testing: {url}\n")

        # Check <title> tag
        title_tag = soup.find("title")
        print(f"Page <title>: {title_tag.get_text(strip=True) if title_tag else 'NONE'}\n")

        # Check for h1, h2 headers
        h1 = soup.find("h1")
        h2 = soup.find("h2")
        print(f"<h1>: {h1.get_text(strip=True) if h1 else 'NONE'}")
        print(f"<h2>: {h2.get_text(strip=True) if h2 else 'NONE'}\n")

        # Check meta tags
        print("=== Meta Tags ===")
        meta_name = soup.find("meta", attrs={"name": "title"})
        meta_prop = soup.find("meta", attrs={"property": "og:title"})
        meta_itemprop = soup.find("meta", attrs={"itemprop": "name"})

        print(f"meta name='title': {meta_name.get('content') if meta_name else 'NONE'}")
        print(f"meta property='og:title': {meta_prop.get('content') if meta_prop else 'NONE'}")
        print(f"meta itemprop='name': {meta_itemprop.get('content') if meta_itemprop else 'NONE'}\n")

        # Check for episode info
        print("=== Episode Info ===")
        episode_info = soup.find("div", class_="seriesListMeta")
        if episode_info:
            print(f"Found div.seriesListMeta:\n{episode_info.get_text(strip=True)[:200]}\n")

        # Check for any element containing episode title
        print("=== Searching for 'Episode' text ===")
        episode_elements = soup.find_all(text=lambda t: t and "Episode" in t and "Staffel" in t)
        for i, elem in enumerate(episode_elements[:5], 1):
            parent = elem.parent
            print(f"{i}. Tag: {parent.name}, Text: {elem.strip()[:100]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_episode_page_title()
