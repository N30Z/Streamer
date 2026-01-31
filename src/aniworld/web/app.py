"""
Flask web application for AniWorld Downloader
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
    """Flask web application wrapper for AniWorld Downloader"""

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

        # Scan for manually placed files at startup
        self._scan_media_library()

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
                from ..parser import arguments
                # Only apply if not overridden by command-line argument
                if not self.arguments or not getattr(self.arguments, "output_dir", None) or \
                   str(getattr(self.arguments, "output_dir", "")) == str(config.DEFAULT_DOWNLOAD_PATH):
                    arguments.output_dir = prefs["download_directory"]
                    logging.info(f"Applied saved download directory: {prefs['download_directory']}")

            # Apply max concurrent downloads
            if prefs.get("max_concurrent_downloads"):
                self.download_manager.max_concurrent_downloads = prefs["max_concurrent_downloads"]
                logging.info(f"Applied saved max concurrent downloads: {prefs['max_concurrent_downloads']}")

        except Exception as e:
            logging.warning(f"Could not apply saved preferences: {e}")

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
            "default_action": getattr(config, "DEFAULT_ACTION", "Download"),
            "accent_color": "purple",
            "animations_enabled": True,
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

        if "download_directory" in data:
            download_dir = Path(data["download_directory"])
            # Create directory if it doesn't exist
            download_dir.mkdir(parents=True, exist_ok=True)
            data["download_directory"] = str(download_dir)

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

        # Update download directory in runtime arguments
        if "download_directory" in data:
            from ..parser import arguments
            arguments.output_dir = data["download_directory"]
            logging.info(f"Updated runtime output_dir to: {data['download_directory']}")

        logging.info(f"Preferences saved: {data}")

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
                print(f"📚 Media Library: {series_count} series, {season_count} seasons, {episode_count} episodes ({format_size(total_size)})")
            else:
                logging.info(f"Media library is empty: {download_path}")

        except Exception as e:
            logging.warning(f"Failed to scan media library: {e}")

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
            if self.auth_enabled and self.db:
                # Check if this is first-time setup
                if not self.db.has_users():
                    return redirect(url_for("setup"))

                # Get current user info for template
                session_token = request.cookies.get("session_token")
                user = self.db.get_user_by_session(session_token)
                return render_template("index.html", user=user, auth_enabled=True)
            else:
                return render_template("index.html", auth_enabled=False)

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

            # Get list of providers
            providers = list(config.SUPPORTED_PROVIDERS)

            return render_template(
                "preferences.html",
                auth_enabled=self.auth_enabled,
                user=user,
                preferences=preferences_data,
                providers=providers
            )

        @self.app.route("/api/preferences", methods=["GET"])
        def api_get_preferences():
            """Get current preferences."""
            preferences_data = self._load_preferences()
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

                # Create wrapper function to handle all logic
                def get_episodes_for_series(series_url):
                    """Wrapper function using existing functions to get episodes and movies"""
                    from ..common import (
                        get_season_episode_count,
                        get_movie_episode_count,
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
                            try:
                                movie_obj = Movie4kMovie(url=series_url)
                                movie_title = movie_obj.title
                            except Exception:
                                movie_title = "Movie"
                            # No seasons/episodes for movies; return a movies list with single item
                            return {}, [{"movie": 1, "title": movie_title, "url": series_url}], series_url

                        raise ValueError("Invalid series URL format")

                    # Use existing function to get season/episode counts
                    season_counts = get_season_episode_count(slug, base_url)

                    # Build episodes structure
                    episodes_by_season = {}
                    for season_num, episode_count in season_counts.items():
                        if episode_count > 0:
                            episodes_by_season[season_num] = []
                            for ep_num in range(1, episode_count + 1):
                                episodes_by_season[season_num].append(
                                    {
                                        "season": season_num,
                                        "episode": ep_num,
                                        "title": f"Episode {ep_num}",
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

                    return episodes_by_season, movies, slug

                # Use the wrapper function
                try:
                    episodes_by_season, movies, slug = get_episodes_for_series(
                        series_url
                    )
                except ValueError as e:
                    return jsonify({"success": False, "error": str(e)}), 400
                except Exception as e:
                    logging.error(f"Failed to get episodes: {e}")
                    return jsonify(
                        {"success": False, "error": "Failed to fetch episodes"}
                    ), 500

                return jsonify(
                    {
                        "success": True,
                        "episodes": episodes_by_season,
                        "movies": movies,
                        "slug": slug,
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
                                folders.append({
                                    "name": item.name,
                                    "path": str(relative_path),
                                    "type": "folder",
                                    "video_count": video_count
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

    def run(self):
        """Run the Flask web application."""
        logging.info("Starting AniWorld Downloader Web Interface...")
        logging.info(f"Server running at http://{self.host}:{self.port}")

        try:
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
    print("🌐 AniWorld Downloader Web Interface")
    print("=" * 69)
    print(f"📍 Server Address:   {server_address}")
    print(f"🔐 Security Mode:    {auth_status}")
    print(f"🌐 External Access:  {expose_status}")
    print(f"📁 Download Path:    {download_path}")
    print(f"🐞 Debug Mode:       {'ENABLED' if debug else 'DISABLED'}")
    print(f"📦 Version:          {config.VERSION}")
    print(f"🌏 Browser:          {browser_status}")
    print("=" * 69)
    print("💡 Access the web interface by opening the URL above in your browser")
    if getattr(arguments, "enable_web_auth", False):
        print("💡 First visit will prompt you to create an admin account")
    print("💡 Press Ctrl+C to stop the server")
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

    web_app.run()


if __name__ == "__main__":
    start_web_interface()
