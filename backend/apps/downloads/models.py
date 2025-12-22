"""
Download Models for Free2Fetch
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid
import os

User = get_user_model()


class DownloadJob(models.Model):
    """
    Download job model to track course downloads
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('queued', _('Queued')),
        ('downloading', _('Downloading')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
        ('paused', _('Paused')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]

    QUALITY_CHOICES = [
        ('360p', _('360p')),
        ('480p', _('480p')),
        ('720p', _('720p')),
        ('1080p', _('1080p')),
        ('auto', _('Auto (Best Available)')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_jobs'
    )

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='download_jobs'
    )

    # Download configuration
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Current download status')
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text=_('Download priority')
    )

    quality = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default='720p',
        help_text=_('Video quality preference')
    )

    # Download options
    include_subtitles = models.BooleanField(
        default=True,
        help_text=_('Download subtitles/captions')
    )

    include_attachments = models.BooleanField(
        default=True,
        help_text=_('Download course attachments')
    )

    selected_lectures = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of specific lecture IDs to download (empty = all)')
    )

    # Progress tracking
    total_items = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of items to download')
    )

    completed_items = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of completed items')
    )

    failed_items = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of failed items')
    )

    progress_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=_('Download progress percentage')
    )

    # File information
    total_size_bytes = models.BigIntegerField(
        default=0,
        help_text=_('Total download size in bytes')
    )

    downloaded_size_bytes = models.BigIntegerField(
        default=0,
        help_text=_('Downloaded size in bytes')
    )

    storage_path = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Local storage path')
    )

    # Speed and ETA
    download_speed_mbps = models.FloatField(
        default=0.0,
        help_text=_('Current download speed in Mbps')
    )

    estimated_time_remaining = models.PositiveIntegerField(
        default=0,
        help_text=_('Estimated time remaining in seconds')
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        help_text=_('Error message if download failed')
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of retry attempts')
    )

    max_retries = models.PositiveIntegerField(
        default=3,
        help_text=_('Maximum retry attempts')
    )

    # Celery task information
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Celery task ID for tracking')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'downloads_download_job'
        verbose_name = _('Download Job')
        verbose_name_plural = _('Download Jobs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['celery_task_id']),
        ]

    def __str__(self):
        return f"Download: {self.course.title} by {self.user.email}"

    @property
    def progress_display(self):
        """Get formatted progress display"""
        return f"{self.completed_items}/{self.total_items} ({self.progress_percentage:.1f}%)"

    @property
    def size_display(self):
        """Get formatted size display"""
        def format_bytes(bytes_size):
            if bytes_size == 0:
                return "0 B"
            sizes = ['B', 'KB', 'MB', 'GB', 'TB']
            i = 0
            while bytes_size >= 1024 and i < len(sizes) - 1:
                bytes_size /= 1024
                i += 1
            return f"{bytes_size:.2f} {sizes[i]}"

        return f"{format_bytes(self.downloaded_size_bytes)} / {format_bytes(self.total_size_bytes)}"

    def update_progress(self, completed_items=None, downloaded_bytes=None):
        """Update download progress"""
        if completed_items is not None:
            self.completed_items = completed_items

        if downloaded_bytes is not None:
            self.downloaded_size_bytes = downloaded_bytes

        # Calculate percentage
        if self.total_items > 0:
            self.progress_percentage = (self.completed_items / self.total_items) * 100

        self.save(update_fields=['completed_items', 'downloaded_size_bytes', 'progress_percentage', 'updated_at'])

    def can_retry(self):
        """Check if download can be retried"""
        return self.retry_count < self.max_retries and self.status == 'failed'


