"""
Celery tasks for download management.
"""

import asyncio
import logging
import os
import json
from pathlib import Path
# Removed typing imports to avoid errors
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from .models import DownloadTask, DownloadItem, DownloadHistory
from apps.courses.models import Course, UserCourse
from apps.core.services.download_engine import DownloadEngine, DownloadConfig, M3U8Downloader
from apps.core.services.udemy_service import UdemyService, UdemyServiceError
# from apps.core.services.utils import Utils  # Utils not implemented yet
from apps.core.services.m3u8_service import M3U8Service

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def download_course_task(self, download_task_id: str, user_id: int):
    """
    Main task for downloading a complete course.
    Replicates the original JavaScript download functionality.
    """
    try:
        # Get download task
        download_task = DownloadTask.objects.get(id=download_task_id)
        download_task.status = 'preparing'
        download_task.started_at = timezone.now()
        download_task.celery_task_id = self.request.id
        download_task.save()

        # Send progress update
        send_progress_update(download_task_id, 'preparing', 0, 'Preparing download...')

        # Fetch course content
        course_data = asyncio.run(fetch_course_content_for_download(download_task))
        if not course_data:
            raise Exception("Failed to fetch course content")

        # Prepare download items
        download_items = prepare_download_items(download_task, course_data)
        if not download_items:
            raise Exception("No downloadable items found")

        # Update task with total items
        download_task.total_items = len(download_items)
        download_task.status = 'downloading'
        download_task.save()

        # Send progress update
        send_progress_update(download_task_id, 'downloading', 0, f'Starting download of {len(download_items)} items...')

        # Initialize download engine
        download_engine = DownloadEngine(DownloadConfig(
            max_retries=3,
            retry_interval=3.0,
            threads_count=5,
            timeout=30.0
        ))

        # Download each item
        completed_items = 0
        for item in download_items:
            try:
                if download_task.refresh_from_db() and download_task.status == 'cancelled':
                    break

                # Download the item
                success = asyncio.run(download_single_item(download_engine, item, download_task))

                if success:
                    item.status = 'completed'
                    item.completed_at = timezone.now()
                    completed_items += 1
                else:
                    item.status = 'failed'
                    download_task.failed_items += 1

                item.save()

                # Update progress
                download_task.downloaded_items = completed_items
                download_task.progress_percentage = (completed_items / len(download_items)) * 100
                download_task.save()

                # Send progress update
                progress_message = f'Downloaded {completed_items}/{len(download_items)} items'
                send_progress_update(
                    download_task_id,
                    'downloading',
                    download_task.progress_percentage,
                    progress_message
                )

            except Exception as e:
                logger.error(f"Failed to download item {item.filename}: {e}")
                item.status = 'failed'
                item.error_message = str(e)
                item.save()

                download_task.failed_items += 1
                download_task.save()

        # Finalize download
        if download_task.status != 'cancelled':
            if download_task.failed_items == 0:
                download_task.status = 'completed'
                progress_message = 'Download completed successfully!'
            else:
                download_task.status = 'completed'
                progress_message = f'Download completed with {download_task.failed_items} failed items'

            download_task.completed_at = timezone.now()
            download_task.progress_percentage = 100.0
            download_task.save()

            # Update download history
            update_download_history(download_task)

            # Send completion notification
            send_progress_update(download_task_id, download_task.status, 100.0, progress_message)

            # Send browser notification if applicable
            send_download_notification(download_task)

    except Exception as e:
        logger.error(f"Download task {download_task_id} failed: {e}")

        # Update task status
        try:
            download_task = DownloadTask.objects.get(id=download_task_id)
            download_task.status = 'failed'
            download_task.error_message = str(e)
            download_task.save()

            # Send failure notification
            send_progress_update(download_task_id, 'failed', 0, f'Download failed: {str(e)}')

        except Exception:
            pass


async def fetch_course_content_for_download(download_task):
    """
    Fetch course content from Udemy API for download preparation.

    Args:
        download_task: Download task instance

    Returns:
        Course curriculum data or None if failed
    """
    try:
        user = download_task.user
        course = download_task.course

        # Initialize Udemy service
        udemy_service = UdemyService(
            user.udemy_access_token,
            user.udemy_subdomain
        )

        # Fetch complete curriculum
        curriculum = await udemy_service.fetch_course_full_curriculum(course.udemy_id)

        return curriculum

    except UdemyServiceError as e:
        logger.error(f"Udemy API error fetching course content: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching course content: {e}")
        return None


def prepare_download_items(download_task, course_data):
    """
    Prepare download items from course curriculum data.

    Args:
        download_task: Download task instance
        course_data: Course curriculum data

    Returns:
        List of download items
    """
    items = []
    curriculum_items = course_data.get('results', [])

    # Apply range filtering if enabled
    if download_task.enable_range_download:
        start_idx = max(0, download_task.download_start - 1)
        end_idx = download_task.download_end if download_task.download_end > 0 else len(curriculum_items)
        curriculum_items = curriculum_items[start_idx:end_idx]

    item_index = 1

    for curriculum_item in curriculum_items:
        if curriculum_item.get('_class') == 'lecture':
            lecture_items = process_lecture_for_download(
                download_task,
                curriculum_item,
                item_index
            )
            items.extend(lecture_items)
            item_index += len(lecture_items)

    return items


