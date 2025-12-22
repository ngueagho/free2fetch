"""
Analytics Models for Free2Fetch
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid
import json

User = get_user_model()


class UserActivity(models.Model):
    """
    Track user activities for analytics
    """
    ACTION_CHOICES = [
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('course_view', _('Course View')),
        ('course_download', _('Course Download')),
        ('search', _('Search')),
        ('profile_update', _('Profile Update')),
        ('subscription_change', _('Subscription Change')),
        ('share_course', _('Share Course')),
        ('stream_video', _('Stream Video')),
        ('api_request', _('API Request')),
        ('file_upload', _('File Upload')),
        ('settings_change', _('Settings Change')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        null=True,
        blank=True,  # Allow anonymous users
        help_text=_('User who performed the action')
    )

    # Activity details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text=_('Type of action performed')
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Human-readable description of the action')
    )

    # Related object (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Context data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional context data')
    )

    # Request information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('User IP address')
    )

    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )

    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text=_('User session key')
    )

    # Location and device info
    country = models.CharField(
        max_length=2,
        blank=True,
        help_text=_('Country code based on IP')
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('City based on IP')
    )

    device_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Device type (mobile, desktop, tablet)')
    )

    browser = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Browser name and version')
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Operating system')
    )

    # Performance metrics
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Response time in milliseconds')
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the activity occurred')
    )

    class Meta:
        db_table = 'analytics_user_activity'
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else 'Anonymous'
        return f"{user_email} - {self.action} - {self.created_at}"


class PageView(models.Model):
    """
    Track page views for analytics
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='page_views',
        null=True,
        blank=True
    )

    # Page information
    path = models.CharField(
        max_length=500,
        help_text=_('URL path visited')
    )

    full_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text=_('Full URL including parameters')
    )

    page_title = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Page title')
    )

    referrer = models.URLField(
        max_length=1000,
        blank=True,
        help_text=_('Referring URL')
    )

    # Session information
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text=_('Session identifier')
    )

    # Request details
    ip_address = models.GenericIPAddressField(
        help_text=_('Visitor IP address')
    )

    user_agent = models.TextField(
        help_text=_('User agent string')
    )

    # Geographic data
    country = models.CharField(
        max_length=2,
        blank=True,
        help_text=_('Country code')
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('City name')
    )

    # Device information
    device_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Device type')
    )

    browser = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Browser information')
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Operating system')
    )

    screen_resolution = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Screen resolution (e.g., 1920x1080)')
    )

    # Engagement metrics
    time_on_page_seconds = models.PositiveIntegerField(
        default=0,
        help_text=_('Time spent on page in seconds')
    )

    bounce = models.BooleanField(
        default=False,
        help_text=_('Single page session (bounce)')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_page_view'
        verbose_name = _('Page View')
        verbose_name_plural = _('Page Views')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['path', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        user_info = self.user.email if self.user else f"Anonymous ({self.ip_address})"
        return f"{user_info} - {self.path}"


class DownloadAnalytics(models.Model):
    """
    Analytics for download performance and usage
    """
    STATUS_CHOICES = [
        ('started', _('Started')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_analytics'
    )

    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='download_analytics'
    )

    download_job = models.ForeignKey(
        'downloads.DownloadJob',
        on_delete=models.CASCADE,
        related_name='analytics',
        null=True,
        blank=True
    )

    # Download details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        help_text=_('Download status')
    )

    quality_requested = models.CharField(
        max_length=20,
        help_text=_('Requested video quality')
    )

    total_files = models.PositiveIntegerField(
        default=0,
        help_text=_('Total files in download')
    )

    completed_files = models.PositiveIntegerField(
        default=0,
        help_text=_('Successfully downloaded files')
    )

    # Size and performance
    total_size_mb = models.FloatField(
        default=0.0,
        help_text=_('Total download size in MB')
    )

    download_speed_mbps = models.FloatField(
        default=0.0,
        help_text=_('Average download speed in Mbps')
    )

    total_duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text=_('Total download time in seconds')
    )

    # Error tracking
    error_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of errors encountered')
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of retries attempted')
    )

    # User behavior
    user_cancelled = models.BooleanField(
        default=False,
        help_text=_('User manually cancelled download')
    )

    user_paused = models.BooleanField(
        default=False,
        help_text=_('User paused download')
    )

    # System information
    server_region = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Server region where download was processed')
    )

    cdn_used = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('CDN endpoint used for download')
    )

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'analytics_download_analytics'
        verbose_name = _('Download Analytics')
        verbose_name_plural = _('Download Analytics')
        ordering = ['-started_at']

    def __str__(self):
        return f"Download Analytics: {self.course.title} by {self.user.email}"

    @property
    def success_rate(self):
        """Calculate download success rate"""
        if self.total_files == 0:
            return 0
        return (self.completed_files / self.total_files) * 100

    @property
    def duration_formatted(self):
        """Format duration as HH:MM:SS"""
        hours = self.total_duration_seconds // 3600
        minutes = (self.total_duration_seconds % 3600) // 60
        seconds = self.total_duration_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class SystemMetrics(models.Model):
    """
    System performance and usage metrics
    """
    METRIC_TYPE_CHOICES = [
        ('cpu_usage', _('CPU Usage')),
        ('memory_usage', _('Memory Usage')),
        ('disk_usage', _('Disk Usage')),
        ('network_io', _('Network I/O')),
        ('active_users', _('Active Users')),
        ('concurrent_downloads', _('Concurrent Downloads')),
        ('api_requests', _('API Requests')),
        ('error_rate', _('Error Rate')),
        ('response_time', _('Response Time')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Metric identification
    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPE_CHOICES,
        help_text=_('Type of metric')
    )

    metric_name = models.CharField(
        max_length=100,
        help_text=_('Specific metric name')
    )

    # Metric values
    value = models.FloatField(
        help_text=_('Metric value')
    )

    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Unit of measurement')
    )

    # Context
    tags = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional tags for filtering and grouping')
    )

    server_instance = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Server instance identifier')
    )

    # Timestamp
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When metric was recorded')
    )

    class Meta:
        db_table = 'analytics_system_metrics'
        verbose_name = _('System Metric')
        verbose_name_plural = _('System Metrics')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_type', 'recorded_at']),
            models.Index(fields=['server_instance', 'recorded_at']),
        ]

    def __str__(self):
        return f"{self.metric_name}: {self.value} {self.unit}"


