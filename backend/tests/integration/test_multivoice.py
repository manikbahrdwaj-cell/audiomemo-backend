#!/usr/bin/env python3
"""
Multi-speaker verification test script
Tests voice authentication with multiple speakers to ensure:
1. Enrolled speakers can verify (True Positive)
2. Non-enrolled speakers cannot verify (True Negative)
3. Different speakers don't cross-verify (Security)
"""

import requests
import time
import sys
from pathlib import Path
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
WORKSPACE_DIR = Path(__file__).parent

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_section(title):
    """Print a formatted section title"""
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}{Colors.END}\n")

def print_subsection(title):
    """Print a formatted subsection title"""
    print(f"\n{Colors.CYAN}─ {title}{Colors.END}")

def print_success(message):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"  {Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"  {Colors.YELLOW}→ {message}{Colors.END}")

def print_result(label, value, unit=""):
    """Print test result in a formatted way"""
    print(f"  {label:<40} {Colors.CYAN}{value}{unit}{Colors.END}")

# Test scenarios
TEST_CASES = [
    {
        "name": "Speaker 1 Enrollment",
        "operation": "enroll",
        "phone": "9876543210",
        "audio_file": "test_voice_speaker1.wav",
        "expected": "success",
        "description": "First speaker enrolls with their voice"
    },
    {
        "name": "Speaker 1 Self-Verification",
        "operation": "verify",
        "phone": "9876543210",
        "audio_file": "test_voice_speaker1.wav",
        "expected": "match",
        "description": "Speaker 1 verifies with same audio (should PASS)"
    },
    {
        "name": "Speaker 1 Variant Verification",
        "operation": "verify",
        "phone": "9876543210",
        "audio_file": "test_voice_speaker1_variant.wav",
        "expected": "match",
        "description": "Speaker 1 verifies with variant audio (should PASS)"
    },
    {
        "name": "Speaker 2 Impersonation Attempt",
        "operation": "verify",
        "phone": "9876543210",
        "audio_file": "test_voice_speaker2.wav",
        "expected": "no_match",
        "description": "Speaker 2 tries to impersonate Speaker 1 (should FAIL)"
    },
    {
        "name": "Speaker 3 Impersonation Attempt",
        "operation": "verify",
        "phone": "9876543210",
        "audio_file": "test_voice_speaker3.wav",
        "expected": "no_match",
        "description": "Speaker 3 tries to impersonate Speaker 1 (should FAIL)"
    },
    {
        "name": "Speaker 2 Enrollment",
        "operation": "enroll",
        "phone": "8765432109",
        "audio_file": "test_voice_speaker2.wav",
        "expected": "success",
        "description": "Second speaker enrolls"
    },
    {
        "name": "Speaker 2 Self-Verification",
        "operation": "verify",
        "phone": "8765432109",
        "audio_file": "test_voice_speaker2.wav",
        "expected": "match",
        "description": "Speaker 2 verifies with their own audio (should PASS)"
    },
    {
        "name": "Speaker 2 Verification with Speaker 1 Audio",
        "operation": "verify",
        "phone": "8765432109",
        "audio_file": "test_voice_speaker1.wav",
        "expected": "no_match",
        "description": "Speaker 2 uses Speaker 1's audio to verify (should FAIL)"
    },
    {
        "name": "Speaker 3 Enrollment",
        "operation": "enroll",
        "phone": "7654321098",
        "audio_file": "test_voice_speaker3.wav",
        "expected": "success",
        "description": "Third speaker enrolls"
    },
    {
        "name": "Speaker 3 Self-Verification",
        "operation": "verify",
        "phone": "7654321098",
        "audio_file": "test_voice_speaker3.wav",
        "expected": "match",
        "description": "Speaker 3 verifies with their own audio (should PASS)"
    },
    {
        "name": "Unenrolled Speaker Verification",
        "operation": "verify",
        "phone": "5555555555",
        "audio_file": "test_voice_speaker1.wav",
        "expected": "error",
        "description": "Attempt to verify unenrolled phone (should FAIL)"
    },
]

