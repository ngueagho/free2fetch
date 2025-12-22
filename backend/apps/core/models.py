"""
Core Models for Free2Fetch
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class SystemSettings(models.Model):
    """
    System-wide settings and configuration
    """
    SETTING_TYPE_CHOICES = [
        ('string', _('String')),
        ('integer', _('Integer')),
        ('float', _('Float')),
        ('boolean', _('Boolean')),
        ('json', _('JSON')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Setting identification
    key = models.CharField(
        max_length=200,
        unique=True,
        help_text=_('Setting key (dot notation supported)')
    )

    name = models.CharField(
        max_length=200,
        help_text=_('Human-readable setting name')
    )

    description = models.TextField(
        blank=True,
        help_text=_('Setting description')
    )

    # Value and type
    value = models.TextField(
        help_text=_('Setting value as string')
    )

    value_type = models.CharField(
        max_length=20,
        choices=SETTING_TYPE_CHOICES,
        default='string',
        help_text=_('Data type of the value')
    )

    default_value = models.TextField(
        blank=True,
        help_text=_('Default value')
    )

    # Validation
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Validation rules for the setting value')
    )

    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text=_('Setting is accessible via public API')
    )

    is_editable = models.BooleanField(
        default=True,
        help_text=_('Setting can be modified')
    )

    requires_restart = models.BooleanField(
        default=False,
        help_text=_('Changing this setting requires application restart')
    )

    # Organization
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Setting category for organization')
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_('Display order within category')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )

    class Meta:
        db_table = 'core_system_settings'
        verbose_name = _('System Setting')
        verbose_name_plural = _('System Settings')
        ordering = ['category', 'sort_order', 'key']

    def __str__(self):
        return f"{self.key}: {self.value}"

    def get_typed_value(self):
        """Return the value converted to its proper type"""
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value

    def set_typed_value(self, value):
        """Set the value from a typed input"""
        if self.value_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)


class APIKey(models.Model):
    """
    API keys for external integrations
    """
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('revoked', _('Revoked')),
        ('expired', _('Expired')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )

    # Key details
    name = models.CharField(
        max_length=200,
        help_text=_('Descriptive name for the API key')
    )

    key = models.CharField(
        max_length=64,
        unique=True,
        help_text=_('The actual API key')
    )

    prefix = models.CharField(
        max_length=8,
        help_text=_('Key prefix for identification')
    )

    # Access control
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text=_('API key status')
    )

    scopes = models.JSONField(
        default=list,
        help_text=_('List of permitted scopes/permissions')
    )

    # Rate limiting
    rate_limit_per_minute = models.PositiveIntegerField(
        default=60,
        help_text=_('Requests per minute limit')
    )

    rate_limit_per_hour = models.PositiveIntegerField(
        default=1000,
        help_text=_('Requests per hour limit')
    )

    rate_limit_per_day = models.PositiveIntegerField(
        default=10000,
        help_text=_('Requests per day limit')
    )

    # Usage tracking
    total_requests = models.BigIntegerField(
        default=0,
        help_text=_('Total API requests made with this key')
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last time this key was used')
    )

    # IP restrictions
    allowed_ips = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of allowed IP addresses (empty = all)')
    )

    # Expiration
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Key expiration date')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_api_key'
        verbose_name = _('API Key')
        verbose_name_plural = _('API Keys')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.prefix}***)"

    @property
    def is_expired(self):
        """Check if API key has expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_active_and_valid(self):
        """Check if API key is active and not expired"""
        return self.status == 'active' and not self.is_expired

    def increment_usage(self):
        """Increment usage counter and update last used time"""
        from django.utils import timezone
        self.total_requests += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['total_requests', 'last_used_at'])