def process_lecture_for_download(download_task, lecture_data, start_index):
    """
    Process a lecture for download preparation.

    Args:
        download_task: Download task instance
        lecture_data: Lecture data from curriculum
        start_index: Starting index for items

    Returns:
        List of download items for this lecture
    """
    items = []
    asset = lecture_data.get('asset', {})

    if not asset:
        return items

    # Get or create lecture model
    from apps.courses.models import Lecture
    try:
        lecture = Lecture.objects.get(udemy_id=lecture_data['id'])
    except Lecture.DoesNotExist:
        lecture = None

    # Process main video asset
    if asset.get('asset_type') in ['Video', 'VideoMashup'] and download_task.download_type in [0, 1]:
        video_item = create_video_download_item(
            download_task,
            lecture_data,
            asset,
            lecture,
            start_index
        )
        if video_item:
            items.append(video_item)

    # Process supplementary assets (attachments)
    if download_task.download_type in [0, 2]:
        supplementary_assets = lecture_data.get('supplementary_assets', [])
        for i, supp_asset in enumerate(supplementary_assets):
            attachment_item = create_attachment_download_item(
                download_task,
                lecture_data,
                supp_asset,
                lecture,
                start_index + len(items) + i + 1
            )
            if attachment_item:
                items.append(attachment_item)

    # Process subtitles if not skipped
    if not download_task.user.preferences.skip_subtitles and asset.get('captions'):
        subtitle_items = create_subtitle_download_items(
            download_task,
            lecture_data,
            asset,
            lecture,
            start_index + len(items)
        )
        items.extend(subtitle_items)

    return items


def create_video_download_item(download_task, lecture_data, asset, lecture, index):
    """
    Create download item for video asset.
    """
    try:
        streams = asset.get('streams', {})
        sources = streams.get('sources', {})

        if not sources:
            return None

        # Select quality based on user preference
        selected_quality, selected_url = select_video_quality(sources, download_task.video_quality)

        if not selected_url:
            return None

        # Check for encryption
        is_encrypted = streams.get('is_encrypted', False)
        if is_encrypted and not download_task.user.preferences.continue_downloading_encrypted:
            logger.info(f"Skipping encrypted video: {lecture_data.get('title')}")
            return None

        # Generate filename
        filename = generate_video_filename(
            lecture_data,
            selected_quality,
            download_task.user.preferences.seq_zero_left,
            index
        )

        # Create download item
        download_item = DownloadItem.objects.create(
            download_task=download_task,
            lecture=lecture,
            item_type='video',
            filename=filename,
            source_url=selected_url,
            quality=selected_quality,
            format='mp4',
            is_encrypted=is_encrypted,
            file_path=os.path.join(download_task.download_path, filename)
        )

        return download_item

    except Exception as e:
        logger.error(f"Error creating video download item: {e}")
        return None


def create_attachment_download_item(download_task, lecture_data, asset, lecture, index):
    """
    Create download item for attachment asset.
    """
    try:
        download_url = asset.get('download_url') or asset.get('external_url')
        if not download_url:
            return None

        filename = asset.get('filename') or f"{asset.get('title', 'attachment')}_{index}"
        filename = sanitize_filename(filename)

        download_item = DownloadItem.objects.create(
            download_task=download_task,
            lecture=lecture,
            item_type='attachment',
            filename=filename,
            source_url=download_url,
            file_path=os.path.join(download_task.download_path, 'attachments', filename)
        )

        return download_item

    except Exception as e:
        logger.error(f"Error creating attachment download item: {e}")
        return None


def create_subtitle_download_items(download_task, lecture_data, asset, lecture, start_index):
    """
    Create download items for subtitle assets.
    """
    items = []
    captions = asset.get('captions', [])

    for i, caption in enumerate(captions):
        try:
            # Filter by selected subtitle language if specified
            if download_task.selected_subtitle:
                if caption.get('language') != download_task.selected_subtitle:
                    continue

            subtitle_url = caption.get('url')
            if not subtitle_url:
                continue

            language = caption.get('language', 'unknown')
            filename = generate_subtitle_filename(
                lecture_data,
                language,
                download_task.user.preferences.seq_zero_left,
                start_index + i
            )

            download_item = DownloadItem.objects.create(
                download_task=download_task,
                lecture=lecture,
                item_type='subtitle',
                filename=filename,
                source_url=subtitle_url,
                quality=language,
                format='srt',
                file_path=os.path.join(download_task.download_path, 'subtitles', filename)
            )

            items.append(download_item)

        except Exception as e:
            logger.error(f"Error creating subtitle download item: {e}")
            continue

    return items


