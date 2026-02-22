"""
Flask web application for AnyLoader
"""

import logging
import os
import time
import threading
import webbrowser
import subprocess
import mimetypes
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response, send_file

from .. import config
from .database import UserDatabase
from .download_manager import get_download_manager


class WebApp:
    """Flask web application wrapper for AnyLoader"""

    def __init__(self, host="127.0.0.1", port=5000, debug=False, arguments=None):
        """
        Initialize the Flask web application.

        Args:
            host: Host to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 5000)
            debug: Enable Flask debug mode (default: False)
            arguments: Command line arguments object
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.arguments = arguments
        self.start_time = time.time()

        # Authentication settings
        self.auth_enabled = (
            getattr(arguments, "enable_web_auth", False) if arguments else False
        )
        self.mobile = (
            getattr(arguments, "mobile", False) if arguments else False
        )
        self.db = UserDatabase() if self.auth_enabled else None

        # Download manager with configurable concurrent downloads
        max_concurrent = getattr(config, "DEFAULT_MAX_CONCURRENT_DOWNLOADS", 3)
        self.download_manager = get_download_manager(self.db, max_concurrent)

        # Chromecast connection cache
        self._chromecast_cache = {}  # {uuid: {'cast': cast_obj, 'browser': browser, 'last_used': timestamp}}
        self._chromecast_cache_lock = threading.Lock()

        # Create Flask app
        self.app = self._create_app()

        # Apply saved preferences at startup
        self._apply_saved_preferences()

        # Ensure FFmpeg is available (download if missing)
        self._ensure_ffmpeg()

        # Scan for manually placed files at startup
        self._scan_media_library()

        # Backfill series metadata for existing download folders (background)
        self._start_metadata_backfill()

        # In-memory store for subscription new-episode notifications
        self._subscription_notifications = []  # list of dicts: {sub_id, title, new_count, detected_at}
        self._subscription_lock = threading.Lock()

        # Start background subscription checker
        self._start_subscription_checker()

        # Setup routes
        self._setup_routes()

    def _create_app(self) -> Flask:
        """Create and configure Flask application."""
        # Get the web module directory
        web_dir = os.path.dirname(os.path.abspath(__file__))

        app = Flask(
            __name__,
            template_folder=os.path.join(web_dir, "templates"),
            static_folder=os.path.join(web_dir, "static"),
        )

        # Configure Flask
        app.config["SECRET_KEY"] = os.urandom(24)
        app.config["JSON_SORT_KEYS"] = False

        return app

    def _apply_saved_preferences(self):
        """Apply saved preferences at startup."""
        try:
            prefs = self._load_preferences()

            # Apply download directory to runtime arguments
            if prefs.get("download_directory"):
                from ..parser import get_arguments
                arguments = get_arguments()
                # Only apply if not overridden by command-line argument
                if not self.arguments or not getattr(self.arguments, "output_dir", None) or \
                   str(getattr(self.arguments, "output_dir", "")) == str(config.DEFAULT_DOWNLOAD_PATH):
                    arguments.output_dir = prefs["download_directory"]
                    logging.info(f"Applied saved download directory: {prefs['download_directory']}")

            # Apply max concurrent downloads
            if prefs.get("max_concurrent_downloads"):
                self.download_manager.max_concurrent_downloads = prefs["max_concurrent_downloads"]
                logging.info(f"Applied saved max concurrent downloads: {prefs['max_concurrent_downloads']}")

            # Apply provider timeout
            if prefs.get("provider_timeout"):
                self.download_manager.provider_timeout = prefs["provider_timeout"]
                logging.info(f"Applied saved provider timeout: {prefs['provider_timeout']}s")

        except Exception as e:
            logging.warning(f"Could not apply saved preferences: {e}")

    def _ensure_ffmpeg(self):
        """Ensure FFmpeg is available, downloading if necessary."""
        from ..ffmpeg_downloader import ensure_ffmpeg
        try:
            result = ensure_ffmpeg()
            if result:
                logging.info("FFmpeg available at: %s", result)
        except Exception as e:
            logging.warning("FFmpeg auto-download failed: %s", e)

    def _get_preferences_file(self) -> Path:
        """Get the path to the preferences file."""
        # Store preferences in the same directory as the database
        if os.name == "nt":  # Windows
            prefs_dir = Path(os.getenv("APPDATA", "")) / "aniworld"
        else:  # Linux/Mac
            prefs_dir = Path.home() / ".local" / "share" / "aniworld"

        prefs_dir.mkdir(parents=True, exist_ok=True)
        return prefs_dir / "preferences.json"

    def _load_preferences(self) -> dict:
        """Load preferences from file or return defaults."""
        import json

        defaults = {
            "max_concurrent_downloads": getattr(config, "DEFAULT_MAX_CONCURRENT_DOWNLOADS", 5),
            "download_directory": str(getattr(config, "DEFAULT_DOWNLOAD_PATH", Path.home() / "Downloads")),
            "default_language": getattr(config, "DEFAULT_LANGUAGE", "German Sub"),
            "default_provider": getattr(config, "DEFAULT_PROVIDER", "VOE"),
            "accent_color": "purple",
            "custom_color": None,
            "animations_enabled": True,
            "provider_timeout": getattr(config, "DEFAULT_PROVIDER_TIMEOUT", 5),
            "plex_enabled": False,
            "plex_token": None,
        }

        # Override download_directory if set via command line
        if self.arguments and hasattr(self.arguments, "output_dir") and self.arguments.output_dir:
            defaults["download_directory"] = str(self.arguments.output_dir)

        prefs_file = self._get_preferences_file()
        if prefs_file.exists():
            try:
                with open(prefs_file, "r") as f:
                    saved_prefs = json.load(f)
                    # Merge saved preferences with defaults
                    defaults.update(saved_prefs)
            except Exception as e:
                logging.error(f"Error loading preferences: {e}")

        return defaults

    def _save_preferences(self, data: dict):
        """Save preferences to file."""
        import json

        # Validate inputs
        if "max_concurrent_downloads" in data:
            val = int(data["max_concurrent_downloads"])
            if val < 1 or val > 10:
                raise ValueError("Parallel downloads must be between 1 and 10")
            data["max_concurrent_downloads"] = val

        if "provider_timeout" in data:
            val = int(data["provider_timeout"])
            data["provider_timeout"] = max(1, min(30, val))

        if "download_directory" in data:
            download_dir = Path(data["download_directory"])
            # Create directory if it doesn't exist
            download_dir.mkdir(parents=True, exist_ok=True)
            data["download_directory"] = str(download_dir)

        # Never save the masked placeholder as the actual token
        if data.get("plex_token") == "********":
            del data["plex_token"]

        # Load existing preferences and merge
        current_prefs = self._load_preferences()
        current_prefs.update(data)

        # Save to file
        prefs_file = self._get_preferences_file()
        with open(prefs_file, "w") as f:
            json.dump(current_prefs, f, indent=2)

        # Update runtime config if applicable
        if "max_concurrent_downloads" in data:
            self.download_manager.max_concurrent_downloads = data["max_concurrent_downloads"]

        if "provider_timeout" in data:
            self.download_manager.provider_timeout = data["provider_timeout"]

        # Update download directory in runtime arguments
        if "download_directory" in data:
            from ..parser import get_arguments
            arguments = get_arguments()
            arguments.output_dir = data["download_directory"]
            logging.info(f"Updated runtime output_dir to: {data['download_directory']}")

        # Log saved preferences (excluding sensitive token)
        safe_log = {k: v for k, v in data.items() if k != "plex_token"}
        logging.info(f"Preferences saved: {safe_log}")

    def _reset_preferences(self):
        """Reset preferences to defaults."""
        prefs_file = self._get_preferences_file()
        if prefs_file.exists():
            prefs_file.unlink()
        logging.info("Preferences reset to defaults")

    def _scan_media_library(self):
        """Scan the download directory for manually placed files at startup."""
        try:
            # Get download directory
            download_path = str(config.DEFAULT_DOWNLOAD_PATH)
            if (
                self.arguments
                and hasattr(self.arguments, "output_dir")
                and self.arguments.output_dir is not None
            ):
                download_path = str(self.arguments.output_dir)

            download_dir = Path(download_path)

            if not download_dir.exists():
                logging.info(f"Media library directory does not exist yet: {download_path}")
                return

            # Scan for video files
            video_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v', '.flv', '.wmv'}

            series_count = 0
            season_count = 0
            episode_count = 0
            total_size = 0

            # Scan directory structure: series/seasonX/episodes
            for series_dir in download_dir.iterdir():
                if series_dir.is_dir():
                    series_count += 1
                    has_seasons = False

                    for item in series_dir.iterdir():
                        if item.is_dir():
                            # Check if it's a season folder
                            folder_name = item.name.lower()
                            if folder_name.startswith('season') or folder_name == 'movies':
                                has_seasons = True
                                season_count += 1

                                # Count episodes in this season
                                for episode_file in item.iterdir():
                                    if episode_file.is_file() and episode_file.suffix.lower() in video_extensions:
                                        episode_count += 1
                                        total_size += episode_file.stat().st_size

                        elif item.is_file() and item.suffix.lower() in video_extensions:
                            # Video file directly in series folder (old structure)
                            episode_count += 1
                            total_size += item.stat().st_size

                    # If no seasons found, check for videos directly in series folder
                    if not has_seasons:
                        for video_file in series_dir.rglob('*'):
                            if video_file.is_file() and video_file.suffix.lower() in video_extensions:
                                if video_file.parent == series_dir:
                                    continue  # Already counted above
                                episode_count += 1
                                total_size += video_file.stat().st_size

            # Format total size
            def format_size(size_bytes):
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if size_bytes < 1024.0:
                        return f"{size_bytes:.1f} {unit}"
                    size_bytes /= 1024.0
                return f"{size_bytes:.1f} PB"

            if episode_count > 0:
                logging.info(
                    f"Media library scan complete: {series_count} series, "
                    f"{season_count} seasons, {episode_count} episodes "
                    f"({format_size(total_size)})"
                )
                print(f" Media Library: {series_count} series, {season_count} seasons, {episode_count} episodes ({format_size(total_size)})")
            else:
                logging.info(f"Media library is empty: {download_path}")

        except Exception as e:
            logging.warning(f"Failed to scan media library: {e}")

    def _start_metadata_backfill(self):
        """Start a background thread to backfill .series_meta.json for existing folders."""
        t = threading.Thread(target=self._backfill_series_metadata, daemon=True)
        t.start()

    def _backfill_series_metadata(self):
        """Scan download folders and create .series_meta.json where missing."""
        try:
            import json as json_mod
            from ..search import fetch_anime_list
            from urllib.parse import quote

            download_path = str(config.DEFAULT_DOWNLOAD_PATH)
            if (
                self.arguments
                and hasattr(self.arguments, "output_dir")
                and self.arguments.output_dir is not None
            ):
                download_path = str(self.arguments.output_dir)

            download_dir = Path(download_path)
            if not download_dir.exists():
                return

            video_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v', '.flv', '.wmv'}
            folders_to_backfill = []

            for item in download_dir.iterdir():
                if not item.is_dir():
                    continue
                meta_file = item / ".series_meta.json"
                if meta_file.exists():
                    # Validate existing metadata has required fields
                    try:
                        meta = json_mod.loads(meta_file.read_text(encoding="utf-8"))
                        if meta.get("url") and meta.get("title"):
                            continue  # Already has valid metadata
                    except Exception:
                        pass  # Invalid JSON, will re-create
                # Check if folder has video files
                has_videos = any(
                    f.is_file() and f.suffix.lower() in video_extensions
                    for f in item.rglob("*")
                )
                if has_videos:
                    folders_to_backfill.append(item)

            if not folders_to_backfill:
                return

            logging.info(
                f"Metadata backfill: {len(folders_to_backfill)} folder(s) without metadata"
            )

            for folder in folders_to_backfill:
                try:
                    folder_name = folder.name
                    best_match = None

                    # Search on aniworld.to
                    try:
                        url = f"{config.ANIWORLD_TO}/ajax/seriesSearch?keyword={quote(folder_name)}"
                        results = fetch_anime_list(url)
                        for r in results:
                            name = r.get("name", "")
                            if name.lower() == folder_name.lower():
                                best_match = {
                                    "url": f"{config.ANIWORLD_TO}/anime/stream/{r.get('link', '')}",
                                    "title": folder_name,
                                    "site": "aniworld.to",
                                    "cover": r.get("cover", ""),
                                }
                                break
                        if not best_match and results:
                            r = results[0]
                            best_match = {
                                "url": f"{config.ANIWORLD_TO}/anime/stream/{r.get('link', '')}",
                                "title": folder_name,
                                "site": "aniworld.to",
                                "cover": r.get("cover", ""),
                            }
                    except Exception as e:
                        logging.debug(f"Backfill aniworld search failed for '{folder_name}': {e}")

                    # Search on s.to if no match found
                    if not best_match:
                        try:
                            from ..search import fetch_sto_search_results
                            results = fetch_sto_search_results(folder_name)
                            for r in results:
                                name = r.get("name", "")
                                if name.lower() == folder_name.lower():
                                    best_match = {
                                        "url": f"{config.S_TO}/serie/{r.get('link', '')}",
                                        "title": folder_name,
                                        "site": "s.to",
                                        "cover": r.get("cover", ""),
                                    }
                                    break
                            if not best_match and results:
                                r = results[0]
                                best_match = {
                                    "url": f"{config.S_TO}/serie/{r.get('link', '')}",
                                    "title": folder_name,
                                    "site": "s.to",
                                    "cover": r.get("cover", ""),
                                }
                        except Exception as e:
                            logging.debug(f"Backfill s.to search failed for '{folder_name}': {e}")

                    if best_match:
                        meta_file = folder / ".series_meta.json"
                        meta_file.write_text(
                            json_mod.dumps(best_match, ensure_ascii=False),
                            encoding="utf-8"
                        )
                        logging.info(
                            f"Backfill: Created metadata for '{folder_name}' -> {best_match['site']}"
                        )
                    else:
                        logging.debug(f"Backfill: No match found for '{folder_name}'")

                except Exception as e:
                    logging.debug(f"Backfill failed for folder '{folder.name}': {e}")

            logging.info("Metadata backfill complete")

        except Exception as e:
            logging.warning(f"Metadata backfill error: {e}")

    def _require_api_auth(self, f):
        """Decorator to require authentication for API routes."""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.auth_enabled:
                return f(*args, **kwargs)

            if not self.db:
                return jsonify({"error": "Authentication database not available"}), 500

            session_token = request.cookies.get("session_token")
            if not session_token:
                return jsonify({"error": "Authentication required"}), 401

            user = self.db.get_user_by_session(session_token)
            if not user:
                return jsonify({"error": "Invalid session"}), 401

            return f(*args, **kwargs)

        return decorated_function

    def _require_auth(self, f):
        """Decorator to require authentication for routes."""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.auth_enabled:
                return f(*args, **kwargs)

            if not self.db:
                return redirect(url_for("login"))

            # Check for session token in cookies
            session_token = request.cookies.get("session_token")
            if not session_token:
                return redirect(url_for("login"))

            user = self.db.get_user_by_session(session_token)
            if not user:
                return redirect(url_for("login"))

            # Store user info in Flask session for templates
            session["user"] = user
            return f(*args, **kwargs)

        return decorated_function

    def _require_admin(self, f):
        """Decorator to require admin privileges for routes."""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.auth_enabled:
                return f(*args, **kwargs)

            if not self.db:
                return jsonify({"error": "Authentication database not available"}), 500

            session_token = request.cookies.get("session_token")
            if not session_token:
                return redirect(url_for("login"))

            user = self.db.get_user_by_session(session_token)
            if not user or not user["is_admin"]:
                return jsonify({"error": "Admin access required"}), 403

            session["user"] = user
            return f(*args, **kwargs)

        return decorated_function

    def _get_cached_chromecast(self, device_uuid, timeout=10):
        """
        Get a Chromecast device from cache or discover it.

        Args:
            device_uuid: The UUID of the Chromecast to find
            timeout: Discovery timeout in seconds (only used on first connection)

        Returns:
            cast object if found, None if not found
        """
        import pychromecast
        from uuid import UUID

        with self._chromecast_cache_lock:
            # Check if we have a cached connection
            if device_uuid in self._chromecast_cache:
                cached = self._chromecast_cache[device_uuid]
                cast = cached['cast']

                # Check if the cast is still connected
                try:
                    # Update last used time
                    cached['last_used'] = time.time()

                    # Try to access the socket to verify connection
                    if cast.socket_client and cast.socket_client.is_connected:
                        return cast
                except Exception:
                    pass

                # Connection is stale, clean it up
                self._cleanup_cached_chromecast(device_uuid)

            # Need to discover the device
            try:
                chromecasts, browser = pychromecast.get_listed_chromecasts(
                    uuids=[UUID(device_uuid)],
                    timeout=timeout
                )

                if chromecasts:
                    cast = chromecasts[0]
                    # Cache the connection
                    self._chromecast_cache[device_uuid] = {
                        'cast': cast,
                        'browser': browser,
                        'last_used': time.time()
                    }
                    return cast

                # No device found, stop the browser
                if browser:
                    browser.stop_discovery()
                return None

            except Exception as e:
                logging.error(f"Failed to discover Chromecast: {e}")
                return None

    def _cleanup_cached_chromecast(self, device_uuid):
        """Clean up a cached Chromecast connection."""
        if device_uuid in self._chromecast_cache:
            cached = self._chromecast_cache[device_uuid]
            try:
                if cached.get('browser'):
                    cached['browser'].stop_discovery()
                if cached.get('cast'):
                    cached['cast'].disconnect()
            except Exception:
                pass
            del self._chromecast_cache[device_uuid]

    def _discover_chromecast_by_uuid(self, device_uuid, timeout=10):
        """
        Discover and return a Chromecast device by UUID.
        Uses caching for faster subsequent access.

        Args:
            device_uuid: The UUID of the Chromecast to find
            timeout: Discovery timeout in seconds

        Returns:
            tuple: (cast, browser) if found, (None, None) if not found
        """
        cast = self._get_cached_chromecast(device_uuid, timeout)
        if cast:
            # Return the cast and None for browser (browser is managed in cache)
            return cast, None
        return None, None

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        @self._require_auth
        def index():
            """Main page route."""
            # Load preferences for the modal
            preferences_data = self._load_preferences()
            # Never expose the actual plex token to templates
            if preferences_data.get("plex_token"):
                preferences_data["plex_token"] = True
            providers = list(config.SUPPORTED_PROVIDERS)

            template = "mobile.html" if self.mobile else "index.html"

            if self.auth_enabled and self.db:
                # Check if this is first-time setup
                if not self.db.has_users():
                    return redirect(url_for("setup"))

                # Get current user info for template
                session_token = request.cookies.get("session_token")
                user = self.db.get_user_by_session(session_token)
                return render_template(template, user=user, auth_enabled=True, preferences=preferences_data, providers=providers)
            else:
                return render_template(template, auth_enabled=False, preferences=preferences_data, providers=providers)

        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            """Login page route."""
            if not self.auth_enabled or not self.db:
                return redirect(url_for("index"))

            # If no users exist, redirect to setup
            if not self.db.has_users():
                return redirect(url_for("setup"))

            if request.method == "POST":
                data = request.get_json()
                username = data.get("username", "").strip()
                password = data.get("password", "")

                if not username or not password:
                    return jsonify(
                        {"success": False, "error": "Username and password required"}
                    ), 400

                user = self.db.verify_user(username, password)
                if user:
                    session_token = self.db.create_session(user["id"])
                    response = jsonify({"success": True, "redirect": url_for("index")})
                    response.set_cookie(
                        "session_token",
                        session_token,
                        httponly=True,
                        secure=False,
                        max_age=30 * 24 * 60 * 60,
                    )
                    return response
                else:
                    return jsonify(
                        {"success": False, "error": "Invalid credentials"}
                    ), 401

            return render_template("login.html")

        @self.app.route("/logout", methods=["POST"])
        def logout():
            """Logout route."""
            if not self.auth_enabled or not self.db:
                return redirect(url_for("index"))

            session_token = request.cookies.get("session_token")
            if session_token:
                self.db.delete_session(session_token)

            response = jsonify({"success": True, "redirect": url_for("login")})
            response.set_cookie("session_token", "", expires=0)
            return response

        @self.app.route("/setup", methods=["GET", "POST"])
        def setup():
            """First-time setup route for creating admin user."""
            if not self.auth_enabled or not self.db:
                return redirect(url_for("index"))

            if self.db.has_users():
                return redirect(url_for("index"))

            if request.method == "POST":
                data = request.get_json()
                username = data.get("username", "").strip()
                password = data.get("password", "")

                if not username or not password:
                    return jsonify(
                        {"success": False, "error": "Username and password required"}
                    ), 400

                if len(password) < 6:
                    return jsonify(
                        {
                            "success": False,
                            "error": "Password must be at least 6 characters",
                        }
                    ), 400

                if self.db.create_user(
                    username, password, is_admin=True, is_original_admin=True
                ):
                    return jsonify(
                        {
                            "success": True,
                            "message": "Admin user created successfully",
                            "redirect": url_for("login"),
                        }
                    )
                else:
                    return jsonify(
                        {"success": False, "error": "Failed to create user"}
                    ), 500

            return render_template("setup.html")

        @self.app.route("/settings")
        @self._require_auth
        def settings():
            """Settings page route."""
            if not self.auth_enabled or not self.db:
                return redirect(url_for("index"))

            session_token = request.cookies.get("session_token")
            user = self.db.get_user_by_session(session_token)
            users = self.db.get_all_users() if user and user["is_admin"] else []

            return render_template("settings.html", user=user, users=users)

        @self.app.route("/preferences")
        def preferences():
            """Preferences page route."""
            # Get current user if auth is enabled
            user = None
            if self.auth_enabled and self.db:
                session_token = request.cookies.get("session_token")
                user = self.db.get_user_by_session(session_token)

            # Load current preferences
            preferences_data = self._load_preferences()
            # Never expose the actual plex token to templates
            if preferences_data.get("plex_token"):
                preferences_data["plex_token"] = True  # truthy for template check
            # Get list of providers
            providers = list(config.SUPPORTED_PROVIDERS)

            return render_template(
                "preferences.html",
                auth_enabled=self.auth_enabled,
                user=user,
                preferences=preferences_data,
                providers=providers,
                log_file_path=config.log_file_path
            )

        @self.app.route("/api/preferences/modal")
        def api_preferences_modal():
            """Get preferences modal HTML."""
            # Load current preferences
            preferences_data = self._load_preferences()
            # Never expose the actual plex token to templates
            if preferences_data.get("plex_token"):
                preferences_data["plex_token"] = True

            # Get list of providers
            providers = list(config.SUPPORTED_PROVIDERS)

            return render_template(
                "preferences_modal.html",
                preferences=preferences_data,
                providers=providers,
                log_file_path=config.log_file_path
            )

        @self.app.route("/api/preferences", methods=["GET"])
        def api_get_preferences():
            """Get current preferences."""
            preferences_data = self._load_preferences()
            # Never expose the actual plex token to the frontend
            if preferences_data.get("plex_token"):
                preferences_data["plex_token"] = "********"
            return jsonify({"success": True, "preferences": preferences_data})

        @self.app.route("/api/preferences", methods=["POST"])
        def api_save_preferences():
            """Save preferences."""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"success": False, "error": "No data provided"}), 400

                # Validate and save preferences
                self._save_preferences(data)

                return jsonify({"success": True, "message": "Preferences saved successfully"})
            except Exception as e:
                logging.error(f"Error saving preferences: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/preferences/reset", methods=["POST"])
        def api_reset_preferences():
            """Reset preferences to defaults."""
            try:
                self._reset_preferences()
                return jsonify({"success": True, "message": "Preferences reset to defaults"})
            except Exception as e:
                logging.error(f"Error resetting preferences: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/logs")
        @self._require_api_auth
        def api_logs():
            """Get application log content (last 200 lines)."""
            try:
                log_path = config.log_file_path
                if not os.path.exists(log_path):
                    return jsonify({"success": True, "content": "(log file not found)", "path": log_path})

                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()

                # Return last 200 lines
                tail_lines = lines[-200:] if len(lines) > 200 else lines
                content = "".join(tail_lines)

                return jsonify({"success": True, "content": content, "path": log_path})
            except Exception as e:
                logging.error("Error reading log file: %s", e)
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/plex/auth/pin", methods=["POST"])
        @self._require_api_auth
        def api_plex_auth_pin():
            """Create a Plex OAuth PIN for authentication."""
            try:
                import requests as req
                import uuid

                # Generate a stable client identifier (per installation)
                prefs = self._load_preferences()
                client_id = prefs.get("plex_client_id")
                if not client_id:
                    client_id = str(uuid.uuid4())
                    self._save_preferences({"plex_client_id": client_id})

                headers = {
                    "Accept": "application/json",
                    "X-Plex-Product": "AnyLoader",
                    "X-Plex-Client-Identifier": client_id,
                }

                response = req.post(
                    "https://plex.tv/api/v2/pins",
                    headers=headers,
                    data={"strong": "true"},
                    timeout=10,
                )
                response.raise_for_status()
                pin_data = response.json()

                pin_id = pin_data.get("id")
                pin_code = pin_data.get("code")

                if not pin_id or not pin_code:
                    return jsonify({"success": False, "error": "Failed to create Plex PIN"}), 500

                # Build the OAuth URL
                from urllib.parse import urlencode
                oauth_params = urlencode({
                    "clientID": client_id,
                    "code": pin_code,
                    "context[device][product]": "AnyLoader",
                })
                oauth_url = f"https://app.plex.tv/auth#?{oauth_params}"

                return jsonify({
                    "success": True,
                    "pin_id": pin_id,
                    "pin_code": pin_code,
                    "oauth_url": oauth_url,
                    "client_id": client_id,
                })

            except Exception as e:
                logging.error(f"Plex PIN creation error: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/plex/auth/check/<int:pin_id>", methods=["GET"])
        @self._require_api_auth
        def api_plex_auth_check(pin_id):
            """Poll a Plex PIN to check if the user has authenticated."""
            try:
                import requests as req

                prefs = self._load_preferences()
                client_id = prefs.get("plex_client_id", "")

                headers = {
                    "Accept": "application/json",
                    "X-Plex-Client-Identifier": client_id,
                }

                response = req.get(
                    f"https://plex.tv/api/v2/pins/{pin_id}",
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                pin_data = response.json()

                auth_token = pin_data.get("authToken")

                if auth_token:
                    # Save the token automatically
                    self._save_preferences({
                        "plex_token": auth_token,
                        "plex_enabled": True,
                    })
                    return jsonify({"success": True, "authenticated": True})
                else:
                    return jsonify({"success": True, "authenticated": False})

            except Exception as e:
                logging.error(f"Plex PIN check error: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/plex/watchlist", methods=["GET"])
        @self._require_api_auth
        def api_plex_watchlist():
            """Fetch the user's Plex watchlist."""
            try:
                import requests as req

                prefs = self._load_preferences()
                if not prefs.get("plex_enabled"):
                    return jsonify({"success": False, "error": "Plex integration is not enabled"}), 400

                plex_token = prefs.get("plex_token")
                if not plex_token:
                    return jsonify({"success": False, "error": "No Plex token configured"}), 400

                headers = {
                    "X-Plex-Token": plex_token,
                    "Accept": "application/json",
                }

                response = req.get(
                    "https://discover.provider.plex.tv/library/sections/watchlist/all",
                    headers=headers,
                    params={
                        "sort": "watchlistedAt:desc",
                        "includeCollections": "0",
                        "includeExternalMedia": "1",
                        "X-Plex-Container-Size": "100",
                    },
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()

                items = []
                media_container = data.get("MediaContainer", {})
                metadata_list = media_container.get("Metadata", [])

                for item in metadata_list:
                    items.append({
                        "ratingKey": item.get("ratingKey", ""),
                        "title": item.get("title", "Unknown"),
                        "type": item.get("type", "unknown"),
                        "year": item.get("year"),
                        "thumb": item.get("thumb", ""),
                    })

                return jsonify({"success": True, "items": items})

            except req.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    return jsonify({"success": False, "error": "Invalid Plex token. Please check your token in Preferences."}), 401
                logging.error(f"Plex API HTTP error: {e}")
                return jsonify({"success": False, "error": f"Plex API error: {str(e)}"}), 500
            except req.exceptions.RequestException as e:
                logging.error(f"Plex API request error: {e}")
                return jsonify({"success": False, "error": f"Failed to connect to Plex: {str(e)}"}), 500
            except Exception as e:
                logging.error(f"Plex watchlist error: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/plex/search-and-download", methods=["POST"])
        @self._require_api_auth
        def api_plex_search_and_download():
            """Search for a Plex watchlist title across all sites and return results."""
            try:
                from flask import request as flask_request
                from ..search import fetch_anime_list
                from urllib.parse import quote

                data = flask_request.get_json()
                if not data or "title" not in data:
                    return jsonify({"success": False, "error": "Title is required"}), 400

                title = data["title"].strip()
                if not title:
                    return jsonify({"success": False, "error": "Title cannot be empty"}), 400

                # Search across all sites
                all_results = []
                seen_slugs = set()

                # Search aniworld.to
                try:
                    url = f"{config.ANIWORLD_TO}/ajax/seriesSearch?keyword={quote(title)}"
                    results = fetch_anime_list(url)
                    for anime in results:
                        slug = anime.get("link", "")
                        if slug and slug not in seen_slugs:
                            anime["site"] = "aniworld.to"
                            anime["base_url"] = config.ANIWORLD_TO
                            anime["stream_path"] = "anime/stream"
                            all_results.append(anime)
                            seen_slugs.add(slug)
                except Exception as e:
                    logging.warning(f"Plex search - aniworld failed: {e}")

                # Search s.to
                try:
                    from ..search import fetch_sto_search_results
                    results = fetch_sto_search_results(title)
                    for anime in results:
                        slug = anime.get("link", "")
                        if slug and slug not in seen_slugs:
                            anime["site"] = "s.to"
                            anime["base_url"] = config.S_TO
                            anime["stream_path"] = "serie"
                            all_results.append(anime)
                            seen_slugs.add(slug)
                except Exception as e:
                    logging.warning(f"Plex search - s.to failed: {e}")

                # Process results
                processed = []
                for anime in all_results[:20]:
                    link = anime.get("link", "")
                    anime_base_url = anime.get("base_url", config.ANIWORLD_TO)
                    anime_stream_path = anime.get("stream_path", "anime/stream")

                    if link and not link.startswith("http"):
                        full_url = f"{anime_base_url}/{anime_stream_path}/{link}"
                    else:
                        full_url = link

                    name = anime.get("name", "Unknown")
                    cover = anime.get("cover", anime.get("image", ""))

                    processed.append({
                        "title": name,
                        "url": full_url,
                        "cover": cover,
                        "site": anime.get("site", "aniworld.to"),
                    })

                return jsonify({"success": True, "results": processed})

            except Exception as e:
                logging.error(f"Plex search error: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/browse-folder", methods=["POST"])
        def api_browse_folder():
            """Open native folder picker dialog and return selected path."""
            try:
                import tkinter as tk
                from tkinter import filedialog

                # Get initial directory from request or use current preference
                data = request.get_json() or {}
                initial_dir = data.get("initial_dir", "")

                if not initial_dir or not Path(initial_dir).exists():
                    # Use current preference or default
                    prefs = self._load_preferences()
                    initial_dir = prefs.get("download_directory", str(Path.home() / "Downloads"))

                # Create hidden root window
                root = tk.Tk()
                root.withdraw()  # Hide the root window
                root.attributes("-topmost", True)  # Bring dialog to front

                # Open folder picker dialog
                selected_folder = filedialog.askdirectory(
                    initialdir=initial_dir,
                    title="Select Download Directory"
                )

                root.destroy()  # Clean up

                if selected_folder:
                    return jsonify({"success": True, "path": selected_folder})
                else:
                    return jsonify({"success": False, "error": "No folder selected"})

            except ImportError:
                logging.error("tkinter not available for folder picker")
                return jsonify({
                    "success": False,
                    "error": "Folder picker not available. Please enter the path manually."
                }), 500
            except Exception as e:
                logging.error(f"Error opening folder picker: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        # User management API routes
        @self.app.route("/api/users", methods=["GET"])
        @self._require_admin
        def api_get_users():
            """Get all users (admin only)."""
            if not self.db:
                return jsonify(
                    {"success": False, "error": "Authentication not available"}
                ), 500
            users = self.db.get_all_users()
            return jsonify({"success": True, "users": users})

        @self.app.route("/api/users", methods=["POST"])
        @self._require_admin
        def api_create_user():
            """Create new user (admin only)."""
            data = request.get_json()

            if not data:
                return jsonify(
                    {"success": False, "error": "No JSON data received"}
                ), 400

            # Debug logging
            logging.debug(f"Received data: {data}")

            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            is_admin = data.get("is_admin", False)

            # Debug logging
            logging.debug(
                f"Processed - username: '{username}', password: 'XXX', is_admin: {is_admin}"
            )

            if not username or not password:
                return jsonify(
                    {
                        "success": False,
                        "error": f'Username and password required. Got username: "{username}", password: "{password}"',
                    }
                ), 400

            if len(password) < 6:
                return jsonify(
                    {
                        "success": False,
                        "error": "Password must be at least 6 characters",
                    }
                ), 400

            if not self.db:
                return jsonify(
                    {"success": False, "error": "Authentication not available"}
                ), 500

            if self.db.create_user(username, password, is_admin):
                return jsonify(
                    {"success": True, "message": "User created successfully"}
                )
            else:
                return jsonify(
                    {
                        "success": False,
                        "error": "Failed to create user (username may already exist)",
                    }
                ), 400

        @self.app.route("/api/users/<int:user_id>", methods=["DELETE"])
        @self._require_admin
        def api_delete_user(user_id):
            """Delete user (admin only)."""
            if not self.db:
                return jsonify(
                    {"success": False, "error": "Authentication not available"}
                ), 500

            # Get user info to check if it's the original admin
            users = self.db.get_all_users()
            user_to_delete = next((u for u in users if u["id"] == user_id), None)

            if user_to_delete and user_to_delete.get("is_original_admin"):
                return jsonify(
                    {"success": False, "error": "Cannot delete the original admin user"}
                ), 400

            if self.db.delete_user(user_id):
                return jsonify(
                    {"success": True, "message": "User deleted successfully"}
                )
            else:
                return jsonify(
                    {"success": False, "error": "Failed to delete user"}
                ), 400

        @self.app.route("/api/users/<int:user_id>", methods=["PUT"])
        @self._require_admin
        def api_update_user(user_id):
            """Update user (admin only)."""
            data = request.get_json()
            username = (
                data.get("username", "").strip() if data.get("username") else None
            )
            password = data.get("password", "") if data.get("password") else None
            is_admin = data.get("is_admin") if "is_admin" in data else None

            if password and len(password) < 6:
                return jsonify(
                    {
                        "success": False,
                        "error": "Password must be at least 6 characters",
                    }
                ), 400

            if not self.db:
                return jsonify(
                    {"success": False, "error": "Authentication not available"}
                ), 500

            if self.db.update_user(user_id, username, password, is_admin):
                return jsonify(
                    {"success": True, "message": "User updated successfully"}
                )
            else:
                return jsonify(
                    {"success": False, "error": "Failed to update user"}
                ), 400

        @self.app.route("/api/change-password", methods=["POST"])
        @self._require_api_auth
        def api_change_password():
            """Change user password."""
            if not self.auth_enabled or not self.db:
                return jsonify(
                    {"success": False, "error": "Authentication not enabled"}
                ), 400

            session_token = request.cookies.get("session_token")
            user = self.db.get_user_by_session(session_token)
            if not user:
                return jsonify({"success": False, "error": "Invalid session"}), 401

            data = request.get_json()
            current_password = data.get("current_password", "")
            new_password = data.get("new_password", "")

            if not current_password or not new_password:
                return jsonify(
                    {
                        "success": False,
                        "error": "Current and new passwords are required",
                    }
                ), 400

            if len(new_password) < 6:
                return jsonify(
                    {
                        "success": False,
                        "error": "New password must be at least 6 characters",
                    }
                ), 400

            if self.db.change_password(user["id"], current_password, new_password):
                return jsonify(
                    {"success": True, "message": "Password changed successfully"}
                )
            else:
                return jsonify(
                    {
                        "success": False,
                        "error": "Failed to change password. Current password may be incorrect.",
                    }
                ), 400

        @self.app.route("/api/test")
        @self._require_api_auth
        def api_test():
            """API test endpoint."""
            return jsonify(
                {
                    "status": "success",
                    "message": "Connection test successful",
                    "timestamp": datetime.now().isoformat(),
                    "version": config.VERSION,
                }
            )

        @self.app.route("/api/info")
        @self._require_api_auth
        def api_info():
            """API info endpoint."""
            uptime_seconds = int(time.time() - self.start_time)
            uptime_str = self._format_uptime(uptime_seconds)

            # Convert latest_version to string if it's a Version object
            latest_version = getattr(config, "LATEST_VERSION", None)
            if latest_version is not None:
                latest_version = str(latest_version)

            return jsonify(
                {
                    "version": config.VERSION,
                    "status": "running",
                    "uptime": uptime_str,
                    "latest_version": latest_version,
                    "is_newest": getattr(config, "IS_NEWEST_VERSION", True),
                    "supported_providers": list(config.SUPPORTED_PROVIDERS),
                    "platform": config.PLATFORM_SYSTEM,
                }
            )

        @self.app.route("/health")
        def health():
            """Health check endpoint."""
            return jsonify(
                {"status": "healthy", "timestamp": datetime.now().isoformat()}
            )

        @self.app.route("/api/search", methods=["POST"])
        @self._require_api_auth
        def api_search():
            """Search for anime endpoint."""
            try:
                from flask import request

                data = request.get_json()
                if not data or "query" not in data:
                    return jsonify(
                        {"success": False, "error": "Query parameter is required"}
                    ), 400

                query = data["query"].strip()
                if not query:
                    return jsonify(
                        {"success": False, "error": "Query cannot be empty"}
                    ), 400

                # Support both old "site" param and new "sites" array
                sites = data.get("sites", None)
                if sites is None:
                    old_site = data.get("site", "both")
                    if old_site == "both":
                        sites = ["aniworld.to", "s.to"]
                    else:
                        sites = [old_site]

                def search_multi_sites(keyword, sites):
                    """Search across multiple sites."""
                    from ..search import fetch_anime_list
                    from .. import config
                    from urllib.parse import quote

                    all_results = []
                    seen_slugs = set()

                    if "aniworld.to" in sites:
                        try:
                            url = f"{config.ANIWORLD_TO}/ajax/seriesSearch?keyword={quote(keyword)}"
                            results = fetch_anime_list(url)
                            for anime in results:
                                slug = anime.get("link", "")
                                if slug and slug not in seen_slugs:
                                    anime["site"] = "aniworld.to"
                                    anime["base_url"] = config.ANIWORLD_TO
                                    anime["stream_path"] = "anime/stream"
                                    all_results.append(anime)
                                    seen_slugs.add(slug)
                        except Exception as e:
                            logging.warning(f"Failed to fetch from aniworld: {e}")

                    if "s.to" in sites:
                        try:
                            from ..search import fetch_sto_search_results
                            results = fetch_sto_search_results(keyword)
                            for anime in results:
                                slug = anime.get("link", "")
                                if slug and slug not in seen_slugs:
                                    anime["site"] = "s.to"
                                    anime["base_url"] = config.S_TO
                                    anime["stream_path"] = "serie"
                                    all_results.append(anime)
                                    seen_slugs.add(slug)
                        except Exception as e:
                            logging.warning(f"Failed to fetch from s.to: {e}")

                    if "movie4k.sx" in sites:
                        try:
                            from ..sites.movie4k import fetch_movie4k_search_results
                            movie_results = fetch_movie4k_search_results(keyword)
                            for movie in movie_results:
                                link = movie.get("link", "")
                                if link and link not in seen_slugs:
                                    # Mark movie entries so the frontend can treat them specially
                                    movie["site"] = "movie4k.sx"
                                    movie["base_url"] = config.MOVIE4K_SX
                                    movie["stream_path"] = "watch"
                                    movie["type"] = "movie"
                                    movie["is_movie"] = True
                                    all_results.append(movie)
                                    seen_slugs.add(link)
                        except Exception as e:
                            logging.warning(f"Failed to fetch from movie4k.sx: {e}")

                    return all_results

                results = search_multi_sites(query, sites)

                # Process results
                processed_results = []
                for anime in results[:50]:
                    link = anime.get("link", "")
                    anime_site = anime.get("site", "aniworld.to")
                    anime_base_url = anime.get("base_url", config.ANIWORLD_TO)
                    anime_stream_path = anime.get("stream_path", "anime/stream")

                    if link and not link.startswith("http"):
                        full_url = f"{anime_base_url}/{anime_stream_path}/{link}"
                    else:
                        full_url = link

                    name = anime.get("name", "Unknown Name")
                    year = anime.get("productionYear", "Unknown Year")

                    if year and year != "Unknown Year" and str(year) not in name:
                        title = f"{name} {year}"
                    else:
                        title = name

                    # Determine a proper slug for movies (use the slug part, not the movie id)
                    if anime_site == "movie4k.sx" and full_url and "/watch/" in full_url:
                        try:
                            parts = full_url.rstrip("/").split("/")
                            # expected: ... /watch/{slug}/{id}
                            slug_val = parts[-2] if len(parts) >= 2 else link
                        except Exception:
                            slug_val = link
                    else:
                        slug_val = link if not link.startswith("http") else link.split("/")[-1]

                    processed_anime = {
                        "title": title,
                        "url": full_url,
                        "description": anime.get("description", ""),
                        "slug": slug_val,
                        "name": name,
                        "year": year,
                        "site": anime_site,
                        "cover": anime.get("cover", ""),
                        # Propagate type information so the UI can render movies differently
                        "type": anime.get("type", "series"),
                        "is_movie": bool(anime.get("is_movie", False)),
                    }

                    processed_results.append(processed_anime)

                return jsonify(
                    {
                        "success": True,
                        "results": processed_results,
                        "count": len(processed_results),
                    }
                )

            except Exception as err:
                logging.error(f"Search error: {err}")
                return jsonify(
                    {"success": False, "error": f"Search failed: {str(err)}"}
                ), 500

        @self.app.route("/api/direct", methods=["POST"])
        @self._require_api_auth
        def api_direct():
            """Handle direct URL input endpoint."""
            try:
                from flask import request
                from urllib.parse import urlparse
                from .. import config

                data = request.get_json()
                if not data or "url" not in data:
                    return jsonify(
                        {"success": False, "error": "URL parameter is required"}
                    ), 400

                url = data["url"].strip()
                if not url:
                    return jsonify(
                        {"success": False, "error": "URL cannot be empty"}
                    ), 400

                # Validate and parse the URL
                try:
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()

                    # Check if URL is from a supported site
                    is_movie4k = "movie4k" in domain
                    is_sto = "s.to" in domain
                    is_aniworld = "aniworld.to" in domain

                    if not is_movie4k and not is_sto and not is_aniworld:
                        return jsonify(
                            {
                                "success": False,
                                "error": "URL must be from aniworld.to, s.to, or movie4k.sx",
                            }
                        ), 400

                    # Handle movie4k.sx direct URLs via API
                    if is_movie4k:
                        path_parts = [p for p in parsed_url.path.split("/") if p]
                        # Expected: /watch/{slug}/{movie_id}
                        if len(path_parts) >= 3 and path_parts[0] == "watch":
                            slug = path_parts[1]
                            movie_id = path_parts[2]
                        else:
                            return jsonify(
                                {"success": False, "error": "Invalid movie4k.sx URL format"}
                            ), 400

                        try:
                            import requests as req
                            api_url = f"{config.MOVIE4K_SX}/data/watch/?_id={movie_id}"
                            resp = req.get(
                                api_url,
                                timeout=config.DEFAULT_REQUEST_TIMEOUT,
                                headers={
                                    "User-Agent": config.RANDOM_USER_AGENT,
                                    "Accept": "application/json",
                                },
                            )
                            resp.raise_for_status()
                            movie_data = resp.json()

                            title = movie_data.get("title", slug.replace("-", " ").title())
                            year = movie_data.get("year", "")
                            if year and str(year) not in title:
                                display_title = f"{title} ({year})"
                            else:
                                display_title = title

                            poster = movie_data.get("poster_path", "")
                            cover = f"https://image.tmdb.org/t/p/w220_and_h330_face{poster}" if poster else ""

                            anime_result = {
                                "title": display_title,
                                "url": url,
                                "slug": slug,
                                "site": "movie4k.sx",
                                "description": movie_data.get("storyline", movie_data.get("overview", "")),
                                "cover": cover,
                            }
                        except Exception as movie_err:
                            logging.warning(f"Failed to fetch movie4k.sx details: {movie_err}")
                            anime_result = {
                                "title": slug.replace("-", " ").title(),
                                "url": url,
                                "slug": slug,
                                "site": "movie4k.sx",
                                "description": "",
                                "cover": "",
                            }

                        return jsonify(
                            {
                                "success": True,
                                "result": anime_result,
                                "source": "direct_url",
                            }
                        )

                    # Determine site and stream path for aniworld/s.to
                    if is_sto:
                        site = "s.to"
                        base_url = config.S_TO
                        stream_path = "serie"
                    else:
                        site = "aniworld.to"
                        base_url = config.ANIWORLD_TO
                        stream_path = "anime/stream"

                    # Extract slug from URL (last part of path)
                    path_parts = [p for p in parsed_url.path.split("/") if p]
                    if not path_parts:
                        return jsonify(
                            {"success": False, "error": "Invalid URL format"}
                        ), 400

                    slug = path_parts[-1]

                    # Use search functionality to get the full anime details
                    from ..search import fetch_anime_list

                    try:
                        search_query = slug.replace("-", " ")

                        if site == "s.to":
                            from ..search import fetch_sto_search_results
                            search_results = fetch_sto_search_results(search_query)
                        else:
                            search_url = f"{config.ANIWORLD_TO}/ajax/seriesSearch?keyword={search_query}"
                            search_results = fetch_anime_list(search_url)

                        matching_anime = None
                        for anime in search_results:
                            if anime.get("link", "").strip() == slug:
                                matching_anime = anime
                                break

                        if matching_anime:
                            name = matching_anime.get("name", slug.replace("-", " ").title())
                            year = matching_anime.get("productionYear", "")

                            if year and year != "Unknown Year" and str(year) not in name:
                                title = f"{name} {year}"
                            else:
                                title = name

                            anime_result = {
                                "title": title,
                                "url": url,
                                "slug": slug,
                                "site": site,
                                "description": matching_anime.get("description", ""),
                                "cover": matching_anime.get("cover", ""),
                            }
                        else:
                            anime_result = {
                                "title": slug.replace("-", " ").title(),
                                "url": url,
                                "slug": slug,
                                "site": site,
                                "description": "",
                                "cover": "",
                            }

                        return jsonify(
                            {
                                "success": True,
                                "result": anime_result,
                                "source": "direct_url",
                            }
                        )

                    except Exception as search_err:
                        logging.warning(f"Failed to fetch details from search for direct URL: {search_err}")
                        anime_result = {
                            "title": slug.replace("-", " ").title(),
                            "url": url,
                            "slug": slug,
                            "site": site,
                            "description": "",
                            "cover": "",
                        }
                        return jsonify(
                            {
                                "success": True,
                                "result": anime_result,
                                "source": "direct_url",
                            }
                        )

                except Exception as url_err:
                    logging.error(f"URL parsing error: {url_err}")
                    return jsonify(
                        {"success": False, "error": f"Invalid URL: {str(url_err)}"}
                    ), 400

            except Exception as err:
                logging.error(f"Direct URL error: {err}")
                return jsonify(
                    {"success": False, "error": f"Failed to process URL: {str(err)}"}
                ), 500

        @self.app.route("/api/download", methods=["POST"])
        @self._require_api_auth
        def api_download():
            """Start download endpoint."""
            try:
                from flask import request

                data = request.get_json()

                # Check for both single episode (legacy) and multiple episodes (new)
                episode_urls = data.get("episode_urls", [])
                single_episode_url = data.get("episode_url")

                if single_episode_url:
                    episode_urls = [single_episode_url]

                if not episode_urls:
                    return jsonify(
                        {"success": False, "error": "Episode URL(s) required"}
                    ), 400

                language = data.get("language", "German Sub")
                provider = data.get("provider", "VOE")

                # DEBUG: Log received parameters
                logging.debug(
                    f"WEB API RECEIVED - Language: '{language}', Provider: '{provider}'"
                )
                logging.debug(f"WEB API RECEIVED - Request data: {data}")

                # Get current user for queue tracking
                current_user = None
                if self.auth_enabled and self.db:
                    session_token = request.cookies.get("session_token")
                    current_user = self.db.get_user_by_session(session_token)

                # Determine anime title
                anime_title = data.get("anime_title", "Unknown Anime")

                # Calculate total episodes by checking episode URLs
                from ..entry import _group_episodes_by_series

                try:
                    anime_list = _group_episodes_by_series(episode_urls)
                    total_episodes = sum(
                        len(anime.episode_list) for anime in anime_list
                    )
                except Exception as e:
                    logging.error(f"Failed to process episode URLs: {e}")
                    return jsonify(
                        {
                            "success": False,
                            "error": "No valid anime objects could be created from provided URLs",
                        }
                    ), 400

                if total_episodes == 0:
                    return jsonify(
                        {
                            "success": False,
                            "error": "No valid anime objects could be created from provided URLs",
                        }
                    ), 400

                # Add to download queue (creates separate job per episode)
                queue_ids = self.download_manager.add_download(
                    anime_title=anime_title,
                    episode_urls=episode_urls,
                    language=language,
                    provider=provider,
                    total_episodes=total_episodes,
                    created_by=current_user["id"] if current_user else None,
                )

                if not queue_ids:
                    return jsonify(
                        {"success": False, "error": "Failed to add download to queue"}
                    ), 500

                # Save series metadata for file browser
                try:
                    import json as json_mod
                    download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                    if (
                        self.arguments
                        and hasattr(self.arguments, "output_dir")
                        and self.arguments.output_dir is not None
                    ):
                        download_path = str(self.arguments.output_dir)

                    # Determine series base URL from first episode URL
                    first_url = episode_urls[0]
                    if "/staffel-" in first_url:
                        series_base_url = first_url.rsplit("/staffel-", 1)[0]
                    elif "/filme/" in first_url:
                        series_base_url = first_url.rsplit("/filme/", 1)[0]
                    else:
                        series_base_url = first_url

                    # Determine site
                    meta_site = "aniworld.to"
                    if "s.to" in first_url or "/serie/" in first_url:
                        meta_site = "s.to"
                    elif "movie4k" in first_url or "/watch/" in first_url:
                        meta_site = "movie4k.sx"

                    meta = {
                        "url": series_base_url,
                        "title": anime_title,
                        "site": meta_site,
                        "cover": data.get("cover", ""),
                    }
                    from ..action.common import sanitize_filename
                    meta_path = Path(download_path) / sanitize_filename(anime_title) / ".series_meta.json"
                    meta_path.parent.mkdir(parents=True, exist_ok=True)
                    meta_path.write_text(json_mod.dumps(meta, ensure_ascii=False), encoding="utf-8")

                    # Download and save cover image locally
                    cover_url = data.get("cover", "")
                    if cover_url:
                        self._download_cover_image(cover_url, meta_site, meta_path.parent)
                except Exception as meta_err:
                    logging.warning("Failed to save series metadata: %s", meta_err)

                return jsonify(
                    {
                        "success": True,
                        "message": f"Download added to queue: {total_episodes} episode(s) will download in parallel",
                        "episode_count": total_episodes,
                        "language": language,
                        "provider": provider,
                        "queue_ids": queue_ids,
                        "max_concurrent": getattr(config, "DEFAULT_MAX_CONCURRENT_DOWNLOADS", 3),
                    }
                )

            except Exception as err:
                logging.error(f"Download error: {err}")
                return jsonify(
                    {"success": False, "error": f"Failed to start download: {str(err)}"}
                ), 500

        @self.app.route("/api/download-path")
        @self._require_api_auth
        def api_download_path():
            """Get download path endpoint."""
            try:
                # Use arguments.output_dir if available, otherwise fall back to default
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                return jsonify({"path": download_path})
            except Exception as err:
                logging.error(f"Failed to get download path: {err}")
                return jsonify({"path": str(config.DEFAULT_DOWNLOAD_PATH)}), 500

        @self.app.route("/api/episodes", methods=["POST"])
        @self._require_api_auth
        def api_episodes():
            """Get episodes for a series endpoint."""
            try:
                from flask import request

                data = request.get_json()
                if not data or "series_url" not in data:
                    return jsonify(
                        {"success": False, "error": "Series URL is required"}
                    ), 400

                series_url = data["series_url"]
                folder_path = data.get("folder_path", "")

                # Create wrapper function to handle all logic
                def get_episodes_for_series(series_url):
                    """Wrapper function using existing functions to get episodes and movies"""
                    from ..common import (
                        get_season_episode_count,
                        get_movie_episode_count,
                        get_episode_titles,
                    )
                    from ..entry import _detect_site_from_url
                    from .. import config

                    # Extract slug and site using existing functions
                    _site = _detect_site_from_url(series_url)

                    if "/anime/stream/" in series_url:
                        slug = series_url.split("/anime/stream/")[-1].rstrip("/")
                        stream_path = "anime/stream"
                        base_url = config.ANIWORLD_TO
                    elif "/serie/" in series_url:
                        slug = series_url.split("/serie/")[-1].rstrip("/")
                        stream_path = "serie"
                        base_url = config.S_TO
                    else:
                        # Special-case movie URLs (movie4k.sx uses /watch/{slug}/{id})
                        from ..sites.movie4k import Movie as Movie4kMovie
                        if "/watch/" in series_url or "movie4k.sx" in series_url:
                            # Use Movie wrapper to get title and provide as a single movie entry
                            movie_description = ""
                            try:
                                movie_obj = Movie4kMovie(url=series_url)
                                movie_title = movie_obj.title
                                movie_description = movie_obj.overview or ""
                            except Exception:
                                movie_title = "Movie"
                            # No seasons/episodes for movies; return a movies list with single item
                            return {}, [{"movie": 1, "title": movie_title, "url": series_url}], series_url, movie_description

                        raise ValueError("Invalid series URL format")

                    # Use existing function to get season/episode counts
                    season_counts = get_season_episode_count(slug, base_url)

                    # Fetch episode titles from season pages
                    try:
                        episode_titles = get_episode_titles(slug, base_url)
                    except Exception as e:
                        logging.warning(
                            "Failed to fetch episode titles for %s: %s",
                            slug, e
                        )
                        episode_titles = {}

                    # Build episodes structure
                    episodes_by_season = {}
                    for season_num, episode_count in season_counts.items():
                        if episode_count > 0:
                            season_titles = episode_titles.get(season_num, {})
                            episodes_by_season[season_num] = []
                            for ep_num in range(1, episode_count + 1):
                                title = season_titles.get(
                                    ep_num, f"Episode {ep_num}"
                                )
                                episodes_by_season[season_num].append(
                                    {
                                        "season": season_num,
                                        "episode": ep_num,
                                        "title": title,
                                        "url": f"{base_url}/{stream_path}/{slug}/staffel-{season_num}/episode-{ep_num}",
                                    }
                                )

                    # Get movies for aniworld.to and s.to
                    movies = []
                    if base_url in (config.ANIWORLD_TO, config.S_TO):
                        try:
                            movie_count = get_movie_episode_count(slug, link=base_url)
                            for movie_num in range(1, movie_count + 1):
                                movies.append(
                                    {
                                        "movie": movie_num,
                                        "title": f"Movie {movie_num}",
                                        "url": f"{base_url}/{stream_path}/{slug}/filme/film-{movie_num}",
                                    }
                                )
                        except Exception as e:
                            logging.warning(
                                f"Failed to get movie count for {slug}: {e}"
                            )

                    # Fallback if no seasons found
                    if not episodes_by_season:
                        episodes_by_season[1] = [
                            {
                                "season": 1,
                                "episode": 1,
                                "title": "Episode 1",
                                "url": f"{base_url}/{stream_path}/{slug}/staffel-1/episode-1",
                            }
                        ]

                    # Fetch description from series page
                    series_description = ""
                    try:
                        import requests as req_lib
                        series_page_url = f"{base_url}/{stream_path}/{slug}"
                        resp = req_lib.get(
                            series_page_url,
                            timeout=config.DEFAULT_REQUEST_TIMEOUT,
                            headers={"User-Agent": config.RANDOM_USER_AGENT},
                        )
                        if resp.ok:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(resp.content, "html.parser")
                            desc_el = soup.find("p", class_="seri_des")
                            if not desc_el:
                                desc_el = soup.find(class_="seri_des") or soup.find(class_="description-text")
                            if desc_el:
                                series_description = desc_el.get("data-full-description", "") or desc_el.get_text(strip=True)
                    except Exception as e:
                        logging.warning("Failed to fetch series description: %s", e)

                    return episodes_by_season, movies, slug, series_description

                def scan_available_providers(sample_url, site):
                    """Scan a sample episode URL for available providers and languages."""
                    from ..models import Episode
                    from ..config import SUPPORTED_PROVIDERS, SITE_LANGUAGE_NAMES

                    available_providers = []
                    available_languages = []
                    try:
                        # movie4k.sx uses Movie class with API-based data
                        if site == "movie4k.sx":
                            from ..sites.movie4k import Movie
                            try:
                                movie = Movie(url=sample_url)
                                available_providers = [
                                    p for p in movie.provider_names
                                    if p in SUPPORTED_PROVIDERS
                                ]
                                available_languages = movie.available_languages
                            except Exception as e:
                                logging.warning("Failed to create Movie object for URL: %s, error: %s", sample_url, e)
                            return available_providers, available_languages

                        try:
                            ep = Episode(link=sample_url, site=site)
                        except Exception as e:
                            logging.warning("Failed to create Episode object for URL: %s, error: %s", sample_url, e)
                            return available_providers, available_languages
                        providers = ep._get_providers_from_html()
                        # Filter to only supported providers, preserve order
                        available_providers = [
                            p for p in providers.keys()
                            if p in SUPPORTED_PROVIDERS
                        ]

                        # Extract available languages from provider data
                        lang_keys = set()
                        for lang_map in providers.values():
                            lang_keys.update(lang_map.keys())

                        lang_names = SITE_LANGUAGE_NAMES.get(site, {})
                        available_languages = [
                            lang_names[k] for k in sorted(lang_keys)
                            if k in lang_names
                        ]
                    except Exception as e:
                        logging.warning(
                            "Failed to scan providers for %s: %s",
                            sample_url, e
                        )

                    return available_providers, available_languages

                # Use the wrapper function
                try:
                    episodes_by_season, movies, slug, description = get_episodes_for_series(
                        series_url
                    )
                except ValueError as e:
                    return jsonify({"success": False, "error": str(e)}), 400
                except Exception as e:
                    logging.error(f"Failed to get episodes: {e}")
                    return jsonify(
                        {"success": False, "error": "Failed to fetch episodes"}
                    ), 500

                # Determine site and pick a sample episode to scan providers
                sample_url = None
                site = "aniworld.to"
                if "s.to" in series_url or "/serie/" in series_url:
                    site = "s.to"
                elif "movie4k.sx" in series_url or "/watch/" in series_url:
                    site = "movie4k.sx"

                # Pick first available episode or movie as sample
                for season_eps in episodes_by_season.values():
                    if season_eps:
                        sample_url = season_eps[0]["url"]
                        break
                if not sample_url and movies:
                    sample_url = movies[0]["url"]

                available_providers = []
                available_languages = []
                if sample_url:
                    available_providers, available_languages = (
                        scan_available_providers(sample_url, site)
                    )

                # Scan for local files - auto-detect folder if not provided
                local_files = {}
                import re as re_mod
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)
                download_dir = Path(download_path)

                # Auto-detect folder from slug/title if no explicit folder_path
                if not folder_path and download_dir.exists():
                    # Try to find a matching folder by checking .series_meta.json
                    for candidate in download_dir.iterdir():
                        if not candidate.is_dir():
                            continue
                        meta_file = candidate / ".series_meta.json"
                        if meta_file.exists():
                            try:
                                import json as json_auto
                                meta = json_auto.loads(meta_file.read_text(encoding="utf-8"))
                                meta_url = meta.get("url", "")
                                # Match by URL (strip trailing slashes and season/episode paths)
                                series_base = series_url.split("/staffel-")[0].split("/filme/")[0].rstrip("/")
                                meta_base = meta_url.split("/staffel-")[0].split("/filme/")[0].rstrip("/")
                                if series_base and meta_base and series_base == meta_base:
                                    folder_path = candidate.name
                                    break
                            except Exception:
                                pass
                    # Also try matching by folder name == slug
                    if not folder_path:
                        slug_clean = slug.replace("-", " ").lower() if slug else ""
                        for candidate in download_dir.iterdir():
                            if candidate.is_dir() and candidate.name.lower() == slug_clean:
                                folder_path = candidate.name
                                break

                target_dir = download_dir / folder_path if folder_path else None
                video_exts = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v', '.flv', '.wmv'}
                if target_dir and target_dir.exists():
                    for f in target_dir.rglob("*"):
                        if f.is_file() and f.suffix.lower() in video_exts:
                            rel_path = str(f.relative_to(download_dir))
                            # Try S##E## pattern in filename first
                            match = re_mod.search(r'S(\d+)E(\d+)', f.name, re_mod.IGNORECASE)
                            if match:
                                s_num, e_num = int(match.group(1)), int(match.group(2))
                                local_files[f"{s_num}-{e_num}"] = rel_path
                                continue
                            # Try "Season X/Episode YYY.mp4" pattern (actual download format)
                            season_match = re_mod.search(r'Season\s+(\d+)', f.parent.name, re_mod.IGNORECASE)
                            ep_match = re_mod.search(r'Episode\s+(\d+)', f.name, re_mod.IGNORECASE)
                            if season_match and ep_match:
                                s_num = int(season_match.group(1))
                                e_num = int(ep_match.group(1))
                                local_files[f"{s_num}-{e_num}"] = rel_path
                                continue
                            # Try "Movies/Movie YYY.mp4" pattern
                            movie_match = re_mod.search(r'Movie\s+(\d+)', f.name, re_mod.IGNORECASE)
                            if movie_match:
                                local_files[f"movie-{int(movie_match.group(1))}"] = rel_path
                                continue
                            # Fallback: unmatched file
                            local_files[f"file-{f.name}"] = rel_path

                # Annotate episodes with local file info
                if local_files:
                    for _, eps in episodes_by_season.items():
                        for ep in eps:
                            key = f"{ep['season']}-{ep['episode']}"
                            if key in local_files:
                                ep["local"] = True
                                ep["local_path"] = local_files[key]
                            else:
                                ep["local"] = False
                    for movie in movies:
                        movie_key = f"movie-{movie.get('movie', 0)}"
                        if movie_key in local_files:
                            movie["local"] = True
                            movie["local_path"] = local_files[movie_key]
                        else:
                            # Fallback: check unmatched files
                            found = False
                            for fkey, fpath in local_files.items():
                                if fkey.startswith("file-"):
                                    found = True
                                    movie["local"] = True
                                    movie["local_path"] = fpath
                                    break
                            if not found:
                                movie["local"] = False

                return jsonify(
                    {
                        "success": True,
                        "episodes": episodes_by_season,
                        "movies": movies,
                        "slug": slug,
                        "description": description,
                        "available_providers": available_providers,
                        "available_languages": available_languages,
                    }
                )

            except Exception as err:
                logging.error(f"Episodes fetch error: {err}")
                return jsonify(
                    {"success": False, "error": f"Failed to fetch episodes: {str(err)}"}
                ), 500

        @self.app.route("/api/queue-status")
        @self._require_api_auth
        def api_queue_status():
            """Get download queue status endpoint."""
            try:
                queue_status = self.download_manager.get_queue_status()

                return jsonify({"success": True, "queue": queue_status})
            except Exception as e:
                logging.error(f"Failed to get queue status: {e}")
                return jsonify(
                    {"success": False, "error": "Failed to get queue status"}
                ), 500

        @self.app.route("/api/queue/cancel/<int:queue_id>", methods=["POST"])
        @self._require_api_auth
        def api_cancel_download(queue_id):
            """Cancel a download by queue ID."""
            try:
                success = self.download_manager.cancel_download(queue_id)
                if success:
                    return jsonify({"success": True})
                return jsonify({"success": False, "error": "Download not found or already finished"}), 404
            except Exception as e:
                logging.error(f"Failed to cancel download: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/popular-new")
        @self._require_api_auth
        def api_popular_new():
            """Get popular and new anime endpoint."""
            try:
                from ..search import fetch_popular_and_new_anime

                anime_data = fetch_popular_and_new_anime()
                return jsonify(
                    {
                        "success": True,
                        "popular": anime_data.get("popular", []),
                        "new": anime_data.get("new", []),
                    }
                )
            except Exception as e:
                logging.error(f"Failed to fetch popular/new anime: {e}")
                return jsonify(
                    {
                        "success": False,
                        "error": f"Failed to fetch popular/new anime: {str(e)}",
                    }
                ), 500

        @self.app.route("/api/popular-new-sto")
        @self._require_api_auth
        def api_popular_new_sto():
            """Get popular and new series from s.to."""
            try:
                from ..search import fetch_popular_and_new_sto

                sto_data = fetch_popular_and_new_sto()
                return jsonify(
                    {
                        "success": True,
                        "popular": sto_data.get("popular", []),
                        "new": sto_data.get("new", []),
                    }
                )
            except Exception as e:
                logging.error(f"Failed to fetch popular/new from s.to: {e}")
                return jsonify(
                    {
                        "success": False,
                        "error": f"Failed to fetch popular/new from s.to: {str(e)}",
                    }
                ), 500

        @self.app.route("/api/popular-new-movie4k")
        @self._require_api_auth
        def api_popular_new_movie4k():
            """Get popular and new movies from movie4k.sx."""
            try:
                from ..search import fetch_popular_and_new_movie4k

                movie4k_data = fetch_popular_and_new_movie4k()
                return jsonify(
                    {
                        "success": True,
                        "popular": movie4k_data.get("popular", []),
                        "new": movie4k_data.get("new", []),
                    }
                )
            except Exception as e:
                logging.error(f"Failed to fetch popular/new from movie4k: {e}")
                return jsonify(
                    {
                        "success": False,
                        "error": f"Failed to fetch popular/new from movie4k: {str(e)}",
                    }
                ), 500

        @self.app.route("/api/files")
        @self._require_api_auth
        def api_list_files():
            """List downloaded files endpoint - supports folder navigation."""
            try:
                # Get download directory
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                logging.debug(f"/api/files: Download directory: {download_dir}")

                # Get the relative subpath from query parameter
                subpath = request.args.get("path", "").strip()
                logging.debug(f"/api/files: Requested subpath: '{subpath}'")

                # Normalize subpath: handle cases where user passes the download directory name itself
                # For example, if download_dir is "/home/captain/Downloads" and subpath is "Downloads",
                # normalize it to empty string to refer to the root
                if subpath:
                    # Check if subpath is just the last component of download_dir
                    if subpath == download_dir.name:
                        logging.debug(f"/api/files: Normalized path from '{subpath}' to root (matched download dir name)")
                        subpath = ""
                    # Also handle forward slash normalization (convert backslashes to forward slashes)
                    subpath = subpath.replace("\\", "/")

                # Calculate current directory
                if subpath:
                    current_dir = download_dir / subpath
                else:
                    current_dir = download_dir

                logging.debug(f"/api/files: Current directory: {current_dir} (subpath: '{subpath}')")

                # Security check: ensure current_dir is within download_dir
                try:
                    current_dir.resolve().relative_to(download_dir.resolve())
                except ValueError:
                    logging.warning(f"/api/files: Security check failed for path: {current_dir}")
                    return jsonify({
                        "success": False,
                        "error": "Invalid path"
                    }), 403

                if not current_dir.exists():
                    logging.warning(f"/api/files: Directory does not exist: {current_dir}")
                    return jsonify({
                        "success": True,
                        "path": download_path,
                        "current_path": subpath,
                        "folders": [],
                        "files": []
                    })

                video_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v', '.flv', '.wmv'}
                folders = []
                files = []

                # List immediate children (folders and video files)
                logging.debug(f"/api/files: Scanning directory: {current_dir}")
                items_found = list(current_dir.iterdir())
                logging.debug(f"/api/files: Found {len(items_found)} items in directory")

                for item in items_found:
                    try:
                        if item.is_dir():
                            # Count video files in this folder (recursively)
                            video_count = self._count_video_files_recursive(item, video_extensions)
                            logging.debug(f"/api/files: Folder '{item.name}' has {video_count} videos")

                            if video_count > 0:  # Only show folders with videos
                                relative_path = item.relative_to(download_dir)
                                # Read series metadata if available
                                folder_meta = {}
                                meta_file = item / ".series_meta.json"
                                if meta_file.exists():
                                    try:
                                        import json as json_mod
                                        folder_meta = json_mod.loads(meta_file.read_text(encoding="utf-8"))
                                    except Exception:
                                        pass
                                # Check for local cover image
                                local_cover = ""
                                for ext in (".jpg", ".png", ".webp"):
                                    if (item / f"cover{ext}").exists():
                                        local_cover = f"/api/files/cover?path={relative_path}"
                                        break

                                # If no local cover and not yet attempted, fetch from TMDB in background
                                if not local_cover and not (item / ".cover_attempted").exists():
                                    import threading as _threading
                                    _cover_title = folder_meta.get("title", item.name)
                                    _cover_dest = item

                                    def _fetch_cover(_dest=_cover_dest, _title=_cover_title):
                                        try:
                                            from ..extractors.cover import download_cover_2x3
                                            download_cover_2x3(_title, output_path=str(_dest / "cover.jpg"))
                                            logging.info("Downloaded TMDB cover for '%s'", _title)
                                        except Exception as _e:
                                            logging.debug("Could not download cover for '%s': %s", _title, _e)
                                        finally:
                                            try:
                                                (_dest / ".cover_attempted").touch()
                                            except Exception:
                                                pass

                                    _threading.Thread(target=_fetch_cover, daemon=True).start()

                                folders.append({
                                    "name": item.name,
                                    "path": str(relative_path),
                                    "type": "folder",
                                    "video_count": video_count,
                                    "cover": folder_meta.get("cover", ""),
                                    "local_cover": local_cover,
                                    "series_url": folder_meta.get("url", ""),
                                    "site": folder_meta.get("site", ""),
                                })
                        elif item.is_file() and item.suffix.lower() in video_extensions:
                            try:
                                stat = item.stat()
                                relative_path = item.relative_to(download_dir)
                                files.append({
                                    "name": item.name,
                                    "path": str(relative_path),
                                    "full_path": str(item),
                                    "type": "file",
                                    "size": stat.st_size,
                                    "size_human": self._format_file_size(stat.st_size),
                                    "modified": stat.st_mtime,
                                    "modified_human": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                                })
                            except Exception as file_error:
                                logging.warning(f"/api/files: Error processing file '{item.name}': {file_error}")
                    except Exception as item_error:
                        logging.warning(f"/api/files: Error processing item '{item}': {item_error}")

                logging.info(f"/api/files: Found {len(folders)} folders and {len(files)} files in '{subpath or 'root'}'")

                # Sort folders alphabetically, files by modification time
                folders.sort(key=lambda x: x["name"].lower())
                files.sort(key=lambda x: x["name"].lower())

                # Calculate parent path for navigation
                parent_path = ""
                if subpath:
                    parent = Path(subpath).parent
                    parent_path = str(parent) if str(parent) != "." else ""

                return jsonify({
                    "success": True,
                    "path": download_path,
                    "current_path": subpath,
                    "parent_path": parent_path,
                    "folders": folders,
                    "files": files
                })

            except Exception as e:
                logging.error(f"Failed to list files: {e}", exc_info=True)
                return jsonify({
                    "success": False,
                    "error": f"Failed to list files: {str(e)}"
                }), 500

        @self.app.route("/api/files/cover")
        @self._require_api_auth
        def api_serve_cover():
            """Serve a locally saved cover image from a series folder."""
            try:
                folder_path = request.args.get("path", "").strip()
                if not folder_path:
                    return jsonify({"error": "Path required"}), 400

                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                cover_dir = download_dir / folder_path

                # Security check
                try:
                    cover_dir.resolve().relative_to(download_dir.resolve())
                except ValueError:
                    return jsonify({"error": "Invalid path"}), 403

                for ext in (".jpg", ".png", ".webp"):
                    cover_file = cover_dir / f"cover{ext}"
                    if cover_file.exists():
                        return send_file(str(cover_file.resolve()))

                return jsonify({"error": "Cover not found"}), 404
            except Exception as e:
                logging.warning("Failed to serve cover: %s", e)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/watch-progress", methods=["GET"])
        @self._require_api_auth
        def api_get_watch_progress():
            """Get watch progress for all files or a specific file."""
            try:
                file_path = request.args.get("file")
                progress_file = self._get_watch_progress_file()

                progress_data = self._load_watch_progress(progress_file)

                if file_path:
                    # Return progress for specific file
                    return jsonify({
                        "success": True,
                        "progress": progress_data.get(file_path, {})
                    })
                else:
                    # Return all progress
                    return jsonify({
                        "success": True,
                        "progress": progress_data
                    })
            except Exception as e:
                logging.error(f"Failed to get watch progress: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        @self.app.route("/api/watch-progress", methods=["POST"])
        @self._require_api_auth
        def api_set_watch_progress():
            """Set watch progress for a file."""
            try:
                data = request.get_json()
                file_path = data.get("file")
                current_time = data.get("current_time", 0)
                duration = data.get("duration", 0)

                if not file_path:
                    return jsonify({
                        "success": False,
                        "error": "File path is required"
                    }), 400

                progress_file = self._get_watch_progress_file()
                progress_data = self._load_watch_progress(progress_file)

                # Update progress for this file
                progress_data[file_path] = {
                    "current_time": current_time,
                    "duration": duration,
                    "last_watched": datetime.now().isoformat(),
                    "percentage": (current_time / duration * 100) if duration > 0 else 0
                }

                # Save progress
                self._save_watch_progress(progress_file, progress_data)

                return jsonify({
                    "success": True,
                    "message": "Progress saved"
                })
            except Exception as e:
                logging.error(f"Failed to save watch progress: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        @self.app.route("/api/watch-progress", methods=["DELETE"])
        @self._require_api_auth
        def api_delete_watch_progress():
            """Delete watch progress for a file."""
            try:
                data = request.get_json()
                file_path = data.get("file")

                if not file_path:
                    return jsonify({
                        "success": False,
                        "error": "File path is required"
                    }), 400

                progress_file = self._get_watch_progress_file()
                progress_data = self._load_watch_progress(progress_file)

                if file_path in progress_data:
                    del progress_data[file_path]
                    self._save_watch_progress(progress_file, progress_data)

                return jsonify({
                    "success": True,
                    "message": "Progress deleted"
                })
            except Exception as e:
                logging.error(f"Failed to delete watch progress: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

        # ---- Subscription Routes ----

        @self.app.route("/api/subscriptions", methods=["GET"])
        @self._require_api_auth
        def api_get_subscriptions():
            """Return all subscriptions."""
            try:
                subs = self._load_subscriptions()
                # Attach any pending notifications
                with self._subscription_lock:
                    notifications = list(self._subscription_notifications)
                return jsonify({"success": True, "subscriptions": subs, "notifications": notifications})
            except Exception as e:
                logging.error("Failed to get subscriptions: %s", e)
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/subscriptions", methods=["POST"])
        @self._require_api_auth
        def api_add_subscription():
            """Add a new subscription."""
            try:
                data = request.get_json()
                series_url = (data.get("series_url") or "").strip()
                title = (data.get("title") or "").strip()
                if not series_url or not title:
                    return jsonify({"success": False, "error": "series_url and title are required"}), 400

                subs = self._load_subscriptions()
                # Check duplicate
                if any(s["series_url"] == series_url for s in subs):
                    return jsonify({"success": False, "error": "Already subscribed to this series"}), 409

                new_id = max((s.get("id", 0) for s in subs), default=0) + 1
                episode_count = self._count_total_episodes(series_url)

                new_sub = {
                    "id": new_id,
                    "series_url": series_url,
                    "title": title,
                    "cover": data.get("cover") or "",
                    "site": data.get("site") or "",
                    "language": data.get("language") or getattr(config, "DEFAULT_LANGUAGE", "German Sub"),
                    "notify": bool(data.get("notify", True)),
                    "auto_download": bool(data.get("auto_download", False)),
                    "last_episode_count": max(episode_count, 0),
                    "last_checked": datetime.now().isoformat(),
                    "created_at": datetime.now().isoformat(),
                }
                subs.append(new_sub)
                self._save_subscriptions(subs)
                return jsonify({"success": True, "subscription": new_sub})
            except Exception as e:
                logging.error("Failed to add subscription: %s", e)
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/subscriptions/<int:sub_id>", methods=["DELETE"])
        @self._require_api_auth
        def api_delete_subscription(sub_id):
            """Delete a subscription."""
            try:
                subs = self._load_subscriptions()
                new_subs = [s for s in subs if s.get("id") != sub_id]
                if len(new_subs) == len(subs):
                    return jsonify({"success": False, "error": "Subscription not found"}), 404
                self._save_subscriptions(new_subs)
                return jsonify({"success": True})
            except Exception as e:
                logging.error("Failed to delete subscription: %s", e)
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/subscriptions/<int:sub_id>", methods=["PUT"])
        @self._require_api_auth
        def api_update_subscription(sub_id):
            """Update subscription settings (notify, auto_download, language)."""
            try:
                data = request.get_json()
                subs = self._load_subscriptions()
                for sub in subs:
                    if sub.get("id") == sub_id:
                        if "notify" in data:
                            sub["notify"] = bool(data["notify"])
                        if "auto_download" in data:
                            sub["auto_download"] = bool(data["auto_download"])
                        if "language" in data:
                            sub["language"] = data["language"]
                        break
                else:
                    return jsonify({"success": False, "error": "Subscription not found"}), 404
                self._save_subscriptions(subs)
                return jsonify({"success": True})
            except Exception as e:
                logging.error("Failed to update subscription: %s", e)
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/subscriptions/check", methods=["POST"])
        @self._require_api_auth
        def api_check_subscriptions():
            """Manually trigger a subscription check."""
            try:
                # Run in background thread to avoid blocking request
                t = threading.Thread(target=self._check_subscriptions_once, daemon=True)
                t.start()
                return jsonify({"success": True, "message": "Subscription check started"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/subscriptions/notifications", methods=["GET"])
        @self._require_api_auth
        def api_get_subscription_notifications():
            """Get and clear pending new-episode notifications."""
            try:
                with self._subscription_lock:
                    notes = list(self._subscription_notifications)
                    self._subscription_notifications.clear()
                return jsonify({"success": True, "notifications": notes})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/subscriptions/check-url", methods=["POST"])
        @self._require_api_auth
        def api_check_subscription_url():
            """Check if a URL is already subscribed."""
            try:
                data = request.get_json()
                series_url = (data.get("series_url") or "").strip()
                subs = self._load_subscriptions()
                sub = next((s for s in subs if s["series_url"] == series_url), None)
                return jsonify({"success": True, "subscribed": sub is not None, "subscription": sub})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        # ---- End Subscription Routes ----

        @self.app.route("/api/files/delete", methods=["POST"])
        @self._require_api_auth
        def api_delete_file():
            """Delete a file endpoint."""
            try:
                data = request.get_json()
                file_path = data.get("path")

                if not file_path:
                    return jsonify({
                        "success": False,
                        "error": "File path is required"
                    }), 400

                # Get download directory
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                full_path = download_dir / file_path

                # Security check: ensure file is within download directory
                try:
                    full_path.resolve().relative_to(download_dir.resolve())
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid file path"
                    }), 403

                if not full_path.exists():
                    return jsonify({
                        "success": False,
                        "error": "File not found"
                    }), 404

                # Delete the file
                full_path.unlink()

                return jsonify({
                    "success": True,
                    "message": "File deleted successfully"
                })

            except Exception as e:
                logging.error(f"Failed to delete file: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to delete file: {str(e)}"
                }), 500

        @self.app.route("/api/files/stream/<path:file_path>")
        @self._require_api_auth
        def api_stream_file(file_path):
            """Stream a video file endpoint."""
            try:
                # Get download directory
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                full_path = download_dir / file_path

                # Security check: ensure file is within download directory
                try:
                    full_path.resolve().relative_to(download_dir.resolve())
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid file path"
                    }), 403

                if not full_path.exists():
                    return jsonify({
                        "success": False,
                        "error": "File not found"
                    }), 404

                # Get MIME type
                mime_type, _ = mimetypes.guess_type(str(full_path))
                if not mime_type:
                    mime_type = "video/mp4"

                # Handle range requests for video seeking
                file_size = full_path.stat().st_size
                range_header = request.headers.get('Range', None)

                if range_header:
                    byte_start, byte_end = 0, None
                    match = range_header.replace('bytes=', '').split('-')
                    byte_start = int(match[0])
                    if len(match) > 1 and match[1]:
                        byte_end = int(match[1])
                    else:
                        byte_end = file_size - 1

                    length = byte_end - byte_start + 1

                    def generate():
                        with open(full_path, 'rb') as f:
                            f.seek(byte_start)
                            remaining = length
                            while remaining > 0:
                                chunk_size = min(8192, remaining)
                                data = f.read(chunk_size)
                                if not data:
                                    break
                                remaining -= len(data)
                                yield data

                    response = Response(
                        generate(),
                        status=206,
                        mimetype=mime_type,
                        direct_passthrough=True
                    )
                    response.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
                    response.headers.add('Accept-Ranges', 'bytes')
                    response.headers.add('Content-Length', str(length))
                    return response
                else:
                    return send_file(
                        full_path,
                        mimetype=mime_type,
                        as_attachment=False
                    )

            except Exception as e:
                logging.error(f"Failed to stream file: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to stream file: {str(e)}"
                }), 500

        @self.app.route("/api/files/download/<path:file_path>")
        @self._require_api_auth
        def api_download_file(file_path):
            """Download a video file endpoint."""
            try:
                # Get download directory
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                full_path = download_dir / file_path

                # Security check: ensure file is within download directory
                try:
                    full_path.resolve().relative_to(download_dir.resolve())
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid file path"
                    }), 403

                if not full_path.exists():
                    return jsonify({
                        "success": False,
                        "error": "File not found"
                    }), 404

                # Get MIME type
                mime_type, _ = mimetypes.guess_type(str(full_path))
                if not mime_type:
                    mime_type = "application/octet-stream"

                return send_file(
                    full_path,
                    mimetype=mime_type,
                    as_attachment=True,
                    download_name=full_path.name
                )

            except Exception as e:
                logging.error(f"Failed to download file: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to download file: {str(e)}"
                }), 500

        @self.app.route("/api/files/play", methods=["POST"])
        @self._require_api_auth
        def api_play_file():
            """Play a video file in the local video player (MPV)."""
            try:
                data = request.get_json()
                file_path = data.get("path")

                if not file_path:
                    return jsonify({
                        "success": False,
                        "error": "File path is required"
                    }), 400

                # Get download directory
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                full_path = download_dir / file_path

                # Security check
                try:
                    full_path.resolve().relative_to(download_dir.resolve())
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid file path"
                    }), 403

                if not full_path.exists():
                    return jsonify({
                        "success": False,
                        "error": "File not found"
                    }), 404

                # Try to play with MPV
                try:
                    subprocess.Popen(
                        ["mpv", str(full_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return jsonify({
                        "success": True,
                        "message": "Playing in MPV"
                    })
                except FileNotFoundError:
                    # MPV not found, return stream URL instead
                    return jsonify({
                        "success": True,
                        "stream_url": f"/api/files/stream/{file_path}",
                        "message": "MPV not found, use stream URL"
                    })

            except Exception as e:
                logging.error(f"Failed to play file: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to play file: {str(e)}"
                }), 500

        @self.app.route("/api/chromecast/discover")
        @self._require_api_auth
        def api_chromecast_discover():
            """Discover Chromecast devices on the network."""
            try:
                try:
                    import pychromecast
                except ImportError:
                    return jsonify({
                        "success": False,
                        "error": "pychromecast not installed. Install with: pip install pychromecast",
                        "devices": []
                    })

                # Use get_chromecasts which handles zeroconf lifecycle properly
                chromecasts, browser = pychromecast.get_chromecasts(timeout=10)

                # Collect device info from discovered chromecasts
                devices = []
                for cc in chromecasts:
                    # Access host/port from cast_info
                    cast_info = cc.cast_info
                    if cast_info and cast_info.host:
                        devices.append({
                            "name": cc.name,
                            "model": cc.model_name,
                            "uuid": str(cc.uuid),
                            "host": cast_info.host,
                            "port": cast_info.port
                        })

                # Stop discovery (keeps zeroconf alive for existing connections)
                browser.stop_discovery()

                return jsonify({
                    "success": True,
                    "devices": devices
                })

            except Exception as e:
                logging.error(f"Failed to discover Chromecasts: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to discover devices: {str(e)}",
                    "devices": []
                })

        @self.app.route("/api/chromecast/cast", methods=["POST"])
        @self._require_api_auth
        def api_chromecast_cast():
            """Cast a video to a Chromecast device."""
            try:
                try:
                    import pychromecast
                except ImportError:
                    return jsonify({
                        "success": False,
                        "error": "pychromecast not installed"
                    })

                data = request.get_json()
                device_uuid = data.get("device_uuid")
                file_path = data.get("file_path")

                if not device_uuid or not file_path:
                    return jsonify({
                        "success": False,
                        "error": "Device UUID and file path are required"
                    }), 400

                # Get download directory and construct full path
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (
                    self.arguments
                    and hasattr(self.arguments, "output_dir")
                    and self.arguments.output_dir is not None
                ):
                    download_path = str(self.arguments.output_dir)

                download_dir = Path(download_path)
                full_path = download_dir / file_path

                if not full_path.exists():
                    return jsonify({
                        "success": False,
                        "error": "File not found"
                    }), 404

                # Find the Chromecast
                cast, _ = self._discover_chromecast_by_uuid(device_uuid)

                if not cast:
                    return jsonify({
                        "success": False,
                        "error": "Chromecast device not found"
                    }), 404

                # Wait for cast device to be ready
                cast.wait()

                # Get the stream URL
                # We need to provide an accessible URL to the Chromecast
                # The file will be served from our Flask server
                host_ip = request.host.split(':')[0]
                if host_ip == 'localhost' or host_ip == '127.0.0.1':
                    # Try to get the actual network IP
                    import socket
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(("8.8.8.8", 80))
                        host_ip = s.getsockname()[0]
                        s.close()
                    except Exception:
                        pass

                port = request.host.split(':')[1] if ':' in request.host else '5000'
                stream_url = f"http://{host_ip}:{port}/api/files/stream/{file_path}"

                # Get MIME type
                mime_type, _ = mimetypes.guess_type(str(full_path))
                if not mime_type:
                    mime_type = "video/mp4"

                # Cast the video
                mc = cast.media_controller
                mc.play_media(stream_url, mime_type)
                mc.block_until_active()

                return jsonify({
                    "success": True,
                    "message": f"Casting to {cast.name}",
                    "device_name": cast.name,
                    "stream_url": stream_url
                })

            except Exception as e:
                logging.error(f"Failed to cast: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to cast: {str(e)}"
                }), 500

        @self.app.route("/api/chromecast/control", methods=["POST"])
        @self._require_api_auth
        def api_chromecast_control():
            """Control Chromecast playback."""
            try:
                try:
                    import pychromecast
                except ImportError:
                    return jsonify({
                        "success": False,
                        "error": "pychromecast not installed"
                    })

                data = request.get_json()
                device_uuid = data.get("device_uuid")
                action = data.get("action")  # play, pause, stop, seek, volume
                value = data.get("value")  # For seek (seconds) or volume (0-100)

                if not device_uuid or not action:
                    return jsonify({
                        "success": False,
                        "error": "Device UUID and action are required"
                    }), 400

                # Find the Chromecast
                cast, _ = self._discover_chromecast_by_uuid(device_uuid)

                if not cast:
                    return jsonify({
                        "success": False,
                        "error": "Chromecast device not found"
                    }), 404

                cast.wait()
                mc = cast.media_controller

                if action == "play":
                    mc.play()
                elif action == "pause":
                    mc.pause()
                elif action == "stop":
                    mc.stop()
                elif action == "seek":
                    if value is not None:
                        mc.seek(float(value))
                elif action == "volume":
                    if value is not None:
                        cast.set_volume(float(value) / 100.0)
                elif action == "rewind":
                    # Rewind 10 seconds
                    if mc.status and mc.status.current_time:
                        new_time = max(0, mc.status.current_time - 10)
                        mc.seek(new_time)
                elif action == "forward":
                    # Forward 10 seconds
                    if mc.status and mc.status.current_time:
                        mc.seek(mc.status.current_time + 10)
                else:
                    return jsonify({
                        "success": False,
                        "error": f"Unknown action: {action}"
                    }), 400

                return jsonify({
                    "success": True,
                    "message": f"Action {action} executed"
                })

            except Exception as e:
                logging.error(f"Chromecast control error: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Control failed: {str(e)}"
                }), 500

        @self.app.route("/api/chromecast/status")
        @self._require_api_auth
        def api_chromecast_status():
            """Get Chromecast playback status."""
            try:
                try:
                    import pychromecast
                except ImportError:
                    return jsonify({
                        "success": False,
                        "error": "pychromecast not installed"
                    })

                device_uuid = request.args.get("device_uuid")

                if not device_uuid:
                    return jsonify({
                        "success": False,
                        "error": "Device UUID is required"
                    }), 400

                # Find the Chromecast
                cast, _ = self._discover_chromecast_by_uuid(device_uuid)

                if not cast:
                    return jsonify({
                        "success": False,
                        "error": "Chromecast device not found"
                    }), 404

                cast.wait()
                mc = cast.media_controller

                status = {
                    "is_playing": False,
                    "is_paused": False,
                    "current_time": 0,
                    "duration": 0,
                    "volume": cast.status.volume_level * 100 if cast.status else 100,
                    "title": ""
                }

                if mc.status:
                    status["is_playing"] = mc.status.player_is_playing
                    status["is_paused"] = mc.status.player_is_paused
                    status["current_time"] = mc.status.current_time or 0
                    status["duration"] = mc.status.duration or 0
                    status["title"] = mc.status.title or ""

                return jsonify({
                    "success": True,
                    "status": status
                })

            except Exception as e:
                logging.error(f"Failed to get Chromecast status: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to get status: {str(e)}"
                })

    @staticmethod
    def _download_cover_image(cover_url: str, site: str, dest_dir: Path) -> None:
        """Download a cover image and save it to the series folder.

        Args:
            cover_url: The cover image URL (may be relative for aniworld/s.to).
            site: The site identifier (e.g. 'aniworld.to', 's.to', 'movie4k.sx').
            dest_dir: The series directory to save cover.jpg into.
        """
        import requests as req_lib

        # Normalize relative URLs to absolute
        if not cover_url.startswith("http"):
            if cover_url.startswith("//"):
                cover_url = "https:" + cover_url
            else:
                base_urls = {
                    "aniworld.to": config.ANIWORLD_TO,
                    "s.to": config.S_TO,
                    "movie4k.sx": config.MOVIE4K_SX,
                }
                base = base_urls.get(site, config.ANIWORLD_TO)
                cover_url = base.rstrip("/") + "/" + cover_url.lstrip("/")

        try:
            resp = req_lib.get(
                cover_url,
                timeout=config.DEFAULT_REQUEST_TIMEOUT,
                headers={"User-Agent": config.RANDOM_USER_AGENT},
            )
            if resp.ok and resp.content:
                content_type = resp.headers.get("Content-Type", "")
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"
                else:
                    ext = ".jpg"
                cover_file = dest_dir / f"cover{ext}"
                cover_file.write_bytes(resp.content)
                logging.debug("Saved cover image to %s", cover_file)
        except Exception as e:
            logging.warning("Failed to download cover image: %s", e)

    def _count_video_files_recursive(self, directory: Path, video_extensions: set) -> int:
        """
        Safely count video files in a directory recursively.
        
        Args:
            directory: The directory to scan
            video_extensions: Set of video file extensions to look for
            
        Returns:
            The count of video files found
        """
        count = 0
        try:
            for path in directory.rglob('*'):
                try:
                    if path.is_file() and path.suffix.lower() in video_extensions:
                        count += 1
                except (OSError, PermissionError):
                    # Skip files we can't access
                    pass
        except (OSError, PermissionError) as e:
            logging.warning(f"Error scanning directory {directory}: {e}")
        return count

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _get_watch_progress_file(self) -> Path:
        """Get the path to the watch progress JSON file."""
        download_path = str(config.DEFAULT_DOWNLOAD_PATH)
        if (
            self.arguments
            and hasattr(self.arguments, "output_dir")
            and self.arguments.output_dir is not None
        ):
            download_path = str(self.arguments.output_dir)

        download_dir = Path(download_path)
        return download_dir / ".watch_progress.json"

    def _load_watch_progress(self, progress_file: Path) -> dict:
        """Load watch progress from JSON file."""
        import json
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load watch progress: {e}")
                return {}
        return {}

    def _save_watch_progress(self, progress_file: Path, data: dict) -> None:
        """Save watch progress to JSON file."""
        import json
        try:
            # Ensure parent directory exists
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save watch progress: {e}")

    # ---- Subscription helpers ----

    def _get_subscriptions_file(self) -> Path:
        """Get path to subscriptions JSON file (same dir as preferences)."""
        if os.name == "nt":
            data_dir = Path(os.getenv("APPDATA", "")) / "aniworld"
        else:
            data_dir = Path.home() / ".local" / "share" / "aniworld"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "subscriptions.json"

    def _load_subscriptions(self) -> list:
        """Load subscriptions list from JSON file."""
        import json
        sub_file = self._get_subscriptions_file()
        if sub_file.exists():
            try:
                with open(sub_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error("Failed to load subscriptions: %s", e)
        return []

    def _save_subscriptions(self, subs: list) -> None:
        """Save subscriptions list to JSON file."""
        import json
        sub_file = self._get_subscriptions_file()
        try:
            with open(sub_file, "w", encoding="utf-8") as f:
                json.dump(subs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error("Failed to save subscriptions: %s", e)

    def _count_total_episodes(self, series_url: str) -> int:
        """Return total episode (+ movie) count for a series URL, or -1 on error."""
        try:
            from ..common import get_season_episode_count, get_movie_episode_count
            from ..entry import _detect_site_from_url
            from .. import config as cfg

            if "/anime/stream/" in series_url:
                slug = series_url.split("/anime/stream/")[-1].rstrip("/")
                base_url = cfg.ANIWORLD_TO
            elif "/serie/" in series_url:
                slug = series_url.split("/serie/")[-1].rstrip("/")
                base_url = cfg.S_TO
            elif "movie4k" in series_url or "/watch/" in series_url:
                return 1  # single movie
            else:
                return -1

            season_counts = get_season_episode_count(slug, base_url)
            total = sum(season_counts.values())

            try:
                movie_count = get_movie_episode_count(slug, link=base_url)
                total += movie_count
            except Exception:
                pass

            return total
        except Exception as e:
            logging.warning("Failed to count episodes for %s: %s", series_url, e)
            return -1

    def _check_subscriptions_once(self) -> None:
        """Check all subscriptions for new episodes and create notifications / trigger downloads."""
        import json
        subs = self._load_subscriptions()
        changed = False

        for sub in subs:
            if not sub.get("notify") and not sub.get("auto_download"):
                continue
            try:
                new_count = self._count_total_episodes(sub["series_url"])
                if new_count < 0:
                    continue
                old_count = sub.get("last_episode_count", 0)
                sub["last_checked"] = datetime.now().isoformat()
                changed = True

                if new_count > old_count and old_count > 0:
                    diff = new_count - old_count
                    logging.info(
                        "Subscription '%s' has %d new episode(s) (%d -> %d)",
                        sub["title"], diff, old_count, new_count
                    )

                    if sub.get("notify", True):
                        with self._subscription_lock:
                            self._subscription_notifications.append({
                                "sub_id": sub["id"],
                                "title": sub["title"],
                                "new_count": diff,
                                "detected_at": datetime.now().isoformat(),
                            })

                    if sub.get("auto_download", False):
                        self._auto_download_new_episodes(sub, old_count, new_count)

                sub["last_episode_count"] = new_count

            except Exception as e:
                logging.warning("Error checking subscription '%s': %s", sub.get("title", "?"), e)

        if changed:
            self._save_subscriptions(subs)

    def _auto_download_new_episodes(self, sub: dict, old_count: int, new_count: int) -> None:
        """Queue new episodes for auto-download."""
        try:
            from ..common import get_season_episode_count
            from .. import config as cfg

            series_url = sub["series_url"]
            language = sub.get("language", cfg.DEFAULT_LANGUAGE)

            if "/anime/stream/" in series_url:
                slug = series_url.split("/anime/stream/")[-1].rstrip("/")
                base_url = cfg.ANIWORLD_TO
                stream_path = "anime/stream"
            elif "/serie/" in series_url:
                slug = series_url.split("/serie/")[-1].rstrip("/")
                base_url = cfg.S_TO
                stream_path = "serie"
            else:
                return

            season_counts = get_season_episode_count(slug, base_url)
            # Collect all episode URLs in order and take only the new ones
            all_urls = []
            for s_num in sorted(season_counts.keys()):
                for ep_num in range(1, season_counts[s_num] + 1):
                    all_urls.append(
                        f"{base_url}/{stream_path}/{slug}/staffel-{s_num}/episode-{ep_num}"
                    )

            new_urls = all_urls[old_count:new_count]
            if not new_urls:
                return

            download_manager = get_download_manager(self.db, getattr(config, "DEFAULT_MAX_CONCURRENT_DOWNLOADS", 5))
            download_path = str(config.DEFAULT_DOWNLOAD_PATH)
            prefs = self._load_preferences()
            if prefs.get("download_directory"):
                download_path = prefs["download_directory"]

            for ep_url in new_urls:
                download_manager.add_download(
                    url=ep_url,
                    language=language,
                    provider=None,
                    output_dir=download_path,
                    anime_title=sub["title"],
                )
            logging.info("Auto-queued %d new episode(s) for '%s'", len(new_urls), sub["title"])
        except Exception as e:
            logging.error("Auto-download failed for subscription '%s': %s", sub.get("title", "?"), e)

    def _start_subscription_checker(self) -> None:
        """Start background thread that checks subscriptions every hour."""
        def checker_loop():
            # Initial delay to let the app fully start
            time.sleep(30)
            while True:
                try:
                    self._check_subscriptions_once()
                except Exception as e:
                    logging.error("Subscription checker error: %s", e)
                time.sleep(3600)  # check every hour

        t = threading.Thread(target=checker_loop, daemon=True, name="subscription-checker")
        t.start()

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in human readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours}h {minutes}m {seconds}s"

    def run(self, live: bool = False):
        """Run the Flask web application. If `live` is True, start a livereload server that auto-refreshes the browser on template/static changes."""
        logging.info("Starting AnyLoader Web Interface...")
        logging.info(f"Server running at http://{self.host}:{self.port}")

        # If live reload is requested, import and configure livereload lazily so it is
        # only required when explicitly requested via the CLI (--live).
        if live:
            logging.info("Live reload requested: attempting to start livereload server...")
            try:
                from livereload import Server
            except Exception as e:
                logging.error(
                    "Live reload requested but 'livereload' package is not available. "
                    "Install it with 'pip install livereload' or run without --live. "
                    f"Import error: {e}"
                )
                logging.info("Falling back to normal Flask server...")
                live = False

        try:
            if live:
                server = Server(self.app.wsgi_app)

                # Watch templates and static assets for changes
                try:
                    # Prefer watching the template folder directly (works recursively)
                    server.watch(self.app.template_folder, delay=0.5)
                except Exception:
                    server.watch(os.path.join(self.app.template_folder, "*.html"), delay=0.5)

                server.watch(os.path.join(self.app.static_folder, "css", "*.css"), delay=0.5)
                server.watch(os.path.join(self.app.static_folder, "js", "*.js"), delay=0.5)

                # Serve using livereload (this will auto-reload the browser when watched files change)
                server.serve(host=self.host, port=self.port, debug=self.debug, root=self.app.static_folder)
            else:
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=self.debug,
                    use_reloader=False,  # Disable reloader to avoid conflicts
                )
        except KeyboardInterrupt:
            logging.info("Web interface stopped by user")
        except Exception as err:
            logging.error(f"Error running web interface: {err}")
            raise


