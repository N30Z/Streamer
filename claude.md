# Claude Code Project Guide

This document provides guidance for AI assistants working on the AniWorld Downloader codebase.

## Project Overview

AniWorld Downloader is a Python-based web application for downloading anime, series and movies from aniworld.to, s.to and movie4k.sx. The primary interface is a Flask web UI, with a secondary CLI download mode.

## Architecture

### Entry Points
- `src/aniworld/__main__.py` - Package entry point, calls `aniworld()` from `entry.py`
- `src/aniworld/entry.py` - Main orchestrator. Default mode launches web UI; CLI mode downloads episodes via URL arguments

### Core Modules
- `config.py` - Global constants, logging setup, provider headers, version checking
- `parser.py` - Argument parsing (web UI flags, episode URLs, provider/language options)
- `models.py` - `Anime` and `Episode` data classes with lazy-loading metadata
- `execute.py` - Action dispatcher (routes to download action)
- `search.py` - Re-exports search functions from site modules

### Action Layer
- `action/download.py` - Downloads episodes using yt-dlp with progress tracking
- `action/common.py` - Shared utilities: `sanitize_filename()`, `get_direct_link()`

### Site Modules (`sites/`)
- `sites/aniworld.py` - aniworld.to search, episode parsing, season/episode counting
- `sites/s_to.py` - s.to search and episode parsing
- `sites/movie4k.py` - movie4k.sx search and movie/episode parsing

### Extractors (`extractors/`)
Provider-specific modules that extract direct video URLs from streaming providers:
- `provider/voe.py`, `provider/vidmoly.py`, `provider/filemoon.py`, `provider/luluvdo.py`
- `provider/doodstream.py`, `provider/vidoza.py`, `provider/speedfiles.py`, `provider/streamtape.py`
- `provider/loadx.py`, `provider/hanime.py`
- `site/aniworld_extractor.py`, `site/s_to_extractor.py` - Site-level link extraction

### Web UI (`web/`)
- `web/app.py` - Flask application with REST API endpoints, download manager, settings
- `web/download_manager.py` - Concurrent download queue management
- `web/templates/` - Jinja2 HTML templates (index, login, settings, preferences)
- `web/static/` - CSS and JavaScript assets

### Supporting Modules
- `aniskip/` - MyAnimeList ID lookup (`get_mal_id_from_title`) used for English descriptions
- `common/common.py` - Link generation utilities (`generate_links`, season/episode counting)
- `movie4k.py` - Movie4k data model adapter

## Key Patterns

### Provider Fallback
When the default provider fails, the system automatically tries other providers. See `models.py` Episode.get_direct_link().

### Site Detection
URLs are routed to the correct site module based on domain matching against `SUPPORTED_SITES` in `config.py`.

### Lazy Loading
The `Anime` model lazily fetches title, description, and episode metadata on first access to avoid unnecessary HTTP requests.

## Dependencies

Core: `requests`, `bs4`, `yt-dlp`, `fake_useragent`, `packaging`, `jsbeautifier`, `flask`

## Testing

No formal test suite. Manual testing against live sites. Test HTML fixtures exist in `tests/`.

## Common Tasks

### Adding a new provider
1. Create `src/aniworld/extractors/provider/<name>.py` with `get_direct_link_from_<name>(url)` function
2. Register in `extractors/__init__.py`
3. Add to `SUPPORTED_PROVIDERS` tuple in `config.py`
4. Add provider-specific headers to `_get_provider_headers_d()` in `config.py` if needed

### Adding a new site
1. Create `src/aniworld/sites/<name>.py` with search, episode parsing, and counting functions
2. Add to `SUPPORTED_SITES` in `config.py`
3. Create site extractor in `extractors/site/`
