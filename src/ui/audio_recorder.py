#using pyaudio to capture the audio

import pyaudio
import wave 
import requests
import tempfile
import os
import json 
from typing import Optional, Dict, Any 

class AudioRecorder:
    ### handles audio recording operations 
    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.frames = []
        self.stream = None
        self.audio = pyaudio.PyAudio()

    def start_recording(self):
        ### start recording the audio and return temporary file path
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        # save the audio data to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        wf = wave.open(temp_file.name, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        return temp_file.name
    

    def record_frame(self):
        # record a single frame of audio
        if self.stream:
            data = self.stream.read(self.chunk)
            self.frames.append(data)

    def cleanup(self):
        ### clean up audio resources
        self.audio.terminate()

class FileManager:
    # handle file operations
    #     
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Remove temporary file safely"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Warning: Could not remove temp file {file_path}: {e}")

class NetworkClient:
    """Handles network communication with backend services"""
    
    def __init__(self, transcribe_url: str = "http://127.0.0.1:7777/transcribe", 
                 inference_url: str = "http://127.0.0.1:8000/inference"):
        self.transcribe_url = transcribe_url
        self.inference_url = inference_url
    
    def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Send audio file for transcription"""
        with open(audio_file_path, 'rb') as audio_file:
            files = {'file': ('audio.wav', audio_file, 'audio/wav')}
            response = requests.post(self.transcribe_url, files=files, timeout=30)
        
        if not response.ok:
            raise Exception(f'Transcription failed: {response.status_code}')
        
        return response.json()
    
    def get_sign_language_video(self, text: str) -> Dict[str, Any]:
        """Get sign language video for given text"""
        inference_data = {'text': text}
        
        response = requests.post(
            self.inference_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(inference_data),
            timeout=30
        )
        
        if not response.ok:
            raise Exception(f'Inference failed: {response.status_code}')
        
        return response.json()