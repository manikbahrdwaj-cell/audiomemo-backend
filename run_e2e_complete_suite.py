#!/usr/bin/env python3
"""
Phase 4.3: Master E2E Test Orchestrator

Orchestrates the complete end-to-end testing workflow:
1. Verify dependencies
2. Generate test audio
3. Start backend server
4. Run workflow tests
5. Run scenario tests
6. Generate combined report
7. Display results summary
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Configuration
WORKSPACE_DIR = Path(__file__).parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
TEST_AUDIO_DIR = WORKSPACE_DIR / "test_audio_files"

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'


def print_header(text):
    """Print header"""
    print(f"\n{Colors.BLUE}{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}{Colors.END}\n")


def print_step(step_num, title):
    """Print step header"""
    print(f"{Colors.CYAN}[Step {step_num}] {title}{Colors.END}")


def print_success(msg):
    """Print success"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg):
    """Print error"""
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_info(msg):
    """Print info"""
    print(f"{Colors.YELLOW}→ {msg}{Colors.END}")


def check_python_version():
    """Check Python version"""
    print_step(1, "Checking Python Version")
    
    version_info = sys.version_info
    version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    
    print_info(f"Python version: {version}")
    
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 8):
        print_error(f"Python 3.8+ required (found {version})")
        return False
    
    print_success("Python version OK")
    return True


def check_required_files():
    """Check if required files exist"""
    print_step(2, "Checking Required Files")
    
    required_files = [
        "test_e2e_workflows.py",
        "test_e2e_scenarios.py",
        "generate_comprehensive_audio.py",
        "backend/main.py",
        "backend/run.py",
    ]
    
    missing = []
    for file in required_files:
        filepath = WORKSPACE_DIR / file
        if not filepath.exists():
            missing.append(file)
            print_error(f"Missing: {file}")
        else:
            print_success(f"Found: {file}")
    
    return len(missing) == 0


def check_audio_files():
    """Check if test audio exists"""
    print_step(3, "Checking Test Audio Files")
    
    audio_files = list(TEST_AUDIO_DIR.glob("test_speaker*.wav"))
    
    if audio_files:
        print_success(f"Found {len(audio_files)} audio files")
        return True
    
    print_info("Test audio files not found - will generate them")
    return None  # Not an error, just need to generate


