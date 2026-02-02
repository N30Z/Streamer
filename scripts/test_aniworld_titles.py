import requests
from bs4 import BeautifulSoup
import re

def test_aniworld_episode_titles(slug: str = "one-piece"):
    """Test episode title extraction from aniworld.to"""
    base_url = f"https://aniworld.to/anime/stream/{slug}/"

    try:
        # Get main page first to find number of seasons
        response = requests.get(base_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        season_meta = soup.find("meta", itemprop="numberOfSeasons")
        number_of_seasons = int(season_meta["content"]) if season_meta else 1

        print(f"Found {number_of_seasons} season(s)")

        # Test season 1
        season = 1
        season_url = f"{base_url}staffel-{season}"
        print(f"\nTesting {season_url}")

        season_response = requests.get(season_url, timeout=15)
        season_response.raise_for_status()
        season_soup = BeautifulSoup(season_response.content, "html.parser")

        # Test different selectors
        print("\n=== Testing Selectors ===")

        # Current selector
        links1 = season_soup.select(f'a[href*="staffel-{season}/episode-"]')
        print(f"1. a[href*=\"staffel-{season}/episode-\"]: {len(links1)} matches")

        # Alternative selectors
        links2 = season_soup.find_all("a", href=re.compile(rf"staffel-{season}/episode-\d+"))
        print(f"2. find_all with regex: {len(links2)} matches")

        links3 = season_soup.select('a[href*="/episode-"]')
        print(f"3. a[href*=\"/episode-\"]: {len(links3)} matches")

        # Show first few links
        if links1:
            print(f"\nFirst 3 links found by current selector:")
            for i, link in enumerate(links1[:3], 1):
                href = link.get("href", "")
                print(f"  {i}. href: {href}")

                # Check for title elements
                strong = link.select_one("strong")
                span = link.select_one("span")
                title_attr = link.get("title")

                print(f"     <strong>: {strong.get_text(strip=True) if strong else 'NONE'}")
                print(f"     <span>: {span.get_text(strip=True) if span else 'NONE'}")
                print(f"     title attr: {title_attr or 'NONE'}")
                print()

        # Check HTML structure around episode links
        print("\n=== HTML Structure Sample ===")
        episode_container = season_soup.find("div", class_="hosterSiteVideo")
        if episode_container:
            print("Found div.hosterSiteVideo")
            sample_links = episode_container.find_all("a", href=True, limit=2)
            for link in sample_links:
                print(f"\nLink HTML:\n{link.prettify()[:500]}")
        else:
            print("No div.hosterSiteVideo found")

            # Try to find any episode link
            sample_link = season_soup.find("a", href=re.compile(r"/episode-\d+"))
            if sample_link:
                print(f"\nSample episode link:\n{sample_link.prettify()[:500]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_aniworld_episode_titles()