async def download_single_item(download_engine, item, download_task):
    """
    Download a single item.

    Args:
        download_engine: Download engine instance
        item: Download item to process
        download_task: Parent download task

    Returns:
        True if successful
    """
    try:
        item.status = 'downloading'
        item.started_at = timezone.now()
        item.save()

        # Ensure directory exists
        os.makedirs(os.path.dirname(item.file_path), exist_ok=True)

        # Handle different item types
        if item.item_type == 'subtitle':
            return await download_subtitle_item(item)
        else:
            return await download_file_item(download_engine, item)

    except Exception as e:
        logger.error(f"Error downloading item {item.filename}: {e}")
        item.error_message = str(e)
        item.save()
        return False


async def download_file_item(download_engine, item):
    """
    Download a regular file item.
    """
    try:
        # Create progress callback
        def progress_callback(task):
            item.progress_percentage = task.progress.percentage
            item.download_speed = task.progress.speed
            item.downloaded_size = task.progress.downloaded_size
            item.file_size = task.progress.total_size
            item.save(update_fields=['progress_percentage', 'download_speed', 'downloaded_size', 'file_size'])

        # Start download
        download_task = download_engine.download(
            item.source_url,
            item.file_path,
            progress_callback
        )

        download_task.start()

        # Wait for completion
        while download_task.status.value not in ['completed', 'failed', 'cancelled']:
            await asyncio.sleep(0.5)

        return download_task.status.value == 'completed'

    except Exception as e:
        logger.error(f"Error downloading file item: {e}")
        return False


async def download_subtitle_item(item):
    """
    Download and convert subtitle item.
    """
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(item.source_url) as response:
                if response.status == 200:
                    vtt_content = await response.text()

                    # Convert VTT to SRT
                    srt_content = convert_vtt_to_srt(vtt_content)

                    # Save SRT file
                    with open(item.file_path, 'w', encoding='utf-8') as f:
                        f.write(srt_content)

                    item.file_size = len(srt_content.encode('utf-8'))
                    item.downloaded_size = item.file_size
                    item.progress_percentage = 100.0
                    item.save()

                    return True

        return False

    except Exception as e:
        logger.error(f"Error downloading subtitle: {e}")
        return False


def select_video_quality(sources, preferred_quality):
    """
    Select video quality and URL from available sources.

    Args:
        sources: Available video sources
        preferred_quality: User's preferred quality setting

    Returns:
        Tuple of (selected_quality, download_url)
    """
    available_qualities = []
    quality_urls = {}

    for quality, source_data in sources.items():
        if not source_data.get('is_encrypted', False):
            available_qualities.append(quality)
            quality_urls[quality] = source_data.get('url')

    if not available_qualities:
        return 'NotFound', None

    # Sort qualities numerically
    numeric_qualities = []
    for q in available_qualities:
        try:
            numeric_qualities.append((int(q), q))
        except ValueError:
            pass

    numeric_qualities.sort(reverse=True)

    # Select based on preference
    if preferred_quality == 'Auto' or preferred_quality == 'Highest':
        selected = numeric_qualities[0][1] if numeric_qualities else available_qualities[0]
    elif preferred_quality == 'Lowest':
        selected = numeric_qualities[-1][1] if numeric_qualities else available_qualities[-1]
    else:
        # Try to find exact match
        if preferred_quality in available_qualities:
            selected = preferred_quality
        else:
            # Find closest match
            try:
                target_quality = int(preferred_quality)
                closest = min(numeric_qualities, key=lambda x: abs(x[0] - target_quality))
                selected = closest[1]
            except (ValueError, IndexError):
                selected = numeric_qualities[0][1] if numeric_qualities else available_qualities[0]

    return selected, quality_urls.get(selected)


def generate_video_filename(lecture_data, quality, seq_zero_left, index):
    """
    Generate filename for video file.
    """
    title = lecture_data.get('title', 'Unknown')
    title = sanitize_filename(title)

    if seq_zero_left:
        prefix = f"{index:03d}-"
    else:
        prefix = f"{index}-"

    return f"{prefix}{title}_{quality}p.mp4"


