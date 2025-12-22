"""
Serializers for Downloads app
"""
from rest_framework import serializers
from django.core.validators import MinValueValidator
from .models import DownloadJob, DownloadItem, DownloadHistory, StorageQuota
from apps.courses.models import Course
from apps.courses.serializers import CourseListSerializer


class DownloadItemSerializer(serializers.ModelSerializer):
    """Serializer for DownloadItem model"""

    size_display = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model = DownloadItem
        fields = [
            'id', 'item_type', 'title', 'filename', 'source_url', 'local_path',
            'file_size_bytes', 'size_display', 'downloaded_bytes', 'file_format',
            'quality', 'status', 'progress_percentage', 'download_speed_kbps',
            'error_message', 'retry_count', 'duration_formatted',
            'created_at', 'started_at', 'completed_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'size_display', 'duration_formatted', 'created_at',
            'started_at', 'completed_at', 'updated_at'
        ]

    def get_duration_formatted(self, obj):
        """Get formatted duration for completion"""
        if obj.started_at and obj.completed_at:
            duration = (obj.completed_at - obj.started_at).total_seconds()
            return f"{duration:.1f}s"
        return None


class DownloadJobSerializer(serializers.ModelSerializer):
    """Serializer for DownloadJob model"""

    course = CourseListSerializer(read_only=True)
    course_id = serializers.UUIDField(write_only=True)
    items = DownloadItemSerializer(many=True, read_only=True)
    progress_display = serializers.ReadOnlyField()
    size_display = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    eta_formatted = serializers.SerializerMethodField()
    speed_formatted = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = DownloadJob
        fields = [
            'id', 'course', 'course_id', 'status', 'priority', 'quality',
            'include_subtitles', 'include_attachments', 'selected_lectures',
            'total_items', 'completed_items', 'failed_items', 'progress_percentage',
            'progress_display', 'total_size_bytes', 'downloaded_size_bytes',
            'size_display', 'storage_path', 'download_speed_mbps', 'speed_formatted',
            'estimated_time_remaining', 'eta_formatted', 'duration_formatted',
            'error_message', 'retry_count', 'max_retries', 'can_retry',
            'celery_task_id', 'items', 'created_at', 'started_at',
            'completed_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_items', 'completed_items', 'failed_items',
            'progress_percentage', 'progress_display', 'total_size_bytes',
            'downloaded_size_bytes', 'size_display', 'storage_path',
            'download_speed_mbps', 'speed_formatted', 'estimated_time_remaining',
            'eta_formatted', 'duration_formatted', 'error_message', 'retry_count',
            'can_retry', 'celery_task_id', 'created_at', 'started_at',
            'completed_at', 'updated_at'
        ]

    def get_duration_formatted(self, obj):
        """Get formatted download duration"""
        if obj.started_at and obj.completed_at:
            duration = (obj.completed_at - obj.started_at).total_seconds()
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)

            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return None

    def get_eta_formatted(self, obj):
        """Get formatted ETA"""
        if obj.estimated_time_remaining > 0:
            eta = obj.estimated_time_remaining
            hours = int(eta // 3600)
            minutes = int((eta % 3600) // 60)
            seconds = int(eta % 60)

            if hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return None

    def get_speed_formatted(self, obj):
        """Get formatted download speed"""
        if obj.download_speed_mbps > 0:
            if obj.download_speed_mbps < 1:
                return f"{obj.download_speed_mbps * 1024:.0f} KB/s"
            else:
                return f"{obj.download_speed_mbps:.1f} MB/s"
        return "0 B/s"

    def get_can_retry(self, obj):
        """Check if download can be retried"""
        return obj.can_retry()

    def validate_course_id(self, value):
        """Validate course exists and user can access it"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError('Authentication required')

        try:
            course = Course.objects.get(id=value, status='active')
        except Course.DoesNotExist:
            raise serializers.ValidationError('Course not found or inactive')

        # Check if user is enrolled in the course
        from apps.courses.models import UserCourse
        if not UserCourse.objects.filter(user=request.user, course=course).exists():
            raise serializers.ValidationError('Must be enrolled in course to download')

        return value

    def validate_selected_lectures(self, value):
        """Validate selected lectures exist in the course"""
        if value:
            course_id = self.initial_data.get('course_id')
            if course_id:
                from apps.courses.models import Curriculum
                valid_lectures = Curriculum.objects.filter(
                    course_id=course_id,
                    id__in=value,
                    is_downloadable=True
                ).count()

                if valid_lectures != len(value):
                    raise serializers.ValidationError('Some selected lectures are not valid or downloadable')

        return value

    def validate(self, attrs):
        """Validate download request"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError('Authentication required')

        user = request.user

        # Check user subscription and download limits
        subscription = getattr(user, 'subscription', None)
        if subscription:
            if not subscription.can_download():
                remaining = subscription.remaining_downloads()
                raise serializers.ValidationError(
                    f'Download limit exceeded. {remaining} downloads remaining this month.'
                )

            # Check concurrent download limits
            active_downloads = DownloadJob.objects.filter(
                user=user,
                status__in=['pending', 'queued', 'downloading', 'processing']
            ).count()

            if active_downloads >= subscription.max_concurrent_downloads:
                raise serializers.ValidationError(
                    f'Too many concurrent downloads. Maximum: {subscription.max_concurrent_downloads}'
                )

        return attrs

    def create(self, validated_data):
        """Create download job"""
        course_id = validated_data.pop('course_id')
        user = self.context['request'].user

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise serializers.ValidationError('Course not found')

        download_job = DownloadJob.objects.create(
            user=user,
            course=course,
            **validated_data
        )

        # Queue the download task
        from .tasks import process_download_job
        task = process_download_job.delay(str(download_job.id))
        download_job.celery_task_id = task.id
        download_job.save()

        return download_job


class DownloadHistorySerializer(serializers.ModelSerializer):
    """Serializer for DownloadHistory model"""

    course = CourseListSerializer(read_only=True)
    success_rate = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    size_display = serializers.SerializerMethodField()

    class Meta:
        model = DownloadHistory
        fields = [
            'id', 'course', 'total_files', 'successful_files', 'failed_files',
            'success_rate', 'total_size_mb', 'size_display', 'total_duration_seconds',
            'duration_formatted', 'average_speed_mbps', 'user_rating',
            'user_feedback', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = [
            'id', 'success_rate', 'size_display', 'duration_formatted', 'created_at'
        ]

    def get_duration_formatted(self, obj):
        """Get formatted duration"""
        duration = obj.total_duration_seconds
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_size_display(self, obj):
        """Get formatted file size"""
        mb = obj.total_size_mb
        if mb >= 1024:
            return f"{mb / 1024:.2f} GB"
        else:
            return f"{mb:.2f} MB"


class StorageQuotaSerializer(serializers.ModelSerializer):
    """Serializer for StorageQuota model"""

    usage_percentage = serializers.ReadOnlyField()
    remaining_bytes = serializers.ReadOnlyField()
    quota_exceeded = serializers.ReadOnlyField()
    warning_threshold_reached = serializers.ReadOnlyField()
    quota_display = serializers.SerializerMethodField()
    used_display = serializers.SerializerMethodField()
    remaining_display = serializers.SerializerMethodField()

    class Meta:
        model = StorageQuota
        fields = [
            'id', 'total_quota_bytes', 'quota_display', 'used_quota_bytes',
            'used_display', 'remaining_bytes', 'remaining_display',
            'usage_percentage', 'max_files', 'current_files',
            'warning_threshold_percentage', 'quota_exceeded',
            'warning_threshold_reached', 'warning_sent', 'created_at',
            'updated_at', 'last_cleanup'
        ]
        read_only_fields = [
            'id', 'used_quota_bytes', 'current_files', 'quota_exceeded',
            'warning_sent', 'created_at', 'updated_at', 'last_cleanup'
        ]

    def get_quota_display(self, obj):
        """Get formatted quota size"""
        gb = obj.total_quota_bytes / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"

    def get_used_display(self, obj):
        """Get formatted used size"""
        gb = obj.used_quota_bytes / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"

    def get_remaining_display(self, obj):
        """Get formatted remaining size"""
        gb = obj.remaining_bytes / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"


class DownloadStatsSerializer(serializers.Serializer):
    """Serializer for download statistics"""

    total_downloads = serializers.IntegerField()
    completed_downloads = serializers.IntegerField()
    failed_downloads = serializers.IntegerField()
    active_downloads = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_size_downloaded = serializers.FloatField()  # GB
    average_speed = serializers.FloatField()  # Mbps
    total_time_spent = serializers.IntegerField()  # seconds
    downloads_this_month = serializers.IntegerField()
    downloads_this_week = serializers.IntegerField()
    most_downloaded_course = serializers.CharField()
    favorite_quality = serializers.CharField()


class DownloadCreateSerializer(serializers.Serializer):
    """Serializer for creating download jobs"""

    course_id = serializers.UUIDField()
    quality = serializers.ChoiceField(
        choices=['360p', '480p', '720p', '1080p', 'auto'],
        default='720p'
    )
    include_subtitles = serializers.BooleanField(default=True)
    include_attachments = serializers.BooleanField(default=True)
    selected_lectures = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high', 'urgent'],
        default='normal'
    )

    def validate_course_id(self, value):
        """Validate course exists"""
        try:
            Course.objects.get(id=value, status='active')
        except Course.DoesNotExist:
            raise serializers.ValidationError('Course not found or inactive')
        return value


class BulkDownloadSerializer(serializers.Serializer):
    """Serializer for bulk download creation"""

    course_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=10
    )
    quality = serializers.ChoiceField(
        choices=['360p', '480p', '720p', '1080p', 'auto'],
        default='720p'
    )
    include_subtitles = serializers.BooleanField(default=True)
    include_attachments = serializers.BooleanField(default=True)
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high'],
        default='normal'
    )

    def validate_course_ids(self, value):
        """Validate all courses exist and user has access"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError('Authentication required')

        user = request.user

        # Check courses exist
        existing_courses = Course.objects.filter(
            id__in=value,
            status='active'
        ).count()

        if existing_courses != len(value):
            raise serializers.ValidationError('Some courses not found or inactive')

        # Check user enrollment
        from apps.courses.models import UserCourse
        enrolled_courses = UserCourse.objects.filter(
            user=user,
            course_id__in=value
        ).count()

        if enrolled_courses != len(value):
            raise serializers.ValidationError('Must be enrolled in all courses')

        return value