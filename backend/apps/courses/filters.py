"""
Filters for Courses app
"""
import django_filters
from django.db.models import Q
from .models import Course, UserCourse


class CourseFilter(django_filters.FilterSet):
    """Filter for Course model"""

    # Text search
    search = django_filters.CharFilter(method='filter_search', label='Search')

    # Category and subcategory
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    subcategory = django_filters.CharFilter(field_name='subcategory', lookup_expr='iexact')

    # Level
    level = django_filters.ChoiceFilter(
        field_name='level',
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ]
    )

    # Language
    language = django_filters.CharFilter(field_name='language', lookup_expr='iexact')

    # Rating range
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')

    # Duration range (in seconds)
    duration_min = django_filters.NumberFilter(field_name='duration_seconds', lookup_expr='gte')
    duration_max = django_filters.NumberFilter(field_name='duration_seconds', lookup_expr='lte')

    # Price range
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Boolean features
    has_captions = django_filters.BooleanFilter(field_name='has_captions')
    has_coding_exercises = django_filters.BooleanFilter(field_name='has_coding_exercises')
    has_quizzes = django_filters.BooleanFilter(field_name='has_quizzes')

    # Instructor
    instructor = django_filters.CharFilter(field_name='instructor_name', lookup_expr='icontains')

    # Date ranges
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='last_updated', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='last_updated', lookup_expr='lte')

    # Popularity filters
    min_students = django_filters.NumberFilter(field_name='num_students', lookup_expr='gte')
    min_reviews = django_filters.NumberFilter(field_name='num_reviews', lookup_expr='gte')
    min_downloads = django_filters.NumberFilter(field_name='download_count', lookup_expr='gte')

    # Free courses
    is_free = django_filters.BooleanFilter(method='filter_is_free')

    class Meta:
        model = Course
        fields = {
            'title': ['icontains'],
            'status': ['exact'],
            'currency': ['exact'],
        }

    def filter_search(self, queryset, name, value):
        """Custom search filter"""
        if not value:
            return queryset

        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(headline__icontains=value) |
            Q(instructor_name__icontains=value) |
            Q(category__icontains=value) |
            Q(subcategory__icontains=value)
        )

    def filter_is_free(self, queryset, name, value):
        """Filter for free courses"""
        if value is True:
            return queryset.filter(price=0)
        elif value is False:
            return queryset.filter(price__gt=0)
        return queryset


class UserCourseFilter(django_filters.FilterSet):
    """Filter for UserCourse model"""

    # Progress filters
    progress_min = django_filters.NumberFilter(field_name='progress_percentage', lookup_expr='gte')
    progress_max = django_filters.NumberFilter(field_name='progress_percentage', lookup_expr='lte')

    # Status filters
    is_favorite = django_filters.BooleanFilter(field_name='is_favorite')
    is_completed = django_filters.BooleanFilter(method='filter_is_completed')
    in_progress = django_filters.BooleanFilter(method='filter_in_progress')
    not_started = django_filters.BooleanFilter(method='filter_not_started')

    # Rating filters
    has_rating = django_filters.BooleanFilter(method='filter_has_rating')
    user_rating_min = django_filters.NumberFilter(field_name='user_rating', lookup_expr='gte')
    user_rating_max = django_filters.NumberFilter(field_name='user_rating', lookup_expr='lte')

    # Course attributes
    course_category = django_filters.CharFilter(field_name='course__category', lookup_expr='iexact')
    course_level = django_filters.ChoiceFilter(
        field_name='course__level',
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ]
    )
    course_language = django_filters.CharFilter(field_name='course__language', lookup_expr='iexact')

    # Date filters
    enrolled_after = django_filters.DateTimeFilter(field_name='enrollment_date', lookup_expr='gte')
    enrolled_before = django_filters.DateTimeFilter(field_name='enrollment_date', lookup_expr='lte')
    accessed_after = django_filters.DateTimeFilter(field_name='last_accessed', lookup_expr='gte')
    accessed_before = django_filters.DateTimeFilter(field_name='last_accessed', lookup_expr='lte')

    # Quality preferences
    preferred_quality = django_filters.ChoiceFilter(
        field_name='preferred_quality',
        choices=[
            ('360p', '360p'),
            ('480p', '480p'),
            ('720p', '720p'),
            ('1080p', '1080p'),
        ]
    )

    class Meta:
        model = UserCourse
        fields = {
            'download_subtitles': ['exact'],
        }

    def filter_is_completed(self, queryset, name, value):
        """Filter for completed courses"""
        if value is True:
            return queryset.filter(progress_percentage=100)
        elif value is False:
            return queryset.exclude(progress_percentage=100)
        return queryset

    def filter_in_progress(self, queryset, name, value):
        """Filter for courses in progress"""
        if value is True:
            return queryset.filter(
                progress_percentage__gt=0,
                progress_percentage__lt=100
            )
        elif value is False:
            return queryset.filter(
                Q(progress_percentage=0) | Q(progress_percentage=100)
            )
        return queryset

    def filter_not_started(self, queryset, name, value):
        """Filter for courses not started"""
        if value is True:
            return queryset.filter(progress_percentage=0)
        elif value is False:
            return queryset.filter(progress_percentage__gt=0)
        return queryset

    def filter_has_rating(self, queryset, name, value):
        """Filter for courses with user ratings"""
        if value is True:
            return queryset.filter(user_rating__isnull=False)
        elif value is False:
            return queryset.filter(user_rating__isnull=True)
        return queryset