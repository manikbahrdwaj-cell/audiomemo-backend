#!/usr/bin/env python3
"""
Phase 4.4: Master Performance/Load Testing Orchestrator

Coordinates all performance and load testing activities:
1. Verify server is running
2. Execute load tests
3. Execute stress test scenarios
4. Generate comprehensive report
5. Display results summary
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Colors for output
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
    print(f"\n{Colors.MAGENTA}{'='*80}")
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


def print_warning(msg):
    """Print warning"""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_info(msg):
    """Print info"""
    print(f"{Colors.CYAN}→ {msg}{Colors.END}")


def check_server_running():
    """Check if server is running"""
    print_step(1, "Verify Backend Server")
    
    import requests
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        print_success("Backend server is running")
        return True
    except:
        print_error("Backend server is not running")
        print_info("Start the server with: python backend/main.py")
        return False


def check_dependencies():
    """Check if required dependencies are installed"""
    print_step(2, "Check Dependencies")
    
    required_packages = [
        'requests',
        'psutil',
        'numpy',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"  {package} is installed")
        except ImportError:
            print_error(f"  {package} is NOT installed")
            missing.append(package)
    
    if missing:
        print_warning(f"Install missing packages: pip install {' '.join(missing)}")
        return False
    
    return True


def run_load_tests():
    """Run load tests"""
    print_step(3, "Execute Load Tests")
    print_info("Running performance and load testing suite...")
    
    try:
        result = subprocess.run(
            [sys.executable, "performance_load_test.py"],
            cwd=Path(__file__).parent,
            capture_output=False,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            print_success("Load tests completed successfully")
            return True
        else:
            print_error("Load tests failed")
            return False
    except subprocess.TimeoutExpired:
        print_error("Load tests timed out (exceeded 10 minutes)")
        return False
    except Exception as e:
        print_error(f"Error running load tests: {e}")
        return False


def run_stress_tests():
    """Run stress tests"""
    print_step(4, "Execute Stress Tests")
    print_info("Running advanced stress test scenarios...")
    
    try:
        result = subprocess.run(
            [sys.executable, "stress_test_scenarios.py"],
            cwd=Path(__file__).parent,
            capture_output=False,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            print_success("Stress tests completed successfully")
            return True
        else:
            print_error("Stress tests failed")
            return False
    except subprocess.TimeoutExpired:
        print_error("Stress tests timed out (exceeded 10 minutes)")
        return False
    except Exception as e:
        print_error(f"Error running stress tests: {e}")
        return False


def generate_report():
    """Generate performance report"""
    print_step(5, "Generate Performance Report")
    print_info("Analyzing results and generating reports...")
    
    try:
        result = subprocess.run(
            [sys.executable, "performance_report_generator.py"],
            cwd=Path(__file__).parent,
            capture_output=False,
            timeout=60
        )
        
        if result.returncode == 0:
            print_success("Report generation completed")
            return True
        else:
            print_error("Report generation failed")
            return False
    except Exception as e:
        print_error(f"Error generating report: {e}")
        return False


def display_summary():
    """Display test summary"""
    print_step(6, "Test Summary")
    
    results_dir = Path(__file__).parent
    
    # Check for results files
    files_to_check = [
        ("performance_test_results.json", "Load Test Results"),
        ("stress_test_results.json", "Stress Test Results"),
        ("performance_report.json", "Performance Report"),
        ("performance_report.html", "HTML Report"),
    ]
    
    print("\nGenerated Files:")
    for filename, description in files_to_check:
        filepath = results_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print_success(f"  {description}: {filename} ({size:,} bytes)")
        else:
            print_warning(f"  {description}: {filename} (NOT FOUND)")
    
    print("\nNext Steps:")
    print("  1. Review the text report above")
    print("  2. Open performance_report.html in a web browser for detailed analysis")
    print("  3. Check performance_report.json for programmatic access to results")
    print("  4. Review recommendations and address any bottlenecks")


def main():
    """Main orchestrator"""
    print_header("Phase 4.4: Performance/Load Testing Suite")
    
    start_time = time.time()
    
    # Step 1: Check server
    if not check_server_running():
        sys.exit(1)
    
    time.sleep(1)
    
    # Step 2: Check dependencies
    if not check_dependencies():
        print_warning("Some dependencies are missing. Install them and try again.")
        sys.exit(1)
    
    time.sleep(1)
    
    # Step 3: Run load tests
    if not run_load_tests():
        print_error("Load tests failed. Skipping stress tests and report generation.")
        sys.exit(1)
    
    time.sleep(2)
    
    # Step 4: Run stress tests
    if not run_stress_tests():
        print_warning("Stress tests failed. Report will only include load test results.")
    
    time.sleep(1)
    
    # Step 5: Generate report
    if not generate_report():
        print_warning("Report generation failed. Raw results are still saved.")
    
    # Step 6: Display summary
    time.sleep(1)
    display_summary()
    
    # Final summary
    total_time = time.time() - start_time
    print_header("Phase 4.4: Testing Complete")
    print_success(f"Total execution time: {total_time:.2f} seconds")
    print(f"\n{Colors.GREEN}{'='*80}")
    print("Performance/Load Testing Summary:")
    print("✓ Load tests executed")
    print("✓ Stress test scenarios executed") 
    print("✓ Performance reports generated")
    print("✓ HTML analysis report created")
    print(f"{'='*80}{Colors.END}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\nTesting interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
