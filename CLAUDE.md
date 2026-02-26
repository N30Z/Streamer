# Claude Code Project Guide

This document provides guidance for AI assistants working on the AnyLoader codebase.

## Project Overview

**AnyLoader** (formerly AniWorld Downloader, v3.9.0) is a Python 3.9+ application for downloading anime, series, and movies from streaming sites (aniworld.to, s.to, movie4k.sx). It provides a Flask-based web UI as the primary interface, with a full-featured CLI for direct downloads and automation. A native Windows desktop app (via pywebview + PyInstaller) is also supported.

The web UI branding is **AnyLoader**. The underlying Python package name remains `aniworld` for backward compatibility.

**Package name:** `aniworld`
**Entry point:** `aniworld = "aniworld.__main__:main"` (defined in `pyproject.toml`)
**License:** MIT
**Repository:** https://github.com/phoenixthrush/AniWorld-Downloader

## Architecture

```
Entry Points (__main__.py -> entry.py)
         |
    +----+----+
    v         v
 Web UI    CLI Mode
(Flask)   (execute.py)
    |         |
    v         v
 Models (Anime, Episode, MovieAnime)
    |
    v
 Sites Layer (aniworld.py, s_to.py, movie4k.py)
    |
    v
 Extractors (10 provider modules, dynamically loaded)
    |
    v
 Download (yt-dlp + FFmpeg integration)
```

### Entry Points

- `src/aniworld/__main__.py` - Package entry point; calls `aniworld()` from `entry.py`, sets terminal title
- `src/aniworld/entry.py` (~227 lines) - Main orchestrator with three execution modes:
  1. **Web UI mode** (default) - Launches Flask server via `web/app.py`
  2. **Episode/File mode** - CLI downloads from `-e` URLs or `-f` file
  3. **Search mode** - Interactive terminal search when no args given
- `native_launcher.py` (root) - Native Windows desktop launcher; starts Flask backend in a daemon thread and opens a pywebview window. Designed for PyInstaller compilation (`--onefile --noconsole`).

### Core Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `config.py` | ~255 | Global constants (`SUPPORTED_SITES`, `SUPPORTED_PROVIDERS`), logging setup, provider headers, version checking |
| `parser.py` | ~355 | CLI argument parsing (web UI flags, episode URLs, provider/language options) |
| `models.py` | ~1,693 | `Anime`, `Episode`, `MovieAnime` data classes with lazy-loading metadata |
| `execute.py` | ~95 | Action dispatcher - routes to download action via `ACTION_MAP` |
| `search.py` | ~36 | Re-exports search functions from site modules |
| `movie4k.py` | ~14 | Movie4k data model adapter (thin re-export wrapper) |
| `ffmpeg_downloader.py` | ~227 | Auto-downloads FFmpeg binaries from BtbN/FFmpeg-Builds if not found on system |

### Action Layer (`action/`)

