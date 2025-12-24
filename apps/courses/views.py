"""
API views for course management.
"""

import asyncio
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Course, Chapter, Lecture, UserCourse, LectureSubtitle, LectureAttachment
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, SyncCoursesSerializer,
    SearchCoursesSerializer, CourseContentSerializer, ExportM3USerializer,
    CourseStatsSerializer
)
from apps.core.services.udemy_service import UdemyService, UdemyServiceError
from apps.core.services.utils import Utils

logger = logging.getLogger(__name__)


class CoursePagination(PageNumberPagination):
    """Custom pagination for courses."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Course management viewset."""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CoursePagination

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseListSerializer

    def get_queryset(self):
        """Get courses for the current user."""
        user = self.request.user
        # Only return courses the user is enrolled in
        enrolled_course_ids = UserCourse.objects.filter(user=user).values_list('course_id', flat=True)
        return Course.objects.filter(id__in=enrolled_course_ids).order_by('-updated_at')

    def retrieve(self, request, pk=None):
        """Get detailed course information."""
        try:
            course = self.get_object()
            serializer = self.get_serializer(course)
            return Response(serializer.data)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found or you do not have access'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    async def content(self, request, pk=None):
        """Get course content structure."""
        course = self.get_object()

        # Check if user has access
        if not UserCourse.objects.filter(user=request.user, course=course).exists():
            return Response(
                {'error': 'You do not have access to this course'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CourseContentSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        content_type = serializer.validated_data['content_type']
        force_refresh = serializer.validated_data['force_refresh']

        try:
            # Sync course content if needed or forced
            if force_refresh or not course.chapters.exists():
                await self._sync_course_content(course, content_type)

            # Return course with content
            response_serializer = CourseDetailSerializer(course, context={'request': request})
            return Response(response_serializer.data)

        except Exception as e:
            logger.error(f"Failed to get course content for {course.udemy_id}: {e}")
            return Response(
                {'error': f'Failed to fetch course content: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def export_m3u(self, request, pk=None):
        """Export course content as M3U playlist."""
        course = self.get_object()

        if not UserCourse.objects.filter(user=request.user, course=course).exists():
            return Response(
                {'error': 'You do not have access to this course'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ExportM3USerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        include_attachments = serializer.validated_data['include_attachments']

        try:
            m3u_content = self._generate_m3u_playlist(course, include_attachments)

            response = Response(m3u_content, content_type='audio/x-mpegurl')
            response['Content-Disposition'] = f'attachment; filename="{Utils.sanitize_filename(course.title)}.m3u"'
            return response

        except Exception as e:
            logger.error(f"Failed to export M3U for course {course.udemy_id}: {e}")
            return Response(
                {'error': f'Failed to export M3U: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get course statistics for the user."""
        user = request.user
        user_courses = UserCourse.objects.filter(user=user)

        stats = {
            'total_courses': user_courses.count(),
            'downloaded_courses': user_courses.filter(is_downloaded=True).count(),
            'in_progress_downloads': 0,  # Will be updated from download tasks
            'failed_downloads': 0,  # Will be updated from download tasks
            'total_size': 0,
            'encrypted_videos': sum(
                course.course.encrypted_videos_count for course in user_courses
            )
        }

        # Add download statistics
        from apps.downloads.models import DownloadTask
        download_tasks = DownloadTask.objects.filter(user=user)
        stats['in_progress_downloads'] = download_tasks.filter(status__in=['preparing', 'downloading']).count()
        stats['failed_downloads'] = download_tasks.filter(status='failed').count()
        stats['total_size'] = sum(task.total_size for task in download_tasks)

        serializer = CourseStatsSerializer(stats)
        return Response(serializer.data)

    async def _sync_course_content(self, course: Course, content_type: str = 'all'):
        """Sync course content from Udemy API."""
        user = self.request.user

        if not user.udemy_access_token or not user.is_token_valid:
            raise Exception("Valid Udemy token required")

        udemy_service = UdemyService(user.udemy_access_token, user.udemy_subdomain)
        content_data = await udemy_service.fetch_course_content(course.udemy_id, content_type)

        if not content_data:
            raise Exception("Failed to fetch course content")

        # Update course with new data
        with transaction.atomic():
            course.course_data = content_data
            course.total_lectures = 0
            course.total_chapters = 0
            course.encrypted_videos_count = 0
            course.available_subtitles = {}
            course.last_synced = timezone.now()

            # Clear existing content
            course.chapters.all().delete()

            # Process course structure
            current_chapter = None

            for item in content_data.get('results', []):
                item_class = item.get('_class', '').lower()

                if item_class == 'chapter':
                    current_chapter = Chapter.objects.create(
                        course=course,
                        udemy_id=item['id'],
                        title=item['title'],
                        description=item.get('description', ''),
                        order=course.total_chapters + 1
                    )
                    course.total_chapters += 1

                elif item_class in ['lecture', 'quiz', 'practice'] and current_chapter:
                    lecture = self._create_lecture_from_item(current_chapter, item, course.total_lectures + 1)
                    current_chapter.lecture_count += 1
                    course.total_lectures += 1

                    # Count encrypted videos
                    if lecture.is_encrypted:
                        course.encrypted_videos_count += 1

                    # Collect subtitle languages
                    for subtitle in lecture.subtitles.all():
                        lang = subtitle.language
                        course.available_subtitles[lang] = course.available_subtitles.get(lang, 0) + 1

            # Update chapter lecture counts
            for chapter in course.chapters.all():
                chapter.save()

            course.save()

    def _create_lecture_from_item(self, chapter: Chapter, item: dict, order: int) -> Lecture:
        """Create lecture from Udemy API item."""
        item_class = item.get('_class', '').lower()

        # Determine lecture type
        if item_class == 'quiz':
            lecture_type = 'quiz'
        elif item_class == 'practice':
            lecture_type = 'practice'
        else:
            lecture_type = 'video'  # Default

        lecture = Lecture.objects.create(
            chapter=chapter,
            udemy_id=item['id'],
            title=item['title'],
            description=item.get('description', ''),
            lecture_type=lecture_type,
            order=order,
            asset_data=item.get('asset', {})
        )

        # Process asset data
        asset = item.get('asset', {})
        if asset:
            self._process_lecture_asset(lecture, asset)

        # Process supplementary assets (attachments)
        supplementary_assets = item.get('supplementary_assets', [])
        for attachment_data in supplementary_assets:
            self._create_lecture_attachment(lecture, attachment_data)

        return lecture

    def _process_lecture_asset(self, lecture: Lecture, asset: dict):
        """Process lecture asset data."""
        asset_type = asset.get('asset_type', '').lower()

        if asset_type in ['video', 'videomashup']:
            # Process video asset
            streams = asset.get('streams', {})
            if streams:
                lecture.source_url = self._get_best_stream_url(streams)
                lecture.quality = streams.get('maxQuality', 'Auto')
                lecture.is_encrypted = streams.get('isEncrypted', False)

            # Process captions/subtitles
            captions = asset.get('captions', [])
            for caption in captions:
                LectureSubtitle.objects.create(
                    lecture=lecture,
                    language=caption.get('video_label', ''),
                    language_label=caption.get('video_label', ''),
                    source_url=caption.get('url', ''),
                    is_auto_generated='[Auto]' in caption.get('video_label', '')
                )

        elif asset_type == 'article':
            lecture.lecture_type = 'article'
            lecture.source_url = asset.get('body', '')

        elif asset_type in ['file', 'e-book']:
            lecture.lecture_type = 'file'
            download_urls = asset.get('download_urls', {})
            if download_urls:
                file_url = download_urls.get(asset_type, [{}])[0].get('file', '')
                lecture.source_url = file_url

        elif asset_type == 'presentation':
            lecture.lecture_type = 'file'
            url_set = asset.get('url_set', {})
            if url_set:
                file_url = url_set.get(asset_type, [{}])[0].get('file', '')
                lecture.source_url = file_url

        lecture.save()

    def _get_best_stream_url(self, streams: dict) -> str:
        """Get the best quality stream URL."""
        sources = streams.get('sources', {})
        if not sources:
            return ''

        # Prefer highest quality
        max_quality = streams.get('maxQuality', 'auto')
        if max_quality in sources:
            return sources[max_quality].get('url', '')

        # Fallback to auto or first available
        if 'auto' in sources:
            return sources['auto'].get('url', '')

        # Return first available
        return next(iter(sources.values())).get('url', '')

    def _create_lecture_attachment(self, lecture: Lecture, attachment_data: dict):
        """Create lecture attachment."""
        download_urls = attachment_data.get('download_urls')
        external_url = attachment_data.get('external_url')

        if download_urls:
            attachment_type = 'file'
            source_url = download_urls.get(attachment_data.get('asset_type', ''), [{}])[0].get('file', '')
        elif external_url:
            attachment_type = 'url'
            source_url = external_url
        else:
            attachment_type = 'article'
            source_url = ''

        LectureAttachment.objects.create(
            lecture=lecture,
            title=attachment_data.get('title', ''),
            attachment_type=attachment_type,
            source_url=source_url,
            external_url=external_url or '',
            filename=attachment_data.get('filename', ''),
            file_size=attachment_data.get('file_size', 0),
            content=attachment_data.get('body', '')
        )

    def _generate_m3u_playlist(self, course: Course, include_attachments: bool = True) -> str:
        """Generate M3U playlist content."""
        lines = ['#EXTM3U']
        index = 0

        for chapter in course.chapters.all().order_by('order'):
            for lecture in chapter.lectures.all().order_by('order'):
                index += 1
                lines.append(f'#EXTINF:-1,{index}. {lecture.title}')
                lines.append(lecture.source_url)

                if include_attachments:
                    for attach_index, attachment in enumerate(lecture.attachments.all()):
                        lines.append(f'#EXTINF:-1,{index}.{attach_index + 1} {attachment.title}')
                        lines.append(attachment.source_url or attachment.external_url)

        return '\n'.join(lines)


class SyncCoursesView(APIView):
    """Sync courses from Udemy API."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=SyncCoursesSerializer,
        responses={
            200: OpenApiResponse(description="Courses synced successfully"),
            400: OpenApiResponse(description="Invalid request or authentication"),
        }
    )
    def post(self, request):
        """Sync user's courses from Udemy."""
        serializer = SyncCoursesSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        force_refresh = serializer.validated_data['force_refresh']
        include_subscriber_content = serializer.validated_data['include_subscriber_content']

        if not user.udemy_access_token or not user.is_token_valid:
            return Response(
                {'error': 'Valid Udemy token required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Sync courses from Udemy
            courses_data = asyncio.run(self._fetch_udemy_courses(user, include_subscriber_content))
            synced_courses = self._process_courses_data(user, courses_data)

            return Response({
                'message': f'Successfully synced {len(synced_courses)} courses',
                'courses_count': len(synced_courses),
                'courses': CourseListSerializer(synced_courses, many=True, context={'request': request}).data
            })

        except UdemyServiceError as e:
            logger.error(f"Udemy API error during sync: {e}")
            return Response(
                {'error': f'Failed to sync courses: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error during course sync: {e}")
            return Response(
                {'error': 'Internal server error during sync'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def _fetch_udemy_courses(self, user, include_subscriber_content: bool):
        """Fetch courses from Udemy API."""
        udemy_service = UdemyService(user.udemy_access_token, user.udemy_subdomain)

        return await udemy_service.fetch_courses(
            page_size=100,
            is_subscriber=include_subscriber_content
        )

    def _process_courses_data(self, user, courses_data: dict):
        """Process and save courses data."""
        synced_courses = []

        with transaction.atomic():
            for course_item in courses_data.get('results', []):
                course, created = self._create_or_update_course(course_item)

                # Create or update user-course relationship
                user_course, user_course_created = UserCourse.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={'enrolled_at': timezone.now()}
                )

                # Update last accessed
                user_course.last_accessed = timezone.now()
                user_course.save()

                synced_courses.append(course)

        return synced_courses

    def _create_or_update_course(self, course_data: dict):
        """Create or update course from API data."""
        udemy_id = course_data['id']

        defaults = {
            'title': course_data.get('title', ''),
            'url': course_data.get('url', ''),
            'image_url': course_data.get('image_240x135', ''),
            'description': course_data.get('description', ''),
            'instructor_name': self._get_instructor_name(course_data),
            'language': course_data.get('locale', {}).get('locale', ''),
            'is_enrolled': True,
            'is_subscriber_content': course_data.get('is_subscriber_content', False),
            'updated_at': timezone.now(),
        }

        course, created = Course.objects.update_or_create(
            udemy_id=udemy_id,
            defaults=defaults
        )

        return course, created

    def _get_instructor_name(self, course_data: dict) -> str:
        """Extract instructor name from course data."""
        visible_instructors = course_data.get('visible_instructors', [])
        if visible_instructors:
            return visible_instructors[0].get('display_name', '')
        return ''


class SearchCoursesView(APIView):
    """Search courses on Udemy."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=SearchCoursesSerializer,
        responses={
            200: OpenApiResponse(description="Search results"),
            400: OpenApiResponse(description="Invalid search parameters"),
        }
    )
    def post(self, request):
        """Search courses on Udemy."""
        serializer = SearchCoursesSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        query = serializer.validated_data['query']
        page_size = serializer.validated_data['page_size']
        include_subscriber_content = serializer.validated_data['include_subscriber_content']

        if not user.udemy_access_token or not user.is_token_valid:
            return Response(
                {'error': 'Valid Udemy token required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Search courses on Udemy
            search_results = asyncio.run(
                self._search_udemy_courses(user, query, page_size, include_subscriber_content)
            )

            # Process and return results
            courses = []
            for course_item in search_results.get('results', []):
                course, created = self._create_or_update_course(course_item)
                courses.append(course)

            return Response({
                'count': search_results.get('count', 0),
                'next': search_results.get('next'),
                'previous': search_results.get('previous'),
                'results': CourseListSerializer(courses, many=True, context={'request': request}).data
            })

        except UdemyServiceError as e:
            logger.error(f"Udemy API error during search: {e}")
            return Response(
                {'error': f'Search failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error during course search: {e}")
            return Response(
                {'error': 'Internal server error during search'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def _search_udemy_courses(self, user, query: str, page_size: int, include_subscriber_content: bool):
        """Search courses on Udemy API."""
        udemy_service = UdemyService(user.udemy_access_token, user.udemy_subdomain)

        return await udemy_service.fetch_search_courses(
            keyword=query,
            page_size=page_size,
            is_subscriber=include_subscriber_content
        )

    def _create_or_update_course(self, course_data: dict):
        """Create or update course from search results."""
        # Same logic as in SyncCoursesView
        udemy_id = course_data['id']

        defaults = {
            'title': course_data.get('title', ''),
            'url': course_data.get('url', ''),
            'image_url': course_data.get('image_240x135', ''),
            'description': course_data.get('description', ''),
            'instructor_name': self._get_instructor_name(course_data),
            'language': course_data.get('locale', {}).get('locale', ''),
            'is_enrolled': True,
            'is_subscriber_content': course_data.get('is_subscriber_content', False),
            'updated_at': timezone.now(),
        }

        course, created = Course.objects.update_or_create(
            udemy_id=udemy_id,
            defaults=defaults
        )

        return course, created

    def _get_instructor_name(self, course_data: dict) -> str:
        """Extract instructor name from course data."""
        visible_instructors = course_data.get('visible_instructors', [])
        if visible_instructors:
            return visible_instructors[0].get('display_name', '')
        return ''