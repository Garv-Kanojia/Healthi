"""
WebSocket consumer for real-time audio transcription using AWS Transcribe Streaming.
Receives 16kHz PCM audio chunks from the frontend.

Lifecycle:
  connect    → accept immediately, spin off _open_stream() as a background task
  _open_stream → opens the AWS Transcribe stream; sends {"status":"ready"} on success
                 or {"error":"..."} + close on failure
  receive    → buffer audio until the stream is ready, then forward it
  disconnect → end the stream gracefully, await the reader task
"""

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from decouple import config

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.model import TranscriptEvent


# Use the region set in .env; falls back to us-east-1
AWS_REGION = config('AWS_TRANSCRIBE_REGION', default='us-east-1')

# Size of PCM sub-chunks sent to AWS (16 KB ≈ 0.5s of audio at 16kHz 16-bit)
CHUNK_SIZE = 1024 * 16

# Minimum PCM bytes to bother sending (< 1600 bytes ≈ < 0.05s, likely silence)
MIN_AUDIO_BYTES = 1600

# How long (seconds) to wait for the AWS stream to open before giving up
STREAM_OPEN_TIMEOUT = 15.0


class TranscriptionConsumer(AsyncWebsocketConsumer):

    # ------------------------------------------------------------------ #
    #  Connection lifecycle                                                #
    # ------------------------------------------------------------------ #

    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.user    = self.scope['user']

        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        try:
            self.chat = await self.get_chat()
        except Exception as e:
            print(f"[Transcribe] Chat verification failed: {e}")
            await self.close(code=4004)
            return

        # ✅ Accept IMMEDIATELY — do not block on AWS latency here.
        await self.accept()

        # State initialisation
        self._finals:         list[str] = []
        self._sent_pcm_bytes: int       = 0
        self._stream                    = None   # set by _open_stream()
        self._reader_task               = None
        self._audio_buffer:  list[bytes] = []    # audio received before stream ready

        # Open the AWS stream in the background so the WS stays alive
        self._open_task = asyncio.ensure_future(self._open_stream())

    async def _open_stream(self):
        """
        Opens the AWS Transcribe stream in the background.
        Sends {"status": "ready"} to the frontend when done, or
        {"error": "..."} and closes if something goes wrong.
        Any audio received while this was running is flushed immediately after.
        """
        try:
            client = TranscribeStreamingClient(region=AWS_REGION)
            self._stream = await asyncio.wait_for(
                client.start_stream_transcription(
                    language_code="en-US",
                    media_sample_rate_hz=16000,
                    media_encoding="pcm",
                ),
                timeout=STREAM_OPEN_TIMEOUT,
            )
            print(f"[Transcribe] Stream opened — user={self.user.email} chat={self.chat_id}")
        except asyncio.TimeoutError:
            msg = f"Transcription service timed out (region={AWS_REGION}). Please try again."
            print(f"[Transcribe] {msg}")
            await self._safe_send({'error': msg})
            await self.close()
            return
        except asyncio.CancelledError:
            # WebSocket disconnected while we were still opening — just exit
            return
        except Exception as e:
            print(f"[Transcribe] Failed to open stream: {e}")
            await self._safe_send({'error': f'Could not start transcription: {e}'})
            await self.close()
            return

        # Start the background result-reader
        self._reader_task = asyncio.ensure_future(self._read_results())

        # Tell the frontend it can start sending audio
        await self._safe_send({'status': 'ready'})

        # Flush any audio chunks that arrived while we were connecting
        if self._audio_buffer:
            for buffered in self._audio_buffer:
                await self._forward_audio(buffered)
            self._audio_buffer.clear()

    async def disconnect(self, close_code):
        # Cancel the open-stream task if it's still running
        if hasattr(self, '_open_task') and not self._open_task.done():
            self._open_task.cancel()
            try:
                await self._open_task
            except (asyncio.CancelledError, Exception):
                pass

        # Signal end-of-audio to AWS so it flushes remaining results
        if self._stream is not None:
            try:
                await self._stream.input_stream.end_stream()
            except Exception:
                pass

        # Wait briefly for the reader to finish flushing final segments
        if self._reader_task is not None:
            try:
                await asyncio.wait_for(self._reader_task, timeout=4.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                self._reader_task.cancel()

        print(f"[Transcribe] Disconnected — user={self.user.email} code={close_code}")

    # ------------------------------------------------------------------ #
    #  Receiving audio                                                     #
    # ------------------------------------------------------------------ #

    async def receive(self, text_data=None, bytes_data=None):
        if not bytes_data:
            await self._safe_send({'error': 'Expected binary audio data'})
            return

        if self._stream is None:
            # Stream not ready yet — buffer the chunk and wait
            self._audio_buffer.append(bytes_data)
        else:
            await self._forward_audio(bytes_data)

    async def _forward_audio(self, audio_data: bytes):
        """
        Strip the WAV header (if present) and send ONLY the new PCM tail to AWS.

        The frontend accumulates all recorded audio and re-sends the full
        buffer on every MediaRecorder tick.  We track how many bytes we have
        already forwarded and only send the delta.
        """
        # Strip 44-byte RIFF/WAV header — Transcribe expects raw PCM
        if audio_data[:4] == b'RIFF':
            audio_data = audio_data[44:]

        new_audio = audio_data[self._sent_pcm_bytes:]

        if len(new_audio) < MIN_AUDIO_BYTES:
            return  # Nothing new, or only silence

        for offset in range(0, len(new_audio), CHUNK_SIZE):
            await self._stream.input_stream.send_audio_event(
                audio_chunk=new_audio[offset:offset + CHUNK_SIZE]
            )

        self._sent_pcm_bytes += len(new_audio)

    # ------------------------------------------------------------------ #
    #  Background result reader                                           #
    # ------------------------------------------------------------------ #

    async def _read_results(self):
        """
        Continuously read TranscriptEvents from AWS and push text to the frontend.

        - Partial results: sent immediately for live-typing feedback.
        - Final results:   appended to self._finals; cumulative text is sent.
        """
        try:
            async for event in self._stream.output_stream:
                if not isinstance(event, TranscriptEvent):
                    continue

                for result in event.transcript.results:
                    if not result.alternatives:
                        continue

                    text = result.alternatives[0].transcript.strip()
                    if not text:
                        continue

                    if result.is_partial:
                        live_text = " ".join(self._finals + [text]).strip()
                        await self._safe_send({'text': live_text})
                    else:
                        self._finals.append(text)
                        full_text = " ".join(self._finals).strip()
                        await self._safe_send({'text': full_text, 'chat_id': self.chat_id})

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Transcribe] Reader error: {e}")
            await self._safe_send({'error': str(e)})

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    async def _safe_send(self, data: dict):
        """Send JSON to the client, silently ignoring closed-connection errors."""
        try:
            await self.send(text_data=json.dumps(data))
        except Exception:
            pass

    @database_sync_to_async
    def get_chat(self):
        from chat_app.models import Chat
        return Chat.objects.get(chat_id=self.chat_id, user=self.user)