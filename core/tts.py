import subprocess
import sounddevice as sd
import threading
import queue
import asyncio

# --- Config ---
PIPER_PATH = r"C:\Users\Krish\piper\piper.exe"
MODEL_PATH = r"C:\Users\Krish\piper\models\en_GB-jarvis-medium.onnx"
CONFIG_PATH = r"C:\Users\Krish\piper\models\en_GB-jarvis-medium.onnx.json"
SAMPLE_RATE = 22050
BLOCK_SIZE = 512

class AsyncPiperTTS:
    def __init__(self):
        self.text_queue = queue.Queue()
        self.running = False
        self.interrupted = False
        self.process = None
        self.audio_thread = None
        self.input_thread = None
        self._interrupt_event = threading.Event()
        self.is_speaking = False

    def start(self):
        """Start the persistent Piper process"""
        if self.running:
            return

        command = [
            PIPER_PATH,
            "-m", MODEL_PATH,
            "-c", CONFIG_PATH,
            "--output_raw",
            "--output_streaming",
            "--length_scale", "0.9",
            "--sentence_silence", "0.05"
        ]

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0
            )

            self.running = True
            print("🎵 [TTS] Ready")

            # Start background threads
            self.input_thread = threading.Thread(target=self._feed_text, daemon=True)
            self.audio_thread = threading.Thread(target=self._play_audio, daemon=True)
            self.input_thread.start()
            self.audio_thread.start()
            
        except Exception as e:
            print(f"❌ [TTS] Failed to start: {e}")

    def _feed_text(self):
        """Feed text to Piper process"""
        while self.running:
            try:
                text = self.text_queue.get(timeout=0.1)
                if text is None or not self.process:
                    continue
                
                if self._interrupt_event.is_set():
                    continue
                
                if self.process.poll() is not None:
                    continue
                    
                self.process.stdin.write((text + "\n").encode("utf-8"))
                self.process.stdin.flush()
            except queue.Empty:
                continue
            except Exception:
                pass

    def _play_audio(self):
        """Play audio with interruption checking"""
        try:
            with sd.RawOutputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype='int16',
                channels=1,
                latency='low'
            ) as stream:
                while self.running and self.process and self.process.poll() is None:
                    if self._interrupt_event.is_set():
                        self.is_speaking = False
                        return

                    data = self.process.stdout.read(BLOCK_SIZE * 2)
                    if not data:
                        if self.interrupted:
                            self.interrupted = False
                            continue
                        elif not self.text_queue.empty():
                            continue
                        else:
                            continue
                    
                    if self._interrupt_event.is_set():
                        continue
                        
                    stream.write(data)
                    self.is_speaking = True
                    
        except Exception:
            pass
        finally:
            self.is_speaking = False

    def interrupt_playback(self):
        """Interrupt current playback and restart TTS"""
        print("🔇 [TTS] Interrupted")
        
        try:
            # Set interrupt flags
            self._interrupt_event.set()
            self.interrupted = True
            self.is_speaking = False
            
            # Clear queue
            while not self.text_queue.empty():
                try:
                    self.text_queue.get_nowait()
                except:
                    break
            
            # Restart in separate thread
            restart_thread = threading.Thread(target=self._restart_engine, daemon=True)
            restart_thread.start()
                
        except Exception:
            pass
    
    def _restart_engine(self):
        """Restart TTS engine"""
        try:
            print("🔄 [TTS] Restarting...")
            
            # Kill process
            if self.process:
                try:
                    self.process.kill()
                    self.process = None
                except:
                    pass
            
            # Reset state
            self.running = False
            self.interrupted = False
            self._interrupt_event.clear()
            self.is_speaking = False
            
            # Restart
            self.start()
            print("✅ [TTS] Ready")
                
        except Exception:
            pass

    def speak(self, text):
        """Queue text to speak"""
        if not self.running:
            self.start()
            
        if self.running and self.process and self.process.poll() is None:
            self.text_queue.put(text)

    async def speak_sentence_immediate(self, text):
        """Async wrapper for immediate speaking"""
        if text.strip():
            self.speak(text.strip())

    async def stop_current_synthesis(self):
        """Async wrapper for interruption"""
        self.interrupt_playback()

    def stop(self):
        """Stop TTS engine"""
        self.running = False
        self._interrupt_event.set()
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except Exception:
                pass
            self.process = None

    async def shutdown(self):
        """Async shutdown"""
        self.stop()
