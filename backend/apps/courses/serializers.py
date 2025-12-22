"""
Serializers for Courses app
"""
from rest_framework import serializers
from django.db.models import Avg, Count
from .models import Course, Curriculum, UserCourse, CourseShare


class CurriculumSerializer(serializers.ModelSerializer):
    """Serializer for Curriculum model"""

    duration_formatted = serializers.ReadOnlyField()

    class Meta:
        model = Curriculum
        fields = [
            'id', 'udemy_item_id', 'title', 'description', 'item_type',
            'section_title', 'order_index', 'section_index', 'duration_seconds',
            'duration_formatted', 'is_free', 'video_url', 'video_quality',
            'is_downloadable', 'download_count', 'created_at'
        ]
        read_only_fields = ['id', 'download_count', 'created_at']


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model"""

    duration_formatted = serializers.ReadOnlyField()
    curriculum_items = CurriculumSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'udemy_course_id', 'title', 'slug', 'description', 'headline',
            'instructor_name', 'level', 'language', 'category', 'subcategory',
            'rating', 'avg_rating', 'num_reviews', 'num_students',
            'duration_seconds', 'duration_formatted', 'num_lectures',
            'has_captions', 'has_coding_exercises', 'has_quizzes',
            'image_url', 'image_file', 'price', 'currency', 'status',
            'last_updated', 'download_count', 'view_count',
            'is_enrolled', 'curriculum_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'download_count', 'view_count', 'created_at',
            'updated_at', 'is_enrolled', 'avg_rating'
        ]

    def get_is_enrolled(self, obj):
        """Check if current user is enrolled"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserCourse.objects.filter(user=request.user, course=obj).exists()
        return False

    def get_avg_rating(self, obj):
        """Get average rating from enrolled users"""
        avg = UserCourse.objects.filter(
            course=obj, user_rating__isnull=False
        ).aggregate(avg_rating=Avg('user_rating'))['avg_rating']
        return round(avg, 1) if avg else obj.rating


class CourseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for course lists"""

    duration_formatted = serializers.ReadOnlyField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'headline', 'instructor_name', 'level',
            'language', 'category', 'rating', 'num_reviews', 'num_students',
            'duration_seconds', 'duration_formatted', 'num_lectures',
            'image_url', 'price', 'currency', 'download_count',
            'is_enrolled', 'created_at'
        ]

    def get_is_enrolled(self, obj):
        """Check if current user is enrolled"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserCourse.objects.filter(user=request.user, course=obj).exists()
        return False


class UserCourseSerializer(serializers.ModelSerializer):
    """Serializer for UserCourse model"""

    course = CourseListSerializer(read_only=True)
    course_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = UserCourse
        fields = [
            'id', 'course', 'course_id', 'enrollment_date', 'progress_percentage',
            'last_accessed', 'completed_lectures', 'user_rating', 'user_review',
            'is_favorite', 'preferred_quality', 'download_subtitles',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Enroll user in course"""
        course_id = validated_data.pop('course_id')
        user = self.context['request'].user

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise serializers.ValidationError('Course not found')

        # Check if already enrolled
        if UserCourse.objects.filter(user=user, course=course).exists():
            raise serializers.ValidationError('Already enrolled in this course')

        user_course = UserCourse.objects.create(
            user=user,
            course=course,
            **validated_data
        )

        return user_course

    def update(self, instance, validated_data):
        """Update user course progress and settings"""
        validated_data.pop('course_id', None)  # Don't allow changing course
        return super().update(instance, validated_data)


class CourseShareSerializer(serializers.ModelSerializer):
    """Serializer for CourseShare model"""

    course = CourseListSerializer(read_only=True)
    shared_by_email = serializers.CharField(source='shared_by.email', read_only=True)
    shared_with_email = serializers.CharField(source='shared_with.email', read_only=True)
    is_valid = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = CourseShare
        fields = [
            'id', 'course', 'shared_by_email', 'shared_with_email', 'share_link',
            'permission_level', 'is_public', 'expires_at', 'max_access_count',
            'current_access_count', 'password_protected', 'is_active',
            'is_valid', 'share_url', 'created_at'
        ]
        read_only_fields = [
            'id', 'share_link', 'current_access_count', 'created_at',
            'is_valid', 'share_url'
        ]

    def get_is_valid(self, obj):
        """Check if share is still valid"""
        return obj.is_valid()

    def get_share_url(self, obj):
        """Generate full share URL"""
        request = self.context.get('request')
        if request:
            base_url = request.build_absolute_uri('/')[:-1]
            return f"{base_url}/share/{obj.share_link}"
        return f"/share/{obj.share_link}"


class CourseStatsSerializer(serializers.Serializer):
    """Serializer for course statistics"""

    total_courses = serializers.IntegerField()
    enrolled_courses = serializers.IntegerField()
    favorite_courses = serializers.IntegerField()
    completed_courses = serializers.IntegerField()
    total_duration_hours = serializers.FloatField()
    avg_progress = serializers.FloatField()
    categories = serializers.DictField()
    languages = serializers.DictField()
    levels = serializers.DictField()


class CourseSearchSerializer(serializers.Serializer):
    """Serializer for course search parameters"""

    query = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False)
    level = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'advanced', 'expert'],
        required=False
    )
    language = serializers.CharField(required=False)
    rating_min = serializers.FloatField(required=False, min_value=0, max_value=5)
    duration_min = serializers.IntegerField(required=False, min_value=0)
    duration_max = serializers.IntegerField(required=False, min_value=0)
    price_min = serializers.FloatField(required=False, min_value=0)
    price_max = serializers.FloatField(required=False, min_value=0)
    has_captions = serializers.BooleanField(required=False)
    has_coding_exercises = serializers.BooleanField(required=False)
    has_quizzes = serializers.BooleanField(required=False)
    instructor = serializers.CharField(required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            'title', 'rating', 'students', 'duration', 'price',
            'created_at', 'updated_at'
        ],
        default='title',
        required=False
    )
    sort_order = serializers.ChoiceField(
        choices=['asc', 'desc'],
        default='asc',
        required=False
    )


class CourseReviewSerializer(serializers.Serializer):
    """Serializer for course reviews"""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(required=False, allow_blank=True)

    def validate_rating(self, value):
        """Validate rating"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5')
        return value


class CourseEnrollmentSerializer(serializers.Serializer):
    """Serializer for course enrollment"""

    course_id = serializers.UUIDField()
    preferred_quality = serializers.ChoiceField(
        choices=['360p', '480p', '720p', '1080p'],
        default='720p'
    )
    download_subtitles = serializers.BooleanField(default=True)

    def validate_course_id(self, value):
        """Validate course exists"""
        try:
            Course.objects.get(id=value, status='active')
        except Course.DoesNotExist:
            raise serializers.ValidationError('Course not found or inactive')
        return value


class PopularCoursesSerializer(serializers.Serializer):
    """Serializer for popular courses data"""

    most_downloaded = CourseListSerializer(many=True)
    highest_rated = CourseListSerializer(many=True)
    recently_added = CourseListSerializer(many=True)
    trending = CourseListSerializer(many=True)