"""
User models for udemy_downloader.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with additional fields for Udemy integration."""

    # Udemy specific fields
    udemy_access_token = models.TextField(
        _('Udemy Access Token'),
        blank=True,
        null=True,
        help_text=_('Udemy API access token for authentication')
    )

    udemy_subdomain = models.CharField(
        _('Udemy Subdomain'),
        max_length=100,
        default='www',
        help_text=_('Udemy subdomain (www for regular users, company name for business)')
    )

    is_udemy_subscriber = models.BooleanField(
        _('Is Udemy Subscriber'),
        default=False,
        help_text=_('Whether user has an active Udemy subscription')
    )

    # Preferences
    preferred_language = models.CharField(
        _('Preferred Language'),
        max_length=10,
        default='en',
        choices=[
            ('en', _('English')),
            ('es', _('Español')),
            ('fr', _('Français')),
            ('de', _('Deutsch')),
            ('it', _('Italian')),
            ('pt-br', _('Português')),
            ('ru', _('Русский')),
            ('ja', _('日本語')),
            ('ko', _('한국어')),
            ('zh', _('简体中文')),
            ('ar', _('العربية')),
            ('hi', _('हिंदी')),
            ('tr', _('Türkçe')),
            ('pl', _('Polski')),
            ('hu', _('Magyar')),
            ('vi', _('Tiếng Việt')),
            ('ms', _('Bahasa Malaysia')),
            ('id', _('Indonesia')),
            ('fa', _('فارسی')),
            ('ta', _('தமிழ்')),
            ('am', _('አማርኛ')),
            ('my', _('မြန်မာ')),
            ('pa', _('Punjabi')),
            ('gr', _('Ελληνικά')),
        ]
    )

    # Timestamps
    last_login_udemy = models.DateTimeField(
        _('Last Udemy Login'),
        blank=True,
        null=True
    )

    token_expires_at = models.DateTimeField(
        _('Token Expires At'),
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'users_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username

    @property
    def is_token_valid(self):
        """Check if the Udemy access token is still valid."""
        if not self.udemy_access_token:
            return False

        if self.token_expires_at:
            from django.utils import timezone
            return timezone.now() < self.token_expires_at

        return True

    def clear_udemy_credentials(self):
        """Clear Udemy authentication data."""
        self.udemy_access_token = None
        self.token_expires_at = None
        self.last_login_udemy = None
        self.save(update_fields=['udemy_access_token', 'token_expires_at', 'last_login_udemy'])


class UserPreferences(models.Model):
    """User preferences model replicating the original settings structure."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences'
    )

    # Download settings
    check_new_version = models.BooleanField(_('Check New Version'), default=True)
    auto_start_download = models.BooleanField(_('Auto Start Download'), default=False)
    continue_downloading_encrypted = models.BooleanField(_('Continue Downloading Encrypted'), default=False)
    enable_download_start_end = models.BooleanField(_('Enable Download Start/End'), default=False)
    download_start = models.PositiveIntegerField(_('Download Start'), default=0)
    download_end = models.PositiveIntegerField(_('Download End'), default=0)

    # Quality and format settings
    video_quality = models.CharField(
        _('Video Quality'),
        max_length=20,
        default='Auto',
        choices=[
            ('Auto', _('Auto')),
            ('144', '144p'),
            ('240', '240p'),
            ('360', '360p'),
            ('480', '480p'),
            ('720', '720p'),
            ('1080', '1080p'),
            ('Highest', _('Highest')),
            ('Lowest', _('Lowest')),
        ]
    )

    DOWNLOAD_TYPE_CHOICES = [
        (0, _('Both (Videos + Attachments)')),
        (1, _('Only Lectures')),
        (2, _('Only Attachments')),
    ]

    download_type = models.IntegerField(
        _('Download Type'),
        choices=DOWNLOAD_TYPE_CHOICES,
        default=0
    )

    # Subtitle settings
    skip_subtitles = models.BooleanField(_('Skip Subtitles'), default=False)
    default_subtitle = models.CharField(
        _('Default Subtitle'),
        max_length=50,
        blank=True,
        help_text=_('Default subtitle language')
    )

    # File management
    download_path = models.CharField(
        _('Download Path'),
        max_length=500,
        help_text=_('Directory where courses will be downloaded')
    )

    seq_zero_left = models.BooleanField(
        _('Sequence Zero Left'),
        default=False,
        help_text=_('Add leading zeros to file names')
    )

    auto_retry = models.BooleanField(_('Auto Retry'), default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_preferences'
        verbose_name = _('User Preferences')
        verbose_name_plural = _('User Preferences')

    def __str__(self):
        return f"{self.user.username} preferences"

    @classmethod
    def get_default_download_path(cls, user):
        """Get default download path for user."""
        from pathlib import Path
        return str(Path.home() / "Downloads" / "Udeler")


class UserSession(models.Model):
    """Track user sessions and activity."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    session_id = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)

    # Activity tracking
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_session'
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.session_id}"


# Alias for compatibility
UserSettings = UserPreferences