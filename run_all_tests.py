#!/usr/bin/env python3
"""
Master Test Orchestration Script
Automates the entire testing workflow:
1. Generate test audio files
2. Start backend API server  
3. Run comprehensive test suite
4. Generate final report
"""

import subprocess
import time
import sys
import os
import json
from pathlib import Path
import signal
import psutil

# Configuration
WORKSPACE_DIR = Path(__file__).parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
RESULTS_FILE = WORKSPACE_DIR / "test_results.json"
FINAL_REPORT = WORKSPACE_DIR / "TEST_REPORT.md"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

def print_header(text):
    """Print header"""
    print(f"\n{Colors.BLUE}{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}{Colors.END}\n")

def print_step(step_num, title):
    """Print step header"""
    print(f"\n{Colors.CYAN}[STEP {step_num}] {title}{Colors.END}")
    print(f"{Colors.CYAN}{'-'*70}{Colors.END}\n")

def print_success(msg):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    """Print error message"""
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    """Print info message"""
    print(f"{Colors.YELLOW}→ {msg}{Colors.END}")

def check_python_packages():
    """Check if required Python packages are installed"""
    print_step(0, "Checking Python Dependencies")
    
    required_packages = {
        'requests': 'requests',
        'librosa': 'librosa',
        'soundfile': 'soundfile',
        'numpy': 'numpy',
        'scipy': 'scipy',
    }
    
    missing = []
    for package, import_name in required_packages.items():
        try:
            __import__(import_name)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            missing.append(package)
    
    if missing:
        print_info(f"\nInstalling missing packages: {', '.join(missing)}")
        try:
            cmd = [sys.executable, "-m", "pip", "install"] + missing
            subprocess.run(cmd, check=True, capture_output=True)
            print_success("All packages installed successfully")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install packages: {e}")
            return False
    
    return True

def generate_test_audio():
    """Run audio generation script"""
    print_step(1, "Generating Test Audio Files")
    
    script = WORKSPACE_DIR / "generate_comprehensive_audio.py"
    
    if not script.exists():
        print_error(f"Audio generation script not found: {script}")
        return False
    
    print_info("Running audio generation...")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=False,
            timeout=120
        )
        
        if result.returncode == 0:
            print_success("Audio generation completed successfully")
            return True
        else:
            print_error("Audio generation failed")
            return False
    
    except subprocess.TimeoutExpired:
        print_error("Audio generation timed out")
        return False
    except Exception as e:
        print_error(f"Error during audio generation: {e}")
        return False

