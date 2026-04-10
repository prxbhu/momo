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

from transcriber import Transcriber
from audio_utils import VoiceActivityDetector

app = FastAPI()
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3030")
WAKE_WORD = "hey momo"

transcriber = Transcriber()
vad = VoiceActivityDetector()

def get_or_create_session():
    # In a real app we might reuse session if recent, matching on UI
    return str(uuid.uuid4())

async def listen_loop():
    print(f"[ASR] Listening for wake word '{WAKE_WORD}'...")
    async for segment in vad.stream():
        audio_array = np.array(segment.numpy_audio, dtype=np.float32).flatten() 
        text = transcriber.transcribe(audio_array)
        print(f"[ASR Debug] Heard: '{text}'")
        lower = text.lower()
        if WAKE_WORD in lower:
            print(f"[ASR] Wake word detected in: '{text}'!")
            # Extract everything after wake word
            try:
                utterance = lower.split(WAKE_WORD, 1)[-1].strip()
            except ValueError:
                utterance = ""
                
            if utterance:
                print(f"[ASR] Sending utterance to orchestrator: '{utterance}'")
                session_id = get_or_create_session()
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"{ORCHESTRATOR_URL}/api/transcribe",
                            json={"text": utterance, "session_id": session_id},
                            timeout=30.0
                        )
                except httpx.RequestError as e:
                     print(f"[ASR] Failed to reach orchestrator: {e}")

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
