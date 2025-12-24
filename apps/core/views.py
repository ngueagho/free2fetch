"""
Core application views.
"""

import json
import logging
from typing import Dict, Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils.translation import gettext as _
from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.courses.models import Course, UserCourse
from apps.downloads.models import DownloadTask
from apps.users.models import UserSettings
from .services.udemy_service import UdemyService

logger = logging.getLogger(__name__)
User = get_user_model()


class DashboardView(TemplateView):
    """Main dashboard view."""
    template_name = 'base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user settings if authenticated
        if self.request.user.is_authenticated:
            try:
                user_settings = UserSettings.objects.get(user=self.request.user)
            except UserSettings.DoesNotExist:
                user_settings = UserSettings.objects.create(user=self.request.user)

            context['settings'] = user_settings

            # Get user statistics
            user_courses = UserCourse.objects.filter(user=self.request.user)
            user_downloads = DownloadTask.objects.filter(user=self.request.user)

            context.update({
                'total_courses': user_courses.count(),
                'downloaded_courses': user_courses.filter(is_downloaded=True).count(),
                'active_downloads': user_downloads.filter(
                    status__in=['pending', 'preparing', 'downloading', 'paused']
                ).count(),
            })

        # Application metadata
        context.update({
            'app_version': getattr(settings, 'APP_VERSION', '2.0.0'),
            'translations_json': self.get_translations_json(),
        })

        return context

    def get_translations_json(self) -> str:
        """Get translations for JavaScript."""
        translations = {
            'loading': _('Loading'),
            'error': _('Error'),
            'success': _('Success'),
            'downloading': _('Downloading'),
            'paused': _('Paused'),
            'completed': _('Completed'),
            'failed': _('Failed'),
            'cancelled': _('Cancelled'),
            'download_started': _('Download started'),
            'download_completed': _('Download completed'),
            'download_failed': _('Download failed'),
            'download_paused': _('Download paused'),
            'download_resumed': _('Download resumed'),
            'download_cancelled': _('Download cancelled'),
            'confirm_cancel': _('Are you sure you want to cancel this download?'),
            'confirm_delete': _('Are you sure you want to delete this item?'),
            'connection_lost': _('Connection lost. Attempting to reconnect...'),
            'connection_restored': _('Connection restored'),
            'select_subtitle': _('Select subtitle language'),
            'no_subtitles': _('No subtitles available'),
            'drm_protected': _('This content is DRM protected and cannot be downloaded'),
        }
        return json.dumps(translations)


class LoginPageView(TemplateView):
    """Login page view."""
    template_name = 'auth/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


class RegisterPageView(TemplateView):
    """Registration page view."""
    template_name = 'auth/register.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


class CoursesView(LoginRequiredMixin, TemplateView):
    """Courses section view."""
    template_name = 'partials/courses.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user courses
        user_courses = UserCourse.objects.filter(
            user=self.request.user
        ).select_related('course').order_by('-enrolled_at')

        context['courses'] = [uc.course for uc in user_courses]
        return context


