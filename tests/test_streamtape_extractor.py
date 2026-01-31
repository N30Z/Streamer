from aniworld.extractors.provider import streamtape as st
from types import SimpleNamespace


def test_streamtape_extract_source_tag():
    html = '<video><source src="https://cdn.example.com/videos/abcd1234.mp4" type="video/mp4"></video>'
    url = st._extract_direct_from_html(html, 'https://streamtape.com/e/abc')
    assert url == 'https://cdn.example.com/videos/abcd1234.mp4'


def test_streamtape_extract_file_key():
    html = 'var conf = {file: "https://cdn.example.com/videos/vid.mkv"};'
    url = st._extract_direct_from_html(html, 'https://streamtape.com/e/abc')
    assert url == 'https://cdn.example.com/videos/vid.mkv'


def test_streamtape_removed_raises():
    html = '<div>Video not found!</div>'
    try:
        st._extract_direct_from_html(html, 'https://streamtape.com/e/abc')
    except ValueError as e:
        assert 'not found' in str(e).lower()
    else:
        assert False, 'Expected ValueError for removed video'


def test_get_direct_link_from_streamtape_monkeypatch(monkeypatch):
    # Simulate a two-stage fetch: first page with script pointing to file, second stage not used
    called = {'n': 0}

    def fake_make_request(url):
        called['n'] += 1
        if called['n'] == 1:
            return SimpleNamespace(text='var config={file: "https://cdn.example.com/m.mp4"}')
        return SimpleNamespace(text='')

    monkeypatch.setattr(st, '_make_request', fake_make_request)
    direct = st.get_direct_link_from_streamtape('https://streamtape.com/e/fake')
    assert direct == 'https://cdn.example.com/m.mp4'
