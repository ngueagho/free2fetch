"""
Admin configuration for Accounts app
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserProfile, UserSubscription, UserLoginLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""

    list_display = [
        'email', 'username', 'full_name', 'is_verified', 'is_premium',
        'subscription_plan', 'created_at', 'last_login', 'is_active'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'is_verified', 'is_premium',
        'created_at', 'last_login', 'language', 'timezone'
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_login', 'date_joined',
        'last_login_ip', 'udemy_token_expires_at'
    ]

    fieldsets = (
        (None, {
            'fields': ('id', 'username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'avatar', 'phone',
                'timezone', 'language'
            )
        }),
        ('Account Status', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'is_verified',
                'is_premium'
            )
        }),
        ('Udemy Integration', {
            'fields': (
                'udemy_user_id', 'udemy_access_token', 'udemy_refresh_token',
                'udemy_token_expires_at'
            ),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'last_login_ip', 'date_joined', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    def subscription_plan(self, obj):
        """Display user subscription plan"""
        try:
            subscription = obj.subscription
            color = {
                'free': 'gray',
                'basic': 'blue',
                'premium': 'green',
                'enterprise': 'purple'
            }.get(subscription.plan, 'gray')

            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                subscription.get_plan_display()
            )
        except:
            return format_html('<span style="color: gray;">Free</span>')

    subscription_plan.short_description = 'Plan'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subscription')

    actions = ['verify_users', 'unverify_users', 'make_premium', 'remove_premium']

    def verify_users(self, request, queryset):
        """Bulk verify users"""
        count = queryset.update(is_verified=True)
        self.message_user(request, f'{count} users verified.')

    verify_users.short_description = "Verify selected users"

    def unverify_users(self, request, queryset):
        """Bulk unverify users"""
        count = queryset.update(is_verified=False)
        self.message_user(request, f'{count} users unverified.')

    unverify_users.short_description = "Unverify selected users"

    def make_premium(self, request, queryset):
        """Make users premium"""
        count = queryset.update(is_premium=True)
        self.message_user(request, f'{count} users made premium.')

    make_premium.short_description = "Make premium"

    def remove_premium(self, request, queryset):
        """Remove premium status"""
        count = queryset.update(is_premium=False)
        self.message_user(request, f'{count} users premium removed.')

    remove_premium.short_description = "Remove premium"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model"""

    list_display = [
        'user', 'location', 'public_profile', 'email_notifications',
        'newsletter_subscription', 'total_downloads', 'storage_usage_gb'
    ]
    list_filter = [
        'public_profile', 'email_notifications', 'newsletter_subscription',
        'created_at'
    ]
    search_fields = ['user__email', 'user__username', 'location']
    readonly_fields = ['created_at', 'updated_at', 'total_downloads', 'total_storage_used']

    def storage_usage_gb(self, obj):
        """Display storage usage in GB"""
        gb = obj.total_storage_used / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"

    storage_usage_gb.short_description = 'Storage Used'


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    """Admin interface for UserSubscription model"""

    list_display = [
        'user', 'plan', 'status', 'downloads_used_display', 'storage_used_display',
        'started_at', 'expires_at', 'auto_renew'
    ]
    list_filter = [
        'plan', 'status', 'streaming_enabled', 'sharing_enabled',
        'api_access_enabled', 'priority_support', 'auto_renew'
    ]
    search_fields = ['user__email', 'user__username']
    readonly_fields = [
        'id', 'started_at', 'created_at', 'updated_at', 'last_reset_date'
    ]

    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Usage Limits', {
            'fields': (
                'monthly_download_limit', 'current_month_downloads',
                'storage_limit_gb', 'max_concurrent_downloads'
            )
        }),
        ('Features', {
            'fields': (
                'streaming_enabled', 'sharing_enabled', 'api_access_enabled',
                'priority_support'
            )
        }),
        ('Billing', {
            'fields': (
                'started_at', 'expires_at', 'auto_renew', 'cancel_at_period_end',
                'stripe_subscription_id'
            )
        }),
        ('Usage Reset', {
            'fields': ('last_reset_date',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def downloads_used_display(self, obj):
        """Display downloads usage"""
        percentage = (obj.current_month_downloads / obj.monthly_download_limit) * 100 if obj.monthly_download_limit > 0 else 0

        color = 'green'
        if percentage > 80:
            color = 'red'
        elif percentage > 60:
            color = 'orange'

        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            obj.current_month_downloads,
            obj.monthly_download_limit if obj.monthly_download_limit > 0 else '∞',
            int(percentage)
        )

    downloads_used_display.short_description = 'Downloads Used'

    def storage_used_display(self, obj):
        """Display storage usage"""
        gb_used = obj.storage_used_bytes / (1024 * 1024 * 1024)
        percentage = (gb_used / obj.storage_limit_gb) * 100 if obj.storage_limit_gb > 0 else 0

        color = 'green'
        if percentage > 80:
            color = 'red'
        elif percentage > 60:
            color = 'orange'

        return format_html(
            '<span style="color: {};">{:.2f}/{} GB ({}%)</span>',
            color,
            gb_used,
            obj.storage_limit_gb if obj.storage_limit_gb > 0 else '∞',
            int(percentage)
        )

    storage_used_display.short_description = 'Storage Used'

    actions = ['reset_usage', 'upgrade_to_premium', 'extend_subscription']

    def reset_usage(self, request, queryset):
        """Reset monthly usage for selected subscriptions"""
        for subscription in queryset:
            subscription.reset_monthly_usage()

        count = queryset.count()
        self.message_user(request, f'Usage reset for {count} subscriptions.')

    reset_usage.short_description = "Reset monthly usage"

    def upgrade_to_premium(self, request, queryset):
        """Upgrade to premium plan"""
        count = queryset.update(
            plan='premium',
            monthly_download_limit=100,
            storage_limit_gb=100,
            max_concurrent_downloads=5,
            streaming_enabled=True,
            sharing_enabled=True,
            api_access_enabled=True,
            priority_support=True
        )
        self.message_user(request, f'{count} subscriptions upgraded to premium.')

    upgrade_to_premium.short_description = "Upgrade to Premium"

    def extend_subscription(self, request, queryset):
        """Extend subscription by 30 days"""
        from django.utils import timezone
        from datetime import timedelta

        for subscription in queryset:
            if subscription.expires_at:
                subscription.expires_at += timedelta(days=30)
            else:
                subscription.expires_at = timezone.now() + timedelta(days=30)
            subscription.save()

        count = queryset.count()
        self.message_user(request, f'{count} subscriptions extended by 30 days.')

    extend_subscription.short_description = "Extend by 30 days"


@admin.register(UserLoginLog)
class UserLoginLogAdmin(admin.ModelAdmin):
    """Admin interface for UserLoginLog model"""

    list_display = [
        'user', 'ip_address', 'success', 'device_type', 'browser',
        'location', 'login_time'
    ]
    list_filter = [
        'success', 'device_type', 'browser', 'login_time'
    ]
    search_fields = [
        'user__email', 'user__username', 'ip_address', 'location'
    ]
    readonly_fields = ['id', 'login_time', 'logout_time']
    ordering = ['-login_time']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def has_add_permission(self, request):
        """Disable adding login logs manually"""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing login logs"""
        return False