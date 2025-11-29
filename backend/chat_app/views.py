from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Chat, Message, MessageFile
from .serializers import (
    ChatSerializer, 
    ChatDetailSerializer, 
    ChatCreateSerializer,
    MessageQuerySerializer
)
from .Services.rag import rag_service


class ChatListCreateView(APIView):
    """
    GET: List all chats for the authenticated user
    POST: Create a new chat (max 3 per user)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all chats for the user."""
        chats = Chat.objects.filter(user=request.user).order_by('-created_at')
        serializer = ChatSerializer(chats, many=True)
        return Response({
            'success': True,
            'chats': serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new chat."""
        serializer = ChatCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                chat = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Chat created successfully',
                    'chat': ChatSerializer(chat).data
                }, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ChatDetailView(APIView):
    """
    GET: Retrieve a specific chat with all messages
    PATCH: Update chat name
    DELETE: Delete a chat and its associated memory
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, chat_id):
        """Get chat details with all messages."""
        chat = get_object_or_404(Chat, chat_id=chat_id, user=request.user)
        serializer = ChatDetailSerializer(chat)
        return Response({
            'success': True,
            'chat': serializer.data
        }, status=status.HTTP_200_OK)
    
    def patch(self, request, chat_id):
        """Update chat name."""
        chat = get_object_or_404(Chat, chat_id=chat_id, user=request.user)
        new_name = request.data.get('name')
        if not new_name:
            return Response({
                'success': False,
                'error': 'Name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        chat.name = new_name
        chat.save()
        
        return Response({
            'success': True,
            'message': 'Chat name updated successfully',
            'chat': ChatSerializer(chat).data
        }, status=status.HTTP_200_OK)
    
    def delete(self, request, chat_id):
        """Delete chat and associated long-term memory."""
        chat = get_object_or_404(Chat, chat_id=chat_id, user=request.user)
        
        try:
            # Delete chat (cascade will delete messages and files)
            chat.delete()
            # Initialize RAG service and destroy chat memory
            rag = rag_service(chat_id=chat.chat_id, username=request.user.email)
            rag.set_up_memoryDB()
            rag.destroy_chat()
            
            return Response({
                'success': True,
                'message': 'Chat deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(f"Error deleting chat: {e}")
            return Response({
                'success': False,
                'error': f'Failed to delete chat: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)