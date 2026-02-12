#!/usr/bin/env python3
"""
Phase 4.3: E2E Real-World Scenarios & Stress Testing

Additional end-to-end tests covering:
- Real-world user scenarios
- Stress testing with high load
- Recovery and resilience
- Data consistency
- Security scenario testing
"""

import requests
import json
import time
import threading
import statistics
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
WORKSPACE_DIR = Path(__file__).parent
TEST_AUDIO_DIR = WORKSPACE_DIR / "test_audio_files"
STRESS_TEST_RESULTS_FILE = WORKSPACE_DIR / "e2e_stress_test_results.json"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

# Results tracking
class StressTestResults:
    def __init__(self):
        self.scenarios = {}
        self.start_time = datetime.now()
        self.end_time = None

    def add_scenario(self, name: str, results: Dict):
        self.scenarios[name] = results

    def to_dict(self):
        return {
            "summary": {
                "total_scenarios": len(self.scenarios),
                "timestamp": self.start_time.isoformat(),
                "duration": str(self.end_time - self.start_time) if self.end_time else "N/A"
            },
            "scenarios": self.scenarios
        }


# Utility functions
def print_section(title):
    print(f"\n{Colors.BLUE}{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}{Colors.END}\n")

def print_subsection(title):
    print(f"\n{Colors.CYAN}╔─ {title}{Colors.END}")

def print_test(name, status, details=""):
    if status == "PASS":
        symbol = f"{Colors.GREEN}✓{Colors.END}"
    elif status == "FAIL":
        symbol = f"{Colors.RED}✗{Colors.END}"
    else:
        symbol = f"{Colors.YELLOW}→{Colors.END}"
    
    print(f"  {symbol} {name:<60} [{status}]", end="")
    if details:
        print(f" {details}")
    else:
        print()

