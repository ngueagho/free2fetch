"""
Notification Models for Free2Fetch
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid

User = get_user_model()


class NotificationTemplate(models.Model):
    """
    Email and notification templates
    """
    TEMPLATE_TYPE_CHOICES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('push', _('Push Notification')),
        ('in_app', _('In-App Notification')),
    ]

    CATEGORY_CHOICES = [
        ('welcome', _('Welcome')),
        ('download_complete', _('Download Complete')),
        ('download_failed', _('Download Failed')),
        ('quota_warning', _('Quota Warning')),
        ('quota_exceeded', _('Quota Exceeded')),
        ('subscription_expiry', _('Subscription Expiry')),
        ('payment_success', _('Payment Success')),
        ('payment_failed', _('Payment Failed')),
        ('account_verification', _('Account Verification')),
        ('password_reset', _('Password Reset')),
        ('security_alert', _('Security Alert')),
        ('system_maintenance', _('System Maintenance')),
        ('course_update', _('Course Update')),
        ('share_notification', _('Share Notification')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Template identification
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text=_('Template identifier name')
    )

    display_name = models.CharField(
        max_length=200,
        help_text=_('Human-readable template name')
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text=_('Notification category')
    )

    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default='email',
        help_text=_('Type of notification template')
    )

    # Template content
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Email subject or notification title')
    )

    html_content = models.TextField(
        blank=True,
        help_text=_('HTML content for email templates')
    )

    text_content = models.TextField(
        blank=True,
        help_text=_('Plain text content')
    )

    # Template variables
    available_variables = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of available template variables')
    )

    # Settings
    is_active = models.BooleanField(
        default=True,
        help_text=_('Template is active and can be used')
    )

    is_system = models.BooleanField(
        default=False,
        help_text=_('System template (cannot be deleted)')
    )

    # Delivery settings
    send_immediately = models.BooleanField(
        default=True,
        help_text=_('Send immediately or queue for batch processing')
    )

    batch_delay_minutes = models.PositiveIntegerField(
        default=0,
        help_text=_('Delay in minutes for batch processing')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications_template'
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.display_name} ({self.template_type})"


class Notification(models.Model):
    """
    Individual notification instances
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]

    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Recipient information
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Template and content
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        related_name='notifications'
    )

    subject = models.CharField(
        max_length=200,
        help_text=_('Final rendered subject')
    )

    content = models.TextField(
        help_text=_('Final rendered content')
    )

    html_content = models.TextField(
        blank=True,
        help_text=_('Final rendered HTML content')
    )

    # Delivery details
    recipient_email = models.EmailField(
        help_text=_('Email address where notification was sent')
    )

    recipient_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Phone number for SMS notifications')
    )

    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Notification delivery status')
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text=_('Notification priority')
    )

    # Delivery tracking
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification was sent')
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification was delivered')
    )

    opened_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When email was opened (if tracked)')
    )

    clicked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When email link was clicked')
    )

    # Error handling
    failure_reason = models.TextField(
        blank=True,
        help_text=_('Reason for delivery failure')
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of delivery attempts')
    )

    max_retries = models.PositiveIntegerField(
        default=3,
        help_text=_('Maximum retry attempts')
    )

    # Related object context
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Additional context data
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional context data used in template')
    )

    # External service tracking
    external_id = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('External service message ID')
    )

    provider = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Email/SMS provider used')
    )

    # Scheduled delivery
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Scheduled delivery time')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications_notification'
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['template', 'created_at']),
        ]

    def __str__(self):
        return f"Notification to {self.user.email}: {self.subject}"

    @property
    def is_read(self):
        """Check if notification has been read/opened"""
        return self.opened_at is not None

    @property
    def can_retry(self):
        """Check if notification can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries


class InAppNotification(models.Model):
    """
    In-app notifications for user dashboard
    """
    TYPE_CHOICES = [
        ('info', _('Information')),
        ('success', _('Success')),
        ('warning', _('Warning')),
        ('error', _('Error')),
        ('announcement', _('Announcement')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='in_app_notifications'
    )

    # Notification content
    title = models.CharField(
        max_length=200,
        help_text=_('Notification title')
    )

    message = models.TextField(
        help_text=_('Notification message')
    )

    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='info',
        help_text=_('Type of notification')
    )

    # Action button (optional)
    action_text = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Action button text')
    )

    action_url = models.URLField(
        blank=True,
        help_text=_('Action button URL')
    )

    # Status
    is_read = models.BooleanField(
        default=False,
        help_text=_('User has read the notification')
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification was read')
    )

    is_dismissed = models.BooleanField(
        default=False,
        help_text=_('User has dismissed the notification')
    )

    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification was dismissed')
    )

    # Related object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Expiration
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification expires')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications_in_app_notification'
        verbose_name = _('In-App Notification')
        verbose_name_plural = _('In-App Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"In-App: {self.title} for {self.user.email}"

    @property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def dismiss(self):
        """Dismiss the notification"""
        if not self.is_dismissed:
            from django.utils import timezone
            self.is_dismissed = True
            self.dismissed_at = timezone.now()
            if not self.is_read:
                self.mark_as_read()
            self.save(update_fields=['is_dismissed', 'dismissed_at'])


class UserNotificationPreferences(models.Model):
    """
    User notification preferences and settings
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Email notifications
    email_enabled = models.BooleanField(
        default=True,
        help_text=_('Receive email notifications')
    )

    download_complete = models.BooleanField(
        default=True,
        help_text=_('Notify when downloads complete')
    )

    download_failed = models.BooleanField(
        default=True,
        help_text=_('Notify when downloads fail')
    )

    quota_warnings = models.BooleanField(
        default=True,
        help_text=_('Notify about quota warnings')
    )

    subscription_updates = models.BooleanField(
        default=True,
        help_text=_('Notify about subscription changes')
    )

    security_alerts = models.BooleanField(
        default=True,
        help_text=_('Notify about security issues')
    )

    course_updates = models.BooleanField(
        default=False,
        help_text=_('Notify about course updates')
    )

    # Marketing and promotional
    marketing_emails = models.BooleanField(
        default=False,
        help_text=_('Receive marketing emails')
    )

    newsletter = models.BooleanField(
        default=False,
        help_text=_('Subscribe to newsletter')
    )

    product_updates = models.BooleanField(
        default=True,
        help_text=_('Notify about product updates')
    )

    # In-app notifications
    in_app_enabled = models.BooleanField(
        default=True,
        help_text=_('Show in-app notifications')
    )

    desktop_notifications = models.BooleanField(
        default=False,
        help_text=_('Show desktop/push notifications')
    )

    # Frequency settings
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', _('Immediate')),
            ('daily', _('Daily Digest')),
            ('weekly', _('Weekly Digest')),
            ('never', _('Never')),
        ],
        default='immediate',
        help_text=_('Email digest frequency')
    )

    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text=_('Start of quiet hours (no notifications)')
    )

    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text=_('End of quiet hours')
    )

    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text=_('User timezone for notification timing')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications_user_preferences'
        verbose_name = _('User Notification Preferences')
        verbose_name_plural = _('User Notification Preferences')

    def __str__(self):
        return f"Notification preferences for {self.user.email}"

    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        from django.utils import timezone
        import pytz

        user_tz = pytz.timezone(self.timezone)
        current_time = timezone.now().astimezone(user_tz).time()

        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:  # Quiet hours span midnight
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end


class NotificationBatch(models.Model):
    """
    Batch notification processing
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Batch details
    name = models.CharField(
        max_length=200,
        help_text=_('Batch name/description')
    )

    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        related_name='batches'
    )

    # Target audience
    target_users = models.ManyToManyField(
        User,
        related_name='notification_batches',
        blank=True
    )

    user_filter_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Criteria for selecting target users')
    )

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Batch processing status')
    )

    # Progress tracking
    total_recipients = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of recipients')
    )

    processed_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of notifications processed')
    )

    success_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of successful deliveries')
    )

    failure_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of failed deliveries')
    )

    # Scheduling
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Scheduled processing time')
    )

    # Context data for template
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Context data for template rendering')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_notification_batches'
    )

    class Meta:
        db_table = 'notifications_batch'
        verbose_name = _('Notification Batch')
        verbose_name_plural = _('Notification Batches')
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch: {self.name} ({self.status})"

    @property
    def progress_percentage(self):
        """Calculate processing progress percentage"""
        if self.total_recipients == 0:
            return 0
        return (self.processed_count / self.total_recipients) * 100

    @property
    def success_rate(self):
        """Calculate delivery success rate"""
        if self.processed_count == 0:
            return 0
        return (self.success_count / self.processed_count) * 100