import pyautogui
import asyncio
import time
import re
from datetime import datetime
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
from typing import List
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# ---------------------
# Volume Control with pycaw
# ---------------------
def get_master_volume_interface():
    """Gets the master volume control interface."""
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)

def set_master_volume(level_percentage: int) -> str:
    """Sets the master volume to a specific percentage (0-100)."""
    try:
        volume_interface = get_master_volume_interface()
        # pycaw uses a scale from 0.0 to 1.0
        level_float = max(0.0, min(1.0, level_percentage / 100.0))
        volume_interface.SetMasterVolumeLevelScalar(level_float, None)
        return f"🔊 Volume set to {level_percentage}%. "
    except Exception as e:
        return f"❌ Failed to set volume: {e}"

def adjust_master_volume(change_percentage: int) -> str:
    """Adjusts the master volume up or down by a percentage."""
    try:
        volume_interface = get_master_volume_interface()
        current_level_float = volume_interface.GetMasterVolumeLevelScalar()
        
        new_level_float = current_level_float + (change_percentage / 100.0)
        new_level_float = max(0.0, min(1.0, new_level_float))
        
        volume_interface.SetMasterVolumeLevelScalar(new_level_float, None)
        new_level_percentage = int(new_level_float * 100)
        return f"🔊 Volume adjusted to {new_level_percentage}%. "
    except Exception as e:
        return f"❌ Failed to adjust volume: {e}"

def mute_master_volume(mute: bool) -> str:
    """Mutes or unmutes the master volume."""
    try:
        volume_interface = get_master_volume_interface()
        volume_interface.SetMute(1 if mute else 0, None)
        status = "muted" if mute else "unmuted"
        return f"🔊 Volume has been {status}. "
    except Exception as e:
        return f"❌ Failed to change mute state: {e}"

