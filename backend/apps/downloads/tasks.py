"""
Celery tasks for Downloads app
"""
from celery import shared_task, current_task
from django.utils import timezone
from django.conf import settings
import os
import subprocess
import logging
import json
import time
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_download_job(self, download_job_id):
    """
    Process a download job - main download task
    """
    from .models import DownloadJob, DownloadItem, DownloadHistory
    from apps.courses.models import Curriculum
    from apps.analytics.models import DownloadAnalytics

    try:
        # Get download job
        download_job = DownloadJob.objects.get(id=download_job_id)
        download_job.status = 'downloading'
        download_job.started_at = timezone.now()
        download_job.celery_task_id = self.request.id
        download_job.save()

        logger.info(f"Starting download job {download_job_id}")

        # Get course curriculum
        course = download_job.course
        curriculum_items = course.curriculum_items.filter(
            item_type='lecture',
            is_downloadable=True
        ).order_by('section_index', 'order_index')

        # Filter selected lectures if specified
        if download_job.selected_lectures:
            curriculum_items = curriculum_items.filter(
                id__in=download_job.selected_lectures
            )

        total_items = curriculum_items.count()
        download_job.total_items = total_items
        download_job.save()

        if total_items == 0:
            download_job.status = 'failed'
            download_job.error_message = 'No downloadable items found'
            download_job.save()
            return

        # Create storage directory
        storage_path = _create_storage_directory(download_job)
        download_job.storage_path = storage_path
        download_job.save()

        # Create analytics record
        analytics = DownloadAnalytics.objects.create(
            user=download_job.user,
            course=course,
            download_job=download_job,
            status='started',
            quality_requested=download_job.quality,
            total_files=total_items,
            started_at=timezone.now()
        )

        completed_items = 0
        failed_items = 0
        total_size = 0

        # Process each curriculum item
        for item in curriculum_items:
            try:
                # Check if task was revoked
                if self.request.called_directly is False:
                    current_task.update_state(
                        state='PROGRESS',
                        meta={
                            'current': completed_items,
                            'total': total_items,
                            'status': f'Downloading {item.title}'
                        }
                    )

                # Create download item
                download_item = DownloadItem.objects.create(
                    download_job=download_job,
                    curriculum_item=item,
                    item_type='video',
                    title=item.title,
                    filename=_sanitize_filename(item.title),
                    source_url=item.video_url,
                    quality=download_job.quality,
                    status='pending'
                )

                # Download the video
                success, file_size = _download_video(download_item, storage_path)

                if success:
                    download_item.status = 'completed'
                    download_item.file_size_bytes = file_size
                    download_item.completed_at = timezone.now()
                    completed_items += 1
                    total_size += file_size

                    # Download subtitles if requested
                    if download_job.include_subtitles:
                        _download_subtitles(download_item, storage_path)

                    # Increment curriculum download count
                    item.download_count += 1
                    item.save()

                else:
                    download_item.status = 'failed'
                    failed_items += 1

                download_item.save()

                # Update job progress
                progress = (completed_items / total_items) * 100
                download_job.completed_items = completed_items
                download_job.failed_items = failed_items
                download_job.progress_percentage = progress
                download_job.total_size_bytes = total_size
                download_job.save()

                # Small delay to prevent overwhelming the server
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error downloading item {item.id}: {e}")
                failed_items += 1
                download_job.failed_items = failed_items
                download_job.save()

        # Complete the download job
        download_job.status = 'completed' if failed_items == 0 else 'failed'
        download_job.completed_at = timezone.now()
        download_job.save()

        # Update analytics
        analytics.status = 'completed' if failed_items == 0 else 'failed'
        analytics.completed_files = completed_items
        analytics.total_size_mb = total_size / (1024 * 1024)
        analytics.completed_at = timezone.now()

        if analytics.started_at:
            duration = (analytics.completed_at - analytics.started_at).total_seconds()
            analytics.total_duration_seconds = int(duration)
            if duration > 0:
                analytics.download_speed_mbps = (total_size / (1024 * 1024)) / duration * 8

        analytics.save()

        # Create download history
        DownloadHistory.objects.create(
            user=download_job.user,
            course=course,
            download_job=download_job,
            total_files=total_items,
            successful_files=completed_items,
            failed_files=failed_items,
            total_size_mb=total_size / (1024 * 1024),
            total_duration_seconds=analytics.total_duration_seconds,
            average_speed_mbps=analytics.download_speed_mbps,
            ip_address=download_job.user.last_login_ip or '0.0.0.0',
            user_agent=''
        )

        # Update user subscription usage
        subscription = getattr(download_job.user, 'subscription', None)
        if subscription:
            subscription.increment_downloads()

        # Update storage quota
        storage_quota = getattr(download_job.user, 'storage_quota', None)
        if storage_quota:
            storage_quota.add_usage(total_size, completed_items)

        # Send completion notification
        send_download_completion_notification.delay(download_job_id)

        logger.info(f"Download job {download_job_id} completed successfully")
        return f"Downloaded {completed_items}/{total_items} items"

    except Exception as e:
        logger.error(f"Error processing download job {download_job_id}: {e}")

        try:
            download_job = DownloadJob.objects.get(id=download_job_id)
            download_job.status = 'failed'
            download_job.error_message = str(e)
            download_job.retry_count += 1
            download_job.save()

            # Retry if possible
            if download_job.can_retry():
                logger.info(f"Retrying download job {download_job_id} (attempt {download_job.retry_count})")
                raise self.retry(countdown=60 * download_job.retry_count)

        except Exception as retry_error:
            logger.error(f"Error handling retry for download job {download_job_id}: {retry_error}")

        raise e


