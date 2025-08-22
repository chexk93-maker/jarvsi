import asyncio
import queue
import numpy as np
import sounddevice as sd
import json
import traceback
import time
from core.stt import AsyncOptimizedSTT
from core.tts import AsyncPiperTTS
from core.tools import get_all_tools, get_all_handlers, handle_tool_call
from tools.reminder import register_speaker, get_reminder_system
from prompts import get_system_prompt
import ollama
from tools.memory import recall_memory
import re

# --- Config ---
SAMPLE_RATE = 16000
ENERGY_THRESHOLD = 0.0005  # Same as your backup
BLOCK_SIZE = int(SAMPLE_RATE * 0.25)

# Model options for different hardware capabilities
MODEL_OPTIONS = {
    "fast": "qwen2.5:3b-instruct-q4_1",          # Fast, good for conversation, moderate function calling
    "balanced": "qwen2.5:7b",      # Best balance of speed and function calling
    "accurate": "llama3.2:3b",     # Alternative with good function calling
    "current": "qwen2.5:3b-instruct-q4_1"        # Currently selected model
}


"""
Pattern-based tool routing removed. The LLM will decide when to call tools.
"""

class JarvisCore:
    def __init__(self):
        self.stt_queue = queue.Queue()
        self.tts_engine = None
        self.stt = None
        
        # Improved interruption flags
        self.interrupt_flag = False
        self.is_speaking = False
        self.is_listening = True
        self.llm_generation_active = False
        self.conversation_lock = asyncio.Lock()
        
        # Audio-based interruption (like your backup)
        self.audio_queue = queue.Queue()
        self.audio_stream = None
        
        # Interruption detection
        self.last_user_input_time = 0
        self.response_start_time = 0
                
        # Correctly load all tools and handlers
        self.all_tools = get_all_tools()
        self.all_handlers = get_all_handlers()

        # For short-term context
        self.last_action_summary = None
        
        # Initialize UI callbacks for web interface integration
        self.on_stream_callback = None
        self.on_user_text_callback = None
        self.on_final_answer_callback = None
        
        # Microphone state control
        self.mic_enabled = True  # Default to enabled for standalone mode
        
        # Conversation history for short-term context across non-tool chats
        self.conversation_history = []  # List[Dict[role, content]] of recent turns
        self.max_history_messages = 4   # Keep the last N messages (user/assistant)
        
    def energy(self, audio):
        """Calculate audio energy - same as your backup"""
        return np.linalg.norm(audio) / len(audio)
    
    def audio_callback(self, indata, frames, time_info, status):
        """Real-time audio callback for interruption detection"""
        if status:
            print(f"[!] Audio Error: {status}")
        
        # Store audio for STT processing
        self.audio_queue.put(indata.copy())
        
        # IMMEDIATE interruption on audio energy
        current_energy = self.energy(indata)
        

        
        if (self.is_speaking or self.llm_generation_active) and current_energy > ENERGY_THRESHOLD:
            print(f"\n⚠️  [INTERRUPT] User speaking")
            self.interrupt_flag = True
            self.is_speaking = False
            self.llm_generation_active = False
            
            # Stop TTS immediately
            if self.tts_engine:
                self.tts_engine.interrupt_playback()
    
    async def start(self):
        """Initialize and start all components"""
        print("🤖 [INIT] Initializing Jarvis components...")
        
        # Initialize TTS
        self.tts_engine = AsyncPiperTTS()
        self.tts_engine.start()
        
        # Initialize STT with improved callback
        self.stt = AsyncOptimizedSTT(on_transcription_callback=self.stt_callback_sync)
        
        # Show available tools - ADD MORE DEBUG
        tools = get_all_tools()
        handlers = get_all_handlers()
        print(f"🔧 [TOOLS] Available tools: {[tool['function']['name'] for tool in tools]}")
        print(f"🔧 [HANDLERS] Available handlers: {list(handlers.keys())}")
        
        # Debug: Print full tool definitions
        for tool in tools:
            print(f"🔧 [TOOL DEBUG] {tool['function']['name']}: {tool['function']['description']}")
        
        # Build tasks: queue processor always runs; audio/STT only if mic enabled
        tasks = [self.stt_queue_processor()]
        if self.mic_enabled:
            self.audio_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=BLOCK_SIZE,
                callback=self.audio_callback
            )
            self.audio_stream.start()
            print("🎧 [LISTENING] Jarvis is listening... Say something!")
            tasks.insert(0, self.stt.start_listening())

        # Start background processors
        # Register TTS as reminder speaker
        try:
            register_speaker(lambda text: self.tts_engine.text_queue.put(text))
        except Exception:
            pass

        # Start proactive monitoring loop
        tasks.append(self._proactive_monitor_loop())

        await asyncio.gather(*tasks)
    
    def stt_callback_sync(self, text):
        """Synchronous STT callback - handles interruption detection"""
        current_time = time.time()
        
        print(f"🎤 [STT DEBUG] Callback triggered! Text: '{text}', mic_enabled: {self.mic_enabled}")
        
        # Check if microphone is enabled - if not, ignore the input
        if not self.mic_enabled:
            print(f"🎤 [MIC] Microphone disabled - ignoring input: '{text}'")
            return
        
        print(f"🎤 [MIC] Received input: '{text}'")
        
        # Detect interruption: user spoke while Jarvis was responding
        if (self.is_speaking or self.llm_generation_active) and (current_time - self.response_start_time) > 1.0:
            print(f"\n⚠️  [INTERRUPT] '{text}'")
            self.interrupt_flag = True
            self.is_speaking = False
            self.llm_generation_active = False
            
            # Stop TTS immediately
            if self.tts_engine:
                self.tts_engine.interrupt_playback()
        
        self.last_user_input_time = current_time
        self.stt_queue.put(text)
        print(f"🎤 [STT DEBUG] Text added to queue")
    
    async def stt_queue_processor(self):
        """Process STT queue with improved interruption handling"""
        while True:
            try:
                # Non-blocking queue check
                try:
                    transcribed_text = self.stt_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                # Skip if microphone is disabled
                if not self.mic_enabled:
                    continue

                # Immediately notify UI of user text before any processing
                try:
                    if hasattr(self, 'on_user_text_callback') and self.on_user_text_callback:
                        self.on_user_text_callback(transcribed_text)
                except Exception:
                    pass

                # Skip if currently processing (unless it's an interruption)
                if self.llm_generation_active and not self.interrupt_flag:
                    continue
                
                # Process the transcription
                async with self.conversation_lock:
                    await self.process_user_input(transcribed_text)
                
            except Exception as e:
                print(f"❌ [ERROR] Queue processor error: {e}")
                await asyncio.sleep(0.1)
    
    async def process_user_input(self, transcribed_text):
        """Process user input with memory integration"""
        
        print(f"\n👤 [USER]: {transcribed_text}")
        print("🤖 [JARVIS]: ", end="", flush=True)
        
        # UI notification happens in stt_queue_processor for immediacy
        
        # Reset flags
        self.interrupt_flag = False
        self.is_listening = False
        self.is_speaking = False
        self.llm_generation_active = False
        self.response_start_time = time.time()
        
        # Generate and speak response with memory context
        response = await self.generate_and_speak_response_async(transcribed_text)
        
        # Final answer callback is handled in generate_and_speak_response_async
        
        # Reset state after response
        self.interrupt_flag = False
        self.is_speaking = False
        self.llm_generation_active = False
        self.is_listening = True
        
        if self.mic_enabled:
            print("\n🎧 [LISTENING] Jarvis is listening...")
    
    async def process_text_input_directly(self, text):
        """Process text input directly from web interface"""
        # Process text input directly, bypassing microphone state check
        async with self.conversation_lock:
            await self.process_user_input(text)
    
    async def process_web_text_input(self, text):
        """Process text input from web interface without triggering user text callback"""
        
        print(f"\n👤 [USER]: {text}")
        print("🤖 [JARVIS]: ", end="", flush=True)
        
        # DON'T call the user text callback for web input - it's already shown in UI
        
        # Reset flags
        self.interrupt_flag = False
        self.is_listening = False
        self.is_speaking = False
        self.llm_generation_active = False
        self.response_start_time = time.time()
        
        # Generate and speak response with memory context
        response = await self.generate_and_speak_response_async(text)
        
        # Reset state after response
        self.interrupt_flag = False
        self.is_speaking = False
        self.llm_generation_active = False
        self.is_listening = True
        
        if self.mic_enabled:
            print("\n🎧 [LISTENING] Jarvis is listening...")

    async def generate_and_speak_response_async(self, user_text):
        """Generate LLM response with improved interruption handling and memory awareness"""
        original_user_text = user_text  # Preserve raw user text for history
        self.interrupt_flag = False
        self.llm_generation_active = True
        
        try:
            # Inject last action context if it exists
            if self.last_action_summary:
                print(f"🧠 [CONTEXT] Injecting last action: {self.last_action_summary}")
                user_text = f"Based on your last action ({self.last_action_summary}), the user now says: {user_text}"
                self.last_action_summary = None # Clear after use

            # Step 1: Recall relevant memories from long-term storage
            recalled_context = await recall_memory(user_text)
            
            # Step 2: Generate the system prompt with the recalled context
            enhanced_system_prompt = get_system_prompt(self.all_tools, recalled_context)

            # Prepare messages with rolling conversation history for better context
            messages = self._build_messages_with_history(enhanced_system_prompt, user_text)
            tools = self.all_tools

            # Streaming loop to handle tool calls and stream content to TTS
            while True:
                try:
                    stream = ollama.chat(
                        model=MODEL_OPTIONS["current"],
                        messages=messages,
                        tools=tools,
                        stream=True,
                        options={
                            "temperature": 0.1,
                            "top_p": 0.9,
                            "top_k": 40,
                            "num_predict": 300,
                        }
                    )
                except Exception as e:
                    print(f"❌ [LLM ERROR] Failed to create Ollama stream: {e}")
                    return "I'm sorry, I encountered an error generating a response."

                assistant_content = ""
                accumulated_chunk = ""
                tool_calls = []
                last_message = None
                
                for chunk in stream:
                    if self.interrupt_flag:
                        print("\n⚠️ [INTERRUPT] Breaking stream due to interruption")
                        break
                    
                    msg = chunk.get("message", {})
                    last_message = msg or last_message
                    content = msg.get("content", "")
                    
                    chunk_tool_calls = msg.get("tool_calls", [])
                    if chunk_tool_calls:
                        tool_calls.extend(chunk_tool_calls)
                    
                    if content:
                        print(content, end="", flush=True)
                        assistant_content += content
                        accumulated_chunk += content
                        
                        if self.on_stream_callback:
                            self.on_stream_callback(content)
                        
                        if not self._looks_like_json_tool_call(accumulated_chunk):
                            if any(punct in accumulated_chunk for punct in ['.', '!', '?', ',', ';', '\n']):
                                cleaned_chunk = self.clean_text_for_tts(accumulated_chunk.strip())
                                if cleaned_chunk:
                                    self.is_speaking = True
                                    self.tts_engine.text_queue.put(cleaned_chunk)
                                accumulated_chunk = ""
                
                if accumulated_chunk.strip() and not self._looks_like_json_tool_call(accumulated_chunk):
                    cleaned_chunk = self.clean_text_for_tts(accumulated_chunk.strip())
                    if cleaned_chunk:
                        self.is_speaking = True
                        self.tts_engine.text_queue.put(cleaned_chunk)
                
                if last_message and last_message.get("tool_calls"):
                    tool_calls = last_message.get("tool_calls")
                
                if tool_calls:
                    messages.append({"role": "assistant", "content": assistant_content, "tool_calls": tool_calls})
                    
                    # Prepare calls
                    prepared_calls = []
                    for call in tool_calls:
                        func = call.get("function", {})
                        tool_name = func.get("name")
                        tool_args = func.get("arguments", {})
                        prepared_calls.append((tool_name, tool_args))

                    # Immediate spoken feedback (sequential for clarity)
                    for tool_name, tool_args in prepared_calls:
                        await self.provide_immediate_feedback(tool_name, tool_args)

                    # Execute tools concurrently to reduce latency
                    tasks = [asyncio.create_task(handle_tool_call(tn, ta)) for tn, ta in prepared_calls]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Append tool results back to the model in the same order as calls
                    tool_summaries = []
                    for (tool_name, tool_args), result in zip(prepared_calls, results):
                        if isinstance(result, Exception):
                            result_str = f"Error executing {tool_name}: {str(result)}"
                        else:
                            result_str = str(result) if result is not None else ""
                        messages.append({
                            "role": "tool",
                            "content": result_str,
                            "name": tool_name,
                        })
                        print(f"🔧 [TOOL] {tool_name} completed: {result_str[:100]}...")
                        tool_summaries.append(f"Tool: {tool_name}, Arguments: {tool_args}")

                    # Create and store the detailed summary for the next turn
                    self.last_action_summary = "; ".join(tool_summaries)

                    continue

                print()
                self.llm_generation_active = False
                
                if not assistant_content.strip():
                    fallback_response = "I'm here and ready to help. What would you like me to do?"
                    assistant_content = fallback_response
                    cleaned_fallback = self.clean_text_for_tts(fallback_response)
                    if cleaned_fallback:
                        self.is_speaking = True
                        self.tts_engine.text_queue.put(cleaned_fallback)
                
                if self.on_final_answer_callback:
                    self.on_final_answer_callback(assistant_content)
                
                # Store this exchange into short-term history for future context
                self._append_exchange_to_history(original_user_text, assistant_content)
                
                return assistant_content
            
        except Exception as e:
            print(f"❌ [ERROR] Response generation error: {e}")
            traceback.print_exc()
        finally:
            self.llm_generation_active = False
            self.is_speaking = False

    def _build_messages_with_history(self, system_prompt, current_user_text):
        """Build the messages list including recent conversation turns for context."""
        messages = [{"role": "system", "content": system_prompt}]
        # Only keep the most recent messages to fit model context
        if self.conversation_history:
            messages.extend(self.conversation_history[-self.max_history_messages:])
        messages.append({"role": "user", "content": current_user_text})
        return messages

    def _append_exchange_to_history(self, user_text, assistant_text):
        """Append the latest user/assistant exchange to rolling history and trim size."""
        if user_text:
            self.conversation_history.append({"role": "user", "content": user_text})
        if assistant_text:
            self.conversation_history.append({"role": "assistant", "content": assistant_text})
        # Trim to the last N messages
        if len(self.conversation_history) > self.max_history_messages:
            self.conversation_history = self.conversation_history[-self.max_history_messages:]


    async def provide_immediate_feedback(self, tool_name, args):
        """Provide immediate feedback before tool execution"""
        feedback_phrases = {
            "maximize_or_minimize_window": {
                "maximize": f"Maximizing the {args.get('title_keyword', 'window')} window for you, Sir.",
                "minimize": f"Minimizing the {args.get('title_keyword', 'window')} window, Sir."
            },
            "switch_window": "Switching to the next window, Sir.",
            "toggle_desktop": "Toggling desktop view, Sir.",
            "open_app": f"Opening {args.get('app_title', 'application')} for you, Sir.",
            "close_app": f"Closing {args.get('window_title', 'application')}, Sir.",
            "manage_folder": "Managing the folder as requested, Sir.",
            "manage_file": "Processing the file operation, Sir.",
            "play_music": f"Searching for {args.get('song_name', 'that song')} on YouTube, Sir.",
            "set_timer": "Setting a timer for you, Sir.",
            "set_reminder": "Setting that reminder, Sir.",
            "google_search": f"Searching the web for {args.get('query', 'that')}, Sir.",
            "get_weather": f"Getting the weather for {args.get('city', 'your location')}, Sir."
        }
        
        if tool_name in feedback_phrases:
            if isinstance(feedback_phrases[tool_name], dict):
                action = args.get('action', 'maximize')
                feedback = feedback_phrases[tool_name].get(action, "Processing your request, Sir.")
            else:
                feedback = feedback_phrases[tool_name]
            
            # Speak immediately
            print(f"🔊 [IMMEDIATE] {feedback}")
            self.is_speaking = True
            self.tts_engine.text_queue.put(feedback)
            await asyncio.sleep(0.3)  # Brief pause for natural flow

    def _looks_like_json_tool_call(self, text):
        """Check if text looks like a JSON tool call"""
        if not text:
            return False
        
        text = text.strip()
        # Check for common JSON tool call patterns
        return (
            text.startswith('{') or 
            text.startswith('```json') or
            ('"name"' in text and '"parameters"' in text) or
            ('{{"name":' in text.replace(' ', ''))
        )
    
    def clean_text_for_tts(self, text):
        """Clean text for better TTS pronunciation"""
        if not text:
            return ""
        
        # Remove URLs completely - they sound terrible when read aloud
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
        
        # Remove reference links and numbered lists that contain URLs
        text = re.sub(r'\d+\.\s*[^\n]*(?:http|www)[^\n]*', '', text)
        text = re.sub(r'For more details.*?visit.*?links?:.*', 'For more information, you can visit the provided links.', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove emojis and technical symbols
        text = re.sub(r'[🚀🎵🌤️✅❌🗑️📂🔧🔍🎧👤🤖⚠️🔊]', '', text)
        
        # Remove punctuation that sounds bad when read
        text = text.replace(' - ', ' ')
        text = text.replace('--', ' ')
        text = text.replace('...', ' ')
        text = re.sub(r'\[\d+\]', '', text)  # Remove reference numbers like [1], [2]
        
        # Remove technical punctuation that doesn't make sense when spoken
        text = re.sub(r'[{}]', '', text)  # Remove curly braces
        text = re.sub(r'\\', '', text)    # Remove backslashes
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        
        # Fix common pronunciation issues
        replacements = {
            'm/s': 'meters per second',
            'km/h': 'kilometers per hour',
            'ft/s': 'feet per second',
            '°C': 'degrees Celsius',
            '°F': 'degrees Fahrenheit',
            '%': 'percent',
            '&': 'and',
            '@': 'at',
            '#': 'hash',
        }
        
        # Apply replacements
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        return text.strip()
    
    async def shutdown(self):
        """Gracefully shutdown all components"""
        print("🚪 [SHUTDOWN] Stopping Jarvis...")
        
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
        
        if self.stt:
            await self.stt.stop_listening()
        
        if self.tts_engine:
            self.tts_engine.stop()
        
        print("✅ [SHUTDOWN] Jarvis stopped successfully")

    async def _proactive_monitor_loop(self):
        """Background loop for proactive assistance (battery, reminders pre-alerts)."""
        battery_warned_levels = set()
        reminder_prealerted = set()  # holds (reminder_id, threshold_min)
        
        while True:
            try:
                # Battery monitor (Windows via psutil if available)
                try:
                    import psutil
                    batt = psutil.sensors_battery()
                    if batt is not None:
                        percent = int(batt.percent)
                        plugged = batt.power_plugged
                        for threshold in (20, 15, 10, 5):
                            key = (threshold, plugged)
                            if percent <= threshold and key not in battery_warned_levels and not plugged:
                                message = f"Sir, battery is at {percent} percent. Please plug in to avoid interruptions."
                                print(f"🔋 [BATTERY] {message}")
                                if self.tts_engine:
                                    self.tts_engine.text_queue.put(message)
                                battery_warned_levels.add(key)
                        # Reset if charging
                        if plugged:
                            battery_warned_levels.clear()
                except Exception:
                    pass

                # Reminder pre-alerts (15m/5m/1m)
                try:
                    from datetime import datetime
                    reminder_system = get_reminder_system()
                    active = reminder_system.get_active_reminders()
                    now = datetime.now()
                    for r in active:
                        rid = r.get('id')
                        rtime = r.get('time')
                        if not rid or not rtime:
                            continue
                        remaining = (rtime - now).total_seconds()
                        for minutes in (15, 5, 1):
                            thresh = minutes * 60
                            key = (rid, minutes)
                            if 0 < remaining <= thresh and key not in reminder_prealerted:
                                msg = f"Sir, reminder in {minutes} minutes: {r.get('task', '')}."
                                print(f"⏰ [REMINDER PRE] {msg}")
                                if self.tts_engine:
                                    self.tts_engine.text_queue.put(msg)
                                reminder_prealerted.add(key)
                except Exception:
                    pass

                await asyncio.sleep(15)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(15)

    async def enable_microphone(self):
        """Enable microphone: start audio stream and STT listener"""
        if self.mic_enabled:
            return
        self.mic_enabled = True
        # Start audio stream if not present
        if self.audio_stream is None:
            self.audio_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=BLOCK_SIZE,
                callback=self.audio_callback
            )
            self.audio_stream.start()
        # Start STT if available and not running
        if self.stt and not getattr(self.stt, 'is_running', False):
            await self.stt.start_listening()
        print("🎧 [MIC] Microphone enabled - capturing resumed")

    async def disable_microphone(self):
        """Disable microphone: stop audio stream and STT listener"""
        if not self.mic_enabled:
            return
        self.mic_enabled = False
        # Stop STT listener
        if self.stt and getattr(self.stt, 'is_running', False):
            await self.stt.stop_listening()
        # Stop and release audio stream
        if self.audio_stream is not None:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None
        print("🎤 [MIC] Microphone disabled - capturing stopped")

if __name__ == "__main__":
    try:
        asyncio.run(JarvisCore().start())
    except KeyboardInterrupt:
        print("\n🚪 [EXIT] Program terminated.")