def generate_subtitle_filename(lecture_data, language, seq_zero_left, index):
    """
    Generate filename for subtitle file.
    """
    title = lecture_data.get('title', 'Unknown')
    title = sanitize_filename(title)

    if seq_zero_left:
        prefix = f"{index:03d}-"
    else:
        prefix = f"{index}-"

    return f"{prefix}{title}_{language}.srt"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system storage.
    """
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename[:200]  # Limit length


def convert_vtt_to_srt(vtt_content: str) -> str:
    """
    Convert VTT subtitle content to SRT format.
    """
    try:
        from io import StringIO
        import re

        lines = vtt_content.strip().split('\n')
        srt_lines = []
        subtitle_count = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip WEBVTT header and empty lines
            if line.startswith('WEBVTT') or line == '' or line.startswith('NOTE'):
                i += 1
                continue

            # Check if this is a timestamp line
            if '-->' in line:
                subtitle_count += 1

                # Convert timestamp format
                timestamp_line = re.sub(r'(\d+):(\d+):(\d+)\.(\d+)', r'\1:\2:\3,\4', line)

                srt_lines.append(str(subtitle_count))
                srt_lines.append(timestamp_line)

                # Get subtitle text
                i += 1
                subtitle_text_lines = []
                while i < len(lines) and lines[i].strip() != '' and '-->' not in lines[i]:
                    subtitle_text_lines.append(lines[i].strip())
                    i += 1

                srt_lines.extend(subtitle_text_lines)
                srt_lines.append('')  # Empty line between subtitles
            else:
                i += 1

        return '\n'.join(srt_lines)

    except Exception as e:
        logger.warning(f"VTT to SRT conversion failed: {e}")
        return vtt_content  # Return original if conversion fails


def update_download_history(download_task: DownloadTask) -> None:
    """
    Update download history after completion.
    """
    try:
        history, created = DownloadHistory.objects.get_or_create(
            user=download_task.user,
            course=download_task.course,
            defaults={
                'is_completed': download_task.status == 'completed',
                'completion_date': download_task.completed_at,
                'download_path': download_task.download_path,
                'encrypted_videos_count': download_task.encrypted_items,
                'total_size': download_task.total_size,
                'selected_subtitle': download_task.selected_subtitle,
                'video_quality': download_task.video_quality,
                'download_type': download_task.download_type
            }
        )

        if not created:
            # Update existing history
            history.is_completed = download_task.status == 'completed'
            history.completion_date = download_task.completed_at
            history.download_path = download_task.download_path
            history.total_size = download_task.total_size
            history.save()

    except Exception as e:
        logger.error(f"Error updating download history: {e}")


def send_progress_update(download_id: str, status: str, percentage: float, message: str) -> None:
    """
    Send progress update to WebSocket clients.
    """
    try:
        from apps.core.consumers import send_download_progress_update
        send_download_progress_update(
            download_id=download_id,
            status=status,
            progress=percentage,
            message=message,
            timestamp=timezone.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error sending progress update: {e}")


def send_download_notification(download_task: DownloadTask) -> None:
    """
    Send download completion notification to user.
    """
    try:
        from apps.core.consumers import send_download_notification as send_notification

        if download_task.status == 'completed':
            notification_type = 'download_completed'
            message = f'Course "{download_task.course.title}" downloaded successfully!'
        else:
            notification_type = 'download_failed'
            message = f'Course "{download_task.course.title}" download failed.'

        send_notification(
            user_id=download_task.user.id,
            download_id=str(download_task.id),
            course_title=download_task.course.title,
            notification_type=notification_type,
            message=message
        )

    except Exception as e:
        logger.error(f"Error sending download notification: {e}")


@shared_task
def cleanup_old_downloads():
    """
    Cleanup old completed and failed download tasks.
    """
    try:
        # Remove download tasks older than 30 days
        old_date = timezone.now() - timedelta(days=30)

        old_tasks = DownloadTask.objects.filter(
            status__in=['completed', 'failed', 'cancelled'],
            completed_at__lt=old_date
        )

        count = old_tasks.count()
        old_tasks.delete()

        logger.info(f"Cleaned up {count} old download tasks")

        return f"Cleaned up {count} old download tasks"

    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        raise


@shared_task
def send_download_stats_update():
    """
    Send download statistics update to admin users.
    """
    try:
        from apps.core.consumers import send_global_stats_update

        # Get current download stats
        active_downloads = DownloadTask.objects.filter(
            status__in=['preparing', 'downloading']
        ).count()

        completed_today = DownloadTask.objects.filter(
            completed_at__date=timezone.now().date(),
            status='completed'
        ).count()

        send_global_stats_update(
            active_downloads=active_downloads,
            completed_downloads_today=completed_today
        )

    except Exception as e:
        logger.error(f"Error sending stats update: {e}")


async def fetch_course_content_for_download(download_task):
    """Fetch course content from Udemy API."""
    try:
        user = download_task.user
        course = download_task.course

        if not user.udemy_access_token or not user.is_token_valid:
            raise Exception("Valid Udemy token required")

        udemy_service = UdemyService(user.udemy_access_token, user.udemy_subdomain)

        content_data = await udemy_service.fetch_course_content(course.udemy_id, "all")
        return content_data

    except Exception as e:
        logger.error(f"Failed to fetch course content for {download_task.course.udemy_id}: {e}")
        return None


def prepare_download_items(download_task: DownloadTask, course_data):
    """Prepare list of items to download based on settings."""
    download_items = []
    download_type = download_task.download_type
    skip_subtitles = download_task.user.preferences.skip_subtitles
    selected_subtitle = download_task.selected_subtitle

    # Create download directory
    course_name = Utils.sanitize_filename(download_task.course.title)
    base_download_path = Path(download_task.download_path)
    course_download_path = base_download_path / course_name
    course_download_path.mkdir(parents=True, exist_ok=True)

    # Process course structure
    current_chapter = None
    lecture_sequence = 0

    for item in course_data.get('results', []):
        item_class = item.get('_class', '').lower()

        if item_class == 'chapter':
            current_chapter = item

        elif item_class in ['lecture', 'quiz', 'practice'] and current_chapter:
            lecture_sequence += 1

            # Check range download settings
            if download_task.enable_range_download:
                if lecture_sequence < download_task.download_start:
                    continue
                if download_task.download_end > 0 and lecture_sequence > download_task.download_end:
                    break

            # Create chapter directory
            chapter_name = Utils.sanitize_filename(current_chapter.get('title', f'Chapter {lecture_sequence}'))
            chapter_path = course_download_path / chapter_name
            chapter_path.mkdir(exist_ok=True)

            # Process lecture
            download_items.extend(
                process_lecture_for_download(
                    download_task, item, chapter_path, lecture_sequence,
                    download_type, skip_subtitles, selected_subtitle
                )
            )

    return download_items


def process_lecture_for_download(
    download_task: DownloadTask,
    lecture_data,
    chapter_path: Path,
    sequence: int,
    download_type: int,
    skip_subtitles: bool,
    selected_subtitle: str
):
    """Process a single lecture for download preparation."""
    download_items = []
    lecture_title = lecture_data.get('title', f'Lecture {sequence}')
    asset = lecture_data.get('asset', {})
    supplementary_assets = lecture_data.get('supplementary_assets', [])

    # Determine lecture type and source
    item_class = lecture_data.get('_class', '').lower()
    asset_type = asset.get('asset_type', '').lower()

    # Create lecture item based on type
    if item_class == 'quiz':
        download_items.append(create_url_download_item(
            download_task, lecture_data, chapter_path, sequence, 'quiz'
        ))
    elif item_class == 'practice':
        download_items.append(create_url_download_item(
            download_task, lecture_data, chapter_path, sequence, 'practice'
        ))
    elif asset_type == 'article':
        download_items.append(create_article_download_item(
            download_task, lecture_data, chapter_path, sequence
        ))
    elif asset_type in ['video', 'videomashup']:
        # Only download videos if type allows
        if download_type in [0, 1]:  # Both or Lectures only
            video_item = create_video_download_item(
                download_task, lecture_data, chapter_path, sequence
            )
            if video_item:
                download_items.append(video_item)

        # Download subtitles if enabled
        if not skip_subtitles and selected_subtitle:
            subtitle_item = create_subtitle_download_item(
                download_task, lecture_data, chapter_path, sequence, selected_subtitle
            )
            if subtitle_item:
                download_items.append(subtitle_item)

    elif asset_type in ['file', 'e-book', 'presentation']:
        file_item = create_file_download_item(
            download_task, lecture_data, chapter_path, sequence
        )
        if file_item:
            download_items.append(file_item)

    # Process attachments if enabled
    if download_type in [0, 2] and supplementary_assets:  # Both or Attachments only
        for idx, attachment in enumerate(supplementary_assets):
            attachment_item = create_attachment_download_item(
                download_task, attachment, chapter_path, sequence, idx + 1
            )
            if attachment_item:
                download_items.append(attachment_item)

    return download_items


def create_video_download_item(
    download_task: DownloadTask,
    lecture_data,
    chapter_path: Path,
    sequence: int
):
    """Create download item for video content."""
    try:
        asset = lecture_data.get('asset', {})
        streams = asset.get('streams', {})

        if not streams or streams.get('isEncrypted', False):
            # Handle encrypted content
            if not download_task.user.preferences.continue_downloading_encrypted:
                return None

        # Determine quality and source URL
        quality = download_task.video_quality
        sources = streams.get('sources', {})

        if not sources:
            return None

        # Select best quality source
        if quality == 'Auto' or quality == 'Highest':
            source_quality = streams.get('maxQuality', 'auto')
        elif quality == 'Lowest':
            source_quality = streams.get('minQuality', 'auto')
        else:
            # Try to find exact quality or closest
            if quality in sources:
                source_quality = quality
            else:
                # Find closest quality
                closest = Utils.get_closest_value(sources, int(quality) if Utils.is_number(quality) else 720)
                source_quality = closest['key']

        if source_quality not in sources:
            source_quality = 'auto'

        source_info = sources.get(source_quality, {})
        source_url = source_info.get('url', '')
        source_type = source_info.get('type', '')

        if not source_url:
            return None

        # Create filename
        lecture_title = Utils.sanitize_filename(lecture_data.get('title', f'Lecture {sequence}'))
        filename = Utils.get_sequence_name(
            sequence,
            download_task.total_items,
            f"{lecture_title}.mp4",
            ". ",
            str(chapter_path),
            download_task.user.preferences.seq_zero_left
        )['fullPath']

        # Create download item
        return DownloadItem.objects.create(
            download_task=download_task,
            item_type='video',
            filename=os.path.basename(filename),
            source_url=source_url,
            file_path=filename,
            quality=source_quality,
            format=source_type,
            is_encrypted=streams.get('isEncrypted', False)
        )

    except Exception as e:
        logger.error(f"Failed to create video download item: {e}")
        return None


def create_article_download_item(
    download_task: DownloadTask,
    lecture_data,
    chapter_path: Path,
    sequence: int
) -> DownloadItem:
    """Create download item for article content."""
    asset = lecture_data.get('asset', {})
    content = asset.get('body', '') or asset.get('data', {}).get('body', '')

    lecture_title = Utils.sanitize_filename(lecture_data.get('title', f'Article {sequence}'))
    filename = Utils.get_sequence_name(
        sequence,
        download_task.total_items,
        f"{lecture_title}.html",
        ". ",
        str(chapter_path),
        download_task.user.preferences.seq_zero_left
    )['fullPath']

    return DownloadItem.objects.create(
        download_task=download_task,
        item_type='article',
        filename=os.path.basename(filename),
        source_url=content,  # Store content in source_url for articles
        file_path=filename,
        quality='Article',
        format='html'
    )


def create_file_download_item(
    download_task: DownloadTask,
    lecture_data,
    chapter_path: Path,
    sequence: int
):
    """Create download item for file content."""
    try:
        asset = lecture_data.get('asset', {})
        asset_type = asset.get('asset_type', '').lower()

        # Get download URL
        if asset_type in ['file', 'e-book']:
            download_urls = asset.get('download_urls', {})
            file_url = download_urls.get(asset_type, [{}])[0].get('file', '')
            extension = '.pdf'  # Default for files
        elif asset_type == 'presentation':
            url_set = asset.get('url_set', {})
            file_url = url_set.get(asset_type, [{}])[0].get('file', '')
            extension = '.pdf'  # Default for presentations
        else:
            return None

        if not file_url:
            return None

        # Create filename
        lecture_title = Utils.sanitize_filename(lecture_data.get('title', f'File {sequence}'))
        filename = Utils.get_sequence_name(
            sequence,
            download_task.total_items,
            f"{lecture_title}{extension}",
            ". ",
            str(chapter_path),
            download_task.user.preferences.seq_zero_left
        )['fullPath']

        return DownloadItem.objects.create(
            download_task=download_task,
            item_type='attachment',
            filename=os.path.basename(filename),
            source_url=file_url,
            file_path=filename,
            quality=asset_type.title(),
            format=extension.lstrip('.')
        )

    except Exception as e:
        logger.error(f"Failed to create file download item: {e}")
        return None


def create_subtitle_download_item(
    download_task: DownloadTask,
    lecture_data,
    chapter_path: Path,
    sequence: int,
    selected_subtitle: str
):
    """Create download item for subtitle content."""
    try:
        asset = lecture_data.get('asset', {})
        captions = asset.get('captions', [])

        if not captions or not selected_subtitle:
            return None

        # Find matching subtitle
        selected_languages = selected_subtitle.split('|')
        subtitle_url = None

        for caption in captions:
            caption_language = caption.get('video_label', '')
            if caption_language in selected_languages:
                subtitle_url = caption.get('url', '')
                break

        if not subtitle_url:
            # Try first available subtitle as fallback
            if captions:
                subtitle_url = captions[0].get('url', '')

        if not subtitle_url:
            return None

        # Create filename
        lecture_title = Utils.sanitize_filename(lecture_data.get('title', f'Subtitle {sequence}'))
        filename = Utils.get_sequence_name(
            sequence,
            download_task.total_items,
            f"{lecture_title}.srt",
            ". ",
            str(chapter_path),
            download_task.user.preferences.seq_zero_left
        )['fullPath']

        return DownloadItem.objects.create(
            download_task=download_task,
            item_type='subtitle',
            filename=os.path.basename(filename),
            source_url=subtitle_url,
            file_path=filename,
            quality='Subtitle',
            format='srt'
        )

    except Exception as e:
        logger.error(f"Failed to create subtitle download item: {e}")
        return None


def create_attachment_download_item(
    download_task: DownloadTask,
    attachment_data,
    chapter_path: Path,
    sequence: int,
    attachment_index: int
):
    """Create download item for attachment content."""
    try:
        attachment_title = attachment_data.get('title', f'Attachment {attachment_index}')
        download_urls = attachment_data.get('download_urls')
        external_url = attachment_data.get('external_url')

        if download_urls:
            # File attachment
            asset_type = attachment_data.get('asset_type', 'file')
            file_url = download_urls.get(asset_type, [{}])[0].get('file', '')

            if not file_url:
                return None

            # Determine file extension
            file_extension = Utils.get_file_extension(file_url)
            if not file_extension and attachment_data.get('filename'):
                file_extension = Utils.get_file_extension(attachment_data['filename'])

            filename = Utils.get_sequence_name(
                sequence,
                download_task.total_items,
                f"{Utils.sanitize_filename(attachment_title)}.{file_extension}",
                f".{attachment_index} ",
                str(chapter_path),
                download_task.user.preferences.seq_zero_left
            )['fullPath']

            return DownloadItem.objects.create(
                download_task=download_task,
                item_type='attachment',
                filename=os.path.basename(filename),
                source_url=file_url,
                file_path=filename,
                quality='Attachment',
                format=file_extension
            )

        elif external_url:
            # External URL - create HTML redirect
            filename = Utils.get_sequence_name(
                sequence,
                download_task.total_items,
                f"{Utils.sanitize_filename(attachment_title)}.html",
                f".{attachment_index} ",
                str(chapter_path),
                download_task.user.preferences.seq_zero_left
            )['fullPath']

            html_content = f'<script type="text/javascript">window.location = "{external_url}";</script>'

            return DownloadItem.objects.create(
                download_task=download_task,
                item_type='attachment',
                filename=os.path.basename(filename),
                source_url=html_content,  # Store HTML content in source_url
                file_path=filename,
                quality='Attachment',
                format='html'
            )

        return None

    except Exception as e:
        logger.error(f"Failed to create attachment download item: {e}")
        return None


def create_url_download_item(
    download_task: DownloadTask,
    lecture_data,
    chapter_path: Path,
    sequence: int,
    item_type: str
) -> DownloadItem:
    """Create download item for URL content (quiz, practice)."""
    course_url = f"https://{download_task.user.udemy_subdomain}.udemy.com{download_task.course.url}"
    redirect_url = f"{course_url}/{lecture_data.get('_class', 'lecture')}/{lecture_data.get('id', '')}"

    lecture_title = Utils.sanitize_filename(lecture_data.get('title', f'{item_type.title()} {sequence}'))
    filename = Utils.get_sequence_name(
        sequence,
        download_task.total_items,
        f"{lecture_title}.html",
        ". ",
        str(chapter_path),
        download_task.user.preferences.seq_zero_left
    )['fullPath']

    html_content = f'<script type="text/javascript">window.location = "{redirect_url}";</script>'

    return DownloadItem.objects.create(
        download_task=download_task,
        item_type='url',
        filename=os.path.basename(filename),
        source_url=html_content,
        file_path=filename,
        quality='Attachment',
        format='html'
    )


async def download_single_item(
    download_engine: DownloadEngine,
    download_item: DownloadItem,
    download_task) -> bool:
    """Download a single item."""
    try:
        download_item.status = 'downloading'
        download_item.started_at = timezone.now()
        download_item.save()

        # Handle different item types
        if download_item.item_type == 'video':
            return await download_video_item(download_engine, download_item)
        elif download_item.item_type == 'article':
            return await download_article_item(download_item)
        elif download_item.item_type == 'attachment':
            if download_item.format == 'html':
                return await download_html_item(download_item)
            else:
                return await download_file_item(download_engine, download_item)
        elif download_item.item_type == 'subtitle':
            return await download_subtitle_item(download_item)
        elif download_item.item_type == 'url':
            return await download_html_item(download_item)

        return False

    except Exception as e:
        logger.error(f"Failed to download item {download_item.filename}: {e}")
        download_item.error_message = str(e)
        download_item.save()
        return False


async def download_video_item(download_engine: DownloadEngine, download_item: DownloadItem) -> bool:
    """Download video content."""
    try:
        # Check if file already exists
        if os.path.exists(download_item.file_path):
            return True

        # Check for M3U8 streams
        if 'application/x-mpegurl' in download_item.source_url or download_item.source_url.endswith('.m3u8'):
            # Use M3U8 downloader
            m3u8_downloader = M3U8Downloader()
            return await m3u8_downloader.download_m3u8_stream(
                download_item.source_url,
                download_item.file_path
            )
        else:
            # Regular file download
            task = download_engine.download(download_item.source_url, download_item.file_path)
            return await task.start()

    except Exception as e:
        logger.error(f"Failed to download video {download_item.filename}: {e}")
        return False


async def download_file_item(download_engine: DownloadEngine, download_item: DownloadItem) -> bool:
    """Download file content."""
    try:
        # Check if file already exists
        if os.path.exists(download_item.file_path):
            return True

        task = download_engine.download(download_item.source_url, download_item.file_path)
        return await task.start()

    except Exception as e:
        logger.error(f"Failed to download file {download_item.filename}: {e}")
        return False


async def download_article_item(download_item: DownloadItem) -> bool:
    """Download article content."""
    try:
        # Article content is stored in source_url
        content = download_item.source_url

        # Ensure directory exists
        os.makedirs(os.path.dirname(download_item.file_path), exist_ok=True)

        # Write HTML content
        with open(download_item.file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        logger.error(f"Failed to download article {download_item.filename}: {e}")
        return False


async def download_html_item(download_item: DownloadItem) -> bool:
    """Download HTML content (redirects, etc.)."""
    try:
        # HTML content is stored in source_url
        content = download_item.source_url

        # Ensure directory exists
        os.makedirs(os.path.dirname(download_item.file_path), exist_ok=True)

        # Write HTML content
        with open(download_item.file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        logger.error(f"Failed to download HTML {download_item.filename}: {e}")
        return False


async def download_subtitle_item(download_item: DownloadItem) -> bool:
    """Download and convert subtitle content."""
    try:
        import aiohttp
        import aiofiles

        # Check if file already exists
        if os.path.exists(download_item.file_path):
            return True

        # Download VTT subtitle
        vtt_path = download_item.file_path.replace('.srt', '.vtt')

        async with aiohttp.ClientSession() as session:
            async with session.get(download_item.source_url) as response:
                if response.status == 200:
                    # Write VTT file
                    async with aiofiles.open(vtt_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)

        # Convert VTT to SRT
        try:
            import webvtt
            vtt = webvtt.read(vtt_path)
            srt_content = ""

            for i, caption in enumerate(vtt, 1):
                start = caption.start.replace('.', ',')
                end = caption.end.replace('.', ',')
                text = caption.text.replace('\n', '\n')

                srt_content += f"{i}\n{start} --> {end}\n{text}\n\n"

            # Write SRT file
            with open(download_item.file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            # Remove temporary VTT file
            os.remove(vtt_path)

            return True

        except ImportError:
            # webvtt not available, keep as VTT
            os.rename(vtt_path, download_item.file_path)
            return True

    except Exception as e:
        logger.error(f"Failed to download subtitle {download_item.filename}: {e}")
        return False


def update_download_history(download_task: DownloadTask):
    """Update download history for completed task."""
    try:
        history, created = DownloadHistory.objects.update_or_create(
            user=download_task.user,
            course=download_task.course,
            defaults={
                'is_completed': download_task.status == 'completed',
                'completion_date': download_task.completed_at,
                'download_path': download_task.download_path,
                'encrypted_videos_count': download_task.encrypted_items,
                'total_size': download_task.total_size,
                'selected_subtitle': download_task.selected_subtitle,
                'video_quality': download_task.video_quality,
                'download_type': download_task.download_type,
            }
        )

        # Update user course status
        user_course, created = UserCourse.objects.get_or_create(
            user=download_task.user,
            course=download_task.course
        )

        user_course.is_downloaded = download_task.status == 'completed'
        user_course.download_path = download_task.download_path
        user_course.save()

    except Exception as e:
        logger.error(f"Failed to update download history: {e}")


def send_progress_update(download_task_id: str, status: str, percentage: float, message: str):
    """Send progress update via WebSocket."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        group_name = f"download_progress_{download_task_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'download_progress',
                'download_id': download_task_id,
                'status': status,
                'percentage': percentage,
                'message': message,
                'timestamp': timezone.now().isoformat()
            }
        )

    except Exception as e:
        logger.warning(f"Failed to send progress update: {e}")


