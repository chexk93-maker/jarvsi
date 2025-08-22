import re
import asyncio
import webbrowser
import requests
import urllib.parse
import json

async def play_music(song_name: str):
    """Play music from YouTube"""
    search_term = song_name.strip()
    print(f"🎵 [MUSIC] Searching for: {search_term}")

    try:
        # Try using a simple requests-based YouTube search
        try:
            # Use YouTube's search API endpoint (no API key needed for basic search)
            encoded_query = urllib.parse.quote_plus(search_term)
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            
            # Make a simple request to get the search page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Look for video IDs in the response
                import re
                video_pattern = r'"videoId":"([^"]+)"'
                matches = re.findall(video_pattern, response.text)
                
                if matches:
                    video_id = matches[0]  # Get the first video
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    # Try to extract title (optional)
                    title_pattern = r'"title":{"runs":\[{"text":"([^"]+)"}'
                    title_matches = re.findall(title_pattern, response.text)
                    title = title_matches[0] if title_matches else search_term
                    
                    print(f"🎵 [MUSIC] Found: {title}")
                    print(f"🎵 [MUSIC] Opening: {video_url}")
                    
                    # Create autoplay URL
                    autoplay_url = video_url + "&autoplay=1"
                    
                    # Open the video with autoplay
                    webbrowser.open(autoplay_url)
                    print(f"✅ [MUSIC] Now playing: {title}")
                    return f"Now playing: {title}"
                else:
                    raise Exception("No videos found in search results")
            else:
                raise Exception(f"Search request failed with status {response.status_code}")
        
        except Exception as search_error:
            print(f"🔄 [MUSIC] Direct search failed: {search_error}")
            print(f"🔄 [MUSIC] Using fallback search method...")
            
            # Fallback: Direct YouTube search URL
            encoded_query = urllib.parse.quote_plus(search_term)
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            
            print(f"🎵 [MUSIC] Opening YouTube search for: {search_term}")
            webbrowser.open(search_url)
            print(f"✅ [MUSIC] Opened YouTube search for: {search_term}")
            return f"Opened YouTube search for: {search_term}. Please select the song you want to play."
            
    except Exception as e:
        print(f"❌ [MUSIC] Error: {e}")
        return f"Sorry sir, I couldn't play {search_term}. Please try again or search manually on YouTube."

def get_tools():
    """Return tool definitions for Ollama"""
    return [
        {
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "Play a song or music on YouTube. Use this when user asks to play any song, music, or audio content.",
                "example": "play the new Taylor Swift song",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "song_name": {
                            "type": "string",
                            "description": "The name of the song, artist, or music to play"
                        }
                    },
                    "required": ["song_name"]
                }
            }
        }
    ]

def get_handlers():
    """Return tool handlers"""
    return {
        "play_music": play_music
    }
