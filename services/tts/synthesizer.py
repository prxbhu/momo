"""
TTS Synthesizer Wrapper using edge-tts
"""
import os
import io
import torch
import asyncio
import soundfile as sf
from pocket_tts import TTSModel
import tempfile
import scipy.io.wavfile

LANGUAGE = os.getenv("TTS_LANGUAGE", "en")

class VoiceSynthesizer:
    def __init__(self):
        print("[TTS] Initializing pocket-tts synthesizer...")
        # A good default English voice
        self.voice = os.getenv("TTS_VOICE", "alba")
        self.model = TTSModel.load_model()
        self.voice_state = self.model.get_state_for_audio_prompt(self.voice)
        self.sample_rate = self.model.sample_rate

    def _synthesize_sync(self, text: str) -> bytes:
        """Generate WAV bytes synchronously."""
        audio = self.model.generate_audio(self.voice_state, text)

        # Create an in-memory bytes buffer
        wav_buffer = io.BytesIO()

        # Write the WAV data directly into the buffer
        scipy.io.wavfile.write(
            wav_buffer,
            self.model.sample_rate,
            audio.detach().cpu().numpy(),
        )

        # Get the raw bytes from the buffer
        wav_bytes = wav_buffer.getvalue()
        wav_buffer.close()
        
        return wav_bytes

    async def synthesize(self, text: str) -> bytes:
        """Returns WAV file bytes for the given text using Pocket TTS."""
        return await asyncio.to_thread(self._synthesize_sync, text)
