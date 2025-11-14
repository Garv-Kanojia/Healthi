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
            # Initialize RAG service and destroy chat memory
            rag = rag_service(chat_id=chat.chat_id, username=request.user.email)
            rag.set_up_memoryDB()
            rag.destroy_chat()
            
            # Delete chat (cascade will delete messages and files)
            chat.delete()
            
            return Response({
                'success': True,
                'message': 'Chat deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to delete chat: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessageQueryView(APIView):
    """
    POST: Send a query to the RAG system and get AI response
    Handles both first message and follow-up messages
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, chat_id):
        """Process user query and return AI response."""
        chat = get_object_or_404(Chat, chat_id=chat_id, user=request.user)
        
        serializer = MessageQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        files = serializer.validated_data.get('files', [])
        
        try:
            # Initialize RAG service
            rag = rag_service(chat_id=chat.chat_id, username=request.user.email)
            
            # Retrieve the very last message based on created_at
            last_message = chat.messages.order_by('-created_at').first()
            file_response = None

            # Create and save message
            with transaction.atomic():
                message = Message.objects.create(chat=chat)
                message.set_content(prompt=query, response=response_text)
                message.save()
                
                # Handle file attachments if any
                if files:
                    file_response = self._process_files(message, files)
            
            # Determine if this is first query or follow-up
            if last_message is None:
                # First query - include patient info if available
                response_text = rag.first_query(query, patient_info=chat.patient_info, file_response=file_response)
            else:
                # Follow-up query - retrieve short-term memory
                rag.set_up_memoryDB()
                
                # Get last 3 messages for short-term memory
                recent_messages = chat.messages.order_by('-created_at').first()
                short_term_memory = self._build_short_term_memory(recent_messages)
                
                response_text = rag.followup_query(query, short_term_memory, file_response=file_response)
            
            # Return response
            return Response({
                'success': True,
                'message': {
                    'prompt': query,
                    'response': response_text,
                    'created_at': message.created_at
                }
            }, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to process query: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _build_short_term_memory(self, messages):
        """Build short-term memory from recent messages."""
        memory_parts = []
        content = list(messages)[0].get_content()
        memory_parts.append(f"User: {content.get('prompt', '')}")
        memory_parts.append(f"Assistant: {content.get('response', '')}")
        return "\n\n".join(memory_parts)
    
    def _process_files(self, message, files):
        """Process and save file metadata."""
        for file in files:
            # Determine file type
            file_extension = file.name.split('.')[-1].lower()
            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                file_type = 'image'
            elif file_extension == 'pdf':
                file_type = 'pdf'
            else:
                continue  # Skip unsupported files
            
            # Create MessageFile entry
            MessageFile.objects.create(
                message=message,
                file_type=file_type,
                file_name=file.name,
                file_size=file.size
            )

        # I will insert the code where the file goes to the file processing API and the response will be returned accordingly.
        response = ""
        return response