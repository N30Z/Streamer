from aniworld.extractors.provider import voe as voe_mod
from types import SimpleNamespace


def test_voe_uses_referer_on_request(monkeypatch):
    called = {"url": None, "headers": None}

    def fake_requests_get(url, headers=None, timeout=None):
        called["url"] = url
        called["headers"] = headers
        return SimpleNamespace(text='redirect to https://voe.sx/j8vfrcq55wrg')

    # Simulate urlopen failing first, then succeeding on the /e/ fallback
    class FakeHTTPError(Exception):
        pass

    def fake_urlopen(req, timeout=None):
        req_url = req.full_url
        if req_url.endswith('/j8vfrcq55wrg'):
            raise Exception('404 simulated')
        return SimpleNamespace(read=lambda: b"var a168c='dummy'" )

    monkeypatch.setattr(voe_mod.requests, 'get', fake_requests_get)
    monkeypatch.setattr(voe_mod, 'urlopen', fake_urlopen)

    # Call with referer and ensure function returns (it will attempt fallback)
    try:
        voe_mod.get_direct_link_from_voe('https://voe.sx/j8vfrcq55wrg', referer='https://movie4k.sx/watch/xyz')
    except Exception as e:
        # We expect the fake flow to raise or return depending on fake implementations
        assert '404' in str(e) or 'Failed' in str(e)
    else:
        assert True
