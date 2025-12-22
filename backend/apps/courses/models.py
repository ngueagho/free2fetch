"""
Course Models for Free2Fetch
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
import uuid
import json

User = get_user_model()


class Course(models.Model):
    """
    Udemy Course model
    """
    COURSE_LEVEL_CHOICES = [
        ('beginner', _('Beginner')),
        ('intermediate', _('Intermediate')),
        ('advanced', _('Advanced')),
        ('expert', _('Expert')),
    ]

    COURSE_STATUS_CHOICES = [
        ('active', _('Active')),
        ('draft', _('Draft')),
        ('archived', _('Archived')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Udemy course information
    udemy_course_id = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Udemy course ID')
    )

    title = models.CharField(
        max_length=500,
        help_text=_('Course title')
    )

    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text=_('URL-friendly course identifier')
    )

    description = models.TextField(
        blank=True,
        help_text=_('Course description')
    )

    headline = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Course headline/subtitle')
    )

    # Course metadata
    instructor_name = models.CharField(
        max_length=200,
        help_text=_('Main instructor name')
    )

    level = models.CharField(
        max_length=20,
        choices=COURSE_LEVEL_CHOICES,
        default='beginner',
        help_text=_('Course difficulty level')
    )

    language = models.CharField(
        max_length=10,
        default='en',
        help_text=_('Course language code')
    )

    category = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Course category')
    )

    subcategory = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Course subcategory')
    )

    # Course metrics
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        help_text=_('Course rating (0-5)')
    )

    num_reviews = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of reviews')
    )

    num_students = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of enrolled students')
    )

    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text=_('Total course duration in seconds')
    )

    num_lectures = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of lectures')
    )

    # Content information
    has_captions = models.BooleanField(
        default=False,
        help_text=_('Course has closed captions')
    )

    has_coding_exercises = models.BooleanField(
        default=False,
        help_text=_('Course has coding exercises')
    )

    has_quizzes = models.BooleanField(
        default=False,
        help_text=_('Course has quizzes')
    )

    # Images
    image_url = models.URLField(
        blank=True,
        help_text=_('Course thumbnail image URL')
    )

    image_file = models.ImageField(
        upload_to='course_images/',
        blank=True,
        null=True,
        help_text=_('Locally stored course image')
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Course price')
    )

    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text=_('Price currency code')
    )

    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=COURSE_STATUS_CHOICES,
        default='active',
        help_text=_('Course status')
    )

    last_updated = models.DateTimeField(
        help_text=_('Last update time from Udemy')
    )

    # Analytics
    download_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times downloaded')
    )

    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times viewed')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_course'
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['udemy_course_id']),
            models.Index(fields=['instructor_name']),
            models.Index(fields=['category']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return self.title

    @property
    def duration_formatted(self):
        """Format duration as HH:MM:SS"""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
        self.save(update_fields=['download_count'])

    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class Curriculum(models.Model):
    """
    Course curriculum/chapter model
    """
    ITEM_TYPE_CHOICES = [
        ('lecture', _('Lecture')),
        ('quiz', _('Quiz')),
        ('practice', _('Practice Exercise')),
        ('assignment', _('Assignment')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='curriculum_items'
    )

    # Udemy curriculum data
    udemy_item_id = models.CharField(
        max_length=100,
        help_text=_('Udemy curriculum item ID')
    )

    title = models.CharField(
        max_length=500,
        help_text=_('Curriculum item title')
    )

    description = models.TextField(
        blank=True,
        help_text=_('Item description')
    )

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default='lecture',
        help_text=_('Type of curriculum item')
    )

    # Hierarchy
    section_title = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Section/chapter title')
    )

    order_index = models.PositiveIntegerField(
        default=0,
        help_text=_('Order within course')
    )

    section_index = models.PositiveIntegerField(
        default=0,
        help_text=_('Section number')
    )

    # Content metadata
    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text=_('Item duration in seconds')
    )

    is_free = models.BooleanField(
        default=False,
        help_text=_('Free preview available')
    )

    # Video information (for lectures)
    video_url = models.URLField(
        blank=True,
        help_text=_('Video URL from Udemy')
    )

    video_quality = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Video quality (480p, 720p, 1080p)')
    )

    # Download status
    is_downloadable = models.BooleanField(
        default=True,
        help_text=_('Item can be downloaded')
    )

    download_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times downloaded')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_curriculum'
        verbose_name = _('Curriculum Item')
        verbose_name_plural = _('Curriculum Items')
        ordering = ['course', 'section_index', 'order_index']
        unique_together = ['course', 'udemy_item_id']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def duration_formatted(self):
        """Format duration as MM:SS"""
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


class UserCourse(models.Model):
    """
    Relationship between users and their enrolled courses
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrolled_courses'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrolled_users'
    )

    # Enrollment information
    enrollment_date = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Date user enrolled in course')
    )

    # Progress tracking
    progress_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text=_('Course completion percentage')
    )

    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last time user accessed course')
    )

    completed_lectures = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of completed lectures')
    )

    # User rating
    user_rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        help_text=_('User rating for this course')
    )

    user_review = models.TextField(
        blank=True,
        help_text=_('User review text')
    )

    # Favorite and bookmarks
    is_favorite = models.BooleanField(
        default=False,
        help_text=_('User marked as favorite')
    )

    # Download preferences
    preferred_quality = models.CharField(
        max_length=20,
        default='720p',
        help_text=_('Preferred download quality')
    )

    download_subtitles = models.BooleanField(
        default=True,
        help_text=_('Download subtitles with videos')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_user_course'
        verbose_name = _('User Course')
        verbose_name_plural = _('User Courses')
        unique_together = ['user', 'course']
        ordering = ['-last_accessed']

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

    def update_progress(self):
        """Calculate and update progress percentage"""
        total_lectures = self.course.curriculum_items.filter(
            item_type='lecture'
        ).count()

        if total_lectures > 0:
            self.progress_percentage = (self.completed_lectures / total_lectures) * 100
            self.save(update_fields=['progress_percentage'])


class CourseShare(models.Model):
    """
    Course sharing between users
    """
    PERMISSION_CHOICES = [
        ('view', _('View Only')),
        ('download', _('View and Download')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='shares'
    )

    shared_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_courses'
    )

    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_shares',
        blank=True,
        null=True
    )

    # Sharing options
    share_link = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text=_('Unique sharing link')
    )

    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default='view',
        help_text=_('Permission level for shared user')
    )

    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text=_('Public sharing (anyone with link)')
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Share expiration date')
    )

    max_access_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Maximum number of accesses')
    )

    current_access_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Current number of accesses')
    )

    # Security
    password_protected = models.BooleanField(
        default=False,
        help_text=_('Require password to access')
    )

    access_password = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Password for access (hashed)')
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_('Share is active')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses_course_share'
        verbose_name = _('Course Share')
        verbose_name_plural = _('Course Shares')
        ordering = ['-created_at']

    def __str__(self):
        return f"Share: {self.course.title} by {self.shared_by.email}"

    def is_valid(self):
        """Check if share is still valid"""
        if not self.is_active:
            return False

        # Check expiration
        if self.expires_at:
            from django.utils import timezone
            if timezone.now() > self.expires_at:
                return False

        # Check access count limit
        if self.max_access_count:
            if self.current_access_count >= self.max_access_count:
                return False

        return True

    def increment_access_count(self):
        """Increment access counter"""
        self.current_access_count += 1
        self.save(update_fields=['current_access_count'])