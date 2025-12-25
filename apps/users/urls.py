"""
URLs for user authentication and management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'preferences', views.UserPreferencesViewSet, basename='preferences')

urlpatterns = [
    # Authentication endpoints
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Udemy authentication - COMPLETE IMPLEMENTATION
    path('udemy-login/', views.UdemyLoginView.as_view(), name='udemy_login'),
    path('udemy-callback/', views.UdemyCallbackView.as_view(), name='udemy_callback'),
    path('token-login/', views.TokenLoginView.as_view(), name='token_login'),
    path('test-connection/', views.TestConnectionView.as_view(), name='test_connection'),
    path('csrf-token/', views.CSRFTokenView.as_view(), name='csrf_token'),
    path('udemy/validate/', views.UdemyValidateView.as_view(), name='udemy_validate'),
    path('udemy/logout/', views.UdemyLogoutView.as_view(), name='udemy_logout'),

    # User profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # Include router URLs
    path('', include(router.urls)),
]