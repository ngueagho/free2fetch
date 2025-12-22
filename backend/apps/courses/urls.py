"""
URLs for Courses app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, UserCourseViewSet, CourseShareViewSet,
    CourseSearchView, PublicShareView
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='courses')
router.register(r'my-courses', UserCourseViewSet, basename='my-courses')
router.register(r'shares', CourseShareViewSet, basename='course-shares')

urlpatterns = [
    # Course search
    path('search/', CourseSearchView.as_view(), name='course_search'),

    # Public share access
    path('share/<uuid:share_link>/', PublicShareView.as_view(), name='public_share'),

    # Include router URLs
    path('', include(router.urls)),
]