"""
API Views for the Udemy Downloader application.
"""

import asyncio
import platform
import sys
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from apps.courses.models import Course, UserCourse
from apps.downloads.models import DownloadTask, DownloadItem
from apps.users.models import UserPreferences
from apps.core.services.udemy_service import UdemyService, UdemyServiceError
from apps.downloads.tasks import download_course_task

from .serializers import (
    CourseSerializer, DownloadTaskSerializer, UserPreferencesSerializer,
    DownloadTaskCreateSerializer, UdemyTokenSerializer
)

User = get_user_model()


class UdemyAuthViewSet(viewsets.ViewSet):
    """Udemy authentication endpoints."""

    @action(detail=False, methods=['post'])
    def validate_token(self, request):
        """Validate Udemy access token."""
        serializer = UdemyTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        access_token = serializer.validated_data['access_token']
        subdomain = serializer.validated_data.get('subdomain', 'www')

        try:
            # Test token by fetching user profile
            udemy_service = UdemyService(access_token, subdomain)

            # Use sync wrapper
            user_profile = udemy_service.get_user_profile_sync()
            if not user_profile:
                return Response(
                    {'error': 'Invalid access token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Update user with Udemy info
            if request.user.is_authenticated:
                user = request.user
                user.udemy_access_token = access_token
                user.udemy_subdomain = subdomain
                user.last_login_udemy = timezone.now()
                user.save()

            return Response({
                'success': True,
                'user_profile': user_profile,
                'subdomain': subdomain
            })

        except UdemyServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {'error': 'Authentication failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CourseViewSet(viewsets.ViewSet):
    """Course management API endpoints."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List user courses."""
        try:
            user_courses = UserCourse.objects.filter(
                user=request.user
            ).select_related('course').order_by('-last_accessed')

            serializer = CourseSerializer(
                [uc.course for uc in user_courses],
                many=True,
                context={'user': request.user}
            )

            return Response({
                'courses': serializer.data,
                'count': user_courses.count()
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def sync_from_udemy(self, request):
        """Sync courses from Udemy API."""
        if not request.user.udemy_access_token:
            return Response(
                {'error': 'No Udemy access token configured'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            udemy_service = UdemyService(
                request.user.udemy_access_token,
                request.user.udemy_subdomain
            )

            # Fetch courses asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                courses_data = loop.run_until_complete(
                    udemy_service.fetch_courses(
                        page_size=100,
                        is_subscriber=request.user.is_udemy_subscriber
                    )
                )
            finally:
                loop.close()

            # Update database
            synced_count = 0
            with transaction.atomic():
                for course_data in courses_data.get('results', []):
                    course, created = Course.objects.get_or_create(
                        udemy_id=course_data['id'],
                        defaults={
                            'title': course_data.get('title', ''),
                            'url': course_data.get('url', ''),
                            'image_url': course_data.get('image_240x135', ''),
                            'instructor_name': course_data.get('visible_instructors', [{}])[0].get('display_name', ''),
                            'is_enrolled': True,
                            'course_data': course_data
                        }
                    )

                    # Create/update user course relationship
                    user_course, _ = UserCourse.objects.get_or_create(
                        user=request.user,
                        course=course,
                        defaults={
                            'completion_percentage': course_data.get('completion_ratio', 0) * 100
                        }
                    )

                    if created:
                        synced_count += 1

            return Response({
                'success': True,
                'synced_courses': synced_count,
                'total_courses': courses_data.get('count', 0)
            })

        except UdemyServiceError as e:
            return Response(
                {'error': f'Udemy API error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def curriculum(self, request, pk=None):
        """Get course curriculum."""
        try:
            course = Course.objects.get(udemy_id=pk)
            user_course = UserCourse.objects.filter(
                user=request.user,
                course=course
            ).first()

            if not user_course:
                return Response(
                    {'error': 'Course not found or not enrolled'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Fetch curriculum from Udemy
            udemy_service = UdemyService(
                request.user.udemy_access_token,
                request.user.udemy_subdomain
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                curriculum = loop.run_until_complete(
                    udemy_service.fetch_course_full_curriculum(course.udemy_id)
                )
            finally:
                loop.close()

            return Response({
                'course': CourseSerializer(course).data,
                'curriculum': curriculum
            })

        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DownloadTaskViewSet(viewsets.ViewSet):
    """Download management API endpoints."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List user's download tasks."""
        try:
            tasks = DownloadTask.objects.filter(
                user=request.user
            ).select_related('course').order_by('-created_at')

            # Filter by status if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                tasks = tasks.filter(status=status_filter)

            serializer = DownloadTaskSerializer(tasks, many=True)
            return Response({
                'downloads': serializer.data,
                'count': tasks.count()
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """Create new download task."""
        serializer = DownloadTaskCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Get course
                course_id = serializer.validated_data['course_id']
                course = Course.objects.get(udemy_id=course_id)

                # Check if user has access to this course
                if not UserCourse.objects.filter(user=request.user, course=course).exists():
                    return Response(
                        {'error': 'You are not enrolled in this course'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Check for existing active download
                existing = DownloadTask.objects.filter(
                    user=request.user,
                    course=course,
                    status__in=['pending', 'preparing', 'downloading']
                ).first()

                if existing:
                    return Response(
                        {'error': 'Download already in progress for this course'},
                        status=status.HTTP_409_CONFLICT
                    )

                # Create download task
                download_task = DownloadTask.objects.create(
                    user=request.user,
                    course=course,
                    selected_subtitle=serializer.validated_data.get('selected_subtitle', ''),
                    download_type=serializer.validated_data.get('download_type', 0),
                    video_quality=serializer.validated_data.get('video_quality', 'Auto'),
                    enable_range_download=serializer.validated_data.get('enable_range_download', False),
                    download_start=serializer.validated_data.get('download_start', 1),
                    download_end=serializer.validated_data.get('download_end', 0),
                    download_path=serializer.validated_data.get('download_path', '/tmp/udeler')
                )

                # Start download task asynchronously
                download_course_task.delay(str(download_task.id), request.user.id)

                return Response(
                    DownloadTaskSerializer(download_task).data,
                    status=status.HTTP_201_CREATED
                )

        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause download task."""
        try:
            task = DownloadTask.objects.get(id=pk, user=request.user)

            if task.status != 'downloading':
                return Response(
                    {'error': 'Can only pause downloading tasks'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            task.status = 'paused'
            task.save()

            # TODO: Send pause signal to Celery task

            return Response(DownloadTaskSerializer(task).data)
        except DownloadTask.DoesNotExist:
            return Response(
                {'error': 'Download task not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume paused download task."""
        try:
            task = DownloadTask.objects.get(id=pk, user=request.user)

            if task.status != 'paused':
                return Response(
                    {'error': 'Can only resume paused tasks'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Restart download task
            download_course_task.delay(str(task.id), request.user.id)

            return Response(DownloadTaskSerializer(task).data)
        except DownloadTask.DoesNotExist:
            return Response(
                {'error': 'Download task not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk=None):
        """Cancel download task."""
        try:
            task = DownloadTask.objects.get(id=pk, user=request.user)

            if task.status not in ['pending', 'preparing', 'downloading', 'paused']:
                return Response(
                    {'error': 'Cannot cancel completed or failed tasks'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            task.status = 'cancelled'
            task.save()

            # TODO: Send cancel signal to Celery task

            return Response({'success': True})
        except DownloadTask.DoesNotExist:
            return Response(
                {'error': 'Download task not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SettingsViewSet(viewsets.ViewSet):
    """User settings management API endpoints."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get user settings."""
        try:
            preferences, created = UserPreferences.objects.get_or_create(
                user=request.user,
                defaults={
                    'download_path': UserPreferences.get_default_download_path(request.user)
                }
            )

            serializer = UserPreferencesSerializer(preferences)
            return Response({
                'settings': serializer.data,
                'is_new': created
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['put'])
    def update_preferences(self, request):
        """Update user preferences."""
        try:
            preferences, _ = UserPreferences.objects.get_or_create(
                user=request.user,
                defaults={
                    'download_path': UserPreferences.get_default_download_path(request.user)
                }
            )

            serializer = UserPreferencesSerializer(
                preferences,
                data=request.data,
                partial=True
            )

            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'settings': serializer.data
                })
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def reset_to_defaults(self, request):
        """Reset settings to default values."""
        try:
            preferences, _ = UserPreferences.objects.get_or_create(user=request.user)

            # Reset to defaults
            preferences.check_new_version = True
            preferences.auto_start_download = False
            preferences.continue_downloading_encrypted = False
            preferences.video_quality = 'Auto'
            preferences.download_type = 0
            preferences.skip_subtitles = False
            preferences.seq_zero_left = False
            preferences.auto_retry = False
            preferences.download_path = UserPreferences.get_default_download_path(request.user)
            preferences.save()

            serializer = UserPreferencesSerializer(preferences)
            return Response({
                'success': True,
                'settings': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemInfoView(APIView):
    """System information endpoint."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Get system information."""
        try:
            return Response({
                'python_version': sys.version,
                'platform': platform.platform(),
                'architecture': platform.architecture(),
                'processor': platform.processor(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'django_version': getattr(settings, 'DJANGO_VERSION', '4.2+'),
                'app_version': getattr(settings, 'APP_VERSION', '1.0.0'),
                'debug': settings.DEBUG,
                'timezone': str(settings.TIME_ZONE),
                'language': getattr(settings, 'LANGUAGE_CODE', 'en'),
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to get system info: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )