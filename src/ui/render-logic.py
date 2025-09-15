from dataclasses import dataclass
from typing import Optional, Callable
import threading
from kivy.clock import Clock

@dataclass
class RecordingState:
    """Application state management"""
    is_recording: bool = False
    is_processing: bool = False
    audio_data: Optional[bytes] = None
    transcribed_text: str = ""
    sign_video_url: Optional[str] = None

class SpeechToSignController:
    """Main controller handling business logic"""
    
    def __init__(self):
        self.state = RecordingState()
        self.audio_recorder = AudioRecorder()
        self.network_client = NetworkClient()
        self.file_manager = FileManager()
        self.recording_thread = None
        
        # Callback functions for UI updates
        self.on_recording_start: Optional[Callable] = None
        self.on_recording_stop: Optional[Callable] = None
        self.on_processing_start: Optional[Callable] = None
        self.on_processing_complete: Optional[Callable] = None
        self.on_processing_error: Optional[Callable] = None
    
    def can_start_recording(self) -> bool:
        """Check if recording can be started"""
        return not self.state.is_recording and not self.state.is_processing
    
    def can_stop_recording(self) -> bool:
        """Check if recording can be stopped"""
        return self.state.is_recording
    
    def start_recording(self):
        """Start audio recording"""
        if not self.can_start_recording():
            return
        
        self.state.is_recording = True
        self.audio_recorder.start_recording()
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._record_audio_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        # Notify UI
        if self.on_recording_start:
            self.on_recording_start()
    
    def stop_recording(self):
        """Stop audio recording and start processing"""
        if not self.can_stop_recording():
            return
        
        self.state.is_recording = False
        
        # Notify UI
        if self.on_recording_stop:
            self.on_recording_stop()
        
        # Save audio file and start processing
        audio_file_path = self.audio_recorder.stop_recording()
        self._start_processing(audio_file_path)
    
    def reset_state(self):
        """Reset application state"""
        self.state = RecordingState()
        self.audio_recorder.stop_recording()
    
    def cleanup(self):
        """Clean up resources"""
        self.audio_recorder.cleanup()
    
    def _record_audio_loop(self):
        """Internal method for recording audio frames"""
        while self.state.is_recording:
            self.audio_recorder.record_frame()
    
    def _start_processing(self, audio_file_path: str):
        """Start audio processing in background thread"""
        self.state.is_processing = True
        
        # Notify UI
        if self.on_processing_start:
            self.on_processing_start()
        
        # Process audio in background thread
        processing_thread = threading.Thread(
            target=self._process_audio,
            args=(audio_file_path,)
        )
        processing_thread.daemon = True
        processing_thread.start()
    
    def _process_audio(self, audio_file_path: str):
        """Process audio file through transcription and inference"""
        try:
            # Step 1: Transcribe audio
            transcribe_data = self.network_client.transcribe_audio(audio_file_path)
            transcribed_text = transcribe_data.get('transcribedText', '')
            
            # Step 2: Get sign language video
            inference_result = self.network_client.get_sign_language_video(transcribed_text)
            
            # Prepare results
            final_text = inference_result.get('input', transcribed_text)
            video_url = f"http://127.0.0.1:8000/{inference_result.get('stitched_video', '')}"
            
            # Update state and notify UI on main thread
            Clock.schedule_once(
                lambda dt: self._on_processing_success(final_text, video_url),
                0
            )
            
        except Exception as e:
            print(f'Error processing audio: {e}')
            Clock.schedule_once(
                lambda dt: self._on_processing_failure(str(e)),
                0
            )
        finally:
            # Clean up temporary file
            self.file_manager.cleanup_temp_file(audio_file_path)
    
    def _on_processing_success(self, transcribed_text: str, video_url: str):
        """Handle successful processing"""
        self.state.is_processing = False
        self.state.transcribed_text = transcribed_text
        self.state.sign_video_url = video_url
        
        if self.on_processing_complete:
            self.on_processing_complete(transcribed_text, video_url)
    
    def _on_processing_failure(self, error_message: str):
        """Handle processing failure"""
        self.state.is_processing = False
        
        if self.on_processing_error:
            self.on_processing_error(error_message)

