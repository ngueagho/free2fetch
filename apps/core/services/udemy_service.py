"""
Udemy service for interacting with Udemy API.
Python conversion of the original JavaScript UdemyService.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse, parse_qs
from django.core.cache import cache
from django.conf import settings
from .m3u8_service import M3U8Service

logger = logging.getLogger(__name__)


class UdemyServiceError(Exception):
    """Base exception for Udemy service errors."""
    pass


class UdemyService:
    """
    Udemy service for API interactions.
    Replicates all functionality from the original JavaScript service.
    """

    def __init__(self, access_token: str = None, subdomain: str = "www", http_timeout: int = 40):
        """
        Initialize Udemy service.

        Args:
            access_token: Udemy API access token
            subdomain: Udemy subdomain (www for regular, company name for business)
            http_timeout: HTTP request timeout in seconds
        """
        self.access_token = access_token
        self.subdomain = (subdomain.strip() or "www").lower()
        self.http_timeout = http_timeout
        self.base_url = f"https://{self.subdomain}.udemy.com"
        self.api_base = f"{self.base_url}/api-2.0"
        self.login_url = f"{self.base_url}/join/login-popup"

        # API endpoints
        self.courses_url = "/users/me/subscribed-courses"
        self.enrolled_courses_url = "/users/me/subscription-course-enrollments"
        self.assets_fields = "&fields[asset]=asset_type,title,filename,body,captions,media_sources,stream_urls,download_urls,external_url,media_license_token"

        # Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-Udemy-Authorization': f'Bearer {access_token}' if access_token else '',
        }
        self.auth_headers = {}

        # Set authorization headers
        if access_token:
            self.set_access_token(access_token)

        # Cache settings (1 hour TTL like original)
        self.cache_ttl = 3600

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL."""
        return f"udemy_service:{hash(url)}"

    async def _fetch_url(self, url: str, method: str = "GET", use_cache: bool = True) -> Dict[str, Any]:
        """
        Fetch URL with caching support.

        Args:
            url: URL to fetch
            method: HTTP method
            use_cache: Whether to use cache

        Returns:
            Response data as dictionary

        Raises:
            UdemyServiceError: If request fails
        """
        # Check cache first
        if use_cache and method == "GET":
            cache_key = self._get_cache_key(url)
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit: {url}")
                return cached_data

        logger.debug(f"Fetching URL: {url}")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.http_timeout)) as session:
                headers = {**self.headers, **self.auth_headers}

                async with session.request(method, url, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise UdemyServiceError(f"HTTP {response.status}: {error_text}")

                    data = await response.json()

                    # Cache successful GET requests
                    if use_cache and method == "GET":
                        cache_key = self._get_cache_key(url)
                        cache.set(cache_key, data, timeout=self.cache_ttl)

                    return data

        except aiohttp.ClientError as e:
            logger.error(f"Error fetching URL {url}: {e}")
            raise UdemyServiceError(f"Request failed: {e}")

    async def _fetch_endpoint(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """
        Fetch API endpoint.

        Args:
            endpoint: API endpoint path
            method: HTTP method

        Returns:
            Response data
        """
        url = urljoin(self.api_base, endpoint)
        return await self._fetch_url(url, method)

    def set_access_token(self, access_token: str) -> None:
        """
        Set access token for authentication.

        Args:
            access_token: Udemy access token
        """
        self.access_token = access_token
        self.auth_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Udemy-Authorization': f'Bearer {access_token}'
        }

    def get_user_profile_sync(self) -> Optional[Dict[str, Any]]:
        """
        Synchronous wrapper for fetching user profile.

        Returns:
            User profile data or None if authentication fails
        """
        if not self.access_token:
            return None

        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.fetch_profile(self.access_token))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Failed to fetch user profile: {e}")
            return None

    async def fetch_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user profile to validate token.

        Args:
            access_token: Udemy access token

        Returns:
            User profile data

        Raises:
            UdemyServiceError: If profile fetch fails
        """
        self.set_access_token(access_token)
        return await self._fetch_endpoint("/contexts/me/?header=True")

    async def fetch_courses(self, page_size: int = 30, is_subscriber: bool = False) -> Dict[str, Any]:
        """
        Fetch user's courses.

        Args:
            page_size: Number of courses per page
            is_subscriber: Whether to fetch subscriber courses

        Returns:
            Courses data with pagination
        """
        page_size = max(page_size, 10)
        params = f"page_size={page_size}&ordering=-last_accessed"

        courses_endpoint = f"{self.courses_url}?{params}"
        enrolled_endpoint = f"{self.enrolled_courses_url}?{params}"

        if is_subscriber:
            # Fetch both regular and enrolled courses in parallel
            courses_task = self._fetch_endpoint(courses_endpoint)
            enrolled_task = self._fetch_endpoint(enrolled_endpoint)

            courses_data, enrolled_data = await asyncio.gather(courses_task, enrolled_task)

            # Combine results
            next_urls = [url for url in [courses_data.get('next'), enrolled_data.get('next')] if url]
            previous_urls = [url for url in [courses_data.get('previous'), enrolled_data.get('previous')] if url]

            return {
                'count': courses_data.get('count', 0) + enrolled_data.get('count', 0),
                'next': next_urls if next_urls else None,
                'previous': previous_urls if previous_urls else None,
                'results': courses_data.get('results', []) + enrolled_data.get('results', [])
            }
        else:
            return await self._fetch_endpoint(courses_endpoint)

    async def fetch_search_courses(self, keyword: str, page_size: int = 25, is_subscriber: bool = False) -> Dict[str, Any]:
        """
        Search courses by keyword.

        Args:
            keyword: Search keyword
            page_size: Number of results per page
            is_subscriber: Whether to search in subscriber courses

        Returns:
            Search results
        """
        if not keyword:
            return await self.fetch_courses(page_size, is_subscriber)

        page_size = max(page_size, 10)
        params = f"page=1&ordering=title&fields[user]=job_title&page_size={page_size}&search={keyword}"

        courses_endpoint = f"{self.courses_url}?{params}"
        enrolled_endpoint = f"{self.enrolled_courses_url}?{params}"

        if is_subscriber:
            courses_task = self._fetch_endpoint(courses_endpoint)
            enrolled_task = self._fetch_endpoint(enrolled_endpoint)

            courses_data, enrolled_data = await asyncio.gather(courses_task, enrolled_task)

            next_urls = [url for url in [courses_data.get('next'), enrolled_data.get('next')] if url]
            previous_urls = [url for url in [courses_data.get('previous'), enrolled_data.get('previous')] if url]

            return {
                'count': courses_data.get('count', 0) + enrolled_data.get('count', 0),
                'next': next_urls if next_urls else None,
                'previous': previous_urls if previous_urls else None,
                'results': courses_data.get('results', []) + enrolled_data.get('results', [])
            }
        else:
            return await self._fetch_endpoint(courses_endpoint)

    async def fetch_load_more(self, url: str) -> Dict[str, Any]:
        """
        Fetch more results from pagination URL.

        Args:
            url: Pagination URL

        Returns:
            Additional results
        """
        return await self._fetch_url(url)

    async def fetch_course_content(self, course_id: int, content_type: str = "all") -> Optional[Dict[str, Any]]:
        """
        Fetch complete course content structure.

        Args:
            course_id: Course ID
            content_type: Type of content to fetch ('all', 'lectures', 'attachments', 'less')

        Returns:
            Course content data or None if not found
        """
        # Build URL with appropriate fields
        url = f"{self.base_url}/api-2.0/courses/{course_id}/cached-subscriber-curriculum-items?page_size=200"

        content_type = (content_type or "less").lower()

        if content_type != "less":
            url += "&fields[lecture]=id,title"

        if content_type == "all":
            url += ",asset,supplementary_assets"
        elif content_type == "lectures":
            url += ",asset"
        elif content_type == "attachments":
            url += ",supplementary_assets"

        if content_type != "less":
            url += self.assets_fields

        try:
            # Fetch all paginated content
            all_results = []
            current_url = url

            while current_url:
                data = await self._fetch_url(current_url)

                if not data:
                    return None

                all_results.extend(data.get('results', []))
                current_url = data.get('next')

                # Decode URL if needed
                if current_url:
                    current_url = current_url.replace('%5B', '[').replace('%5D', ']').replace('%2C', ',')

            # Combine all results
            content_data = {
                'count': len(all_results),
                'results': all_results,
                'next': None,
                'previous': None
            }

        except UdemyServiceError as e:
            if "503" in str(e):  # Service unavailable, try fallback
                return await self.fetch_course_fallback(course_id)
            raise

        if not content_data or content_data['count'] == 0:
            return None

        # Ensure first item is a chapter
        if content_data['results'] and content_data['results'][0].get('_class') != 'chapter':
            content_data['results'].insert(0, {
                'id': 0,
                '_class': 'chapter',
                'title': 'Chapter 1'
            })
            content_data['count'] += 1

        # Fetch detailed lecture data if needed
        if content_type in ['all', 'lectures', 'attachments']:
            await self._enrich_lecture_data(course_id, content_data['results'])

        # Prepare stream sources
        await self._prepare_streams_source(course_id, content_data['results'])

        return content_data

    async def fetch_course_fallback(self, course_id: int) -> Dict[str, Any]:
        """
        Fallback method for fetching course when main method fails.

        Args:
            course_id: Course ID

        Returns:
            Basic course data
        """
        endpoint = f"/courses/{course_id}/cached-subscriber-curriculum-items?page_size=10000&fields[lecture]=id,title,asset"
        return await self._fetch_endpoint(endpoint)

    async def fetch_lecture(self, course_id: int, lecture_id: int, get_attachments: bool = False, all_assets: bool = False) -> Dict[str, Any]:
        """
        Fetch detailed lecture data.

        Args:
            course_id: Course ID
            lecture_id: Lecture ID
            get_attachments: Whether to fetch attachments
            all_assets: Whether to fetch all asset fields

        Returns:
            Lecture data
        """
        endpoint = f"/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}?fields[lecture]=id,title,asset"

        if get_attachments:
            endpoint += ",supplementary_assets"

        if all_assets:
            endpoint += "&fields[asset]=@all"
        else:
            endpoint += self.assets_fields

        return await self._fetch_endpoint(endpoint)

    async def _enrich_lecture_data(self, course_id: int, results: List[Dict[str, Any]]) -> None:
        """
        Enrich lecture data by fetching detailed information.

        Args:
            course_id: Course ID
            results: List of course items to enrich
        """
        lecture_tasks = []
        lecture_indices = []

        for i, item in enumerate(results):
            if item.get('_class') == 'lecture':
                task = self.fetch_lecture(course_id, item['id'], True, False)
                lecture_tasks.append(task)
                lecture_indices.append(i)

        if lecture_tasks:
            lecture_data_list = await asyncio.gather(*lecture_tasks, return_exceptions=True)

            for lecture_data, index in zip(lecture_data_list, lecture_indices):
                if not isinstance(lecture_data, Exception):
                    results[index]['asset'] = lecture_data.get('asset', {})
                    results[index]['supplementary_assets'] = lecture_data.get('supplementary_assets', [])

    async def _prepare_streams_source(self, course_id: int, items: List[Dict[str, Any]]) -> None:
        """
        Prepare stream sources for video content.

        Args:
            course_id: Course ID
            items: List of items to process
        """
        tasks = []
        for item in items:
            if item.get('_class') == 'lecture':
                tasks.append(self._prepare_stream_source(course_id, item))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _prepare_stream_source(self, course_id: int, lecture: Dict[str, Any]) -> None:
        """
        Prepare stream source for a single lecture.

        Args:
            course_id: Course ID
            lecture: Lecture data to process
        """
        try:
            if lecture.get('_class') != 'lecture':
                return

            asset = lecture.get('asset', {})
            asset_type = asset.get('asset_type', '').lower()

            if asset_type in ['video', 'videomashup']:
                stream_urls = asset.get('stream_urls', {}).get('Video') or asset.get('media_sources', [])
                is_encrypted = bool(asset.get('media_license_token'))

                if stream_urls:
                    streams = await self._convert_to_streams(stream_urls, is_encrypted, asset.get('title', ''))

                    # Remove original stream data and add processed streams
                    asset.pop('stream_urls', None)
                    asset.pop('media_sources', None)
                    asset['streams'] = streams

            elif asset_type == 'presentation':
                # Fetch detailed presentation data
                detailed_lecture = await self.fetch_lecture(course_id, lecture['id'], True, True)
                lecture['asset'] = detailed_lecture.get('asset', {})
                lecture['supplementary_assets'] = detailed_lecture.get('supplementary_assets', [])

        except Exception as e:
            logger.warning(f"Failed to prepare stream source for lecture {lecture.get('id')}: {e}")

    async def _convert_to_streams(self, stream_urls: List[Dict[str, Any]], is_encrypted: bool, title: str = "") -> Dict[str, Any]:
        """
        Convert stream URLs to standardized format.

        Args:
            stream_urls: List of stream URL data
            is_encrypted: Whether content is encrypted
            title: Content title for logging

        Returns:
            Standardized streams data
        """
        try:
            if not stream_urls:
                raise UdemyServiceError("No streams found to convert")

            sources = {}
            min_quality = float('inf')
            max_quality = float('-inf')

            # Filter out encrypted streams if not encrypted
            if not is_encrypted:
                filtered_streams = [
                    stream for stream in stream_urls
                    if '/encrypted-files' not in (stream.get('file') or stream.get('src', ''))
                ]
                is_encrypted = len(filtered_streams) == 0
                stream_urls = filtered_streams if filtered_streams else stream_urls

            # Process each stream
            for video in stream_urls:
                video_type = video.get('type')

                if video_type == 'application/dash+xml':
                    continue  # Skip DASH streams

                quality = video.get('label', '').lower()
                url = video.get('file') or video.get('src')

                if not url:
                    continue

                sources[quality] = {
                    'type': video_type,
                    'url': url
                }

                # Track quality range
                if quality != 'auto':
                    try:
                        numeric_quality = int(quality)
                        min_quality = min(min_quality, numeric_quality)
                        max_quality = max(max_quality, numeric_quality)
                    except (ValueError, TypeError):
                        pass
                else:
                    # Handle auto quality with M3U8
                    if not is_encrypted:
                        try:
                            m3u8_service = M3U8Service(url)
                            playlist = await m3u8_service.load_playlist()

                            for item in playlist:
                                item_quality = item['quality']
                                min_quality = min(min_quality, item_quality)
                                max_quality = max(max_quality, item_quality)

                                quality_key = str(item_quality)
                                if quality_key not in sources:
                                    sources[quality_key] = {
                                        'type': video_type,
                                        'url': item['url']
                                    }
                        except Exception as e:
                            logger.warning(f"Failed to process M3U8 playlist for {title}: {e}")

            # Finalize quality range
            min_quality_str = str(int(min_quality)) if min_quality != float('inf') else ('auto' if 'auto' in sources else None)
            max_quality_str = str(int(max_quality)) if max_quality != float('-inf') else ('auto' if 'auto' in sources else None)

            return {
                'minQuality': min_quality_str,
                'maxQuality': max_quality_str,
                'isEncrypted': is_encrypted,
                'sources': sources
            }

        except Exception as e:
            logger.error(f"Error converting streams for {title}: {e}")
            raise UdemyServiceError(f"Stream conversion failed: {e}")

    @property
    def url_base(self) -> str:
        """Get base URL."""
        return self.base_url

    @property
    def url_login(self) -> str:
        """Get login URL."""
        return self.login_url