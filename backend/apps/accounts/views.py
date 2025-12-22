"""
Views for Accounts app
"""
from rest_framework import status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from .models import User, UserProfile, UserSubscription, UserLoginLog
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordChangeSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,
    ProfileUpdateSerializer, UserLoginLogSerializer, UserStatsSerializer
)
from apps.courses.models import UserCourse
from apps.downloads.models import DownloadJob
import logging

logger = logging.getLogger(__name__)


class UserViewSet(ModelViewSet):
    """ViewSet for User model"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        """Return the current user"""
        return self.request.user

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """Update user profile"""
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        user = request.user
        subscription = getattr(user, 'subscription', None)

        # Get courses and downloads stats
        user_courses = UserCourse.objects.filter(user=user)
        download_jobs = DownloadJob.objects.filter(user=user)

        # Calculate stats
        stats = {
            'total_courses': user_courses.count(),
            'total_downloads': download_jobs.count(),
            'storage_used': getattr(user.profile, 'total_storage_used', 0) / (1024 * 1024 * 1024),  # GB
            'storage_limit': subscription.storage_limit_gb if subscription else 5,
            'downloads_this_month': subscription.current_month_downloads if subscription else 0,
            'download_limit': subscription.monthly_download_limit if subscription else 3,
            'active_downloads': download_jobs.filter(status__in=['pending', 'downloading', 'queued']).count(),
            'completed_downloads': download_jobs.filter(status='completed').count(),
            'failed_downloads': download_jobs.filter(status='failed').count(),
            'avg_download_speed': download_jobs.filter(download_speed_mbps__gt=0).aggregate(
                avg_speed=models.Avg('download_speed_mbps')
            )['avg_speed'] or 0,
            'join_date': user.created_at,
            'subscription_plan': subscription.plan if subscription else 'free',
            'subscription_status': subscription.status if subscription else 'active'
        }

        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def login_history(self, request):
        """Get user login history"""
        logs = UserLoginLog.objects.filter(user=request.user).order_by('-login_time')[:20]
        serializer = UserLoginLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def verify_email(self, request):
        """Send email verification"""
        # TODO: Implement email verification logic
        return Response({'message': 'Verification email sent'})

    @action(detail=False, methods=['post'])
    def upload_avatar(self, request):
        """Upload user avatar"""
        if 'avatar' not in request.FILES:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = request.FILES['avatar']
        user.save()

        return Response({'message': 'Avatar uploaded successfully', 'avatar_url': user.avatar.url})

    @action(detail=False, methods=['delete'])
    def delete_account(self, request):
        """Delete user account"""
        user = request.user

        # Soft delete - deactivate account
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.com"
        user.username = f"deleted_{user.id}"
        user.save()

        # Log the deletion
        logger.info(f"User account deleted: {user.email}")

        return Response({'message': 'Account deleted successfully'})


class RegisterView(generics.CreateAPIView):
    """User registration view"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                user = serializer.save()

                # Generate tokens
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token

                # Log successful registration
                logger.info(f"New user registered: {user.email}")

                return Response({
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(access_token),
                        'refresh': str(refresh)
                    },
                    'message': 'Registration successful'
                }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """User login view"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            user = serializer.validated_data['user']
            remember_me = serializer.validated_data.get('remember_me', False)

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Set token expiration based on remember_me
            if remember_me:
                # 30 days
                refresh.set_exp(lifetime=timezone.timedelta(days=30))
                access_token.set_exp(lifetime=timezone.timedelta(hours=24))

            # Log successful login
            self._log_login_attempt(user, request, success=True)

            # Update last login IP
            user.last_login_ip = self._get_client_ip(request)
            user.save(update_fields=['last_login_ip'])

            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                },
                'message': 'Login successful'
            })

        # Log failed login attempt
        email = request.data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                self._log_login_attempt(user, request, success=False)
            except User.DoesNotExist:
                pass

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _log_login_attempt(self, user, request, success=True):
        """Log login attempt"""
        try:
            UserLoginLog.objects.create(
                user=user,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=success,
                device_type=self._get_device_type(request),
                browser=self._get_browser(request)
            )
        except Exception as e:
            logger.error(f"Error logging login attempt: {e}")

    def _get_device_type(self, request):
        """Get device type from user agent"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'mobile' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent:
            return 'tablet'
        return 'desktop'

    def _get_browser(self, request):
        """Get browser from user agent"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'chrome' in user_agent:
            return 'Chrome'
        elif 'firefox' in user_agent:
            return 'Firefox'
        elif 'safari' in user_agent:
            return 'Safari'
        elif 'edge' in user_agent:
            return 'Edge'
        return 'Unknown'


class LogoutView(APIView):
    """User logout view"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Update logout time in login log
            try:
                login_log = UserLoginLog.objects.filter(
                    user=request.user,
                    logout_time__isnull=True
                ).order_by('-login_time').first()

                if login_log:
                    login_log.logout_time = timezone.now()
                    login_log.save()
            except Exception as e:
                logger.error(f"Error updating logout time: {e}")

            return Response({'message': 'Logout successful'})

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    """Password reset request view"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']

            # TODO: Generate reset token and send email
            # For now, just return success
            return Response({'message': 'Password reset email sent'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Password reset confirmation view"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            # TODO: Validate token and reset password
            return Response({'message': 'Password reset successful'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UdemyAuthView(APIView):
    """Udemy OAuth authentication view"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get Udemy OAuth URL"""
        # TODO: Generate Udemy OAuth URL
        oauth_url = "https://www.udemy.com/oauth2/authorize"
        return Response({'oauth_url': oauth_url})

    def post(self, request):
        """Handle Udemy OAuth callback"""
        code = request.data.get('code')

        if not code:
            return Response({'error': 'Authorization code required'}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Exchange code for tokens and save to user
        return Response({'message': 'Udemy account connected successfully'})


class ConnectedAccountsView(APIView):
    """Connected accounts view"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get connected accounts"""
        user = request.user

        connected_accounts = {
            'udemy': {
                'connected': bool(user.udemy_access_token),
                'user_id': user.udemy_user_id,
                'connected_at': user.created_at,  # TODO: Add proper connected_at field
                'expires_at': user.udemy_token_expires_at
            }
        }

        return Response(connected_accounts)

    def delete(self, request):
        """Disconnect account"""
        account_type = request.data.get('account_type')

        if account_type == 'udemy':
            user = request.user
            user.udemy_access_token = None
            user.udemy_refresh_token = None
            user.udemy_user_id = None
            user.udemy_token_expires_at = None
            user.save()

            return Response({'message': 'Udemy account disconnected'})

        return Response({'error': 'Invalid account type'}, status=status.HTTP_400_BAD_REQUEST)