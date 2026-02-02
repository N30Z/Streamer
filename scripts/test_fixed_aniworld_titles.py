"""Test the fixed episode title extraction for aniworld.to"""
import sys
sys.path.insert(0, 'src')

from aniworld.sites.aniworld import get_episode_titles

def test_titles():
    """Test episode title extraction for aniworld.to"""

    # Test with the anime from the user's example
    slug = "sentenced-to-be-a-hero"

    print(f"Testing episode titles for: {slug}")
    print("=" * 60)

    try:
        titles = get_episode_titles(slug)

        if not titles:
            print("❌ No titles found!")
            return

        print(f"✓ Found titles for {len(titles)} season(s)\n")

        for season_num, episode_titles in sorted(titles.items()):
            print(f"Season {season_num}: {len(episode_titles)} episodes")

            # Show first 5 episodes
            for ep_num in sorted(list(episode_titles.keys())[:5]):
                title = episode_titles[ep_num]
                print(f"  Episode {ep_num}: {title}")

            if len(episode_titles) > 5:
                print(f"  ... and {len(episode_titles) - 5} more episodes")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_titles()
