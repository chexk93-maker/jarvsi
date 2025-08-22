# Real AudioToTextRecorder implementation using RealtimeSTT
import threading
import time
import numpy as np
from typing import Callable, Optional

try:
    # Try to import the real RealtimeSTT library
    from RealtimeSTT import AudioToTextRecorder as RealAudioToTextRecorder
    REALTIME_STT_AVAILABLE = True
    print("[AudioToTextRecorder] Real RealtimeSTT library found")
except ImportError:
    print("[AudioToTextRecorder] RealtimeSTT library not found, using fallback")
    REALTIME_STT_AVAILABLE = False

class AudioToTextRecorder:
    """Real AudioToTextRecorder implementation using RealtimeSTT library"""
    
    def __init__(self, **kwargs):
        # Store configuration
        self.model = kwargs.get('model', 'small.en')
        self.realtime_model_type = kwargs.get('realtime_model_type', 'base.en')
        self.language = kwargs.get('language', 'en')
        self.use_microphone = kwargs.get('use_microphone', True)
        self.enable_realtime_transcription = kwargs.get('enable_realtime_transcription', True)
        self.debug_mode = kwargs.get('debug_mode', False)
        
        print(f"[AudioToTextRecorder] Initializing with model: {self.model}")
        
        if REALTIME_STT_AVAILABLE:
            try:
                # Initialize the real RealtimeSTT recorder
                self.recorder = RealAudioToTextRecorder(
                    model=self.model,
                    realtime_model_type=self.realtime_model_type,
                    language=self.language,
                    use_microphone=self.use_microphone,
                    enable_realtime_transcription=self.enable_realtime_transcription,
                    
                    # Pass through all other kwargs
                    **{k: v for k, v in kwargs.items() if k not in [
                        'model', 'realtime_model_type', 'language', 
                        'use_microphone', 'enable_realtime_transcription'
                    ]}
                )
                self.is_real_stt = True
                print("[AudioToTextRecorder] Real RealtimeSTT recorder initialized successfully")
            except Exception as e:
                print(f"[AudioToTextRecorder] Failed to initialize real STT: {e}")
                print("[AudioToTextRecorder] Falling back to mock implementation")
                self.is_real_stt = False
                self._init_fallback()
        else:
            print("[AudioToTextRecorder] Using fallback implementation")
            self.is_real_stt = False
            self._init_fallback()
    
    def _init_fallback(self):
        """Initialize fallback mock implementation"""
        self.is_recording = False
        self.last_text = ""
        print("[AudioToTextRecorder] Fallback mock implementation initialized")
    
    def text(self) -> str:
        """Get transcribed text"""
        if self.is_real_stt:
            try:
                # Use the real RealtimeSTT recorder
                result = self.recorder.text()
                if self.debug_mode and result:
                    print(f"[AudioToTextRecorder] Real STT returned: '{result}'")
                return result
            except Exception as e:
                if self.debug_mode:
                    print(f"[AudioToTextRecorder] Real STT error: {e}")
                return ""
        else:
            # Fallback mock implementation
            if not self.is_recording:
                self.is_recording = True
                time.sleep(1)  # Simulate recording time
                self.is_recording = False
            
            time.sleep(0.1)
            return ""
    
    def stop(self):
        """Stop recording"""
        if self.is_real_stt:
            try:
                if hasattr(self.recorder, 'stop'):
                    self.recorder.stop()
                print("[AudioToTextRecorder] Real STT stopped")
            except Exception as e:
                print(f"[AudioToTextRecorder] Error stopping real STT: {e}")
        else:
            self.is_recording = False
            print("[AudioToTextRecorder] Mock STT stopped")
