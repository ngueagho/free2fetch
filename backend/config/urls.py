"""
URL configuration for Free2Fetch project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health check
    path('health/', lambda request: HttpResponse('OK'), name='health'),

    # API placeholder
    path('api/', lambda request: HttpResponse('Free2Fetch API v1.0'), name='api'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin configuration
admin.site.site_header = "Free2Fetch Administration"
admin.site.site_title = "Free2Fetch Admin Portal"
admin.site.index_title = "Welcome to Free2Fetch Administration"