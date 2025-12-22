"""
Admin configuration for Courses app
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from .models import Course, Curriculum, UserCourse, CourseShare


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin interface for Course model"""

    list_display = [
        'title', 'instructor_name', 'category', 'level', 'language',
        'rating_display', 'students_display', 'duration_display',
        'download_count', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'level', 'category', 'language', 'has_captions',
        'has_coding_exercises', 'has_quizzes', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'instructor_name', 'category',
        'subcategory', 'udemy_course_id'
    ]
    readonly_fields = [
        'id', 'slug', 'udemy_course_id', 'download_count', 'view_count',
        'created_at', 'updated_at', 'curriculum_count', 'enrolled_users_count'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'udemy_course_id', 'title', 'slug', 'description', 'headline'
            )
        }),
        ('Instructor & Classification', {
            'fields': (
                'instructor_name', 'category', 'subcategory', 'level', 'language'
            )
        }),
        ('Metrics', {
            'fields': (
                'rating', 'num_reviews', 'num_students', 'duration_seconds',
                'num_lectures', 'download_count', 'view_count'
            )
        }),
        ('Features', {
            'fields': (
                'has_captions', 'has_coding_exercises', 'has_quizzes'
            )
        }),
        ('Media', {
            'fields': ('image_url', 'image_file')
        }),
        ('Pricing', {
            'fields': ('price', 'currency')
        }),
        ('Status & Dates', {
            'fields': (
                'status', 'last_updated', 'created_at', 'updated_at'
            )
        }),
        ('Statistics', {
            'fields': ('curriculum_count', 'enrolled_users_count'),
            'classes': ('collapse',)
        })
    )

    def rating_display(self, obj):
        """Display rating with stars"""
        stars = '⭐' * int(obj.rating)
        return format_html(
            '{} <span style="color: #666;">({:.1f})</span>',
            stars,
            obj.rating
        )

    rating_display.short_description = 'Rating'

    def students_display(self, obj):
        """Display formatted student count"""
        if obj.num_students >= 1000000:
            return f"{obj.num_students / 1000000:.1f}M"
        elif obj.num_students >= 1000:
            return f"{obj.num_students / 1000:.1f}K"
        return str(obj.num_students)

    students_display.short_description = 'Students'

    def duration_display(self, obj):
        """Display formatted duration"""
        return obj.duration_formatted

    duration_display.short_description = 'Duration'

    def curriculum_count(self, obj):
        """Count curriculum items"""
        return obj.curriculum_items.count()

    curriculum_count.short_description = 'Curriculum Items'

    def enrolled_users_count(self, obj):
        """Count enrolled users"""
        return obj.enrolled_users.count()

    enrolled_users_count.short_description = 'Enrolled Users'

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            curriculum_count=Count('curriculum_items'),
            enrolled_count=Count('enrolled_users')
        )

    actions = ['make_active', 'make_draft', 'update_metrics']

    def make_active(self, request, queryset):
        """Make selected courses active"""
        count = queryset.update(status='active')
        self.message_user(request, f'{count} courses made active.')

    make_active.short_description = "Make active"

    def make_draft(self, request, queryset):
        """Make selected courses draft"""
        count = queryset.update(status='draft')
        self.message_user(request, f'{count} courses made draft.')

    make_draft.short_description = "Make draft"

    def update_metrics(self, request, queryset):
        """Update course metrics"""
        # This would integrate with Udemy API to update metrics
        count = queryset.count()
        self.message_user(request, f'Metrics update queued for {count} courses.')

    update_metrics.short_description = "Update metrics"


class CurriculumInline(admin.TabularInline):
    """Inline admin for Curriculum"""

    model = Curriculum
    extra = 0
    readonly_fields = ['udemy_item_id', 'download_count', 'created_at']
    fields = [
        'title', 'item_type', 'section_title', 'order_index', 'section_index',
        'duration_seconds', 'is_free', 'video_quality', 'is_downloadable'
    ]


@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    """Admin interface for Curriculum model"""

    list_display = [
        'title', 'course_title', 'item_type', 'section_title',
        'duration_display', 'is_downloadable', 'download_count'
    ]
    list_filter = [
        'item_type', 'is_free', 'is_downloadable', 'video_quality', 'created_at'
    ]
    search_fields = [
        'title', 'course__title', 'section_title', 'udemy_item_id'
    ]
    readonly_fields = [
        'id', 'udemy_item_id', 'download_count', 'created_at', 'updated_at'
    ]
    ordering = ['course', 'section_index', 'order_index']

    def course_title(self, obj):
        """Display course title with link"""
        url = reverse('admin:courses_course_change', args=[obj.course.pk])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    course_title.short_description = 'Course'

    def duration_display(self, obj):
        """Display formatted duration"""
        return obj.duration_formatted

    duration_display.short_description = 'Duration'


