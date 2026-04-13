"""
ASR Service - FastAPI app
Listens for wake word and provides /transcribe endpoint.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import asyncio
import os
import uuid
import numpy as np
import soundfile as sf
import sounddevice as sd
import time
import base64
import io
import json
import queue
import threading
from transcriber import Transcriber
from audio_utils import VoiceActivityDetector

app = FastAPI()
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3030")
WAKE_WORD = "momo"

transcriber = Transcriber()
vad = VoiceActivityDetector()

def get_or_create_session():
    # In a real app we might reuse session if recent, matching on UI
    return str(uuid.uuid4())

def play_audio_bytes(audio_data: bytes):
    """Decodes and plays raw WAV bytes using sounddevice."""
    try:
        data, fs = sf.read(io.BytesIO(audio_data))
        sd.play(data, fs)
        sd.wait() # Wait for audio to finish before listening again
    except Exception as e:
        print(f"[ASR Error] Failed to play audio: {e}")

def audio_player_worker(audio_queue):
    """Background thread that continuously plays incoming raw PCM chunks."""
    try:
        # pocket-tts default is 24000Hz 
        stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16')
        stream.start()
        
        header_skipped = False
        buffer = b""
        
        while True:
            chunk = audio_queue.get()
            if chunk is None:  # to stop thread
                break
                
            buffer += chunk
            
            # Strip the 44-byte WAV header so we don't hear a click at the start
            if not header_skipped:
                if len(buffer) >= 44:
                    buffer = buffer[44:]
                    header_skipped = True
                else:
                    continue
                    
            if len(buffer) > 0:
                stream.write(buffer)
                buffer = b""
                
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"[ASR Error] Player thread crashed: {e}")

async def send_to_orchestrator(utterance: str):
    print(f"[ASR] Sending query to orchestrator: '{utterance}'")
    session_id = get_or_create_session()
    audio_queue = queue.Queue()
    player_thread = threading.Thread(target=audio_player_worker, args=(audio_queue,))
    player_thread.start()
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{ORCHESTRATOR_URL}/api/transcribe",
                json={"text": utterance, "session_id": session_id},
                timeout=60.0 # Give LLM time to process
            ) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            
                            if "response" in data:
                                print(f"\n🤖 MOMO: {data['response']}\n")
                            elif "audio_chunk" in data:
                                audio_bytes = base64.b64decode(data["audio_chunk"])
                                audio_queue.put(audio_bytes)
                                
                        except json.JSONDecodeError:
                            continue
                else:
                    print(f"[ASR Error] Orchestrator returned status {response.status_code}")
    except httpx.RequestError as e:
         print(f"[ASR Error] Failed to reach orchestrator: {e}")
    audio_queue.put(None)
    await asyncio.to_thread(player_thread.join)
    # finally:
    #     audio_queue.put(None)
    #     player_thread.join()

async def listen_loop():
    print(f"[ASR] Listening for wake word '{WAKE_WORD}'...")
    is_awake = False
    wake_time = 0
    async for segment in vad.stream():
        audio_array = np.array(segment.numpy_audio, dtype=np.float32).flatten() 
        text = transcriber.transcribe(audio_array)
        cleaned_text = text.strip(' .,!?').lower()
        if not cleaned_text:
            continue
        print(f"[ASR Debug] Heard: '{text}'")
        lower = cleaned_text.lower()

        if not is_awake:
            if WAKE_WORD in lower:
                print(f"[ASR] Wake word detected in: '{text}'!")
                is_awake = True
                wake_time = time.time()
                try:
                    notif_path = os.path.join(os.path.dirname(__file__), "notif.wav")
                    if os.path.exists(notif_path):
                        data, fs = sf.read(notif_path)
                        sd.play(data, fs)
                        sd.wait()
                except Exception as e:
                    print(f"[ASR Debug] Could not play notification: {e}")

                # Did they speak the query in the exact same breath? (e.g. "Momo what time is it")
                parts = lower.split(WAKE_WORD, 1)
                utterance = parts[-1].strip(' .,!?') if len(parts) > 1 else ""
                
                if utterance:
                    await send_to_orchestrator(utterance)
                    is_awake = False
                else:
                    print("[ASR] Waiting for your query...")
        else:
            # STATE: AWAKE -> Waiting for Query
            elapsed = time.time() - wake_time
            
            if lower:
                await send_to_orchestrator(text.strip(' .,!?'))
                is_awake = False
            elif elapsed > 15.0:
                print("[ASR] Timeout waiting for query. Going back to sleep.")
                is_awake = False

@app.on_event("startup")
async def startup():
    # Start the background listening task
    asyncio.create_task(listen_loop())

@app.post("/transcribe")
async def transcribe_audio(request: Request):
    """Called externally with raw PCM bytes — returns transcription"""
    audio_bytes = await request.body()
    try:
        text = transcriber.transcribe(audio_bytes)
        return {"text": text}
    except Exception as e:
         return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok"}