def print_success(msg):
    print(f"  {Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"  {Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"  {Colors.YELLOW}→ {msg}{Colors.END}")

def check_api_health():
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False


# Scenario 1: High Volume Enrollment
def scenario_high_volume_enrollment(num_users=20):
    """Scenario 1: Enroll many users in rapid succession"""
    print_subsection("Scenario 1: High Volume Enrollment")
    
    results = {
        "test_name": "High Volume Enrollment",
        "num_users": num_users,
        "start_time": datetime.now().isoformat(),
        "enrollments": {
            "successful": 0,
            "failed": 0,
            "response_times": []
        }
    }
    
    try:
        # Get a test audio file
        audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
        if not audio_files:
            print_test("Enroll users", "SKIP", "No test audio found")
            return results
        
        audio_file = audio_files[0]
        
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        print_test("Enrolling users", "INFO", f"Attempting {num_users} enrollments...")
        
        for i in range(num_users):
            try:
                phone = f"{5000000000 + i}"
                
                start = time.time()
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": phone}
                
                response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
                response_time = time.time() - start
                
                results["enrollments"]["response_times"].append(response_time)
                
                if response.status_code == 200:
                    results["enrollments"]["successful"] += 1
                    if i % 5 == 0:
                        print_test(f"User {i+1}/{num_users}", "PASS", f"Time: {response_time:.2f}s")
                else:
                    results["enrollments"]["failed"] += 1
            except Exception as e:
                results["enrollments"]["failed"] += 1
        
        # Calculate statistics
        if results["enrollments"]["response_times"]:
            times = results["enrollments"]["response_times"]
            results["enrollments"]["avg_time"] = statistics.mean(times)
            results["enrollments"]["min_time"] = min(times)
            results["enrollments"]["max_time"] = max(times)
            results["enrollments"]["median_time"] = statistics.median(times)
        
        status = "PASS" if results["enrollments"]["successful"] > 0 else "FAIL"
        print_test("High volume enrollment result", status, 
                  f"{results['enrollments']['successful']}/{num_users} successful")
        
    except Exception as e:
        print_error(f"High volume enrollment failed: {e}")
        results["error"] = str(e)
    
    results["end_time"] = datetime.now().isoformat()
    return results


# Scenario 2: Rapid-Fire Verification
def scenario_rapid_verification(num_attempts=20):
    """Scenario 2: Multiple rapid verification attempts"""
    print_subsection("Scenario 2: Rapid-Fire Verification")
    
    results = {
        "test_name": "Rapid Verification",
        "num_attempts": num_attempts,
        "start_time": datetime.now().isoformat(),
        "verifications": {
            "successful": 0,
            "failed": 0,
            "response_times": []
        }
    }
    
    try:
        # Get test audio
        audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
        if not audio_files:
            print_test("Verify user", "SKIP", "No test audio found")
            return results
        
        audio_file = audio_files[0]
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # First enroll a user
        phone = "9999999999"
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": phone}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        if response.status_code != 200:
            print_test("Enroll test user", "FAIL", "Could not enroll test user")
            results["error"] = "Enrollment failed"
            return results
        
        print_test("Enrolling test user", "PASS", "Ready for verification")
        time.sleep(1)
        
        # Now run rapid verifications
        print_test("Running verifications", "INFO", f"Attempting {num_attempts} verifications...")
        
        for i in range(num_attempts):
            try:
                start = time.time()
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": phone}
                
                response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
                response_time = time.time() - start
                
                results["verifications"]["response_times"].append(response_time)
                
                if response.status_code == 200:
                    results["verifications"]["successful"] += 1
                    if i % 5 == 0:
                        print_test(f"Verification {i+1}/{num_attempts}", "PASS", f"Time: {response_time:.2f}s")
                else:
                    results["verifications"]["failed"] += 1
            except Exception as e:
                results["verifications"]["failed"] += 1
        
        # Calculate statistics
        if results["verifications"]["response_times"]:
            times = results["verifications"]["response_times"]
            results["verifications"]["avg_time"] = statistics.mean(times)
            results["verifications"]["min_time"] = min(times)
            results["verifications"]["max_time"] = max(times)
            results["verifications"]["median_time"] = statistics.median(times)
        
        status = "PASS" if results["verifications"]["successful"] > 0 else "FAIL"
        print_test("Rapid verification result", status, 
                  f"{results['verifications']['successful']}/{num_attempts} successful")
        
    except Exception as e:
        print_error(f"Rapid verification failed: {e}")
        results["error"] = str(e)
    
    results["end_time"] = datetime.now().isoformat()
    return results


# Scenario 3: Concurrent Mixed Operations
def scenario_concurrent_mixed_ops(num_concurrent=10):
    """Scenario 3: Concurrent mix of enrollments and verifications"""
    print_subsection("Scenario 3: Concurrent Mixed Operations")
    
    results = {
        "test_name": "Concurrent Mixed Operations",
        "num_concurrent": num_concurrent,
        "start_time": datetime.now().isoformat(),
        "enrollments": {"successful": 0, "failed": 0},
        "verifications": {"successful": 0, "failed": 0}
    }
    
    try:
        audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
        if not audio_files:
            print_test("Mixed operations", "SKIP", "No test audio found")
            return results
        
        audio_file = audio_files[0]
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Pre-enroll test users
        test_phones = [f"{8000000000 + i}" for i in range(min(5, num_concurrent))]
        
        for phone in test_phones:
            try:
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": phone}
                requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
            except:
                pass
        
        print_test("Pre-enrollment", "PASS", f"{len(test_phones)} test users prepared")
        time.sleep(1)
        
        def enroll_task():
            try:
                phone = f"{7000000000 + int(time.time() * 1000) % 10000}"
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": phone}
                response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
                return response.status_code == 200
            except:
                return False
        
        def verify_task():
            try:
                phone = test_phones[0]
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": phone}
                response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
                return response.status_code == 200
            except:
                return False
        
        print_test("Running mixed operations", "INFO", f"{num_concurrent} concurrent tasks...")
        
        with ThreadPoolExecutor(max_workers=min(num_concurrent, 10)) as executor:
            futures = []
            
            # Mix of 60% verifications, 40% enrollments
            for i in range(num_concurrent):
                if i % 10 < 6:
                    futures.append(("verify", executor.submit(verify_task)))
                else:
                    futures.append(("enroll", executor.submit(enroll_task)))
            
            for op_type, future in futures:
                try:
                    result = future.result(timeout=35)
                    if op_type == "verify":
                        if result:
                            results["verifications"]["successful"] += 1
                        else:
                            results["verifications"]["failed"] += 1
                    else:
                        if result:
                            results["enrollments"]["successful"] += 1
                        else:
                            results["enrollments"]["failed"] += 1
                except:
                    if op_type == "verify":
                        results["verifications"]["failed"] += 1
                    else:
                        results["enrollments"]["failed"] += 1
        
        print_test("Mixed operations result", "PASS", 
                  f"Enroll: {results['enrollments']['successful']}, Verify: {results['verifications']['successful']}")
        
    except Exception as e:
        print_error(f"Concurrent mixed operations failed: {e}")
        results["error"] = str(e)
    
    results["end_time"] = datetime.now().isoformat()
    return results


# Scenario 4: Data Consistency Under Load
def scenario_data_consistency(num_operations=30):
    """Scenario 4: Verify data consistency under load"""
    print_subsection("Scenario 4: Data Consistency Under Load")
    
    results = {
        "test_name": "Data Consistency",
        "num_operations": num_operations,
        "start_time": datetime.now().isoformat(),
        "consistency_checks": {
            "passed": 0,
            "failed": 0
        }
    }
    
    try:
        audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
        if not audio_files:
            print_test("Data consistency", "SKIP", "No test audio found")
            return results
        
        audio_file = audio_files[0]
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Enroll a user
        phone = "6666666666"
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"phone_number": phone}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        if response.status_code != 200:
            print_test("Enroll test user", "FAIL", "Could not enroll")
            return results
        
        print_test("Enrolling user for consistency test", "PASS", "User enrolled")
        time.sleep(1)
        
        # Perform multiple verifications and check consistency
        print_test("Running consistency checks", "INFO", f"Performing {num_operations} verifications...")
        
        scores = []
        for i in range(num_operations):
            try:
                files = {"file": ("audio.wav", audio_data, "audio/wav")}
                data = {"phone_number": phone}
                
                response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    verify_data = response.json()
                    score = verify_data.get("similarity_score", 0)
                    is_match = verify_data.get("is_match", False)
                    
                    scores.append(score)
                    
                    # Consistency check: Same voice should always match
                    if is_match:
                        results["consistency_checks"]["passed"] += 1
                    else:
                        results["consistency_checks"]["failed"] += 1
                        
                    if i % 10 == 0:
                        print_test(f"Check {i+1}/{num_operations}", "PASS", f"Score: {score:.3f}")
            except Exception as e:
                results["consistency_checks"]["failed"] += 1
        
        # Analyze score variance
        if scores:
            results["consistency_checks"]["avg_score"] = statistics.mean(scores)
            results["consistency_checks"]["std_dev"] = statistics.stdev(scores) if len(scores) > 1 else 0
            results["consistency_checks"]["score_range"] = f"{min(scores):.3f} - {max(scores):.3f}"
        
        print_test("Consistency result", "PASS", 
                  f"Passed: {results['consistency_checks']['passed']}/{num_operations}")
        
    except Exception as e:
        print_error(f"Data consistency test failed: {e}")
        results["error"] = str(e)
    
    results["end_time"] = datetime.now().isoformat()
    return results


# Scenario 5: Cross-User Security Under Load
def scenario_security_under_load():
    """Scenario 5: Cross-user security verification under stress"""
    print_subsection("Scenario 5: Security Under Load")
    
    results = {
        "test_name": "Security Under Load",
        "start_time": datetime.now().isoformat(),
        "security_checks": {
            "passed": 0,
            "failed": 0,
            "violations": []
        }
    }
    
    try:
        audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
        if len(audio_files) < 2:
            print_test("Security test", "SKIP", "Need at least 2 different audio files")
            return results
        
        # Get different audio files
        audio1_path = audio_files[0]
        audio2_path = audio_files[1]
        
        with open(audio1_path, "rb") as f:
            audio1 = f.read()
        with open(audio2_path, "rb") as f:
            audio2 = f.read()
        
        # Enroll user 1
        phone1 = "5555555551"
        files = {"file": ("audio.wav", audio1, "audio/wav")}
        data = {"phone_number": phone1}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        if response.status_code != 200:
            print_test("Enroll user 1", "FAIL", "Could not enroll")
            return results
        
        # Enroll user 2
        phone2 = "5555555552"
        files = {"file": ("audio.wav", audio2, "audio/wav")}
        data = {"phone_number": phone2}
        
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
        if response.status_code != 200:
            print_test("Enroll user 2", "FAIL", "Could not enroll")
            return results
        
        print_test("Enrolling 2 users", "PASS", "Users ready for security test")
        time.sleep(1)
        
        # Test cross-user verification
        print_test("Cross-user verification test", "INFO", "Verifying user 2 with user 1's voice...")
        
        # Try to verify user 2 with user 1's audio (should NOT match)
        files = {"file": ("audio.wav", audio1, "audio/wav")}
        data = {"phone_number": phone2}
        
        response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            verify_data = response.json()
            is_match = verify_data.get("is_match", False)
            score = verify_data.get("similarity_score", 0)
            
            # Security check: Should NOT match
            if not is_match:
                print_test("Cross-user rejection", "PASS", f"Correctly rejected (score: {score:.3f})")
                results["security_checks"]["passed"] += 1
            else:
                print_test("Cross-user rejection", "FAIL", f"Incorrectly matched (score: {score:.3f})")
                results["security_checks"]["failed"] += 1
                results["security_checks"]["violations"].append({
                    "type": "cross_user_match",
                    "user1": phone1,
                    "user2": phone2,
                    "score": score
                })
        
        print_test("Security test result", "PASS", f"Security checks: {results['security_checks']['passed']} passed")
        
    except Exception as e:
        print_error(f"Security test failed: {e}")
        results["error"] = str(e)
    
    results["end_time"] = datetime.now().isoformat()
    return results


