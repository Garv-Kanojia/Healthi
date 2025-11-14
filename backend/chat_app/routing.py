"""
WebSocket URL routing for chat_app.
Defines WebSocket endpoints for real-time features.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/transcribe/<str:chat_id>/', consumers.TranscriptionConsumer.as_asgi()),
]
