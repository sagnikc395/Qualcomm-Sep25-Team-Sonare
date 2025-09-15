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
