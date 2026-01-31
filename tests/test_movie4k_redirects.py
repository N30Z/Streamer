import requests
from types import SimpleNamespace

import aniworld.sites.movie4k as mv4k_mod
import aniworld.extractors as extracts_mod


def test_movie4k_resolves_redirect_and_passes_referer(monkeypatch):
    movie_url = "https://movie4k.sx/watch/test/619"

    movie = mv4k_mod.Movie(url=movie_url)
    movie_embed = "https://redir.example/abc"
    movie.embeded_link = movie_embed

    # Simulate HEAD redirect to a VOE provider URL
    def fake_head(url, headers=None, timeout=None, allow_redirects=None):
        class Resp:
            status_code = 302
            headers = {"Location": "https://voe.sx/j8vfrcq55wrg"}
        return Resp()

    monkeypatch.setattr(requests, "head", fake_head)

    called = {"embed": None, "referer": None}

    def fake_voe(embeded_voe_link=None, referer=None):
        called["embed"] = embeded_voe_link
        called["referer"] = referer
        return "https://cdn.example/test.mp4"

    monkeypatch.setattr(extracts_mod, "get_direct_link_from_voe", fake_voe)

    direct = movie.get_direct_link()

    assert direct == "https://cdn.example/test.mp4"
    assert called["embed"] == "https://voe.sx/j8vfrcq55wrg"
    assert called["referer"] == movie.link
    assert movie._selected_provider == "VOE"
    assert movie.embeded_link == "https://voe.sx/j8vfrcq55wrg"


def test_movie4k_provider_direct_link_passes_referer(monkeypatch):
    movie_url = "https://movie4k.sx/watch/test/619"

    movie = mv4k_mod.Movie(url=movie_url)
    # Direct VOE provider link already present
    movie.embeded_link = "https://voe.sx/j8vfrcq55wrg"
    movie._selected_provider = "VOE"

    called = {"embed": None, "referer": None}

    def fake_voe(embeded_voe_link=None, referer=None):
        called["embed"] = embeded_voe_link
        called["referer"] = referer
        return "https://cdn.example/direct.mp4"

    monkeypatch.setattr(extracts_mod, "get_direct_link_from_voe", fake_voe)

    direct = movie.get_direct_link()

    assert direct == "https://cdn.example/direct.mp4"
    assert called["embed"] == "https://voe.sx/j8vfrcq55wrg"
    assert called["referer"] == movie.link
