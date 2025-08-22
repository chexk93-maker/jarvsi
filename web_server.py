import asyncio
import websockets
import json
import threading
import queue
import time
import logging
import sys
import socket
from core.brain import JarvisCore

# Setup logging - suppress handshake errors as they're mostly noise
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("websockets.server").setLevel(logging.CRITICAL)  # Suppress handshake errors
logger = logging.getLogger(__name__)

def is_port_available(host, port):
    """Check if a port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result != 0  # True if port is available (connection failed)
    except Exception:
        return False  # Assume not available if we can't check

class JarvisWebServer:
    def __init__(self):
        self.jarvis = None
        self.websocket_clients = set()
        self.message_queue = queue.Queue()
        self.audio_level_queue = queue.Queue()
        self.is_running = False
        self.client_counter = 0  # Track total unique clients
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        # Clean up any disconnected clients first
        await self._cleanup_disconnected_clients()
        
        # Check if client is already registered
        if websocket in self.websocket_clients:
            logger.debug("Client already registered")
            return
            
        self.websocket_clients.add(websocket)
        self.client_counter += 1
        logger.info(f"Client connected. Total clients: {len(self.websocket_clients)} (Total unique: {self.client_counter})")
        
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        # Check if client was actually registered
        if websocket in self.websocket_clients:
            self.websocket_clients.discard(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.websocket_clients)}")
        else:
            logger.debug("Client was not registered, skipping unregister")
        
    async def _cleanup_disconnected_clients(self):
        """Remove any clients that are no longer connected"""
        if not self.websocket_clients:
            return
            
        disconnected = set()
        for client in self.websocket_clients:
            # Check if the client is closed using the proper way
            try:
                # Try to ping the client to see if it's still connected
                await client.ping()
            except websockets.exceptions.ConnectionClosed:
                # If ping fails with ConnectionClosed, the client is disconnected
                disconnected.add(client)
            except websockets.exceptions.ConnectionClosedError:
                # If ping fails with ConnectionClosedError, the client is disconnected
                disconnected.add(client)
            except Exception as e:
                # If any other exception occurs, assume the client is disconnected
                logger.debug(f"Error pinging client, assuming disconnected: {e}")
                disconnected.add(client)
        
        if disconnected:
            self.websocket_clients -= disconnected
            logger.info(f"Cleaned up {len(disconnected)} disconnected clients. Remaining: {len(self.websocket_clients)}")
        
        # Also return the number of disconnected clients for monitoring
        return len(disconnected)
        
    async def broadcast_message(self, message):
        """Broadcast message to all connected clients"""
        if not self.websocket_clients:
            return
            
        # Clean up disconnected clients first
        await self._cleanup_disconnected_clients()
        
        if not self.websocket_clients:
            return
            
        # Send message to all connected clients
        disconnected = set()
        for client in self.websocket_clients:
            try:
                # Check if client is still open before sending
                await client.ping()
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except websockets.exceptions.ConnectionClosedError:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                # Only mark as disconnected for connection-related errors
                if "connection" in str(e).lower() or "closed" in str(e).lower():
                    disconnected.add(client)
        
        # Clean up disconnected clients
        if disconnected:
            self.websocket_clients -= disconnected
            logger.debug(f"Removed {len(disconnected)} disconnected clients during broadcast")
    
    def setup_jarvis_callbacks(self):
        """Setup callbacks to capture Jarvis events"""
        if not self.jarvis:
            return
            
        # Store the current accumulated response to avoid duplicates
        self._current_response = ""
        self._response_sent = False
        
        def web_stream_callback(text):
            # Send chunks as they arrive from LLM for fast streaming
            logger.debug(f"Stream callback received: {repr(text)}")
            asyncio.create_task(self.broadcast_message({
                "type": "assistant_stream",
                "text": text
            }))
        
        def web_user_text_callback(text):
            logger.info(f"User text callback received: {repr(text)}")
            # Reset response tracking for new user input (both voice and text)
            self._response_sent = False
            self._current_response = ""
            asyncio.create_task(self.broadcast_message({
                "type": "user_text", 
                "text": text
            }))
        
        def web_final_answer_callback(text):
            # Only send final answer once, and avoid sending if streaming was used
            logger.info(f"🟢 Final answer callback received: {repr(text[:100])}, response_sent: {self._response_sent}")
            if not self._response_sent:
                self._response_sent = True
                logger.info(f"🟢 Broadcasting final answer to {len(self.websocket_clients)} clients")
                asyncio.create_task(self.broadcast_message({
                    "type": "assistant_final",
                    "text": text
                }))
            else:
                logger.info("🟡 Final answer callback ignored - response already sent")
        
        # Set the callbacks without preserving originals to avoid conflicts
        self.jarvis.on_stream_callback = web_stream_callback
        self.jarvis.on_user_text_callback = web_user_text_callback
        self.jarvis.on_final_answer_callback = web_final_answer_callback
        
    async def handle_client_message(self, websocket, message_data):
        """Handle messages from web clients"""
        message_type = message_data.get("type")
        logger.debug(f"Received message from client: {message_type}")
        
        if message_type == "text_input":
            # Process text input from web client
            text = message_data.get("text", "").strip()
            if text and self.jarvis:
                # Process the text input without duplicating user message broadcast
                # The user message will be broadcasted by the callback
                asyncio.create_task(self.process_text_input(text))
                
        elif message_type == "enable_mic":
            # Enable microphone mode
            if self.jarvis:
                # Only act if mic wasn't already enabled
                if not self.jarvis.mic_enabled:
                    try:
                        await self.jarvis.enable_microphone()
                    except Exception as e:
                        logger.error(f"Failed to enable microphone: {e}")
                    logger.info("🎤 [MIC] Microphone enabled - STT will now process voice input")
                    print("🎤 [MIC] Microphone enabled - STT will now process voice input")
                else:
                    logger.debug("🎤 [MIC] Microphone already enabled")
            await self.broadcast_message({
                "type": "mode_change", 
                "mode": "listening"
            })
            
        elif message_type == "disable_mic":
            # Disable microphone mode  
            if self.jarvis:
                # Only act if mic wasn't already disabled
                if self.jarvis.mic_enabled:
                    try:
                        await self.jarvis.disable_microphone()
                    except Exception as e:
                        logger.error(f"Failed to disable microphone: {e}")
                    logger.info("🎤 [MIC] Microphone disabled - STT will ignore voice input")
                    print("🎤 [MIC] Microphone disabled - STT will ignore voice input")
                else:
                    logger.debug("🎤 [MIC] Microphone already disabled")
            await self.broadcast_message({
                "type": "mode_change",
                "mode": "idle"
            })
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def process_text_input(self, text):
        """Process text input and generate response"""
        try:
            logger.info(f"Processing text input: {repr(text)}")
            # Reset response tracking for new request
            self._response_sent = False
            self._current_response = ""
            
            # Notify thinking mode
            await self.broadcast_message({
                "type": "mode_change",
                "mode": "thinking"
            })
            
            # Short delay to show thinking state
            await asyncio.sleep(0.5)
            
            # Set speaking mode
            await self.broadcast_message({
                "type": "mode_change",
                "mode": "speaking",
                "intensity": 0.8
            })
            
            # Generate response using Jarvis
            if self.jarvis:
                logger.info("🔄 Generating response...")
                # Use web text processing that doesn't trigger user text callback
                async with self.jarvis.conversation_lock:
                    await self.jarvis.process_web_text_input(text)
                logger.info("🔄 Response processing completed")
                
                # No timeout needed - let the natural callback flow handle it
                
                # Don't send final response here as it's already handled by the callback
                # The final callback will be triggered by the brain.py
            
            # Return to idle mode
            await asyncio.sleep(1)
            await self.broadcast_message({
                "type": "mode_change",
                "mode": "idle"
            })
            
        except Exception as e:
            logger.error(f"Error processing text input: {e}")
            await self.broadcast_message({
                "type": "assistant_final",
                "text": "Sorry, I encountered an error processing your request."
            })
            await self.broadcast_message({
                "type": "mode_change",
                "mode": "idle"
            })
    
    def _safe_stream_callback(self, char):
        """Safely handle streaming callback"""
        try:
            asyncio.create_task(self.broadcast_message({
                "type": "assistant_stream",
                "text": char
            }))
        except Exception as e:
            logger.error(f"Stream callback error: {e}")
    
    async def audio_level_monitor(self):
        """Monitor audio levels and send updates"""
        cleanup_counter = 0
        while self.is_running:
            try:
                # Periodically clean up disconnected clients (every 500 iterations = every 50 seconds)
                cleanup_counter += 1
                if cleanup_counter >= 500:
                    disconnected_count = await self._cleanup_disconnected_clients()
                    if disconnected_count and disconnected_count > 0:
                        logger.info(f"Audio monitor cleaned up {disconnected_count} disconnected clients")
                    cleanup_counter = 0
                
                # Simulate audio level monitoring
                # In a real implementation, this would get actual audio levels
                if self.jarvis and self.jarvis.is_speaking:
                    # Simulate varying audio levels during speech
                    import random
                    level = 0.3 + random.random() * 0.5  # Random level between 0.3-0.8
                    
                    await self.broadcast_message({
                        "type": "audio_level",
                        "mode": "speaking", 
                        "level": level
                    })
                
                await asyncio.sleep(0.1)  # Update 10 times per second
                
            except Exception as e:
                logger.error(f"Audio level monitor error: {e}")
                await asyncio.sleep(1)
    
    async def websocket_handler(self, websocket):
        """Handle WebSocket connections"""
        # Check if the websocket is still open before registering
        try:
            await websocket.ping()
        except:
            logger.debug("WebSocket connection already closed during handshake")
            return
            
        await self.register_client(websocket)
        
        try:
            # Send initial status only if the connection is still open
            try:
                await websocket.ping()
                await websocket.send(json.dumps({
                    "type": "mode_change",
                    "mode": "idle"
                }))
            except:
                logger.debug("Could not send initial status, connection closed")
                await self.unregister_client(websocket)
                return
            
            # Track if we've already sent the initial mic enable message
            mic_enabled_sent = False
            
            async for message in websocket:
                try:
                    message_data = json.loads(message)
                    await self.handle_client_message(websocket, message_data)
                    
                    # If this is the first enable_mic message, note it
                    if message_data.get("type") == "enable_mic" and not mic_enabled_sent:
                        mic_enabled_sent = True
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.debug(f"Client connection closed unexpectedly: {e}")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self, host="localhost", port=8765):
        """Start the WebSocket server"""
        logger.info(f"Starting Jarvis WebSocket server on {host}:{port}")
        
        # Check if port is available
        if not is_port_available(host, port):
            logger.error(f"❌ Port {port} is already in use on {host}")
            logger.error("Please stop the application using this port or use a different port.")
            logger.error("You can change the port by modifying the start_server call in main()")
            return
            
        try:
            # Initialize Jarvis core with error handling
            try:
                self.jarvis = JarvisCore()
                # Start with microphone disabled in web mode; UI will explicitly enable it
                self.jarvis.mic_enabled = False
                self.setup_jarvis_callbacks()
            except Exception as e:
                logger.error(f"Failed to initialize Jarvis core: {e}")
                logger.info("This might be due to another instance of Jarvis already running")
                logger.info("Please make sure no other Jarvis instances are running")
                return
            
            # Start audio level monitoring
            self.is_running = True
            audio_task = asyncio.create_task(self.audio_level_monitor())
            
            # Start WebSocket server with better error handling
            server = await websockets.serve(
                self.websocket_handler, 
                host, 
                port,
                ping_interval=60,  # Increase ping interval to reduce overhead (1 minute)
                ping_timeout=45,   # Increase ping timeout (45 seconds)
                close_timeout=10,  # Reduce close timeout
                max_size=2**22,    # Increase max message size to 4MB
                max_queue=16,      # Reduce message queue size to prevent memory issues
                # Add better error handling for invalid requests
                process_request=self._handle_invalid_request
            )
            
            logger.info(f"✅ Jarvis WebSocket server successfully started on ws://{host}:{port}")
            logger.info("WebSocket server is now listening for connections...")
            
            # Start Jarvis after WebSocket server is ready
            jarvis_task = asyncio.create_task(self.start_jarvis())
            
            try:
                await asyncio.gather(jarvis_task, audio_task, server.wait_closed())
            except Exception as e:
                logger.error(f"Error in server tasks: {e}")
            finally:
                self.is_running = False
                if self.jarvis:
                    try:
                        await self.jarvis.shutdown()
                    except Exception as shutdown_error:
                        logger.error(f"Error during Jarvis shutdown: {shutdown_error}")
                        
        except websockets.exceptions.InvalidMessage as e:
            logger.error(f"Invalid WebSocket message received: {e}")
            logger.info("This might be caused by health checks or non-WebSocket connections to the port")
        except OSError as e:
            if "Address already in use" in str(e) or "Only one usage of each socket address" in str(e):
                logger.error(f"❌ Port {port} is already in use. Please stop the application using this port or use a different port.")
                logger.error("You can change the port by modifying the start_server call in main()")
                logger.info("This might also happen if another instance of Jarvis is already running")
            else:
                logger.error(f"❌ OS Error starting WebSocket server: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket server: {e}")
            logger.error(f"Error details: {type(e).__name__}: {e}")
            self.is_running = False
            if self.jarvis:
                try:
                    await self.jarvis.shutdown()
                except Exception as shutdown_error:
                    logger.error(f"Error during Jarvis shutdown: {shutdown_error}")
    
    async def _handle_invalid_request(self, path, request_headers):
        """Handle invalid HTTP requests (like health checks or browser preflight requests)"""
        # Log the invalid request for debugging
        try:
            headers_dict = dict(request_headers)
            logger.debug(f"Invalid HTTP request received: {path}, Headers: {headers_dict}")
        except Exception as e:
            logger.debug(f"Invalid HTTP request received: {path}, Headers: (could not parse - {e})")
        
        # If this looks like a health check or browser request, send a simple response
        try:
            headers_dict = dict(request_headers)
            user_agent = headers_dict.get("User-Agent", "")
            if "curl" in user_agent or "Mozilla" in user_agent or "Health" in user_agent or "kube-probe" in user_agent:
                # Send a simple HTTP response for health checks or browser requests
                return (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 2\r\n"
                    "\r\n"
                    "OK"
                )
        except Exception as e:
            logger.debug(f"Could not process request headers for health check: {e}")
        
        # Return None to let the default handler deal with it
        return None
    
    async def start_jarvis(self):
        """Start Jarvis core system"""
        try:
            if self.jarvis:
                await self.jarvis.start()
        except Exception as e:
            logger.error(f"Error starting Jarvis: {e}")

def main():
    """Main entry point"""
    server = JarvisWebServer()
    
    try:
        logger.info("Starting Jarvis Web Server...")
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
