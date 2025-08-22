import os
import subprocess
import sys
import logging
import asyncio
from fuzzywuzzy import process

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Add more user-specific directories here for a wider search scope
ALLOWED_FOLDERS = [
    os.path.expanduser("~\Downloads"),
    os.path.expanduser("~\Videos"),
    os.path.expanduser("~\Music"),
]
# Minimum score for a fuzzy match to be considered valid
FUZZY_MATCH_THRESHOLD = 85

# --- Core Functions ---

async def index_paths(base_dirs):
    """Recursively index all files and folders in the given base directories."""
    path_index = []
    logger.info(f"Starting indexing for: {base_dirs}")
    for base_dir in base_dirs:
        if not os.path.isdir(base_dir):
            logger.warning(f"Directory not found, skipping: {base_dir}")
            continue
        for root, dirs, files in os.walk(base_dir):
            # Index files
            for f in files:
                path_index.append({"name": f, "path": os.path.join(root, f), "type": "file"})
            # Index directories
            for d in dirs:
                path_index.append({"name": d, "path": os.path.join(root, d), "type": "folder"})
    logger.info(f"Indexing complete. Found {len(path_index)} files and folders.")
    return path_index

async def search_path(query: str, index: list, item_type: str = "file"):
    """
    Search for a file or folder in the index using fuzzy matching.
    `item_type` can be 'file' or 'folder'.
    """
    choices = [item["name"] for item in index if item["type"] == item_type]
    if not choices:
        logger.warning(f"No items of type '{item_type}' available to search.")
        return None

    # The scorer helps in matching queries like "one piece 32" to "[Judas] One Piece - 032.mkv"
    best_match, score = process.extractOne(query, choices)
    
    logger.info(f"Fuzzy match for '{query}' ({item_type}): '{best_match}' (Score: {score})")
    
    if score >= FUZZY_MATCH_THRESHOLD:
        for item in index:
            if item["name"] == best_match and item["type"] == item_type:
                return item
    return None

async def open_path_os_specific(path: str):
    """Open a file or folder using the default OS application."""
    try:
        logger.info(f"Attempting to open: {path}")
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else: # Linux and other Unix-like
            subprocess.run(["xdg-open", path], check=True)
        return f"Successfully initiated opening of '{os.path.basename(path)}'."
    except FileNotFoundError:
        logger.error(f"Path not found: {path}")
        return f"Error: Path not found at '{path}'."
    except Exception as e:
        logger.error(f"Failed to open path '{path}': {e}")
        return f"An error occurred: {e}"

# --- Tool-Facing Function ---

async def open_item(query: str) -> str:
    """
    Opens a file or folder based on a search query.
    It first searches for files, and if no suitable file is found, it then searches for folders.
    For example: 'open my project folder' or 'play the latest one piece episode'.
    """
    # Sanitize query
    query = query.lower().replace("open", "").replace("play", "").replace("find", "").strip()
    
    index = await index_paths(ALLOWED_FOLDERS)
    
    # 1. Search for files first
    file_item = await search_path(query, index, item_type="file")
    if file_item:
        return await open_path_os_specific(file_item["path"])
        
    # 2. If no file found, search for folders
    folder_item = await search_path(query, index, item_type="folder")
    if folder_item:
        return await open_path_os_specific(folder_item["path"])

    logger.warning(f"Could not find a suitable file or folder matching '{query}'.")
    return f"Sorry, I couldn't find any file or folder matching '{query}'."

# --- LangChain/Tool Integration ---

def get_tools():
    """Return tool definitions for the agent."""
    return [
        {
            "type": "function",
            "function": {
                "name": "open_item",
                "description": "Opens any file or folder by its name from user directories.",
                "example": "open my project folder",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The name of the file or folder to open (e.g., 'my resume.pdf' or 'project folder')."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

def get_handlers():
    """Return tool handlers for the agent."""
    return {
        "open_item": open_item
    }