def create_app(host="127.0.0.1", port=5000, debug=False, arguments=None) -> WebApp:
    """
    Factory function to create web application.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
        arguments: Command line arguments object

    Returns:
        WebApp instance
    """
    return WebApp(host=host, port=port, debug=debug, arguments=arguments)


def start_web_interface(arguments=None, port=5000, debug=False):
    """Start the web interface with configurable settings."""
    # Determine host based on web_expose argument
    host = "0.0.0.0" if getattr(arguments, "web_expose", False) else "127.0.0.1"
    web_app = create_app(host=host, port=port, debug=debug, arguments=arguments)

    # Print startup status
    auth_status = (
        "Authentication ENABLED"
        if getattr(arguments, "enable_web_auth", False)
        else "No Authentication (Local Mode)"
    )
    browser_status = (
        "Browser will open automatically"
        if not getattr(arguments, "no_browser", False)
        else "Browser auto-open disabled"
    )
    expose_status = (
        "ENABLED (0.0.0.0)"
        if getattr(arguments, "web_expose", False)
        else "DISABLED (localhost only)"
    )

    # Get download path
    download_path = str(config.DEFAULT_DOWNLOAD_PATH)
    if (
        arguments
        and hasattr(arguments, "output_dir")
        and arguments.output_dir is not None
    ):
        download_path = str(arguments.output_dir)

    # Show appropriate server address based on host
    server_address = (
        f"http://{host}:{port}" if host == "0.0.0.0" else f"http://localhost:{port}"
    )

    print("\n" + "=" * 69)
    print(" AnyLoader Web Interface")
    print("=" * 69)
    print(f" Server Address:   {server_address}")
    print(f" Security Mode:    {auth_status}")
    print(f" External Access:  {expose_status}")
    print(f" Download Path:    {download_path}")
    print(f" Debug Mode:       {'ENABLED' if debug else 'DISABLED'}")
    print(f" Version:          {config.VERSION}")
    print(f" Browser:          {browser_status}")
    print("=" * 69)
    print(" Access the web interface by opening the URL above in your browser")
    if getattr(arguments, "enable_web_auth", False):
        print(" First visit will prompt you to create an admin account")
    print(" Press Ctrl+C to stop the server")
    print("=" * 69 + "\n")

    # Open browser automatically unless disabled
    if not getattr(arguments, "no_browser", False):

        def open_browser():
            # Wait a moment for the server to start
            time.sleep(1.5)
            url = f"http://localhost:{port}"
            logging.info(f"Opening browser at {url}")
            try:
                webbrowser.open(url)
            except Exception as e:
                logging.warning(f"Could not open browser automatically: {e}")

        # Start browser opening in a separate thread
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()

    # Determine whether live reload was requested via CLI
    live_enabled = getattr(arguments, "live", False)
    web_app.run(live=live_enabled)


if __name__ == "__main__":
    start_web_interface()
