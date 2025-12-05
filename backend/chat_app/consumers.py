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
import base64
from chat_app.Services.file_extractor import extract_text_from_pdf, ocr_from_preprocessed_image

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


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for text-based chat using RAG.
    """
    
    async def connect(self):
        """
        Handle WebSocket connection.
        """
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close(code=4001)
            return
        
        try:
            self.chat = await self.get_chat()
        except Exception as e:
            print(f"Chat verification failed: {e}")
            await self.close(code=4004)
            return

        # ✅ Initialize RAG service ONCE when websocket connects
        self.rag = None
            
        await self.accept()
        print(f"Chat WebSocket connected: User {self.user.email}, Chat {self.chat_id}")

    def __init_rag_service(self):
        """Initialize RAG service with ChromaDB (runs in thread)."""
        from chat_app.Services.rag import rag_service
        rag = rag_service(chat_id=self.chat.chat_id, username=self.user.email)
        rag.set_up_memoryDB()
        return rag

    async def disconnect(self, close_code):
        self.rag = None
        print(f"Chat WebSocket disconnected: User {self.user.email}, Code {close_code}")

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages.
        """
        if not self.rag:
            self.rag = await asyncio.to_thread(self.__init_rag_service)
        if text_data:
            try:
                data = json.loads(text_data)
                query = data.get('query')
                files = data.get('files', []) # Expecting list of file objects: {name: "...", content: "base64..."}
                
                if not query:
                    await self.send(text_data=json.dumps({
                        'error': 'Query is required'
                    }))
                    return

                # Process query asynchronously
                response_data = await self.process_query(query, files)
                
                await self.send(text_data=json.dumps(response_data))
                
            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({
                    'error': 'Invalid JSON'
                }))
            except Exception as e:
                print(f"Error processing message: {e}")
                await self.send(text_data=json.dumps({
                    'error': str(e)
                }))

    @database_sync_to_async
    def get_chat(self):
        from chat_app.models import Chat
        return Chat.objects.get(chat_id=self.chat_id, user=self.user)

    async def process_query(self, query, files):
        """
        Process the query using RAG service.
        """
        try:
            # We need to run the blocking RAG operations in a separate thread
            return await asyncio.to_thread(self._sync_process_query, query, files)
        except Exception as e:
            print(f"Query processing error: {e}")
            return {'error': str(e)}

    def _sync_process_query(self, query, files):
        """
        Synchronous method to handle DB operations and RAG service.
        """
        from chat_app.models import Message, MessageFile
        from django.db import transaction

        # Use the pre-initialized RAG service from connect()
        rag = self.rag
        
        # Retrieve the very last message based on created_at
        last_message = self.chat.messages.order_by('-created_at').first()
        file_response_text = ""
        
        # Create message with placeholder response initially
        with transaction.atomic():
            message = Message.objects.create(chat=self.chat)
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
                        
                        # Save metadata only
                        MessageFile.objects.create(
                            message=message,
                            file_type=file_type,
                            file_name=file_name,
                            file_size=len(file_content) # Approximate size from base64
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
                    print("File Response created")


        # Determine if this is first query or follow-up
        if last_message is None:
            response_text = rag.first_query(query, patient_info=self.chat.patient_info, file_response=file_response_text)
        else:
            # memory_db is already set up in connect() via __init_rag_service()
            
            # Get last message for short-term memory
            short_term_memory = ""
            if last_message:
                content = last_message.get_content()
                short_term_memory = f"User: {content.get('prompt', '')}\n\nAssistant: {content.get('response', '')}"
            
            response_text = rag.followup_query(query, short_term_memory, file_response=file_response_text)
        
        # Update message with actual response
        message.set_content(prompt=query, response=response_text)
        message.save()
        
        return {
            'success': True,
            'message': {
                'prompt': query,
                'response': response_text,
                'created_at': message.created_at.isoformat()
            }
        }


def file_cleaned_output(text):
    """
    Clean and structure the extracted text.
    """
    import requests
    import json
    import os
    import dotenv
    dotenv.load_dotenv()

    prompt = f"""
Your task is to clean the medical data and return it in a structured format strictly retaining all the information. 

Input: {text}
    """

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
    return json.loads(response.content)['choices'][0]['message']['content']