# ---------------------
# SafeController Class
# ---------------------
class SafeController:
    def __init__(self):
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.active = False
        self.activation_time = None
        
        self.special_keys = {
            "ctrl": Key.ctrl, "alt": Key.alt, "shift": Key.shift, "enter": Key.enter,
            "space": Key.space, "tab": Key.tab, "escape": Key.esc, "backspace": Key.backspace,
            "delete": Key.delete, "home": Key.home, "end": Key.end, "page_up": Key.page_up,
            "page_down": Key.page_down, "up": Key.up, "down": Key.down, "left": Key.left,
            "right": Key.right, "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
            "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8, "f9": Key.f9,
            "f10": Key.f10, "f11": Key.f11, "f12": Key.f12
        }
        self.valid_keys = set("abcdefghijklmnopqrstuvwxyz0123456789")

    def resolve_key(self, key):
        return self.special_keys.get(key.lower(), key)

    def log(self, action: str):
        with open("control_log.txt", "a") as f:
            f.write(f"{datetime.now()}: {action}\n")

    def activate(self, token=None):
        if token != "my_secret_token":
            self.log("Activation attempt failed.")
            return
        self.active = True
        self.activation_time = time.time()
        self.log("Controller auto-activated.")

    def deactivate(self):
        self.active = False
        self.log("Controller auto-deactivated.")

    def is_active(self):
        return self.active

    async def move_cursor(self, direction: str, distance: int = 100):
        if not self.is_active(): return "🛑 Controller is inactive."
        x, y = self.mouse.position
        if direction == "left": self.mouse.position = (x - distance, y)
        elif direction == "right": self.mouse.position = (x + distance, y)
        elif direction == "up": self.mouse.position = (x, y - distance)
        elif direction == "down": self.mouse.position = (x, y + distance)
        await asyncio.sleep(0.2)
        self.log(f"Mouse moved {direction}")
        return f"🖱️ Moved mouse {direction} by {distance} pixels, sir."

    async def mouse_click(self, button: str = "left"):
        if not self.is_active(): return "🛑 Controller is inactive."
        if button == "left": self.mouse.click(Button.left, 1)
        elif button == "right": self.mouse.click(Button.right, 1)
        elif button == "double": self.mouse.click(Button.left, 2)
        await asyncio.sleep(0.2)
        self.log(f"Mouse clicked: {button}")
        return f"🖱️ {button.capitalize()} clicked, sir."

    async def scroll_cursor(self, direction: str, amount: int = 10):
        if not self.is_active(): return "🛑 Controller is inactive."
        try:
            if direction == "up": self.mouse.scroll(0, amount)
            elif direction == "down": self.mouse.scroll(0, -amount)
        except:
            pyautogui.scroll(amount * 100)
        await asyncio.sleep(0.2)
        self.log(f"Mouse scrolled {direction}")
        return f"🖱️ Scrolled {direction} by {amount} units, sir."

    async def type_text(self, text: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        for char in text:
            if not char.isprintable(): continue
            try:
                self.keyboard.press(char)
                self.keyboard.release(char)
                await asyncio.sleep(0.05)
            except Exception:
                continue
        self.log(f"Typed text: {text}")
        return f"⌨️ Typed '{text}', sir."

    async def press_key(self, key: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        if key.lower() not in self.special_keys and key.lower() not in self.valid_keys:
            return f"❌ Invalid key: {key}"
        k = self.resolve_key(key)
        try:
            self.keyboard.press(k)
            self.keyboard.release(k)
        except Exception as e:
            return f"❌ Failed key: {key} — {e}"
        await asyncio.sleep(0.2)
        self.log(f"Pressed key: {key}")
        return f"⌨️ Key '{key}' pressed, sir."

    async def press_hotkey(self, keys: List[str]):
        if not self.is_active(): return "🛑 Controller is inactive."
        resolved = [self.resolve_key(k) for k in keys if k.lower() in self.special_keys or k.lower() in self.valid_keys]
        if len(resolved) != len(keys): return "❌ Invalid key in hotkey."
        for k in resolved: self.keyboard.press(k)
        for k in reversed(resolved): self.keyboard.release(k)
        await asyncio.sleep(0.3)
        self.log(f"Pressed hotkey: {' + '.join(keys)}")
        return f"⌨️ Hotkey {' + '.join(keys)} executed, sir."

    async def control_volume(self, command: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        command = command.lower().strip()

        # Pattern 1: Set volume to specific percentage (e.g., "set volume to 50%")
        match = re.search(r'(set|to)\s+(\d{1,3})%?', command)
        if match:
            level = int(match.group(2))
            return set_master_volume(level)

        # Pattern 2: Adjust volume up/down by percentage (e.g., "up by 20%")
        match = re.search(r'(up|down)\s+by\s+(\d{1,3})%?', command)
        if match:
            direction, amount = match.groups()
            change = int(amount) if direction == 'up' else -int(amount)
            return adjust_master_volume(change)
            
        # Pattern 3: Mute/Unmute
        if "mute" in command:
            return mute_master_volume(True)
        if "unmute" in command:
            return mute_master_volume(False)

        # Fallback to key presses for simple up/down if specific percentages aren't mentioned
        if "up" in command:
            pyautogui.press("volumeup")
            return "🔊 Volume turned up."
        if "down" in command:
            pyautogui.press("volumedown")
            return "🔊 Volume turned down."

        return "❌ Invalid volume command. Please say something like 'set volume to 50%', 'up by 10%', or 'mute'."

    async def swipe_gesture(self, direction: str):
        if not self.is_active(): return "🛑 Controller is inactive."
        screen_width, screen_height = pyautogui.size()
        x, y = screen_width // 2, screen_height // 2
        try:
            if direction == "up": pyautogui.moveTo(x, y + 200); pyautogui.dragTo(x, y - 200, duration=0.5)
            elif direction == "down": pyautogui.moveTo(x, y - 200); pyautogui.dragTo(x, y + 200, duration=0.5)
            elif direction == "left": pyautogui.moveTo(x + 200, y); pyautogui.dragTo(x - 200, y, duration=0.5)
            elif direction == "right": pyautogui.moveTo(x - 200, y); pyautogui.dragTo(x + 200, y, duration=0.5)
        except Exception:
            pass
        await asyncio.sleep(0.5)
        self.log(f"Swipe gesture: {direction}")
        return f"🖱️ Swipe {direction} gesture completed, sir."

# ------------------------------
# Local Tool Wrappers (Jarvis)
# ------------------------------
controller = SafeController()

async def with_temporary_activation(fn, *args, **kwargs):
    controller.activate("my_secret_token")
    result = await fn(*args, **kwargs)
    await asyncio.sleep(2)
    controller.deactivate()
    return result

async def move_cursor_tool(direction: str, distance: int = 100):
    return await with_temporary_activation(controller.move_cursor, direction, distance)
async def mouse_click_tool(button: str = "left"):
    return await with_temporary_activation(controller.mouse_click, button)
async def scroll_cursor_tool(direction: str, amount: int = 10):
    return await with_temporary_activation(controller.scroll_cursor, direction, amount)
async def type_text_tool(text: str):
    return await with_temporary_activation(controller.type_text, text)
async def press_key_tool(key: str):
    return await with_temporary_activation(controller.press_key, key)
async def press_hotkey_tool(keys: List[str]):
    return await with_temporary_activation(controller.press_hotkey, keys)
async def control_volume_tool(command: str):
    """
    Controls system volume based on a command.
    Examples: 'set volume to 50%', 'turn it up by 20', 'mute'.
    """
    return await with_temporary_activation(controller.control_volume, command)
async def swipe_gesture_tool(direction: str):
    return await with_temporary_activation(controller.swipe_gesture, direction)

def get_tools():
    """Return tool definitions for Ollama"""
    return [
        {
            "type": "function",
            "function": {
                "name": "move_cursor_tool",
                "description": "Moves the mouse cursor in a specified direction (up, down, left, right).",
                "example": "move the mouse up by 200 pixels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "description": "The direction to move ('up', 'down', 'left', 'right')."},
                        "distance": {"type": "integer", "description": "The distance to move in pixels.", "default": 100}
                    },
                    "required": ["direction"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mouse_click_tool",
                "description": "Performs a mouse click (left, right, or double).",
                "example": "perform a right click",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "button": {"type": "string", "description": "The mouse button to click ('left', 'right', 'double').", "default": "left"}
                    },
                    "required": ["button"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scroll_cursor_tool",
                "description": "Scrolls the mouse wheel up or down.",
                "example": "scroll down a bit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "description": "The direction to scroll ('up', 'down')."},
                        "amount": {"type": "integer", "description": "The amount to scroll.", "default": 10}
                    },
                    "required": ["direction"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "type_text_tool",
                "description": "Types the given text using the keyboard.",
                "example": "type the words hello world",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The text to type."}
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "press_key_tool",
                "description": "Presses a single special key (e.g., 'enter', 'shift', 'esc').",
                "example": "press the enter key",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "The special key to press."}
                    },
                    "required": ["key"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "press_hotkey_tool",
                "description": "Presses a combination of keys (hotkey), like 'ctrl+c'.",
                "example": "press control c to copy",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "A list of keys to press simultaneously (e.g., ['ctrl', 'c'])."
                        }
                    },
                    "required": ["keys"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "control_volume_tool",
                "description": "Controls system volume with natural language commands.",
                "example": "turn the volume up by 20 percent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The volume command, e.g., 'set volume to 50%', 'up by 10', 'mute'."}
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "swipe_gesture_tool",
                "description": "Performs a swipe gesture on the screen.",
                "example": "swipe left on the screen",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "description": "The direction to swipe ('up', 'down', 'left', 'right')."}
                    },
                    "required": ["direction"]
                }
            }
        }
    ]

def get_handlers():
    """Return tool handlers"""
    return {
        "move_cursor_tool": move_cursor_tool,
        "mouse_click_tool": mouse_click_tool,
        "scroll_cursor_tool": scroll_cursor_tool,
        "type_text_tool": type_text_tool,
        "press_key_tool": press_key_tool,
        "press_hotkey_tool": press_hotkey_tool,
        "control_volume_tool": control_volume_tool,
        "swipe_gesture_tool": swipe_gesture_tool
    }
