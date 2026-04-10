"""
Moonshine Transcriber wrapper
"""
import os
from moonshine_voice import Transcriber as MoonshineTranscriber
from moonshine_voice import get_model_for_language

class Transcriber:
    def __init__(self):
        print("[ASR] Initializing Moonshine Transcriber...")
        language = "en"
        
        # Download and load models automatically
        model_path, model_arch = get_model_for_language(language)
        self.engine = MoonshineTranscriber(model_path=model_path, model_arch=model_arch)
    
    def transcribe(self, audio_data) -> str:
        """
        Expects audio_data as a numpy array, or appropriate supported format 
        along with matching sample_rate (assumed 16000).
        """
        # We assume sample_rate is 16000 based on standard VAD input
        transcript = self.engine.transcribe_without_streaming(
            audio_data, sample_rate=16000
        )
        
        if not transcript or not transcript.lines:
            return ""
            
        full_text = " ".join(line.text.strip() for line in transcript.lines)
        return full_text
