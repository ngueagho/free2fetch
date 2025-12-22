"""
Views for Courses app
"""
from rest_framework import status, permissions, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from django.db.models import Q, Avg, Count, Sum, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from .models import Course, Curriculum, UserCourse, CourseShare
from .serializers import (
    CourseSerializer, CourseListSerializer, CurriculumSerializer,
    UserCourseSerializer, CourseShareSerializer, CourseStatsSerializer,
    CourseSearchSerializer, CourseReviewSerializer, CourseEnrollmentSerializer,
    PopularCoursesSerializer
)
from .filters import CourseFilter
import logging

logger = logging.getLogger(__name__)


class CourseViewSet(ReadOnlyModelViewSet):
    """ViewSet for Course model - Read only"""

    queryset = Course.objects.filter(status='active')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ['title', 'description', 'instructor_name', 'category']
    ordering_fields = ['title', 'rating', 'num_students', 'duration_seconds', 'price', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Prefetch related data for performance
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('curriculum_items')

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Get course details and increment view count"""
        instance = self.get_object()

        # Increment view count
        instance.increment_view_count()

        # Track user activity
        try:
            from apps.analytics.models import UserActivity
            UserActivity.objects.create(
                user=request.user,
                action='course_view',
                description=f'Viewed course: {instance.title}',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={
                    'course_id': str(instance.id),
                    'course_title': instance.title
                }
            )
        except Exception as e:
            logger.error(f"Error tracking course view: {e}")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def curriculum(self, request, pk=None):
        """Get course curriculum"""
        course = self.get_object()
        curriculum = course.curriculum_items.all().order_by('section_index', 'order_index')
        serializer = CurriculumSerializer(curriculum, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """Enroll user in course"""
        course = self.get_object()
        user = request.user

        # Check if already enrolled
        if UserCourse.objects.filter(user=user, course=course).exists():
            return Response(
                {'error': 'Already enrolled in this course'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create enrollment
        user_course_data = {
            'course_id': course.id,
            'preferred_quality': request.data.get('preferred_quality', '720p'),
            'download_subtitles': request.data.get('download_subtitles', True)
        }

        serializer = UserCourseSerializer(
            data=user_course_data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def unenroll(self, request, pk=None):
        """Unenroll user from course"""
        course = self.get_object()
        user = request.user

        try:
            user_course = UserCourse.objects.get(user=user, course=course)
            user_course.delete()
            return Response({'message': 'Successfully unenrolled from course'})
        except UserCourse.DoesNotExist:
            return Response(
                {'error': 'Not enrolled in this course'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Toggle course favorite status"""
        course = self.get_object()
        user = request.user

        try:
            user_course = UserCourse.objects.get(user=user, course=course)
            user_course.is_favorite = not user_course.is_favorite
            user_course.save()

            return Response({
                'is_favorite': user_course.is_favorite,
                'message': 'Favorite status updated'
            })
        except UserCourse.DoesNotExist:
            return Response(
                {'error': 'Not enrolled in this course'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Add/update course review"""
        course = self.get_object()
        user = request.user

        try:
            user_course = UserCourse.objects.get(user=user, course=course)
        except UserCourse.DoesNotExist:
            return Response(
                {'error': 'Must be enrolled to review course'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CourseReviewSerializer(data=request.data)
        if serializer.is_valid():
            user_course.user_rating = serializer.validated_data['rating']
            user_course.user_review = serializer.validated_data.get('review', '')
            user_course.save()

            return Response({
                'rating': user_course.user_rating,
                'review': user_course.user_review,
                'message': 'Review updated successfully'
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular courses"""
        cache_key = 'popular_courses'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        # Most downloaded courses
        most_downloaded = Course.objects.filter(
            status='active'
        ).order_by('-download_count')[:10]

        # Highest rated courses
        highest_rated = Course.objects.filter(
            status='active', rating__gte=4.5
        ).order_by('-rating', '-num_reviews')[:10]

        # Recently added courses
        recently_added = Course.objects.filter(
            status='active'
        ).order_by('-created_at')[:10]

        # Trending courses (high view count in last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        trending = Course.objects.filter(
            status='active',
            updated_at__gte=thirty_days_ago
        ).order_by('-view_count')[:10]

        data = {
            'most_downloaded': CourseListSerializer(most_downloaded, many=True, context={'request': request}).data,
            'highest_rated': CourseListSerializer(highest_rated, many=True, context={'request': request}).data,
            'recently_added': CourseListSerializer(recently_added, many=True, context={'request': request}).data,
            'trending': CourseListSerializer(trending, many=True, context={'request': request}).data,
        }

        # Cache for 1 hour
        cache.set(cache_key, data, 3600)

        return Response(data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get course categories with counts"""
        cache_key = 'course_categories'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        categories = Course.objects.filter(
            status='active'
        ).values('category').annotate(
            count=Count('id')
        ).order_by('category')

        # Cache for 2 hours
        cache.set(cache_key, list(categories), 7200)

        return Response(categories)

    def _get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserCourseViewSet(ModelViewSet):
    """ViewSet for UserCourse model"""

    serializer_class = UserCourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['course__title', 'course__instructor_name']
    ordering_fields = ['enrollment_date', 'progress_percentage', 'last_accessed']
    ordering = ['-enrollment_date']

    def get_queryset(self):
        return UserCourse.objects.filter(
            user=self.request.user
        ).select_related('course')

    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """Get favorite courses"""
        favorites = self.get_queryset().filter(is_favorite=True)
        page = self.paginate_queryset(favorites)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(favorites, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def in_progress(self, request):
        """Get courses in progress"""
        in_progress = self.get_queryset().filter(
            progress_percentage__gt=0,
            progress_percentage__lt=100
        )
        page = self.paginate_queryset(in_progress)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(in_progress, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed courses"""
        completed = self.get_queryset().filter(progress_percentage=100)
        page = self.paginate_queryset(completed)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(completed, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update course progress"""
        user_course = self.get_object()

        completed_lectures = request.data.get('completed_lectures')
        if completed_lectures is not None:
            user_course.completed_lectures = completed_lectures
            user_course.update_progress()
            user_course.last_accessed = timezone.now()
            user_course.save()

            return Response({
                'progress_percentage': user_course.progress_percentage,
                'completed_lectures': user_course.completed_lectures,
                'message': 'Progress updated successfully'
            })

        return Response(
            {'error': 'completed_lectures is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user course statistics"""
        user_courses = self.get_queryset()

        stats = {
            'total_courses': user_courses.count(),
            'enrolled_courses': user_courses.count(),
            'favorite_courses': user_courses.filter(is_favorite=True).count(),
            'completed_courses': user_courses.filter(progress_percentage=100).count(),
            'total_duration_hours': user_courses.aggregate(
                total_duration=Sum('course__duration_seconds')
            )['total_duration'] / 3600 if user_courses.exists() else 0,
            'avg_progress': user_courses.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
        }

        # Add category breakdown
        categories = user_courses.values('course__category').annotate(
            count=Count('id')
        ).order_by('-count')
        stats['categories'] = {item['course__category']: item['count'] for item in categories}

        # Add language breakdown
        languages = user_courses.values('course__language').annotate(
            count=Count('id')
        ).order_by('-count')
        stats['languages'] = {item['course__language']: item['count'] for item in languages}

        # Add level breakdown
        levels = user_courses.values('course__level').annotate(
            count=Count('id')
        ).order_by('-count')
        stats['levels'] = {item['course__level']: item['count'] for item in levels}

        serializer = CourseStatsSerializer(stats)
        return Response(serializer.data)


class CourseShareViewSet(ModelViewSet):
    """ViewSet for CourseShare model"""

    serializer_class = CourseShareSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseShare.objects.filter(shared_by=self.request.user)

    def perform_create(self, serializer):
        """Create course share"""
        serializer.save(shared_by=self.request.user)

    @action(detail=False, methods=['get'])
    def received(self, request):
        """Get shares received by user"""
        received_shares = CourseShare.objects.filter(
            shared_with=request.user,
            is_active=True
        ).select_related('course', 'shared_by')

        page = self.paginate_queryset(received_shares)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(received_shares, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def access(self, request, pk=None):
        """Access a shared course"""
        share = self.get_object()

        if not share.is_valid():
            return Response(
                {'error': 'Share link is no longer valid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check password if required
        if share.password_protected:
            password = request.data.get('password')
            if not password or password != share.access_password:
                return Response(
                    {'error': 'Invalid password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Increment access count
        share.increment_access_count()

        # Return course details
        course_serializer = CourseSerializer(share.course, context={'request': request})
        return Response(course_serializer.data)


class CourseSearchView(APIView):
    """Course search view"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Search courses with filters"""
        serializer = CourseSearchSerializer(data=request.query_params)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = serializer.validated_data
        queryset = Course.objects.filter(status='active')

        # Apply filters
        if filters.get('query'):
            query = filters['query']
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(instructor_name__icontains=query) |
                Q(category__icontains=query)
            )

        if filters.get('category'):
            queryset = queryset.filter(category__iexact=filters['category'])

        if filters.get('level'):
            queryset = queryset.filter(level=filters['level'])

        if filters.get('language'):
            queryset = queryset.filter(language__iexact=filters['language'])

        if filters.get('rating_min'):
            queryset = queryset.filter(rating__gte=filters['rating_min'])

        if filters.get('duration_min'):
            queryset = queryset.filter(duration_seconds__gte=filters['duration_min'])

        if filters.get('duration_max'):
            queryset = queryset.filter(duration_seconds__lte=filters['duration_max'])

        if filters.get('price_min'):
            queryset = queryset.filter(price__gte=filters['price_min'])

        if filters.get('price_max'):
            queryset = queryset.filter(price__lte=filters['price_max'])

        if filters.get('has_captions'):
            queryset = queryset.filter(has_captions=True)

        if filters.get('has_coding_exercises'):
            queryset = queryset.filter(has_coding_exercises=True)

        if filters.get('has_quizzes'):
            queryset = queryset.filter(has_quizzes=True)

        if filters.get('instructor'):
            queryset = queryset.filter(instructor_name__icontains=filters['instructor'])

        # Apply sorting
        sort_by = filters.get('sort_by', 'title')
        sort_order = filters.get('sort_order', 'asc')

        if sort_order == 'desc':
            sort_by = f'-{sort_by}'

        queryset = queryset.order_by(sort_by)

        # Paginate results
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = CourseListSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = CourseListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class PublicShareView(APIView):
    """Public course share access view"""

    permission_classes = [permissions.AllowAny]

    def get(self, request, share_link):
        """Access public course share"""
        try:
            share = CourseShare.objects.get(
                share_link=share_link,
                is_active=True,
                is_public=True
            )
        except CourseShare.DoesNotExist:
            return Response(
                {'error': 'Share not found or not public'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not share.is_valid():
            return Response(
                {'error': 'Share link has expired'},
                status=status.HTTP_410_GONE
            )

        # Increment access count
        share.increment_access_count()

        # Return limited course info for public access
        course_data = {
            'id': share.course.id,
            'title': share.course.title,
            'description': share.course.description,
            'instructor_name': share.course.instructor_name,
            'level': share.course.level,
            'duration_seconds': share.course.duration_seconds,
            'num_lectures': share.course.num_lectures,
            'image_url': share.course.image_url,
            'shared_by': share.shared_by.email,
            'permission_level': share.permission_level,
            'message': 'Login required to access full course content'
        }

        return Response(course_data)