class DownloadsView(LoginRequiredMixin, TemplateView):
    """Downloads section view."""
    template_name = 'partials/downloads.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get active downloads
        downloads = DownloadTask.objects.filter(
            user=self.request.user
        ).select_related('course').order_by('-created_at')

        context.update({
            'downloads': downloads,
            'is_download_section': True,
        })
        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings section view."""
    template_name = 'partials/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            user_settings = UserSettings.objects.get(user=self.request.user)
        except UserSettings.DoesNotExist:
            user_settings = UserSettings.objects.create(user=self.request.user)

        context['settings'] = user_settings
        return context


class AboutView(TemplateView):
    """About section view."""
    template_name = 'partials/about.html'


class LoggerView(LoginRequiredMixin, TemplateView):
    """Logger section view."""
    template_name = 'partials/logger.html'


# HTMX Views

class CourseCardView(LoginRequiredMixin, TemplateView):
    """HTMX view for individual course cards."""
    template_name = 'partials/course_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = kwargs.get('course_id')

        try:
            course = Course.objects.get(udemy_id=course_id)
            user_course = UserCourse.objects.get(
                user=self.request.user,
                course=course
            )
            context.update({
                'course': course,
                'user_course': user_course,
            })
        except (Course.DoesNotExist, UserCourse.DoesNotExist):
            context['course'] = None

        return context


class DownloadCardView(LoginRequiredMixin, TemplateView):
    """HTMX view for individual download cards."""
    template_name = 'partials/course_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        download_id = kwargs.get('download_id')

        try:
            download_task = DownloadTask.objects.get(
                id=download_id,
                user=self.request.user
            )
            context.update({
                'course': download_task.course,
                'download_task': download_task,
                'is_download_section': True,
            })
        except DownloadTask.DoesNotExist:
            context['course'] = None

        return context


class ProgressBarView(LoginRequiredMixin, TemplateView):
    """HTMX view for progress bars."""
    template_name = 'partials/progress_bar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        download_id = kwargs.get('download_id')

        try:
            download_task = DownloadTask.objects.get(
                id=download_id,
                user=self.request.user
            )
            context['download_task'] = download_task
        except DownloadTask.DoesNotExist:
            context['download_task'] = None

        return context


class SubtitleModalView(LoginRequiredMixin, APIView):
    """HTMX view for subtitle selection modal."""
    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, course_id: int) -> Response:
        """Get available subtitle languages for a course."""
        try:
            # Get course
            course = Course.objects.get(udemy_id=course_id)

            # Check if user has access
            UserCourse.objects.get(user=request.user, course=course)

            # Get cached subtitle info or fetch from Udemy
            cache_key = f"course_subtitles_{course_id}"
            subtitle_data = cache.get(cache_key)

            if not subtitle_data:
                # Fetch from Udemy API
                udemy_service = UdemyService(
                    access_token=request.user.udemy_access_token,
                    subdomain=request.user.udemy_subdomain
                )

                course_content = udemy_service.fetch_course_content_sync(course_id)
                if course_content:
                    # Extract available subtitle languages
                    subtitle_languages = set()
                    for lecture in course_content.get('results', []):
                        if lecture.get('asset') and lecture['asset'].get('captions'):
                            for caption in lecture['asset']['captions']:
                                subtitle_languages.add((
                                    caption.get('locale_id', 'en'),
                                    caption.get('title', 'English')
                                ))

                    subtitle_data = {
                        'subtitle_choices': list(subtitle_languages)
                    }
                    cache.set(cache_key, subtitle_data, 3600)  # Cache for 1 hour
                else:
                    subtitle_data = {'subtitle_choices': []}

            return Response(subtitle_data)

        except (Course.DoesNotExist, UserCourse.DoesNotExist):
            return Response(
                {'error': _('Course not found or access denied')},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching subtitles for course {course_id}: {e}")
            return Response(
                {'error': _('Failed to fetch subtitle information')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# API Views for HTMX and AJAX requests

class SystemInfoView(LoginRequiredMixin, APIView):
    """Get system information."""
    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest) -> Response:
        """Get system information."""
        try:
            import psutil
            import os

            # Get memory usage
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            # Get cache size (approximate)
            cache_size = len(str(cache._cache)) if hasattr(cache, '_cache') else 0

            # Get download statistics
            total_downloads = DownloadTask.objects.filter(user=request.user).count()

            info = {
                'platform': f"{psutil.system()} {psutil.release()}",
                'memory_usage': memory_info.rss,
                'cache_size': cache_size * 1024,  # Rough estimate
                'total_downloads': total_downloads,
                'python_version': f"Python {psutil.python_version()}",
                'uptime': psutil.boot_time(),
            }

            return Response(info)

        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return Response(
                {'error': _('Failed to get system information')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogsView(LoginRequiredMixin, APIView):
    """Get application logs."""
    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest) -> Response:
        """Get recent log entries."""
        try:
            # This would typically read from log files or database
            # For now, return mock data
            logs = [
                {
                    'id': 1,
                    'timestamp': '2024-01-01T12:00:00Z',
                    'level': 'info',
                    'logger': 'udemy.service',
                    'message': 'Successfully authenticated with Udemy API',
                },
                {
                    'id': 2,
                    'timestamp': '2024-01-01T12:01:00Z',
                    'level': 'debug',
                    'logger': 'download.engine',
                    'message': 'Starting download for course: Python Masterclass',
                },
                # Add more mock logs as needed
            ]

            return Response({'logs': logs})

        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return Response(
                {'error': _('Failed to get logs')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request: HttpRequest) -> Response:
        """Clear logs."""
        try:
            # Implementation would clear log files/database
            return Response({'success': True})
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return Response(
                {'error': _('Failed to clear logs')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateCheckView(APIView):
    """Check for application updates."""

    def get(self, request: HttpRequest) -> Response:
        """Check for updates."""
        try:
            # Mock update check - in real implementation, check GitHub releases
            current_version = getattr(settings, 'APP_VERSION', '2.0.0')

            # Simulate update check logic
            update_info = {
                'update_available': False,
                'current_version': current_version,
                'latest_version': current_version,
                'download_url': '',
                'release_notes': '',
            }

            return Response(update_info)

        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return Response(
                {'error': _('Failed to check for updates')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )