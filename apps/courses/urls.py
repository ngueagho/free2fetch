"""
URLs for courses management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.CourseViewSet, basename='courses')

urlpatterns = [
    # Course management
    path('sync/', views.SyncCoursesView.as_view(), name='sync_courses'),
    path('search/', views.SearchCoursesView.as_view(), name='search_courses'),

    # Include router URLs
    path('', include(router.urls)),
]