def _create_storage_directory(download_job):
    """Create storage directory for download job"""
    base_path = settings.FREE2FETCH_SETTINGS.get('STORAGE_ROOT', '/tmp/storage')
    user_path = os.path.join(base_path, f"user_{download_job.user.id}")
    course_path = os.path.join(user_path, f"course_{download_job.course.id}")

    os.makedirs(course_path, exist_ok=True)
    return course_path


def _sanitize_filename(filename):
    """Sanitize filename for filesystem"""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def _download_video(download_item, storage_path):
    """Download video using yt-dlp or similar tool"""
    try:
        download_item.status = 'downloading'
        download_item.started_at = timezone.now()
        download_item.save()

        # For demonstration - in reality this would use Udemy API or yt-dlp
        # Here we simulate the download process
        import random
        time.sleep(random.uniform(2, 5))  # Simulate download time

        # Simulate file creation
        filename = f"{download_item.filename}.mp4"
        file_path = os.path.join(storage_path, filename)

        # Create a dummy file for demonstration
        with open(file_path, 'w') as f:
            f.write(f"Video content for {download_item.title}")

        file_size = os.path.getsize(file_path)
        download_item.local_path = file_path
        download_item.file_size_bytes = file_size

        return True, file_size

    except Exception as e:
        download_item.error_message = str(e)
        download_item.status = 'failed'
        download_item.save()
        logger.error(f"Error downloading video {download_item.id}: {e}")
        return False, 0


def _download_subtitles(download_item, storage_path):
    """Download subtitles for video"""
    try:
        # Create subtitle file
        subtitle_filename = f"{download_item.filename}.srt"
        subtitle_path = os.path.join(storage_path, subtitle_filename)

        # Create dummy subtitle file
        with open(subtitle_path, 'w') as f:
            f.write(f"Subtitles for {download_item.title}")

        # Create subtitle download item
        from .models import DownloadItem
        DownloadItem.objects.create(
            download_job=download_item.download_job,
            curriculum_item=download_item.curriculum_item,
            item_type='subtitle',
            title=f"{download_item.title} - Subtitles",
            filename=subtitle_filename,
            source_url='',
            local_path=subtitle_path,
            file_size_bytes=os.path.getsize(subtitle_path),
            status='completed',
            quality='',
            started_at=timezone.now(),
            completed_at=timezone.now()
        )

    except Exception as e:
        logger.error(f"Error downloading subtitles for {download_item.id}: {e}")


@shared_task
def send_download_completion_notification(download_job_id):
    """Send notification when download is completed"""
    from .models import DownloadJob
    from apps.notifications.models import Notification, NotificationTemplate

    try:
        download_job = DownloadJob.objects.get(id=download_job_id)

        # Get notification template
        template_name = 'download_complete' if download_job.status == 'completed' else 'download_failed'

        try:
            template = NotificationTemplate.objects.get(name=template_name, is_active=True)
        except NotificationTemplate.DoesNotExist:
            logger.warning(f"Notification template {template_name} not found")
            return

        # Create notification
        subject = f"Download {'Completed' if download_job.status == 'completed' else 'Failed'}: {download_job.course.title}"

        content = f"""
        Your download of "{download_job.course.title}" has {'completed successfully' if download_job.status == 'completed' else 'failed'}.

        Downloaded: {download_job.completed_items}/{download_job.total_items} items
        Size: {download_job.size_display}
        Quality: {download_job.quality}

        {'You can now access your downloaded content in your library.' if download_job.status == 'completed' else 'Please try downloading again or contact support.'}
        """

        Notification.objects.create(
            user=download_job.user,
            template=template,
            subject=subject,
            content=content,
            recipient_email=download_job.user.email,
            priority='normal',
            context_data={
                'download_job_id': str(download_job.id),
                'course_title': download_job.course.title,
                'status': download_job.status,
                'completed_items': download_job.completed_items,
                'total_items': download_job.total_items
            }
        )

        logger.info(f"Download completion notification sent for job {download_job_id}")

    except Exception as e:
        logger.error(f"Error sending download completion notification: {e}")


