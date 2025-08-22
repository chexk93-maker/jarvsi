import asyncio
import signal
import sys
import logging
from core.brain import JarvisCore

# Suppress faster_whisper logs
logging.getLogger("faster_whisper").setLevel(logging.WARNING)
logging.getLogger("root").setLevel(logging.WARNING)

async def main():
    """Main entry point for Jarvis AI Assistant"""
    print("🚀 [JARVIS] Starting AI Assistant...")
    
    # Initialize Jarvis core
    jarvis = JarvisCore() 
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        print("\n🚪 [EXIT] Shutting down gracefully...")
        asyncio.create_task(jarvis.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start Jarvis
        await jarvis.start()
    except KeyboardInterrupt:
        print("\n🚪 [EXIT] Program terminated.")
    except Exception as e:
        print(f"❌ [ERROR] Fatal error: {e}")
    finally:
        await jarvis.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

