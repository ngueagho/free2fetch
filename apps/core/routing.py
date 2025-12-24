"""
WebSocket routing for real-time updates.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/download-progress/<uuid:download_id>/', consumers.DownloadProgressConsumer.as_asgi()),
    path('ws/user-notifications/<int:user_id>/', consumers.UserNotificationConsumer.as_asgi()),
    path('ws/download-control/<uuid:download_id>/', consumers.DownloadControlConsumer.as_asgi()),
    path('ws/global-stats/<int:user_id>/', consumers.GlobalStatsConsumer.as_asgi()),
    path('ws/logger/', consumers.LoggerConsumer.as_asgi()),
]