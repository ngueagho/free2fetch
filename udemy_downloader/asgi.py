"""
ASGI config for udemy_downloader project.
It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import apps.core.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'udemy_downloader.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.core.routing.websocket_urlpatterns
        )
    ),
})