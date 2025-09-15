from .logic import SpeechToSignController
from .ui_components import SpeechToSignUI

from kivy.app import App

class SpeechToSignLanguageApp(App):
    """Main Kivy application"""
    
    def build(self):
        self.controller = SpeechToSignController()
        self.ui = SpeechToSignUI(self.controller)
        return self.ui
    
    def on_stop(self):
        """Clean up resources when app stops"""
        if hasattr(self, 'controller'):
            self.controller.cleanup()

def main():
    """Entry point for the application"""
    SpeechToSignLanguageApp().run()

if __name__ == '__main__':
    main()
