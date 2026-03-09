# AnyLoader

Web-based downloader for anime, series and movies from [aniworld.to](https://aniworld.to), [s.to](https://s.to) and [movie4k.sx](https://movie4k.sx).

## Features

- **Web UI** - Flask-based web interface for browsing, searching and downloading
- **Multi-site support** - Anime (aniworld.to), Serien (s.to) and Movies (movie4k.sx)
- **Multiple providers** - VOE, Vidmoly, Filemoon, Luluvdo, Doodstream, Vidoza, SpeedFiles, Streamtape, LoadX
- **Provider fallback chain** - If a provider's primary extractor fails, automatically tries Playwright browser intercept, then native yt-dlp extraction
- **Language selection** - German Dub, English Sub, German Sub, English Dub
- **Parallel downloads** - Configurable concurrent download queue
- **Parallel segments** - Configurable parallel HLS/DASH segment downloads per video (default: 5, see Preferences)
- **Subscriptions** - Subscribe to series/anime; get notified or auto-download new episodes
- **Continue Watching** - Home page shows in-progress content; resume from where you left off
- **Watch progress tracking** - Progress bars in file browser and download modal; resume any episode
- **Plex integration** - Sign in with Plex and sync your watchlist
- **Chromecast support** - Discover and cast to Chromecast devices on your network
- **Built-in file browser** - Stream or download files directly from the web UI
- **Authentication** - Optional web interface authentication with user management
- **Auto FFmpeg** - Automatically downloads FFmpeg if not found on your system

## Installation

### Windows (Native App)

Download `Streamer.exe` from the [latest release](https://github.com/N30Z/Streamer/releases) and run it. No installation or Python required -- FFmpeg is bundled in.

### pip (All Platforms)

```bash
pip install aniworld
```

Optional Chromecast support:

```bash
pip install aniworld[chromecast]
```

Optional browser-based provider fallback (Playwright):

```bash
pip install aniworld[browser]
playwright install chromium
```

When installed, Playwright is used as an automatic fallback when a provider's standard extractor fails — it loads the embed page in headless Chromium and intercepts the stream URL.

### Requirements (pip install)

- Python 3.9+
- FFmpeg (auto-downloaded if missing)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (installed automatically as dependency)

## Usage

### Web UI (default)

```bash
aniworld
```

Starts the web interface at `http://localhost:5000`.

### Web UI options

```bash
aniworld --web-ui                 # Explicit web UI flag
aniworld --web-port 8080          # Custom port
aniworld --web-expose             # Bind to 0.0.0.0 for external access
aniworld --enable-web-auth        # Enable authentication
aniworld --no-browser             # Don't auto-open browser
```

### CLI download

```bash
aniworld -e https://aniworld.to/anime/stream/example/staffel-1/episode-1
aniworld -e <url1> <url2> -p VOE -L "English Sub"
aniworld -f episodes.txt -o /path/to/downloads
```

### Options

| Flag | Description |
|------|-------------|
| `-w`, `--web-ui` | Start web interface |
| `-wP`, `--web-port` | Web interface port (default: 5000) |
| `-wE`, `--web-expose` | Bind to 0.0.0.0 |
| `-wA`, `--enable-web-auth` | Enable web authentication |
| `-wN`, `--no-browser` | Don't auto-open browser |
| `-e`, `--episode` | Episode URL(s) |
| `-f`, `--episode-file` | File with episode URLs |
| `-o`, `--output-dir` | Download directory |
| `-L`, `--language` | Language (German Dub/English Sub/German Sub/English Dub) |
| `-p`, `--provider` | Provider (VOE, Vidmoly, Filemoon, etc.) |
| `-s`, `--slug` | Series slug |
| `-K`, `--keep-watching` | Continue to next episodes |
| `-D`, `--only-direct-link` | Output direct link only |
| `-C`, `--only-command` | Output command only |
| `-d`, `--debug` | Enable debug logging |
| `-v`, `--version` | Show version |

## Subscriptions

Open any series in the download modal and click the **Subscribe** button (⭐) to subscribe. You can configure:

- **Notify** — show a browser notification when new episodes are available
- **Auto-download** — automatically queue new episodes for download

Subscribed series appear in the **Subscriptions panel** (star icon in the navbar). AnyLoader checks for new episodes **on every server start** (after a short 30-second delay) and then **every hour** in the background. You can also trigger a manual check from the subscriptions panel refresh button.

## License

MIT
