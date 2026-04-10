import sounddevice as sd
import numpy as np

# Change this to the index number you found in Step 1!
# If you leave it as None, it uses the system default.
TEST_DEVICE_ID = None 

def audio_callback(indata, frames, time, status):
    volume = np.linalg.norm(indata) * 10
    if volume > 0.5:
        print(f"🎤 Hearing audio! Volume level: {volume:.2f}")

print("Listening for 10 seconds... Speak now!")
with sd.InputStream(device=TEST_DEVICE_ID, callback=audio_callback):
    sd.sleep(10000)