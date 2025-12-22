"""
Social Auth Pipeline for Free2Fetch
Custom pipeline functions for OAuth integration
"""
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile, UserSubscription
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def create_user_profile(strategy, details, backend, user=None, *args, **kwargs):
    """
    Create user profile and subscription when a new user is created via OAuth
    """
    if user and kwargs.get('is_new', False):
        try:
            # Create user profile if it doesn't exist
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'bio': '',
                    'public_profile': True,
                    'email_notifications': True,
                    'newsletter_subscription': False,
                }
            )

            # Create default free subscription
            subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={
                    'plan': 'free',
                    'status': 'active',
                    'monthly_download_limit': 3,
                    'storage_limit_gb': 5,
                    'max_concurrent_downloads': 1,
                    'streaming_enabled': False,
                    'sharing_enabled': False,
                    'api_access_enabled': False,
                    'priority_support': False,
                }
            )

            # Store Udemy OAuth tokens if this is a Udemy login
            if backend.name == 'udemy':
                access_token = kwargs.get('access_token', '')
                refresh_token = kwargs.get('refresh_token', '')

                if access_token:
                    user.udemy_access_token = access_token

                if refresh_token:
                    user.udemy_refresh_token = refresh_token

                # Store Udemy user ID from OAuth response
                if 'response' in kwargs and 'id' in kwargs['response']:
                    user.udemy_user_id = str(kwargs['response']['id'])

                user.save()

            logger.info(f"Created profile and subscription for new user: {user.email}")

        except Exception as e:
            logger.error(f"Error creating user profile/subscription: {e}")

    return {'user': user}


def update_user_details(strategy, details, backend, user=None, *args, **kwargs):
    """
    Update user details from OAuth provider
    """
    if user:
        try:
            updated = False

            # Update basic user info
            if details.get('first_name') and not user.first_name:
                user.first_name = details['first_name']
                updated = True

            if details.get('last_name') and not user.last_name:
                user.last_name = details['last_name']
                updated = True

            if details.get('email') and user.email != details['email']:
                user.email = details['email']
                updated = True

            # Mark email as verified since it comes from OAuth
            if not user.is_verified:
                user.is_verified = True
                updated = True

            if updated:
                user.save()
                logger.info(f"Updated user details for: {user.email}")

        except Exception as e:
            logger.error(f"Error updating user details: {e}")

    return {'user': user}


def save_udemy_token_info(strategy, details, backend, user=None, *args, **kwargs):
    """
    Save Udemy OAuth token information and expiration
    """
    if user and backend.name == 'udemy':
        try:
            # Get token info from response
            response = kwargs.get('response', {})

            if 'access_token' in response:
                user.udemy_access_token = response['access_token']

            if 'refresh_token' in response:
                user.udemy_refresh_token = response['refresh_token']

            # Calculate token expiration
            if 'expires_in' in response:
                from django.utils import timezone
                from datetime import timedelta

                expires_in_seconds = int(response['expires_in'])
                user.udemy_token_expires_at = (
                    timezone.now() + timedelta(seconds=expires_in_seconds)
                )

            user.save()
            logger.info(f"Saved Udemy token info for user: {user.email}")

        except Exception as e:
            logger.error(f"Error saving Udemy token info: {e}")

    return {'user': user}


def log_oauth_login(strategy, details, backend, user=None, *args, **kwargs):
    """
    Log OAuth login attempt for analytics
    """
    if user:
        try:
            from apps.analytics.models import UserActivity
            from django.utils import timezone

            # Get request info
            request = strategy.request if hasattr(strategy, 'request') else None
            ip_address = None
            user_agent = ''

            if request:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0].strip()
                else:
                    ip_address = request.META.get('REMOTE_ADDR')

                user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Log the OAuth login activity
            UserActivity.objects.create(
                user=user,
                action='login',
                description=f'OAuth login via {backend.name}',
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    'oauth_provider': backend.name,
                    'is_new_user': kwargs.get('is_new', False),
                    'login_method': 'oauth',
                }
            )

            logger.info(f"Logged OAuth login for user: {user.email}")

        except Exception as e:
            logger.error(f"Error logging OAuth login: {e}")

    return {'user': user}