class RateLimit(models.Model):
    """
    Track rate limiting for users and API keys
    """
    LIMIT_TYPE_CHOICES = [
        ('user', _('User')),
        ('api_key', _('API Key')),
        ('ip', _('IP Address')),
    ]

    TIME_WINDOW_CHOICES = [
        ('minute', _('Per Minute')),
        ('hour', _('Per Hour')),
        ('day', _('Per Day')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Subject being rate limited
    limit_type = models.CharField(
        max_length=20,
        choices=LIMIT_TYPE_CHOICES,
        help_text=_('Type of entity being rate limited')
    )

    identifier = models.CharField(
        max_length=200,
        help_text=_('Unique identifier (user ID, API key, IP, etc.)')
    )

    # Rate limiting details
    resource = models.CharField(
        max_length=100,
        help_text=_('Resource being accessed (API endpoint, action, etc.)')
    )

    time_window = models.CharField(
        max_length=20,
        choices=TIME_WINDOW_CHOICES,
        help_text=_('Time window for the limit')
    )

    # Usage tracking
    request_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of requests in current window')
    )

    limit_count = models.PositiveIntegerField(
        help_text=_('Maximum allowed requests in window')
    )

    # Window tracking
    window_start = models.DateTimeField(
        help_text=_('Start of current time window')
    )

    window_end = models.DateTimeField(
        help_text=_('End of current time window')
    )

    # Status
    is_blocked = models.BooleanField(
        default=False,
        help_text=_('Currently blocked due to rate limiting')
    )

    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Blocked until this time')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_rate_limit'
        verbose_name = _('Rate Limit')
        verbose_name_plural = _('Rate Limits')
        unique_together = ['limit_type', 'identifier', 'resource', 'time_window']
        indexes = [
            models.Index(fields=['identifier', 'resource', 'window_end']),
            models.Index(fields=['is_blocked', 'blocked_until']),
        ]

    def __str__(self):
        return f"Rate limit: {self.identifier} - {self.resource}"

    @property
    def is_limit_exceeded(self):
        """Check if rate limit has been exceeded"""
        return self.request_count >= self.limit_count

    @property
    def remaining_requests(self):
        """Get remaining requests in current window"""
        return max(0, self.limit_count - self.request_count)

    def increment_requests(self, count=1):
        """Increment request counter"""
        self.request_count += count
        if self.is_limit_exceeded:
            self.is_blocked = True
            # Block until end of current window
            self.blocked_until = self.window_end
        self.save()

    def reset_window(self):
        """Reset the rate limiting window"""
        from django.utils import timezone
        from datetime import timedelta

        self.request_count = 0
        self.is_blocked = False
        self.blocked_until = None
        self.window_start = timezone.now()

        if self.time_window == 'minute':
            self.window_end = self.window_start + timedelta(minutes=1)
        elif self.time_window == 'hour':
            self.window_end = self.window_start + timedelta(hours=1)
        elif self.time_window == 'day':
            self.window_end = self.window_start + timedelta(days=1)

        self.save()


class AuditLog(models.Model):
    """
    Audit log for tracking system changes and administrative actions
    """
    ACTION_CHOICES = [
        ('create', _('Create')),
        ('read', _('Read')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('permission_change', _('Permission Change')),
        ('settings_change', _('Settings Change')),
        ('subscription_change', _('Subscription Change')),
        ('download_start', _('Download Start')),
        ('download_complete', _('Download Complete')),
        ('api_access', _('API Access')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Actor (who performed the action)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_('User who performed the action')
    )

    actor_email = models.EmailField(
        blank=True,
        help_text=_('Email of the actor (preserved if user is deleted)')
    )

    # Action details
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text=_('Type of action performed')
    )

    resource_type = models.CharField(
        max_length=100,
        help_text=_('Type of resource affected (model name)')
    )

    resource_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=_('ID of the affected resource')
    )

    resource_repr = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('String representation of the resource')
    )

    # Change details
    old_values = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Previous values (for updates)')
    )

    new_values = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('New values (for creates/updates)')
    )

    # Context information
    description = models.TextField(
        blank=True,
        help_text=_('Human-readable description of the action')
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('IP address of the actor')
    )

    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )

    # Request context
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Request path where action occurred')
    )

    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text=_('HTTP method')
    )

    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text=_('Session key')
    )

    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional context data')
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the action occurred')
    )

    class Meta:
        db_table = 'core_audit_log'
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        actor = self.user.email if self.user else self.actor_email or 'System'
        return f"{actor} {self.action} {self.resource_type} at {self.created_at}"


class Feature(models.Model):
    """
    Feature flags for controlling functionality
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Feature identification
    key = models.CharField(
        max_length=200,
        unique=True,
        help_text=_('Unique feature key')
    )

    name = models.CharField(
        max_length=200,
        help_text=_('Human-readable feature name')
    )

    description = models.TextField(
        blank=True,
        help_text=_('Feature description')
    )

    # Feature status
    is_enabled = models.BooleanField(
        default=False,
        help_text=_('Feature is enabled globally')
    )

    is_staff_only = models.BooleanField(
        default=False,
        help_text=_('Feature is only available to staff users')
    )

    # Rollout configuration
    rollout_percentage = models.PositiveIntegerField(
        default=0,
        help_text=_('Percentage of users who should see this feature (0-100)')
    )

    target_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='targeted_features',
        help_text=_('Specific users who should see this feature')
    )

    # Conditions
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Conditions that must be met for feature to be enabled')
    )

    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_features'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_feature'
        verbose_name = _('Feature')
        verbose_name_plural = _('Features')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({'Enabled' if self.is_enabled else 'Disabled'})"

    def is_enabled_for_user(self, user):
        """Check if feature is enabled for a specific user"""
        if not self.is_enabled:
            return False

        # Staff-only check
        if self.is_staff_only and not user.is_staff:
            return False

        # Specific user targeting
        if self.target_users.filter(id=user.id).exists():
            return True

        # Rollout percentage check
        if self.rollout_percentage > 0:
            # Use user ID to determine if they're in the rollout
            user_hash = hash(str(user.id) + self.key) % 100
            return user_hash < self.rollout_percentage

        return True