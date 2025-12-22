"""
Serializers for Accounts app
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile, UserSubscription, UserLoginLog


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""

    class Meta:
        model = UserProfile
        fields = [
            'bio', 'birth_date', 'location', 'website', 'public_profile',
            'email_notifications', 'newsletter_subscription', 'total_downloads',
            'total_storage_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_downloads', 'total_storage_used', 'created_at', 'updated_at']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for UserSubscription model"""

    plan_name = serializers.CharField(source='get_plan_display', read_only=True)
    status_name = serializers.CharField(source='get_status_display', read_only=True)
    remaining_downloads = serializers.SerializerMethodField()
    storage_used_gb = serializers.SerializerMethodField()
    can_download = serializers.SerializerMethodField()

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'plan_name', 'status', 'status_name', 'monthly_download_limit',
            'current_month_downloads', 'remaining_downloads', 'storage_limit_gb',
            'storage_used_gb', 'max_concurrent_downloads', 'streaming_enabled',
            'sharing_enabled', 'api_access_enabled', 'priority_support',
            'started_at', 'expires_at', 'can_download'
        ]
        read_only_fields = [
            'id', 'plan_name', 'status_name', 'remaining_downloads', 'storage_used_gb',
            'started_at', 'can_download'
        ]

    def get_remaining_downloads(self, obj):
        return obj.remaining_downloads()

    def get_storage_used_gb(self, obj):
        return round(obj.storage_used_bytes / (1024 * 1024 * 1024), 2)

    def get_can_download(self, obj):
        return obj.can_download()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    profile = UserProfileSerializer(read_only=True)
    subscription = UserSubscriptionSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    has_valid_udemy_token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'avatar', 'phone', 'timezone', 'language', 'is_verified', 'is_premium',
            'has_valid_udemy_token', 'created_at', 'updated_at', 'last_login',
            'profile', 'subscription'
        ]
        read_only_fields = [
            'id', 'is_verified', 'is_premium', 'has_valid_udemy_token',
            'created_at', 'updated_at', 'last_login'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True}
        }

    def get_has_valid_udemy_token(self, obj):
        return obj.has_valid_udemy_token()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    accept_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password', 'first_name',
            'last_name', 'accept_terms'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")

        if not attrs.get('accept_terms'):
            raise serializers.ValidationError("You must accept the terms and conditions")

        # Remove confirm_password and accept_terms as they're not model fields
        attrs.pop('confirm_password')
        attrs.pop('accept_terms')

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        # Create user profile and subscription
        from apps.accounts.pipeline import create_user_profile
        create_user_profile(None, {}, None, user=user, is_new=True)

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                              username=email, password=password)

            if not user:
                raise serializers.ValidationError('Invalid email or password')

            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password')


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""

    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError('User with this email does not exist')
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""

    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs


class UserLoginLogSerializer(serializers.ModelSerializer):
    """Serializer for UserLoginLog model"""

    status = serializers.SerializerMethodField()

    class Meta:
        model = UserLoginLog
        fields = [
            'id', 'ip_address', 'user_agent', 'success', 'status', 'location',
            'device_type', 'browser', 'login_time', 'logout_time'
        ]
        read_only_fields = ['id', 'login_time', 'logout_time']

    def get_status(self, obj):
        return 'Success' if obj.success else 'Failed'


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""

    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'timezone', 'language', 'profile'
        ]

    def update(self, instance, validated_data):
        # Update user fields
        profile_data = validated_data.pop('profile', {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile fields
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""

    total_courses = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    storage_used = serializers.FloatField()
    storage_limit = serializers.FloatField()
    downloads_this_month = serializers.IntegerField()
    download_limit = serializers.IntegerField()
    active_downloads = serializers.IntegerField()
    completed_downloads = serializers.IntegerField()
    failed_downloads = serializers.IntegerField()
    avg_download_speed = serializers.FloatField()
    join_date = serializers.DateTimeField()
    subscription_plan = serializers.CharField()
    subscription_status = serializers.CharField()