"""
API URLs configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'settings', views.SettingsViewSet, basename='settings')

urlpatterns = [
    path('system/info/', views.SystemInfoView.as_view(), name='system-info'),
    path('', include(router.urls)),
]