"""
Download Queue Manager for AniWorld Downloader
Handles global download queue processing and status tracking
Supports parallel downloads with configurable concurrent worker threads
"""

import threading
import time
import logging
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from .database import UserDatabase


class DownloadQueueManager:
    """Manages the global download queue processing with in-memory storage
    
    Supports parallel downloads using a thread pool executor. The number of
    concurrent downloads is configurable via max_concurrent_downloads parameter.
    """

    def __init__(self, database: Optional[UserDatabase] = None, max_concurrent_downloads: int = 3):
        self.db = database  # Only used for user auth, not download storage
        self.is_processing = False
        self.worker_thread = None
        self._stop_event = threading.Event()
        
        # Parallel download configuration
        self.max_concurrent_downloads = max_concurrent_downloads
        self.thread_pool = None
        self.active_workers = set()  # Track active worker jobs

        # In-memory download queue storage
        self._next_id = 1
        self._queue_lock = threading.Lock()
        self._active_downloads = {}  # id -> download_job dict
        self._completed_downloads = []  # list of completed download jobs (keep last N)
        self._max_completed_history = 10
        self._cancelled_ids = set()  # Track cancelled download IDs

    def start_queue_processor(self):
        """Start the background queue processor with thread pool"""
        if not self.is_processing:
            self.is_processing = True
            self._stop_event.clear()
            # Create thread pool for parallel downloads
            self.thread_pool = ThreadPoolExecutor(max_workers=self.max_concurrent_downloads)
            self.worker_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
            self.worker_thread.start()
            logging.info(f"Download queue processor started with {self.max_concurrent_downloads} concurrent workers")

    def stop_queue_processor(self):
        """Stop the background queue processor and thread pool"""
        if self.is_processing:
            self.is_processing = False
            self._stop_event.set()
            
            # Wait for all active workers to complete
            if self.active_workers:
                logging.info(f"Waiting for {len(self.active_workers)} active downloads to complete...")
                # Give workers time to finish gracefully
                timeout = 30
                start_time = time.time()
                while self.active_workers and time.time() - start_time < timeout:
                    time.sleep(0.5)
            
            # Shutdown thread pool
            if self.thread_pool:
                self.thread_pool.shutdown(wait=True)
                self.thread_pool = None
            
            # Wait for main worker thread
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            
            logging.info("Download queue processor stopped")

    def add_download(
        self,
        anime_title: str,
        episode_urls: list,
        language: str,
        provider: str,
        total_episodes: int,
        created_by: int = None,
    ) -> list:
        """Add a download to the queue
        
        Args:
            anime_title: Title of the anime
            episode_urls: List of episode URLs to download
            language: Language for the download
            provider: Provider to use for download
            total_episodes: Total number of episodes
            created_by: User ID who initiated the download
            
        Returns:
            List of queue IDs for each episode download
        """
        queue_ids = []
        
        with self._queue_lock:
            # Create individual download jobs for each episode URL
            for i, episode_url in enumerate(episode_urls, 1):
                queue_id = self._next_id
                self._next_id += 1

                download_job = {
                    "id": queue_id,
                    "anime_title": anime_title,
                    "episode_urls": [episode_url],  # Single episode URL
                    "episode_number": i,  # Track episode position
                    "language": language,
                    "provider": provider,
                    "total_episodes": 1,  # Each job is one episode
                    "completed_episodes": 0,
                    "status": "queued",
                    "current_episode": "",
                    "progress_percentage": 0.0,
                    "current_episode_progress": 0.0,
                    "error_message": "",
                    "created_by": created_by,
                    "created_at": datetime.now(),
                    "started_at": None,
                    "completed_at": None,
                }

                self._active_downloads[queue_id] = download_job
                queue_ids.append(queue_id)

        # Start processor if not running
        if not self.is_processing:
            self.start_queue_processor()

        logging.info(f"Added {len(queue_ids)} episode(s) to download queue for {anime_title}")
        return queue_ids

    def get_queue_status(self):
        """Get current queue status"""
        with self._queue_lock:
            active_downloads = []
            for download in self._active_downloads.values():
                if download["status"] in ["queued", "downloading"]:
                    # Format for API compatibility
                    active_downloads.append(
                        {
                            "id": download["id"],
                            "anime_title": download["anime_title"],
                            "episode_number": download["episode_number"],
                            "total_episodes": download["total_episodes"],
                            "completed_episodes": download["completed_episodes"],
                            "status": download["status"],
                            "current_episode": download["current_episode"],
                            "progress_percentage": download["progress_percentage"],
                            "current_episode_progress": download[
                                "current_episode_progress"
                            ],
                            "error_message": download["error_message"],
                            "created_at": download["created_at"].isoformat()
                            if download["created_at"]
                            else None,
                        }
                    )

            completed_downloads = []
            for download in self._completed_downloads:
                completed_downloads.append(
                    {
                        "id": download["id"],
                        "anime_title": download["anime_title"],
                        "episode_number": download.get("episode_number", 0),
                        "total_episodes": download["total_episodes"],
                        "completed_episodes": download["completed_episodes"],
                        "status": download["status"],
                        "current_episode": download["current_episode"],
                        "progress_percentage": download["progress_percentage"],
                        "current_episode_progress": download.get(
                            "current_episode_progress", 100.0
                        ),
                        "error_message": download["error_message"],
                        "completed_at": download["completed_at"].isoformat()
                        if download["completed_at"]
                        else None,
                    }
                )

            return {"active": active_downloads, "completed": completed_downloads}

    def cancel_download(self, queue_id: int) -> bool:
        """Cancel a download by its queue ID.

        Queued jobs are removed immediately. Downloading jobs are flagged for
        cancellation so the worker thread can stop gracefully.
        """
        with self._queue_lock:
            if queue_id in self._active_downloads:
                job = self._active_downloads[queue_id]
                if job["status"] == "queued":
                    # Not started yet – just remove it
                    del self._active_downloads[queue_id]
                    logging.info(f"Cancelled queued download {queue_id}")
                    return True
                elif job["status"] == "downloading":
                    # Mark for cancellation so the worker picks it up
                    self._cancelled_ids.add(queue_id)
                    job["status"] = "cancelled"
                    logging.info(f"Cancelling active download {queue_id}")
                    return True
            return False

    def is_cancelled(self, queue_id: int) -> bool:
        """Check whether a download has been cancelled."""
        return queue_id in self._cancelled_ids

    def _process_queue(self):
        """Background worker that processes the download queue with parallel execution"""
        while self.is_processing and not self._stop_event.is_set():
            try:
                # Get next queued download jobs (up to max_concurrent_downloads)
                jobs_to_start = []
                
                with self._queue_lock:
                    # Check how many slots are available
                    available_slots = self.max_concurrent_downloads - len(self.active_workers)
                    
                    if available_slots > 0:
                        # Get next queued jobs
                        for download in self._active_downloads.values():
                            if download["status"] == "queued" and len(jobs_to_start) < available_slots:
                                jobs_to_start.append(download)
                
                # Submit jobs to thread pool
                if jobs_to_start and self.thread_pool is not None:
                    for job in jobs_to_start:
                        # Check again before each submit in case of shutdown
                        if self._stop_event.is_set() or self.thread_pool is None:
                            break
                        # Mark as downloading
                        self._update_download_status(
                            job["id"], "downloading", current_episode="Starting download..."
                        )
                        # Submit to thread pool
                        try:
                            worker_future = self.thread_pool.submit(self._process_download_job, job)
                            self.active_workers.add(job["id"])

                            # Add callback to remove from active workers when done
                            worker_future.add_done_callback(
                                lambda f, job_id=job["id"]: self.active_workers.discard(job_id)
                            )
                        except RuntimeError as e:
                            # Thread pool was shut down between check and submit
                            logging.debug(f"Could not submit job {job['id']}: {e}")
                            break

                    logging.info(f"Started {len(jobs_to_start)} parallel download(s)")
                else:
                    # No jobs available or workers at max capacity, wait a bit
                    time.sleep(2)

            except Exception as e:
                logging.error(f"Error in queue processor: {e}")
                time.sleep(5)

    def _process_download_job(self, job):
        """Process a single download job (one episode)"""
        queue_id = job["id"]

        try:
            # Mark as downloading
            self._update_download_status(
                queue_id, "downloading", current_episode="Starting download..."
            )

            # Import necessary modules
            from ..entry import _group_episodes_by_series
            from ..models import Anime
            from pathlib import Path
            from ..action.common import sanitize_filename
            from .. import config
            import os

            # Process the single episode URL
            anime_list = _group_episodes_by_series(job["episode_urls"])

            if not anime_list:
                self._update_download_status(
                    queue_id, "failed", error_message="Failed to process episode URL"
                )
                return

            # Apply settings to anime objects
            provider = job["provider"]
            is_auto_provider = (provider == "auto" or not provider)

            for anime in anime_list:
                anime.language = job["language"]
                anime.action = "Download"
                if not is_auto_provider:
                    anime.provider = provider
                    for episode in anime.episode_list:
                        episode._selected_language = job["language"]
                        episode._selected_provider = provider
                else:
                    # Auto-provider: resolve working provider with timeout
                    anime.provider = "VOE"  # Fallback default
                    for episode in anime.episode_list:
                        episode._selected_language = job["language"]
                        resolved_provider = self._resolve_provider_with_timeout(
                            episode, job["language"], queue_id
                        )
                        if resolved_provider:
                            episode._selected_provider = resolved_provider
                            anime.provider = resolved_provider
                        else:
                            episode._selected_provider = "VOE"

            # Get download directory from arguments (which includes -o parameter)
            from ..parser import get_arguments
            arguments = get_arguments()

            download_dir = str(
                getattr(
                    config, "DEFAULT_DOWNLOAD_PATH", os.path.expanduser("~/Downloads")
                )
            )
            if hasattr(arguments, "output_dir") and arguments.output_dir is not None:
                download_dir = str(arguments.output_dir)

            # Download the episode
            successful = False
            
            for anime in anime_list:
                # Since this is a single episode job, episode_list should have exactly one element
                for episode in anime.episode_list:
                    if self._stop_event.is_set() or self.is_cancelled(queue_id):
                        if self.is_cancelled(queue_id):
                            self._update_download_status(
                                queue_id, "cancelled", error_message="Cancelled by user"
                            )
                            self._cancelled_ids.discard(queue_id)
                        break

                    episode_info = f"{anime.title} - Episode {episode.episode} (Season {episode.season})"

                    # Update progress
                    self._update_download_status(
                        queue_id,
                        "downloading",
                        current_episode=f"Downloading {episode_info}",
                        current_episode_progress=0.0,
                    )

                    try:
                        # Create temp anime with single episode
                        temp_anime = Anime(
                            title=anime.title,
                            slug=anime.slug,
                            site=anime.site,
                            language=anime.language,
                            provider=anime.provider,
                            action=anime.action,
                            episode_list=[episode],
                        )

                        # Create web progress callback for this specific download
                        def web_progress_callback(progress_data):
                            """Handle progress updates from yt-dlp and update web interface"""
                            try:
                                # Check if we should stop during download
                                if self._stop_event.is_set() or self.is_cancelled(queue_id):
                                    # Signal yt-dlp to stop by raising an exception
                                    raise KeyboardInterrupt("Download stopped by user")

                                if progress_data["status"] == "downloading":
                                    # Try multiple methods to extract progress percentage
                                    percentage = 0.0

                                    # Method 1: _percent_str field
                                    percent_str = progress_data.get("_percent_str")
                                    if percent_str:
                                        try:
                                            percentage = float(
                                                percent_str.replace("%", "")
                                            )
                                        except (ValueError, TypeError):
                                            pass

                                    # Method 2: Calculate from downloaded/total bytes
                                    if percentage == 0.0:
                                        downloaded = progress_data.get(
                                            "downloaded_bytes", 0
                                        )
                                        total = progress_data.get("total_bytes", 0)
                                        if total and total > 0:
                                            percentage = (downloaded / total) * 100

                                    # Method 3: Use fragment info if available
                                    if percentage == 0.0:
                                        fragment_index = progress_data.get(
                                            "fragment_index", 0
                                        )
                                        fragment_count = progress_data.get(
                                            "fragment_count", 0
                                        )
                                        if fragment_count and fragment_count > 0:
                                            percentage = (
                                                fragment_index / fragment_count
                                            ) * 100

                                    # Ensure percentage is valid
                                    percentage = min(100.0, max(0.0, percentage))

                                    # Create status message
                                    speed = progress_data.get("_speed_str", "N/A")
                                    eta = progress_data.get("_eta_str", "N/A")

                                    # Clean ANSI color codes from yt-dlp output
                                    import re

                                    if speed != "N/A":
                                        speed = re.sub(
                                            r"\x1b\[[0-9;]*m", "", str(speed)
                                        ).strip()
                                    if eta != "N/A":
                                        eta = re.sub(
                                            r"\x1b\[[0-9;]*m", "", str(eta)
                                        ).strip()

                                    status_msg = f"Downloading {episode_info} - {percentage:.1f}%"
                                    if speed != "N/A" and speed:
                                        status_msg += f" | Speed: {speed}"
                                    if eta != "N/A" and eta:
                                        status_msg += f" | ETA: {eta}"

                                    # Update episode progress
                                    self.update_episode_progress(
                                        queue_id, percentage, status_msg
                                    )

                                elif progress_data["status"] == "finished":
                                    logging.info(
                                        f"Episode finished for queue {queue_id}"
                                    )

                            except Exception as e:
                                logging.warning(f"Web progress callback error: {e}")

                        # Execute download and capture result
                        try:
                            # Check files before download to better detect success
                            from pathlib import Path

                            # Use the actual configured download directory
                            anime_download_dir = Path(download_dir) / sanitize_filename(
                                anime.title
                            )

                            # Count video files before download (recursively for season subdirs)
                            video_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.m4v', '.flv', '.wmv'}
                            files_before = 0
                            if anime_download_dir.exists():
                                files_before = len([f for f in anime_download_dir.rglob("*") if f.is_file() and f.suffix.lower() in video_extensions])

                            # Import and call the download function with progress callback
                            from ..action.download import download

                            download(temp_anime, web_progress_callback)

                            # Count video files after download (recursively for season subdirs)
                            files_after = 0
                            if anime_download_dir.exists():
                                files_after = len([f for f in anime_download_dir.rglob("*") if f.is_file() and f.suffix.lower() in video_extensions])

                            # Check if any new files were created
                            if files_after > files_before:
                                successful = True
                                logging.info(f"Downloaded: {episode_info}")

                                # Update completed episodes count
                                self._update_download_status(
                                    queue_id,
                                    "downloading",
                                    completed_episodes=1,
                                    current_episode=f"Completed {episode_info}",
                                    current_episode_progress=100.0,
                                )
                            else:
                                logging.warning(
                                    f"Failed to download: {episode_info} - No new files created"
                                )

                        except KeyboardInterrupt:
                            # HARD cancel path – yt-dlp was aborted via progress callback
                            logging.info(f"Download cancelled during execution for queue {queue_id}")

                            self._update_download_status(
                                queue_id,
                                "cancelled",
                                error_message="Cancelled by user",
                            )

                            self._cancelled_ids.discard(queue_id)
                            return
                        
                        except Exception as download_error:
                            import traceback
                            logging.warning(
                                f"Failed to download: {episode_info} - Error: {download_error}\n"
                                f"Traceback:\n{traceback.format_exc()}"
                            )

                    except Exception as e:
                        import traceback
                        logging.error(f"Error downloading {episode_info}: {e}\n{traceback.format_exc()}")

            # Final status update (skip if cancelled)
            if self.is_cancelled(queue_id):
                self._update_download_status(
                    queue_id,
                    "cancelled",
                    error_message="Cancelled by user",
                )
                self._cancelled_ids.discard(queue_id)
                return

            if successful:
                status = "completed"
                error_msg = f"Successfully downloaded episode"
            else:
                status = "failed"
                error_msg = f"Failed to download episode"

            self._update_download_status(
                queue_id,
                status,
                completed_episodes=1 if successful else 0,
                current_episode=error_msg,
                error_message=error_msg if status == "failed" else None,
            )

        except Exception as e:
            logging.error(f"Download job {queue_id} failed: {e}")
            self._update_download_status(
                queue_id, "failed", error_message=f"Download failed: {str(e)}"
            )


    def _resolve_provider_with_timeout(self, episode, language, queue_id, timeout_sec=5):
        """Try each supported provider with a timeout to find one that works.

        Args:
            episode: Episode object to resolve direct link for
            language: Language string
            queue_id: Queue ID for status updates
            timeout_sec: Seconds to wait per provider attempt

        Returns:
            Provider name that worked, or None if all failed
        """
        from ..config import SUPPORTED_PROVIDERS

        result_container = {}

        for provider_name in SUPPORTED_PROVIDERS:
            if self._stop_event.is_set() or self.is_cancelled(queue_id):
                return None

            self._update_download_status(
                queue_id, "downloading",
                current_episode=f"Trying provider {provider_name}..."
            )

            def try_provider(pname=provider_name):
                try:
                    link = episode.get_direct_link(provider=pname, language=language)
                    if link:
                        result_container["link"] = link
                        result_container["provider"] = pname
                except Exception as e:
                    logging.debug("Provider %s failed: %s", pname, e)

            t = threading.Thread(target=try_provider, daemon=True)
            t.start()
            t.join(timeout=timeout_sec)

            if "provider" in result_container:
                logging.info("Auto-provider resolved to '%s' for queue %s",
                             result_container["provider"], queue_id)
                # Reset episode state for actual download
                episode.direct_link = None
                episode.embeded_link = None
                episode.redirect_link = None
                return result_container["provider"]

            # Reset episode state before next attempt
            episode.direct_link = None
            episode.embeded_link = None
            episode.redirect_link = None
            logging.info("Provider %s timed out or failed for queue %s", provider_name, queue_id)

        return None

    def update_episode_progress(
        self, queue_id: int, episode_progress: float, current_episode_desc: str = None
    ):
        """Update the progress within the current episode"""
        with self._queue_lock:
            if queue_id not in self._active_downloads:
                return False

            download = self._active_downloads[queue_id]
            download["current_episode_progress"] = min(
                100.0, max(0.0, episode_progress)
            )

            if current_episode_desc:
                download["current_episode"] = current_episode_desc

            # Calculate overall progress: completed episodes + current episode progress
            completed = download["completed_episodes"]
            total = download["total_episodes"]
            if total > 0:
                current_episode_contribution = (
                    (episode_progress / 100.0) if episode_progress >= 0 else 0
                )
                new_progress = (completed + current_episode_contribution) / total * 100
                download["progress_percentage"] = new_progress

            return True

    def _update_download_status(
        self,
        queue_id: int,
        status: str,
        completed_episodes: int = None,
        current_episode: str = None,
        error_message: str = None,
        total_episodes: int = None,
        current_episode_progress: float = None,
    ):
        """Update the status of a download job"""
        with self._queue_lock:
            if queue_id not in self._active_downloads:
                return False

            download = self._active_downloads[queue_id]
            download["status"] = status

            if completed_episodes is not None:
                download["completed_episodes"] = completed_episodes
                # Calculate progress percentage - only use current episode progress if status is downloading and we haven't completed this episode yet
                total = download["total_episodes"]
                current_ep_progress = download.get("current_episode_progress", 0.0)

                if total > 0:
                    # For completed episodes, don't add extra current episode contribution
                    # since the episode is already counted as completed
                    if status == "downloading" and current_ep_progress < 100.0:
                        # Episode is in progress, add partial progress
                        current_episode_contribution = (
                            (current_ep_progress / 100.0)
                            if current_ep_progress >= 0
                            else 0
                        )
                        new_progress = (
                            (completed_episodes + current_episode_contribution)
                            / total
                            * 100
                        )
                    else:
                        # Episode is completed or we're not actively downloading, use completed count only
                        new_progress = completed_episodes / total * 100

                    download["progress_percentage"] = new_progress
                else:
                    download["progress_percentage"] = 0

            if current_episode is not None:
                download["current_episode"] = current_episode

            if current_episode_progress is not None:
                download["current_episode_progress"] = min(
                    100.0, max(0.0, current_episode_progress)
                )

                # If we're updating episode progress but not completed_episodes,
                # recalculate overall progress with current values
                if completed_episodes is None:
                    total = download["total_episodes"]
                    current_completed = download["completed_episodes"]
                    if total > 0:
                        # Only add current episode contribution if actively downloading and episode not yet completed
                        if status == "downloading" and current_episode_progress < 100.0:
                            current_episode_contribution = (
                                (current_episode_progress / 100.0)
                                if current_episode_progress >= 0
                                else 0
                            )
                            new_progress = (
                                (current_completed + current_episode_contribution)
                                / total
                                * 100
                            )
                        else:
                            # Use completed count only
                            new_progress = current_completed / total * 100

                        download["progress_percentage"] = new_progress

            if error_message is not None:
                download["error_message"] = error_message

            if total_episodes is not None:
                download["total_episodes"] = total_episodes

            # Update timestamps based on status
            if status == "downloading" and download["started_at"] is None:
                download["started_at"] = datetime.now()
            elif status in ["completed", "failed", "cancelled"]:
                download["completed_at"] = datetime.now()
                # Set final progress for completed downloads
                if status == "completed":
                    download["current_episode_progress"] = 100.0
                    download["progress_percentage"] = 100.0

                # Move to completed list and remove from active
                self._completed_downloads.append(download.copy())
                # Keep only recent completed downloads
                if len(self._completed_downloads) > self._max_completed_history:
                    self._completed_downloads = self._completed_downloads[
                        -self._max_completed_history :
                    ]

                # Remove from active downloads
                del self._active_downloads[queue_id]

            return True


# Global instance
_download_manager = None


def get_download_manager(
    database: Optional[UserDatabase] = None,
    max_concurrent_downloads: int = 3,
) -> DownloadQueueManager:
    """Get or create the global download manager instance
    
    Args:
        database: Optional UserDatabase instance for user authentication
        max_concurrent_downloads: Number of concurrent downloads (default: 3)
    
    Returns:
        DownloadQueueManager instance
    """
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadQueueManager(database, max_concurrent_downloads)
    return _download_manager