class UsageStatistics(models.Model):
    """
    Daily usage statistics rollup
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    date = models.DateField(
        help_text=_('Statistics date')
    )

    # User statistics
    total_users = models.PositiveIntegerField(
        default=0,
        help_text=_('Total registered users')
    )

    active_users = models.PositiveIntegerField(
        default=0,
        help_text=_('Active users on this date')
    )

    new_signups = models.PositiveIntegerField(
        default=0,
        help_text=_('New user signups')
    )

    # Subscription statistics
    free_users = models.PositiveIntegerField(
        default=0,
        help_text=_('Users on free plan')
    )

    premium_users = models.PositiveIntegerField(
        default=0,
        help_text=_('Users on premium plans')
    )

    # Download statistics
    total_downloads = models.PositiveIntegerField(
        default=0,
        help_text=_('Total downloads started')
    )

    completed_downloads = models.PositiveIntegerField(
        default=0,
        help_text=_('Successfully completed downloads')
    )

    failed_downloads = models.PositiveIntegerField(
        default=0,
        help_text=_('Failed downloads')
    )

    total_download_size_gb = models.FloatField(
        default=0.0,
        help_text=_('Total download volume in GB')
    )

    # Course statistics
    total_courses = models.PositiveIntegerField(
        default=0,
        help_text=_('Total courses in system')
    )

    popular_courses = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of most popular courses')
    )

    # System statistics
    server_uptime_percentage = models.FloatField(
        default=0.0,
        help_text=_('Server uptime percentage')
    )

    average_response_time_ms = models.FloatField(
        default=0.0,
        help_text=_('Average response time in milliseconds')
    )

    error_rate_percentage = models.FloatField(
        default=0.0,
        help_text=_('Error rate percentage')
    )

    # Revenue statistics (for admin)
    daily_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Daily revenue')
    )

    new_subscriptions = models.PositiveIntegerField(
        default=0,
        help_text=_('New subscription purchases')
    )

    cancelled_subscriptions = models.PositiveIntegerField(
        default=0,
        help_text=_('Subscription cancellations')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_usage_statistics'
        verbose_name = _('Usage Statistics')
        verbose_name_plural = _('Usage Statistics')
        unique_together = ['date']
        ordering = ['-date']

    def __str__(self):
        return f"Usage Stats for {self.date}"

    @property
    def download_success_rate(self):
        """Calculate download success rate"""
        if self.total_downloads == 0:
            return 0
        return (self.completed_downloads / self.total_downloads) * 100


class ErrorLog(models.Model):
    """
    Application error logging for monitoring
    """
    SEVERITY_CHOICES = [
        ('debug', _('Debug')),
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('error', _('Error')),
        ('critical', _('Critical')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Error details
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='error',
        help_text=_('Error severity level')
    )

    message = models.TextField(
        help_text=_('Error message')
    )

    exception_type = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Exception class name')
    )

    stack_trace = models.TextField(
        blank=True,
        help_text=_('Full stack trace')
    )

    # Context
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='error_logs'
    )

    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Request path where error occurred')
    )

    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('HTTP method')
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('User IP address')
    )

    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )

    # Additional context
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional error context')
    )

    # Status
    resolved = models.BooleanField(
        default=False,
        help_text=_('Error has been resolved')
    )

    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_errors'
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When error was resolved')
    )

    # Timestamps
    occurred_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When error occurred')
    )

    class Meta:
        db_table = 'analytics_error_log'
        verbose_name = _('Error Log')
        verbose_name_plural = _('Error Logs')
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['severity', 'occurred_at']),
            models.Index(fields=['user', 'occurred_at']),
            models.Index(fields=['resolved', 'occurred_at']),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.message[:100]}"