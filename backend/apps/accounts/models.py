"""
User Account Models for Free2Fetch
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
import uuid


class User(AbstractUser):
    """
    Extended User model with additional fields for Free2Fetch
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Required. Enter a valid email address.')
    )

    # Profile fields
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text=_('User profile picture')
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_('User phone number')
    )

    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text=_('User timezone')
    )

    language = models.CharField(
        max_length=10,
        default='en',
        help_text=_('User preferred language')
    )

    # Account status
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Email verification status')
    )

    is_premium = models.BooleanField(
        default=False,
        help_text=_('Premium subscription status')
    )

    # Udemy integration
    udemy_user_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Udemy user ID for API integration')
    )

    udemy_access_token = models.TextField(
        blank=True,
        null=True,
        help_text=_('Udemy OAuth access token')
    )

    udemy_refresh_token = models.TextField(
        blank=True,
        null=True,
        help_text=_('Udemy OAuth refresh token')
    )

    udemy_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Udemy token expiration time')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def has_valid_udemy_token(self):
        """Check if user has a valid Udemy token"""
        if not self.udemy_access_token:
            return False
        if not self.udemy_token_expires_at:
            return True
        from django.utils import timezone
        return timezone.now() < self.udemy_token_expires_at


class UserProfile(models.Model):
    """
    Extended user profile with additional information
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Personal information
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text=_('User biography')
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        help_text=_('User birth date')
    )

    location = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('User location')
    )

    website = models.URLField(
        blank=True,
        help_text=_('User website')
    )

    # Privacy settings
    public_profile = models.BooleanField(
        default=True,
        help_text=_('Make profile public')
    )

    email_notifications = models.BooleanField(
        default=True,
        help_text=_('Receive email notifications')
    )

    newsletter_subscription = models.BooleanField(
        default=False,
        help_text=_('Subscribe to newsletter')
    )

    # Usage statistics
    total_downloads = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of downloads')
    )

    total_storage_used = models.BigIntegerField(
        default=0,
        help_text=_('Total storage used in bytes')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_user_profile'
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')

    def __str__(self):
        return f"Profile for {self.user.email}"


class UserSubscription(models.Model):
    """
    User subscription model for freemium features
    """
    PLAN_CHOICES = [
        ('free', _('Free')),
        ('basic', _('Basic')),
        ('premium', _('Premium')),
        ('enterprise', _('Enterprise')),
    ]

    STATUS_CHOICES = [
        ('active', _('Active')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
        ('suspended', _('Suspended')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='subscription'
    )

    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='free',
        help_text=_('Subscription plan')
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text=_('Subscription status')
    )

    # Limits based on plan
    monthly_download_limit = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(0)],
        help_text=_('Monthly download limit')
    )

    current_month_downloads = models.PositiveIntegerField(
        default=0,
        help_text=_('Downloads used this month')
    )

    storage_limit_gb = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(0)],
        help_text=_('Storage limit in GB')
    )

    max_concurrent_downloads = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Maximum concurrent downloads allowed')
    )

    # Features enabled
    streaming_enabled = models.BooleanField(
        default=False,
        help_text=_('Enable course streaming')
    )

    sharing_enabled = models.BooleanField(
        default=False,
        help_text=_('Enable course sharing')
    )

    api_access_enabled = models.BooleanField(
        default=False,
        help_text=_('Enable API access')
    )

    priority_support = models.BooleanField(
        default=False,
        help_text=_('Priority customer support')
    )

    # Subscription dates
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Subscription expiry date')
    )

    # Payment information
    stripe_subscription_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Stripe subscription ID')
    )

    # Reset tracking
    last_reset_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Last monthly reset date')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_user_subscription'
        verbose_name = _('User Subscription')
        verbose_name_plural = _('User Subscriptions')

    def __str__(self):
        return f"{self.user.email} - {self.plan.title()} Plan"

    def can_download(self):
        """Check if user can download based on their subscription"""
        if self.plan == 'free':
            return self.current_month_downloads < self.monthly_download_limit
        elif self.plan in ['basic', 'premium', 'enterprise']:
            if self.status != 'active':
                return False
            return self.current_month_downloads < self.monthly_download_limit
        return False

    def remaining_downloads(self):
        """Get remaining downloads for this month"""
        return max(0, self.monthly_download_limit - self.current_month_downloads)

    def reset_monthly_usage(self):
        """Reset monthly download counter"""
        from django.utils import timezone
        self.current_month_downloads = 0
        self.last_reset_date = timezone.now()
        self.save()


class UserLoginLog(models.Model):
    """
    Track user login activities for security and analytics
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_logs'
    )

    ip_address = models.GenericIPAddressField(
        help_text=_('IP address of login attempt')
    )

    user_agent = models.TextField(
        help_text=_('User agent string')
    )

    success = models.BooleanField(
        default=True,
        help_text=_('Login attempt was successful')
    )

    location = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Geographic location based on IP')
    )

    device_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Type of device used')
    )

    browser = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Browser used for login')
    )

    # Timestamps
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Logout time if available')
    )

    class Meta:
        db_table = 'accounts_user_login_log'
        verbose_name = _('User Login Log')
        verbose_name_plural = _('User Login Logs')
        ordering = ['-login_time']

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.user.email} - {status} - {self.login_time}"