@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    """Admin interface for UserCourse model"""

    list_display = [
        'user_email', 'course_title', 'progress_display', 'user_rating',
        'is_favorite', 'enrollment_date', 'last_accessed'
    ]
    list_filter = [
        'is_favorite', 'preferred_quality', 'download_subtitles',
        'enrollment_date', 'last_accessed'
    ]
    search_fields = [
        'user__email', 'user__username', 'course__title', 'course__instructor_name'
    ]
    readonly_fields = [
        'id', 'enrollment_date', 'created_at', 'updated_at'
    ]
    ordering = ['-enrollment_date']

    def user_email(self, obj):
        """Display user email with link"""
        url = reverse('admin:accounts_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)

    user_email.short_description = 'User'

    def course_title(self, obj):
        """Display course title with link"""
        url = reverse('admin:courses_course_change', args=[obj.course.pk])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    course_title.short_description = 'Course'

    def progress_display(self, obj):
        """Display progress with bar"""
        percentage = obj.progress_percentage
        color = 'green' if percentage == 100 else 'orange' if percentage > 50 else 'red'

        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 3px; '
            'display: flex; align-items: center; justify-content: center; color: white; '
            'font-size: 12px;">{:.1f}%</div></div>',
            percentage, color, percentage
        )

    progress_display.short_description = 'Progress'

    actions = ['mark_as_favorite', 'unmark_as_favorite', 'reset_progress']

    def mark_as_favorite(self, request, queryset):
        """Mark courses as favorite"""
        count = queryset.update(is_favorite=True)
        self.message_user(request, f'{count} courses marked as favorite.')

    mark_as_favorite.short_description = "Mark as favorite"

    def unmark_as_favorite(self, request, queryset):
        """Unmark courses as favorite"""
        count = queryset.update(is_favorite=False)
        self.message_user(request, f'{count} courses unmarked as favorite.')

    unmark_as_favorite.short_description = "Unmark as favorite"

    def reset_progress(self, request, queryset):
        """Reset course progress"""
        count = queryset.update(
            progress_percentage=0,
            completed_lectures=0
        )
        self.message_user(request, f'Progress reset for {count} courses.')

    reset_progress.short_description = "Reset progress"


@admin.register(CourseShare)
class CourseShareAdmin(admin.ModelAdmin):
    """Admin interface for CourseShare model"""

    list_display = [
        'course_title', 'shared_by_email', 'shared_with_email',
        'permission_level', 'is_public', 'access_display',
        'is_active', 'expires_at', 'created_at'
    ]
    list_filter = [
        'permission_level', 'is_public', 'is_active', 'password_protected',
        'created_at', 'expires_at'
    ]
    search_fields = [
        'course__title', 'shared_by__email', 'shared_with__email',
        'share_link'
    ]
    readonly_fields = [
        'id', 'share_link', 'current_access_count', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']

    def course_title(self, obj):
        """Display course title with link"""
        url = reverse('admin:courses_course_change', args=[obj.course.pk])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    course_title.short_description = 'Course'

    def shared_by_email(self, obj):
        """Display shared by email with link"""
        url = reverse('admin:accounts_user_change', args=[obj.shared_by.pk])
        return format_html('<a href="{}">{}</a>', url, obj.shared_by.email)

    shared_by_email.short_description = 'Shared By'

    def shared_with_email(self, obj):
        """Display shared with email with link"""
        if obj.shared_with:
            url = reverse('admin:accounts_user_change', args=[obj.shared_with.pk])
            return format_html('<a href="{}">{}</a>', url, obj.shared_with.email)
        return 'Public Share'

    shared_with_email.short_description = 'Shared With'

    def access_display(self, obj):
        """Display access count with limit"""
        if obj.max_access_count:
            percentage = (obj.current_access_count / obj.max_access_count) * 100
            color = 'red' if percentage >= 100 else 'orange' if percentage >= 80 else 'green'

            return format_html(
                '<span style="color: {};">{}/{}</span>',
                color, obj.current_access_count, obj.max_access_count
            )
        return f"{obj.current_access_count}/∞"

    access_display.short_description = 'Access Count'

    actions = ['deactivate_shares', 'extend_expiry', 'reset_access_count']

    def deactivate_shares(self, request, queryset):
        """Deactivate selected shares"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} shares deactivated.')

    deactivate_shares.short_description = "Deactivate shares"

    def extend_expiry(self, request, queryset):
        """Extend expiry by 30 days"""
        from django.utils import timezone
        from datetime import timedelta

        for share in queryset:
            if share.expires_at:
                share.expires_at += timedelta(days=30)
            else:
                share.expires_at = timezone.now() + timedelta(days=30)
            share.save()

        count = queryset.count()
        self.message_user(request, f'Expiry extended by 30 days for {count} shares.')

    extend_expiry.short_description = "Extend expiry by 30 days"

    def reset_access_count(self, request, queryset):
        """Reset access count"""
        count = queryset.update(current_access_count=0)
        self.message_user(request, f'Access count reset for {count} shares.')

    reset_access_count.short_description = "Reset access count"