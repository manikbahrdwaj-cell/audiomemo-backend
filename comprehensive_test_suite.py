#!/usr/bin/env python3
"""
Comprehensive Multi-Speaker Voice Verification Test Suite
Tests the app with:
- Multiple human speakers (different voice characteristics)
- Cross-speaker verification (security checks)
- Edge cases (silence, noise, speech variations)
- Summary report with success/failure metrics
"""

import requests
import json
import time
from pathlib import Path
import numpy as np
from datetime import datetime
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
WORKSPACE_DIR = Path(__file__).parent
TEST_AUDIO_DIR = WORKSPACE_DIR / "test_audio_files"
RESULTS_FILE = WORKSPACE_DIR / "test_results.json"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

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
    else:  # INFO
        symbol = f"{Colors.YELLOW}→{Colors.END}"
    
    print(f"  {symbol} {test_name:<50} [{status}]", end="")
    if details:
        print(f" {details}")
    else:
        print()

def print_result(label, value, unit="", color=None):
    """Print formatted result line"""
    if color:
        print(f"    {label:<45} {color}{value}{unit}{Colors.END}")
    else:
        print(f"    {label:<45} {Colors.CYAN}{value}{unit}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"  {Colors.RED}✗ Error: {message}{Colors.END}")

def print_success(message):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"  {Colors.YELLOW}→ {message}{Colors.END}")

# Test data definitions
TEST_SPEAKERS = {
    "Speaker_1_Male": {
        "phone": "9876543210",
        "description": "Male speaker with deep voice",
        "enrollment_audio": "test_speaker1_enroll.wav",
        "verification_audios": {
            "same_speaker": "test_speaker1_verify.wav",
            "different_variant": "test_speaker1_variant.wav",
        }
    },
    "Speaker_2_Female": {
        "phone": "8765432109",
        "description": "Female speaker with higher pitch",
        "enrollment_audio": "test_speaker2_enroll.wav",
        "verification_audios": {
            "same_speaker": "test_speaker2_verify.wav",
            "different_variant": "test_speaker2_variant.wav",
        }
    },
    "Speaker_3_Child": {
        "phone": "7654321098",
        "description": "Child speaker (high pitch variation)",
        "enrollment_audio": "test_speaker3_enroll.wav",
        "verification_audios": {
            "same_speaker": "test_speaker3_verify.wav",
        }
    },
}

EDGE_CASES = {
    "animal_dog_bark": {
        "file": "animal_dog_bark.wav",
        "description": "Dog barking sound",
        "expected_behavior": "Should NOT match any speaker"
    },
    "animal_cat_meow": {
        "file": "animal_cat_meow.wav",
        "description": "Cat meowing sound",
        "expected_behavior": "Should NOT match any speaker"
    },
    "ambient_noise": {
        "file": "ambient_noise.wav",
        "description": "Background noise only",
        "expected_behavior": "Should NOT match any speaker"
    },
    "whisper": {
        "file": "whisper_sound.wav",
        "description": "Whispered speech (not normal voice)",
        "expected_behavior": "May match poorly or not at all"
    },
}