@shared_task
def cleanup_old_downloads():
    """Clean up old download files and records"""
    from .models import DownloadJob, DownloadHistory
    from django.conf import settings

    try:
        # Get expiry days from settings
        expiry_days = settings.FREE2FETCH_SETTINGS.get('DOWNLOAD_EXPIRY_DAYS', 30)
        cutoff_date = timezone.now() - timedelta(days=expiry_days)

        # Find old completed downloads
        old_jobs = DownloadJob.objects.filter(
            status='completed',
            completed_at__lt=cutoff_date
        )

        deleted_files = 0
        freed_space = 0

        for job in old_jobs:
            # Delete physical files
            if job.storage_path and os.path.exists(job.storage_path):
                try:
                    import shutil
                    size = _get_directory_size(job.storage_path)
                    shutil.rmtree(job.storage_path)
                    freed_space += size
                    deleted_files += 1
                    logger.info(f"Deleted old download files for job {job.id}")
                except Exception as e:
                    logger.error(f"Error deleting files for job {job.id}: {e}")

            # Update storage quota
            storage_quota = getattr(job.user, 'storage_quota', None)
            if storage_quota:
                storage_quota.remove_usage(job.total_size_bytes, job.completed_items)

        # Delete old job records but keep history
        old_jobs.delete()

        logger.info(f"Cleanup completed: {deleted_files} jobs cleaned, {freed_space / (1024*1024):.2f} MB freed")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def _get_directory_size(directory):
    """Get total size of directory"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError):
                pass
    return total_size


@shared_task
def update_download_progress(download_job_id, progress_data):
    """Update download progress in real-time"""
    from .models import DownloadJob

    try:
        download_job = DownloadJob.objects.get(id=download_job_id)

        download_job.progress_percentage = progress_data.get('progress', 0)
        download_job.download_speed_mbps = progress_data.get('speed', 0)
        download_job.estimated_time_remaining = progress_data.get('eta', 0)
        download_job.downloaded_size_bytes = progress_data.get('downloaded', 0)

        download_job.save(update_fields=[
            'progress_percentage', 'download_speed_mbps',
            'estimated_time_remaining', 'downloaded_size_bytes'
        ])

        # Send WebSocket update to user
        send_download_progress_update.delay(download_job_id, progress_data)

    except Exception as e:
        logger.error(f"Error updating download progress: {e}")


@shared_task
def send_download_progress_update(download_job_id, progress_data):
    """Send WebSocket update for download progress"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    try:
        channel_layer = get_channel_layer()
        download_job = DownloadJob.objects.get(id=download_job_id)

        # Send to user's personal channel
        group_name = f"user_{download_job.user.id}_downloads"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'download_progress',
                'message': {
                    'download_job_id': str(download_job_id),
                    'progress': progress_data.get('progress', 0),
                    'speed': progress_data.get('speed', 0),
                    'eta': progress_data.get('eta', 0),
                    'status': download_job.status
                }
            }
        )

    except Exception as e:
        logger.error(f"Error sending WebSocket update: {e}")


@shared_task
def retry_failed_downloads():
    """Retry failed downloads that can be retried"""
    from .models import DownloadJob

    try:
        failed_jobs = DownloadJob.objects.filter(
            status='failed',
            retry_count__lt=models.F('max_retries')
        )

        retried_count = 0
        for job in failed_jobs:
            if job.can_retry():
                # Queue for retry
                process_download_job.delay(str(job.id))
                retried_count += 1

        logger.info(f"Queued {retried_count} failed downloads for retry")

    except Exception as e:
        logger.error(f"Error retrying failed downloads: {e}")


@shared_task
def generate_download_reports():
    """Generate daily download reports for analytics"""
    from .models import DownloadJob, DownloadHistory
    from apps.analytics.models import UsageStatistics
    from datetime import date

    try:
        today = date.today()

        # Calculate daily stats
        daily_downloads = DownloadJob.objects.filter(
            created_at__date=today
        ).count()

        completed_downloads = DownloadJob.objects.filter(
            created_at__date=today,
            status='completed'
        ).count()

        failed_downloads = DownloadJob.objects.filter(
            created_at__date=today,
            status='failed'
        ).count()

        total_size = DownloadHistory.objects.filter(
            created_at__date=today
        ).aggregate(
            total=models.Sum('total_size_mb')
        )['total'] or 0

        # Update or create usage statistics
        stats, created = UsageStatistics.objects.get_or_create(
            date=today,
            defaults={
                'total_downloads': daily_downloads,
                'completed_downloads': completed_downloads,
                'failed_downloads': failed_downloads,
                'total_download_size_gb': total_size / 1024
            }
        )

        if not created:
            stats.total_downloads = daily_downloads
            stats.completed_downloads = completed_downloads
            stats.failed_downloads = failed_downloads
            stats.total_download_size_gb = total_size / 1024
            stats.save()

        logger.info(f"Generated download report for {today}")

    except Exception as e:
        logger.error(f"Error generating download reports: {e}")