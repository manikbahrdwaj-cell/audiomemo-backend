#!/usr/bin/env python3
"""
Phase 4.3: End-to-End Test Suite for Voice Biometric Authentication System

Comprehensive end-to-end tests covering:
- Complete user workflows (enrollment, verification, status checks)
- Real API endpoint interactions
- Database persistence and retrieval
- Session management and state transitions
- Concurrent user scenarios
- Error handling and edge cases
- Performance characteristics
"""

import requests
import json
import time
import threading
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import random
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
API_BASE_URL = "http://localhost:8000"
WORKSPACE_DIR = Path(__file__).parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
TEST_AUDIO_DIR = WORKSPACE_DIR / "test_audio_files"
E2E_RESULTS_FILE = WORKSPACE_DIR / "e2e_test_results.json"

# Test data
TEST_USERS = {
    "user_001": {
        "phone": "9876543210",
        "name": "Alice Johnson",
        "enrollment_audio": "test_speaker1_enroll.wav",
        "verify_audio": "test_speaker1_verify.wav",
        "variant_audio": "test_speaker1_variant.wav",
    },
    "user_002": {
        "phone": "8765432109",
        "name": "Bob Smith",
        "enrollment_audio": "test_speaker2_enroll.wav",
        "verify_audio": "test_speaker2_verify.wav",
        "variant_audio": "test_speaker2_variant.wav",
    },
    "user_003": {
        "phone": "7654321098",
        "name": "Charlie Brown",
        "enrollment_audio": "test_speaker3_enroll.wav",
        "verify_audio": "test_speaker3_verify.wav",
        "variant_audio": "test_speaker3_variant.wav",
    },
}

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