def send_download_notification(download_task: DownloadTask):
    """Send download completion notification."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        group_name = f"user_notifications_{download_task.user.id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'download_notification',
                'title': download_task.course.title,
                'message': 'Download completed successfully!',
                'download_path': download_task.download_path,
                'course_image': download_task.course.image_url,
                'timestamp': timezone.now().isoformat()
            }
        )

    except Exception as e:
        logger.warning(f"Failed to send download notification: {e}")


@shared_task
def cleanup_old_downloads():
    """Clean up old download tasks and files."""
    try:
        # Clean up completed tasks older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        old_tasks = DownloadTask.objects.filter(
            status__in=['completed', 'failed', 'cancelled'],
            updated_at__lt=cutoff_date
        )

        deleted_count = 0
        for task in old_tasks:
            try:
                # Remove associated download items
                task.download_items.all().delete()
                task.delete()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete task {task.id}: {e}")

        logger.info(f"Cleaned up {deleted_count} old download tasks")

    except Exception as e:
        logger.error(f"Download cleanup task failed: {e}")


@shared_task
def retry_failed_downloads():
    """Retry failed downloads that can be retried."""
    try:
        failed_tasks = DownloadTask.objects.filter(
            status='failed',
            retry_count__lt=3,
            updated_at__gt=timezone.now() - timedelta(hours=24)
        )

        for task in failed_tasks:
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = 'pending'
                task.error_message = ''
                task.save()

                # Restart the download
                download_course_task.delay(str(task.id), task.user.id)

                logger.info(f"Retrying download task {task.id} (attempt {task.retry_count})")

    except Exception as e:
        logger.error(f"Retry failed downloads task failed: {e}")
