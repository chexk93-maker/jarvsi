import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import subprocess
import platform

class ReminderSystem:
    def __init__(self, data_file="reminders.json"):
        self.data_file = data_file
        self.reminders = self.load_reminders()
        self.reminder_threads = {}
        self.speak_callback = None
        self.load_and_start_reminders()

    def load_reminders(self) -> Dict:
        """Load reminders from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    reminders = json.load(f)
                    # Convert time strings back to datetime objects
                    for rid, r in reminders.items():
                        if isinstance(r.get('time'), str):
                            reminders[rid]['time'] = datetime.fromisoformat(r['time'])
                        if isinstance(r.get('created_at'), str):
                            reminders[rid]['created_at'] = datetime.fromisoformat(r['created_at'])
                    return reminders
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    def save_reminders(self):
        """Save reminders to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.reminders, f, indent=2, default=str)

    def speak(self, text: str):
        """Speech output routed to registered speaker if available."""
        try:
            if callable(self.speak_callback):
                self.speak_callback(text)
            else:
                print(f"🔊 REMINDER: {text}")
        except Exception:
            print(f"🔊 REMINDER: {text}")

    def show_notification(self, title: str, message: str):
        """Show system notification"""
        try:
            if platform.system() == "Windows":
                # The win10toast library is not a standard dependency, using console output
                print(f"🔔 {title}: {message}")
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}" '])
            else:  # Linux
                subprocess.run(["notify-send", title, message])
        except Exception as e:
            print(f"Notification error: {e}")

    def parse_natural_language_time(self, text: str) -> Tuple[Optional[str], Optional[datetime]]:
        """Parse natural language time expressions from a command"""
        text = text.lower().strip()
        text = re.sub(r'^(remind me to|set a reminder to|add a reminder to)\s+', '', text)

        current_time = datetime.now()
        task = None
        target_time = None

        # "in 5 minutes", "in 1 hour"
        match = re.search(r'(.+?)\s+in\s+(\d+)\s+(minutes?|mins?|hours?|hrs?)', text)
        if match:
            task, duration, unit = match.groups()
            duration = int(duration)
            if 'minute' in unit or 'min' in unit:
                target_time = current_time + timedelta(minutes=duration)
            elif 'hour' in unit or 'hr' in unit:
                target_time = current_time + timedelta(hours=duration)

        # "at 9:00 PM", "at 8am"
        if not target_time:
            match = re.search(r'(.+?)\s+at\s+(\d{1,2}):?(\d{0,2})\s*(am|pm)?', text)
            if match:
                task, hour_str, minute_str, ampm = match.groups()
                hour = int(hour_str)
                minute = int(minute_str) if minute_str else 0
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                
                target_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time <= current_time:
                    target_time += timedelta(days=1)

        # "tomorrow", "today"
        if not target_time:
            match = re.search(r'(.+?)\s+(tomorrow|today)', text)
            if match:
                task, day = match.groups()
                day_offset = 1 if day == 'tomorrow' else 0
                target_time = (current_time + timedelta(days=day_offset)).replace(hour=9, minute=0, second=0, microsecond=0)

        return task.strip() if task else None, target_time

    def set_reminder(self, command: str) -> str:
        """
        Sets a reminder based on a natural language command.
        For example: 'Set a reminder to call mom in 2 hours' or 'remind me to check the oven at 5:30pm'.
        """
        task, target_time = self.parse_natural_language_time(command)

        if not task or not target_time:
            return "Sorry, I couldn't understand the reminder. Please specify a task and a time."

        reminder_id = f"reminder_{len(self.reminders) + 1}_{int(time.time())}"
        reminder_data = {
            'id': reminder_id,
            'task': task,
            'time': target_time,
            'created_at': datetime.now(),
            'completed': False
        }

        self.reminders[reminder_id] = reminder_data
        self.save_reminders()
        self.start_reminder_thread(reminder_id, reminder_data)

        time_str = target_time.strftime("%Y-%m-%d %H:%M")
        response = f"OK, I will remind you to '{task}' at {time_str}."
        return response

    def start_reminder_thread(self, reminder_id: str, reminder_data: Dict):
        """Start a thread to handle the reminder notification"""
        def reminder_worker():
            target_time = reminder_data['time']
            wait_seconds = (target_time - datetime.now()).total_seconds()

            if wait_seconds > 0:
                time.sleep(wait_seconds)

            if reminder_id in self.reminders and not self.reminders[reminder_id]['completed']:
                task = reminder_data['task']
                message = f"Sir, it's time to {task}."
                self.speak(message)
                self.show_notification("Jarvis Reminder", f"Time to {task}")
                # Mark as completed after notification
                self.reminders[reminder_id]['completed'] = True
                self.save_reminders()

        thread = threading.Thread(target=reminder_worker, daemon=True)
        thread.start()
        self.reminder_threads[reminder_id] = thread

    def list_reminders(self) -> str:
        """
        Lists all active (not completed) reminders.
        """
        active_reminders = []
        for r_id, r_data in self.reminders.items():
            if not r_data.get('completed'):
                active_reminders.append(r_data)
        
        if not active_reminders:
            return "You have no active reminders."

        response = "Here are your active reminders:\n"
        sorted_reminders = sorted(active_reminders, key=lambda x: x['time'])

        for i, r in enumerate(sorted_reminders, 1):
            time_str = r['time'].strftime("%Y-%m-%d %H:%M")
            response += f"{i}. {r['task']} at {time_str}\n"
        
        return response.strip()

    def delete_reminder(self, task_query: str) -> str:
        """
        Deletes a reminder that contains the given query text.
        For example: 'delete reminder about calling mom'.
        """
        query = task_query.lower().replace("reminder about", "").replace("the reminder", "").strip()
        r_to_delete = None
        
        for r_id, r_data in self.reminders.items():
            if query in r_data['task'].lower() and not r_data.get('completed'):
                r_to_delete = r_id
                break
        
        if r_to_delete:
            task = self.reminders[r_to_delete]['task']
            del self.reminders[r_to_delete]
            self.save_reminders()
            return f"I've deleted the reminder for '{task}'."
        
        return f"I couldn't find an active reminder matching '{query}'."

    def load_and_start_reminders(self):
        """Load existing reminders and start their threads on init"""
        for r_id, r_data in self.reminders.items():
            if not r_data.get('completed') and r_data['time'] > datetime.now():
                self.start_reminder_thread(r_id, r_data)

    def get_active_reminders(self) -> List[Dict]:
        """Return a list of active, not-completed reminder dicts."""
        return [r for r in self.reminders.values() if not r.get('completed')]

