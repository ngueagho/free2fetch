"""
Core Middleware for Free2Fetch
"""
import json
import time
import uuid
from django.utils import timezone
from django.http import JsonResponse
from django.urls import resolve
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class LoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests and user activities
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Process incoming request"""
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())

        # Skip logging for certain paths
        skip_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/health/',
        ]

        request.should_log = not any(
            request.path.startswith(path) for path in skip_paths
        )

        return None

    def process_response(self, request, response):
        """Process outgoing response and log activity"""
        if not hasattr(request, 'should_log') or not request.should_log:
            return response

        try:
            # Calculate response time
            if hasattr(request, 'start_time'):
                response_time = (time.time() - request.start_time) * 1000  # ms
            else:
                response_time = 0

            # Get user info
            user = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user

            # Get client info
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Log the activity
            self.log_user_activity(
                user=user,
                action=self.determine_action(request),
                description=f"{request.method} {request.path}",
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                response_code=response.status_code,
                response_time=response_time,
                request_id=getattr(request, 'request_id', None)
            )

        except Exception as e:
            logger.error(f"Error in LoggingMiddleware: {e}")

        return response

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def determine_action(self, request):
        """Determine the action type based on request"""
        try:
            url_name = resolve(request.path_info).url_name
            method = request.method

            if 'login' in request.path or url_name == 'login':
                return 'login'
            elif 'logout' in request.path or url_name == 'logout':
                return 'logout'
            elif 'download' in request.path:
                return 'course_download'
            elif 'stream' in request.path:
                return 'stream_video'
            elif 'api' in request.path:
                return 'api_request'
            elif method == 'POST':
                return 'create_update'
            elif method == 'GET':
                return 'view'
            else:
                return 'other'

        except Exception:
            return 'unknown'

    def log_user_activity(self, **kwargs):
        """Log user activity asynchronously"""
        try:
            from apps.analytics.models import UserActivity

            # Extract data
            user = kwargs.get('user')
            action = kwargs.get('action', 'unknown')
            description = kwargs.get('description', '')
            ip_address = kwargs.get('ip_address')
            user_agent = kwargs.get('user_agent', '')
            response_time = kwargs.get('response_time', 0)

            # Create activity record
            activity = UserActivity.objects.create(
                user=user,
                action=action,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                response_time_ms=int(response_time),
                metadata={
                    'request_path': kwargs.get('request_path', ''),
                    'request_method': kwargs.get('request_method', ''),
                    'response_code': kwargs.get('response_code', 200),
                    'request_id': kwargs.get('request_id', ''),
                }
            )

            # Update user's last login IP if this is a successful login
            if user and action == 'login' and kwargs.get('response_code') == 200:
                user.last_login_ip = ip_address
                user.save(update_fields=['last_login_ip'])

        except Exception as e:
            logger.error(f"Error logging user activity: {e}")


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for API endpoints and sensitive actions
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Check rate limits before processing request"""
        # Skip rate limiting for certain paths
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/health/',
        ]

        if any(request.path.startswith(path) for path in skip_paths):
            return None

        # Check if rate limiting should be applied
        if not self.should_rate_limit(request):
            return None

        # Get rate limit key and limits
        rate_limit_key = self.get_rate_limit_key(request)
        rate_limits = self.get_rate_limits(request)

        # Check each time window
        for window, limit in rate_limits.items():
            if self.is_rate_limited(rate_limit_key, window, limit):
                return self.rate_limit_response(window, limit)

        # Increment request counters
        for window in rate_limits.keys():
            self.increment_request_count(rate_limit_key, window)

        return None

    def should_rate_limit(self, request):
        """Determine if request should be rate limited"""
        # Always rate limit API requests
        if request.path.startswith('/api/'):
            return True

        # Rate limit login attempts
        if 'login' in request.path and request.method == 'POST':
            return True

        # Rate limit download requests
        if 'download' in request.path:
            return True

        return False

    def get_rate_limit_key(self, request):
        """Generate cache key for rate limiting"""
        # Use user ID if authenticated, otherwise IP address
        if hasattr(request, 'user') and request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            ip = self.get_client_ip(request)
            identifier = f"ip:{ip}"

        # Include path for specific endpoint limits
        endpoint = request.path.split('/')[:3]  # First 3 parts of path
        endpoint_str = '/'.join(endpoint)

        return f"rate_limit:{identifier}:{endpoint_str}"

    def get_rate_limits(self, request):
        """Get rate limits for the request"""
        # Default limits
        limits = {
            'minute': 60,
            'hour': 1000,
            'day': 10000,
        }

        # API-specific limits
        if request.path.startswith('/api/'):
            limits = {
                'minute': 100,
                'hour': 2000,
                'day': 20000,
            }

        # Login-specific limits
        if 'login' in request.path:
            limits = {
                'minute': 5,
                'hour': 20,
                'day': 100,
            }

        # Download-specific limits
        if 'download' in request.path:
            limits = {
                'minute': 10,
                'hour': 50,
                'day': 200,
            }

        # Check if user has custom limits (API key or premium subscription)
        if hasattr(request, 'user') and request.user.is_authenticated:
            custom_limits = self.get_user_custom_limits(request.user)
            if custom_limits:
                limits.update(custom_limits)

        return limits

    def get_user_custom_limits(self, user):
        """Get custom rate limits for user based on subscription/API key"""
        try:
            # Check for API key in headers
            api_key = self.extract_api_key_from_request(user)
            if api_key:
                return {
                    'minute': api_key.rate_limit_per_minute,
                    'hour': api_key.rate_limit_per_hour,
                    'day': api_key.rate_limit_per_day,
                }

            # Check subscription level
            subscription = getattr(user, 'subscription', None)
            if subscription and subscription.is_active:
                if subscription.plan.plan_type == 'premium':
                    return {
                        'minute': 200,
                        'hour': 5000,
                        'day': 50000,
                    }
                elif subscription.plan.plan_type == 'enterprise':
                    return {
                        'minute': 500,
                        'hour': 10000,
                        'day': 100000,
                    }

        except Exception as e:
            logger.error(f"Error getting custom rate limits: {e}")

        return None

    def extract_api_key_from_request(self, user):
        """Extract and validate API key from request"""
        # This would be implemented based on your API key authentication
        return None

    def is_rate_limited(self, key, window, limit):
        """Check if rate limit is exceeded for given window"""
        cache_key = f"{key}:{window}"
        current_count = cache.get(cache_key, 0)
        return current_count >= limit

    def increment_request_count(self, key, window):
        """Increment request count for given window"""
        cache_key = f"{key}:{window}"

        # Set timeout based on window
        timeout_map = {
            'minute': 60,
            'hour': 3600,
            'day': 86400,
        }
        timeout = timeout_map.get(window, 60)

        try:
            # Try to increment existing counter
            current_count = cache.get(cache_key, 0)
            cache.set(cache_key, current_count + 1, timeout)
        except Exception as e:
            logger.error(f"Error incrementing rate limit counter: {e}")

    def rate_limit_response(self, window, limit):
        """Return rate limit exceeded response"""
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'message': f'Too many requests. Limit: {limit} per {window}',
            'retry_after': self.get_retry_after(window)
        }, status=429)

    def get_retry_after(self, window):
        """Get retry-after time in seconds"""
        retry_map = {
            'minute': 60,
            'hour': 3600,
            'day': 86400,
        }
        return retry_map.get(window, 60)

    def get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityMiddleware(MiddlewareMixin):
    """
    Security middleware for additional protection
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Process security checks on incoming requests"""
        # Check for suspicious patterns
        if self.is_suspicious_request(request):
            logger.warning(f"Suspicious request detected from {self.get_client_ip(request)}")
            return JsonResponse({
                'error': 'Request blocked for security reasons'
            }, status=403)

        return None

    def process_response(self, request, response):
        """Add security headers to response"""
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Add Content Security Policy for non-API responses
        if not request.path.startswith('/api/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )

        return response

    def is_suspicious_request(self, request):
        """Check for suspicious request patterns"""
        suspicious_patterns = [
            # SQL injection patterns
            'union select',
            'drop table',
            'delete from',
            # XSS patterns
            '<script',
            'javascript:',
            'onload=',
            # Path traversal
            '../',
            '..\\',
            # Command injection
            '&&',
            '||',
            ';',
        ]

        # Check URL and query parameters
        full_url = request.get_full_path().lower()
        for pattern in suspicious_patterns:
            if pattern in full_url:
                return True

        # Check POST data
        if request.method == 'POST':
            try:
                body = request.body.decode('utf-8').lower()
                for pattern in suspicious_patterns:
                    if pattern in body:
                        return True
            except Exception:
                pass

        return False

    def get_client_ip(self, request):
        """Extract client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MaintenanceMiddleware(MiddlewareMixin):
    """
    Middleware to handle maintenance mode
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Check if system is in maintenance mode"""
        try:
            from apps.core.models import SystemSettings

            # Check if maintenance mode is enabled
            try:
                maintenance_setting = SystemSettings.objects.get(
                    key='system.maintenance_mode'
                )
                is_maintenance = maintenance_setting.get_typed_value()
            except SystemSettings.DoesNotExist:
                is_maintenance = False

            if not is_maintenance:
                return None

            # Allow admin and staff users
            if (hasattr(request, 'user') and
                request.user.is_authenticated and
                (request.user.is_staff or request.user.is_superuser)):
                return None

            # Allow certain paths during maintenance
            allowed_paths = [
                '/admin/',
                '/health/',
                '/api/health/',
            ]

            if any(request.path.startswith(path) for path in allowed_paths):
                return None

            # Return maintenance response
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Service temporarily unavailable',
                    'message': 'System is currently under maintenance',
                    'maintenance': True
                }, status=503)
            else:
                # Return maintenance page (would render a template)
                from django.http import HttpResponse
                return HttpResponse(
                    '<h1>System Maintenance</h1>'
                    '<p>We are currently performing scheduled maintenance. '
                    'Please check back in a few minutes.</p>',
                    status=503,
                    content_type='text/html'
                )

        except Exception as e:
            logger.error(f"Error in MaintenanceMiddleware: {e}")
            return None

        return None