class DownloadItem(models.Model):
    """
    Individual download item (lecture, attachment, etc.)
    """
    ITEM_TYPE_CHOICES = [
        ('video', _('Video')),
        ('subtitle', _('Subtitle')),
        ('attachment', _('Attachment')),
        ('thumbnail', _('Thumbnail')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('downloading', _('Downloading')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('skipped', _('Skipped')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    download_job = models.ForeignKey(
        DownloadJob,
        on_delete=models.CASCADE,
        related_name='items'
    )

    curriculum_item = models.ForeignKey(
        'courses.Curriculum',
        on_delete=models.CASCADE,
        related_name='download_items',
        null=True,
        blank=True
    )

    # Item details
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        help_text=_('Type of download item')
    )

    title = models.CharField(
        max_length=500,
        help_text=_('Item title')
    )

    filename = models.CharField(
        max_length=255,
        help_text=_('Local filename')
    )

    # URLs and paths
    source_url = models.URLField(
        help_text=_('Source URL for download')
    )

    local_path = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Local file path')
    )

    # File information
    file_size_bytes = models.BigIntegerField(
        default=0,
        help_text=_('File size in bytes')
    )

    downloaded_bytes = models.BigIntegerField(
        default=0,
        help_text=_('Downloaded bytes')
    )

    file_format = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('File format/extension')
    )

    quality = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Video quality if applicable')
    )

    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Download status')
    )

    progress_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=_('Download progress percentage')
    )

    download_speed_kbps = models.FloatField(
        default=0.0,
        help_text=_('Download speed in KB/s')
    )

    # Error information
    error_message = models.TextField(
        blank=True,
        help_text=_('Error message if download failed')
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of retry attempts')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'downloads_download_item'
        verbose_name = _('Download Item')
        verbose_name_plural = _('Download Items')
        ordering = ['download_job', 'created_at']

    def __str__(self):
        return f"{self.title} ({self.item_type})"

    @property
    def size_display(self):
        """Get formatted file size"""
        if self.file_size_bytes == 0:
            return "Unknown"

        sizes = ['B', 'KB', 'MB', 'GB']
        i = 0
        size = self.file_size_bytes
        while size >= 1024 and i < len(sizes) - 1:
            size /= 1024
            i += 1
        return f"{size:.2f} {sizes[i]}"

    def get_file_path(self):
        """Get full file path"""
        if self.local_path:
            return os.path.join(self.download_job.storage_path, self.local_path)
        return None


class DownloadHistory(models.Model):
    """
    Download history for analytics and user tracking
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_history'
    )

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        related_name='download_history'
    )

    download_job = models.OneToOneField(
        DownloadJob,
        on_delete=models.CASCADE,
        related_name='history'
    )

    # Download summary
    total_files = models.PositiveIntegerField(
        default=0,
        help_text=_('Total files downloaded')
    )

    successful_files = models.PositiveIntegerField(
        default=0,
        help_text=_('Successfully downloaded files')
    )

    failed_files = models.PositiveIntegerField(
        default=0,
        help_text=_('Failed file downloads')
    )

    total_size_mb = models.FloatField(
        default=0.0,
        help_text=_('Total download size in MB')
    )

    # Time tracking
    total_duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text=_('Total download time in seconds')
    )

    average_speed_mbps = models.FloatField(
        default=0.0,
        help_text=_('Average download speed in Mbps')
    )

    # User experience
    user_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('User rating for download experience')
    )

    user_feedback = models.TextField(
        blank=True,
        help_text=_('User feedback about download')
    )

    # System information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('User IP address during download')
    )

    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'downloads_download_history'
        verbose_name = _('Download History')
        verbose_name_plural = _('Download Histories')
        ordering = ['-created_at']

    def __str__(self):
        course_title = self.course.title if self.course else "Deleted Course"
        return f"History: {course_title} by {self.user.email}"

    @property
    def success_rate(self):
        """Calculate download success rate"""
        if self.total_files == 0:
            return 0
        return (self.successful_files / self.total_files) * 100


class StorageQuota(models.Model):
    """
    User storage quota tracking
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='storage_quota'
    )

    # Quota limits (in bytes)
    total_quota_bytes = models.BigIntegerField(
        default=5368709120,  # 5GB default
        help_text=_('Total storage quota in bytes')
    )

    used_quota_bytes = models.BigIntegerField(
        default=0,
        help_text=_('Used storage in bytes')
    )

    # File count limits
    max_files = models.PositiveIntegerField(
        default=1000,
        help_text=_('Maximum number of files')
    )

    current_files = models.PositiveIntegerField(
        default=0,
        help_text=_('Current number of files')
    )

    # Warning thresholds
    warning_threshold_percentage = models.FloatField(
        default=80.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=_('Warning threshold percentage')
    )

    # Status flags
    quota_exceeded = models.BooleanField(
        default=False,
        help_text=_('Quota has been exceeded')
    )

    warning_sent = models.BooleanField(
        default=False,
        help_text=_('Warning notification sent')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_cleanup = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'downloads_storage_quota'
        verbose_name = _('Storage Quota')
        verbose_name_plural = _('Storage Quotas')

    def __str__(self):
        return f"Storage: {self.user.email}"

    @property
    def usage_percentage(self):
        """Calculate storage usage percentage"""
        if self.total_quota_bytes == 0:
            return 0
        return (self.used_quota_bytes / self.total_quota_bytes) * 100

    @property
    def remaining_bytes(self):
        """Get remaining storage space"""
        return max(0, self.total_quota_bytes - self.used_quota_bytes)

    def is_quota_exceeded(self):
        """Check if quota is exceeded"""
        return self.used_quota_bytes >= self.total_quota_bytes

    def is_warning_threshold_reached(self):
        """Check if warning threshold is reached"""
        return self.usage_percentage >= self.warning_threshold_percentage

    def add_usage(self, bytes_used, file_count=1):
        """Add storage usage"""
        self.used_quota_bytes += bytes_used
        self.current_files += file_count
        self.quota_exceeded = self.is_quota_exceeded()

        if self.is_warning_threshold_reached() and not self.warning_sent:
            self.warning_sent = True

        self.save()

    def remove_usage(self, bytes_removed, file_count=1):
        """Remove storage usage"""
        self.used_quota_bytes = max(0, self.used_quota_bytes - bytes_removed)
        self.current_files = max(0, self.current_files - file_count)
        self.quota_exceeded = self.is_quota_exceeded()

        # Reset warning if usage drops below threshold
        if not self.is_warning_threshold_reached():
            self.warning_sent = False

        self.save()