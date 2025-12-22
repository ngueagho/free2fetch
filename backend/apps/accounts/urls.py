"""
URLs for Accounts app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, RegisterView, LoginView, LogoutView,
    PasswordResetRequestView, PasswordResetConfirmView,
    UdemyAuthView, ConnectedAccountsView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Password reset
    path('password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # OAuth integrations
    path('oauth/udemy/', UdemyAuthView.as_view(), name='udemy_oauth'),
    path('connected-accounts/', ConnectedAccountsView.as_view(), name='connected_accounts'),

    # User management
    path('', include(router.urls)),
]