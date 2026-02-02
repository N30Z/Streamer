"""Test the _parse_episode_titles function directly"""
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict

def _parse_episode_titles(soup: BeautifulSoup, season: int) -> Dict[int, str]:
    """Copy of the fixed function"""
    titles: Dict[int, str] = {}
    pattern = re.compile(rf"staffel-{season}/episode-(\d+)")

    # Find episode titles in <td class="seasonEpisodeTitle">
    for td in soup.select('td.seasonEpisodeTitle'):
        link = td.find('a', href=True)
        if not link:
            continue

        href = str(link.get('href', ''))
        match = pattern.search(href)
        if not match:
            continue

        ep_num = int(match.group(1))
        if ep_num in titles:
            continue

        # Extract titles from <strong> (German) and <span> (English)
        strong = link.find('strong')
        span = link.find('span')

        g_text = strong.get_text(strip=True) if strong else ""
        e_text = span.get_text(strip=True) if span else ""

        # Build title string
        if g_text and e_text:
            title = f"{g_text} / {e_text}"
        elif g_text:
            title = g_text
        elif e_text:
            title = e_text
        else:
            # Fallback to title attribute or link text
            title_attr = link.get('title')
            title = str(title_attr).strip() if title_attr else link.get_text(strip=True)

        if title:
            titles[ep_num] = title

    return titles

def test():
    """Test with real aniworld.to page"""
    slug = "sentenced-to-be-a-hero"
    season = 1
    url = f"https://aniworld.to/anime/stream/{slug}/staffel-{season}"

    print(f"Testing: {url}\n")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        titles = _parse_episode_titles(soup, season)

        print(f"Found {len(titles)} episode titles:\n")

        for ep_num, title in sorted(titles.items())[:10]:
            print(f"  Episode {ep_num}: {title}")

        if len(titles) > 10:
            print(f"\n  ... and {len(titles) - 10} more episodes")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
