"""
Core application URLs.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main application views
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginPageView.as_view(), name='login'),
    path('register/', views.RegisterPageView.as_view(), name='register'),

    # Dashboard sections
    path('courses/', views.CoursesView.as_view(), name='courses'),
    path('downloads/', views.DownloadsView.as_view(), name='downloads'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('logger/', views.LoggerView.as_view(), name='logger'),

    # HTMX endpoints
    path('htmx/course-card/<int:course_id>/', views.CourseCardView.as_view(), name='course_card'),
    path('htmx/download-card/<uuid:download_id>/', views.DownloadCardView.as_view(), name='download_card'),
    path('htmx/progress-bar/<uuid:download_id>/', views.ProgressBarView.as_view(), name='progress_bar'),
    path('htmx/subtitle-modal/<int:course_id>/', views.SubtitleModalView.as_view(), name='subtitle_modal'),
]