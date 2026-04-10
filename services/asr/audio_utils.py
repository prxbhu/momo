"""
Audio utilities for capturing mic, VAD, and openWakeWord.
"""
import asyncio
import numpy as np
import sounddevice as sd
import torch

class VoiceActivityDetector:
    def __init__(self, sample_rate=16000, frame_duration=32):
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration
        self.chunk_size = int(sample_rate * frame_duration / 1000)  # 512 for 16kHz
        
        print("[VAD] Loading Silero VAD from PyTorch Hub...")
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True
        )
        self.get_speech_timestamps = utils[0]
        self.model.eval()

    async def stream(self):
        """Yields audio segments when voice activity is detected."""
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"[VAD warning] {status}")
            loop.call_soon_threadsafe(queue.put_nowait, indata.copy())
            
        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=self.chunk_size,
            callback=audio_callback
        )
        
        buffer = []
        is_speaking = False
        silence_threshold = 1.0  # seconds of silence to trigger end of speech
        silence_frames = 0
        max_silence_frames = int(silence_threshold / (self.frame_duration / 1000))
        
        print("[VAD] Listening for voice activity...")
        with stream:
            while True:
                chunk = await queue.get()
                
                # Check VAD (requires tensor shape [chunk_size])
                tensor_chunk = torch.from_numpy(chunk).squeeze()
                
                with torch.no_grad():
                    speech_prob = self.model(tensor_chunk, self.sample_rate).item()
                
                if speech_prob > 0.5:
                    if not is_speaking:
                        print("[VAD] Speech started")
                        is_speaking = True
                    silence_frames = 0
                    buffer.append(chunk)
                else:
                    if is_speaking:
                        silence_frames += 1
                        buffer.append(chunk) 
                        if silence_frames > max_silence_frames:
                            print("[VAD] Speech ended")
                            is_speaking = False
                            
                            audio_data = np.concatenate(buffer, axis=0)
                            buffer = []
                            silence_frames = 0
                            
                            class Segment:
                                def __init__(self, data):
                                    # Useful for streaming or passing to ASR
                                    int16_data = (data * 32767).astype(np.int16)
                                    self.audio = int16_data.tobytes()
                                    self.numpy_audio = data
                            
                            yield Segment(audio_data)
