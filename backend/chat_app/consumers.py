"""
WebSocket consumer for real-time audio transcription using Hugging Face Space.
Receives 16kHz audio chunks from frontend and transcribes them in real-time.
"""

import json
import tempfile
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from gradio_client import Client, handle_file


# Initialize Hugging Face Client for transcription (private space requires token)
HF_TOKEN = os.environ.get("HF_TOKEN")
print("Initializing Hugging Face Client for transcription...")
HF_CLIENT = Client("Megatron14/Audio_Transcription", hf_token=HF_TOKEN)
print("Hugging Face Client initialized successfully!")


class TranscriptionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for audio transcription.
    Handles real-time audio streaming and transcription using Hugging Face Space.
    """
    
    async def connect(self):
        """
        Handle WebSocket connection.
        Verify user authentication and chat ownership before accepting.
        """
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close(code=4001)  # Unauthorized
            return
        
        # Verify chat exists and belongs to user
        try:
            self.chat = await self.get_chat()
        except Exception as e:
            print(f"Chat verification failed: {e}")
            await self.close(code=4004)  # Not found
            return
        
        # Accept WebSocket connection
        await self.accept()
        print(f"WebSocket connected: User {self.user.email}, Chat {self.chat_id}")
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        """
        print(f"WebSocket disconnected: User {self.user.email}, Code {close_code}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages from WebSocket.
        Expects audio data as bytes (16kHz WAV format).
        """
        if bytes_data:
            # Process audio data and transcribe
            result = await self.transcribe_audio(bytes_data)
            
            # Send transcription result back to client
            await self.send(text_data=json.dumps(result))
        else:
            # Handle text messages if needed
            await self.send(text_data=json.dumps({
                'error': 'Expected audio data as bytes'
            }))
    
    def call_hf_api(self, file_path):
        """
        Call Hugging Face Space API to transcribe audio.
        
        Args:
            file_path: Path to the audio file to transcribe
        
        Returns:
            str: Transcription result or error message
        """
        try:
            # The api_name depends on your Gradio app, usually /predict
            result = HF_CLIENT.predict(
                audio_filepath=handle_file(file_path),
                api_name="/predict"
            )
            return result
        except Exception as e:
            return str(e)
    
    async def transcribe_audio(self, audio_data):
        """
        Transcribe audio data using Hugging Face Space API.
        Saves audio to temporary file, sends to HF Space, and cleans up.
        
        Args:
            audio_data: Audio bytes in WAV format (16kHz)
        
        Returns:
            dict: Transcription result with 'text' or 'error'
        """
        temp_audio_path = None
        
        try:
            # Save audio data to temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name
            
            # Transcribe using HF Space API in thread pool (blocking operation)
            transcribed_text = await asyncio.to_thread(
                self.call_hf_api,
                temp_audio_path
            )
            
            # Check if result is an error message
            if transcribed_text and not transcribed_text.startswith("Error"):
                return {
                    'text': transcribed_text.strip() if isinstance(transcribed_text, str) else str(transcribed_text).strip(),
                    'chat_id': self.chat_id
                }
            else:
                return {
                    'text': '',
                    'error': transcribed_text
                }
        
        except Exception as e:
            print(f"Transcription error: {e}")
            return {
                'text': '',
                'error': str(e)
            }
        
        finally:
            # Clean up temporary file
            if temp_audio_path:
                try:
                    os.unlink(temp_audio_path)
                except Exception as e:
                    print(f"Failed to delete temp file: {e}")
    
    @database_sync_to_async
    def get_chat(self):
        """
        Retrieve chat from database and verify ownership.
        """
        from chat_app.models import Chat
        return Chat.objects.get(chat_id=self.chat_id, user=self.user)