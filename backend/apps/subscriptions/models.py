"""
Subscription Models for Free2Fetch
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
import uuid
from decimal import Decimal

User = get_user_model()


class SubscriptionPlan(models.Model):
    """
    Subscription plan configuration
    """
    PLAN_TYPE_CHOICES = [
        ('free', _('Free')),
        ('basic', _('Basic')),
        ('premium', _('Premium')),
        ('enterprise', _('Enterprise')),
    ]

    BILLING_PERIOD_CHOICES = [
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('yearly', _('Yearly')),
        ('lifetime', _('Lifetime')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Plan identification
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Plan name')
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_('URL-friendly plan identifier')
    )

    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        help_text=_('Type of subscription plan')
    )

    # Description and marketing
    description = models.TextField(
        blank=True,
        help_text=_('Plan description')
    )

    short_description = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Short marketing description')
    )

    features = models.JSONField(
        default=list,
        help_text=_('List of features included in this plan')
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Plan price')
    )

    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text=_('Currency code')
    )

    billing_period = models.CharField(
        max_length=20,
        choices=BILLING_PERIOD_CHOICES,
        default='monthly',
        help_text=_('Billing frequency')
    )

    # Limits and quotas
    monthly_download_limit = models.PositiveIntegerField(
        default=0,
        help_text=_('Monthly download limit (0 = unlimited)')
    )

    storage_limit_gb = models.PositiveIntegerField(
        default=0,
        help_text=_('Storage limit in GB (0 = unlimited)')
    )

    max_concurrent_downloads = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_('Maximum concurrent downloads')
    )

    max_file_size_mb = models.PositiveIntegerField(
        default=500,
        validators=[MinValueValidator(1)],
        help_text=_('Maximum file size in MB')
    )

    # Feature flags
    streaming_enabled = models.BooleanField(
        default=False,
        help_text=_('Enable course streaming')
    )

    sharing_enabled = models.BooleanField(
        default=False,
        help_text=_('Enable course sharing')
    )

    api_access = models.BooleanField(
        default=False,
        help_text=_('API access enabled')
    )

    priority_support = models.BooleanField(
        default=False,
        help_text=_('Priority customer support')
    )

    advanced_analytics = models.BooleanField(
        default=False,
        help_text=_('Advanced analytics and reporting')
    )

    bulk_downloads = models.BooleanField(
        default=False,
        help_text=_('Bulk download features')
    )

    custom_quality_settings = models.BooleanField(
        default=False,
        help_text=_('Custom quality and format settings')
    )

    # API rate limits
    api_requests_per_hour = models.PositiveIntegerField(
        default=100,
        help_text=_('API requests per hour limit')
    )

    api_requests_per_day = models.PositiveIntegerField(
        default=1000,
        help_text=_('API requests per day limit')
    )

    # Plan management
    is_active = models.BooleanField(
        default=True,
        help_text=_('Plan is available for subscription')
    )

    is_popular = models.BooleanField(
        default=False,
        help_text=_('Mark as popular plan')
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_('Display order')
    )

    # Stripe integration
    stripe_price_id = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Stripe price ID')
    )

    stripe_product_id = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Stripe product ID')
    )

    # Trial settings
    trial_days = models.PositiveIntegerField(
        default=0,
        help_text=_('Free trial period in days')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions_plan'
        verbose_name = _('Subscription Plan')
        verbose_name_plural = _('Subscription Plans')
        ordering = ['sort_order', 'price']

    def __str__(self):
        return f"{self.name} ({self.price} {self.currency}/{self.billing_period})"

    @property
    def is_free(self):
        """Check if plan is free"""
        return self.plan_type == 'free' or self.price == 0

    @property
    def monthly_equivalent_price(self):
        """Calculate monthly equivalent price"""
        if self.billing_period == 'monthly':
            return self.price
        elif self.billing_period == 'quarterly':
            return self.price / 3
        elif self.billing_period == 'yearly':
            return self.price / 12
        else:  # lifetime
            return 0


class Subscription(models.Model):
    """
    User subscription instance
    """
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('trialing', _('Trialing')),
        ('past_due', _('Past Due')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
        ('suspended', _('Suspended')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )

    # Subscription status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text=_('Current subscription status')
    )

    # Dates
    start_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Subscription start date')
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Subscription end date')
    )

    trial_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Trial period end date')
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Cancellation date')
    )

    # Current period
    current_period_start = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Current billing period start')
    )

    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Current billing period end')
    )

    # Usage tracking (resets monthly)
    downloads_used = models.PositiveIntegerField(
        default=0,
        help_text=_('Downloads used in current period')
    )

    storage_used_bytes = models.BigIntegerField(
        default=0,
        help_text=_('Storage used in bytes')
    )

    api_requests_used = models.PositiveIntegerField(
        default=0,
        help_text=_('API requests used today')
    )

    last_usage_reset = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Last usage counter reset')
    )

    # Payment information
    stripe_subscription_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Stripe subscription ID')
    )

    stripe_customer_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Stripe customer ID')
    )

    # Cancellation
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text=_('Cancel at end of current period')
    )

    cancellation_reason = models.TextField(
        blank=True,
        help_text=_('Reason for cancellation')
    )

    # Auto-renewal
    auto_renew = models.BooleanField(
        default=True,
        help_text=_('Automatically renew subscription')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions_subscription'
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status in ['active', 'trialing']

    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        if not self.trial_end_date:
            return False
        from django.utils import timezone
        return timezone.now() < self.trial_end_date

    def can_download(self):
        """Check if user can download based on subscription"""
        if not self.is_active:
            return False

        if self.plan.monthly_download_limit == 0:  # Unlimited
            return True

        return self.downloads_used < self.plan.monthly_download_limit

    def remaining_downloads(self):
        """Get remaining downloads for current period"""
        if self.plan.monthly_download_limit == 0:
            return float('inf')
        return max(0, self.plan.monthly_download_limit - self.downloads_used)

    def can_use_storage(self, additional_bytes=0):
        """Check if additional storage can be used"""
        if self.plan.storage_limit_gb == 0:  # Unlimited
            return True

        limit_bytes = self.plan.storage_limit_gb * 1024 * 1024 * 1024
        return (self.storage_used_bytes + additional_bytes) <= limit_bytes

    def increment_downloads(self, count=1):
        """Increment download counter"""
        self.downloads_used += count
        self.save(update_fields=['downloads_used'])

    def reset_usage_counters(self):
        """Reset monthly usage counters"""
        from django.utils import timezone
        self.downloads_used = 0
        self.api_requests_used = 0
        self.last_usage_reset = timezone.now()
        self.save(update_fields=['downloads_used', 'api_requests_used', 'last_usage_reset'])


class PaymentHistory(models.Model):
    """
    Payment transaction history
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('refunded', _('Refunded')),
        ('cancelled', _('Cancelled')),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('stripe', _('Stripe')),
        ('paypal', _('PayPal')),
        ('bank_transfer', _('Bank Transfer')),
        ('credit_card', _('Credit Card')),
        ('other', _('Other')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_history'
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )

    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_('Payment amount')
    )

    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text=_('Currency code')
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Payment status')
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='stripe',
        help_text=_('Payment method used')
    )

    # External payment information
    stripe_payment_intent_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Stripe payment intent ID')
    )

    stripe_charge_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Stripe charge ID')
    )

    external_transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_('External transaction ID')
    )

    # Payment metadata
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Payment description')
    )

    invoice_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Invoice number')
    )

    # Billing address
    billing_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Billing name')
    )

    billing_email = models.EmailField(
        blank=True,
        help_text=_('Billing email')
    )

    billing_address = models.TextField(
        blank=True,
        help_text=_('Billing address')
    )

    # Error information
    failure_reason = models.TextField(
        blank=True,
        help_text=_('Failure reason if payment failed')
    )

    # Refund information
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Amount refunded')
    )

    refund_reason = models.TextField(
        blank=True,
        help_text=_('Refund reason')
    )

    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Refund date')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Payment processing date')
    )

    class Meta:
        db_table = 'subscriptions_payment_history'
        verbose_name = _('Payment History')
        verbose_name_plural = _('Payment Histories')
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment: {self.amount} {self.currency} by {self.user.email}"


