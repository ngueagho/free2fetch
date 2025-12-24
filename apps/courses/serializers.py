"""
Serializers for course-related API endpoints.
"""

from rest_framework import serializers
from .models import Course, Chapter, Lecture, LectureSubtitle, LectureAttachment, UserCourse


class LectureSubtitleSerializer(serializers.ModelSerializer):
    """Serializer for lecture subtitles."""

    class Meta:
        model = LectureSubtitle
        fields = ['language', 'language_label', 'source_url', 'is_auto_generated']


class LectureAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for lecture attachments."""

    class Meta:
        model = LectureAttachment
        fields = [
            'title', 'attachment_type', 'source_url', 'external_url',
            'filename', 'file_size', 'content'
        ]


class LectureSerializer(serializers.ModelSerializer):
    """Serializer for lectures."""

    subtitles = LectureSubtitleSerializer(many=True, read_only=True)
    attachments = LectureAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Lecture
        fields = [
            'id', 'udemy_id', 'title', 'description', 'lecture_type',
            'quality', 'source_url', 'is_encrypted', 'duration',
            'file_size', 'order', 'asset_data', 'subtitles', 'attachments'
        ]


class ChapterSerializer(serializers.ModelSerializer):
    """Serializer for chapters."""

    lectures = LectureSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = [
            'id', 'udemy_id', 'title', 'description', 'order',
            'lecture_count', 'lectures'
        ]


class CourseListSerializer(serializers.ModelSerializer):
    """Serializer for course list view."""

    enrolled_at = serializers.SerializerMethodField()
    is_downloaded = serializers.SerializerMethodField()
    download_path = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'udemy_id', 'title', 'url', 'image_url', 'description',
            'instructor_name', 'duration', 'language', 'total_lectures',
            'total_chapters', 'encrypted_videos_count', 'is_enrolled',
            'is_subscriber_content', 'available_subtitles', 'created_at',
            'updated_at', 'enrolled_at', 'is_downloaded', 'download_path'
        ]

    def get_enrolled_at(self, obj):
        """Get enrollment date for current user."""
        user = self.context['request'].user
        try:
            user_course = UserCourse.objects.get(user=user, course=obj)
            return user_course.enrolled_at
        except UserCourse.DoesNotExist:
            return None

    def get_is_downloaded(self, obj):
        """Check if course is downloaded for current user."""
        user = self.context['request'].user
        try:
            user_course = UserCourse.objects.get(user=user, course=obj)
            return user_course.is_downloaded
        except UserCourse.DoesNotExist:
            return False

    def get_download_path(self, obj):
        """Get download path for current user."""
        user = self.context['request'].user
        try:
            user_course = UserCourse.objects.get(user=user, course=obj)
            return user_course.download_path
        except UserCourse.DoesNotExist:
            return ""


class CourseDetailSerializer(serializers.ModelSerializer):
    """Serializer for course detail view."""

    chapters = ChapterSerializer(many=True, read_only=True)
    enrolled_at = serializers.SerializerMethodField()
    is_downloaded = serializers.SerializerMethodField()
    download_path = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'udemy_id', 'title', 'url', 'image_url', 'description',
            'instructor_name', 'duration', 'language', 'total_lectures',
            'total_chapters', 'encrypted_videos_count', 'is_enrolled',
            'is_subscriber_content', 'available_subtitles', 'course_data',
            'created_at', 'updated_at', 'last_synced', 'chapters',
            'enrolled_at', 'is_downloaded', 'download_path'
        ]

    def get_enrolled_at(self, obj):
        """Get enrollment date for current user."""
        user = self.context['request'].user
        try:
            user_course = UserCourse.objects.get(user=user, course=obj)
            return user_course.enrolled_at
        except UserCourse.DoesNotExist:
            return None

    def get_is_downloaded(self, obj):
        """Check if course is downloaded for current user."""
        user = self.context['request'].user
        try:
            user_course = UserCourse.objects.get(user=user, course=obj)
            return user_course.is_downloaded
        except UserCourse.DoesNotExist:
            return False

    def get_download_path(self, obj):
        """Get download path for current user."""
        user = self.context['request'].user
        try:
            user_course = UserCourse.objects.get(user=user, course=obj)
            return user_course.download_path
        except UserCourse.DoesNotExist:
            return ""


class UserCourseSerializer(serializers.ModelSerializer):
    """Serializer for user-course relationship."""

    course = CourseListSerializer(read_only=True)

    class Meta:
        model = UserCourse
        fields = [
            'course', 'enrolled_at', 'last_accessed', 'is_completed',
            'completion_percentage', 'is_downloaded', 'download_path'
        ]


class SyncCoursesSerializer(serializers.Serializer):
    """Serializer for course sync request."""

    force_refresh = serializers.BooleanField(default=False)
    include_subscriber_content = serializers.BooleanField(default=None)

    def validate_include_subscriber_content(self, value):
        """Auto-detect subscriber status if not specified."""
        if value is None:
            user = self.context['request'].user
            return user.is_udemy_subscriber
        return value


class SearchCoursesSerializer(serializers.Serializer):
    """Serializer for course search request."""

    query = serializers.CharField(required=True, min_length=1)
    page_size = serializers.IntegerField(default=25, min_value=1, max_value=100)
    include_subscriber_content = serializers.BooleanField(default=None)

    def validate_include_subscriber_content(self, value):
        """Auto-detect subscriber status if not specified."""
        if value is None:
            user = self.context['request'].user
            return user.is_udemy_subscriber
        return value


class CourseContentSerializer(serializers.Serializer):
    """Serializer for course content request."""

    content_type = serializers.ChoiceField(
        choices=['all', 'lectures', 'attachments', 'less'],
        default='all'
    )

    force_refresh = serializers.BooleanField(default=False)


class ExportM3USerializer(serializers.Serializer):
    """Serializer for M3U export request."""

    course_id = serializers.IntegerField()
    include_attachments = serializers.BooleanField(default=True)

    def validate_course_id(self, value):
        """Validate course exists and user has access."""
        user = self.context['request'].user
        try:
            course = Course.objects.get(udemy_id=value)
            # Check if user has access to this course
            if not UserCourse.objects.filter(user=user, course=course).exists():
                raise serializers.ValidationError("You don't have access to this course.")
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found.")


class CourseStatsSerializer(serializers.Serializer):
    """Serializer for course statistics."""

    total_courses = serializers.IntegerField()
    downloaded_courses = serializers.IntegerField()
    in_progress_downloads = serializers.IntegerField()
    failed_downloads = serializers.IntegerField()
    total_size = serializers.IntegerField()
    encrypted_videos = serializers.IntegerField()