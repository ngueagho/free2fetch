"""
URL configuration for Free2Fetch project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Admin customization
admin.site.site_header = 'Free2Fetch Administration'
admin.site.site_title = 'Free2Fetch Admin'
admin.site.index_title = 'Welcome to Free2Fetch Administration'

urlpatterns = [
    # Admin URLs
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # OAuth2 URLs
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('auth/', include('social_django.urls', namespace='social')),

    # API URLs
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/courses/', include('apps.courses.urls')),
    path('api/v1/downloads/', include('apps.downloads.urls')),
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/', include('apps.core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns