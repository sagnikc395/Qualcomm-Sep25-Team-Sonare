
"""
UI Package for Speech to Sign Language Application

A Kivy-based user interface for converting speech to sign language videos.
"""

__version__ = "1.0.0"

from .main import SpeechToSignLanguageApp, main
from .logic import SpeechToSignController, RecordingState
from .ui_components import PulsingMicrophone, SpeechToSignUI
from .io_operations import AudioRecorder, NetworkClient, FileManager

__all__ = [
    'SpeechToSignLanguageApp',
    'main',
    'SpeechToSignController', 
    'RecordingState',
    'PulsingMicrophone',
    'SpeechToSignUI',
    'AudioRecorder',
    'NetworkClient',
    'FileManager'
]