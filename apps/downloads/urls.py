"""
URLs for downloads management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tasks', views.DownloadTaskViewSet, basename='tasks')
router.register(r'history', views.DownloadHistoryViewSet, basename='history')

urlpatterns = [
    # Download management
    path('start/', views.StartDownloadView.as_view(), name='start_download'),
    path('batch-start/', views.BatchStartDownloadView.as_view(), name='batch_start'),

    # Include router URLs
    path('', include(router.urls)),
]