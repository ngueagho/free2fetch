"""
Serializers for download-related API endpoints.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import DownloadTask, DownloadItem, DownloadHistory, DownloadSession
from apps.courses.models import Course


class DownloadTaskSerializer(serializers.ModelSerializer):
    """Serializer for download tasks."""

    course_title = serializers.CharField(source='course.title', read_only=True)
    course_image = serializers.CharField(source='course.image_url', read_only=True)
    estimated_time_remaining_formatted = serializers.SerializerMethodField()
    download_speed_formatted = serializers.SerializerMethodField()
    total_size_formatted = serializers.SerializerMethodField()
    downloaded_size_formatted = serializers.SerializerMethodField()

    class Meta:
        model = DownloadTask
        fields = [
            'id', 'course', 'course_title', 'course_image', 'status',
            'progress_percentage', 'total_items', 'downloaded_items',
            'failed_items', 'encrypted_items', 'download_path',
            'total_size', 'downloaded_size', 'download_speed',
            'estimated_time_remaining', 'error_message', 'retry_count',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'selected_subtitle', 'download_type', 'video_quality',
            'enable_range_download', 'download_start', 'download_end',
            'estimated_time_remaining_formatted', 'download_speed_formatted',
            'total_size_formatted', 'downloaded_size_formatted'
        ]
        read_only_fields = [
            'id', 'status', 'progress_percentage', 'total_items',
            'downloaded_items', 'failed_items', 'encrypted_items',
            'total_size', 'downloaded_size', 'download_speed',
            'estimated_time_remaining', 'error_message', 'retry_count',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'course_title', 'course_image'
        ]

    def get_estimated_time_remaining_formatted(self, obj):
        """Format estimated time remaining."""
        if obj.estimated_time_remaining:
            from apps.core.services.utils import Utils
            return Utils.format_duration(obj.estimated_time_remaining.total_seconds())
        return ""

    def get_download_speed_formatted(self, obj):
        """Format download speed."""
        from apps.core.services.utils import Utils
        speed_data = Utils.get_download_speed(obj.download_speed)
        return f"{speed_data['value']} {speed_data['unit']}"

    def get_total_size_formatted(self, obj):
        """Format total file size."""
        from apps.core.services.utils import Utils
        return Utils.format_file_size(obj.total_size)

    def get_downloaded_size_formatted(self, obj):
        """Format downloaded size."""
        from apps.core.services.utils import Utils
        return Utils.format_file_size(obj.downloaded_size)


class DownloadItemSerializer(serializers.ModelSerializer):
    """Serializer for download items."""

    file_size_formatted = serializers.SerializerMethodField()
    downloaded_size_formatted = serializers.SerializerMethodField()
    download_speed_formatted = serializers.SerializerMethodField()

    class Meta:
        model = DownloadItem
        fields = [
            'id', 'item_type', 'filename', 'source_url', 'status',
            'progress_percentage', 'file_path', 'file_size', 'downloaded_size',
            'quality', 'format', 'download_speed', 'is_encrypted',
            'error_message', 'retry_count', 'created_at', 'updated_at',
            'started_at', 'completed_at', 'file_size_formatted',
            'downloaded_size_formatted', 'download_speed_formatted'
        ]
        read_only_fields = [
            'id', 'status', 'progress_percentage', 'downloaded_size',
            'download_speed', 'error_message', 'retry_count',
            'created_at', 'updated_at', 'started_at', 'completed_at'
        ]

    def get_file_size_formatted(self, obj):
        """Format file size."""
        from apps.core.services.utils import Utils
        return Utils.format_file_size(obj.file_size)

    def get_downloaded_size_formatted(self, obj):
        """Format downloaded size."""
        from apps.core.services.utils import Utils
        return Utils.format_file_size(obj.downloaded_size)

    def get_download_speed_formatted(self, obj):
        """Format download speed."""
        from apps.core.services.utils import Utils
        speed_data = Utils.get_download_speed(obj.download_speed)
        return f"{speed_data['value']} {speed_data['unit']}"


class DownloadHistorySerializer(serializers.ModelSerializer):
    """Serializer for download history."""

    course_title = serializers.CharField(source='course.title', read_only=True)
    course_image = serializers.CharField(source='course.image_url', read_only=True)
    total_size_formatted = serializers.SerializerMethodField()
    completion_date_formatted = serializers.SerializerMethodField()

    class Meta:
        model = DownloadHistory
        fields = [
            'id', 'course', 'course_title', 'course_image', 'is_completed',
            'completion_date', 'download_path', 'encrypted_videos_count',
            'total_size', 'selected_subtitle', 'video_quality', 'download_type',
            'created_at', 'updated_at', 'total_size_formatted',
            'completion_date_formatted'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'course_title', 'course_image'
        ]

    def get_total_size_formatted(self, obj):
        """Format total size."""
        from apps.core.services.utils import Utils
        return Utils.format_file_size(obj.total_size)

    def get_completion_date_formatted(self, obj):
        """Format completion date."""
        if obj.completion_date:
            return obj.completion_date.strftime('%Y-%m-%d %H:%M:%S')
        return ""


class StartDownloadSerializer(serializers.Serializer):
    """Serializer for starting a download."""

    course_id = serializers.IntegerField()
    selected_subtitle = serializers.CharField(required=False, default="")
    download_type = serializers.ChoiceField(
        choices=[(0, 'Both'), (1, 'Lectures Only'), (2, 'Attachments Only')],
        default=0
    )
    video_quality = serializers.CharField(default='Auto')
    enable_range_download = serializers.BooleanField(default=False)
    download_start = serializers.IntegerField(default=1, min_value=1)
    download_end = serializers.IntegerField(default=0, min_value=0)

    def validate_course_id(self, value):
        """Validate course exists and user has access."""
        user = self.context['request'].user

        try:
            course = Course.objects.get(udemy_id=value)
            # Check user access
            from apps.courses.models import UserCourse
            if not UserCourse.objects.filter(user=user, course=course).exists():
                raise serializers.ValidationError(_("You don't have access to this course."))
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError(_("Course not found."))

    def validate(self, data):
        """Cross-field validation."""
        if data['enable_range_download']:
            start = data['download_start']
            end = data['download_end']

            if end > 0 and start > end:
                raise serializers.ValidationError(
                    _("Download start cannot be greater than download end.")
                )

        return data


class BatchStartDownloadSerializer(serializers.Serializer):
    """Serializer for batch download start."""

    course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=50
    )
    download_settings = StartDownloadSerializer(required=False)

    def validate_course_ids(self, value):
        """Validate all courses exist and user has access."""
        user = self.context['request'].user
        accessible_courses = []

        for course_id in value:
            try:
                course = Course.objects.get(udemy_id=course_id)
                from apps.courses.models import UserCourse
                if UserCourse.objects.filter(user=user, course=course).exists():
                    accessible_courses.append(course_id)
                else:
                    raise serializers.ValidationError(
                        _("You don't have access to course {}.").format(course_id)
                    )
            except Course.DoesNotExist:
                raise serializers.ValidationError(
                    _("Course {} not found.").format(course_id)
                )

        return accessible_courses


class DownloadStatsSerializer(serializers.Serializer):
    """Serializer for download statistics."""

    total_downloads = serializers.IntegerField()
    active_downloads = serializers.IntegerField()
    completed_downloads = serializers.IntegerField()
    failed_downloads = serializers.IntegerField()
    total_size = serializers.IntegerField()
    downloaded_size = serializers.IntegerField()
    average_speed = serializers.FloatField()
    estimated_completion_time = serializers.CharField()


class DownloadProgressSerializer(serializers.Serializer):
    """Serializer for download progress updates."""

    download_id = serializers.UUIDField()
    status = serializers.CharField()
    progress_percentage = serializers.FloatField()
    download_speed = serializers.FloatField()
    estimated_time_remaining = serializers.DurationField()
    current_item = serializers.CharField()
    error_message = serializers.CharField(required=False)


class SubtitleChoiceSerializer(serializers.Serializer):
    """Serializer for subtitle selection."""

    available_subtitles = serializers.DictField()
    total_lectures = serializers.IntegerField()
    default_subtitle = serializers.CharField(required=False)

    def to_representation(self, instance):
        """Format subtitle choices for frontend."""
        data = super().to_representation(instance)

        # Format subtitle choices
        subtitle_choices = []
        available_subs = data.get('available_subtitles', {})
        total_lectures = data.get('total_lectures', 0)

        for language, count in available_subs.items():
            # Clean language name (remove [Auto] markers)
            clean_language = language.replace('[Auto]', '').strip()
            count = min(total_lectures, count)

            subtitle_choices.append({
                'name': f"<b>{clean_language}</b> <i>{count} Lectures</i>",
                'value': language,
                'language': clean_language,
                'count': count
            })

        # Sort by language name
        subtitle_choices.sort(key=lambda x: x['language'])

        # Add "No subtitles" option at the beginning
        subtitle_choices.insert(0, {
            'name': 'No subtitles',
            'value': '',
            'language': '',
            'count': 0
        })

        data['subtitle_choices'] = subtitle_choices
        return data