class TestResults:
    def __init__(self):
        self.results = {
            "test_suite": "Comprehensive Voice Verification Tests",
            "timestamp": datetime.now().isoformat(),
            "api_url": API_BASE_URL,
            "tests": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "success_rate": 0.0
            }
        }
    
    def add_test(self, test_name, category, status, details):
        """Add a test result"""
        self.results["tests"].append({
            "name": test_name,
            "category": category,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def update_summary(self):
        """Update test summary"""
        tests = self.results["tests"]
        self.results["summary"]["total_tests"] = len(tests)
        self.results["summary"]["passed"] = sum(1 for t in tests if t["status"] == "PASS")
        self.results["summary"]["failed"] = sum(1 for t in tests if t["status"] == "FAIL")
        self.results["summary"]["skipped"] = sum(1 for t in tests if t["status"] == "SKIP")
        
        total = self.results["summary"]["total_tests"]
        if total > 0:
            self.results["summary"]["success_rate"] = (
                self.results["summary"]["passed"] / total * 100
            )
    
    def save(self, filepath):
        """Save results to JSON file"""
        self.update_summary()
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {filepath}")

def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def enroll_speaker(phone_number, audio_file, speaker_name):
    """Enroll a speaker"""
    audio_path = TEST_AUDIO_DIR / audio_file
    
    if not audio_path.exists():
        return None, f"Audio file not found: {audio_file}"
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {'phone_number': phone_number}
            response = requests.post(
                f"{API_BASE_URL}/enroll",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            return result, f"Phone: {phone_number} | Vector ID: {result.get('vector_id', 'N/A')}"
        else:
            return None, f"API responded with {response.status_code}: {response.text}"
    
    except Exception as e:
        return None, str(e)

def verify_speaker(phone_number, audio_file):
    """Verify a speaker"""
    audio_path = TEST_AUDIO_DIR / audio_file
    
    if not audio_path.exists():
        return None, f"Audio file not found: {audio_file}"
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {'phone_number': phone_number}
            response = requests.post(
                f"{API_BASE_URL}/verify",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            return result, f"Score: {result.get('similarity_score', 0):.4f} | Match: {result.get('is_match', False)}"
        else:
            return None, f"API responded with {response.status_code}: {response.text}"
    
    except Exception as e:
        return None, str(e)

def run_enrollment_tests(results, test_results):
    """Test speaker enrollment"""
    print_section("PHASE 1: SPEAKER ENROLLMENT TESTS")
    
    enrolled_speakers = {}
    
    for speaker_key, speaker_info in TEST_SPEAKERS.items():
        print_subsection(f"Enrolling {speaker_key} ({speaker_info['description']})")
        
        phone = speaker_info["phone"]
        audio_file = speaker_info["enrollment_audio"]
        
        print_info(f"Phone: {phone}")
        print_info(f"Audio: {audio_file}")
        
        response, message = enroll_speaker(phone, audio_file, speaker_key)
        
        if response and response.get("success"):
            print_test(
                f"{speaker_key} Enrollment",
                "PASS",
                message
            )
            test_results.add_test(
                f"{speaker_key} Enrollment",
                "Enrollment",
                "PASS",
                {"phone": phone, "vector_id": response.get("vector_id"), "message": message}
            )
            enrolled_speakers[speaker_key] = speaker_info
        else:
            print_test(f"{speaker_key} Enrollment", "FAIL", message)
            test_results.add_test(
                f"{speaker_key} Enrollment",
                "Enrollment",
                "FAIL",
                {"phone": phone, "error": message}
            )
    
    return enrolled_speakers

def run_self_verification_tests(results, test_results, enrolled_speakers):
    """Test self-verification (same speaker, same/similar audio)"""
    print_section("PHASE 2: SELF-VERIFICATION TESTS (Expected: All PASS)")
    
    for speaker_key, speaker_info in enrolled_speakers.items():
        print_subsection(f"Self-Verification: {speaker_key}")
        
        phone = speaker_info["phone"]
        
        # Test with verification audio
        for variant_name, audio_file in speaker_info["verification_audios"].items():
            print_info(f"Testing variant: {variant_name} ({audio_file})")
            
            response, message = verify_speaker(phone, audio_file)
            
            if response and response.get("is_match"):
                print_test(
                    f"{speaker_key} - {variant_name}",
                    "PASS",
                    message
                )
                test_results.add_test(
                    f"{speaker_key} - {variant_name}",
                    "Self-Verification",
                    "PASS",
                    {
                        "phone": phone,
                        "audio_file": audio_file,
                        "similarity_score": response.get("similarity_score"),
                        "threshold": response.get("threshold")
                    }
                )
            else:
                print_test(
                    f"{speaker_key} - {variant_name}",
                    "FAIL",
                    f"{message} (Expected match but got: is_match={response.get('is_match') if response else 'N/A'})"
                )
                test_results.add_test(
                    f"{speaker_key} - {variant_name}",
                    "Self-Verification",
                    "FAIL",
                    {
                        "phone": phone,
                        "audio_file": audio_file,
                        "expected": "match",
                        "got": "no_match",
                        "error": message
                    }
                )

def run_cross_speaker_tests(results, test_results, enrolled_speakers):
    """Test cross-speaker verification (security - should fail)"""
    print_section("PHASE 3: CROSS-SPEAKER VERIFICATION TESTS (Expected: All FAIL - Security Check)")
    
    speakers_list = list(enrolled_speakers.items())
    
    for i, (speaker_a_key, speaker_a_info) in enumerate(speakers_list):
        for j, (speaker_b_key, speaker_b_info) in enumerate(speakers_list):
            if i < j:  # Avoid duplicate combinations
                print_subsection(f"Cross-Speaker Test: {speaker_a_key} ↔ {speaker_b_key}")
                
                # Test A's audio against B's phone
                print_info(f"Testing {speaker_a_key}'s audio against {speaker_b_key}'s account")
                response, message = verify_speaker(
                    speaker_b_info["phone"],
                    speaker_a_info["enrollment_audio"]
                )
                
                test_name = f"{speaker_a_key} Audio vs {speaker_b_key} Account"
                
                if response and not response.get("is_match"):
                    print_test(test_name, "PASS", "Correctly rejected (Security working)")
                    test_results.add_test(
                        test_name,
                        "Cross-Speaker Security",
                        "PASS",
                        {
                            "speaker_a": speaker_a_key,
                            "speaker_b": speaker_b_key,
                            "similarity_score": response.get("similarity_score"),
                            "threshold": response.get("threshold"),
                            "correctly_rejected": True
                        }
                    )
                else:
                    print_test(
                        test_name,
                        "FAIL",
                        "SECURITY ISSUE: Speaker A audio matched Speaker B's account!"
                    )
                    test_results.add_test(
                        test_name,
                        "Cross-Speaker Security",
                        "FAIL",
                        {
                            "speaker_a": speaker_a_key,
                            "speaker_b": speaker_b_key,
                            "security_issue": True,
                            "error": "Cross-speaker match detected"
                        }
                    )
                
                # Test B's audio against A's phone
                print_info(f"Testing {speaker_b_key}'s audio against {speaker_a_key}'s account")
                response, message = verify_speaker(
                    speaker_a_info["phone"],
                    speaker_b_info["enrollment_audio"]
                )
                
                test_name = f"{speaker_b_key} Audio vs {speaker_a_key} Account"
                
                if response and not response.get("is_match"):
                    print_test(test_name, "PASS", "Correctly rejected (Security working)")
                    test_results.add_test(
                        test_name,
                        "Cross-Speaker Security",
                        "PASS",
                        {
                            "speaker_b": speaker_b_key,
                            "speaker_a": speaker_a_key,
                            "similarity_score": response.get("similarity_score"),
                            "correctly_rejected": True
                        }
                    )
                else:
                    print_test(
                        test_name,
                        "FAIL",
                        "SECURITY ISSUE: Speaker B audio matched Speaker A's account!"
                    )
                    test_results.add_test(
                        test_name,
                        "Cross-Speaker Security",
                        "FAIL",
                        {
                            "speaker_b": speaker_b_key,
                            "speaker_a": speaker_a_key,
                            "security_issue": True,
                            "error": "Cross-speaker match detected"
                        }
                    )

def run_edge_case_tests(results, test_results, enrolled_speakers):
    """Test edge cases: animals, noise, etc."""
    print_section("PHASE 4: EDGE CASE TESTS (Animals, Noise, etc.)")
    
    if not enrolled_speakers:
        print_info("Skipping edge case tests - no enrolled speakers")
        return
    
    # Pick first enrolled speaker for testing
    test_phone = list(enrolled_speakers.values())[0]["phone"]
    
    for edge_case_key, edge_case_info in EDGE_CASES.items():
        print_subsection(f"Edge Case: {edge_case_key}")
        print_info(f"Description: {edge_case_info['description']}")
        print_info(f"Expected: {edge_case_info['expected_behavior']}")
        
        audio_file = edge_case_info["file"]
        response, message = verify_speaker(test_phone, audio_file)
        
        if response:
            is_match = response.get("is_match", False)
            score = response.get("similarity_score", 0)
            
            # For edge cases, we expect NO match
            if not is_match:
                print_test(
                    f"{edge_case_key}",
                    "PASS",
                    f"Correctly rejected (score: {score:.4f})"
                )
                test_results.add_test(
                    f"Edge Case: {edge_case_key}",
                    "Edge Cases",
                    "PASS",
                    {
                        "description": edge_case_info["description"],
                        "similarity_score": score,
                        "correctly_rejected": True
                    }
                )
            else:
                print_test(
                    f"{edge_case_key}",
                    "FAIL",
                    f"Incorrectly matched! (score: {score:.4f})"
                )
                test_results.add_test(
                    f"Edge Case: {edge_case_key}",
                    "Edge Cases",
                    "FAIL",
                    {
                        "description": edge_case_info["description"],
                        "similarity_score": score,
                        "issue": "Non-speaker sound matched a speaker account"
                    }
                )
        else:
            print_test(
                f"{edge_case_key}",
                "SKIP",
                f"Audio file not available: {audio_file}"
            )
            test_results.add_test(
                f"Edge Case: {edge_case_key}",
                "Edge Cases",
                "SKIP",
                {"reason": "Audio file not found"}
            )

def run_unenrolled_speaker_test(results, test_results, enrolled_speakers):
    """Test verification with unenrolled phone number"""
    print_section("PHASE 5: UNENROLLED SPEAKER TEST")
    
    if not enrolled_speakers:
        print_info("Skipping - no enrolled speakers")
        return
    
    # Use audio from first enrolled speaker with a different phone
    first_speaker = list(enrolled_speakers.values())[0]
    audio_file = first_speaker["enrollment_audio"]
    
    # Try to verify with non-existent phone
    unenrolled_phone = "1111111111"
    
    print_subsection("Testing unauthorized verification attempt")
    print_info(f"Attempting verification with unenrolled phone: {unenrolled_phone}")
    
    response, message = verify_speaker(unenrolled_phone, audio_file)
    
    if response is None or not response.get("success"):
        print_test(
            "Unenrolled Phone Rejection",
            "PASS",
            "Correctly rejected (Phone not found)"
        )
        test_results.add_test(
            "Unenrolled Phone Rejection",
            "Authorization",
            "PASS",
            {"phone": unenrolled_phone, "correctly_rejected": True}
        )
    else:
        print_test(
            "Unenrolled Phone Rejection",
            "FAIL",
            f"Incorrectly allowed verification: {message}"
        )
        test_results.add_test(
            "Unenrolled Phone Rejection",
            "Authorization",
            "FAIL",
            {"phone": unenrolled_phone, "issue": "Unenrolled phone was allowed"}
        )

def print_summary(test_results):
    """Print test summary"""
    print_section("TEST SUMMARY")
    
    summary = test_results.results["summary"]
    tests = test_results.results["tests"]
    
    # Overall statistics
    print_result("Total Tests", summary["total_tests"])
    print_result("Passed", summary["passed"], color=Colors.GREEN)
    print_result("Failed", summary["failed"], color=Colors.RED if summary["failed"] > 0 else Colors.GREEN)
    print_result("Skipped", summary["skipped"], color=Colors.YELLOW if summary["skipped"] > 0 else Colors.GREEN)
    print_result("Success Rate", f"{summary['success_rate']:.1f}%")
    
    # Category breakdown
    print("\n{:<20} {:>15} {:>15} {:>15}".format("Category", "Total", "Passed", "Failed"))
    print("-" * 65)
    
    categories = {}
    for test in tests:
        cat = test["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "failed": 0}
        categories[cat]["total"] += 1
        if test["status"] == "PASS":
            categories[cat]["passed"] += 1
        elif test["status"] == "FAIL":
            categories[cat]["failed"] += 1
    
    for cat, stats in sorted(categories.items()):
        color = Colors.GREEN if stats["failed"] == 0 else Colors.RED
        print("{:<20} {:>15} {:>15} {:>15}".format(
            cat[:19],
            stats["total"],
            f"{Colors.GREEN}{stats['passed']}{Colors.END}",
            f"{color}{stats['failed']}{Colors.END}"
        ))

def main():
    """Main test execution"""
    print_section("VOICE VERIFICATION APP - COMPREHENSIVE TEST SUITE")
    
    # Check audio directory
    if not TEST_AUDIO_DIR.exists():
        print_error(f"Test audio directory not found: {TEST_AUDIO_DIR}")
        print_info("Please generate test audio files first using: python generate_test_audio.py")
        return
    
    # Check API
    print_info(f"API URL: {API_BASE_URL}")
    if not check_api_health():
        print_error("API is not running!")
        print_info("Start backend with: cd backend && python run.py")
        return
    
    print_success("API is running and healthy")
    
    # Initialize results tracker
    test_results = TestResults()
    results = {}
    
    # Run test phases
    enrolled_speakers = run_enrollment_tests(results, test_results)
    
    if enrolled_speakers:
        run_self_verification_tests(results, test_results, enrolled_speakers)
        run_cross_speaker_tests(results, test_results, enrolled_speakers)
        run_edge_case_tests(results, test_results, enrolled_speakers)
        run_unenrolled_speaker_test(results, test_results, enrolled_speakers)
    else:
        print_error("No speakers were successfully enrolled. Cannot continue with verification tests.")
    
    # Print and save results
    print_summary(test_results)
    test_results.save(RESULTS_FILE)

if __name__ == "__main__":
    main()
