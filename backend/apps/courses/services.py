import logging
from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from .models import Course, Curriculum, UserCourse
from ..accounts.oauth import get_udemy_service

User = get_user_model()
logger = logging.getLogger(__name__)

class CourseService:
    """
    Service for managing course data and synchronization with Udemy
    """

    def __init__(self):
        self.udemy_service = get_udemy_service()

    def sync_user_courses(self, user: User, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Synchronize user's courses from Udemy
        """
        try:
            access_token = self.udemy_service.ensure_valid_token(user)

            # Check if we need to sync (only sync once per hour unless forced)
            if not force_refresh:
                last_sync = getattr(user.profile, 'last_course_sync', None)
                if (last_sync and
                    timezone.now() - last_sync < timezone.timedelta(hours=1)):
                    return {
                        'success': True,
                        'message': 'Courses already synced recently',
                        'courses_added': 0,
                        'courses_updated': 0
                    }

            courses_added = 0
            courses_updated = 0
            page = 1
            has_more = True

            with transaction.atomic():
                while has_more:
                    # Get courses from Udemy API
                    response = self.udemy_service.get_user_courses(
                        access_token, page=page, page_size=50
                    )

                    courses_data = response.get('results', [])
                    has_more = bool(response.get('next'))
                    page += 1

                    for course_data in courses_data:
                        course, created = self._create_or_update_course(course_data)

                        # Create or update user course relationship
                        user_course, uc_created = UserCourse.objects.get_or_create(
                            user=user,
                            course=course,
                            defaults={
                                'enrollment_date': timezone.now(),
                                'last_accessed': timezone.now(),
                                'is_favorite': False,
                                'progress_percentage': 0
                            }
                        )

                        if not uc_created:
                            user_course.last_accessed = timezone.now()
                            user_course.save()
                            courses_updated += 1
                        else:
                            courses_added += 1

                        # Sync course curriculum if it's a new course
                        if created:
                            self._sync_course_curriculum(course, course_data, access_token)

                # Update last sync time
                user.profile.last_course_sync = timezone.now()
                user.profile.save()

            logger.info(f'Synced courses for user {user.email}: {courses_added} added, {courses_updated} updated')

            return {
                'success': True,
                'message': 'Courses synchronized successfully',
                'courses_added': courses_added,
                'courses_updated': courses_updated
            }

        except Exception as e:
            logger.error(f'Failed to sync courses for user {user.email}: {e}')
            return {
                'success': False,
                'message': f'Failed to synchronize courses: {str(e)}',
                'courses_added': 0,
                'courses_updated': 0
            }

    def _create_or_update_course(self, course_data: Dict[str, Any]) -> tuple[Course, bool]:
        """
        Create or update a course from Udemy data
        """
        udemy_id = str(course_data.get('id'))

        # Extract instructor information
        instructors = course_data.get('visible_instructors', [])
        instructor_names = [inst.get('display_name', '') for inst in instructors]
        instructor = ', '.join(instructor_names) if instructor_names else 'Unknown'

        # Parse duration (content_length is in seconds)
        content_length = course_data.get('content_length', 0)
        duration_hours = content_length // 3600
        duration_minutes = (content_length % 3600) // 60
        duration_formatted = f"{duration_hours}h {duration_minutes}m"

        defaults = {
            'title': course_data.get('title', ''),
            'instructor': instructor,
            'description': course_data.get('headline', ''),
            'thumbnail': self._get_best_image(course_data),
            'duration': duration_formatted,
            'rating': course_data.get('avg_rating', 0.0),
            'enrolled_students': course_data.get('num_subscribers', 0),
            'total_lectures': course_data.get('num_lectures', 0),
            'level': course_data.get('instructional_level', 'Beginner'),
            'language': course_data.get('locale', {}).get('english_title', 'English'),
            'udemy_url': course_data.get('url', ''),
            'is_public': course_data.get('is_public', False),
            'created_at': self._parse_udemy_date(course_data.get('created')),
            'published_at': self._parse_udemy_date(course_data.get('published_time')),
        }

        return Course.objects.update_or_create(
            udemy_id=udemy_id,
            defaults=defaults
        )

    def _sync_course_curriculum(self, course: Course, course_data: Dict[str, Any], access_token: str):
        """
        Sync course curriculum from Udemy
        """
        try:
            # Get detailed course info including curriculum
            detailed_course = self.udemy_service.get_course_details(access_token, course.udemy_id)
            curriculum_data = detailed_course.get('curriculum', [])

            for item_data in curriculum_data:
                self._create_curriculum_item(course, item_data)

            logger.info(f'Synced curriculum for course {course.title}')

        except Exception as e:
            logger.error(f'Failed to sync curriculum for course {course.title}: {e}')

    def _create_curriculum_item(self, course: Course, item_data: Dict[str, Any]):
        """
        Create curriculum item from Udemy data
        """
        defaults = {
            'title': item_data.get('title', ''),
            'description': item_data.get('description', ''),
            'sort_order': item_data.get('sort_order', 0),
            'item_type': self._determine_item_type(item_data),
            'duration': self._extract_duration(item_data),
            'is_free': item_data.get('is_free', False),
        }

        curriculum_item, created = Curriculum.objects.update_or_create(
            course=course,
            udemy_id=str(item_data.get('id')),
            defaults=defaults
        )

        return curriculum_item

    def _get_best_image(self, course_data: Dict[str, Any]) -> str:
        """
        Get the best available image URL from course data
        """
        # Try to get the highest quality image available
        for size in ['image_480x270', 'image_240x135']:
            if course_data.get(size):
                return course_data[size]
        return ''

    def _parse_udemy_date(self, date_string: Optional[str]) -> Optional[timezone.datetime]:
        """
        Parse Udemy date string to datetime object
        """
        if not date_string:
            return None

        try:
            from datetime import datetime
            # Udemy typically uses ISO 8601 format
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

    def _determine_item_type(self, item_data: Dict[str, Any]) -> str:
        """
        Determine curriculum item type from Udemy data
        """
        # This is a simplified version - in practice, you'd need to check
        # the asset type and other fields to determine the actual type
        asset = item_data.get('asset', {})
        asset_type = asset.get('asset_type', '').lower()

        if asset_type in ['video', 'presentation']:
            return 'lecture'
        elif asset_type in ['article', 'text']:
            return 'article'
        elif asset_type in ['file', 'source_code']:
            return 'resource'
        elif asset_type == 'practice':
            return 'quiz'
        else:
            return 'lecture'  # Default to lecture

    def _extract_duration(self, item_data: Dict[str, Any]) -> int:
        """
        Extract duration in seconds from item data
        """
        asset = item_data.get('asset', {})
        time_estimation = asset.get('time_estimation', 0)

        # time_estimation is usually in seconds
        return int(time_estimation) if time_estimation else 0

    def get_user_courses(self, user: User, filters: Optional[Dict[str, Any]] = None) -> List[Course]:
        """
        Get user's courses with optional filters
        """
        queryset = Course.objects.filter(
            usercourse__user=user
        ).select_related().prefetch_related('curriculum_set')

        if filters:
            # Apply search filter
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    models.Q(title__icontains=search) |
                    models.Q(instructor__icontains=search) |
                    models.Q(description__icontains=search)
                )

            # Apply status filter
            download_status = filters.get('download_status')
            if download_status:
                queryset = queryset.filter(download_status=download_status)

            # Apply ordering
            ordering = filters.get('ordering', '-usercourse__last_accessed')
            queryset = queryset.order_by(ordering)

        return list(queryset)

    def update_course_progress(self, user: User, course_id: str, progress_percentage: int):
        """
        Update user's progress for a course
        """
        try:
            user_course = UserCourse.objects.get(user=user, course_id=course_id)
            user_course.progress_percentage = max(0, min(100, progress_percentage))
            user_course.last_accessed = timezone.now()
            user_course.save()

            logger.info(f'Updated progress for user {user.email}, course {course_id}: {progress_percentage}%')

        except UserCourse.DoesNotExist:
            logger.warning(f'UserCourse not found for user {user.email}, course {course_id}')

    def toggle_favorite(self, user: User, course_id: str) -> bool:
        """
        Toggle favorite status for a course
        """
        try:
            user_course = UserCourse.objects.get(user=user, course_id=course_id)
            user_course.is_favorite = not user_course.is_favorite
            user_course.save()

            logger.info(f'Toggled favorite for user {user.email}, course {course_id}: {user_course.is_favorite}')
            return user_course.is_favorite

        except UserCourse.DoesNotExist:
            logger.warning(f'UserCourse not found for user {user.email}, course {course_id}')
            return False


def get_course_service() -> CourseService:
    """
    Get singleton instance of CourseService
    """
    return CourseService()