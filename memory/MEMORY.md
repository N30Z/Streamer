# AnyLoader Project Memory

## Project
- Python app (aniworld package) for downloading anime/series/movies
- Flask web UI, CLI, Windows native app (PyInstaller)
- Main source: `src/aniworld/`

## Key Files
- Extractors: `src/aniworld/extractors/provider/`
- Config/providers: `src/aniworld/config.py`
- Web app: `src/aniworld/web/app.py`
- Test scripts: `scripts/`

## User Preferences
- Communication in German or English (user writes German)
- Direct, concise responses

## veev.to Extractor — COMPLETE
See `veev-research.md` for full details.

**Status:** Fully implemented with requests fast-path + Playwright fallback.
- `src/aniworld/extractors/provider/veev.py` — requests fast-path (cmd=gi) + Playwright fallback
- `src/aniworld/extractors/browser_interceptor.py` — generic reusable Playwright URL interceptor
- "Veev" added to `SUPPORTED_PROVIDERS` in `config.py`
- `playwright` optional dep: `pip install aniworld[browser]`
- Native exe: `--hidden-import` entries added to `build-native-exe.yml`

## Generic Browser Interceptor
`src/aniworld/extractors/browser_interceptor.py` — `intercept_url(page_url, match, *, timeout, referrer, wait_for, extra_headers)`
Reusable for any provider that needs headless browser URL capture (filemoon, luluvdo, etc.)
