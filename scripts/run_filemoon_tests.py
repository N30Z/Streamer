import sys
sys.path.insert(0, 'src')
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location(
    'test_filemoon_extractor',
    str(pathlib.Path(__file__).resolve().parents[1] / 'tests' / 'test_filemoon_extractor.py'),
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

test_extract_iframe_src_from_script = module.test_extract_iframe_src_from_script
test_extract_iframe_src_from_fallback_html = module.test_extract_iframe_src_from_fallback_html
test_get_direct_link_from_filemoon_monkeypatch = module.test_get_direct_link_from_filemoon_monkeypatch


# Run tests
print('Running filemoon extractor tests...')
try:
    test_extract_iframe_src_from_script()
    print('test_extract_iframe_src_from_script: PASS')
    test_extract_iframe_src_from_fallback_html()
    print('test_extract_iframe_src_from_fallback_html: PASS')

    # Run monkeypatched end-to-end test
    # It requires pytest monkeypatch fixture; call the helper manually
    from types import SimpleNamespace
    from aniworld.extractors.provider import filemoon as fm

    download_page = SimpleNamespace(text="""
        <html><body>
        <script>var a = document.createElement('iframe'); a.src='//player.filemoon.to/e/abcd1234';</script>
        </body></html>
    """)

    iframe_page = SimpleNamespace(text="var video = {file: \"https://cdn.filemoon.to/videos/abcd1234.mp4\"};")

    calls = {'n': 0}

    def fake_make_request(url, headers=None):
        calls['n'] += 1
        if calls['n'] == 1:
            return download_page
        return iframe_page

    fm._make_request = fake_make_request
    direct = fm.get_direct_link_from_filemoon('https://filemoon.to/e/eawuwyrd40an')
    assert direct == 'https://cdn.filemoon.to/videos/abcd1234.mp4'
    print('test_get_direct_link_from_filemoon_monkeypatch: PASS')

    print('All filemoon extractor tests passed')
except AssertionError as e:
    print('Assertion failed:', e)
    sys.exit(1)
except Exception as e:
    print('Error running tests:', type(e).__name__, e)
    sys.exit(2)