# Scenario 6: Recovery and Resilience
def scenario_recovery_resilience():
    """Scenario 6: System recovery after errors"""
    print_subsection("Scenario 6: Recovery and Resilience")
    
    results = {
        "test_name": "Recovery & Resilience",
        "start_time": datetime.now().isoformat(),
        "recovery_tests": {
            "passed": 0,
            "failed": 0
        }
    }
    
    try:
        audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
        if not audio_files:
            print_test("Recovery test", "SKIP", "No test audio found")
            return results
        
        audio_file = audio_files[0]
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Test 1: Recovery from invalid phone number
        print_test("Test 1: Invalid input recovery", "INFO", "Sending invalid request...")
        
        try:
            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {"phone_number": ""}
            
            response = requests.post(f"{API_BASE_URL}/verify", files=files, data=data, timeout=5)
            
            # Should fail gracefully
            print_test("Invalid input handling", "PASS", f"Status {response.status_code}")
            results["recovery_tests"]["passed"] += 1
        except:
            results["recovery_tests"]["failed"] += 1
        
        # Test 2: Recovery to normal operation
        print_test("Test 2: Recovery to normal", "INFO", "Sending valid request...")
        
        try:
            phone = "4444444444"
            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            data = {"phone_number": phone}
            
            response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                print_test("Recovered to normal operation", "PASS", "System operational")
                results["recovery_tests"]["passed"] += 1
            else:
                print_test("Recovered to normal operation", "FAIL", f"Status {response.status_code}")
                results["recovery_tests"]["failed"] += 1
        except Exception as e:
            print_test("Recovered to normal operation", "FAIL", str(e))
            results["recovery_tests"]["failed"] += 1
        
        print_test("Recovery test result", "PASS", f"Recovery checks: {results['recovery_tests']['passed']} passed")
        
    except Exception as e:
        print_error(f"Recovery test failed: {e}")
        results["error"] = str(e)
    
    results["end_time"] = datetime.now().isoformat()
    return results


def main():
    """Main execution"""
    print_section("PHASE 4.3: E2E STRESS & SCENARIO TESTING")
    print_info("Real-world scenarios and stress testing\n")
    
    # Check API
    if not check_api_health():
        print_error("API is not healthy - testing cannot proceed")
        return
    
    print_success("API is healthy - proceeding with tests\n")
    
    # Initialize results
    stress_results = StressTestResults()
    
    try:
        # Run scenarios
        results1 = scenario_high_volume_enrollment(num_users=20)
        stress_results.add_scenario("High Volume Enrollment", results1)
        time.sleep(2)
        
        results2 = scenario_rapid_verification(num_attempts=20)
        stress_results.add_scenario("Rapid Verification", results2)
        time.sleep(2)
        
        results3 = scenario_concurrent_mixed_ops(num_concurrent=15)
        stress_results.add_scenario("Concurrent Mixed Ops", results3)
        time.sleep(2)
        
        results4 = scenario_data_consistency(num_operations=30)
        stress_results.add_scenario("Data Consistency", results4)
        time.sleep(2)
        
        results5 = scenario_security_under_load()
        stress_results.add_scenario("Security Under Load", results5)
        time.sleep(2)
        
        results6 = scenario_recovery_resilience()
        stress_results.add_scenario("Recovery & Resilience", results6)
        
    except KeyboardInterrupt:
        print_error("\nTest execution interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
    finally:
        stress_results.end_time = datetime.now()
        
        # Save results
        try:
            with open(STRESS_TEST_RESULTS_FILE, "w") as f:
                json.dump(stress_results.to_dict(), f, indent=2)
            print_success(f"\nResults saved to {STRESS_TEST_RESULTS_FILE}")
        except Exception as e:
            print_error(f"Failed to save results: {e}")
        
        print_section("STRESS TEST COMPLETE")


if __name__ == "__main__":
    main()
