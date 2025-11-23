from django.urls import path
from .views import (
    ChatListCreateView,
    ChatDetailView,
    MessageQueryView
)

urlpatterns = [
    # Chat endpoints
    path('chats/', ChatListCreateView.as_view(), name='chat-list-create'),
    path('chats/<str:chat_id>/', ChatDetailView.as_view(), name='chat-detail'),
    # Message/Query endpoints
    path('chats/<str:chat_id>/query/', MessageQueryView.as_view(), name='message-query'),
]
