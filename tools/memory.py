import chromadb
import os
import datetime
from typing import List, Dict

# --- Configuration ---
# Path to the database directory
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory_db")
# Name of the collection
COLLECTION_NAME = "jarvis_long_term_memory"

# Ensure the database directory exists
os.makedirs(DB_PATH, exist_ok=True)

# --- ChromaDB Client Initialization ---
# Initialize a persistent client
client = chromadb.PersistentClient(path=DB_PATH)

# Get or create the collection. This will use the default embedding model.
# The first time this runs, it may download the model.
memory_collection = client.get_or_create_collection(name=COLLECTION_NAME)

# --- Core Memory Functions ---

async def store_memory(text: str) -> str:
    """
    Stores a piece of information in Jarvis's long-term memory.
    This should be used when the user explicitly asks to remember something.
    Example: "Remember that my wife's favorite flower is a lily."
    """
    try:
        # Generate a unique ID based on the current timestamp
        doc_id = datetime.datetime.now().isoformat()
        
        # Store the text in the collection
        memory_collection.add(
            documents=[text],
            ids=[doc_id]
        )
        
        print(f"🧠 [MEMORY] Stored: '{text}'")
        return "OK, Sir. I will remember that."
    except Exception as e:
        print(f"❌ [MEMORY ERROR] Failed to store memory: {e}")
        return "I had trouble remembering that, Sir. There might be an issue with my memory systems."

async def recall_memory(query: str, n_results: int = 3) -> str:
    """
    Recalls the most relevant memories based on a user's query.
    This is used internally to provide context to the main LLM.
    """
    try:
        # Query the collection to find the most relevant documents
        results = memory_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        documents = results.get('documents', [[]])[0]
        
        if not documents:
            return ""
            
        # Format the results into a string
        recalled_memories = "\n".join(f"- {doc}" for doc in documents)
        print(f"🧠 [MEMORY] Recalled for query '{query}':\n{recalled_memories}")
        
        return recalled_memories
        
    except Exception as e:
        print(f"❌ [MEMORY ERROR] Failed to recall memory: {e}")
        return ""

# --- Tool Definitions for LLM ---

def get_tools() -> List[Dict]:
    """Returns the tool definitions for the memory system."""
    return [
        {
            "type": "function",
            "function": {
                "name": "store_memory",
                "description": "Stores a specific piece of text in long-term memory when the user explicitly asks to remember something.",
                "example": "Remember that my mother's birthday is on the 15th of January.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The exact text content to be stored."
                        }
                    },
                    "required": ["text"]
                }
            }
        }
    ]

def get_handlers() -> Dict:
    """Returns the tool handlers for the memory system."""
    return {
        "store_memory": store_memory,
        # recall_memory is not intended to be called by the LLM directly
    }
