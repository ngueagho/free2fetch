"""
Download engine for handling file downloads with progress tracking.
Python conversion of the original JavaScript download functionality.
"""

import os
import asyncio
import aiofiles
import aiohttp
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from urllib.parse import urlparse, unquote
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
from django.conf import settings

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Download status enumeration."""
    PENDING = "pending"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Download progress tracking."""
    total_size: int = 0
    downloaded_size: int = 0
    speed: float = 0.0  # bytes per second
    percentage: float = 0.0
    estimated_time_remaining: float = 0.0  # seconds
    start_time: float = field(default_factory=time.time)


@dataclass
class DownloadConfig:
    """Download configuration."""
    max_retries: int = 3
    retry_interval: float = 3.0  # seconds
    threads_count: int = 5
    timeout: float = 30.0  # seconds
    chunk_size: int = 8192
    range_start: int = 0
    range_end: int = 100


class DownloadEngine:
    """
    Multi-threaded download engine with progress tracking.
    Replicates the mt-files-downloader functionality.
    """

    def __init__(self, config: Optional[DownloadConfig] = None):
        """
        Initialize download engine.

        Args:
            config: Download configuration
        """
        self.config = config or DownloadConfig()
        self.downloads: Dict[str, 'DownloadTask'] = {}
        self._lock = threading.RLock()

    def download(self, url: str, file_path: str, progress_callback: Optional[Callable] = None) -> 'DownloadTask':
        """
        Start a new download.

        Args:
            url: URL to download
            file_path: Path to save file
            progress_callback: Callback for progress updates

        Returns:
            Download task instance
        """
        download_id = self._generate_download_id(url, file_path)

        with self._lock:
            if download_id in self.downloads:
                return self.downloads[download_id]

            task = DownloadTask(
                download_id=download_id,
                url=url,
                file_path=file_path,
                config=self.config,
                progress_callback=progress_callback
            )

            self.downloads[download_id] = task
            return task

    def resume_download(self, file_path: str) -> Optional['DownloadTask']:
        """
        Resume a paused download.

        Args:
            file_path: Path of the file to resume

        Returns:
            Download task if found and resumable
        """
        metadata_path = f"{file_path}.mtd"

        if not os.path.exists(metadata_path):
            return None

        try:
            # Read metadata to get original URL and config
            with open(metadata_path, 'r') as f:
                import json
                metadata = json.load(f)

            url = metadata.get('url')
            if not url:
                return None

            # Get existing downloaded size
            downloaded_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            task = self.download(url, file_path)
            task.progress.downloaded_size = downloaded_size
            task.status = DownloadStatus.PAUSED

            return task

        except Exception as e:
            logger.error(f"Failed to resume download for {file_path}: {e}")
            return None

    def _generate_download_id(self, url: str, file_path: str) -> str:
        """Generate unique download ID."""
        content = f"{url}:{file_path}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_download(self, download_id: str) -> Optional['DownloadTask']:
        """Get download task by ID."""
        return self.downloads.get(download_id)

    def pause_download(self, download_id: str) -> bool:
        """
        Pause a download.

        Args:
            download_id: Download ID to pause

        Returns:
            True if successfully paused
        """
        with self._lock:
            task = self.downloads.get(download_id)
            if task and task.status == DownloadStatus.DOWNLOADING:
                task.pause()
                return True
            return False

    def resume_download_by_id(self, download_id: str) -> bool:
        """
        Resume a paused download by ID.

        Args:
            download_id: Download ID to resume

        Returns:
            True if successfully resumed
        """
        with self._lock:
            task = self.downloads.get(download_id)
            if task and task.status == DownloadStatus.PAUSED:
                task.resume()
                return True
            return False

    def cancel_download(self, download_id: str) -> bool:
        """
        Cancel a download.

        Args:
            download_id: Download ID to cancel

        Returns:
            True if successfully cancelled
        """
        with self._lock:
            task = self.downloads.get(download_id)
            if task and task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED, DownloadStatus.PREPARING]:
                task.cancel()
                return True
            return False

    def get_active_downloads(self) -> List['DownloadTask']:
        """
        Get list of active downloads.

        Returns:
            List of active download tasks
        """
        with self._lock:
            return [
                task for task in self.downloads.values()
                if task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PREPARING]
            ]

    def cleanup_completed(self) -> int:
        """
        Remove completed downloads from memory.

        Returns:
            Number of downloads cleaned up
        """
        with self._lock:
            completed_ids = [
                download_id for download_id, task in self.downloads.items()
                if task.status in [DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED]
            ]

            for download_id in completed_ids:
                del self.downloads[download_id]

            return len(completed_ids)


