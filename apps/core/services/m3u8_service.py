"""
M3U8 service for handling HLS playlists.
Python conversion of the original JavaScript M3U8Service.
"""

import re
import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class M3U8ServiceError(Exception):
    """Base exception for M3U8 service errors."""
    pass


class M3U8Service:
    """
    M3U8 service for parsing and handling HLS playlists.
    Replicates functionality from the original JavaScript service.
    """

    def __init__(self, m3u8_url: str):
        """
        Initialize M3U8 service.

        Args:
            m3u8_url: URL of the M3U8 playlist

        Raises:
            M3U8ServiceError: If URL is invalid
        """
        if not self._is_valid_url(m3u8_url):
            raise M3U8ServiceError("Invalid URL")

        self.m3u8_url = m3u8_url
        self.playlist: List[Dict[str, Any]] = []

    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid
        """
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _is_valid_m3u8_content(self, content: str) -> bool:
        """
        Check if content is valid M3U8 playlist.

        Args:
            content: Content to validate

        Returns:
            True if content is valid M3U8
        """
        return content.strip().startswith("#EXTM3U")

    def _extract_urls_and_qualities(self, m3u8_content: str) -> List[Dict[str, Any]]:
        """
        Extract URLs and qualities from M3U8 playlist content.

        Args:
            m3u8_content: M3U8 playlist content

        Returns:
            List of extracted stream information
        """
        lines = m3u8_content.strip().split('\n')
        urls_and_qualities = []

        current_resolution = None
        current_quality = None

        for line in lines:
            line = line.strip()

            if line.startswith('#EXT-X-STREAM-INF'):
                # Extract resolution from stream info
                match = re.search(r'RESOLUTION=(\d+x\d+)', line)
                if match:
                    current_resolution = match.group(1)
                    # Extract height as quality
                    width, height = current_resolution.split('x')
                    current_quality = int(height)

            elif line.startswith('http'):
                if current_resolution and current_quality:
                    urls_and_qualities.append({
                        'quality': current_quality,
                        'resolution': current_resolution,
                        'url': line
                    })
                    # Reset for next stream
                    current_resolution = None
                    current_quality = None

        return urls_and_qualities

    @staticmethod
    async def get_file(url: str, is_binary: bool = False, max_retries: int = 3) -> str:
        """
        Fetch file from URL with retry logic.

        Args:
            url: URL to fetch
            is_binary: Whether file is binary (not used in this implementation)
            max_retries: Maximum number of retry attempts

        Returns:
            File content as string

        Raises:
            M3U8ServiceError: If file fetch fails after retries
        """
        retries = 0

        while retries < max_retries:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise aiohttp.ClientError(f"HTTP {response.status}: {response.reason}")

                        if is_binary:
                            return await response.read()
                        else:
                            return await response.text()

            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    break

                logger.warning(f"Retry {retries}/{max_retries} for {url}: {e}")
                await asyncio.sleep(1)  # Wait before retry

        raise M3U8ServiceError("Failed to load file after multiple attempts")

    async def load_playlist(self, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Load and parse M3U8 playlist.

        Args:
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed playlist data

        Raises:
            M3U8ServiceError: If playlist loading fails
        """
        try:
            playlist_content = await self.get_file(self.m3u8_url, False, max_retries)

            if not self._is_valid_m3u8_content(playlist_content):
                raise M3U8ServiceError("Invalid M3U8 playlist content")

            self.playlist = self._extract_urls_and_qualities(playlist_content)
            return self.playlist

        except Exception as e:
            logger.error(f"Failed to load playlist from {self.m3u8_url}: {e}")
            raise M3U8ServiceError(f"Playlist loading failed: {e}")

    def get_playlist(self) -> List[Dict[str, Any]]:
        """
        Get the current playlist.

        Returns:
            Current playlist data
        """
        return self.playlist

    def _sort_playlist_by_quality(self, ascending: bool = True) -> List[Dict[str, Any]]:
        """
        Sort playlist by quality.

        Args:
            ascending: Sort in ascending order if True

        Returns:
            Sorted playlist
        """
        return sorted(
            self.playlist,
            key=lambda x: x['quality'],
            reverse=not ascending
        )

    def get_highest_quality(self) -> Optional[Dict[str, Any]]:
        """
        Get highest quality stream from playlist.

        Returns:
            Highest quality stream or None if playlist is empty
        """
        if not self.playlist:
            return None

        return self._sort_playlist_by_quality(ascending=False)[0]

    def get_lowest_quality(self) -> Optional[Dict[str, Any]]:
        """
        Get lowest quality stream from playlist.

        Returns:
            Lowest quality stream or None if playlist is empty
        """
        if not self.playlist:
            return None

        return self._sort_playlist_by_quality(ascending=True)[0]

    def get_quality(self, target_quality: int) -> Optional[Dict[str, Any]]:
        """
        Get stream with specific quality or closest match.

        Args:
            target_quality: Target quality (height in pixels)

        Returns:
            Stream with requested or closest quality
        """
        if not self.playlist:
            return None

        # Try to find exact match first
        for stream in self.playlist:
            if stream['quality'] == target_quality:
                return stream

        # Find closest quality
        closest_stream = None
        smallest_diff = float('inf')

        for stream in self.playlist:
            diff = abs(stream['quality'] - target_quality)
            if diff < smallest_diff:
                smallest_diff = diff
                closest_stream = stream

        return closest_stream

    def get_available_qualities(self) -> List[int]:
        """
        Get list of available qualities.

        Returns:
            List of available quality values
        """
        return sorted(list(set(stream['quality'] for stream in self.playlist)))

    def __str__(self) -> str:
        """String representation of the service."""
        return f"M3U8Service(url={self.m3u8_url}, streams={len(self.playlist)})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()