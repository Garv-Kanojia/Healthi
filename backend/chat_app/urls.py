from django.urls import path
from .views import (
    ChatListCreateView,
    ChatDetailView
)

urlpatterns = [
    # Chat endpoints
    path('chats/', ChatListCreateView.as_view(), name='chat-list-create'),
    path('chats/<str:chat_id>/', ChatDetailView.as_view(), name='chat-detail'),
]