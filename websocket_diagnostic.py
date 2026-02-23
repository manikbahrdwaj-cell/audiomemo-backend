#!/usr/bin/env python3
"""
WebSocket Connection Diagnostic Tool
Checks if all services are running and accessible
"""

import socket
import requests
import json
import sys
from urllib.parse import urljoin

def check_port(host, port, name):
    """Check if a service is running on a specific port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ {name} is running on {host}:{port}")
            return True
        else:
            print(f"✗ {name} is NOT running on {host}:{port}")
            return False
    except Exception as e:
        print(f"✗ Error checking {name}: {str(e)}")
        return False

def check_backend_health(url):
    """Check backend health endpoint"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Backend health check passed: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Backend health check failed: {str(e)}")
        return False

def check_frontend_running(url):
    """Check if frontend is serving"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✓ Frontend is running and responding")
            return True
        else:
            print(f"✗ Frontend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Frontend not responding: {str(e)}")
        return False

def check_env_files():
    """Check for required environment files"""
    import os
    
    print("\n" + "=" * 60)
    print("Checking Configuration Files")
    print("=" * 60 + "\n")
    
    configs = {
        "Root .env": ".env",
        "Backend .env": "backend/.env",
        "Frontend .env.local": "frontend/.env.local",
    }
    
    for name, path in configs.items():
        if os.path.exists(path):
            print(f"✓ {name} found at {path}")
        else:
            print(f"✗ {name} NOT found at {path}")

def main():
    print("\n" + "=" * 60)
    print("Voice Biometric - WebSocket Diagnostic")
    print("=" * 60 + "\n")
    
    # Check Python environment
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Python Path: {sys.executable}\n")
    
    # Check ports
    print("=" * 60)
    print("Checking Services")
    print("=" * 60 + "\n")
    
    results = {}
    results['mongodb'] = check_port('localhost', 27017, 'MongoDB')
    results['backend'] = check_port('localhost', 8000, 'Backend API')
    results['frontend'] = check_port('localhost', 3000, 'Frontend Dev Server')
    
    # More detailed checks if services are running
    print("\n" + "=" * 60)
    print("Service Health Checks")
    print("=" * 60 + "\n")
    
    if results['backend']:
        check_backend_health("http://localhost:8000")
    
    if results['frontend']:
        check_frontend_running("http://localhost:3000")
    
    # Check environment files
    check_env_files()
    
    # Summary
    print("\n" + "=" * 60)
    print("Diagnostic Summary")
    print("=" * 60 + "\n")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("✓ All services are running! You should be good to go.")
        print("\nVisit: http://localhost:3000 to start using the app")
    else:
        print("✗ Some services are not running.\n")
        
        if not results['mongodb']:
            print("To start MongoDB:")
            print("  mongod")
        
        if not results['backend']:
            print("\nTo start Backend:")
            print("  cd backend")
            print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        
        if not results['frontend']:
            print("\nTo start Frontend:")
            print("  cd frontend")
            print("  npm start")
    
    print("\n" + "=" * 60)
    print("WebSocket Connection Details")
    print("=" * 60)
    print("""
Frontend connects to: ws://localhost:8000/ws/verify/PHONE_NUMBER

Expected flow:
  1. Frontend on http://localhost:3000
  2. User enters phone number
  3. Clicks "Initialize Verification"
  4. Connection to backend WebSocket: ws://localhost:8000/ws/verify/PHONE_NUMBER
  5. Backend retrieves user's voice profile from MongoDB
  6. Session created and ready for audio chunks
  
If you get a timeout error:
  ✓ Make sure backend is running on port 8000
  ✓ Make sure MongoDB is running on port 27017
  ✓ Check that frontend .env.local has correct backend URL
  
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during diagnostic: {str(e)}")
        sys.exit(1)
