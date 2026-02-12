#!/usr/bin/env python
"""
Unified Backend Server Launcher
Starts both FastAPI backend (port 8000) and WebSocket server (port 8001)
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

# Configuration
BACKEND_DIR = Path(__file__).parent
FASTAPI_PORT = 8000
WEBSOCKET_PORT = 8001
BACKEND_API_URL = f"http://localhost:{FASTAPI_PORT}"

class BackendLauncher:
    def __init__(self):
        self.fastapi_process = None
        self.websocket_process = None
        self.is_windows = sys.platform == 'win32'
        
    def start_fastapi(self):
        """Start FastAPI server"""
        print(f"\n{'='*60}")
        print(f"Starting FastAPI Server (Port {FASTAPI_PORT})...")
        print(f"{'='*60}\n")
        
        try:
            if self.is_windows:
                # Windows: Use CREATE_NEW_CONSOLE for separate window
                self.fastapi_process = subprocess.Popen(
                    [sys.executable, "run.py"],
                    cwd=str(BACKEND_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # Unix: Run in background
                self.fastapi_process = subprocess.Popen(
                    [sys.executable, "run.py"],
                    cwd=str(BACKEND_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            print(f"✓ FastAPI process started (PID: {self.fastapi_process.pid})")
            return True
        except Exception as e:
            print(f"✗ Failed to start FastAPI: {e}")
            return False
    
    def start_websocket(self):
        """Start WebSocket server"""
        print(f"\n{'='*60}")
        print(f"Starting WebSocket Server (Port {WEBSOCKET_PORT})...")
        print(f"{'='*60}\n")
        
        try:
            if self.is_windows:
                # Windows: Use CREATE_NEW_CONSOLE for separate window
                self.websocket_process = subprocess.Popen(
                    ['node', 'app.js'],
                    cwd=str(BACKEND_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    env={**os.environ, 'BACKEND_API_URL': BACKEND_API_URL}
                )
            else:
                # Unix: Run in background
                self.websocket_process = subprocess.Popen(
                    ['node', 'app.js'],
                    cwd=str(BACKEND_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, 'BACKEND_API_URL': BACKEND_API_URL}
                )
            
            print(f"✓ WebSocket process started (PID: {self.websocket_process.pid})")
            return True
        except Exception as e:
            print(f"✗ Failed to start WebSocket server: {e}")
            return False
    
    def wait_for_servers(self):
        """Wait for servers to become ready"""
        import requests
        
        print("\n" + "="*60)
        print("Waiting for servers to be ready...")
        print("="*60 + "\n")
        
        # Check FastAPI
        for attempt in range(30):
            try:
                response = requests.get(f"http://localhost:{FASTAPI_PORT}/", timeout=2)
                if response.status_code == 200:
                    print("✓ FastAPI server is ready")
                    break
            except:
                if attempt < 29:
                    print(f"  Waiting for FastAPI... ({attempt + 1}/30)")
                    time.sleep(1)
        else:
            print("✗ FastAPI server did not respond")
        
        # Check WebSocket (just verify process is running)
        if self.websocket_process and self.websocket_process.poll() is None:
            print("✓ WebSocket server is running")
        else:
            print("✗ WebSocket server failed to start")
    
    def run(self):
        """Start both servers"""
        print("\n╔════════════════════════════════════════════════════╗")
        print("║  Voice Biometric Backend - Unified Launcher       ║")
        print("║                                                    ║")
        print("║  Starting both FastAPI and WebSocket servers...  ║")
        print("╚════════════════════════════════════════════════════╝")
        
        # Check if Node.js is installed
        try:
            subprocess.run(['node', '--version'], capture_output=True, check=True)
        except:
            print("\n✗ Error: Node.js is not installed or not in PATH")
            print("   Please install Node.js from https://nodejs.org")
            return False
        
        # Start FastAPI
        if not self.start_fastapi():
            return False
        
        time.sleep(2)
        
        # Start WebSocket server
        if not self.start_websocket():
            self.stop()
            return False
        
        time.sleep(2)
        
        # Wait for servers to be ready
        try:
            self.wait_for_servers()
        except ImportError:
            print("\n⚠️  Could not verify server readiness (requests module needed)")
            print("   Install with: pip install requests")
        
        # Display summary
        print("\n" + "="*60)
        print("BACKEND SERVERS STARTED SUCCESSFULLY")
        print("="*60)
        print(f"\nAPI Server:        http://localhost:{FASTAPI_PORT}")
        print(f"WebSocket Server:  ws://localhost:{WEBSOCKET_PORT}")
        print(f"\nDocs:              http://localhost:{FASTAPI_PORT}/docs")
        print(f"\nFastAPI PID:       {self.fastapi_process.pid}")
        print(f"WebSocket PID:     {self.websocket_process.pid}")
        print("\nPress Ctrl+C to shutdown all servers\n")
        print("="*60 + "\n")
        
        return True
    
    def stop(self):
        """Stop both servers"""
        print("\n\nShutting down servers...\n")
        
        if self.fastapi_process and self.fastapi_process.poll() is None:
            try:
                print(f"Stopping FastAPI (PID {self.fastapi_process.pid})...")
                self.fastapi_process.terminate()
                self.fastapi_process.wait(timeout=5)
                print("✓ FastAPI stopped")
            except:
                self.fastapi_process.kill()
                print("✓ FastAPI killed")
        
        if self.websocket_process and self.websocket_process.poll() is None:
            try:
                print(f"Stopping WebSocket (PID {self.websocket_process.pid})...")
                self.websocket_process.terminate()
                self.websocket_process.wait(timeout=5)
                print("✓ WebSocket server stopped")
            except:
                self.websocket_process.kill()
                print("✓ WebSocket server killed")
        
        print("\nAll servers shut down\n")

def main():
    launcher = BackendLauncher()
    
    if not launcher.run():
        sys.exit(1)
    
    # Handle Ctrl+C and graceful shutdown
    def signal_handler(sig, frame):
        launcher.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
            # Monitor processes
            if launcher.fastapi_process and launcher.fastapi_process.poll() is not None:
                print("\n⚠️  FastAPI server crashed!")
            if launcher.websocket_process and launcher.websocket_process.poll() is not None:
                print("\n⚠️  WebSocket server crashed!")
    except KeyboardInterrupt:
        launcher.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
