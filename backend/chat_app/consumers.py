"""
WebSocket consumer for real-time audio transcription using Faster Whisper.
Receives 16kHz audio chunks from frontend and transcribes them in real-time.
"""

import json
import tempfile
import os
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from faster_whisper import WhisperModel

# Initialize Faster Whisper model globally (loaded once at startup)
print("Loading Whisper model for transcription...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Whisper model loaded successfully!")


class TranscriptionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for audio transcription.
    Handles real-time audio streaming and transcription using Faster Whisper.
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
    
    async def transcribe_audio(self, audio_data):
        """
        Transcribe audio data using Faster Whisper.
        Saves audio to temporary file, transcribes, and cleans up.
        
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
            
            # Transcribe using Faster Whisper in thread pool (blocking operation)
            segments, info = await asyncio.to_thread(
                whisper_model.transcribe,
                temp_audio_path,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Collect transcribed text from segments
            transcribed_text = "".join([segment.text for segment in segments])
            
            print(f"Transcribed: {transcribed_text.strip()}")
            
            return {
                'text': transcribed_text.strip(),
                'chat_id': self.chat_id
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