def generate_test_audio():
    """Generate test audio files"""
    print_step(4, "Generating Test Audio")
    
    try:
        print_info("Running audio generation script...")
        result = subprocess.run(
            [sys.executable, "generate_comprehensive_audio.py"],
            cwd=str(WORKSPACE_DIR),
            timeout=120,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("Test audio generated successfully")
            return True
        else:
            print_error(f"Audio generation failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print_error("Audio generation timed out")
        return False
    except Exception as e:
        print_error(f"Audio generation failed: {e}")
        return False


def check_api_health(timeout=10):
    """Check if API is healthy"""
    import requests
    
    try:
        response = requests.get("http://localhost:8000/", timeout=timeout)
        return response.status_code == 200
    except:
        return False


def start_backend_server():
    """Start backend server"""
    print_step(5, "Starting Backend Server")
    
    # Check if already running
    if check_api_health(timeout=2):
        print_success("Backend already running")
        return None
    
    try:
        print_info("Starting backend server...")
        
        if sys.platform == "win32":
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print_success(f"Backend started (PID: {process.pid})")
        
        # Wait for backend to be ready
        print_info("Waiting for backend to be ready...")
        for attempt in range(30):
            if check_api_health(timeout=2):
                print_success("Backend is ready!")
                return process
            time.sleep(1)
            if attempt % 5 == 0:
                print_info(f"Still waiting... ({attempt}s)")
        
        print_error("Backend did not respond in time")
        return None
        
    except Exception as e:
        print_error(f"Failed to start backend: {e}")
        return None


def run_workflow_tests():
    """Run workflow tests"""
    print_step(6, "Running Workflow Tests")
    
    try:
        print_info("Executing workflow test suite...")
        result = subprocess.run(
            [sys.executable, "test_e2e_workflows.py"],
            cwd=str(WORKSPACE_DIR),
            timeout=300
        )
        
        if result.returncode == 0:
            print_success("Workflow tests completed")
            return True
        else:
            print_error(f"Workflow tests failed (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print_error("Workflow tests timed out")
        return False
    except Exception as e:
        print_error(f"Workflow tests failed: {e}")
        return False


def run_scenario_tests():
    """Run scenario tests"""
    print_step(7, "Running Scenario Tests")
    
    try:
        print_info("Executing scenario test suite...")
        result = subprocess.run(
            [sys.executable, "test_e2e_scenarios.py"],
            cwd=str(WORKSPACE_DIR),
            timeout=300
        )
        
        if result.returncode == 0:
            print_success("Scenario tests completed")
            return True
        else:
            print_error(f"Scenario tests failed (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print_error("Scenario tests timed out")
        return False
    except Exception as e:
        print_error(f"Scenario tests failed: {e}")
        return False


def generate_combined_report():
    """Generate combined test report"""
    print_step(8, "Generating Combined Report")
    
    try:
        workflow_results = None
        scenario_results = None
        
        # Load workflow results
        workflow_file = WORKSPACE_DIR / "e2e_test_results.json"
        if workflow_file.exists():
            with open(workflow_file) as f:
                workflow_results = json.load(f)
        
        # Load scenario results
        scenario_file = WORKSPACE_DIR / "e2e_stress_test_results.json"
        if scenario_file.exists():
            with open(scenario_file) as f:
                scenario_results = json.load(f)
        
        # Create combined report
        combined = {
            "timestamp": datetime.now().isoformat(),
            "workflow_tests": workflow_results,
            "scenario_tests": scenario_results,
        }
        
        report_file = WORKSPACE_DIR / "e2e_combined_report.json"
        with open(report_file, "w") as f:
            json.dump(combined, f, indent=2)
        
        print_success(f"Report generated: {report_file}")
        return True
        
    except Exception as e:
        print_error(f"Report generation failed: {e}")
        return False


def display_summary():
    """Display test summary"""
    print_header("PHASE 4.3: E2E TEST COMPLETE")
    
    try:
        # Load results
        workflow_file = WORKSPACE_DIR / "e2e_test_results.json"
        scenario_file = WORKSPACE_DIR / "e2e_stress_test_results.json"
        
        summary_data = {
            "workflow_tests": None,
            "scenario_tests": None
        }
        
        if workflow_file.exists():
            with open(workflow_file) as f:
                data = json.load(f)
                summary_data["workflow_tests"] = data["summary"]
        
        if scenario_file.exists():
            with open(scenario_file) as f:
                data = json.load(f)
                summary_data["scenario_tests"] = data["summary"]
        
        # Display workflow summary
        if summary_data["workflow_tests"]:
            print(f"{Colors.CYAN}Workflow Tests:{Colors.END}")
            ws = summary_data["workflow_tests"]
            print(f"  Total:     {ws['total']}")
            print(f"  {Colors.GREEN}Passed:   {ws['passed']}{Colors.END}")
            print(f"  {Colors.RED}Failed:   {ws['failed']}{Colors.END}")
            print(f"  Pass Rate: {ws['pass_rate']}")
            print(f"  Duration:  {ws['duration']}\n")
        
        # Display scenario summary
        if summary_data["scenario_tests"]:
            print(f"{Colors.CYAN}Scenario Tests:{Colors.END}")
            ss = summary_data["scenario_tests"]
            print(f"  Total Scenarios: {ss['total_scenarios']}")
            print(f"  Duration:        {ss['duration']}\n")
        
        # Overall assessment
        if summary_data["workflow_tests"]:
            pass_rate = float(summary_data["workflow_tests"]["pass_rate"].rstrip('%'))
            if pass_rate == 100:
                print(f"{Colors.GREEN}✓ ALL TESTS PASSED - READY FOR PRODUCTION{Colors.END}\n")
            elif pass_rate >= 95:
                print(f"{Colors.YELLOW}✓ Most tests passed - review failures{Colors.END}\n")
            else:
                print(f"{Colors.RED}✗ Some tests failed - investigate before deployment{Colors.END}\n")
        
    except Exception as e:
        print_error(f"Could not display summary: {e}")
    
    print_info("Results saved to:")
    print_info("  - e2e_test_results.json (workflow tests)")
    print_info("  - e2e_stress_test_results.json (scenario tests)")
    print_info("  - e2e_combined_report.json (combined)")


def cleanup():
    """Cleanup operations"""
    pass


def main():
    """Main orchestration"""
    print_header("PHASE 4.3: COMPREHENSIVE E2E TEST ORCHESTRATION")
    print_info("Voice Biometric Authentication System\n")
    
    start_time = time.time()
    
    try:
        # Step 1: Check Python version
        if not check_python_version():
            return False
        
        time.sleep(1)
        
        # Step 2: Check required files
        if not check_required_files():
            print_error("Required files missing")
            return False
        
        time.sleep(1)
        
        # Step 3: Check audio files
        audio_status = check_audio_files()
        time.sleep(1)
        
        # Step 4: Generate audio if needed
        if audio_status is None:
            if not generate_test_audio():
                print_error("Audio generation failed")
                return False
            time.sleep(2)
        elif audio_status is False:
            print_error("Audio check failed")
            return False
        
        # Step 5: Start backend
        backend_process = start_backend_server()
        time.sleep(2)
        
        # Step 6: Run workflow tests
        workflow_ok = run_workflow_tests()
        time.sleep(2)
        
        # Step 7: Run scenario tests
        scenario_ok = run_scenario_tests()
        time.sleep(1)
        
        # Step 8: Generate combined report
        generate_combined_report()
        time.sleep(1)
        
        # Step 9: Display summary
        display_summary()
        
        # Calculate total time
        total_time = time.time() - start_time
        print_success(f"Total execution time: {total_time/60:.1f} minutes ({total_time:.0f}s)")
        
        # Cleanup
        if backend_process:
            print_info("Stopping backend server...")
            backend_process.terminate()
        
        return workflow_ok and scenario_ok
        
    except KeyboardInterrupt:
        print_error("\nOrchestration interrupted by user")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
