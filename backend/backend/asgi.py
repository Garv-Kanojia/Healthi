"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/

IMPORTANT: os.environ.setdefault + get_asgi_application() MUST be called
before any Django app imports (middleware, routing, models) to ensure the
app registry is fully initialized before WebSocket connections arrive.
"""

import os
from django.core.asgi import get_asgi_application

# Step 1: Set settings env var FIRST — before any Django app imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Step 2: Initialize Django — fully populates the app registry
django_asgi_app = get_asgi_application()

# Step 3: NOW safe to import Django app-specific modules
from channels.routing import ProtocolTypeRouter, URLRouter
from chat_app.middleware import JWTAuthMiddleware
from chat_app.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
