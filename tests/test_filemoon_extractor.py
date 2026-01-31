from aniworld.extractors.provider.filemoon import _extract_iframe_src


def test_extract_iframe_src_from_script():
    source_url = "https://filemoon.sx/d/w5clfextaz08"
    # Simulate HTML where <iframe> is not present but script contains protocol-relative embed URL
    html = """
    <html>
    <head></head>
    <body>
    <script>
    // Some JS which sets iframe src dynamically
    var s = document.createElement('iframe');
    s.src = '//player.filemoon.to/e/abcd1234';
    document.body.appendChild(s);
    </script>
    </body>
    </html>
    """

    iframe_src = _extract_iframe_src(html, source_url)
    assert iframe_src.startswith("https://")
    assert "/e/" in iframe_src or "/d/" in iframe_src


def test_extract_iframe_src_from_fallback_html():
    source_url = "https://filemoon.sx/d/w5clfextaz08"
    html = '<div>Watch at https://filemoon.to/e/abcd5678 embedded here</div>'
    iframe_src = _extract_iframe_src(html, source_url)
    assert iframe_src.startswith("https://filemoon.to/e/")


def test_get_direct_link_from_filemoon_monkeypatch(monkeypatch):
    import types
    from aniworld.extractors.provider import filemoon as fm

    # Simulate download page without iframe but script that sets iframe src
    download_page = types.SimpleNamespace(text="""
        <html><body>
        <script>var a = document.createElement('iframe'); a.src='//player.filemoon.to/e/abcd1234';</script>
        </body></html>
    """)

    # Simulate iframe content with JS containing file: "<direct_url>"
    iframe_page = types.SimpleNamespace(text="""
        // Some packed JS
        var video = {file: "https://cdn.filemoon.to/videos/abcd1234.mp4"};
    """)

    calls = {"n": 0}

    def fake_make_request(url, headers=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return download_page
        return iframe_page

    monkeypatch.setattr(fm, "_make_request", fake_make_request)

    direct = fm.get_direct_link_from_filemoon("https://filemoon.to/e/eawuwyrd40an")
    assert direct == "https://cdn.filemoon.to/videos/abcd1234.mp4"
