from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from faster_whisper import WhisperModel
import tempfile
import os
from pathlib import Path

app = FastAPI()

# Initialize Faster Whisper model
print("Loading Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Model loaded successfully!")

# Serve the HTML file
@app.get("/")
async def get():
    html_path = Path(__file__).parent / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established")
    
    try:
        while True:
            # Receive audio data from frontend (now as WAV)
            audio_data = await websocket.receive_bytes()
            
            # Save audio data to temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name
            
            try:
                # Transcribe audio using faster_whisper
                segments, info = model.transcribe(
                    temp_audio_path,
                    language="en",
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                
                # Collect transcribed text
                transcribed_text = ""
                for segment in segments:
                    transcribed_text += segment.text
                
                # Send transcribed text back to frontend
                if transcribed_text.strip():
                    await websocket.send_json({
                        "text": transcribed_text.strip()
                    })
                    print(f"Transcribed: {transcribed_text.strip()}")
                
            except Exception as e:
                print(f"Transcription error: {e}")
                await websocket.send_json({
                    "text": "",
                    "error": str(e)
                })
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                    
    except WebSocketDisconnect:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"Error: {e}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)