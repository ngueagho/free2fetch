"""
Course models for udemy_downloader.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
import json

User = get_user_model()


class Course(models.Model):
    """Course model representing a Udemy course."""

    # Udemy course information
    udemy_id = models.PositiveIntegerField(_('Udemy Course ID'), unique=True)
    title = models.CharField(_('Title'), max_length=500)
    url = models.URLField(_('Course URL'), max_length=1000)
    image_url = models.URLField(_('Image URL'), max_length=1000, blank=True)

    # Course metadata
    description = models.TextField(_('Description'), blank=True)
    instructor_name = models.CharField(_('Instructor Name'), max_length=200, blank=True)
    duration = models.DurationField(_('Duration'), blank=True, null=True)
    language = models.CharField(_('Language'), max_length=50, blank=True)

    # Course structure
    total_lectures = models.PositiveIntegerField(_('Total Lectures'), default=0)
    total_chapters = models.PositiveIntegerField(_('Total Chapters'), default=0)
    encrypted_videos_count = models.PositiveIntegerField(_('Encrypted Videos Count'), default=0)

    # Availability
    is_enrolled = models.BooleanField(_('Is Enrolled'), default=False)
    is_subscriber_content = models.BooleanField(_('Is Subscriber Content'), default=False)

    # Content metadata (JSON field for flexible data storage)
    available_subtitles = models.JSONField(
        _('Available Subtitles'),
        default=dict,
        help_text=_('Available subtitle languages and their counts')
    )

    course_data = models.JSONField(
        _('Course Data'),
        default=dict,
        help_text=_('Complete course structure data from Udemy API')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(_('Last Synced'), auto_now=True)

    class Meta:
        db_table = 'courses_course'
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} (ID: {self.udemy_id})"

    @property
    def has_encrypted_content(self):
        """Check if course has encrypted content."""
        return self.encrypted_videos_count > 0

    def get_subtitle_languages(self):
        """Get list of available subtitle languages."""
        if isinstance(self.available_subtitles, dict):
            return list(self.available_subtitles.keys())
        return []


class Chapter(models.Model):
    """Chapter model representing a course chapter."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='chapters'
    )

    # Chapter information
    udemy_id = models.PositiveIntegerField(_('Udemy Chapter ID'))
    title = models.CharField(_('Title'), max_length=500)
    description = models.TextField(_('Description'), blank=True)

    # Ordering
    order = models.PositiveIntegerField(_('Order'))

    # Metadata
    lecture_count = models.PositiveIntegerField(_('Lecture Count'), default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_chapter'
        verbose_name = _('Chapter')
        verbose_name_plural = _('Chapters')
        ordering = ['course', 'order']
        unique_together = ['course', 'udemy_id']

    def __str__(self):
        return f"{self.course.title} - Chapter {self.order}: {self.title}"


class Lecture(models.Model):
    """Lecture model representing a course lecture."""

    LECTURE_TYPE_CHOICES = [
        ('video', _('Video')),
        ('article', _('Article')),
        ('quiz', _('Quiz')),
        ('practice', _('Practice')),
        ('file', _('File')),
        ('url', _('URL')),
    ]

    QUALITY_CHOICES = [
        ('Auto', _('Auto')),
        ('144', '144p'),
        ('240', '240p'),
        ('360', '360p'),
        ('480', '480p'),
        ('720', '720p'),
        ('1080', '1080p'),
        ('Highest', _('Highest')),
        ('Lowest', _('Lowest')),
        ('Attachment', _('Attachment')),
        ('Subtitle', _('Subtitle')),
        ('NotFound', _('Not Found')),
    ]

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='lectures'
    )

    # Lecture information
    udemy_id = models.PositiveIntegerField(_('Udemy Lecture ID'))
    title = models.CharField(_('Title'), max_length=500)
    description = models.TextField(_('Description'), blank=True)

    # Content information
    lecture_type = models.CharField(
        _('Lecture Type'),
        max_length=20,
        choices=LECTURE_TYPE_CHOICES,
        default='video'
    )

    quality = models.CharField(
        _('Quality'),
        max_length=20,
        choices=QUALITY_CHOICES,
        default='Auto'
    )

    # URLs and sources
    source_url = models.URLField(_('Source URL'), max_length=2000, blank=True)
    is_encrypted = models.BooleanField(_('Is Encrypted'), default=False)

    # Duration and size
    duration = models.DurationField(_('Duration'), blank=True, null=True)
    file_size = models.BigIntegerField(_('File Size'), blank=True, null=True)

    # Ordering
    order = models.PositiveIntegerField(_('Order'))

    # Metadata
    asset_data = models.JSONField(
        _('Asset Data'),
        default=dict,
        help_text=_('Complete asset data from Udemy API')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_lecture'
        verbose_name = _('Lecture')
        verbose_name_plural = _('Lectures')
        ordering = ['chapter', 'order']
        unique_together = ['chapter', 'udemy_id']

    def __str__(self):
        return f"{self.chapter.title} - Lecture {self.order}: {self.title}"

    @property
    def course(self):
        """Get the course this lecture belongs to."""
        return self.chapter.course


class LectureSubtitle(models.Model):
    """Subtitle model for lecture subtitles."""

    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
        related_name='subtitles'
    )

    # Subtitle information
    language = models.CharField(_('Language'), max_length=50)
    language_label = models.CharField(_('Language Label'), max_length=100)
    source_url = models.URLField(_('Source URL'), max_length=2000)

    # File information
    is_auto_generated = models.BooleanField(_('Is Auto Generated'), default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_lecture_subtitle'
        verbose_name = _('Lecture Subtitle')
        verbose_name_plural = _('Lecture Subtitles')
        unique_together = ['lecture', 'language']

    def __str__(self):
        return f"{self.lecture.title} - {self.language_label}"


class LectureAttachment(models.Model):
    """Attachment model for lecture attachments."""

    ATTACHMENT_TYPE_CHOICES = [
        ('file', _('File')),
        ('url', _('URL')),
        ('article', _('Article')),
    ]

    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    # Attachment information
    title = models.CharField(_('Title'), max_length=500)
    attachment_type = models.CharField(
        _('Type'),
        max_length=20,
        choices=ATTACHMENT_TYPE_CHOICES,
        default='file'
    )

    source_url = models.URLField(_('Source URL'), max_length=2000, blank=True)
    external_url = models.URLField(_('External URL'), max_length=2000, blank=True)

    # File information
    filename = models.CharField(_('Filename'), max_length=255, blank=True)
    file_size = models.BigIntegerField(_('File Size'), blank=True, null=True)

    # Content (for articles)
    content = models.TextField(_('Content'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_lecture_attachment'
        verbose_name = _('Lecture Attachment')
        verbose_name_plural = _('Lecture Attachments')
        ordering = ['lecture', 'title']

    def __str__(self):
        return f"{self.lecture.title} - {self.title}"


class UserCourse(models.Model):
    """Relationship between users and courses."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_courses'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrolled_users'
    )

    # Enrollment information
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(_('Last Accessed'), auto_now=True)

    # Progress tracking
    is_completed = models.BooleanField(_('Is Completed'), default=False)
    completion_percentage = models.FloatField(_('Completion Percentage'), default=0.0)

    # Download tracking
    is_downloaded = models.BooleanField(_('Is Downloaded'), default=False)
    download_path = models.CharField(_('Download Path'), max_length=1000, blank=True)

    class Meta:
        db_table = 'courses_user_course'
        verbose_name = _('User Course')
        verbose_name_plural = _('User Courses')
        unique_together = ['user', 'course']
        ordering = ['-last_accessed']

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"