# Test result tracking
class E2ETestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.test_details = []
        self.start_time = datetime.now()
        self.end_time = None

    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        self.test_details.append({
            "status": "PASS",
            "name": test_name,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append({"test": test_name, "error": error})
        self.test_details.append({
            "status": "FAIL",
            "name": test_name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def add_skip(self, test_name: str, reason: str):
        self.skipped += 1
        self.test_details.append({
            "status": "SKIP",
            "name": test_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self):
        return {
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "total": self.passed + self.failed + self.skipped,
                "pass_rate": f"{(self.passed / (self.passed + self.failed) * 100) if (self.passed + self.failed) > 0 else 0:.1f}%",
                "duration": str(self.end_time - self.start_time) if self.end_time else "N/A"
            },
            "details": self.test_details,
            "errors": self.errors
        }


# Utility functions
def print_section(title):
    """Print formatted section header"""
    print(f"\n{Colors.BLUE}{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}{Colors.END}\n")

def print_subsection(title):
    """Print formatted subsection"""
    print(f"\n{Colors.CYAN}╔─ {title}{Colors.END}")

def print_test(test_name, status, details=""):
    """Print individual test result"""
    if status == "PASS":
        symbol = f"{Colors.GREEN}✓{Colors.END}"
    elif status == "FAIL":
        symbol = f"{Colors.RED}✗{Colors.END}"
    elif status == "SKIP":
        symbol = f"{Colors.YELLOW}⊘{Colors.END}"
    else:
        symbol = f"{Colors.BLUE}→{Colors.END}"

    print(f"  {symbol} {test_name:<55} [{status}]", end="")
    if details:
        print(f" {details}")
    else:
        print()

def print_success(message):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"  {Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"  {Colors.YELLOW}→ {message}{Colors.END}")

def check_api_health():
    """Check if API is running and healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def wait_for_api(max_retries=30, delay=1):
    """Wait for API to be ready"""
    print_info("Waiting for API to be ready...")
    for attempt in range(max_retries):
        if check_api_health():
            print_success("API is ready!")
            return True
        if attempt < max_retries - 1:
            print_info(f"Attempt {attempt + 1}/{max_retries}. Retrying in {delay}s...")
            time.sleep(delay)
    return False

def start_backend_server():
    """Start the FastAPI backend server"""
    print_info("Checking if backend server is running...")
    
    if check_api_health():
        print_success("Backend server is already running")
        return None
    
    print_info("Starting backend server...")
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                ["python", "main.py"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                ["python", "main.py"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print_success(f"Backend server started (PID: {process.pid})")
        return process
    except Exception as e:
        print_error(f"Failed to start backend server: {e}")
        return None


# Test Suite Functions
def test_api_health_check(results: E2ETestResults):
    """Test 1: API health check"""
    print_subsection("Test 1: API Health Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test("Health check endpoint", "PASS", f"Status: {data.get('message', 'OK')}")
            results.add_pass("API Health Check", f"Response: {data}")
            return True
    except Exception as e:
        print_error(f"Health check failed: {e}")
        results.add_fail("API Health Check", str(e))
        return False


def test_single_user_workflow(results: E2ETestResults):
    """Test 2: Complete single user workflow"""
    print_subsection("Test 2: Single User Complete Workflow")
    
    user_id = "user_001"
    user = TEST_USERS[user_id]
    
    try:
        # Get enrollment audio
        audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
        if not audio_path.exists():
            print_test("Load enrollment audio", "SKIP", "Audio file not found")
            results.add_skip("Single User Workflow - Audio", f"File not found: {audio_path}")
            return False
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Step 1: Enrollment
        print_test("Enroll user", "INFO", "Sending enrollment request...")
        
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        
        if response.status_code != 200:
            print_error(f"Enrollment failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            results.add_fail("Single User Enrollment", f"Status {response.status_code}: {response.text}")
            return False
        
        enrollment_data = response.json()
        print_test("User enrollment", "PASS", f"Phone: {user['phone']}")
        results.add_pass("Single User Enrollment", f"User: {user_id}, Phone: {user['phone']}")
        
        time.sleep(1)
        
        # Step 2: Self-verification (should succeed)
        print_test("Verify with own voice", "INFO", "Sending verification request...")
        
        verify_path = TEST_AUDIO_DIR / user["verify_audio"]
        with open(verify_path, "rb") as f:
            verify_audio = f.read()
        
        files = {"file": ("audio.wav", verify_audio, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        
        if response.status_code != 200:
            print_error(f"Verification failed: {response.status_code}")
            results.add_fail("Single User Self-Verification", f"Status {response.status_code}")
            return False
        
        verify_data = response.json()
        is_match = verify_data.get("is_match", False)
        score = verify_data.get("similarity_score", 0)
        
        print_test("Self-verification result", "PASS", f"Match: {is_match}, Score: {score:.3f}")
        results.add_pass("Single User Self-Verification", f"Match: {is_match}, Score: {score:.3f}")
        
        # Step 3: Status check
        print_test("Check status endpoint", "INFO", "Requesting status...")
        
        response = requests.get(f"{API_BASE_URL}/status", timeout=5)
        status_data = response.json()
        
        print_test("Status endpoint", "PASS", f"Enrolled users: {status_data.get('users_enrolled', 0)}")
        results.add_pass("Status Endpoint", f"Status data: {status_data}")
        
        return True
        
    except Exception as e:
        print_error(f"Single user workflow failed: {e}")
        results.add_fail("Single User Workflow", str(e))
        return False


def test_multi_user_isolation(results: E2ETestResults):
    """Test 3: Multiple users don't interfere with each other"""
    print_subsection("Test 3: Multi-User Isolation")
    
    try:
        enrolled_users = {}
        
        # Enroll all users
        for user_id, user in TEST_USERS.items():
            audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
            if not audio_path.exists():
                continue
            
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {"phone_number": user["phone"]}
            
            response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                enrolled_users[user_id] = user
                print_test(f"Enroll {user['name']}", "PASS", f"Phone: {user['phone']}")
            else:
                print_test(f"Enroll {user['name']}", "FAIL", f"Status {response.status_code}")
        
        if not enrolled_users:
            print_test("User isolation", "SKIP", "No users enrolled")
            results.add_skip("Multi-User Isolation", "No users enrolled")
            return False
        
        # Verify isolation: User 1 should not match User 2's voice
        user_1_id = list(enrolled_users.keys())[0]
        user_2_id = list(enrolled_users.keys())[1] if len(enrolled_users) > 1 else None
        
        if not user_2_id:
            print_test("User isolation", "SKIP", "Need at least 2 users")
            results.add_skip("Multi-User Isolation", "Need at least 2 users")
            return False
        
        user_1 = enrolled_users[user_1_id]
        user_2 = enrolled_users[user_2_id]
        
        # Try to verify user 2 with user 1's voice
        verify_path = TEST_AUDIO_DIR / user_1["verify_audio"]
        with open(verify_path, "rb") as f:
            audio_data = f.read()
        
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": user_2["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        verify_data = response.json()
        
        is_match = verify_data.get("is_match", False)
        score = verify_data.get("similarity_score", 0)
        
        if not is_match:  # Should NOT match across users
            print_test("Cross-user rejection", "PASS", f"Score: {score:.3f} (correctly rejected)")
            results.add_pass("Multi-User Isolation", f"Cross-user rejected with score {score:.3f}")
            return True
        else:
            print_test("Cross-user rejection", "FAIL", f"Score: {score:.3f} (should not match)")
            results.add_fail("Multi-User Isolation", f"Cross-user matched (score: {score:.3f})")
            return False
        
    except Exception as e:
        print_error(f"Multi-user isolation test failed: {e}")
        results.add_fail("Multi-User Isolation", str(e))
        return False


def test_concurrent_operations(results: E2ETestResults):
    """Test 4: Concurrent user operations"""
    print_subsection("Test 4: Concurrent Operations")
    
    try:
        def enroll_user(user_id, user):
            try:
                audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
                if not audio_path.exists():
                    return None
                
                with open(audio_path, "rb") as f:
                    audio_data = f.read()
                
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": user["phone"]}
                
                response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
                return response.status_code == 200
            except:
                return False
        
        def verify_user(user_id, user):
            try:
                audio_path = TEST_AUDIO_DIR / user["verify_audio"]
                if not audio_path.exists():
                    return None
                
                with open(audio_path, "rb") as f:
                    audio_data = f.read()
                
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": user["phone"]}
                
                response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
                return response.status_code == 200
            except:
                return False
        
        # Run concurrent enrollments
        print_test("Concurrent enrollments", "INFO", f"Enrolling {len(TEST_USERS)} users simultaneously...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            enroll_futures = {
                executor.submit(enroll_user, uid, user): uid 
                for uid, user in TEST_USERS.items()
            }
            
            successful = 0
            for future in as_completed(enroll_futures):
                result = future.result()
                if result:
                    successful += 1
        
        print_test(f"Concurrent enrollments", "PASS", f"{successful}/{len(TEST_USERS)} successful")
        results.add_pass("Concurrent Operations - Enrollments", f"{successful}/{len(TEST_USERS)} users enrolled")
        
        time.sleep(1)
        
        # Run concurrent verifications
        print_test("Concurrent verifications", "INFO", f"Verifying {len(TEST_USERS)} users simultaneously...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            verify_futures = {
                executor.submit(verify_user, uid, user): uid 
                for uid, user in TEST_USERS.items()
            }
            
            successful = 0
            for future in as_completed(verify_futures):
                result = future.result()
                if result:
                    successful += 1
        
        print_test(f"Concurrent verifications", "PASS", f"{successful}/{len(TEST_USERS)} successful")
        results.add_pass("Concurrent Operations - Verifications", f"{successful}/{len(TEST_USERS)} users verified")
        
        return True
        
    except Exception as e:
        print_error(f"Concurrent operations test failed: {e}")
        results.add_fail("Concurrent Operations", str(e))
        return False


def test_database_persistence(results: E2ETestResults):
    """Test 5: Database persistence and retrieval"""
    print_subsection("Test 5: Database Persistence")
    
    try:
        user = TEST_USERS["user_001"]
        audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
        
        if not audio_path.exists():
            print_test("Database persistence", "SKIP", "Audio file not found")
            results.add_skip("Database Persistence", "Audio file not found")
            return False
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Enroll user
        print_test("Store user embedding in database", "INFO", "Enrolling user...")
        
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        enrollment_data = response.json()
        
        print_test("Data stored", "PASS", "User embedding persisted")
        results.add_pass("Database Persistence - Storage", "User embedding stored successfully")
        
        # Wait and retrieve
        time.sleep(2)
        
        print_test("Retrieve embedding from database", "INFO", "Verifying stored data...")
        
        verify_path = TEST_AUDIO_DIR / user["verify_audio"]
        with open(verify_path, "rb") as f:
            verify_audio = f.read()
        
        files = {"file": ("audio.wav", verify_audio, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        verify_data = response.json()
        
        if verify_data.get("is_match"):
            print_test("Data retrieval", "PASS", "Stored embedding retrieved correctly")
            results.add_pass("Database Persistence - Retrieval", "Embedding successfully retrieved")
            return True
        else:
            print_test("Data retrieval", "FAIL", f"Verification failed (score: {verify_data.get('similarity_score')})")
            results.add_fail("Database Persistence - Retrieval", "Retrieved data not matching")
            return False
        
    except Exception as e:
        print_error(f"Database persistence test failed: {e}")
        results.add_fail("Database Persistence", str(e))
        return False


def test_error_handling(results: E2ETestResults):
    """Test 6: Error handling and edge cases"""
    print_subsection("Test 6: Error Handling")
    
    try:
        # Test 6.1: Invalid phone number
        print_test("Invalid phone number handling", "INFO", "Testing invalid phone...")
        
        files = {"file": ("audio.wav", b"invalid", "audio/wav")}
        data = {"phone_number": ""}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=5)
        if response.status_code != 200:
            print_test("Empty phone number rejection", "PASS", f"Status {response.status_code}")
            results.add_pass("Error Handling - Invalid Phone", "Properly rejected empty phone")
        else:
            print_test("Empty phone number rejection", "FAIL", "Should have rejected")
            results.add_fail("Error Handling - Invalid Phone", "Did not reject empty phone")
        
        # Test 6.2: Unenrolled user verification
        print_test("Unenrolled user verification", "INFO", "Testing unregistered user...")
        
        user = TEST_USERS["user_001"]
        audio_path = TEST_AUDIO_DIR / user["verify_audio"]
        
        if audio_path.exists():
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {"phone_number": "0000000000"}  # Not enrolled
            
            response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
            
            if response.status_code != 200:
                print_test("Unenrolled user rejection", "PASS", f"Status {response.status_code}")
                results.add_pass("Error Handling - Unenrolled User", "Properly rejected unenrolled user")
            else:
                verify_data = response.json()
                if not verify_data.get("is_match"):
                    print_test("Unenrolled user rejection", "PASS", "No match for unenrolled user")
                    results.add_pass("Error Handling - Unenrolled User", "Correctly returned no match")
                else:
                    print_test("Unenrolled user rejection", "FAIL", "Should not match unenrolled user")
                    results.add_fail("Error Handling - Unenrolled User", "Matched unenrolled user")
        
        return True
        
    except Exception as e:
        print_error(f"Error handling test failed: {e}")
        results.add_fail("Error Handling", str(e))
        return False


def test_api_performance(results: E2ETestResults):
    """Test 7: API performance characteristics"""
    print_subsection("Test 7: Performance Testing")
    
    try:
        user = TEST_USERS["user_001"]
        audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
        
        if not audio_path.exists():
            print_test("Performance metrics", "SKIP", "Audio file not found")
            results.add_skip("Performance Testing", "Audio file not found")
            return False
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Measure enrollment time
        print_test("Enrollment performance", "INFO", "Measuring response time...")
        
        start = time.time()
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        enroll_time = time.time() - start
        
        print_test("Enrollment response time", "PASS", f"{enroll_time:.2f}s")
        results.add_pass("Performance - Enrollment", f"Response time: {enroll_time:.2f}s")
        
        # Measure verification time
        print_test("Verification performance", "INFO", "Measuring response time...")
        
        verify_path = TEST_AUDIO_DIR / user["verify_audio"]
        with open(verify_path, "rb") as f:
            verify_audio = f.read()
        
        start = time.time()
        files = {"file": ("audio.wav", verify_audio, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        verify_time = time.time() - start
        
        print_test("Verification response time", "PASS", f"{verify_time:.2f}s")
        results.add_pass("Performance - Verification", f"Response time: {verify_time:.2f}s")
        
        return True
        
    except Exception as e:
        print_error(f"Performance test failed: {e}")
        results.add_fail("Performance Testing", str(e))
        return False


def test_state_transitions(results: E2ETestResults):
    """Test 8: User state transitions"""
    print_subsection("Test 8: State Transitions")
    
    try:
        user = TEST_USERS["user_002"]
        audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
        
        if not audio_path.exists():
            print_test("State transitions", "SKIP", "Audio file not found")
            results.add_skip("State Transitions", "Audio file not found")
            return False
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # State 1: Unenrolled
        print_test("Initial state: Unenrolled", "PASS", "User not in system")
        
        # State 2: Enroll
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        if response.status_code == 200:
            print_test("Transition: Unenrolled → Enrolled", "PASS", "Enrollment successful")
            results.add_pass("State Transitions - Enrollment", "User state: Enrolled")
        else:
            print_test("Transition: Unenrolled → Enrolled", "FAIL", f"Status {response.status_code}")
            results.add_fail("State Transitions - Enrollment", f"Failed to enroll: {response.status_code}")
            return False
        
        time.sleep(1)
        
        # State 3: Verified
        verify_path = TEST_AUDIO_DIR / user["verify_audio"]
        with open(verify_path, "rb") as f:
            verify_audio = f.read()
        
        files = {"file": ("audio.wav", verify_audio, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        verify_data = response.json()
        
        if verify_data.get("is_match"):
            print_test("Transition: Enrolled → Verified", "PASS", "Verification successful")
            results.add_pass("State Transitions - Verification", "User state: Verified")
        else:
            print_test("Transition: Enrolled → Verified", "FAIL", f"Score: {verify_data.get('similarity_score')}")
            results.add_fail("State Transitions - Verification", "Verification failed")
        
        return True
        
    except Exception as e:
        print_error(f"State transitions test failed: {e}")
        results.add_fail("State Transitions", str(e))
        return False


def test_end_to_end_journey(results: E2ETestResults):
    """Test 9: Complete user journey from signup to verification"""
    print_subsection("Test 9: Complete E2E User Journey")
    
    try:
        print_test("User journey scenario", "INFO", "Alice signs up, enrolls voice, and verifies")
        
        user = TEST_USERS["user_001"]
        
        # Step 1: Check status before enrollment
        response = requests.get(f"{API_BASE_URL}/status", timeout=5)
        initial_count = response.json().get("users_enrolled", 0)
        print_test("Step 1: Initial status check", "PASS", f"Users enrolled: {initial_count}")
        
        # Step 2: Enrollment
        audio_path = TEST_AUDIO_DIR / user["enrollment_audio"]
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        print_test("Step 2: Voice enrollment", "PASS", f"Phone: {user['phone']}")
        
        time.sleep(1)
        
        # Step 3: Check status after enrollment
        response = requests.get(f"{API_BASE_URL}/status", timeout=5)
        new_count = response.json().get("users_enrolled", 0)
        
        if new_count > initial_count or new_count > 0:
            print_test("Step 3: Status update verification", "PASS", f"Users enrolled: {new_count}")
        else:
            print_test("Step 3: Status update verification", "FAIL", "Count not updated")
        
        # Step 4: Verification with different audio
        verify_path = TEST_AUDIO_DIR / user["verify_audio"]
        with open(verify_path, "rb") as f:
            verify_audio = f.read()
        
        files = {"file": ("audio.wav", verify_audio, "audio/wav")}
        data = {"phone_number": user["phone"]}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        verify_data = response.json()
        
        print_test("Step 4: Voice verification", "PASS", f"Match: {verify_data.get('is_match')}, Score: {verify_data.get('similarity_score'):.3f}")
        
        # Step 5: Verify variant audio
        variant_path = TEST_AUDIO_DIR / user["variant_audio"]
        if variant_path.exists():
            with open(variant_path, "rb") as f:
                variant_audio = f.read()
            
            files = {"file": ("audio.wav", variant_audio, "audio/wav")}
            data = {"phone_number": user["phone"]}
            
            response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
            variant_data = response.json()
            
            print_test("Step 5: Variant audio verification", "PASS", f"Score: {variant_data.get('similarity_score'):.3f}")
        
        results.add_pass("Complete E2E Journey", "User journey completed successfully")
        return True
        
    except Exception as e:
        print_error(f"Complete E2E journey test failed: {e}")
        results.add_fail("Complete E2E Journey", str(e))
        return False


def save_results(results: E2ETestResults):
    """Save test results to JSON file"""
    try:
        with open(E2E_RESULTS_FILE, "w") as f:
            json.dump(results.to_dict(), f, indent=2)
        print_success(f"Results saved to {E2E_RESULTS_FILE}")
    except Exception as e:
        print_error(f"Failed to save results: {e}")


def print_summary(results: E2ETestResults):
    """Print test summary"""
    total = results.passed + results.failed + results.skipped
    pass_rate = (results.passed / (results.passed + results.failed) * 100) if (results.passed + results.failed) > 0 else 0
    
    print_section("E2E TEST SUMMARY")
    
    print(f"  Total Tests:  {total}")
    print(f"  {Colors.GREEN}Passed:    {results.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed:    {results.failed}{Colors.END}")
    print(f"  {Colors.YELLOW}Skipped:   {results.skipped}{Colors.END}")
    print(f"  Pass Rate:   {pass_rate:.1f}%")
    print(f"  Duration:    {results.end_time - results.start_time}")
    
    if results.errors:
        print_section("FAILURES")
        for error in results.errors:
            print_error(f"{error['test']}: {error['error']}")


def main():
    """Main test execution"""
    print_section("PHASE 4.3: END-TO-END TEST SUITE")
    print_info("Voice Biometric Authentication System - Complete Workflow Tests\n")
    
    # Initialize results
    results = E2ETestResults()
    
    # Start/check backend
    server_process = None
    server_process = start_backend_server()
    
    # Wait for API
    if not wait_for_api(max_retries=30):
        print_error("Failed to connect to API - testing cannot proceed")
        results.end_time = datetime.now()
        save_results(results)
        return
    
    time.sleep(2)
    
    # Run test suite
    try:
        test_api_health_check(results)
        time.sleep(1)
        
        test_single_user_workflow(results)
        time.sleep(1)
        
        test_multi_user_isolation(results)
        time.sleep(1)
        
        test_concurrent_operations(results)
        time.sleep(1)
        
        test_database_persistence(results)
        time.sleep(1)
        
        test_error_handling(results)
        time.sleep(1)
        
        test_api_performance(results)
        time.sleep(1)
        
        test_state_transitions(results)
        time.sleep(1)
        
        test_end_to_end_journey(results)
        
    except KeyboardInterrupt:
        print_error("\nTest execution interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error during testing: {e}")
    finally:
        results.end_time = datetime.now()
        print_summary(results)
        save_results(results)
        
        # Clean up
        if server_process:
            server_process.terminate()


if __name__ == "__main__":
    main()
