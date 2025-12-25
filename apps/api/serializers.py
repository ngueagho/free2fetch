"""
API Serializers for the Udemy Downloader application.
"""

from rest_framework import serializers
from apps.courses.models import Course, Chapter, Lecture
from apps.downloads.models import DownloadTask, DownloadItem
from apps.users.models import UserPreferences


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""

    instructor_name = serializers.CharField(read_only=True)
    total_lectures = serializers.IntegerField(read_only=True)
    total_chapters = serializers.IntegerField(read_only=True)
    has_encrypted_content = serializers.BooleanField(read_only=True)
    available_subtitle_languages = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'udemy_id', 'title', 'url', 'image_url', 'description',
            'instructor_name', 'duration', 'language', 'total_lectures',
            'total_chapters', 'encrypted_videos_count', 'is_enrolled',
            'is_subscriber_content', 'has_encrypted_content',
            'available_subtitle_languages', 'created_at', 'updated_at'
        ]

    def get_available_subtitle_languages(self, obj):
        """Get list of available subtitle languages."""
        return obj.get_subtitle_languages()


class ChapterSerializer(serializers.ModelSerializer):
    """Serializer for Chapter model."""

    class Meta:
        model = Chapter
        fields = [
            'id', 'udemy_id', 'title', 'description', 'order',
            'lecture_count', 'created_at', 'updated_at'
        ]


class LectureSerializer(serializers.ModelSerializer):
    """Serializer for Lecture model."""

    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Lecture
        fields = [
            'id', 'udemy_id', 'title', 'description', 'lecture_type',
            'quality', 'source_url', 'is_encrypted', 'duration',
            'file_size', 'order', 'chapter_title', 'course_title',
            'created_at', 'updated_at'
        ]


class DownloadItemSerializer(serializers.ModelSerializer):
    """Serializer for DownloadItem model."""

    lecture_title = serializers.CharField(source='lecture.title', read_only=True)
    formatted_size = serializers.SerializerMethodField()

    class Meta:
        model = DownloadItem
        fields = [
            'id', 'item_type', 'filename', 'status', 'progress_percentage',
            'file_path', 'file_size', 'formatted_size', 'downloaded_size',
            'quality', 'format', 'download_speed', 'is_encrypted',
            'error_message', 'retry_count', 'lecture_title',
            'created_at', 'started_at', 'completed_at'
        ]

    def get_formatted_size(self, obj):
        """Get human-readable file size."""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class DownloadTaskSerializer(serializers.ModelSerializer):
    """Serializer for DownloadTask model."""

    course_title = serializers.CharField(source='course.title', read_only=True)
    course_image = serializers.CharField(source='course.image_url', read_only=True)
    download_items = DownloadItemSerializer(many=True, read_only=True)
    formatted_speed = serializers.SerializerMethodField()
    formatted_eta = serializers.SerializerMethodField()
    formatted_total_size = serializers.SerializerMethodField()
    formatted_downloaded_size = serializers.SerializerMethodField()

    class Meta:
        model = DownloadTask
        fields = [
            'id', 'course_title', 'course_image', 'selected_subtitle',
            'download_type', 'video_quality', 'enable_range_download',
            'download_start', 'download_end', 'status', 'progress_percentage',
            'total_items', 'downloaded_items', 'failed_items', 'encrypted_items',
            'download_path', 'total_size', 'formatted_total_size',
            'downloaded_size', 'formatted_downloaded_size', 'download_speed',
            'formatted_speed', 'estimated_time_remaining', 'formatted_eta',
            'error_message', 'retry_count', 'max_retries', 'download_items',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'progress_percentage', 'total_items',
            'downloaded_items', 'failed_items', 'encrypted_items',
            'total_size', 'downloaded_size', 'download_speed',
            'estimated_time_remaining', 'error_message', 'retry_count',
            'created_at', 'started_at', 'completed_at'
        ]

    def get_formatted_speed(self, obj):
        """Get formatted download speed."""
        speed = obj.download_speed
        if speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed / (1024 * 1024):.1f} MB/s"
        else:
            return f"{speed / (1024 * 1024 * 1024):.1f} GB/s"

    def get_formatted_eta(self, obj):
        """Get formatted estimated time remaining."""
        if not obj.estimated_time_remaining:
            return "--:--"

        total_seconds = int(obj.estimated_time_remaining.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def get_formatted_total_size(self, obj):
        """Get human-readable total size."""
        return self._format_bytes(obj.total_size)

    def get_formatted_downloaded_size(self, obj):
        """Get human-readable downloaded size."""
        return self._format_bytes(obj.downloaded_size)

    def _format_bytes(self, size):
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class DownloadTaskCreateSerializer(serializers.Serializer):
    """Serializer for creating download tasks."""

    course_id = serializers.IntegerField(required=True)
    selected_subtitle = serializers.CharField(max_length=100, required=False, allow_blank=True)
    download_type = serializers.ChoiceField(
        choices=[(0, 'Both'), (1, 'Only Lectures'), (2, 'Only Attachments')],
        default=0
    )
    video_quality = serializers.ChoiceField(
        choices=[
            ('Auto', 'Auto'), ('144', '144p'), ('240', '240p'),
            ('360', '360p'), ('480', '480p'), ('720', '720p'),
            ('1080', '1080p'), ('Highest', 'Highest'), ('Lowest', 'Lowest')
        ],
        default='Auto'
    )
    enable_range_download = serializers.BooleanField(default=False)
    download_start = serializers.IntegerField(default=1, min_value=1)
    download_end = serializers.IntegerField(default=0, min_value=0)
    download_path = serializers.CharField(max_length=1000, required=False)

    def validate(self, data):
        """Validate download configuration."""
        if data['enable_range_download']:
            if data['download_end'] > 0 and data['download_start'] > data['download_end']:
                raise serializers.ValidationError(
                    "Download start must be less than or equal to download end"
                )
        return data


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for UserPreferences model."""

    class Meta:
        model = UserPreferences
        fields = [
            'check_new_version', 'auto_start_download', 'continue_downloading_encrypted',
            'enable_download_start_end', 'download_start', 'download_end',
            'video_quality', 'download_type', 'skip_subtitles', 'default_subtitle',
            'download_path', 'seq_zero_left', 'auto_retry', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UdemyTokenSerializer(serializers.Serializer):
    """Serializer for Udemy token validation."""

    access_token = serializers.CharField(required=True, min_length=10)
    subdomain = serializers.CharField(required=False, default='www', max_length=100)

    def validate_subdomain(self, value):
        """Validate subdomain format."""
        if not value:
            return 'www'

        # Clean and validate subdomain
        subdomain = value.strip().lower()
        if not subdomain:
            return 'www'

        # Basic validation - alphanumeric and hyphens only
        import re
        if not re.match(r'^[a-z0-9-]+$', subdomain):
            raise serializers.ValidationError("Invalid subdomain format")

        return subdomain