import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Web Scraping and Summarization ---

async def scrape_and_summarize_url(url: str, summary_sentences: int = 3) -> str:
    """
    Scrapes the text content from a URL and returns a short summary.
    """
    try:
        logger.info(f"Scraping URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/53.36'
        }
        # Use a timeout to prevent hanging
        response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all paragraph tags, which usually contain the main content
        paragraphs = soup.find_all('p')
        
        text_content = ' '.join([p.get_text() for p in paragraphs])
        
        if not text_content:
            logger.warning("No paragraph text found on the page.")
            return "Could not extract a summary from this page."

        # Create a simple summary by taking the first few sentences
        sentences = text_content.split('.')
        summary = '.'.join(sentences[:summary_sentences]).strip() + '.'
        
        # Clean up summary
        summary = summary.replace('\n', ' ').replace('  ', ' ')
        logger.info(f"Generated summary: {summary}")
        
        return summary

    except requests.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return f"Failed to access the page: {e}"
    except Exception as e:
        logger.error(f"Error scraping or summarizing {url}: {e}")
        return "An error occurred while trying to summarize the page."

# --- Main Tool Function ---

async def google_search(query: str) -> str:
    """
    Searches the web using Google, scrapes the top result, and provides a summary.
    """
    logger.info(f"Received search query: {query}")

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")

    if not api_key or not search_engine_id:
        logger.error("Missing Google API key or Search Engine ID.")
        return "API key or Search Engine ID is missing."

    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": search_engine_id, "q": query, "num": 3}

    logger.info("Sending request to Google Custom Search API...")
    try:
        response = await asyncio.to_thread(requests.get, url, params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Google API request failed: {e}")
        return f"Error connecting to Google Search: {e}"

    data = response.json()
    results = data.get("items", [])

    if not results:
        logger.info("No results found from Google Search.")
        return "No results found for your query."

    # --- Generate Summary from Top Result ---
    top_result_url = results[0].get("link")
    summary = await scrape_and_summarize_url(top_result_url)

    # --- Format Final Output ---
    final_response = f"Here is a summary of the top result:\n\n{summary}\n\n"
    final_response += "For more information, you can check the provided links."

    return final_response.strip()

async def get_current_datetime() -> str:
    """Get the current date and time."""
    return datetime.now().isoformat()

# --- LangChain/Tool Integration ---

def get_tools():
    """Return tool definitions for the agent."""
    return [
        {
            "type": "function",
            "function": {
                "name": "google_search",
                "description": "Searches the web and provides a summary of the top result.",
                "example": "search for the latest news on AI",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up on the web."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Get the current date and time.",
                "example": "what is the date and time?"
            }
        }
    ]

def get_handlers():
    """Return tool handlers for the agent."""
    return {
        "google_search": google_search,
        "get_current_datetime": get_current_datetime
    }
