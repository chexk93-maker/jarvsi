import re
import time
import threading
import tkinter as tk
from typing import Dict, Optional
from win10toast import ToastNotifier

def parse_time_string(time_str: str) -> int:
    """
    Parses a time string like '2hr 34min 78sec' or '200 minutes'
    and returns total seconds.
    """
    time_str = time_str.lower().strip()
    total_seconds = 0
    patterns = {
        "hours": r"(\d+)\s*(h|hr|hrs|hour|hours)",
        "minutes": r"(\d+)\s*(m|min|mins|minute|minutes)",
        "seconds": r"(\d+)\s*(s|sec|secs|second|seconds)"
    }
    hours_match = re.search(patterns["hours"], time_str)
    minutes_match = re.search(patterns["minutes"], time_str)
    seconds_match = re.search(patterns["seconds"], time_str)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60
    if seconds_match:
        total_seconds += int(seconds_match.group(1))
    if total_seconds == 0 and time_str.isdigit():
        # If only a number is provided, treat it as minutes
        total_seconds = int(time_str) * 60
    elif total_seconds == 0:
        # Try to match a simple number
        match = re.match(r'^(\d+)', time_str)
        if match:
            total_seconds = int(match.group(1)) * 60  # Default to minutes
    return total_seconds

class TimerWindow(tk.Toplevel):
    def __init__(self, master, duration_seconds: int, title: str):
        super().__init__(master)
        self.title(title)
        self.geometry("300x150")
        self.configure(bg='#2c3e50')
        self.attributes('-topmost', True)
        self.label = tk.Label(self, text=self.format_time(duration_seconds), font=("Helvetica", 30), fg='white', bg='#2c3e50')
        self.label.pack(pady=20)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.stop_event = threading.Event()

    def format_time(self, seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02}"

    def update_label(self, seconds: int):
        try:
            self.after(0, lambda: self.label.config(text=self.format_time(seconds)))
        except:
            pass

    def on_close(self):
        self.stop_event.set()
        self.destroy()

