"""
TTS Service - FastAPI App
Takes text in, streams WAV bytes out.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from synthesizer import VoiceSynthesizer

app = FastAPI()

try:
    synthesizer = VoiceSynthesizer()
except Exception as e:
    print(f"[TTS] Startup error: {e}")
    synthesizer = None

class SpeakBody(BaseModel):
    text: str

@app.post("/speak")
async def speak(body: SpeakBody):
    """Body: { "text": "..." } — returns audio/wav"""
    if synthesizer is None:
         raise HTTPException(status_code=500, detail="VoiceSynthesizer failed to initialize. Check voice samples existence.")
         
    if not body.text:
         raise HTTPException(status_code=400, detail="Text cannot be empty.")
         
    try:
         print(f"[TTS] Request to synthesize: '{body.text}'")
         wav_bytes = await synthesizer.synthesize(body.text)
         return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "synthesizer_loaded": bool(synthesizer)}
