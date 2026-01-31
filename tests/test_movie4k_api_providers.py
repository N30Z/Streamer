from aniworld.models import Episode


def test_movie4k_providers_monkeypatch(monkeypatch):
    """Ensure Episode._get_providers_from_html uses Movie API streams for movie links."""
    movie_url = "https://movie4k.sx/watch/outlander/6195193258607cdfb9fa2e98"

    class DummyMovie:
        def __init__(self, url=None):
            self.url = url
            # Two streams with different providers and language names
            self.streams = [
                {"stream": "https://streamtape.com/e/abcd", "lang": "Deutsch"},
                {"stream": "https://filemoon.sx/f/1234", "lang": "English"},
            ]
            self.available_languages = ["Deutsch", "English"]

    # Monkeypatch the Movie class inside the movie4k module import location used by models
    import aniworld.sites.movie4k as mv4k_mod

    monkeypatch.setattr(mv4k_mod, "Movie", DummyMovie)

    ep = Episode(link=movie_url)

    providers = ep._get_providers_from_html()

    # Expect provider keys to be mapped to supported provider names
    assert "Streamtape" in providers or "Streamtape" in providers
    assert "Filemoon" in providers

    # Language keys should map to site codes (SITE_LANGUAGE_CODES mapping is used internally)
    # Ensure that for one provider we have at least one language mapping
    assert any(isinstance(k, int) for k in providers.get("Streamtape", {}).keys())
    assert any(isinstance(k, int) for k in providers.get("Filemoon", {}).keys())
