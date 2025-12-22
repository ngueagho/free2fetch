import requests
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from .models import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)

class UdemyOAuthService:
    """
    Service for handling Udemy OAuth authentication and API interactions
    """

    BASE_URL = 'https://www.udemy.com/api-2.0'
    AUTH_URL = 'https://www.udemy.com/oauth2/authorize'
    TOKEN_URL = 'https://www.udemy.com/oauth2/token'

    def __init__(self):
        self.client_id = settings.UDEMY_CLIENT_ID
        self.client_secret = settings.UDEMY_CLIENT_SECRET
        self.redirect_uri = settings.UDEMY_REDIRECT_URI

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL for Udemy
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'read',  # Adjust scopes as needed
        }

        if state:
            params['state'] = state

        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'{self.AUTH_URL}?{query_string}'

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        """
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Failed to exchange code for token: {e}')
            raise AuthenticationFailed('Failed to authenticate with Udemy')

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        """
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Failed to refresh token: {e}')
            raise AuthenticationFailed('Failed to refresh Udemy token')

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Udemy API
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json, text/plain, */*',
        }

        try:
            response = requests.get(f'{self.BASE_URL}/users/me', headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Failed to get user info: {e}')
            raise AuthenticationFailed('Failed to get user information from Udemy')

    def get_user_courses(self, access_token: str, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        Get user's enrolled courses from Udemy
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json, text/plain, */*',
        }

        params = {
            'page': page,
            'page_size': page_size,
            'fields[course]': 'id,title,headline,description,image_240x135,image_480x270,num_lectures,content_length,avg_rating,num_reviews,is_public,created,published_time,instructional_level,locale,url,visible_instructors',
            'fields[user]': 'id,title,name,display_name,job_title,image_50x50,image_100x100',
            'ordering': '-last_accessed',
        }

        try:
            response = requests.get(
                f'{self.BASE_URL}/users/me/subscribed-courses',
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Failed to get user courses: {e}')
            raise AuthenticationFailed('Failed to get courses from Udemy')

    def get_course_details(self, access_token: str, course_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific course
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json, text/plain, */*',
        }

        params = {
            'fields[course]': 'id,title,headline,description,image_240x135,image_480x270,num_lectures,content_length,avg_rating,num_reviews,is_public,created,published_time,instructional_level,locale,url,visible_instructors,curriculum',
            'fields[user]': 'id,title,name,display_name,job_title,image_50x50,image_100x100',
            'fields[curriculum_item]': 'id,title,description,sort_order,asset,curriculum_lectures',
            'fields[lecture]': 'id,title,description,sort_order,asset',
            'fields[asset]': 'id,title,filename,asset_type,status,time_estimation,is_external,slide_urls,download_urls,stream_urls,captions',
        }

        try:
            response = requests.get(
                f'{self.BASE_URL}/courses/{course_id}',
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Failed to get course details for {course_id}: {e}')
            raise AuthenticationFailed('Failed to get course details from Udemy')

    def create_or_update_user(self, udemy_user_data: Dict[str, Any], token_data: Dict[str, Any]) -> User:
        """
        Create or update user based on Udemy OAuth data
        """
        udemy_id = str(udemy_user_data.get('id'))
        email = udemy_user_data.get('email')
        display_name = udemy_user_data.get('display_name', '')
        name_parts = display_name.split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Try to find existing user by Udemy ID first
        try:
            profile = UserProfile.objects.get(udemy_id=udemy_id)
            user = profile.user
        except UserProfile.DoesNotExist:
            # Try to find by email
            try:
                user = User.objects.get(email=email)
                profile, created = UserProfile.objects.get_or_create(user=user)
            except User.DoesNotExist:
                # Create new user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                profile = UserProfile.objects.create(user=user)

        # Update profile with Udemy data
        profile.udemy_id = udemy_id
        profile.udemy_access_token = token_data.get('access_token')
        profile.udemy_refresh_token = token_data.get('refresh_token')
        profile.udemy_token_expires_at = self._calculate_token_expiry(token_data.get('expires_in'))
        profile.display_name = display_name
        profile.udemy_profile_url = udemy_user_data.get('url', '')
        profile.save()

        # Update user info
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        logger.info(f'Created/updated user {user.email} from Udemy OAuth')
        return user

    def _calculate_token_expiry(self, expires_in: Optional[int]) -> Optional[Any]:
        """
        Calculate token expiry datetime
        """
        if not expires_in:
            return None

        from django.utils import timezone
        from datetime import timedelta

        return timezone.now() + timedelta(seconds=expires_in)

    def ensure_valid_token(self, user: User) -> str:
        """
        Ensure user has a valid Udemy access token, refresh if necessary
        """
        profile = user.profile

        if not profile.udemy_access_token:
            raise AuthenticationFailed('User not connected to Udemy')

        # Check if token needs refresh
        if (profile.udemy_token_expires_at and
            profile.udemy_token_expires_at <= timezone.now() and
            profile.udemy_refresh_token):

            try:
                token_data = self.refresh_token(profile.udemy_refresh_token)
                profile.udemy_access_token = token_data.get('access_token')
                profile.udemy_refresh_token = token_data.get('refresh_token', profile.udemy_refresh_token)
                profile.udemy_token_expires_at = self._calculate_token_expiry(token_data.get('expires_in'))
                profile.save()

                logger.info(f'Refreshed Udemy token for user {user.email}')
            except AuthenticationFailed:
                # Token refresh failed, user needs to re-authenticate
                profile.udemy_access_token = None
                profile.udemy_refresh_token = None
                profile.udemy_token_expires_at = None
                profile.save()
                raise AuthenticationFailed('Udemy token expired, please re-authenticate')

        return profile.udemy_access_token


def get_udemy_service() -> UdemyOAuthService:
    """
    Get singleton instance of UdemyOAuthService
    """
    return UdemyOAuthService()