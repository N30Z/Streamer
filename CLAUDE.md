# Claude Code Project Guide

This document provides guidance for AI assistants working on the AniWorld Downloader codebase.

## Project Overview

**AniWorld Downloader** (v3.9.0) is a Python 3.9+ application for downloading anime, series, and movies from streaming sites (aniworld.to, s.to, movie4k.sx). It provides a Flask-based web UI as the primary interface, with a full-featured CLI for direct downloads and automation.

**Package name:** `aniworld`
**Entry point:** `aniworld = "aniworld.__main__:main"` (defined in `pyproject.toml`)
**License:** MIT

## Architecture

```
Entry Points (__main__.py → entry.py)
         │
    ┌────┴────┐
    ▼         ▼
 Web UI    CLI Mode
(Flask)   (execute.py)
    │         │
    ▼         ▼
 Models (Anime, Episode, MovieAnime)
    │
    ▼
 Sites Layer (aniworld.py, s_to.py, movie4k.py)
    │
    ▼
 Extractors (9+ provider modules)
    │
    ▼
 Download (yt-dlp integration)
```

### Entry Points

- `src/aniworld/__main__.py` - Package entry point; calls `aniworld()` from `entry.py`
- `src/aniworld/entry.py` - Main orchestrator with three execution modes:
  1. **Web UI mode** (default) - Launches Flask server via `web/app.py`
  2. **Episode/File mode** - CLI downloads from `-e` URLs or `-f` file
  3. **Search mode** - Interactive terminal search when no args given

### Core Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Global constants (`SUPPORTED_SITES`, `SUPPORTED_PROVIDERS`), logging setup, provider headers, version checking |
| `parser.py` | CLI argument parsing (web UI flags, episode URLs, provider/language options) |
| `models.py` | `Anime`, `Episode`, `MovieAnime` data classes with lazy-loading metadata (~1,700 lines) |
| `execute.py` | Action dispatcher - routes to download action via `ACTION_MAP` |
| `search.py` | Re-exports search functions from site modules |
| `movie4k.py` | Movie4k data model adapter |

### Action Layer (`action/`)

- `download.py` - Downloads episodes using yt-dlp with progress hooks and custom filename formatting (S##E## pattern)
- `common.py` - Shared utilities: `sanitize_filename()`, `get_direct_link()`

### Site Modules (`sites/`)

Each site module provides search, episode parsing, and season/episode counting:

- `aniworld.py` - Uses AJAX JSON API for search (`/ajax/autocomplete`), HTML scraping for episode data
- `s_to.py` - Pure HTML scraping, search via `/suche?term=<keyword>`, different language codes
- `movie4k.py` - JSON API-based access via `/api/` endpoints, uses TMDB poster images

### Extractors (`extractors/`)

**Dynamic loading:** `extractors/__init__.py` uses `importlib` to auto-discover provider modules. Any file in `provider/` with a `get_direct_link_from_<name>()` function is automatically registered.

**Provider extractors** (`provider/`):
- `voe.py` - Multi-step decoding: ROT13 → pattern replacement → Base64 → JSON → M3U8 URL
- `vidmoly.py`, `filemoon.py`, `luluvdo.py`, `doodstream.py`, `vidoza.py`
- `speedfiles.py`, `streamtape.py`, `loadx.py`, `hanime.py`
- `common.py` - Shared extractor utilities

**Site extractors** (`site/`):
- `aniworld_extractor.py`, `s_to_extractor.py` - Site-level link extraction routing

### Web UI (`web/`)

- `app.py` - Flask application (~2,500 lines) with REST API, WebSocket support, authentication, download queue
- `download_manager.py` - ThreadPoolExecutor-based concurrent download queue (default: 5 workers)
- `database.py` - SQLite user authentication (SHA-256 + salt password hashing)
- `templates/` - Jinja2 templates: `index.html`, `login.html`, `settings.html`, `preferences.html`, `setup.html`
- `static/` - `css/style.css` and `js/app.js` (vanilla JavaScript, no frameworks)

### Supporting Modules

- `aniskip/aniskip.py` - MyAnimeList ID lookup for English descriptions
- `common/common.py` - Link generation utilities (`generate_links`, season/episode counting)

## Key REST API Endpoints

```
GET  /                          Main page
POST /api/search                Search across sites
GET  /api/popular-new           Popular/new content for homepage
POST /api/episodes/<slug>       Get episode tree for a series
POST /api/download              Add episodes to download queue
GET  /api/queue/status          Download queue status
GET  /api/queue/cancel/<id>     Cancel a download
GET  /api/files                 Browse downloaded files
GET  /api/version               Version info
GET  /api/providers             Available providers
GET  /api/languages             Available languages
```

## Key Patterns

### Provider Fallback

When a provider fails, the system tries others in order. See `Episode.get_direct_link()` in `models.py`:
```
Specified provider → Parent anime provider → Config default → All other providers in order
```

### Lazy Loading

The `Anime` model lazily fetches title, description, and episode metadata on first property access. Results are cached internally to avoid duplicate HTTP requests. A shared `_ANIME_DATA_CACHE` dict stores season/episode counts across instances.

### Site Detection

URLs are routed to the correct site module by matching the domain against `SUPPORTED_SITES` in `config.py`.

### Dynamic Provider Loading

New providers are auto-discovered from `extractors/provider/` via `importlib`. No manual registration in `__init__.py` is needed beyond the module naming convention.

## Code Conventions

### Naming

- **Modules:** `snake_case` (e.g., `download_manager.py`)
- **Classes:** `PascalCase` (e.g., `Anime`, `Episode`, `UserDatabase`)
- **Functions:** `snake_case` (e.g., `get_direct_link_from_voe()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `SUPPORTED_SITES`, `DEFAULT_LANGUAGE`)
- **Private:** Leading underscore (e.g., `_extract_slug_from_episodes()`)

### Error Handling

```python
try:
    response = requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
    response.raise_for_status()
except requests.RequestException as err:
    logging.error("Request failed: %s", err)
    raise ValueError("Descriptive error") from err
```

### Logging

Uses Python `logging` module. Log file: `{tempdir}/aniworld.log`. Levels: DEBUG for troubleshooting, INFO for general messages, WARNING/ERROR/CRITICAL for issues. Debug mode enabled via `-d` flag.

### Type Hints

Extensive use of type hints throughout the codebase including `Optional`, `Union`, `Dict`, `List`, and `Tuple`.

### Caching

- `@lru_cache(maxsize=128)` for expensive operations (e.g., search requests)
- Manual dict caching in `Anime` class for shared metadata

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests for scraping and API calls |
| `bs4` (BeautifulSoup4) | HTML parsing |
| `yt-dlp` | Core video downloading engine |
| `fake_useragent` | User agent rotation to avoid blocking |
| `packaging` | Version comparison |
| `jsbeautifier` | JavaScript decoding for obfuscated provider scripts |
| `flask` | Web server and REST API |
| `pychromecast` | Optional: Chromecast device casting |

## Build & CI

### GitHub Actions

- **build.yml** - Triggered on GitHub release: extracts version from `pyproject.toml`, builds sdist + wheel, uploads to PyPI
- **lint.yml** - Manual dispatch: runs `ruff check` and `pylint` against `src/aniworld/`

### Building Locally

```bash
pip install build
python -m build              # Creates dist/ with .tar.gz and .whl
pip install -e .             # Editable install for development
```

### Linting

```bash
ruff check src/aniworld
pylint src/aniworld --disable=broad-exception-caught,missing-module-docstring
```

## Testing

No formal automated test suite. Tests in `tests/` are manual scripts that run against live streaming sites:

- `test.py` - Main test suite
- `test_providers.py` - Provider extraction tests
- `test_voe_extractor.py`, `test_filemoon_extractor.py`, `test_streamtape_extractor.py` - Provider-specific
- `test_movie4k_api_providers.py`, `test_movie4k_redirects.py` - Movie4k tests
- `full_aniworld_test.py` - Comprehensive AniWorld tests

Debug scripts in `scripts/` for development (e.g., `debug_movie4k.py`, `fetch_filemoon_page.py`).

## Data Storage Paths

| Platform | Location |
|----------|----------|
| Linux/Mac | `~/.local/share/aniworld/` |
| Windows | `%APPDATA%/aniworld/` |
| Docker | `/app/data/` |

Files stored: `aniworld.db` (SQLite auth database), `preferences.json` (user settings).

## Common Tasks

### Adding a New Provider

1. Create `src/aniworld/extractors/provider/<name>.py` with a `get_direct_link_from_<name>(url)` function
2. Add to `SUPPORTED_PROVIDERS` tuple in `config.py`
3. Add provider-specific headers to `_get_provider_headers_d()` in `config.py` if needed
4. The dynamic loader in `extractors/__init__.py` will auto-discover it

### Adding a New Streaming Site

1. Create `src/aniworld/sites/<name>.py` with search, episode parsing, and counting functions
2. Add to `SUPPORTED_SITES` dict in `config.py` with `base_url`, `stream_path`, and optional `type`
3. Create site extractor in `extractors/site/<name>_extractor.py`
4. Add language code mappings if different from existing sites
5. Update web UI search and popular/new sections in `web/app.py`

### Modifying the Web UI

- Backend routes: `src/aniworld/web/app.py`
- Frontend logic: `src/aniworld/web/static/js/app.js` (vanilla JS, no build step)
- Styles: `src/aniworld/web/static/css/style.css`
- Templates: `src/aniworld/web/templates/` (Jinja2)
- No frontend build pipeline - edit files directly

### Running the Application

```bash
# Web UI (default)
aniworld
aniworld --web-ui --web-port 8080 --web-expose

# CLI download
aniworld -e https://aniworld.to/anime/stream/example/staffel-1/episode-1
aniworld -e <url1> <url2> -p VOE -L "English Sub" -o /path/to/downloads

# From file
aniworld -f episodes.txt

# Direct link only (for external players)
aniworld -e <url> -D

# Debug mode
aniworld -d -e <url>
```

## Directory Structure

```
src/aniworld/
├── __main__.py              # Package entry point
├── entry.py                 # Main orchestrator
├── config.py                # Constants, logging, version
├── parser.py                # CLI argument parsing
├── models.py                # Anime/Episode/MovieAnime models
├── execute.py               # Action dispatcher
├── search.py                # Search re-exports
├── movie4k.py               # Movie4k adapter
├── action/
│   ├── download.py          # yt-dlp download logic
│   └── common.py            # Shared utilities
├── web/
│   ├── app.py               # Flask app + REST API
│   ├── download_manager.py  # Concurrent download queue
│   ├── database.py          # SQLite user auth
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS + JS assets
├── sites/
│   ├── aniworld.py          # aniworld.to scraper
│   ├── s_to.py              # s.to scraper
│   └── movie4k.py           # movie4k.sx API client
├── extractors/
│   ├── __init__.py          # Dynamic provider loader
│   ├── provider/            # Video provider extractors (9+)
│   └── site/                # Site-level extractors
├── aniskip/
│   └── aniskip.py           # MyAnimeList integration
└── common/
    └── common.py            # Link generation utilities
```