- `download.py` (~384 lines) - Downloads episodes using yt-dlp with progress hooks and custom filename formatting (S##E## pattern)
- `common.py` - Shared utilities: `sanitize_filename()`, `get_direct_link()`

### Site Modules (`sites/`)

Each site module provides search, episode parsing, and season/episode counting:

- `aniworld.py` (~608 lines) - Uses AJAX JSON API for search (`/ajax/autocomplete`), HTML scraping for episode data
- `s_to.py` (~471 lines) - Pure HTML scraping, search via `/suche?term=<keyword>`, different language codes
- `movie4k.py` (~740 lines) - JSON API-based access via `/api/` endpoints, uses TMDB poster images

### Extractors (`extractors/`)

**Dynamic loading:** `extractors/__init__.py` uses `pkgutil.iter_modules` to auto-discover provider modules. Any file in `provider/` with a `get_direct_link_from_<name>()` function is automatically registered.

**Provider extractors** (`provider/`):
- `voe.py` (~263 lines) - Multi-step decoding: ROT13 -> pattern replacement -> Base64 -> JSON -> M3U8 URL
- `filemoon.py` (~240 lines) - JavaScript beautification, iframe extraction
- `hanime.py` (~489 lines) - Hanime extractor (separate site, not in SUPPORTED_PROVIDERS)
- `loadx.py` (~276 lines) - LoadX extractor
- `luluvdo.py` (~293 lines) - Luluvdo extractor
- `speedfiles.py` (~281 lines) - SpeedFiles extractor
- `doodstream.py` (~158 lines) - Doodstream extractor
- `vidmoly.py` (~100 lines) - Vidmoly extractor
- `vidoza.py` (~62 lines) - Vidoza extractor
- `streamtape.py` (~87 lines) - Streamtape extractor
- `common.py` - Shared extractor utilities

**Note:** The `extractors/site/` directory referenced in older docs does not exist. Site-level extraction logic is handled within `models.py` and the site modules themselves.

### Web UI (`web/`)

- `app.py` (~3,400+ lines) - Flask application wrapped in a `WebApp` class. REST API, authentication, download queue, Plex integration, Chromecast support, file streaming, watch progress tracking, **subscription management**.
  - **`WebApp.__init__()` startup sequence**: (1) init download manager, (2) create Flask app, (3) apply saved preferences, (4) ensure FFmpeg is available, (5) scan media library (log series/season/episode counts), (6) start metadata backfill (background), (7) init subscription notification store, (8) **start subscription checker** (background — 30 s delay then immediate check + hourly loop), (9) set up routes.
- `download_manager.py` (~764 lines) - `DownloadQueueManager` with ThreadPoolExecutor-based concurrent download queue (default: 5 workers). In-memory job storage with progress tracking and graceful cancellation.
- `database.py` (~479 lines) - `UserDatabase` class for SQLite user authentication (SHA-256 + salt password hashing)
- `templates/` - Jinja2 templates:
  - `index.html` - Main page with search, results, download queue, **subscriptions panel**, **continue watching**
  - `login.html` - Authentication form
  - `settings.html` - Application settings
  - `preferences.html` - User preferences page
  - `preferences_modal.html` - Preferences modal variant
  - `setup.html` - First-run setup wizard
- `static/` - Frontend assets (no build pipeline, edit directly):
  - `css/style.css` (~103 KB) - Complete styling with responsive design
  - `js/app.js` (~140+ KB) - Vanilla JavaScript, no frameworks

### Supporting Modules

- `aniskip/aniskip.py` - MyAnimeList ID lookup for English descriptions
- `common/common.py` (~263 lines) - Link generation utilities (`generate_links`, season/episode counting), shared `_ANIME_DATA_CACHE`

## Key REST API Endpoints

### Core
```
GET  /                               Main page
GET  /health                         Health check
GET  /api/info                       Server info (version, uptime, auth status)
GET  /api/test                       API connectivity test
```

### Search & Content
```
POST /api/search                     Search across sites
GET  /api/popular-new                Popular/new content (aniworld.to)
GET  /api/popular-new-sto            Popular/new content (s.to)
GET  /api/popular-new-movie4k        Popular/new content (movie4k.sx)
POST /api/episodes                   Get episode tree for a series
POST /api/direct                     Get direct download link for an episode
```

### Downloads
```
POST /api/download                   Add episodes to download queue
GET  /api/queue-status               Download queue status
POST /api/queue/cancel/<id>          Cancel a download
GET  /api/download-path              Get current download directory
```

### File Management
```
GET  /api/files                      Browse downloaded files
POST /api/files/delete               Delete downloaded files
GET  /api/files/stream/<path>        Stream a file (video/audio)
GET  /api/files/download/<path>      Download a file
POST /api/files/play                 Launch file in local media player
```

### Watch Progress
```
GET  /api/watch-progress             Get watch progress for files
POST /api/watch-progress             Save watch progress
DELETE /api/watch-progress           Clear watch progress
```

### Subscriptions
```
GET  /api/subscriptions              List all subscriptions (+ pending notifications)
POST /api/subscriptions              Add a new subscription
DELETE /api/subscriptions/<id>       Remove a subscription
PUT  /api/subscriptions/<id>         Update subscription settings (notify, auto_download, language)
POST /api/subscriptions/check        Manually trigger a new-episode check (background)
GET  /api/subscriptions/notifications Get and clear pending new-episode notifications
POST /api/subscriptions/check-url    Check if a series URL is already subscribed
```

### Plex Integration
```
POST /api/plex/auth/pin              Create Plex OAuth PIN for sign-in
GET  /api/plex/auth/check/<pin_id>   Check if Plex PIN was authorized
GET  /api/plex/watchlist             Get user's Plex watchlist
POST /api/plex/search-and-download   Search & download from Plex watchlist
```

### Chromecast
```
GET  /api/chromecast/discover        Discover Chromecast devices on network
POST /api/chromecast/cast            Cast a file to Chromecast
POST /api/chromecast/control         Control Chromecast playback (play/pause/stop/seek)
GET  /api/chromecast/status          Get current Chromecast playback status
```

### Preferences
```
GET  /api/preferences                Get user preferences
POST /api/preferences                Save user preferences
POST /api/preferences/reset          Reset preferences to defaults
GET  /api/preferences/modal          Render preferences modal HTML
```

### User Management (auth-enabled mode)
```
GET  /api/users                      List users
POST /api/users                      Create user
PUT  /api/users/<id>                 Update user
DELETE /api/users/<id>               Delete user
POST /api/change-password            Change current user password
```

### Authentication Pages
```
GET/POST /login                      Login page
POST     /logout                     Logout
GET/POST /setup                      First-run admin setup
GET      /settings                   Settings page
GET      /preferences                Preferences page
```

### Utility
```
POST /api/browse-folder              Browse filesystem directories
```

## Key Patterns

### Provider Fallback

When a provider fails, the system tries others in order. See `Episode.get_direct_link()` in `models.py`:
```
Specified provider -> Parent anime provider -> Config default -> All other providers in order
```

### Lazy Loading

The `Anime` model lazily fetches title, description, and episode metadata on first property access. Results are cached internally to avoid duplicate HTTP requests. A shared `_ANIME_DATA_CACHE` dict in `common/common.py` stores season/episode counts across instances.

### Site Detection

URLs are routed to the correct site module by matching the domain against `SUPPORTED_SITES` in `config.py`.

### Dynamic Provider Loading

New providers are auto-discovered from `extractors/provider/` via `pkgutil.iter_modules`. No manual registration in `__init__.py` is needed beyond the module naming convention (`get_direct_link_from_<name>()`).

### FFmpeg Auto-Download

`ffmpeg_downloader.py` checks for FFmpeg in order: PyInstaller bundle -> System PATH -> App data directory. If not found anywhere, it auto-downloads pre-built binaries from BtbN/FFmpeg-Builds for the current platform (Windows x64/x86, Linux x64/ARM64).

## Configuration Constants (`config.py`)

```python
SUPPORTED_SITES = {
    "aniworld.to": {"base_url": ..., "stream_path": "anime/stream"},
    "s.to":        {"base_url": ..., "stream_path": "serie"},
    "movie4k.sx":  {"base_url": ..., "stream_path": "watch", "type": "movie"},
}

SUPPORTED_PROVIDERS = (
    "LoadX", "VOE", "Vidmoly", "Filemoon", "Luluvdo",
    "Doodstream", "Vidoza", "SpeedFiles", "Streamtape",
)

DEFAULT_LANGUAGE = "German Sub"
DEFAULT_PROVIDER = "VOE"
DEFAULT_DOWNLOAD_PATH = ~/Downloads
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 5
DEFAULT_REQUEST_TIMEOUT = 30
```

### Language Code Mappings

| Site | German Dub | English Sub/Dub | German Sub |
|------|-----------|-----------------|------------|
| aniworld.to | 1 | 2 (English Sub) | 3 |
| s.to | 1 | 2 (English Dub) | 3 |
| movie4k.sx | 2 (Deutsch) | 3 (English) | - |

## Code Conventions

### Naming

- **Modules:** `snake_case` (e.g., `download_manager.py`)
- **Classes:** `PascalCase` (e.g., `Anime`, `Episode`, `WebApp`, `UserDatabase`)
- **Functions:** `snake_case` (e.g., `get_direct_link_from_voe()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `SUPPORTED_SITES`, `DEFAULT_LANGUAGE`)
- **Private:** Leading underscore (e.g., `_extract_slug_from_episodes()`, `_get_ffmpeg_dir()`)

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

Uses Python `logging` module. Log file: `{tempdir}/aniworld.log`. Custom `CriticalErrorHandler` raises `SystemExit` on CRITICAL. Console handler set to WARNING level. Debug mode enabled via `-d` flag.

Third-party loggers (`urllib3`, `charset_normalizer`, `bs4.dammit`) are silenced to WARNING/ERROR level.

### Type Hints

Extensive use of type hints throughout the codebase including `Optional`, `Union`, `Dict`, `List`, and `Tuple`.

### Caching

- `@lru_cache(maxsize=128)` for expensive operations (e.g., search requests)
- `@lru_cache(maxsize=1)` for singletons (e.g., `get_latest_github_version()`, `get_random_user_agent()`)
- Manual dict caching in `Anime` class via shared `_ANIME_DATA_CACHE`

## Dependencies

### Core (pyproject.toml)

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests for scraping and API calls |
| `bs4` (BeautifulSoup4) | HTML parsing |
| `yt-dlp` | Core video downloading engine |
| `fake_useragent` | User agent rotation to avoid blocking |
| `packaging` | Version comparison |
| `jsbeautifier` | JavaScript decoding for obfuscated provider scripts |
| `flask` | Web server and REST API |

### Optional (pyproject.toml)

| Package | Purpose |
|---------|---------|
| `pychromecast` | Chromecast device casting (`pip install aniworld[chromecast]`) |

### Development / Native App (requirements.txt)

| Package | Purpose |
|---------|---------|
| `npyscreen` | Terminal UI framework |
| `tqdm` | Progress bars |
| `pywebview` | Native desktop window wrapper (for `native_launcher.py`) |
| `windows-curses` | Windows terminal support |
| `winfcntl` | Windows file locking |

## Build & CI

### GitHub Actions

- **build.yml** - Triggered on GitHub release or manual dispatch: extracts version from `pyproject.toml`, builds sdist + wheel, uploads to PyPI via trusted publishing
- **lint.yml** - Manual dispatch: runs `ruff check` and `pylint` against `src/aniworld/`
- **build-native-exe.yml** - Triggered on push to main: builds a Windows native .exe using PyInstaller with embedded FFmpeg, pywebview, and all provider modules as hidden imports. Output: `dist/Streamer.exe`

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
- `sto.py` - S.to-specific tests
- Sample HTML files for offline parsing tests

Debug scripts in `scripts/` for development:
- `debug_movie4k.py`, `movie4k_query.py` - Movie4k debugging
- `fetch_filemoon_page.py`, `fetch_streamtape_page.py` - Provider page fetching
- `run_quick_test.py`, `run_filemoon_tests.py` - Test runners
- `test_aniworld_titles.py`, `test_ani_title.py`, `test_fixed_aniworld_titles.py` - Title parsing
- `test_aniworld_episode_page.py`, `test_aniworld_api.py` - AniWorld API/page tests
- `test_parse_episode_titles.py` - Episode title parsing
- `test_doodstream.py` - Doodstream tests
- `test_sto_title.py` - S.to title tests

## New Features (AnyLoader)

### Subscription System
- Subscriptions stored in `~/.local/share/aniworld/subscriptions.json` (Windows: `%APPDATA%/aniworld/subscriptions.json`)
- **Startup check**: `_start_subscription_checker()` is called during `WebApp.__init__()`. It spawns a daemon thread that waits 30 seconds (so the app finishes initialising), then runs `_check_subscriptions_once()` immediately. This means subscriptions are verified for new episodes shortly after every server start, not just on the hourly schedule.
- **Hourly polling**: After the initial startup check the background thread sleeps for 1 hour and re-checks in a loop.
- **Per-subscription settings**: notify on new episodes, auto-download new episodes, language
- **Navbar**: Star button opens subscriptions panel listing all subscribed series
- **Download modal**: Subscribe button in footer; expands subscription settings panel
- Helper methods in `WebApp`:
  - `_get_subscriptions_file()` / `_load_subscriptions()` / `_save_subscriptions()`
  - `_count_total_episodes(series_url)` - counts episodes for new-episode detection
  - `_check_subscriptions_once()` - runs the check loop body (iterates every subscription, compares episode counts, fires notifications & auto-downloads)
  - `_auto_download_new_episodes(sub, old, new)` - queues new episodes
  - `_start_subscription_checker()` - spawns daemon thread (30 s delay → initial check → hourly loop)

### Watch Progress in Download Modal
- When the download modal opens for a series with local files, episode progress is fetched via `/api/watch-progress`
- Episodes/movies with partial progress (5%–95%) show an **orange progress bar** and a **Resume** (↩) button
- Episodes with >95% progress show a **Watched** ✓ badge
- Clicking Resume starts playback from the saved timestamp

### Continue Watching (Home Page)
- The home page shows a "Continue Watching" horizontal grid of in-progress files
- Files with 5%–95% watch progress appear; clicking starts from saved position
- Updates on every page load

### AnyLoader Branding
- UI title, page titles, and all user-facing text now say **AnyLoader**
- Index columns renamed: `aniworld.to → Anime`, `s.to → Serien`, `movie4k.sx → Movies`
- Search checkboxes reflect the same labels

## Data Storage Paths

| Platform | Location |
|----------|----------|
| Linux/Mac | `~/.local/share/aniworld/` |
| Windows | `%APPDATA%/aniworld/` |
| Docker | `/app/data/` |

Files stored:
- `aniworld.db` - SQLite authentication database
- `preferences.json` - User settings
- `subscriptions.json` - Series subscriptions (notify/auto-download settings)
- `ffmpeg/` - Auto-downloaded FFmpeg/FFprobe binaries

## CLI Arguments

### General
- `-d, --debug` - Enable debug logging
- `-v, --version` - Show version

### Episode Input
- `-e, --episode` - One or more episode URLs
- `-f, --episode-file` - File containing episode URLs
- `-pl, --provider-link` - Direct provider URLs

### Download Options
- `-o, --output-dir` - Download directory (default: `~/Downloads`)
- `-L, --language` - Language: `German Dub`, `English Sub`, `German Sub`, `English Dub`
- `-p, --provider` - Provider: `LoadX`, `VOE`, `Vidmoly`, `Filemoon`, `Luluvdo`, `Doodstream`, `Vidoza`, `SpeedFiles`, `Streamtape`

### Web UI
- `-w, --web-ui` - Start Flask web interface
- `-wP, --web-port` - Web port (default: 5000)
- `-wA, --enable-web-auth` - Enable authentication
- `-wN, --no-browser` - Don't auto-open browser
- `-wE, --web-expose` - Bind to 0.0.0.0 (network-accessible)

### Miscellaneous
- `-s, --slug` - Search slug
- `-K, --keep-watching` - Continue to next episodes automatically
- `-r, --random-anime` - Play random anime by genre
- `-D, --only-direct-link` - Output direct link only (for external players)
- `-C, --only-command` - Output yt-dlp command only

## Common Tasks

### Adding a New Provider

1. Create `src/aniworld/extractors/provider/<name>.py` with a `get_direct_link_from_<name>(url)` function
2. Add to `SUPPORTED_PROVIDERS` tuple in `config.py`
3. Add provider-specific headers to `_get_provider_headers_d()` in `config.py` if needed
4. Add `--hidden-import aniworld.extractors.provider.<name>` to `.github/workflows/build-native-exe.yml`
5. The dynamic loader in `extractors/__init__.py` will auto-discover it at runtime

### Adding a New Streaming Site

1. Create `src/aniworld/sites/<name>.py` with search, episode parsing, and counting functions
2. Add to `SUPPORTED_SITES` dict in `config.py` with `base_url`, `stream_path`, and optional `type`
3. Add language code mappings to `LANGUAGE_CODES_*` / `LANGUAGE_NAMES_*` in `config.py`
4. Update `SITE_LANGUAGE_CODES` and `SITE_LANGUAGE_NAMES` dicts
5. Update web UI search and popular/new sections in `web/app.py`

### Modifying the Web UI

- Backend routes: `src/aniworld/web/app.py` (`WebApp` class)
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

# Command only (output yt-dlp command)
aniworld -e <url> -C

# Debug mode
aniworld -d -e <url>
```

## Directory Structure

```
Streamer/
├── CLAUDE.md                        # This file - AI assistant guide
├── README.md                        # User documentation
├── LICENSE                          # MIT License
├── pyproject.toml                   # Project metadata & dependencies
├── requirements.txt                 # Development/native app dependencies
├── MANIFEST.in                      # Package manifest (includes web assets)
├── native_launcher.py               # Windows native desktop launcher (pywebview)
├── .github/
│   ├── workflows/
│   │   ├── build.yml                # PyPI release workflow
│   │   ├── lint.yml                 # Ruff & PyLint linting
│   │   └── build-native-exe.yml     # Windows PyInstaller build
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── src/aniworld/
│   ├── __init__.py                  # Empty package init
│   ├── __main__.py                  # Package entry point
│   ├── entry.py                     # Main orchestrator
│   ├── config.py                    # Constants, logging, version
│   ├── parser.py                    # CLI argument parsing
│   ├── models.py                    # Anime/Episode/MovieAnime models
│   ├── execute.py                   # Action dispatcher
│   ├── search.py                    # Search re-exports
│   ├── movie4k.py                   # Movie4k adapter (re-exports)
│   ├── ffmpeg_downloader.py         # FFmpeg auto-download utility
│   ├── action/
│   │   ├── download.py              # yt-dlp download logic
│   │   └── common.py                # Shared utilities
│   ├── web/
│   │   ├── app.py                   # Flask app (WebApp class) + REST API
│   │   ├── download_manager.py      # Concurrent download queue
│   │   ├── database.py              # SQLite user auth
│   │   ├── templates/
│   │   │   ├── index.html           # Main page
│   │   │   ├── login.html           # Login page
│   │   │   ├── settings.html        # Settings page
│   │   │   ├── preferences.html     # Preferences page
│   │   │   ├── preferences_modal.html # Preferences modal variant
│   │   │   └── setup.html           # First-run setup wizard
│   │   └── static/
│   │       ├── css/style.css        # Main stylesheet (~101 KB)
│   │       └── js/app.js            # Frontend logic (~129 KB, vanilla JS)
│   ├── sites/
│   │   ├── __init__.py              # Re-exports all site functions
│   │   ├── aniworld.py              # aniworld.to scraper
│   │   ├── s_to.py                  # s.to scraper
│   │   └── movie4k.py               # movie4k.sx API client
│   ├── extractors/
│   │   ├── __init__.py              # Dynamic provider loader (pkgutil)
│   │   └── provider/               # Video provider extractors (10 modules)
│   │       ├── common.py            # Shared extractor utilities
│   │       ├── voe.py               # VOE extractor
│   │       ├── filemoon.py          # Filemoon extractor
│   │       ├── hanime.py            # Hanime extractor
│   │       ├── loadx.py             # LoadX extractor
│   │       ├── luluvdo.py           # Luluvdo extractor
│   │       ├── speedfiles.py        # SpeedFiles extractor
│   │       ├── doodstream.py        # Doodstream extractor
│   │       ├── vidmoly.py           # Vidmoly extractor
│   │       ├── vidoza.py            # Vidoza extractor
│   │       └── streamtape.py        # Streamtape extractor
│   ├── aniskip/
│   │   └── aniskip.py               # MyAnimeList integration
│   └── common/
│       └── common.py                # Link generation utilities
├── tests/                           # Manual test scripts (live site tests)
└── scripts/                         # Debug & development scripts
```
