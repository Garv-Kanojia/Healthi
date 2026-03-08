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
from .Services.file_extractor import extract_text_from_pdf, ocr_from_preprocessed_image
import base64
import tempfile
import os
import requests
import json
import dotenv
dotenv.load_dotenv()


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
        chat = get_object_or_404(Chat.objects.prefetch_related('messages__files'), chat_id=chat_id, user=request.user)
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
            # Capture data needed for background task
            # Import task locally to avoid potential circular import or loading issues
            from .tasks import delete_chat_remains

            # We pass email and chat_id to the task
            username = request.user.email
            
            # Trigger background cleanup for vectors/heavy data
            delete_chat_remains.delay(chat_id, username)
            
            # Delete chat (cascade will delete messages and files from Postgres immediately)
            chat.delete()
            
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


def file_cleaned_output(text):
    """
    Clean and structure the extracted text.
    """
    prompt = f"""
Your task is to clean the medical data and return it in a structured format strictly retaining all the information. 

Input: {text}
    """

    try:
        response = requests.post(
            url="https://lightning.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('LIGHTNING_API_KEY')}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "google/gemini-2.5-flash",
                "messages": [
                {
                    "role": "user",
                    "content": [{ "type": "text", "text": prompt }]
                },
                ],
            })
        )
        response.raise_for_status()
        return json.loads(response.content)['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error in file cleaning: {e}")
        return text  # Return original text if cleaning fails


class ChatInteractionView(APIView):
    """
    POST: Send a message to the chat and get a response (replaces WebSocket)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        chat = get_object_or_404(Chat, chat_id=chat_id, user=request.user)
        
        query = request.data.get('query')
        files = request.data.get('files', [])

        if not query:
            return Response({
                'success': False,
                'error': 'Query is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Initialize RAG service
            rag = rag_service(chat_id=chat.chat_id, username=request.user.email)

            # Retrieve the very last message based on created_at
            last_message = chat.messages.order_by('-created_at').first()
            file_response_text = ""
            
            # Create message with placeholder response initially
            with transaction.atomic():
                message = Message.objects.create(chat=chat)
                message.set_content(prompt=query, response="")
                message.save()
                
                # Handle file attachments
                if files:
                    processed_outputs = []
                    for file_data in files:
                        file_name = file_data.get('name')
                        file_content = file_data.get('content') # Base64 string
                        
                        if file_name and file_content:
                            # Determine file type
                            file_extension = file_name.split('.')[-1].lower()
                            file_type = 'pdf' if file_extension == 'pdf' else 'image'
                            
                            # Save filename only (with extension)
                            MessageFile.objects.create(
                                message=message,
                                file_name=file_name
                            )
                            
                            # Process file content
                            try:
                                # Decode base64 content
                                if ',' in file_content:
                                    file_content = file_content.split(',')[1]
                                decoded_content = base64.b64decode(file_content)
                                
                                # Create temp file
                                suffix = f".{file_extension}" if file_extension else ""
                                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                                    temp_file.write(decoded_content)
                                    temp_file_path = temp_file.name
                                
                                # Extract text
                                extracted_text = ""
                                if file_type == 'pdf':
                                    extracted_text = extract_text_from_pdf(temp_file_path)
                                else:
                                    extracted_text = ocr_from_preprocessed_image(temp_file_path)
                                    
                                if extracted_text:
                                    processed_outputs.append(f"File: {file_name}\nContent: {extracted_text}")
                                else:
                                    processed_outputs.append(f"File: {file_name}\nContent: [No text extracted]")
                                    
                                # Clean up
                                if os.path.exists(temp_file_path):
                                    os.remove(temp_file_path)
                                    
                            except Exception as e:
                                print(f"Error processing file {file_name}: {e}")
                                processed_outputs.append(f"File: {file_name}\nError: Failed to process file")
                    
                    if processed_outputs:
                        file_response_text = file_cleaned_output("File Data\n\n".join(processed_outputs))
                        rag.add_file_to_memory(file_response_text)
                        print("File Response created and added to memory")

            # Determine if this is first query or follow-up
            if last_message is None:
                response_text = rag.first_query(query, patient_info=chat.patient_info, file_response=file_response_text)
            else:
                # Get last message for short-term memory
                short_term_memory = ""
                content = last_message.get_content()
                short_term_memory = f"User: {content.get('prompt', '')}\n\nAssistant: {content.get('response', '')}"
                
                response_text = rag.followup_query(query, short_term_memory, file_response=file_response_text)
            
            # Update message with actual response
            message.set_content(prompt=query, response=response_text)
            message.save()
            
            return Response({
                'success': True,
                'message': {
                    'prompt': query,
                    'response': response_text,
                    'created_at': message.created_at.isoformat()
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Chat interaction error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)