def start_backend_server():
    """Start backend API server"""
    print_step(2, "Starting Backend API Server")
    
    # Check if already running
    try:
        import requests
        response = requests.get("http://localhost:8000/", timeout=2)
        if response.status_code == 200:
            print_success("Backend is already running")
            return True
    except:
        pass
    
    print_info("Starting backend server on port 8000...")
    
    run_script = BACKEND_DIR / "run.py"
    if not run_script.exists():
        print_error(f"Backend run script not found: {run_script}")
        return False
    
    try:
        # Start in background
        if sys.platform == "win32":
            # Windows: Start in new window
            process = subprocess.Popen(
                [sys.executable, str(run_script)],
                cwd=str(BACKEND_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Unix: Start with output redirection
            process = subprocess.Popen(
                [sys.executable, str(run_script)],
                cwd=str(BACKEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # Wait for server to start
        print_info("Waiting for server to initialize...")
        import requests
        
        for attempt in range(30):
            try:
                response = requests.get("http://localhost:8000/", timeout=2)
                if response.status_code == 200:
                    print_success("Backend server is running and ready")
                    return True
            except:
                if attempt < 29:
                    print_info(f"  Waiting... ({attempt + 1}/30)")
                    time.sleep(2)
        
        print_error("Server did not start within timeout")
        return False
    
    except Exception as e:
        print_error(f"Failed to start backend: {e}")
        return False

def run_comprehensive_tests():
    """Run the comprehensive test suite"""
    print_step(3, "Running Comprehensive Test Suite")
    
    script = WORKSPACE_DIR / "comprehensive_test_suite.py"
    
    if not script.exists():
        print_error(f"Test script not found: {script}")
        return False
    
    print_info("Executing tests...")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            print_success("Test suite completed")
            return True
        else:
            print_error("Test suite execution failed")
            return False
    
    except subprocess.TimeoutExpired:
        print_error("Test execution timed out")
        return False
    except Exception as e:
        print_error(f"Error running tests: {e}")
        return False

def load_test_results():
    """Load test results from JSON"""
    if not RESULTS_FILE.exists():
        return None
    
    try:
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def generate_markdown_report(test_data):
    """Generate detailed markdown report"""
    if not test_data:
        return
    
    print_step(4, "Generating Final Report")
    
    summary = test_data.get("summary", {})
    tests = test_data.get("tests", [])
    
    report = []
    report.append("# Voice Biometric App - Testing Report\n")
    report.append(f"**Generated:** {test_data.get('timestamp', 'N/A')}\n")
    report.append(f"**API:** {test_data.get('api_url', 'N/A')}\n\n")
    
    # Executive Summary
    report.append("## Executive Summary\n")
    report.append("| Metric | Value |\n")
    report.append("|--------|-------|\n")
    report.append(f"| Total Tests | {summary.get('total_tests', 0)} |\n")
    report.append(f"| Passed | {summary.get('passed', 0)} |\n")
    report.append(f"| Failed | {summary.get('failed', 0)} |\n")
    report.append(f"| Skipped | {summary.get('skipped', 0)} |\n")
    report.append(f"| Success Rate | {summary.get('success_rate', 0):.1f}% |\n\n")
    
    # Status indicator
    success_rate = summary.get('success_rate', 0)
    if success_rate == 100:
        status = "✅ **ALL TESTS PASSED** - App is fully functional"
    elif success_rate >= 80:
        status = "⚠️  **MOSTLY PASSED** - App is mostly functional with minor issues"
    elif success_rate >= 50:
        status = "❌ **PARTIALLY PASSED** - App has significant issues"
    else:
        status = "❌ **FAILED** - App needs serious fixes"
    
    report.append(f"## Overall Status: {status}\n\n")
    
    # Test Categories
    report.append("## Test Results by Category\n\n")
    
    categories = {}
    for test in tests:
        cat = test.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = {"tests": [], "pass": 0, "fail": 0, "skip": 0}
        categories[cat]["tests"].append(test)
        if test["status"] == "PASS":
            categories[cat]["pass"] += 1
        elif test["status"] == "FAIL":
            categories[cat]["fail"] += 1
        else:
            categories[cat]["skip"] += 1
    
    for category, data in sorted(categories.items()):
        total = len(data["tests"])
        report.append(f"### {category}\n")
        report.append(f"Status: **{data['pass']}/{total}** passed\n\n")
        report.append("| Test Name | Status | Details |\n")
        report.append("|-----------|--------|----------|\n")
        
        for test in data["tests"]:
            status_icon = "✅ PASS" if test["status"] == "PASS" else "❌ FAIL" if test["status"] == "FAIL" else "⏭️  SKIP"
            details = str(test.get("details", ""))[:50]
            report.append(f"| {test.get('name', 'Unknown')} | {status_icon} | {details} |\n")
        
        report.append("\n")
    
    # Detailed Failures
    failed_tests = [t for t in tests if t["status"] == "FAIL"]
    if failed_tests:
        report.append("## Failed Tests (Detailed)\n\n")
        for test in failed_tests:
            report.append(f"### {test.get('name', 'Unknown')}\n")
            report.append(f"**Category:** {test.get('category', 'Unknown')}\n")
            report.append(f"**Details:** {json.dumps(test.get('details', {}), indent=2)}\n\n")
    
    # Recommendations
    report.append("## Recommendations\n\n")
    
    if success_rate == 100:
        report.append("✅ The voice verification system is **fully functional** and ready for production.\n\n")
        report.append("- All speakers correctly verify with their own voices\n")
        report.append("- Cross-speaker security is working properly\n")
        report.append("- Edge cases (animals, noise) are properly rejected\n")
    else:
        report.append("⚠️  The following issues need to be addressed:\n\n")
        
        security_failures = [t for t in failed_tests if "Security" in t.get("category", "")]
        if security_failures:
            report.append("**Security Issues Found:**\n")
            for test in security_failures:
                report.append(f"- {test.get('name', 'Unknown')}\n")
            report.append("\n")
        
        verification_failures = [t for t in failed_tests if "Self-Verification" in t.get("category", "")]
        if verification_failures:
            report.append("**Verification Failures:**\n")
            for test in verification_failures:
                report.append(f"- {test.get('name', 'Unknown')}: Speaker cannot verify properly\n")
            report.append("\n")
    
    # Save report
    report_text = "".join(report)
    with open(FINAL_REPORT, 'w') as f:
        f.write(report_text)
    
    print_success(f"Report saved to: {FINAL_REPORT}")
    return report_text

def print_final_summary():
    """Print final summary"""
    print_header("TEST EXECUTION COMPLETE")
    
    # Load results
    test_data = load_test_results()
    
    if test_data:
        summary = test_data.get("summary", {})
        print(f"{Colors.CYAN}Test Summary:{Colors.END}")
        print(f"  Total Tests: {summary.get('total_tests', 0)}")
        print(f"  {Colors.GREEN}Passed: {summary.get('passed', 0)}{Colors.END}")
        print(f"  {Colors.RED}Failed: {summary.get('failed', 0)}{Colors.END}")
        print(f"  Success Rate: {summary.get('success_rate', 0):.1f}%")
        
        print(f"\n{Colors.CYAN}Output Files:{Colors.END}")
        print(f"  Results: {RESULTS_FILE}")
        print(f"  Report: {FINAL_REPORT}")
    else:
        print_error("No test results found")

def cleanup_and_exit():
    """Cleanup and exit"""
    print_info("\nClosing background processes...")
    
    # Kill any Python processes running the backend
    for proc in psutil.process_iter():
        try:
            cmd = " ".join(proc.cmdline())
            if "run.py" in cmd and "backend" in cmd:
                print_info(f"Stopping backend process (PID: {proc.pid})")
                proc.terminate()
        except:
            pass

def main():
    """Main orchestration"""
    print_header("VOICE BIOMETRIC APP - COMPREHENSIVE TEST ORCHESTRATION")
    
    try:
        # Step 0: Check dependencies
        if not check_python_packages():
            print_error("Dependency check failed")
            return
        
        # Step 1: Generate audio
        if not generate_test_audio():
            print_error("Audio generation failed - cannot continue")
            return
        
        # Step 2: Start backend
        if not start_backend_server():
            print_error("Backend startup failed - cannot continue")
            return
        
        # Step 3: Run tests
        if not run_comprehensive_tests():
            print_error("Tests failed to run")
            return
        
        # Step 4: Generate report
        test_data = load_test_results()
        if test_data:
            report = generate_markdown_report(test_data)
            print("\n")
            print(report)
        
        # Print summary
        print_final_summary()
    
    except KeyboardInterrupt:
        print_error("\nTest execution interrupted by user")
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_and_exit()

if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("Installing psutil...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "psutil"],
            capture_output=True
        )
        import psutil
    
    main()
