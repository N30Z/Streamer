# Claude Code Project Guide

This document provides guidance for AI assistants working on the AniWorld Downloader codebase.

## Project Overview

**AniWorld Downloader** is a Python application for downloading and streaming anime from aniworld.to and s.to. It provides multiple interfaces:

- **Web UI** - Flask-based web interface with user authentication
- **CLI** - Command-line interface with interactive menu
- **Python Library** - Importable module for programmatic use

**Version:** 3.9.0
**Python:** 3.9+
**Framework:** Flask (web), yt-dlp (downloads), BeautifulSoup4 (scraping)

## Project Structure

```
/home/user/Streamer/
├── src/aniworld/                 # Main source code
│   ├── web/                      # Web application
│   │   ├── app.py               # Flask routes and main web app
│   │   ├── database.py          # User authentication & sessions
│   │   ├── download_manager.py  # Parallel download queue
│   │   ├── templates/           # Jinja2 HTML templates
│   │   │   ├── index.html       # Main page
│   │   │   ├── settings.html    # User/admin settings (authentication)
│   │   │   ├── preferences.html # Application preferences (downloads, appearance)
│   │   │   ├── login.html       # Login page
│   │   │   └── setup.html       # Initial setup
│   │   └── static/              # CSS and JavaScript
│   ├── action/                   # Core actions
│   │   ├── download.py          # Download functionality
│   │   ├── watch.py             # Streaming/watching
│   │   ├── syncplay.py          # Syncplay integration
│   │   └── common.py            # Shared utilities
│   ├── extractors/               # Video extractors
│   │   └── provider/            # Provider implementations (9 providers)
│   ├── models.py                 # Data models (Anime, Episode)
│   ├── search.py                 # Search functionality
│   ├── config.py                 # Constants and configuration
│   ├── parser.py                 # CLI argument parsing
│   └── menu.py                   # Interactive menu
├── tests/                        # Test files
├── API.md                        # API documentation
└── pyproject.toml               # Project configuration
```

## Key Files

| File | Purpose |
|------|---------|
| `src/aniworld/web/app.py` | Main Flask application with all API routes |
| `src/aniworld/web/database.py` | SQLite user/session management |
| `src/aniworld/web/download_manager.py` | ThreadPoolExecutor-based download queue |
| `src/aniworld/web/templates/preferences.html` | Application preferences page |
| `src/aniworld/web/templates/settings.html` | User/admin settings page |
| `src/aniworld/models.py` | `Anime` and `Episode` dataclasses |
| `src/aniworld/search.py` | Search implementation for both sites |
| `src/aniworld/config.py` | Default configuration values |
| `src/aniworld/extractors/provider/` | Video URL extraction for each provider |

## Supported Sites

- `aniworld.to` - Anime streaming
- `s.to` - Series/TV shows

## Supported Providers

1. LoadX
2. VOE
3. Vidmoly
4. Filemoon
5. Luluvdo
6. Doodstream
7. Vidoza
8. SpeedFiles
9. Streamtape

## Code Conventions

### Python Style

- Python 3.9+ with type hints
- Dataclasses for models
- Flask for web routes
- Logging via Python's `logging` module

### API Patterns

All API endpoints follow this pattern:

```python
@app.route('/api/endpoint', methods=['POST'])
@login_required
def api_endpoint():
    try:
        data = request.get_json()
        # Process request
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
```

### Response Format

All API responses use consistent JSON format:

```json
// Success
{"success": true, "data": ...}

// Error
{"success": false, "message": "Error description"}
```

### Authentication

- Session-based authentication with 30-day expiry
- `@login_required` decorator for protected routes
- `@admin_required` decorator for admin-only routes

## Common Tasks

### Adding a New API Endpoint

1. Add route to `src/aniworld/web/app.py`
2. Use `@login_required` decorator if authentication needed
3. Return JSON with `{"success": true/false, ...}` format
4. Add error handling with try/except
5. Document in `API.md`

### Adding a New Provider

1. Create file in `src/aniworld/extractors/provider/`
2. Implement extractor class with `get_video_url()` method
3. Register in provider index
4. Update supported providers list in documentation

### Modifying Download Behavior

- Download logic is in `src/aniworld/action/download.py`
- Queue management in `src/aniworld/web/download_manager.py`
- Progress callbacks come from yt-dlp

## Database

SQLite database with two main tables:

```sql
-- Users
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    is_original_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- Sessions
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    session_token TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

**Database location by OS:**
- Docker: `/app/data/aniworld.db`
- Windows: `%APPDATA%/aniworld/aniworld.db`
- Linux/Mac: `~/.local/share/aniworld/aniworld.db`

## Testing

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_search.py
```

## Running the Application

```bash
# Web interface
aniworld --web

# Web interface exposed to network
aniworld --web --web-expose

# CLI interactive mode
aniworld

# Direct download
aniworld --url "https://aniworld.to/anime/stream/..."
```

## Important Notes

1. **Security**: File paths are validated to prevent directory traversal
2. **Parallel Downloads**: Default is 5 concurrent downloads (configurable via Preferences)
3. **Session Duration**: 30 days before expiry
4. **Video Formats**: mp4, mkv, avi, webm, mov, m4v, flv, wmv supported

## Preferences System

The application has a preferences system (`/preferences`) for configuring:

### Download Settings
- **Parallel Downloads**: Number of concurrent downloads (1-10)
- **Download Directory**: Where files are saved
- **Default Language**: German Dub, English Sub, German Sub
- **Default Provider**: Video provider for downloads (VOE, Filemoon, etc.)

### Appearance Settings
- **Accent Color**: UI color theme (purple, blue, green, orange, red, pink, cyan)
- **Animations**: Toggle background animations and particles

### Playback Settings
- **Default Action**: Download, Watch, or Syncplay
- **Watch Provider**: Preferred provider for streaming

### Preferences Storage
- **Windows**: `%APPDATA%/aniworld/preferences.json`
- **Linux/Mac**: `~/.local/share/aniworld/preferences.json`

### Preferences API Endpoints
- `GET /api/preferences` - Get current preferences
- `POST /api/preferences` - Save preferences
- `POST /api/preferences/reset` - Reset to defaults

## API Documentation

See `API.md` for complete API documentation with examples.

## Debugging Tips

- Web app logging goes to console and can be verbose
- Check `download_manager.py` for download queue issues
- Provider extractors may break if upstream sites change
- Use `/api/test` endpoint to verify API connectivity
- Use `/health` endpoint for health checks (no auth required)

## Environment Variables

No required environment variables. Configuration is done via:
- Command-line arguments
- Web interface settings
- `config.py` defaults
