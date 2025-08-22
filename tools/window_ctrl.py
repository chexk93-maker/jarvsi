import os
import subprocess
import logging
import sys
import asyncio
from fuzzywuzzy import process

# Setup encoding and logger
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try optional dependencies
try:
    import win32gui
    import win32con
    import win32com.client
except ImportError:
    win32gui = None
    win32con = None
    win32com = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import psutil
except ImportError:
    psutil = None

# App command map
APP_MAPPINGS = {
    "notepad": "notepad",
    "calculator": "calc",
    "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "vlc": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "command prompt": "cmd",
    "control panel": "control",
    "settings": "ms-settings:",
    "paint": "mspaint",
    "vs code": "C:\\Users\\Krish\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
}

# Allowed folders for file interaction
ALLOWED_FOLDERS = [
    r"C:\\Users\\Krish\\Downloads",
    r"C:\\Users\\Krish\\Videos",
    r"C:\\Users\\Krish\\Music"
]

# Async window focus utility
async def focus_window(title_keyword: str) -> bool:
    """Focus on a window by its title."""
    if not gw:
        logger.warning("⚠ pygetwindow not available")
        return False

    await asyncio.sleep(1.5)
    title_keyword = title_keyword.lower().strip()

    for window in gw.getAllWindows():
        if title_keyword in window.title.lower():
            try:
                # Restore if minimized
                if window.isMinimized:
                    window.restore()
                # Activate the window
                window.activate()
                # Bring to front
                window.activate()  # Second call sometimes helps
                return True
            except Exception as e:
                logger.error(f"Error focusing window: {e}")
                # Try alternative method
                try:
                    window.restore()
                    window.maximize()
                    return True
                except:
                    pass
    return False

# New Feature: Maximize/Minimize window
async def maximize_or_minimize_window(title_keyword: str, action: str) -> str:
    """Maximize or minimize a window by its title."""
    if not gw:
        return "❌ pygetwindow not available"

    for window in gw.getAllWindows():
        if title_keyword.lower() in window.title.lower():
            if action == "maximize":
                window.maximize()
                return f"🗖 Maximized: {window.title}"
            elif action == "minimize":
                window.minimize()
                return f"🗕 Minimized: {window.title}"
    return "❌ Window not found."

# New Feature: Switch window (Alt+Tab)
async def switch_window():
    """Switch to the next window."""
    if pyautogui:
        pyautogui.keyDown('alt')
        pyautogui.press('tab')
        await asyncio.sleep(0.5)
        pyautogui.keyUp('alt')
        return "🔄 Switched window."
    return "❌ pyautogui not available"

# New Feature: Show desktop (Win+D)
async def toggle_desktop():
    """Show or hide the desktop."""
    if pyautogui:
        pyautogui.hotkey('win', 'd')
        return "🖥️ Toggled desktop view."
    return "❌ pyautogui not available"

# Index files/folders
async def index_items(base_dirs):
    """Index files and folders in a list of directories."""
    item_index = []
    for base_dir in base_dirs:
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                item_index.append({"name": d, "path": os.path.join(root, d), "type": "folder"})
            for f in files:
                item_index.append({"name": f, "path": os.path.join(root, f), "type": "file"})
    logger.info(f"✅ Indexed {len(item_index)} items.")
    return item_index

async def search_item(query, index, item_type):
    """Search for an item in the index."""
    filtered = [item for item in index if item["type"] == item_type]
    choices = [item["name"] for item in filtered]
    if not choices:
        return None
    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' with score {score}")
    if score > 70:
        for item in filtered:
            if item["name"] == best_match:
                return item
    return None

# File/folder actions
async def open_folder(path):
    """Open a folder."""
    try:
        os.startfile(path)
        await focus_window(os.path.basename(path))
    except Exception as e:
        logger.error(f"❌ Error opening folder: {e}")

async def play_file(path):
    """Play a file."""
    try:
        os.startfile(path)
        await focus_window(os.path.basename(path))
    except Exception as e:
        logger.error(f"❌ Error playing file: {e}")


# Battery Status
async def get_battery_status() -> str:
    """Get the system's battery status."""
    if not psutil:
        return "❌ psutil library not available. Cannot retrieve battery status."
    battery = psutil.sensors_battery()
    if battery:
        percent = battery.percent
        return f"Sir, the battery is at {percent}%."
    return "❌ Could not retrieve battery status."


# App control
async def open_app(app_title: str) -> str:
    """Open an application."""
    app_title = app_title.lower().strip()
    app_command = APP_MAPPINGS.get(app_title, app_title)
    try:
        # Launch the application
        await asyncio.create_subprocess_shell(f'start "" "{app_command}"')
        
        # Wait longer for app to fully load
        await asyncio.sleep(3)
        
        # Try to focus the window multiple times
        focused = False
        for attempt in range(3):
            focused = await focus_window(app_title)
            if focused:
                break
            await asyncio.sleep(1)
        
        if focused:
            return f"{app_title.title()} is now open and ready to use."
        else:
            # Even if focus failed, the app is likely open
            return f"{app_title.title()} has been opened. You may need to click on it to bring it to the front."
    except Exception as e:
        return f"Sorry Sir, I couldn't open {app_title}. Error: {e}"

async def close_app(window_title: str) -> str:
    """Close an application by its window title."""
    if not win32gui:
        return "❌ win32gui not available"

    def enumHandler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    win32gui.EnumWindows(enumHandler, None)
    return f"✅ Window closed: {window_title}"

# File management functions
async def manage_folder(action: str, folder_name: str = "", new_name: str = "") -> str:
    """Manage folders (open)."""
    index = await index_items(ALLOWED_FOLDERS)

    if action == "open":
        item = await search_item(folder_name, index, "folder")
        if item:
            await open_folder(item["path"])
            return f"✅ Folder opened: {item['name']}"
        return "❌ Folder not found."
        

async def manage_file(action: str, file_name: str = "", new_name: str = "") -> str:
    """Manage files (open)."""
    index = await index_items(ALLOWED_FOLDERS)

    if action == "open":
        item = await search_item(file_name, index, "file")
        if item:
            await play_file(item["path"])
            return f"✅ File opened: {item['name']}"
        return "❌ File not found."
   

async def window_control_wrapper(title_keyword: str, action: str) -> str:
    """Wrapper for maximize/minimize with better error handling"""
    try:
        result = await maximize_or_minimize_window(title_keyword, action)
        logger.info(f"Window control result: {result}")
        return result
    except Exception as e:
        error_msg = f"❌ Error controlling window: {e}"
        logger.error(error_msg)
        return error_msg

async def switch_window_wrapper() -> str:
    """Wrapper for switch window with better error handling"""
    try:
        result = await switch_window()
        logger.info(f"Window switch result: {result}")
        return result
    except Exception as e:
        error_msg = f"❌ Error switching window: {e}"
        logger.error(error_msg)
        return error_msg

async def toggle_desktop_wrapper() -> str:
    """Wrapper for toggle desktop with better error handling"""
    try:
        result = await toggle_desktop()
        logger.info(f"Desktop toggle result: {result}")
        return result
    except Exception as e:
        error_msg = f"❌ Error toggling desktop: {e}"
        logger.error(error_msg)
        return error_msg

def get_tools():
    """Return tool definitions for Ollama"""
    return [
        {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "Open an application or program.",
                "example": "open chrome for me",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_title": {
                            "type": "string",
                            "description": "Name of the application to open"
                        }
                    },
                    "required": ["app_title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "close_app",
                "description": "Close an application or window.",
                "example": "close notepad",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "window_title": {
                            "type": "string",
                            "description": "Name of the window/application to close"
                        }
                    },
                    "required": ["window_title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "maximize_or_minimize_window",
                "description": "Maximize or minimize a specific window.",
                "example": "maximize the chrome window",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title_keyword": {
                            "type": "string",
                            "description": "Keyword or part of the window title to find"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["maximize", "minimize"],
                            "description": "Action to perform - maximize or minimize the window"
                        }
                    },
                    "required": ["title_keyword", "action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "switch_window",
                "description": "Switch to the next window (Alt+Tab functionality).",
                "example": "switch to the other window",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "toggle_desktop",
                "description": "Show or hide desktop (Win+D functionality).",
                "example": "show me the desktop",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "manage_folder",
                "description": "Opens a folder from user directories.",
                "example": "open the downloads folder",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["open"],
                            "description": "Action to perform on the folder"
                        },
                        "folder_name": {
                            "type": "string",
                            "description": "Name of the folder"
                        }
                    },
                    "required": ["action", "folder_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "manage_file",
                "description": "Opens a file from user directories.",
                "example": "open the file named resume",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["open"],
                            "description": "Action to perform on the file"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "Name of the file"
                        }
                    },
                    "required": ["action", "file_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_battery_status",
                "description": "Get the current battery status of the system.",
                "example": "what's my battery level?",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

def get_handlers():
    """Return tool handlers"""
    return {
        "open_app": open_app,
        "close_app": close_app,
        "maximize_or_minimize_window": window_control_wrapper,
        "switch_window": switch_window_wrapper,
        "toggle_desktop": toggle_desktop_wrapper,
        "manage_folder": manage_folder,
        "manage_file": manage_file,
        "get_battery_status": get_battery_status
    }