class SubscriptionChange(models.Model):
    """
    Track subscription plan changes
    """
    CHANGE_TYPE_CHOICES = [
        ('upgrade', _('Upgrade')),
        ('downgrade', _('Downgrade')),
        ('renewal', _('Renewal')),
        ('cancellation', _('Cancellation')),
        ('reactivation', _('Reactivation')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscription_changes'
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='changes'
    )

    # Change details
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        help_text=_('Type of change')
    )

    from_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='changes_from',
        null=True,
        blank=True,
        help_text=_('Previous plan')
    )

    to_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='changes_to',
        null=True,
        blank=True,
        help_text=_('New plan')
    )

    # Financial impact
    prorated_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Prorated amount for change')
    )

    # Change reason and notes
    reason = models.TextField(
        blank=True,
        help_text=_('Reason for change')
    )

    admin_notes = models.TextField(
        blank=True,
        help_text=_('Admin notes about the change')
    )

    # Effective dates
    effective_date = models.DateTimeField(
        help_text=_('When change becomes effective')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_subscription_changes',
        help_text=_('Admin who processed the change')
    )

    class Meta:
        db_table = 'subscriptions_subscription_change'
        verbose_name = _('Subscription Change')
        verbose_name_plural = _('Subscription Changes')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.change_type.title()}: {self.user.email} - {self.effective_date}"