"""
API views for download management.
"""

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import DownloadTask, DownloadItem, DownloadHistory, DownloadSession
from .serializers import (
    DownloadTaskSerializer, DownloadItemSerializer, DownloadHistorySerializer,
    StartDownloadSerializer, BatchStartDownloadSerializer, DownloadStatsSerializer,
    SubtitleChoiceSerializer
)
from .tasks import download_course_task
from apps.courses.models import Course, UserCourse
from apps.core.services.utils import Utils

logger = logging.getLogger(__name__)


class DownloadPagination(PageNumberPagination):
    """Custom pagination for downloads."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DownloadTaskViewSet(viewsets.ModelViewSet):
    """Download task management viewset."""

    serializer_class = DownloadTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DownloadPagination

    def get_queryset(self):
        """Get download tasks for the current user."""
        return DownloadTask.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """Create new download task (use StartDownloadView instead)."""
        return Response(
            {'error': 'Use /api/downloads/start/ endpoint to create downloads'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a download task."""
        download_task = self.get_object()

        if download_task.status not in ['downloading']:
            return Response(
                {'error': 'Download cannot be paused in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        download_task.status = 'paused'
        download_task.save()

        # TODO: Send signal to celery worker to pause
        self._send_task_control_signal(download_task, 'pause')

        return Response({'message': 'Download paused successfully'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused download task."""
        download_task = self.get_object()

        if download_task.status not in ['paused']:
            return Response(
                {'error': 'Download cannot be resumed in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        download_task.status = 'downloading'
        download_task.save()

        # TODO: Send signal to celery worker to resume
        self._send_task_control_signal(download_task, 'resume')

        return Response({'message': 'Download resumed successfully'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a download task."""
        download_task = self.get_object()

        if download_task.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Download cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        download_task.status = 'cancelled'
        download_task.save()

        # Cancel celery task if running
        if download_task.celery_task_id:
            from celery import current_app
            current_app.control.revoke(download_task.celery_task_id, terminate=True)

        return Response({'message': 'Download cancelled successfully'})

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed download task."""
        download_task = self.get_object()

        if download_task.status not in ['failed']:
            return Response(
                {'error': 'Only failed downloads can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if download_task.retry_count >= download_task.max_retries:
            return Response(
                {'error': 'Maximum retry attempts exceeded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset task status
        download_task.status = 'pending'
        download_task.retry_count += 1
        download_task.error_message = ''
        download_task.save()

        # Restart download
        download_course_task.delay(str(download_task.id), request.user.id)

        return Response({'message': 'Download retry initiated'})

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """Get download items for a task."""
        download_task = self.get_object()
        items = download_task.download_items.all().order_by('created_at')

        serializer = DownloadItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active downloads."""
        active_downloads = self.get_queryset().filter(
            status__in=['pending', 'preparing', 'downloading', 'paused']
        )

        serializer = self.get_serializer(active_downloads, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def cancel_all(self, request):
        """Cancel all active downloads."""
        active_downloads = self.get_queryset().filter(
            status__in=['pending', 'preparing', 'downloading', 'paused']
        )

        cancelled_count = 0
        for download_task in active_downloads:
            download_task.status = 'cancelled'
            download_task.save()

            # Cancel celery task if running
            if download_task.celery_task_id:
                from celery import current_app
                current_app.control.revoke(download_task.celery_task_id, terminate=True)

            cancelled_count += 1

        return Response({
            'message': f'Cancelled {cancelled_count} downloads',
            'cancelled_count': cancelled_count
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get download statistics."""
        user_downloads = self.get_queryset()

        stats = {
            'total_downloads': user_downloads.count(),
            'active_downloads': user_downloads.filter(
                status__in=['pending', 'preparing', 'downloading', 'paused']
            ).count(),
            'completed_downloads': user_downloads.filter(status='completed').count(),
            'failed_downloads': user_downloads.filter(status='failed').count(),
            'total_size': sum(task.total_size for task in user_downloads),
            'downloaded_size': sum(task.downloaded_size for task in user_downloads),
            'average_speed': 0,  # Calculate from recent downloads
            'estimated_completion_time': '0s'
        }

        # Calculate average speed from active downloads
        active_downloads = user_downloads.filter(status='downloading')
        if active_downloads.exists():
            total_speed = sum(task.download_speed for task in active_downloads)
            stats['average_speed'] = total_speed / active_downloads.count()

            # Estimate completion time
            remaining_size = sum(
                task.total_size - task.downloaded_size
                for task in active_downloads
                if task.total_size > task.downloaded_size
            )

            if stats['average_speed'] > 0:
                estimated_seconds = remaining_size / stats['average_speed']
                stats['estimated_completion_time'] = Utils.format_duration(estimated_seconds)

        serializer = DownloadStatsSerializer(stats)
        return Response(serializer.data)

    def _send_task_control_signal(self, download_task: DownloadTask, action: str):
        """Send control signal to celery worker."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            group_name = f"download_control_{download_task.id}"

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'download_control',
                    'action': action,
                    'download_id': str(download_task.id),
                    'timestamp': timezone.now().isoformat()
                }
            )

        except Exception as e:
            logger.warning(f"Failed to send task control signal: {e}")


class DownloadHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Download history viewset."""

    serializer_class = DownloadHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DownloadPagination

    def get_queryset(self):
        """Get download history for the current user."""
        return DownloadHistory.objects.filter(user=self.request.user).order_by('-updated_at')

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear download history."""
        deleted_count, _ = self.get_queryset().delete()

        return Response({
            'message': f'Cleared {deleted_count} history entries',
            'deleted_count': deleted_count
        })

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Remove specific history entry."""
        history_item = self.get_object()
        history_item.delete()

        return Response({'message': 'History entry removed'})


class StartDownloadView(APIView):
    """Start a new download."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=StartDownloadSerializer,
        responses={
            200: OpenApiResponse(description="Download started successfully"),
            400: OpenApiResponse(description="Invalid request or course not accessible"),
        }
    )
    def post(self, request):
        """Start downloading a course."""
        serializer = StartDownloadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        course_id = serializer.validated_data['course_id']
        user = request.user

        try:
            # Get course
            course = Course.objects.get(udemy_id=course_id)

            # Check if user has access
            if not UserCourse.objects.filter(user=user, course=course).exists():
                return Response(
                    {'error': 'You do not have access to this course'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if download already exists
            existing_task = DownloadTask.objects.filter(
                user=user,
                course=course,
                status__in=['pending', 'preparing', 'downloading', 'paused']
            ).first()

            if existing_task:
                return Response(
                    {
                        'error': 'Download already in progress for this course',
                        'existing_task_id': str(existing_task.id)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get user preferences for download path
            download_path = user.preferences.download_path
            if not download_path:
                download_path = user.preferences.get_default_download_path(user)

            # Create download task
            with transaction.atomic():
                download_task = DownloadTask.objects.create(
                    user=user,
                    course=course,
                    selected_subtitle=serializer.validated_data.get('selected_subtitle', ''),
                    download_type=serializer.validated_data['download_type'],
                    video_quality=serializer.validated_data['video_quality'],
                    enable_range_download=serializer.validated_data['enable_range_download'],
                    download_start=serializer.validated_data['download_start'],
                    download_end=serializer.validated_data['download_end'],
                    download_path=download_path,
                    status='pending'
                )

                # Start download task
                download_course_task.delay(str(download_task.id), user.id)

                return Response({
                    'message': 'Download started successfully',
                    'download_task': DownloadTaskSerializer(download_task).data
                }, status=status.HTTP_201_CREATED)

        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Failed to start download for course {course_id}: {e}")
            return Response(
                {'error': f'Failed to start download: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchStartDownloadView(APIView):
    """Start multiple downloads in batch."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=BatchStartDownloadSerializer,
        responses={
            200: OpenApiResponse(description="Batch download started successfully"),
            400: OpenApiResponse(description="Invalid request"),
        }
    )
    def post(self, request):
        """Start downloading multiple courses."""
        serializer = BatchStartDownloadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        course_ids = serializer.validated_data['course_ids']
        download_settings = serializer.validated_data.get('download_settings', {})
        user = request.user

        started_downloads = []
        failed_downloads = []

        # Default settings if not provided
        default_settings = {
            'selected_subtitle': '',
            'download_type': 0,
            'video_quality': 'Auto',
            'enable_range_download': False,
            'download_start': 1,
            'download_end': 0
        }
        download_settings = {**default_settings, **download_settings}

        try:
            with transaction.atomic():
                for course_id in course_ids:
                    try:
                        course = Course.objects.get(udemy_id=course_id)

                        # Check if download already exists
                        existing_task = DownloadTask.objects.filter(
                            user=user,
                            course=course,
                            status__in=['pending', 'preparing', 'downloading', 'paused']
                        ).first()

                        if existing_task:
                            failed_downloads.append({
                                'course_id': course_id,
                                'error': 'Download already in progress'
                            })
                            continue

                        # Get user preferences for download path
                        download_path = user.preferences.download_path
                        if not download_path:
                            download_path = user.preferences.get_default_download_path(user)

                        # Create download task
                        download_task = DownloadTask.objects.create(
                            user=user,
                            course=course,
                            selected_subtitle=download_settings['selected_subtitle'],
                            download_type=download_settings['download_type'],
                            video_quality=download_settings['video_quality'],
                            enable_range_download=download_settings['enable_range_download'],
                            download_start=download_settings['download_start'],
                            download_end=download_settings['download_end'],
                            download_path=download_path,
                            status='pending'
                        )

                        # Start download task
                        download_course_task.delay(str(download_task.id), user.id)

                        started_downloads.append({
                            'course_id': course_id,
                            'download_task_id': str(download_task.id)
                        })

                    except Course.DoesNotExist:
                        failed_downloads.append({
                            'course_id': course_id,
                            'error': 'Course not found'
                        })

                    except Exception as e:
                        failed_downloads.append({
                            'course_id': course_id,
                            'error': str(e)
                        })

                return Response({
                    'message': f'Started {len(started_downloads)} downloads',
                    'started_downloads': started_downloads,
                    'failed_downloads': failed_downloads,
                    'total_started': len(started_downloads),
                    'total_failed': len(failed_downloads)
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Batch download failed: {e}")
            return Response(
                {'error': f'Batch download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubtitleSelectionView(APIView):
    """Get available subtitles for a course."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        """Get available subtitles for course selection."""
        try:
            course = Course.objects.get(udemy_id=course_id)
            user = request.user

            # Check if user has access
            if not UserCourse.objects.filter(user=user, course=course).exists():
                return Response(
                    {'error': 'You do not have access to this course'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get available subtitles from course data
            available_subtitles = course.available_subtitles or {}
            total_lectures = course.total_lectures

            # Get user's default subtitle preference
            default_subtitle = user.preferences.default_subtitle

            subtitle_data = {
                'available_subtitles': available_subtitles,
                'total_lectures': total_lectures,
                'default_subtitle': default_subtitle
            }

            serializer = SubtitleChoiceSerializer(subtitle_data)
            return Response(serializer.data)

        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Failed to get subtitles for course {course_id}: {e}")
            return Response(
                {'error': f'Failed to get subtitles: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )