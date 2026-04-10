"""
TTS audio format utils
"""
import io
import wave
import torch
import torchaudio
import numpy as np

def wav_to_pcm(wav_bytes: bytes) -> bytes:
    """Properly extracts raw PCM data from WAV bytes regardless of header size."""
    try:
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav_file:
            return wav_file.readframes(wav_file.getnframes())
    except wave.Error:
        # Fallback if it's already headerless or malformed
        return wav_bytes

def convert_sample_rate(audio_bytes: bytes, orig_sr: int, target_sr: int) -> bytes:
    """
    Converts sample rate of raw PCM audio bytes.
    Expects 16-bit PCM bytes.
    """
    if orig_sr == target_sr:
        return audio_bytes
        
    # Convert bytes to tensor
    audio_arr = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    waveform = torch.from_numpy(audio_arr).unsqueeze(0)  # shape (1, T)
    
    # Resample using torchaudio
    resampler = torchaudio.transforms.Resample(orig_freq=orig_sr, new_freq=target_sr)
    resampled_waveform = resampler(waveform)
    
    # Convert back to PCM bytes
    resampled_arr = (resampled_waveform.squeeze().numpy() * 32767.0).astype(np.int16)
    return resampled_arr.tobytes()
