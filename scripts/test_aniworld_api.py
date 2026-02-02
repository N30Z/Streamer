import requests
from bs4 import BeautifulSoup
import json
import re

def test_aniworld_api(slug: str = "one-piece"):
    """Check for API endpoints or JSON data with episode titles"""
    base_url = f"https://aniworld.to/anime/stream/{slug}/"

    try:
        # Check main page for JSON data
        print("=== Checking main anime page ===")
        response = requests.get(base_url, timeout=15)
        response.raise_for_status()

        # Search for JSON-LD structured data
        soup = BeautifulSoup(response.content, "html.parser")
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            print("Found JSON-LD:")
            data = json.loads(json_ld.string)
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            print()

        # Search for JavaScript variables with episode data
        print("\n=== Checking for JavaScript episode data ===")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "episode" in script.string.lower():
                content = script.string[:500]
                if "title" in content.lower() or "name" in content.lower():
                    print(f"Found potential episode data:\n{content}\n")
                    break

        # Check season page
        print("\n=== Checking season page ===")
        season_url = f"{base_url}staffel-1"
        season_response = requests.get(season_url, timeout=15)
        season_response.raise_for_status()
        season_soup = BeautifulSoup(season_response.content, "html.parser")

        # Check for JSON data
        season_json_ld = season_soup.find("script", type="application/ld+json")
        if season_json_ld:
            print("Found JSON-LD on season page:")
            season_data = json.loads(season_json_ld.string)
            print(json.dumps(season_data, indent=2, ensure_ascii=False)[:1000])
            print()

        # Search for data attributes
        print("\n=== Checking data attributes ===")
        links_with_data = season_soup.find_all("a", attrs={"data-episode-id": True})
        if links_with_data:
            sample = links_with_data[0]
            print(f"Sample link attributes: {sample.attrs}")

        # Check if there's an AJAX endpoint for episodes
        print("\n=== Testing potential AJAX endpoints ===")

        # Try getting episode data via AJAX
        ajax_urls = [
            f"https://aniworld.to/ajax/episodeList/{slug}/1",
            f"https://aniworld.to/ajax/episodes/{slug}/1",
            f"https://aniworld.to/ajax/season/{slug}/1",
        ]

        for ajax_url in ajax_urls:
            try:
                ajax_response = requests.get(ajax_url, timeout=10)
                if ajax_response.status_code == 200:
                    print(f"\n✓ {ajax_url}")
                    print(f"Response (first 500 chars):\n{ajax_response.text[:500]}")
            except:
                pass

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_aniworld_api()
