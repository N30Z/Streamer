from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aniworld.models import Episode
import aniworld.sites.movie4k as mv4k_mod

class DummyMovie:
    def __init__(self, url=None):
        self.url = url
        self.streams = [
            {"stream": "https://streamtape.com/e/abcd", "lang": "Deutsch"},
            {"stream": "https://filemoon.sx/f/1234", "lang": "English"},
        ]
        self.available_languages = ["Deutsch", "English"]

mv4k_mod.Movie = DummyMovie

movie_url = "https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98"
ep = Episode(link=movie_url)
print('Available languages (from HTML parser):', ep._get_available_languages_from_html())
prov = ep._get_providers_from_html()
print('Providers extracted:', prov)