class TimerSystem:
    def __init__(self):
        self.active_timers: Dict[str, Dict] = {}
        self.timer_counter = 0
        self.notifier = ToastNotifier()

    def _create_timer_window(self, duration_seconds: int, timer_name: str):
        """Create timer window in its own thread with its own event loop"""
        try:
            # Create a new root window for this thread
            root = tk.Tk()
            root.withdraw()  # Hide the main root
            
            # Create the timer window
            window = tk.Toplevel(root)
            window.title("Jarvis Timer")
            window.geometry("350x220")
            window.configure(bg='#2c3e50')
            window.attributes('-topmost', True)
            window.resizable(False, False)
            
            # Center the window
            window.update_idletasks()
            x = (window.winfo_screenwidth() // 2) - (350 // 2)
            y = (window.winfo_screenheight() // 2) - (220 // 2)
            window.geometry(f"350x220+{x}+{y}")
            
            # Time display label (larger, centered)
            time_label = tk.Label(
                window, 
                text=self._format_time(duration_seconds), 
                font=("Arial", 52, "bold"),
                fg='#e74c3c',
                bg='#2c3e50'
            )
            time_label.pack(pady=(30, 10))
            
            # Progress info
            progress_label = tk.Label(
                window,
                text="Timer running...",
                font=("Arial", 11),
                fg='#bdc3c7',
                bg='#2c3e50'
            )
            progress_label.pack(pady=(0, 15))
            
            # Cancel button
            def cancel_timer():
                window.destroy()
                root.destroy()
            
            cancel_btn = tk.Button(
                window,
                text="Cancel Timer",
                command=cancel_timer,
                bg='#e74c3c',
                fg='white',
                font=("Arial", 11, "bold"),
                padx=25,
                pady=8,
                relief='flat',
                cursor='hand2'
            )
            cancel_btn.pack(pady=(0, 20))
            
            # Update function
            remaining = duration_seconds
            def update_timer():
                nonlocal remaining
                if remaining > 0:
                    time_label.config(text=self._format_time(remaining))
                    if remaining <= 10:
                        time_label.config(fg='#f39c12')  # Orange for last 10 seconds
                    if remaining <= 5:
                        time_label.config(fg='#e74c3c')  # Red for last 5 seconds
                    remaining -= 1
                    window.after(1000, update_timer)
                else:
                    # Timer finished
                    time_label.config(text="00:00", fg='#27ae60')  # Green
                    progress_label.config(text="Time's up!", fg='#27ae60')
                    cancel_btn.config(text="Close", bg='#27ae60')
                    
                    # Auto-close after 10 seconds
                    window.after(10000, lambda: (window.destroy(), root.destroy()))
            
            # Start the timer update
            window.after(1000, update_timer)
            
            # Show the window
            window.deiconify()
            window.focus_force()
            
            # Start the event loop for this window
            root.mainloop()
            
        except Exception as e:
            print(f"⚠️ [TIMER] Window creation error: {e}")

    def _run_timer(self, duration: int, name: str, window: Optional[TimerWindow]):
        """Internal method to run a single timer thread."""
        remaining_seconds = duration
        print(f"⏰ [TIMER] Started: {name} ({self._format_time(duration)})")
        
        while remaining_seconds > 0:
            # Check if window exists and if it was cancelled
            if window and window.stop_event.is_set():
                print(f"Timer '{name}' cancelled by closing window.")
                if name in self.active_timers:
                    del self.active_timers[name]
                return
            
            # Update window if it exists
            if window:
                try:
                    window.update_label(remaining_seconds)
                except:
                    pass
            
            # Print progress every 10 seconds or at key intervals
            if remaining_seconds % 10 == 0 or remaining_seconds <= 10:
                print(f"⏰ [TIMER] {name}: {self._format_time(remaining_seconds)} remaining")
            
            time.sleep(1)
            remaining_seconds -= 1

        # Timer completion
        if window:
            try:
                window.update_label(0)
            except:
                pass
                
        print(f"🔔 [TIMER] FINISHED: {name}!")
        
        # Play timer.mp3 if it exists
        self._play_timer_sound()
        
        # Show notification using PowerShell
        try:
            import subprocess
            title = "Jarvis Timer"
            message = f"Time's up! {name} has finished."
            
            # Use PowerShell to show a message box
            ps_command = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.MessageBox]::Show("{message}", "{title}", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
            '''
            
            subprocess.Popen([
                "powershell", "-WindowStyle", "Hidden", "-Command", ps_command
            ], creationflags=subprocess.CREATE_NO_WINDOW)
            
        except Exception as e:
            print(f"⚠️ [TIMER] Notification error: {e}")
            
        if name in self.active_timers:
            del self.active_timers[name]
        
        # Auto-close window after a delay
        if window:
            time.sleep(5)
            try:
                window.destroy()
            except:
                pass

    def _format_time(self, seconds: int) -> str:
        """Format seconds into HH:MM:SS or MM:SS"""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02}:{m:02}:{s:02}"
        else:
            return f"{m:02}:{s:02}"

    def _play_timer_sound(self):
        """Play timer.mp3 if it exists"""
        try:
            import os
            if os.path.exists('timer.mp3'):
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load('timer.mp3')
                pygame.mixer.music.play()
                print("🔊 [TIMER] Playing timer.mp3")
                # Wait for sound to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                print("🔊 [TIMER] timer.mp3 not found, using system beep")
                import winsound
                for _ in range(3):
                    winsound.Beep(1000, 500)
                    time.sleep(0.2)
        except Exception as e:
            print(f"⚠️ [TIMER] Sound error: {e}")

    def _cleanup_finished_timers(self):
        """Remove finished timers from active list"""
        finished_timers = []
        for name, timer_data in self.active_timers.items():
            if not timer_data["thread"].is_alive():
                finished_timers.append(name)
        
        for name in finished_timers:
            del self.active_timers[name]

    def set_timer(self, command: str) -> str:
        """
        Sets a timer for a specified duration.
        For example: 'set a timer for 10 minutes'.
        """
        # Clean up any finished timers first
        self._cleanup_finished_timers()
        
        # More flexible parsing of timer commands
        duration_str = command.lower()
        
        # Remove common prefixes
        prefixes = ["set a timer", "start a timer", "create a timer", "make a timer", "timer"]
        for prefix in prefixes:
            if duration_str.startswith(prefix):
                duration_str = duration_str[len(prefix):].strip()
                break
        
        # Remove "for" if present
        if duration_str.startswith("for "):
            duration_str = duration_str[4:].strip()
        
        # Handle "X minutes" format directly
        if not duration_str:
            return "Sorry, I couldn't understand the timer duration. Please specify a time like '30 seconds' or '5 minutes'."
        
        duration_seconds = parse_time_string(duration_str)

        if duration_seconds <= 0:
            return "Invalid time format. Please specify a valid time like '30 seconds', '5 minutes' or '2 hours 30 minutes'."

        # Format the duration string for display
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        
        duration_display = ""
        if hours > 0:
            duration_display += f"{hours} hour{'s' if hours > 1 else ''} "
        if minutes > 0:
            duration_display += f"{minutes} minute{'s' if minutes > 1 else ''} "
        if seconds > 0:
            duration_display += f"{seconds} second{'s' if seconds > 1 else ''}"
        
        self.timer_counter += 1
        timer_name = f"Timer #{self.timer_counter} ({duration_display.strip()})"
        
        # Create window in a separate thread to avoid main thread issues
        window = None
        try:
            window_thread = threading.Thread(target=self._create_timer_window, args=(duration_seconds, timer_name))
            window_thread.daemon = True
            window_thread.start()
            print("⏰ [TIMER] Timer window starting...")
        except Exception as e:
            print(f"⚠️ [TIMER] Cannot create timer window: {e}")
            window = None
        
        thread = threading.Thread(target=self._run_timer, args=(duration_seconds, timer_name, window))
        thread.daemon = True
        thread.start()
        
        self.active_timers[timer_name] = {"thread": thread, "window": window}
        
        return f"Timer set for {duration_display.strip()}. I'll notify you when it's done!"

    def cancel_timer(self, timer_name: str = "last") -> str:
        """
        Cancels a running timer.
        Cancels the most recent timer if 'last' is used.
        """
        # Clean up finished timers first
        self._cleanup_finished_timers()
        
        if not self.active_timers:
            return "There are no active timers to cancel."

        if timer_name == "last":
            timer_to_cancel = list(self.active_timers.keys())[-1]
        else:
            # Find by partial match
            found_timer = None
            for name in self.active_timers.keys():
                if timer_name.lower() in name.lower():
                    found_timer = name
                    break
            timer_to_cancel = found_timer

        if not timer_to_cancel or timer_to_cancel not in self.active_timers:
            return f"Timer '{timer_name}' not found."

        timer_data = self.active_timers[timer_to_cancel]
        if timer_data["window"]:
            try:
                if timer_data["window"].winfo_exists():
                    timer_data["window"].on_close()  # This will set the stop_event
            except:
                pass
        del self.active_timers[timer_to_cancel]
        
        return f"Cancelled: {timer_to_cancel}"

    def list_timers(self) -> str:
        """Lists all currently active timers."""
        # Clean up finished timers first
        self._cleanup_finished_timers()
        
        if not self.active_timers:
            return "You have no active timers."
        
        response = "Here are your active timers:\n"
        for i, name in enumerate(self.active_timers.keys(), 1):
            response += f"{i}. {name}\n"
        return response.strip()

# --- Tool Integration ---
_timer_system_instance = TimerSystem()

def get_handlers():
    """Returns a dictionary of tool handlers for the timer system."""
    return {
        "set_timer": _timer_system_instance.set_timer,
        "cancel_timer": _timer_system_instance.cancel_timer,
        "list_timers": _timer_system_instance.list_timers,
    }

def get_tools():
    """Returns a list of tool definitions for the timer system."""
    return [
        {
            "type": "function",
            "function": {
                "name": "set_timer",
                "description": "SETS A COUNTDOWN TIMER FOR A SPECIFIED DURATION (like a kitchen timer or stopwatch). USE THIS EXCLUSIVELY FOR TIMING ACTIVITIES, COOKING, BREAKS, ETC. Shows a visual countdown window. DO NOT USE FOR SCHEDULING REMINDERS AT SPECIFIC TIMES.",
                "example": "set a timer for 5 minutes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The timer command with duration (e.g., '5 minutes' or '1 hour 30 seconds')"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_timer",
                "description": "Cancels a running timer and closes its window. Can cancel the most recent timer.",
                "example": "cancel the last timer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timer_name": {
                            "type": "string",
                            "description": "The name or part of the name of the timer to cancel, or 'last' for the most recent one.",
                            "default": "last"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_timers",
                "description": "Lists all currently active timers.",
                "example": "show all active timers"
            }
        }
    ]
