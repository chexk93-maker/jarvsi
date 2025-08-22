#!/usr/bin/env python3
"""
Simple launcher for JARVIS Blob GUI
"""

import subprocess
import sys
import time
import os

def main():
    print("Starting JARVIS with Animated Blob GUI...")
    print("=" * 50)
    
    # Change to JARVIS directory
    os.chdir(r"C:\Users\Krish\jarvis")
    
    # Start the Python backend
    print("Starting Python WebSocket server...")
    backend_process = subprocess.Popen([
        sys.executable, "web_server.py"
    ], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    # Wait a moment for backend to start
    print("Waiting for backend to initialize...")
    time.sleep(3)
    
    # Start the React frontend
    print("Starting React development server...")
    frontend_process = subprocess.Popen([
        "cmd", "/c", "npm start"
    ], cwd=r"C:\Users\Krish\jarvis\web_gui", 
    creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    print("\nJARVIS Blob GUI is starting!")
    print("Backend: ws://localhost:8765")
    print("Frontend: http://localhost:3000")
    print("\nThe frontend will open in your browser automatically.")
    print("Press Ctrl+C to stop all services.")
    
    try:
        # Keep the launcher running
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("Backend process stopped!")
                break
            if frontend_process.poll() is not None:
                print("Frontend process stopped!")
                break
                
    except KeyboardInterrupt:
        print("\nStopping JARVIS services...")
        
        # Terminate processes
        if backend_process.poll() is None:
            backend_process.terminate()
        if frontend_process.poll() is None:
            frontend_process.terminate()
        
        print("All services stopped.")

if __name__ == "__main__":
    main()