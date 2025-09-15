import kivy
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp

# Relative import within the ui package
from .logic import SpeechToSignController

kivy.require('2.0.0')

class PulsingMicrophone(Widget):
    """Custom microphone widget with pulsing animation"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_recording = False
        self.pulse_animation = None
        
        with self.canvas:
            Color(0.2, 0.6, 1.0, 1.0)  # Blue color
            self.outer_circle = Ellipse(size=(100, 100))
            Color(0.1, 0.4, 0.8, 0.5)  # Semi-transparent blue
            self.pulse_circle = Ellipse(size=(100, 100))
            Color(1, 1, 1, 1)  # White for microphone icon
            self.mic_circle = Ellipse(size=(60, 60))
        
        self.bind(size=self.update_graphics, pos=self.update_graphics)
    
    def update_graphics(self, *args):
        """Update graphic positions"""
        center_x = self.center_x
        center_y = self.center_y
        
        self.outer_circle.pos = (center_x - 50, center_y - 50)
        self.pulse_circle.pos = (center_x - 50, center_y - 50)
        self.mic_circle.pos = (center_x - 30, center_y - 30)
    
    def start_pulse(self):
        """Start pulsing animation"""
        self.is_recording = True
        if self.pulse_animation:
            self.pulse_animation.stop(self)
        
        # Create pulsing animation
        self.pulse_animation = Animation(
            size=(120, 120), duration=0.8
        ) + Animation(
            size=(100, 100), duration=0.8
        )
        self.pulse_animation.repeat = True
        self.pulse_animation.bind(on_progress=self.update_pulse)
        self.pulse_animation.start(self)
    
    def stop_pulse(self):
        """Stop pulsing animation"""
        self.is_recording = False
        if self.pulse_animation:
            self.pulse_animation.stop(self)
        
        # Reset to normal size
        with self.canvas:
            self.canvas.clear()
            Color(0.2, 0.6, 1.0, 1.0)
            self.outer_circle = Ellipse(size=(100, 100))
            Color(1, 1, 1, 1)
            self.mic_circle = Ellipse(size=(60, 60))
        self.update_graphics()
    
    def update_pulse(self, animation, widget, progress):
        """Update pulse animation frame"""
        if self.is_recording:
            pulse_size = 100 + (20 * progress)
            center_x = self.center_x
            center_y = self.center_y
            
            with self.canvas:
                self.canvas.clear()
                Color(0.2, 0.6, 1.0, 1.0)
                self.outer_circle = Ellipse(
                    size=(100, 100),
                    pos=(center_x - 50, center_y - 50)
                )
                Color(0.1, 0.4, 0.8, 0.3)
                self.pulse_circle = Ellipse(
                    size=(pulse_size, pulse_size),
                    pos=(center_x - pulse_size/2, center_y - pulse_size/2)
                )
                Color(1, 1, 1, 1)
                self.mic_circle = Ellipse(
                    size=(60, 60),
                    pos=(center_x - 30, center_y - 30)
                )

class SpeechToSignUI(BoxLayout):
    """Main UI layout for the Speech to Sign application"""
    
    def __init__(self, controller: SpeechToSignController, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(20)
        self.spacing = dp(20)
        
        self.controller = controller
        self.setup_controller_callbacks()
        self.setup_ui()
        self.bind_keyboard()
    
    def setup_controller_callbacks(self):
        """Set up callbacks for controller events"""
        self.controller.on_recording_start = self.on_recording_start
        self.controller.on_recording_stop = self.on_recording_stop
        self.controller.on_processing_start = self.on_processing_start
        self.controller.on_processing_complete = self.on_processing_complete
        self.controller.on_processing_error = self.on_processing_error
    
    def setup_ui(self):
        """Create UI components"""
        # Header
        header = self.create_header()
        
        # Main content area
        main_content = BoxLayout(orientation='vertical', spacing=dp(20))
        
        # Recording area
        recording_area = self.create_recording_area()
        
        # Results area (initially hidden)
        self.results_area = self.create_results_area()
        
        main_content.add_widget(recording_area)
        main_content.add_widget(self.results_area)
        
        # Footer
        footer = self.create_footer()
        
        self.add_widget(header)
        self.add_widget(main_content)
        self.add_widget(footer)
    
    def create_header(self) -> BoxLayout:
        """Create header section"""
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        
        title = Label(
            text='Speech to Sign Language',
            font_size='24sp',
            size_hint_y=None,
            height=dp(40),
            color=(0.2, 0.2, 0.2, 1)
        )
        
        subtitle = Label(
            text='Hold the spacebar to record your speech',
            font_size='16sp',
            size_hint_y=None,
            height=dp(30),
            color=(0.5, 0.5, 0.5, 1)
        )
        
        header.add_widget(title)
        header.add_widget(subtitle)
        return header
    
    def create_recording_area(self) -> BoxLayout:
        """Create recording area with microphone and status"""
        recording_area = BoxLayout(
            orientation='vertical',
            spacing=dp(20),
            size_hint_y=None,
            height=dp(300)
        )
        
        # Microphone widget
        self.microphone = PulsingMicrophone(size_hint=(None, None), size=(100, 100))
        mic_container = BoxLayout()
        mic_container.add_widget(Widget())  # Spacer
        mic_container.add_widget(self.microphone)
        mic_container.add_widget(Widget())  # Spacer
        
        # Status text
        self.status_label = Label(
            text='Hold spacebar to start recording',
            font_size='16sp',
            size_hint_y=None,
            height=dp(40),
            color=(0.3, 0.3, 0.3, 1)
        )
        
        # Progress bar (initially hidden)
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(10)
        )
        self.progress_bar.opacity = 0
        
        recording_area.add_widget(mic_container)
        recording_area.add_widget(self.status_label)
        recording_area.add_widget(self.progress_bar)
        
        return recording_area
    
    def create_results_area(self) -> BoxLayout:
        """Create results area with transcription and video"""
        results_area = BoxLayout(
            orientation='vertical',
            spacing=dp(15),
            size_hint_y=None,
            height=0
        )
        
        # Transcribed text
        transcription_label = Label(
            text='Transcribed Text:',
            font_size='18sp',
            size_hint_y=None,
            height=dp(30),
            color=(0.2, 0.2, 0.2, 1)
        )
        
        self.transcribed_text = Label(
            text='',
            font_size='16sp',
            text_size=(None, None),
            halign='left',
            size_hint_y=None,
            height=dp(60),
            color=(0.1, 0.1, 0.1, 1)
        )
        
        # Video player
        video_label = Label(
            text='Sign Language Video:',
            font_size='18sp',
            size_hint_y=None,
            height=dp(30),
            color=(0.2, 0.2, 0.2, 1)
        )
        
        self.video_player = VideoPlayer(
            size_hint_y=None,
            height=dp(250),
            state='stop'
        )
        
        # Reset button
        self.reset_button = Button(
            text='Record Again',
            size_hint_y=None,
            height=dp(50),
            background_color=(0.2, 0.6, 1.0, 1),
            color=(1, 1, 1, 1)
        )
        self.reset_button.bind(on_press=self.reset_app)
        
        results_area.add_widget(transcription_label)
        results_area.add_widget(self.transcribed_text)
        results_area.add_widget(video_label)
        results_area.add_widget(self.video_player)
        results_area.add_widget(self.reset_button)
        
        return results_area
    
    def create_footer(self) -> Label:
        """Create footer section"""
        return Label(
            text='Press and hold the spacebar to record your speech',
            font_size='14sp',
            size_hint_y=None,
            height=dp(30),
            color=(0.4, 0.4, 0.4, 1)
        )
    
    def bind_keyboard(self):
        """Bind keyboard events"""
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)
    
    def on_key_down(self, window, key, scancode, codepoint, modifier):
        """Handle key down events"""
        if key == 32:  # Spacebar
            self.controller.start_recording()
        return True
    
    def on_key_up(self, window, key, scancode):
        """Handle key up events"""
        if key == 32:  # Spacebar
            self.controller.stop_recording()
        return True
    
    # Controller callback implementations
    def on_recording_start(self):
        """Handle recording start"""
        self.microphone.start_pulse()
        self.status_label.text = 'Recording... Release spacebar to stop'
        self.status_label.color = (1, 0.2, 0.2, 1)  # Red color
    
    def on_recording_stop(self):
        """Handle recording stop"""
        self.microphone.stop_pulse()
    
    def on_processing_start(self):
        """Handle processing start"""
        self.status_label.text = 'Processing audio...'
        self.status_label.color = (0.2, 0.6, 1.0, 1)  # Blue color
        self.progress_bar.opacity = 1
        self.animate_progress()
    
    def on_processing_complete(self, transcribed_text: str, video_url: str):
        """Handle processing completion"""
        self.status_label.text = 'Processing complete!'
        self.status_label.color = (0.2, 0.8, 0.2, 1)  # Green color
        
        self.transcribed_text.text = transcribed_text
        self.transcribed_text.text_size = (self.width - dp(40), None)
        
        # Load video
        if video_url:
            self.video_player.source = video_url
            self.video_player.state = 'play'
        
        # Show results area
        self.results_area.height = dp(400)
        self.results_area.opacity = 1
        self.progress_bar.opacity = 0
    
    def on_processing_error(self, error_message: str):
        """Handle processing error"""
        self.status_label.text = 'Error processing audio. Try again.'
        self.status_label.color = (1, 0.2, 0.2, 1)  # Red color
        self.progress_bar.opacity = 0
    
    def animate_progress(self):
        """Animate progress bar during processing"""
        def update_progress(dt):
            if self.controller.state.is_processing:
                self.progress_bar.value = (self.progress_bar.value + 5) % 100
                return True
            else:
                self.progress_bar.opacity = 0
                self.progress_bar.value = 0
                return False
        
        Clock.schedule_interval(update_progress, 0.1)
    
    def reset_app(self, button):
        """Reset application to initial state"""
        # Reset controller state
        self.controller.reset_state()
        
        # Reset UI
        self.status_label.text = 'Hold spacebar to start recording'
        self.status_label.color = (0.3, 0.3, 0.3, 1)
        self.transcribed_text.text = ''
        self.video_player.source = ''
        self.video_player.state = 'stop'
        self.results_area.height = 0
        self.results_area.opacity = 0
        self.progress_bar.opacity = 0
        self.microphone.stop_pulse()