def enroll_speaker(phone_number, audio_file):
    """Enroll a speaker"""
    audio_path = WORKSPACE_DIR / audio_file
    
    if not audio_path.exists():
        return {"success": False, "error": f"Audio file not found: {audio_file}"}
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': (audio_file, f, 'audio/wav')}
            data = {'phone_number': phone_number}
            
            response = requests.post(
                f"{API_BASE_URL}/enroll",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": result['message'],
                "vector_id": result.get('vector_id'),
                "phone": result['phone_number']
            }
        else:
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def verify_speaker(phone_number, audio_file):
    """Verify a speaker"""
    audio_path = WORKSPACE_DIR / audio_file
    
    if not audio_path.exists():
        return {"success": False, "error": f"Audio file not found: {audio_file}"}
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': (audio_file, f, 'audio/wav')}
            data = {'phone_number': phone_number}
            
            response = requests.post(
                f"{API_BASE_URL}/verify",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "is_match": result['is_match'],
                "similarity_score": result['similarity_score'],
                "threshold": result['threshold'],
                "phone": result['phone_number']
            }
        elif response.status_code == 404:
            return {"success": False, "is_enrolled": False, "error": response.json().get('detail')}
        else:
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_test_case(test_case, test_num, total_tests):
    """Run a single test case"""
    name = test_case["name"]
    operation = test_case["operation"]
    phone = test_case["phone"]
    audio_file = test_case["audio_file"]
    expected = test_case["expected"]
    description = test_case["description"]
    
    print_info(f"[{test_num}/{total_tests}] {name}")
    print_result("Description", description)
    print_result("Phone Number", phone)
    print_result("Audio File", audio_file)
    print_result("Expected Result", expected.upper())
    
    # Execute operation
    if operation == "enroll":
        result = enroll_speaker(phone, audio_file)
    else:  # verify
        result = verify_speaker(phone, audio_file)
    
    # Evaluate result
    passed = False
    
    if expected == "success":
        if result.get("success"):
            print_success(f"Enrollment successful - Vector ID: {result.get('vector_id', 'N/A')}")
            passed = True
        else:
            print_error(f"Enrollment failed: {result.get('error')}")
    
    elif expected == "match":
        if result.get("success") and result.get("is_match"):
            similarity = result.get("similarity_score", 0)
            threshold = result.get("threshold", 0)
            print_success(f"Voice MATCHED (Score: {similarity:.4f} > Threshold: {threshold:.4f})")
            passed = True
        elif result.get("success") and not result.get("is_match"):
            similarity = result.get("similarity_score", 0)
            threshold = result.get("threshold", 0)
            print_error(f"Voice did NOT match (Score: {similarity:.4f} < Threshold: {threshold:.4f})")
        else:
            print_error(f"Verification failed: {result.get('error')}")
    
    elif expected == "no_match":
        if result.get("success") and not result.get("is_match"):
            similarity = result.get("similarity_score", 0)
            threshold = result.get("threshold", 0)
            print_success(f"Security PASSED - Voice correctly REJECTED (Score: {similarity:.4f} < Threshold: {threshold:.4f})")
            passed = True
        elif result.get("success") and result.get("is_match"):
            similarity = result.get("similarity_score", 0)
            print_error(f"SECURITY BREACH - Different speaker was accepted! (Score: {similarity:.4f})")
        else:
            print_error(f"Verification failed: {result.get('error')}")
    
    elif expected == "error":
        if not result.get("success"):
            print_success(f"Correctly rejected unenrolled speaker: {result.get('error')}")
            passed = True
        else:
            print_error(f"Should have failed for unenrolled speaker")
    
    return passed

def main():
    """Run all multi-speaker tests"""
    print_section("MULTI-SPEAKER VOICE VERIFICATION TEST SUITE")
    
    print_info("Testing voice authentication system with multiple speakers")
    print_info("Verifying security and accuracy of biometric matching\n")
    
    # Check API connectivity
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print_success(f"API is ready: {response.json()['message']}")
        else:
            print_error("API is not responding correctly")
            return False
    except Exception as e:
        print_error(f"Cannot connect to API: {e}")
        return False
    
    print_section("Running Test Cases")
    
    passed_tests = 0
    failed_tests = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print_subsection(f"TEST {i:02d}: {test_case['name']}")
        
        if run_test_case(test_case, i, len(TEST_CASES)):
            passed_tests += 1
        else:
            failed_tests += 1
        
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print_section("TEST SUMMARY")
    
    total = len(TEST_CASES)
    success_rate = (passed_tests / total * 100) if total > 0 else 0
    
    print(f"  Total Tests:      {Colors.CYAN}{total}{Colors.END}")
    print(f"  Passed:           {Colors.GREEN}{passed_tests}{Colors.END}")
    print(f"  Failed:           {Colors.RED}{failed_tests}{Colors.END}")
    print(f"  Success Rate:     {Colors.CYAN}{success_rate:.1f}%{Colors.END}")
    
    if failed_tests == 0:
        print_success("All tests passed! Voice authentication system is secure and accurate.")
        return True
    else:
        print_error(f"{failed_tests} test(s) failed. Review results above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
