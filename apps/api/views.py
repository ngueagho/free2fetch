"""
API Views for the Udemy Downloader application.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

User = get_user_model()

class CourseViewSet(viewsets.ViewSet):
    """Course management API endpoints."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List user courses."""
        return Response({'courses': []})

class DownloadTaskViewSet(viewsets.ViewSet):
    """Download management API endpoints."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List download tasks."""
        return Response({'downloads': []})

class AuthViewSet(viewsets.ViewSet):
    """Authentication API endpoints."""

    def create(self, request):
        """Login endpoint."""
        return Response({'success': True})

class SettingsViewSet(viewsets.ViewSet):
    """Settings management API endpoints."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get user settings."""
        return Response({'settings': {}})