"""
Download models for udemy_downloader.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class DownloadTask(models.Model):
    """Main download task model."""

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('preparing', _('Preparing')),
        ('downloading', _('Downloading')),
        ('paused', _('Paused')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]

    # Task identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_tasks'
    )

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='download_tasks'
    )

    # Task configuration
    selected_subtitle = models.CharField(
        _('Selected Subtitle'),
        max_length=100,
        blank=True,
        help_text=_('Selected subtitle language for download')
    )

    download_type = models.IntegerField(
        _('Download Type'),
        choices=[
            (0, _('Both (Videos + Attachments)')),
            (1, _('Only Lectures')),
            (2, _('Only Attachments')),
        ],
        default=0
    )

    video_quality = models.CharField(
        _('Video Quality'),
        max_length=20,
        default='Auto'
    )

    # Range download settings
    enable_range_download = models.BooleanField(_('Enable Range Download'), default=False)
    download_start = models.PositiveIntegerField(_('Download Start'), default=1)
    download_end = models.PositiveIntegerField(_('Download End'), default=0)

    # Status and progress
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    progress_percentage = models.FloatField(
        _('Progress Percentage'),
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )

    # Download statistics
    total_items = models.PositiveIntegerField(_('Total Items'), default=0)
    downloaded_items = models.PositiveIntegerField(_('Downloaded Items'), default=0)
    failed_items = models.PositiveIntegerField(_('Failed Items'), default=0)
    encrypted_items = models.PositiveIntegerField(_('Encrypted Items'), default=0)

    # File information
    download_path = models.CharField(_('Download Path'), max_length=1000)
    total_size = models.BigIntegerField(_('Total Size'), default=0, help_text=_('Size in bytes'))
    downloaded_size = models.BigIntegerField(_('Downloaded Size'), default=0, help_text=_('Size in bytes'))

    # Speed and timing
    download_speed = models.FloatField(_('Download Speed'), default=0.0, help_text=_('Speed in bytes/second'))
    estimated_time_remaining = models.DurationField(_('Estimated Time Remaining'), blank=True, null=True)

    # Error handling
    error_message = models.TextField(_('Error Message'), blank=True)
    retry_count = models.PositiveIntegerField(_('Retry Count'), default=0)
    max_retries = models.PositiveIntegerField(_('Max Retries'), default=3)

    # Celery task tracking
    celery_task_id = models.CharField(_('Celery Task ID'), max_length=255, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(_('Started At'), blank=True, null=True)
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)

    class Meta:
        db_table = 'downloads_task'
        verbose_name = _('Download Task')
        verbose_name_plural = _('Download Tasks')
        ordering = ['-created_at']

    def __str__(self):
        return f"Download: {self.course.title} ({self.status})"

    @property
    def is_active(self):
        """Check if download is currently active."""
        return self.status in ['preparing', 'downloading']

    @property
    def can_be_resumed(self):
        """Check if download can be resumed."""
        return self.status in ['paused', 'failed']

    @property
    def can_be_cancelled(self):
        """Check if download can be cancelled."""
        return self.status in ['pending', 'preparing', 'downloading', 'paused']

    def calculate_progress(self):
        """Calculate overall progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.downloaded_items / self.total_items) * 100


class DownloadItem(models.Model):
    """Individual download item (lecture, attachment, subtitle, etc.)."""

    ITEM_TYPE_CHOICES = [
        ('video', _('Video')),
        ('article', _('Article')),
        ('attachment', _('Attachment')),
        ('subtitle', _('Subtitle')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('downloading', _('Downloading')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('skipped', _('Skipped')),
        ('encrypted', _('Encrypted')),
    ]

    # Relationships
    download_task = models.ForeignKey(
        DownloadTask,
        on_delete=models.CASCADE,
        related_name='download_items'
    )

    lecture = models.ForeignKey(
        'courses.Lecture',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    # Item information
    item_type = models.CharField(
        _('Item Type'),
        max_length=20,
        choices=ITEM_TYPE_CHOICES
    )

    filename = models.CharField(_('Filename'), max_length=500)
    source_url = models.URLField(_('Source URL'), max_length=2000)

    # Status and progress
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    progress_percentage = models.FloatField(
        _('Progress Percentage'),
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )

    # File information
    file_path = models.CharField(_('File Path'), max_length=1000, blank=True)
    file_size = models.BigIntegerField(_('File Size'), default=0, help_text=_('Size in bytes'))
    downloaded_size = models.BigIntegerField(_('Downloaded Size'), default=0, help_text=_('Size in bytes'))

    # Quality and format
    quality = models.CharField(_('Quality'), max_length=20, blank=True)
    format = models.CharField(_('Format'), max_length=50, blank=True)

    # Download metadata
    download_speed = models.FloatField(_('Download Speed'), default=0.0, help_text=_('Speed in bytes/second'))
    is_encrypted = models.BooleanField(_('Is Encrypted'), default=False)

    # Error handling
    error_message = models.TextField(_('Error Message'), blank=True)
    retry_count = models.PositiveIntegerField(_('Retry Count'), default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(_('Started At'), blank=True, null=True)
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)

    class Meta:
        db_table = 'downloads_item'
        verbose_name = _('Download Item')
        verbose_name_plural = _('Download Items')
        ordering = ['download_task', 'created_at']

    def __str__(self):
        return f"{self.filename} ({self.status})"


class DownloadHistory(models.Model):
    """Download history tracking model."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_history'
    )

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='download_history'
    )

    # Download information
    is_completed = models.BooleanField(_('Is Completed'), default=False)
    completion_date = models.DateTimeField(_('Completion Date'), blank=True, null=True)
    download_path = models.CharField(_('Download Path'), max_length=1000)

    # Statistics
    encrypted_videos_count = models.PositiveIntegerField(_('Encrypted Videos Count'), default=0)
    total_size = models.BigIntegerField(_('Total Size'), default=0, help_text=_('Size in bytes'))
    selected_subtitle = models.CharField(_('Selected Subtitle'), max_length=100, blank=True)

    # Quality settings used
    video_quality = models.CharField(_('Video Quality'), max_length=20)
    download_type = models.IntegerField(_('Download Type'), default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'downloads_history'
        verbose_name = _('Download History')
        verbose_name_plural = _('Download History')
        ordering = ['-updated_at']
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.completion_date})"


class DownloadSession(models.Model):
    """Track download sessions for analytics and monitoring."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_sessions'
    )

    # Session information
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)

    # Session statistics
    total_downloads = models.PositiveIntegerField(_('Total Downloads'), default=0)
    successful_downloads = models.PositiveIntegerField(_('Successful Downloads'), default=0)
    failed_downloads = models.PositiveIntegerField(_('Failed Downloads'), default=0)

    # Data usage
    total_data_downloaded = models.BigIntegerField(_('Total Data Downloaded'), default=0, help_text=_('Size in bytes'))
    average_speed = models.FloatField(_('Average Speed'), default=0.0, help_text=_('Speed in bytes/second'))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(_('Ended At'), blank=True, null=True)

    class Meta:
        db_table = 'downloads_session'
        verbose_name = _('Download Session')
        verbose_name_plural = _('Download Sessions')
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id} - {self.user.username}"

    @property
    def duration(self):
        """Calculate session duration."""
        if self.ended_at:
            return self.ended_at - self.created_at
        return None

    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_downloads == 0:
            return 0.0
        return (self.successful_downloads / self.total_downloads) * 100