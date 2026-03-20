"""
WebSocket consumer for real-time audio transcription using local faster-whisper.
Receives 16kHz audio chunks from frontend and transcribes them in real-time.
"""

import json
import tempfile
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from faster_whisper import WhisperModel


# Initialize faster-whisper locally
print("Initializing local faster-whisper model...")
# Using 'base' model by default for real-time performance. You can change this to 'small' or 'medium' for better accuracy.
# Make sure to update device to 'cuda' and compute_type to 'float16' if you're running on a GPU.
WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
print("Local faster-whisper model initialized successfully!")


class TranscriptionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for audio transcription.
    Handles real-time audio streaming and transcription using local faster-whisper.
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
    
    def call_local_whisper(self, file_path):
        """
        Call local faster-whisper model to transcribe audio.
        
        Args:
            file_path: Path to the audio file to transcribe
        
        Returns:
            str: Transcription result or error message
        """
        try:
            segments, info = WHISPER_MODEL.transcribe(file_path, beam_size=5)
            text = " ".join([segment.text for segment in segments])
            return text
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def transcribe_audio(self, audio_data):
        """
        Transcribe audio data using local faster-whisper model.
        Saves audio to temporary file, transcribes using local model, and cleans up.
        
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
            
            # Transcribe using local model in thread pool (blocking operation)
            transcribed_text = await asyncio.to_thread(
                self.call_local_whisper,
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