class DownloadTask:
    """
    Individual download task with progress tracking and control.
    """

    def __init__(self, download_id: str, url: str, file_path: str, config: DownloadConfig, progress_callback: Optional[Callable] = None):
        """
        Initialize download task.

        Args:
            download_id: Unique download identifier
            url: URL to download
            file_path: Path to save file
            config: Download configuration
            progress_callback: Progress callback function
        """
        self.download_id = download_id
        self.url = url
        self.file_path = file_path
        self.config = config
        self.progress_callback = progress_callback

        self.status = DownloadStatus.PENDING
        self.progress = DownloadProgress()
        self.error_message = ""
        self.retry_count = 0

        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """
        Start the download.
        """
        if self.status == DownloadStatus.PENDING:
            self.status = DownloadStatus.PREPARING
            self._thread = threading.Thread(target=self._download_worker, daemon=True)
            self._thread.start()

    def pause(self) -> None:
        """
        Pause the download.
        """
        if self.status == DownloadStatus.DOWNLOADING:
            self._pause_event.set()
            self.status = DownloadStatus.PAUSED

    def resume(self) -> None:
        """
        Resume the download.
        """
        if self.status == DownloadStatus.PAUSED:
            self._pause_event.clear()
            self.status = DownloadStatus.DOWNLOADING
            if self._thread and not self._thread.is_alive():
                self._thread = threading.Thread(target=self._download_worker, daemon=True)
                self._thread.start()

    def cancel(self) -> None:
        """
        Cancel the download.
        """
        self._cancel_event.set()
        self.status = DownloadStatus.CANCELLED

    def _download_worker(self) -> None:
        """
        Main download worker thread.
        """
        try:
            # Prepare download directory
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            # Check if file already exists and get size
            downloaded_size = 0
            if os.path.exists(self.file_path):
                downloaded_size = os.path.getsize(self.file_path)
                self.progress.downloaded_size = downloaded_size

            # Get file info from server
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; UdemyDownloader/1.0)'}
            if downloaded_size > 0:
                headers['Range'] = f'bytes={downloaded_size}-'

            # Start download
            self.status = DownloadStatus.DOWNLOADING
            self._download_with_requests(headers, downloaded_size)

        except Exception as e:
            logger.error(f"Download failed for {self.url}: {e}")
            self.error_message = str(e)
            if self.retry_count < self.config.max_retries:
                self.retry_count += 1
                logger.info(f"Retrying download ({self.retry_count}/{self.config.max_retries})...")
                time.sleep(self.config.retry_interval)
                self._download_worker()
            else:
                self.status = DownloadStatus.FAILED

    def _download_with_requests(self, headers: Dict[str, str], resume_size: int) -> None:
        """
        Download file using requests with progress tracking.

        Args:
            headers: HTTP headers
            resume_size: Size to resume from
        """
        import requests

        try:
            with requests.get(self.url, headers=headers, stream=True, timeout=self.config.timeout) as response:
                response.raise_for_status()

                # Get total file size
                content_length = response.headers.get('content-length')
                if content_length:
                    self.progress.total_size = resume_size + int(content_length)
                else:
                    self.progress.total_size = 0

                # Save metadata for resumable downloads
                self._save_metadata()

                # Open file in append mode if resuming
                mode = 'ab' if resume_size > 0 else 'wb'
                with open(self.file_path, mode) as file:
                    start_time = time.time()
                    last_update = start_time

                    for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                        # Check for cancellation
                        if self._cancel_event.is_set():
                            return

                        # Check for pause
                        while self._pause_event.is_set():
                            time.sleep(0.1)
                            if self._cancel_event.is_set():
                                return

                        if chunk:
                            file.write(chunk)
                            self.progress.downloaded_size += len(chunk)

                            # Update progress periodically
                            current_time = time.time()
                            if current_time - last_update >= 0.5:  # Update every 500ms
                                self._update_progress(current_time - start_time)
                                last_update = current_time

                # Final progress update
                self._update_progress(time.time() - start_time)

                # Mark as completed
                if not self._cancel_event.is_set():
                    self.status = DownloadStatus.COMPLETED
                    self.progress.percentage = 100.0
                    self._cleanup_metadata()
                    if self.progress_callback:
                        self.progress_callback(self)

        except requests.RequestException as e:
            logger.error(f"HTTP error downloading {self.url}: {e}")
            raise

    def _update_progress(self, elapsed_time: float) -> None:
        """
        Update download progress and call callback.

        Args:
            elapsed_time: Time elapsed since start
        """
        if self.progress.total_size > 0:
            self.progress.percentage = (self.progress.downloaded_size / self.progress.total_size) * 100

        # Calculate speed
        if elapsed_time > 0:
            self.progress.speed = self.progress.downloaded_size / elapsed_time

            # Calculate ETA
            if self.progress.speed > 0 and self.progress.total_size > 0:
                remaining_bytes = self.progress.total_size - self.progress.downloaded_size
                self.progress.estimated_time_remaining = remaining_bytes / self.progress.speed

        # Call progress callback
        if self.progress_callback:
            self.progress_callback(self)

    def _save_metadata(self) -> None:
        """
        Save download metadata for resume capability.
        """
        metadata = {
            'url': self.url,
            'total_size': self.progress.total_size,
            'downloaded_size': self.progress.downloaded_size,
            'timestamp': time.time()
        }

        metadata_path = f"{self.file_path}.mtd"
        try:
            with open(metadata_path, 'w') as f:
                import json
                json.dump(metadata, f)
        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")

    def _cleanup_metadata(self) -> None:
        """
        Remove metadata file after successful completion.
        """
        metadata_path = f"{self.file_path}.mtd"
        try:
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup metadata: {e}")

    def get_formatted_speed(self) -> str:
        """
        Get formatted download speed string.

        Returns:
            Formatted speed (e.g., "2.5 MB/s")
        """
        speed = self.progress.speed
        if speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed / (1024 * 1024):.1f} MB/s"
        else:
            return f"{speed / (1024 * 1024 * 1024):.1f} GB/s"

    def get_formatted_eta(self) -> str:
        """
        Get formatted estimated time remaining.

        Returns:
            Formatted ETA (e.g., "05:30")
        """
        eta = self.progress.estimated_time_remaining
        if eta <= 0:
            return "--:--"

        hours = int(eta // 3600)
        minutes = int((eta % 3600) // 60)
        seconds = int(eta % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"


class M3U8Downloader:
    """
    Specialized downloader for M3U8 playlists.
    """

    def __init__(self, config: Optional[DownloadConfig] = None):
        """Initialize M3U8 downloader."""
        self.config = config or DownloadConfig()
        self.download_engine = DownloadEngine(config)

    async def download_m3u8(self, m3u8_url: str, output_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Download M3U8 playlist and combine segments.

        Args:
            m3u8_url: M3U8 playlist URL
            output_path: Output file path
            progress_callback: Progress callback

        Returns:
            True if successful
        """
        try:
            from .m3u8_service import M3U8Service

            # Parse M3U8 playlist
            m3u8_service = M3U8Service(m3u8_url)
            segments = await m3u8_service.get_segments()

            if not segments:
                raise Exception("No segments found in M3U8 playlist")

            # Download all segments
            temp_dir = f"{output_path}.tmp"
            os.makedirs(temp_dir, exist_ok=True)

            segment_files = []
            for i, segment_url in enumerate(segments):
                segment_path = os.path.join(temp_dir, f"segment_{i:04d}.ts")
                task = self.download_engine.download(segment_url, segment_path)
                task.start()
                segment_files.append(segment_path)

                # Wait for completion
                while task.status not in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                    await asyncio.sleep(0.1)

                if task.status != DownloadStatus.COMPLETED:
                    raise Exception(f"Failed to download segment {i}: {task.error_message}")

                # Update progress
                if progress_callback:
                    overall_progress = (i + 1) / len(segments) * 100
                    progress_callback({'percentage': overall_progress, 'segment': i + 1, 'total_segments': len(segments)})

            # Combine segments
            await self._combine_segments(segment_files, output_path)

            # Cleanup temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

            return True

        except Exception as e:
            logger.error(f"Failed to download M3U8 {m3u8_url}: {e}")
            return False

    async def _combine_segments(self, segment_files: List[str], output_path: str) -> None:
        """
        Combine downloaded segments into single file.

        Args:
            segment_files: List of segment file paths
            output_path: Output file path
        """
        with open(output_path, 'wb') as output_file:
            for segment_file in segment_files:
                if os.path.exists(segment_file):
                    with open(segment_file, 'rb') as f:
                        output_file.write(f.read())

    def cancel_all_downloads(self):
        """Cancel all active downloads."""
        with self._lock:
            for task in self.downloads.values():
                task.cancel()


class DownloadTask:
    """
    Individual download task with multi-threaded downloading.
    """

    def __init__(self, download_id: str, url: str, file_path: str, config: DownloadConfig, progress_callback: Optional[Callable] = None):
        """
        Initialize download task.

        Args:
            download_id: Unique download ID
            url: URL to download
            file_path: Path to save file
            config: Download configuration
            progress_callback: Progress callback function
        """
        self.download_id = download_id
        self.url = url
        self.file_path = file_path
        self.config = config
        self.progress_callback = progress_callback

        self.status = DownloadStatus.PENDING
        self.progress = DownloadProgress()
        self.error_message = ""

        self._session: Optional[aiohttp.ClientSession] = None
        self._download_task: Optional[asyncio.Task] = None
        self._cancelled = threading.Event()
        self._paused = threading.Event()

    async def start(self) -> bool:
        """
        Start the download.

        Returns:
            True if download completed successfully
        """
        try:
            self.status = DownloadStatus.PREPARING
            self._notify_progress()

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            # Check if file already exists and is complete
            if await self._is_file_complete():
                self.status = DownloadStatus.COMPLETED
                self.progress.percentage = 100.0
                self._notify_progress()
                return True

            self.status = DownloadStatus.DOWNLOADING
            self._notify_progress()

            # Start download with retry logic
            for attempt in range(self.config.max_retries):
                try:
                    success = await self._download_with_progress()
                    if success:
                        await self._finalize_download()
                        return True

                except Exception as e:
                    logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                    self.error_message = str(e)

                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_interval)
                    else:
                        self.status = DownloadStatus.FAILED
                        self._notify_progress()
                        return False

            return False

        except Exception as e:
            logger.error(f"Download failed for {self.url}: {e}")
            self.status = DownloadStatus.FAILED
            self.error_message = str(e)
            self._notify_progress()
            return False

    async def pause(self):
        """Pause the download."""
        self._paused.set()
        if self.status == DownloadStatus.DOWNLOADING:
            self.status = DownloadStatus.PAUSED
            self._notify_progress()

    async def resume(self):
        """Resume the download."""
        self._paused.clear()
        if self.status == DownloadStatus.PAUSED:
            self.status = DownloadStatus.DOWNLOADING
            self._notify_progress()

    def cancel(self):
        """Cancel the download."""
        self._cancelled.set()
        self._paused.clear()
        if self._download_task and not self._download_task.done():
            self._download_task.cancel()

        self.status = DownloadStatus.CANCELLED
        self._notify_progress()

    async def _is_file_complete(self) -> bool:
        """Check if file is already completely downloaded."""
        if not os.path.exists(self.file_path):
            return False

        try:
            # Get remote file size
            async with aiohttp.ClientSession() as session:
                async with session.head(self.url) as response:
                    if response.status == 200:
                        remote_size = int(response.headers.get('Content-Length', 0))
                        local_size = os.path.getsize(self.file_path)
                        return remote_size > 0 and local_size == remote_size
        except Exception:
            pass

        return False

    async def _download_with_progress(self) -> bool:
        """Download file with progress tracking."""
        temp_file_path = f"{self.file_path}.tmp"
        metadata_path = f"{self.file_path}.mtd"

        # Check for existing partial download
        resume_position = 0
        if os.path.exists(temp_file_path):
            resume_position = os.path.getsize(temp_file_path)
            self.progress.downloaded_size = resume_position

        headers = {}
        if resume_position > 0:
            headers['Range'] = f'bytes={resume_position}-'

        # Save metadata for resume capability
        await self._save_metadata(metadata_path)

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
            self._session = session

            async with session.get(self.url, headers=headers) as response:
                if response.status not in [200, 206]:  # 206 = Partial Content
                    raise Exception(f"HTTP {response.status}: {response.reason}")

                # Get total file size
                if response.status == 200:
                    self.progress.total_size = int(response.headers.get('Content-Length', 0))
                    # If we're resuming but got 200, start over
                    if resume_position > 0:
                        resume_position = 0
                        self.progress.downloaded_size = 0
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                else:  # 206 Partial Content
                    content_range = response.headers.get('Content-Range', '')
                    if content_range:
                        # Parse "bytes start-end/total"
                        total_size = int(content_range.split('/')[-1])
                        self.progress.total_size = total_size

                # Open file for writing
                mode = 'ab' if resume_position > 0 else 'wb'

                async with aiofiles.open(temp_file_path, mode) as f:
                    start_time = time.time()
                    last_update = start_time

                    async for chunk in response.content.iter_chunked(self.config.chunk_size):
                        # Check for cancellation or pause
                        if self._cancelled.is_set():
                            return False

                        while self._paused.is_set() and not self._cancelled.is_set():
                            await asyncio.sleep(0.1)

                        if self._cancelled.is_set():
                            return False

                        await f.write(chunk)
                        self.progress.downloaded_size += len(chunk)

                        # Update progress periodically
                        current_time = time.time()
                        if current_time - last_update >= 0.5:  # Update every 500ms
                            await self._update_progress_stats(start_time, current_time)
                            self._notify_progress()
                            last_update = current_time

        # Move temp file to final location
        if os.path.exists(temp_file_path):
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            os.rename(temp_file_path, self.file_path)

        # Clean up metadata
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        return True

    async def _update_progress_stats(self, start_time: float, current_time: float):
        """Update progress statistics."""
        elapsed_time = current_time - start_time

        if elapsed_time > 0:
            self.progress.speed = self.progress.downloaded_size / elapsed_time

        if self.progress.total_size > 0:
            self.progress.percentage = (self.progress.downloaded_size / self.progress.total_size) * 100

            # Estimate remaining time
            if self.progress.speed > 0:
                remaining_bytes = self.progress.total_size - self.progress.downloaded_size
                self.progress.estimated_time_remaining = remaining_bytes / self.progress.speed

    async def _save_metadata(self, metadata_path: str):
        """Save download metadata for resume capability."""
        metadata = {
            'url': self.url,
            'file_path': self.file_path,
            'start_time': self.progress.start_time,
            'config': {
                'max_retries': self.config.max_retries,
                'retry_interval': self.config.retry_interval,
                'threads_count': self.config.threads_count,
                'timeout': self.config.timeout,
            }
        }

        try:
            async with aiofiles.open(metadata_path, 'w') as f:
                import json
                await f.write(json.dumps(metadata, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")

    async def _finalize_download(self):
        """Finalize successful download."""
        self.status = DownloadStatus.COMPLETED
        self.progress.percentage = 100.0

        # Clean up temporary files
        temp_files = [f"{self.file_path}.tmp", f"{self.file_path}.mtd"]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_file}: {e}")

        self._notify_progress()

    def _notify_progress(self):
        """Notify progress callback of updates."""
        if self.progress_callback:
            try:
                self.progress_callback({
                    'download_id': self.download_id,
                    'status': self.status.value,
                    'progress': {
                        'total_size': self.progress.total_size,
                        'downloaded_size': self.progress.downloaded_size,
                        'percentage': self.progress.percentage,
                        'speed': self.progress.speed,
                        'estimated_time_remaining': self.progress.estimated_time_remaining,
                    },
                    'error_message': self.error_message
                })
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current download statistics."""
        return {
            'download_id': self.download_id,
            'url': self.url,
            'file_path': self.file_path,
            'status': self.status.value,
            'total_size': self.progress.total_size,
            'downloaded_size': self.progress.downloaded_size,
            'percentage': self.progress.percentage,
            'speed': self.progress.speed,
            'estimated_time_remaining': self.progress.estimated_time_remaining,
            'error_message': self.error_message
        }


class M3U8Downloader:
    """
    Specialized downloader for M3U8/HLS streams.
    Handles chunked downloading and stream assembly.
    """

    def __init__(self, config: Optional[DownloadConfig] = None):
        """Initialize M3U8 downloader."""
        self.config = config or DownloadConfig()

    async def download_m3u8_stream(self, playlist_url: str, output_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Download M3U8 stream by fetching individual segments.

        Args:
            playlist_url: M3U8 playlist URL
            output_path: Output file path
            progress_callback: Progress callback

        Returns:
            True if download successful
        """
        try:
            from .m3u8_service import M3U8Service

            # Parse M3U8 playlist
            m3u8_service = M3U8Service(playlist_url)
            segments = await self._get_stream_segments(playlist_url)

            if not segments:
                raise Exception("No segments found in M3U8 playlist")

            # Download segments in chunks
            chunk_size = 100  # Process 100 segments at a time
            total_segments = len(segments)
            downloaded_segments = 0

            # Create output file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            async with aiofiles.open(output_path, 'wb') as output_file:
                for i in range(0, total_segments, chunk_size):
                    chunk_segments = segments[i:i + chunk_size]

                    # Download chunk segments
                    segment_data = await self._download_segments_chunk(chunk_segments, progress_callback)

                    # Write to file
                    for data in segment_data:
                        if data:
                            await output_file.write(data)

                    downloaded_segments += len(chunk_segments)

                    # Update progress
                    if progress_callback:
                        progress_callback({
                            'type': 'segment_progress',
                            'downloaded_segments': downloaded_segments,
                            'total_segments': total_segments,
                            'percentage': (downloaded_segments / total_segments) * 100
                        })

            return True

        except Exception as e:
            logger.error(f"M3U8 download failed: {e}")
            return False

    async def _get_stream_segments(self, playlist_url: str) -> List[str]:
        """Get list of segment URLs from M3U8 playlist."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(playlist_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch playlist: HTTP {response.status}")

                    playlist_content = await response.text()

                    # Extract .ts segment URLs
                    lines = playlist_content.strip().split('\n')
                    segments = []

                    for line in lines:
                        line = line.strip()
                        if line.endswith('.ts'):
                            # Convert relative URLs to absolute
                            if not line.startswith('http'):
                                from urllib.parse import urljoin
                                line = urljoin(playlist_url, line)
                            segments.append(line)

                    return segments

        except Exception as e:
            logger.error(f"Failed to parse M3U8 segments: {e}")
            return []

    async def _download_segments_chunk(self, segment_urls: List[str], progress_callback: Optional[Callable] = None) -> List[bytes]:
        """Download a chunk of segments concurrently."""
        async def download_segment(url: str) -> bytes:
            try:
                async with aiohttp.ClientSession() as session:
                    start_time = time.time()

                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.read()

                            # Calculate speed for this segment
                            elapsed_time = time.time() - start_time
                            if progress_callback and elapsed_time > 0:
                                speed = len(data) / elapsed_time
                                progress_callback({
                                    'type': 'segment_downloaded',
                                    'url': url,
                                    'size': len(data),
                                    'speed': speed
                                })

                            return data
                        else:
                            logger.warning(f"Failed to download segment {url}: HTTP {response.status}")
                            return b''

            except Exception as e:
                logger.warning(f"Error downloading segment {url}: {e}")
                return b''

        # Download all segments in this chunk concurrently
        tasks = [download_segment(url) for url in segment_urls]
        return await asyncio.gather(*tasks)