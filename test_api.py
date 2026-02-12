#!/usr/bin/env python3
"""
Test script for voice enrollment and verification
Tests the complete workflow: enroll voice -> verify voice
"""

import requests
import time
import subprocess
import sys
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
BACKEND_DIR = Path(__file__).parent / "backend"
TEST_AUDIO_FILE = Path(__file__).parent / "test_voice.wav"
TEST_PHONE_NUMBER = "1234567890"  # Test phone number

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_section(title):
    """Print a formatted section title"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{Colors.END}\n")

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.YELLOW}→ {message}{Colors.END}")

def wait_for_api(max_retries=30, delay=1):
    """Wait for API to be ready"""
    print_info("Waiting for API to be ready...")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=2)
            if response.status_code == 200:
                print_success("API is ready!")
                return True
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print_info(f"Attempt {attempt + 1}/{max_retries}. Retrying in {delay}s...")
                time.sleep(delay)
            continue
    
    return False

def start_backend_server():
    """Start the FastAPI backend server"""
    print_info("Starting backend server...")
    
    # Check if server is already running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=2)
        if response.status_code == 200:
            print_success("Backend server is already running")
            return None
    except requests.exceptions.ConnectionError:
        pass
    
    # Start the server
    try:
        # On Windows, start in a new process
        if sys.platform == "win32":
            process = subprocess.Popen(
                ["python", "main.py"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
        else:
            process = subprocess.Popen(
                ["python", "main.py"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print_success("Backend server started (PID: {})".format(process.pid))
        return process
    except Exception as e:
        print_error(f"Failed to start backend server: {e}")
        return None

def test_enrollment():
    """Test voice enrollment"""
    print_section("STEP 1: VOICE ENROLLMENT")
    
    if not TEST_AUDIO_FILE.exists():
        print_error(f"Test audio file not found: {TEST_AUDIO_FILE}")
        return False
    
    print_info(f"Loading audio file: {TEST_AUDIO_FILE}")
    print_info(f"Phone number: {TEST_PHONE_NUMBER}")
    
    try:
        with open(TEST_AUDIO_FILE, 'rb') as f:
            files = {
                'file': (TEST_AUDIO_FILE.name, f, 'audio/wav')
            }
            data = {
                'phone_number': TEST_PHONE_NUMBER
            }
            
            print_info("Sending enrollment request...")
            response = requests.post(
                f"{API_BASE_URL}/enroll",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Enrollment successful!")
            print(f"  Response: {result['message']}")
            print(f"  Phone: {result['phone_number']}")
            if result.get('vector_id'):
                print(f"  Vector ID: {result['vector_id']}")
            return True
        else:
            print_error(f"Enrollment failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Enrollment error: {e}")
        return False

def test_verification():
    """Test voice verification"""
    print_section("STEP 2: VOICE VERIFICATION")
    
    if not TEST_AUDIO_FILE.exists():
        print_error(f"Test audio file not found: {TEST_AUDIO_FILE}")
        return False
    
    print_info(f"Verifying with same audio file: {TEST_AUDIO_FILE}")
    print_info(f"Phone number: {TEST_PHONE_NUMBER}")
    
    try:
        with open(TEST_AUDIO_FILE, 'rb') as f:
            files = {
                'file': (TEST_AUDIO_FILE.name, f, 'audio/wav')
            }
            data = {
                'phone_number': TEST_PHONE_NUMBER
            }
            
            print_info("Sending verification request...")
            response = requests.post(
                f"{API_BASE_URL}/verify",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Verification successful!")
            print(f"  Phone: {result['phone_number']}")
            print(f"  Similarity Score: {result['similarity_score']:.4f}")
            print(f"  Threshold: {result['threshold']:.4f}")
            print(f"  Match Result: {'✓ MATCH' if result['is_match'] else '✗ NO MATCH'}")
            
            if result['is_match']:
                print_success("Voice verified successfully!")
                return True
            else:
                print_error("Voice does not match enrolled identity")
                return False
        else:
            print_error(f"Verification failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Verification error: {e}")
        return False

def test_check_enrollment():
    """Test enrollment status check"""
    print_section("STEP 3: CHECK ENROLLMENT STATUS")
    
    print_info(f"Checking enrollment status for: {TEST_PHONE_NUMBER}")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/check/{TEST_PHONE_NUMBER}",
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Status check successful!")
            print(f"  Phone: {result['phone_number']}")
            print(f"  Enrolled: {'✓ YES' if result['enrolled'] else '✗ NO'}")
            return result['enrolled']
        else:
            print_error(f"Status check failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Status check error: {e}")
        return False

def main():
    """Run all tests"""
    print_section("VOICE BIOMETRIC API - TEST SUITE")
    print_info("Starting complete workflow test: Enrollment → Verification → Status Check")
    
    server_process = None
    
    try:
        # Start backend server
        server_process = start_backend_server()
        time.sleep(2)
        
        # Wait for API to be ready
        if not wait_for_api():
            print_error("Failed to connect to API after multiple retries")
            return False
        
        # Run tests
        print_info("\nRunning test sequence...\n")
        
        # Test 1: Health check
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=5)
            print_success(f"Health check passed: {response.json()['message']}")
        except Exception as e:
            print_error(f"Health check failed: {e}")
            return False
        
        # Test 2: Enrollment
        enrollment_ok = test_enrollment()
        if not enrollment_ok:
            return False
        
        time.sleep(1)
        
        # Test 3: Verification
        verification_ok = test_verification()
        if not verification_ok:
            return False
        
        time.sleep(1)
        
        # Test 4: Check status
        status_ok = test_check_enrollment()
        
        # Summary
        print_section("TEST SUMMARY")
        print_success("✓ Enrollment test passed")
        print_success("✓ Verification test passed")
        print_success("✓ Status check test passed")
        print_success("\n🎉 All tests passed successfully!")
        
        return True
        
    except KeyboardInterrupt:
        print_error("\nTests interrupted by user")
        return False
    except Exception as e:
        print_error(f"Unexpected error during testing: {e}")
        return False
    finally:
        # Keep server running if it was started by us
        if server_process:
            print_info("\nBackend server is still running in the new window")
            print_info("Press Ctrl+C in the backend window to stop it")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
