import time
import threading
import asyncio
from core.RealtimeSTT import AudioToTextRecorder

class AsyncOptimizedSTT:
    def __init__(self, on_transcription_callback=None):
        self.on_transcription_callback = on_transcription_callback
        self.is_running = False
        self.last_transcription = ""
        self.stop_event = threading.Event()
        
        print("[INFO] Initializing async RealtimeSTT with optimized settings...")
        
        # Optimized for your hardware: 512MB VRAM, 8GB RAM
        self.recorder = AudioToTextRecorder(
            model="small.en",                    
            realtime_model_type="base.en",       
            language="en",
            use_microphone=True,
            enable_realtime_transcription=True,
            
            # Performance optimizations
            silero_use_onnx=True,
            silero_deactivity_detection=True,
            faster_whisper_vad_filter=True,
            
            # Force float32 to avoid warnings
            compute_type="float32",
            
            # Accuracy settings
            beam_size=5,
            realtime_processing_pause=0.03,      
            
            # Voice detection tuning - BALANCED
            silero_sensitivity=0.08,              # Balanced sensitivity
            post_speech_silence_duration=0.5,    # Balanced silence duration
            min_length_of_recording=0.4,         # Balanced minimum recording
            min_gap_between_recordings=0.2,      # Balanced gap
            
            # Clean output
            debug_mode=False,                     
            no_log_file=True,
            spinner=False
        )
        
        print("[INFO] Async RealtimeSTT initialized successfully")
    
    async def start_listening(self):
        """Start continuous listening - ALWAYS ACTIVE"""
        self.is_running = True
        self.stop_event.clear()
        print("[INFO] Jarvis async STT listening started...")
        print(f"[STT DEBUG] Callback function set: {self.on_transcription_callback is not None}")
        
        # Start in separate thread so it NEVER gets blocked
        self.transcription_thread = threading.Thread(target=self._transcription_worker_sync, daemon=True)
        self.transcription_thread.start()
        print("[STT DEBUG] Transcription thread started")
        
        # Return a task that runs forever
        return asyncio.create_task(self._keep_alive())
    
    def _transcription_worker_sync(self):
        """SYNCHRONOUS transcription worker - runs in separate thread"""
        print("[STT DEBUG] Transcription worker thread started")
        while self.is_running and not self.stop_event.is_set():
            try:
                print("[STT DEBUG] Waiting for speech...")
                # This is BLOCKING but runs in separate thread
                text = self.recorder.text()
                print(f"[STT DEBUG] Recorder returned: '{text}'")
                
                if not self.is_running or self.stop_event.is_set():
                    break
                
                if text and text.strip() and text != self.last_transcription:
                    self.last_transcription = text
                    print(f"[STT DEBUG] New transcription detected: '{text.strip()}'")
                    
                    # Call callback SYNCHRONOUSLY
                    if self.on_transcription_callback:
                        try:
                            print(f"[STT DEBUG] Calling callback with: '{text.strip()}'")
                            self.on_transcription_callback(text.strip())
                        except Exception as e:
                            print(f"[ERROR] Callback error: {e}")
                else:
                    print(f"[STT DEBUG] Ignoring empty/duplicate text: '{text}'")
                        
            except Exception as e:
                if self.is_running:
                    print(f"[ERROR] STT error: {e}")
                time.sleep(0.1)
        print("[STT DEBUG] Transcription worker thread stopped")
    
    async def _keep_alive(self):
        """Keep the async task alive"""
        while self.is_running:
            await asyncio.sleep(1)
    
    async def stop_listening(self):
        """Stop listening"""
        print("[INFO] Stopping STT...")
        self.is_running = False
        self.stop_event.set()
        # Ensure underlying recorder releases the microphone device
        try:
            if hasattr(self, 'recorder') and hasattr(self.recorder, 'stop'):
                self.recorder.stop()
        except Exception as e:
            print(f"[WARN] Failed to stop recorder cleanly: {e}")
        
        if hasattr(self, 'transcription_thread') and self.transcription_thread.is_alive():
            self.transcription_thread.join(timeout=2)

# Legacy compatibility function (now async)
async def transcribe_once_async(timeout=3):
    """Async legacy function for compatibility"""
    stt = AsyncOptimizedSTT()
    result_queue = asyncio.Queue()
    
    async def callback(text):
        await result_queue.put(text)
    
    stt.on_transcription_callback = callback
    await stt.start_listening()
    
    try:
        result = await asyncio.wait_for(result_queue.get(), timeout=timeout)
        await stt.stop_listening()
        return result
    except asyncio.TimeoutError:
        await stt.stop_listening()
        return ""

async def main():
    """Test the async STT functionality"""
    def on_transcription(text):
        print(f"[TRANSCRIBED] {text}")
    
    stt = AsyncOptimizedSTT(on_transcription_callback=on_transcription)
    await stt.start_listening()
    
    print("Say something... Press Ctrl+C to stop")
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        await stt.stop_listening()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[EXIT] Program terminated.")
