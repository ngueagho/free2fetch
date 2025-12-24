"""
Serializers for user-related API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from .models import User, UserPreferences


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'preferred_language', 'is_udemy_subscriber', 'udemy_subdomain',
            'last_login_udemy', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'last_login_udemy']

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(_("User with this email already exists."))
        return value


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError(_("User account is disabled."))
                data['user'] = user
            else:
                raise serializers.ValidationError(_("Invalid username or password."))
        else:
            raise serializers.ValidationError(_("Must include username and password."))

        return data


class UdemyLoginSerializer(serializers.Serializer):
    """Serializer for Udemy authentication."""

    access_token = serializers.CharField()
    subdomain = serializers.CharField(default='www')
    is_business = serializers.BooleanField(default=False)

    def validate_subdomain(self, value):
        """Validate subdomain format."""
        if not value or not value.strip():
            return 'www'

        # Basic validation for subdomain format
        import re
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$', value.strip()):
            raise serializers.ValidationError(_("Invalid subdomain format."))

        return value.strip().lower()


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences."""

    class Meta:
        model = UserPreferences
        exclude = ['id', 'user']

    def validate_download_path(self, value):
        """Validate download path."""
        import os

        if not value:
            # Use default path
            return UserPreferences.get_default_download_path(self.context['request'].user)

        # Basic path validation
        try:
            expanded_path = os.path.expanduser(value)
            if not os.path.isabs(expanded_path):
                raise serializers.ValidationError(_("Download path must be absolute."))
        except Exception:
            raise serializers.ValidationError(_("Invalid download path."))

        return value

    def validate_download_start(self, value):
        """Validate download start index."""
        if value < 0:
            raise serializers.ValidationError(_("Download start must be 0 or greater."))
        return value

    def validate_download_end(self, value):
        """Validate download end index."""
        if value < 0:
            raise serializers.ValidationError(_("Download end must be 0 or greater."))
        return value

    def validate(self, data):
        """Cross-field validation."""
        download_start = data.get('download_start', 0)
        download_end = data.get('download_end', 0)

        if download_end > 0 and download_start > download_end:
            raise serializers.ValidationError(_("Download start cannot be greater than download end."))

        return data


class UdemyProfileSerializer(serializers.Serializer):
    """Serializer for Udemy profile data."""

    header = serializers.DictField()

    def validate_header(self, value):
        """Validate Udemy profile header data."""
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Invalid profile data format."))

        if not value.get('isLoggedIn'):
            raise serializers.ValidationError(_("User is not logged in to Udemy."))

        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate password change data."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(_("New passwords do not match."))
        return data

    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Invalid old password."))
        return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password', 'confirm_password', 'preferred_language'
        ]

    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("Username already exists."))
        return value

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("Email already exists."))
        return value

    def validate(self, data):
        """Cross-field validation."""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(_("Passwords do not match."))
        return data

    def create(self, validated_data):
        """Create new user."""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        # Create default preferences
        UserPreferences.objects.create(
            user=user,
            download_path=UserPreferences.get_default_download_path(user)
        )

        return user