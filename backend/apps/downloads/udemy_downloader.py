import asyncio
import aiohttp
import aiofiles
import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path
import m3u8
from ..accounts.oauth import get_udemy_service

logger = logging.getLogger(__name__)

class UdemyDownloader:
    """
    Service for downloading Udemy course content
    """

    def __init__(self, access_token: str, max_concurrent_downloads: int = 3):
        self.access_token = access_token
        self.max_concurrent_downloads = max_concurrent_downloads
        self.session = None
        self.udemy_service = get_udemy_service()

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=50)
        timeout = aiohttp.ClientTimeout(total=300)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Authorization': f'Bearer {self.access_token}'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_course_curriculum(self, course_id: str) -> Dict[str, Any]:
        """
        Get course curriculum with download URLs
        """
        try:
            url = f'https://www.udemy.com/api-2.0/courses/{course_id}/cached-subscriber-curriculum-items'
            params = {
                'page_size': 10000,
                'fields[lecture]': 'id,title,asset,supplementary_assets',
                'fields[asset]': 'asset_type,title,filename,body,captions,media_sources,stream_urls,download_urls,external_url,media_license_token'
            }

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

            # Process curriculum items to extract downloadable content
            processed_curriculum = await self._process_curriculum_items(course_id, data.get('results', []))

            return {
                'course_id': course_id,
                'curriculum': processed_curriculum,
                'total_items': len([item for item in processed_curriculum if item.get('downloadable')])
            }

        except Exception as e:
            logger.error(f'Error getting course curriculum {course_id}: {e}')
            raise

    async def _process_curriculum_items(self, course_id: str, items: List[Dict]) -> List[Dict]:
        """
        Process curriculum items to extract downloadable content
        """
        processed_items = []

        for item in items:
            if item.get('_class') == 'lecture' and item.get('asset'):
                asset = item['asset']
                asset_type = asset.get('asset_type', '').lower()

                processed_item = {
                    'id': item['id'],
                    'title': item.get('title', ''),
                    'type': asset_type,
                    'downloadable': False,
                    'download_urls': [],
                    'subtitles': [],
                    'supplementary_assets': []
                }

                if asset_type in ['video', 'videomashup']:
                    # Process video content
                    video_urls = await self._extract_video_urls(asset)
                    processed_item['download_urls'] = video_urls
                    processed_item['downloadable'] = len(video_urls) > 0

                    # Extract subtitles
                    if asset.get('captions'):
                        processed_item['subtitles'] = self._extract_subtitles(asset['captions'])

                elif asset_type == 'article':
                    # Process article content
                    processed_item['content'] = asset.get('body', '')
                    processed_item['downloadable'] = True

                elif asset_type in ['file', 'sourceCode']:
                    # Process downloadable files
                    download_urls = asset.get('download_urls', {})
                    if download_urls:
                        processed_item['download_urls'] = [
                            {
                                'quality': 'file',
                                'url': list(download_urls.values())[0].get('file', ''),
                                'type': 'file'
                            }
                        ]
                        processed_item['downloadable'] = True

                # Process supplementary assets
                if item.get('supplementary_assets'):
                    supplementary = await self._process_supplementary_assets(
                        course_id, item['id'], item['supplementary_assets']
                    )
                    processed_item['supplementary_assets'] = supplementary

                processed_items.append(processed_item)

            elif item.get('_class') == 'chapter':
                processed_items.append({
                    'id': item['id'],
                    'title': item.get('title', ''),
                    'type': 'chapter',
                    'downloadable': False
                })

        return processed_items

    async def _extract_video_urls(self, asset: Dict) -> List[Dict]:
        """
        Extract video download URLs from asset
        """
        video_urls = []

        # Check for stream URLs
        stream_urls = asset.get('stream_urls', {}).get('Video', [])
        if not stream_urls:
            stream_urls = asset.get('media_sources', [])

        # Check if content is encrypted
        is_encrypted = bool(asset.get('media_license_token'))

        if stream_urls:
            # Filter out encrypted URLs if possible
            if is_encrypted:
                filtered_urls = [url for url in stream_urls if '/encrypted-files' not in url.get('file', '')]
                if filtered_urls:
                    stream_urls = filtered_urls
                    is_encrypted = False

            for stream in stream_urls:
                if stream.get('type') != 'application/dash+xml':
                    quality = stream.get('label', 'auto').lower()
                    url = stream.get('file') or stream.get('src')

                    if url:
                        if quality == 'auto' and not is_encrypted:
                            # Parse M3U8 playlist for quality options
                            playlist_urls = await self._parse_m3u8_playlist(url)
                            video_urls.extend(playlist_urls)
                        else:
                            video_urls.append({
                                'quality': quality,
                                'url': url,
                                'type': stream.get('type', 'video/mp4'),
                                'encrypted': is_encrypted
                            })

        return video_urls

    async def _parse_m3u8_playlist(self, playlist_url: str) -> List[Dict]:
        """
        Parse M3U8 playlist to extract quality variants
        """
        try:
            async with self.session.get(playlist_url) as response:
                response.raise_for_status()
                playlist_content = await response.text()

            playlist = m3u8.loads(playlist_content, uri=playlist_url)
            quality_urls = []

            if playlist.is_variant:
                for variant in playlist.playlists:
                    resolution = variant.stream_info.resolution
                    if resolution:
                        quality = str(resolution[1])  # Height as quality
                        quality_urls.append({
                            'quality': quality,
                            'url': urljoin(playlist_url, variant.uri),
                            'type': 'application/x-mpegURL'
                        })

            return quality_urls

        except Exception as e:
            logger.error(f'Error parsing M3U8 playlist {playlist_url}: {e}')
            return []

    def _extract_subtitles(self, captions: List[Dict]) -> List[Dict]:
        """
        Extract subtitle information
        """
        subtitles = []
        for caption in captions:
            subtitles.append({
                'language': caption.get('locale_id', 'en'),
                'language_name': caption.get('title', 'English'),
                'url': caption.get('url', ''),
                'file_name': f"{caption.get('locale_id', 'en')}.srt"
            })
        return subtitles

    async def _process_supplementary_assets(self, course_id: str, lecture_id: str, assets: List[Dict]) -> List[Dict]:
        """
        Process supplementary assets (attachments)
        """
        supplementary = []
        for asset in assets:
            supplementary.append({
                'id': asset.get('id'),
                'title': asset.get('title', ''),
                'filename': asset.get('filename', ''),
                'download_url': asset.get('download_urls', {}).get('File', [{}])[0].get('file', ''),
                'file_size': asset.get('file_size', 0)
            })
        return supplementary

    async def download_course(self, course_id: str, output_dir: str,
                            quality: str = '720p',
                            download_subtitles: bool = True,
                            download_attachments: bool = True,
                            progress_callback=None) -> Dict[str, Any]:
        """
        Download complete course
        """
        try:
            # Create course directory
            course_dir = Path(output_dir) / f'course_{course_id}'
            course_dir.mkdir(parents=True, exist_ok=True)

            # Get course curriculum
            curriculum_data = await self.get_course_curriculum(course_id)
            curriculum = curriculum_data['curriculum']

            # Filter downloadable items
            downloadable_items = [item for item in curriculum if item.get('downloadable')]

            total_items = len(downloadable_items)
            completed_items = 0
            failed_items = []

            logger.info(f'Starting download of course {course_id}: {total_items} items')

            # Create semaphore for concurrent downloads
            semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

            async def download_item(item):
                nonlocal completed_items
                async with semaphore:
                    try:
                        await self._download_curriculum_item(
                            item, course_dir, quality, download_subtitles, download_attachments
                        )
                        completed_items += 1

                        if progress_callback:
                            await progress_callback(completed_items, total_items)

                    except Exception as e:
                        logger.error(f'Error downloading item {item["title"]}: {e}')
                        failed_items.append({
                            'item_id': item['id'],
                            'title': item['title'],
                            'error': str(e)
                        })

            # Download all items concurrently
            tasks = [download_item(item) for item in downloadable_items]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Save course metadata
            await self._save_course_metadata(course_dir, curriculum_data, quality)

            result = {
                'course_id': course_id,
                'total_items': total_items,
                'completed_items': completed_items,
                'failed_items': failed_items,
                'download_path': str(course_dir),
                'success': len(failed_items) == 0
            }

            logger.info(f'Course download completed: {completed_items}/{total_items} items')
            return result

        except Exception as e:
            logger.error(f'Error downloading course {course_id}: {e}')
            raise

    async def _download_curriculum_item(self, item: Dict, course_dir: Path,
                                      quality: str, download_subtitles: bool,
                                      download_attachments: bool):
        """
        Download individual curriculum item
        """
        item_type = item.get('type')
        item_title = self._sanitize_filename(item.get('title', ''))

        if item_type in ['video', 'videomashup']:
            await self._download_video(item, course_dir, item_title, quality)

            if download_subtitles and item.get('subtitles'):
                await self._download_subtitles(item['subtitles'], course_dir, item_title)

        elif item_type == 'article':
            await self._save_article(item, course_dir, item_title)

        elif item_type in ['file', 'sourceCode']:
            await self._download_file(item, course_dir, item_title)

        # Download supplementary assets
        if download_attachments and item.get('supplementary_assets'):
            attachments_dir = course_dir / 'attachments' / item_title
            attachments_dir.mkdir(parents=True, exist_ok=True)

            for asset in item['supplementary_assets']:
                await self._download_attachment(asset, attachments_dir)

    async def _download_video(self, item: Dict, course_dir: Path, item_title: str, preferred_quality: str):
        """
        Download video content
        """
        download_urls = item.get('download_urls', [])
        if not download_urls:
            return

        # Find best quality match
        selected_url = self._select_video_quality(download_urls, preferred_quality)

        if not selected_url:
            return

        # Create video directory
        videos_dir = course_dir / 'videos'
        videos_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension
        url = selected_url['url']
        if selected_url['type'] == 'application/x-mpegURL':
            # M3U8 stream - need to download segments
            await self._download_m3u8_stream(url, videos_dir / f'{item_title}.mp4')
        else:
            # Direct video download
            file_extension = self._get_file_extension(url)
            await self._download_file_from_url(url, videos_dir / f'{item_title}{file_extension}')

    def _select_video_quality(self, download_urls: List[Dict], preferred_quality: str) -> Optional[Dict]:
        """
        Select best video quality from available options
        """
        # Create quality preference order
        quality_preferences = [preferred_quality, '720p', '480p', '1080p', '360p', 'auto']

        for quality in quality_preferences:
            for url_info in download_urls:
                if url_info.get('quality') == quality and not url_info.get('encrypted', False):
                    return url_info

        # If no preference match, return first non-encrypted URL
        for url_info in download_urls:
            if not url_info.get('encrypted', False):
                return url_info

        return None

    async def _download_m3u8_stream(self, playlist_url: str, output_path: Path):
        """
        Download M3U8 stream by downloading segments and concatenating
        """
        try:
            async with self.session.get(playlist_url) as response:
                response.raise_for_status()
                playlist_content = await response.text()

            playlist = m3u8.loads(playlist_content, uri=playlist_url)

            if playlist.is_variant:
                # Get highest quality variant
                best_variant = max(playlist.playlists, key=lambda x: x.stream_info.bandwidth or 0)
                playlist_url = urljoin(playlist_url, best_variant.uri)

                # Load the actual playlist
                async with self.session.get(playlist_url) as response:
                    response.raise_for_status()
                    playlist_content = await response.text()
                playlist = m3u8.loads(playlist_content, uri=playlist_url)

            # Download segments
            segments = []
            base_url = playlist_url.rsplit('/', 1)[0] + '/'

            for segment in playlist.segments:
                segment_url = urljoin(base_url, segment.uri)
                segments.append(segment_url)

            # Download segments concurrently
            segment_data = []
            semaphore = asyncio.Semaphore(5)  # Limit concurrent segment downloads

            async def download_segment(url, index):
                async with semaphore:
                    async with self.session.get(url) as response:
                        response.raise_for_status()
                        data = await response.read()
                        return index, data

            tasks = [download_segment(url, i) for i, url in enumerate(segments)]
            results = await asyncio.gather(*tasks)

            # Sort by index and concatenate
            results.sort(key=lambda x: x[0])

            async with aiofiles.open(output_path, 'wb') as f:
                for _, data in results:
                    await f.write(data)

        except Exception as e:
            logger.error(f'Error downloading M3U8 stream {playlist_url}: {e}')
            raise

    async def _download_file_from_url(self, url: str, output_path: Path):
        """
        Download file from URL
        """
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()

                async with aiofiles.open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)

        except Exception as e:
            logger.error(f'Error downloading file {url}: {e}')
            raise

    async def _download_subtitles(self, subtitles: List[Dict], course_dir: Path, item_title: str):
        """
        Download subtitle files
        """
        subtitles_dir = course_dir / 'subtitles' / item_title
        subtitles_dir.mkdir(parents=True, exist_ok=True)

        for subtitle in subtitles:
            url = subtitle.get('url')
            if url:
                file_name = subtitle.get('file_name', f"{subtitle.get('language', 'en')}.srt")
                await self._download_file_from_url(url, subtitles_dir / file_name)

    async def _download_file(self, item: Dict, course_dir: Path, item_title: str):
        """
        Download file asset
        """
        download_urls = item.get('download_urls', [])
        if not download_urls:
            return

        url = download_urls[0].get('url')
        if url:
            files_dir = course_dir / 'files'
            files_dir.mkdir(parents=True, exist_ok=True)

            file_extension = self._get_file_extension(url)
            await self._download_file_from_url(url, files_dir / f'{item_title}{file_extension}')

    async def _download_attachment(self, asset: Dict, attachments_dir: Path):
        """
        Download supplementary attachment
        """
        url = asset.get('download_url')
        filename = asset.get('filename', f"attachment_{asset.get('id', '')}")

        if url and filename:
            await self._download_file_from_url(url, attachments_dir / filename)

    async def _save_article(self, item: Dict, course_dir: Path, item_title: str):
        """
        Save article content as HTML file
        """
        content = item.get('content', '')
        if content:
            articles_dir = course_dir / 'articles'
            articles_dir.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(articles_dir / f'{item_title}.html', 'w', encoding='utf-8') as f:
                await f.write(content)

    async def _save_course_metadata(self, course_dir: Path, curriculum_data: Dict, quality: str):
        """
        Save course metadata
        """
        metadata = {
            'course_id': curriculum_data['course_id'],
            'total_items': curriculum_data['total_items'],
            'download_quality': quality,
            'curriculum': curriculum_data['curriculum']
        }

        async with aiofiles.open(course_dir / 'metadata.json', 'w') as f:
            await f.write(json.dumps(metadata, indent=2))

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe file system usage
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        return filename[:100]  # Limit length

    def _get_file_extension(self, url: str) -> str:
        """
        Extract file extension from URL
        """
        parsed = urlparse(url)
        path = parsed.path
        extension = os.path.splitext(path)[1]
        return extension if extension else '.mp4'