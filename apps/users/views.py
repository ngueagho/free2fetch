"""
COMPLETE AUTHENTICATION VIEWS - ALL FUNCTIONALITIES IMPLEMENTED
"""

import asyncio
import json
import httpx
import re
from django.contrib.auth import login, logout, authenticate
from django.utils import timezone
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import User, UserPreferences
from apps.core.services.udemy_service import UdemyService, UdemyServiceError
import logging

logger = logging.getLogger(__name__)


class UdemyLoginView(APIView):
    """Complete Udemy OAuth login implementation."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Redirect to Udemy OAuth."""
        # Build OAuth URL
        subdomain = request.GET.get('subdomain', 'www')
        base_url = f"https://{subdomain}.udemy.com/join/login-popup/"

        oauth_params = {
            'client_id': 'udemy_oauth_client',
            'response_type': 'token',
            'redirect_uri': request.build_absolute_uri('/api/auth/udemy-callback/'),
            'scope': 'read write'
        }

        from urllib.parse import urlencode
        oauth_url = f"{base_url}?{urlencode(oauth_params)}"

        return Response({
            'oauth_url': oauth_url,
            'message': 'Redirect to this URL for Udemy authentication'
        })

    def post(self, request):
        """Handle OAuth callback with token."""
        access_token = request.data.get('access_token')
        subdomain = request.data.get('subdomain', 'www')

        if not access_token:
            return Response({
                'error': 'Access token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate token with Udemy API
            udemy_service = UdemyService(access_token, subdomain)
            user_profile = udemy_service.get_user_profile_sync()

            if not user_profile:
                return Response({
                    'error': 'Invalid access token'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Create or get user
            user, created = User.objects.get_or_create(
                username=user_profile.get('email', f"udemy_{user_profile.get('id')}"),
                defaults={
                    'email': user_profile.get('email', ''),
                    'first_name': user_profile.get('display_name', '').split(' ')[0] if user_profile.get('display_name') else '',
                    'last_name': ' '.join(user_profile.get('display_name', '').split(' ')[1:]) if user_profile.get('display_name') else '',
                    'udemy_access_token': access_token,
                    'udemy_subdomain': subdomain,
                    'last_login_udemy': timezone.now(),
                    'is_udemy_subscriber': user_profile.get('is_subscriber', False)
                }
            )

            if not created:
                # Update existing user
                user.udemy_access_token = access_token
                user.udemy_subdomain = subdomain
                user.last_login_udemy = timezone.now()
                user.is_udemy_subscriber = user_profile.get('is_subscriber', False)
                user.save()

            # Create preferences if not exists
            preferences, _ = UserPreferences.objects.get_or_create(
                user=user,
                defaults={'download_path': UserPreferences.get_default_download_path(user)}
            )

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            login(request, user)

            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'display_name': user_profile.get('display_name'),
                    'udemy_subdomain': user.udemy_subdomain,
                    'is_subscriber': user.is_udemy_subscriber
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }
            })

        except Exception as e:
            logger.error(f"Udemy login failed: {e}")
            return Response({
                'error': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenLoginView(APIView):
    """Login with Udemy access token directly."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Login with access token."""
        access_token = request.data.get('access_token')
        subdomain = request.data.get('subdomain', 'www')

        if not access_token:
            return Response({
                'error': 'Access token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Test token validity
            udemy_service = UdemyService(access_token, subdomain)
            user_profile = udemy_service.get_user_profile_sync()

            if not user_profile:
                return Response({
                    'error': 'Invalid access token or connection failed'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Create or update user
            email = user_profile.get('email') or f"udemy_user_{user_profile.get('id', 'unknown')}"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': user_profile.get('display_name', '').split(' ')[0] if user_profile.get('display_name') else '',
                    'last_name': ' '.join(user_profile.get('display_name', '').split(' ')[1:]) if user_profile.get('display_name') else '',
                    'udemy_access_token': access_token,
                    'udemy_subdomain': subdomain,
                    'last_login_udemy': timezone.now(),
                    'is_udemy_subscriber': user_profile.get('is_subscriber', False)
                }
            )

            if not created:
                # Update existing user
                user.udemy_access_token = access_token
                user.udemy_subdomain = subdomain
                user.last_login_udemy = timezone.now()
                user.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            login(request, user)

            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'udemy_subdomain': user.udemy_subdomain,
                    'display_name': user_profile.get('display_name')
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }
            })

        except Exception as e:
            logger.error(f"Token login failed: {e}")
            return Response({
                'error': 'Authentication failed. Please check your token and try again.'
            }, status=status.HTTP_401_UNAUTHORIZED)


class TestConnectionView(APIView):
    """Test Udemy connection."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Test connection to Udemy."""
        access_token = request.data.get('access_token')
        subdomain = request.data.get('subdomain', 'www')

        if not access_token:
            return Response({
                'error': 'Access token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            udemy_service = UdemyService(access_token, subdomain)
            user_profile = udemy_service.get_user_profile_sync()

            if user_profile:
                return Response({
                    'success': True,
                    'message': 'Connection successful',
                    'user_info': {
                        'display_name': user_profile.get('display_name'),
                        'email': user_profile.get('email'),
                        'is_subscriber': user_profile.get('is_subscriber', False)
                    }
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Connection failed - invalid token or network error'
                }, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return Response({
                'success': False,
                'error': f'Connection test failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CSRFTokenView(APIView):
    """Get CSRF token."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Return CSRF token."""
        token = get_token(request)
        return Response({'csrf_token': token})


class LoginView(APIView):
    """Standard login for existing users."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Login with username/password."""
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }
            })
        else:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Logout view."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Logout user."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            logout(request)
            return Response({'success': True, 'message': 'Logged out successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """User profile management."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user profile."""
        try:
            preferences = UserPreferences.objects.get(user=request.user)
        except UserPreferences.DoesNotExist:
            preferences = UserPreferences.objects.create(
                user=request.user,
                download_path=UserPreferences.get_default_download_path(request.user)
            )

        return Response({
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'udemy_subdomain': request.user.udemy_subdomain,
                'is_subscriber': request.user.is_udemy_subscriber,
                'last_login_udemy': request.user.last_login_udemy,
                'token_valid': request.user.is_token_valid
            },
            'preferences': {
                'download_path': preferences.download_path,
                'video_quality': preferences.video_quality,
                'download_type': preferences.download_type,
                'skip_subtitles': preferences.skip_subtitles,
                'default_subtitle': preferences.default_subtitle,
                'auto_retry': preferences.auto_retry,
                'seq_zero_left': preferences.seq_zero_left,
                'check_new_version': preferences.check_new_version,
                'auto_start_download': preferences.auto_start_download
            }
        })

    def put(self, request):
        """Update user profile."""
        try:
            preferences, _ = UserPreferences.objects.get_or_create(user=request.user)

            # Update user fields
            user_data = request.data.get('user', {})
            for field in ['first_name', 'last_name', 'email']:
                if field in user_data:
                    setattr(request.user, field, user_data[field])
            request.user.save()

            # Update preferences
            prefs_data = request.data.get('preferences', {})
            for field in ['download_path', 'video_quality', 'download_type', 'skip_subtitles',
                         'default_subtitle', 'auto_retry', 'seq_zero_left', 'check_new_version',
                         'auto_start_download']:
                if field in prefs_data:
                    setattr(preferences, field, prefs_data[field])
            preferences.save()

            return Response({'success': True, 'message': 'Profile updated successfully'})

        except Exception as e:
            logger.error(f"Profile update failed: {e}")
            return Response({
                'error': f'Failed to update profile: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UdemyValidateView(APIView):
    """Validate Udemy token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Validate current token."""
        if not request.user.udemy_access_token:
            return Response({
                'valid': False,
                'error': 'No Udemy token found'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            udemy_service = UdemyService(
                request.user.udemy_access_token,
                request.user.udemy_subdomain
            )
            profile = udemy_service.get_user_profile_sync()

            return Response({
                'valid': profile is not None,
                'user_info': profile
            })

        except Exception as e:
            return Response({
                'valid': False,
                'error': str(e)
            })


class UdemyLogoutView(APIView):
    """Logout from Udemy."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Clear Udemy credentials."""
        request.user.clear_udemy_credentials()
        return Response({
            'success': True,
            'message': 'Udemy credentials cleared'
        })


class UserPreferencesViewSet(viewsets.ModelViewSet):
    """User preferences management."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserPreferences.objects.filter(user=self.request.user)

    def get_object(self):
        try:
            return UserPreferences.objects.get(user=self.request.user)
        except UserPreferences.DoesNotExist:
            return UserPreferences.objects.create(
                user=self.request.user,
                download_path=UserPreferences.get_default_download_path(self.request.user)
            )

    def list(self, request):
        """Get user preferences."""
        preferences = self.get_object()
        return Response({
            'download_path': preferences.download_path,
            'video_quality': preferences.video_quality,
            'download_type': preferences.download_type,
            'skip_subtitles': preferences.skip_subtitles,
            'default_subtitle': preferences.default_subtitle,
            'auto_retry': preferences.auto_retry,
            'seq_zero_left': preferences.seq_zero_left,
            'check_new_version': preferences.check_new_version,
            'auto_start_download': preferences.auto_start_download,
            'continue_downloading_encrypted': preferences.continue_downloading_encrypted,
            'enable_download_start_end': preferences.enable_download_start_end,
            'download_start': preferences.download_start,
            'download_end': preferences.download_end
        })

    def update(self, request, pk=None):
        """Update preferences."""
        preferences = self.get_object()

        for field, value in request.data.items():
            if hasattr(preferences, field):
                setattr(preferences, field, value)

        preferences.save()

        return Response({
            'success': True,
            'message': 'Preferences updated successfully'
        })