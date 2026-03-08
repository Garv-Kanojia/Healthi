from django.urls import path
from .views import (
    ChatListCreateView,
    ChatDetailView,
    ChatInteractionView
)

urlpatterns = [
    # Chat endpoints
    path('chats/', ChatListCreateView.as_view(), name='chat-list-create'),
    path('chats/<str:chat_id>/', ChatDetailView.as_view(), name='chat-detail'),
    path('chats/<str:chat_id>/message/', ChatInteractionView.as_view(), name='chat-message'),
]