# --- Tool Integration ---
# Singleton instance of the reminder system
_reminder_system_instance = ReminderSystem()

def get_handlers():
    """
    Returns a dictionary of tool handlers for the reminder system.
    """
    return {
        "set_reminder": _reminder_system_instance.set_reminder,
        "list_reminders": _reminder_system_instance.list_reminders,
        "delete_reminder": _reminder_system_instance.delete_reminder,
    }

def get_tools():
    """
    Returns a list of tool definitions for the reminder system.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "set_reminder",
                "description": "SETS A REMINDER FOR A SPECIFIC TASK AT A FUTURE TIME OR DATE. USE THIS EXCLUSIVELY FOR SCHEDULING TASKS, APPOINTMENTS, OR THINGS TO REMEMBER LATER AT SPECIFIC TIMES/DATES. DO NOT USE FOR SIMPLE COUNTDOWN TIMERS.",
                "example": "remind me to call mom in 2 hours",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The natural language reminder command with task and time (e.g., 'call mom in 2 hours')"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_reminders",
                "description": "Lists all active (not completed) reminders.",
                "example": "what are my reminders?"
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_reminder",
                "description": "Deletes a reminder that contains the given query text.",
                "example": "delete the reminder about calling mom",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_query": {
                            "type": "string",
                            "description": "The query text to match against reminder tasks (e.g., 'calling mom')"
                        }
                    },
                    "required": ["task_query"]
                }
            }
        }
    ]

def register_speaker(speaker_callable):
    """Register a callable(text) used to speak reminder messages."""
    _reminder_system_instance.speak_callback = speaker_callable

def get_reminder_system() -> ReminderSystem:
    """Return the singleton reminder system instance for inspection."""
    return _reminder_system_instance
