"""
Utility functions for the core services.
Python conversion of the original JavaScript utility functions.
"""

import os
import re
import math
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from urllib.parse import quote, unquote
import logging

logger = logging.getLogger(__name__)


class Utils:
    """Utility functions class."""

    @staticmethod
    def is_number(value: Any) -> bool:
        """
        Check if value is a number.

        Args:
            value: Value to check

        Returns:
            True if value is a number
        """
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def to_boolean(value: Any) -> bool:
        """
        Convert value to boolean.

        Args:
            value: Value to convert

        Returns:
            Boolean representation
        """
        if Utils.is_number(value):
            return not re.match(r'^0$', str(value), re.IGNORECASE)
        return bool(re.match(r'^true$', str(value), re.IGNORECASE))

    @staticmethod
    def dynamic_sort(property_name: str):
        """
        Create a sort function for dynamic property sorting.

        Args:
            property_name: Property name to sort by (prefix with '-' for descending)

        Returns:
            Sort function for use with sorted()
        """
        sort_order = 1
        if property_name.startswith('-'):
            sort_order = -1
            property_name = property_name[1:]

        def sort_function(a: Dict[str, Any], b: Dict[str, Any]) -> int:
            prop_a = a.get(property_name, '')
            prop_b = b.get(property_name, '')

            if sort_order == -1:
                if prop_a < prop_b:
                    return 1
                elif prop_a > prop_b:
                    return -1
                return 0
            else:
                if prop_a < prop_b:
                    return -1
                elif prop_a > prop_b:
                    return 1
                return 0

        return sort_function

    @staticmethod
    def zero_pad(num: int, max_val: int) -> str:
        """
        Pad number with leading zeros.

        Args:
            num: Number to pad
            max_val: Maximum value to determine padding length

        Returns:
            Zero-padded string
        """
        digits = math.floor(math.log10(max_val) + 1) if max_val > 0 else 1
        return str(num).zfill(digits)

    @staticmethod
    def get_sequence_name(
        index: int,
        count: int,
        name: str,
        separator_index: str = ". ",
        path: Optional[str] = None,
        seq_zero_left: bool = False
    ) -> Dict[str, str]:
        """
        Generate sequence name with optional zero padding.

        Args:
            index: Sequence index
            count: Total count
            name: Base name
            separator_index: Separator between index and name
            path: Optional base path
            seq_zero_left: Whether to use zero padding

        Returns:
            Dict with 'name' and 'fullPath' keys
        """
        from django.utils.text import slugify

        # Sanitize name
        sanitized_name = Utils.sanitize_filename(name)

        # Create both index and sequence versions
        index_name = f"{index}{separator_index}{sanitized_name}"
        sequence_name = f"{Utils.zero_pad(index, count)}{separator_index}{sanitized_name}"

        # Build paths
        index_path = os.path.join(path, index_name) if path else index_name
        sequence_path = os.path.join(path, sequence_name) if path else sequence_name

        if index_path == sequence_path:
            return {'name': index_name, 'fullPath': index_path}

        if seq_zero_left:
            # Use sequence format (with leading zeros)
            if os.path.exists(index_path):
                try:
                    os.rename(index_path, sequence_path)
                except OSError as e:
                    logger.warning(f"Failed to rename {index_path} to {sequence_path}: {e}")

            return {'name': sequence_name, 'fullPath': sequence_path}
        else:
            # Use index format (no leading zeros)
            if os.path.exists(sequence_path):
                try:
                    os.rename(sequence_path, index_path)
                except OSError as e:
                    logger.warning(f"Failed to rename {sequence_path} to {index_path}: {e}")

            return {'name': index_name, 'fullPath': index_path}

    @staticmethod
    def sanitize_filename(filename: str, replacement: str = "-") -> str:
        """
        Sanitize filename for filesystem compatibility.

        Args:
            filename: Filename to sanitize
            replacement: Character to replace invalid chars with

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, replacement, filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')

        # Limit length (255 is common filesystem limit)
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            max_name_length = 255 - len(ext)
            sanitized = name[:max_name_length] + ext

        return sanitized or "unnamed"

    @staticmethod
    def get_download_speed(bytes_per_second: float) -> Dict[str, Union[float, str]]:
        """
        Calculate human-readable download speed.

        Args:
            bytes_per_second: Speed in bytes per second

        Returns:
            Dict with 'value' and 'unit' keys
        """
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        bytes_per_kb = 1024

        speed = float(bytes_per_second)
        unit_index = 0

        if speed >= bytes_per_kb:
            if speed >= bytes_per_kb ** 3:
                unit_index = 3
            elif speed >= bytes_per_kb ** 2:
                unit_index = 2
            else:
                unit_index = 1

            speed /= bytes_per_kb ** unit_index

        return {
            'value': round(speed, 2),
            'unit': units[unit_index]
        }

    @staticmethod
    def paginate(array: List[Any], page_size: int, page_number: int) -> List[Any]:
        """
        Paginate array.

        Args:
            array: Array to paginate
            page_size: Items per page
            page_number: Page number (1-based)

        Returns:
            Paginated subset of array
        """
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        return array[start_index:end_index]

    @staticmethod
    async def sleep(milliseconds: int):
        """
        Async sleep for given milliseconds.

        Args:
            milliseconds: Sleep duration in milliseconds
        """
        await asyncio.sleep(milliseconds / 1000.0)

    @staticmethod
    def new_error(name: str, message: str = "") -> Exception:
        """
        Create new exception with custom name.

        Args:
            name: Error name
            message: Error message

        Returns:
            Exception instance
        """
        error = Exception(message)
        error.__class__.__name__ = name
        return error

    @staticmethod
    def get_closest_value(obj: Dict[str, Any], target: Union[int, float]) -> Dict[str, Any]:
        """
        Get the value in object closest to target.

        Args:
            obj: Dictionary of values
            target: Target value

        Returns:
            Dict with 'key' and 'value' of closest match
        """
        try:
            numeric_keys = []
            for key in obj.keys():
                try:
                    numeric_keys.append((float(key), key))
                except (ValueError, TypeError):
                    continue

            if not numeric_keys:
                # If no numeric keys, return first item
                first_key = next(iter(obj))
                return {'key': first_key, 'value': obj[first_key]}

            # Find closest numeric key
            closest_distance = float('inf')
            closest_key = None

            for numeric_value, original_key in numeric_keys:
                distance = abs(numeric_value - target)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_key = original_key

            return {'key': closest_key, 'value': obj[closest_key]}

        except Exception as e:
            logger.warning(f"Error finding closest value: {e}")
            # Return first item as fallback
            first_key = next(iter(obj))
            return {'key': first_key, 'value': obj[first_key]}

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)

        return f"{s} {size_names[i]}"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}h {minutes}m {secs}s"

    @staticmethod
    def ensure_directory_exists(path: str):
        """
        Ensure directory exists, create if it doesn't.

        Args:
            path: Directory path
        """
        Path(path).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_file_extension(url: str) -> str:
        """
        Get file extension from URL.

        Args:
            url: URL to extract extension from

        Returns:
            File extension (without dot)
        """
        try:
            from urllib.parse import urlparse, unquote
            parsed_url = urlparse(url)
            path = unquote(parsed_url.path)
            _, ext = os.path.splitext(path)
            return ext.lstrip('.').lower()
        except Exception:
            return ""

    @staticmethod
    def is_video_url(url: str) -> bool:
        """
        Check if URL points to a video file.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a video
        """
        video_extensions = {
            'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', 'ogv', '3gp'
        }
        extension = Utils.get_file_extension(url)
        return extension in video_extensions

    @staticmethod
    def is_encrypted_url(url: str) -> bool:
        """
        Check if URL points to encrypted content.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be encrypted
        """
        return '/encrypted-files' in url

    @staticmethod
    def get_timestamp() -> float:
        """Get current timestamp."""
        return time.time()

    @staticmethod
    def timestamp_to_string(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Convert timestamp to formatted string.

        Args:
            timestamp: Unix timestamp
            format_str: Format string

        Returns:
            Formatted date string
        """
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime(format_str)