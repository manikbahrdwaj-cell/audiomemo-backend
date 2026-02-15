#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration Tests Verification Script
======================================

Validates that integration tests are properly set up and ready to run
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Tuple, Dict
import json

# Fix Windows UTF-8 encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Color codes for terminal output
class Colors:
    """Terminal color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def check_python_version() -> bool:
    """Check Python version (3.8+)"""
    print_header("1. Checking Python Version")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version_str} (required: 3.8+)")
        return True
    else:
        print_error(f"Python {version_str} - Please upgrade to Python 3.8 or later")
        return False

def check_test_file_exists() -> bool:
    """Check if integration test file exists"""
    print_header("2. Checking Test Files")
    
    test_file = Path("test_integration_flows.py")
    if test_file.exists():
        size_kb = test_file.stat().st_size / 1024
        print_success(f"test_integration_flows.py ({size_kb:.1f} KB)")
        return True
    else:
        print_error("test_integration_flows.py not found")
        return False

def check_documentation_files() -> bool:
    """Check if documentation files exist"""
    print_header("3. Checking Documentation")
    
    doc_files = [
        "INTEGRATION_TESTS_DOCUMENTATION.md",
        "INTEGRATION_TESTS_QUICK_REFERENCE.md"
    ]
    
    all_exist = True
    for doc_file in doc_files:
        if Path(doc_file).exists():
            print_success(f"{doc_file}")
        else:
            print_error(f"{doc_file} not found")
            all_exist = False
    
    return all_exist

def check_required_packages() -> bool:
    """Check if required packages are installed"""
    print_header("4. Checking Required Packages")
    
    required_packages = {
        'pytest': 'Testing framework',
        'numpy': 'Numerical computing',
        'torch': 'PyTorch (for embedding model)',
        'soundfile': 'Audio file I/O',
    }
    
    optional_packages = {
        'pytest_cov': 'Coverage reporting',
        'pytest_html': 'HTML reports',
        'pytest_asyncio': 'Async test support',
        'bson': 'MongoDB serialization',
    }
    
    all_installed = True
    
    # Check required packages
    print(f"{Colors.BOLD}Required Packages:{Colors.RESET}")
    for package, description in required_packages.items():
        spec = importlib.util.find_spec(package)
        if spec is not None:
            try:
                mod = importlib.import_module(package)
                version = getattr(mod, '__version__', 'unknown')
                print_success(f"{package:20} ({description}) - v{version}")
            except Exception as e:
                print_warning(f"{package:20} ({description}) - installed but error loading")
        else:
            print_error(f"{package:20} ({description}) - NOT INSTALLED")
            all_installed = False
    
    # Check optional packages
    print(f"\n{Colors.BOLD}Optional Packages:{Colors.RESET}")
    for package, description in optional_packages.items():
        spec = importlib.util.find_spec(package)
        if spec is not None:
            print_success(f"{package:20} ({description})")
        else:
            print_warning(f"{package:20} ({description}) - not installed (optional)")
    
    return all_installed

def check_test_file_content() -> bool:
    """Check that test file has valid content"""
    print_header("5. Checking Test File Content")
    
    try:
        with open("test_integration_flows.py", "r") as f:
            content = f.read()
        
        # Check for key test classes
        test_classes = [
            "TestEnrollmentFlowIntegration",
            "TestVerificationFlowIntegration",
            "TestAudioProcessingPipeline",
            "TestEmbeddingMatchingPipeline",
            "TestMultiSpeakerScenarios",
            "TestErrorHandlingAndRecovery",
            "TestEndToEndAPIFlow",
            "TestPerformanceAndStress"
        ]
        
        all_found = True
        for test_class in test_classes:
            if f"class {test_class}" in content:
                print_success(f"Found test suite: {test_class}")
            else:
                print_error(f"Missing test suite: {test_class}")
                all_found = False
        
        # Count test methods
        test_count = content.count("def test_")
        print_info(f"Total test methods: {test_count}")
        
        return all_found
    
    except Exception as e:
        print_error(f"Error reading test file: {e}")
        return False

def check_pytest_installed() -> bool:
    """Check if pytest can be run"""
    print_header("6. Checking Pytest Installation")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_line = result.stdout.strip()
            print_success(f"pytest: {version_line}")
            return True
        else:
            print_error(f"pytest --version returned: {result.stderr}")
            return False
    
    except Exception as e:
        print_error(f"Could not run pytest: {e}")
        return False

def try_collect_tests() -> Tuple[bool, int]:
    """Try to collect tests"""
    print_header("7. Collecting Tests")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "test_integration_flows.py", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Parse output to count tests
            output = result.stdout
            # Look for "X tests collected"
            import re
            match = re.search(r'(\d+) test', output)
            if match:
                test_count = int(match.group(1))
                print_success(f"Successfully collected {test_count} tests")
                
                # List test suites
                print_info("Test suites found:")
                for line in output.split('\n'):
                    if '::Test' in line:
                        # Extract class name
                        parts = line.split('::')
                        if len(parts) >= 2:
                            test_info = parts[1].strip()
                            if test_info:
                                print(f"  - {test_info}")
                
                return True, test_count
            else:
                print_warning("Could not parse test count from output")
                print(f"pytest output:\n{output}")
                return False, 0
        else:
            print_error(f"pytest collection failed: {result.stderr}")
            return False, 0
    
    except subprocess.TimeoutExpired:
        print_error("pytest collection timed out")
        return False, 0
    except Exception as e:
        print_error(f"Error collecting tests: {e}")
        return False, 0

def generate_verification_report() -> Dict:
    """Generate verification report"""
    print_header("INTEGRATION TESTS VERIFICATION REPORT")
    
    results = {
        'python_version': check_python_version(),
        'test_file': check_test_file_exists(),
        'documentation': check_documentation_files(),
        'required_packages': check_required_packages(),
        'test_content': check_test_file_content(),
        'pytest_installed': check_pytest_installed(),
    }
    
    # Try to collect tests
    try_collect_result, test_count = try_collect_tests()
    results['test_collection'] = try_collect_result
    results['test_count'] = test_count
    
    return results

def print_summary(results: Dict):
    """Print verification summary"""
    print_header("VERIFICATION SUMMARY")
    
    checks = {
        'python_version': ('Python Version', results['python_version']),
        'test_file': ('Test File Exists', results['test_file']),
        'documentation': ('Documentation Files', results['documentation']),
        'required_packages': ('Required Packages', results['required_packages']),
        'test_content': ('Test Content Valid', results['test_content']),
        'pytest_installed': ('Pytest Installed', results['pytest_installed']),
        'test_collection': ('Test Collection', results['test_collection']),
    }
    
    passed = 0
    failed = 0
    
    print(f"{Colors.BOLD}Checks:{Colors.RESET}")
    for check_key, (check_name, check_result) in checks.items():
        status = "PASS" if check_result else "FAIL"
        symbol = "✓" if check_result else "✗"
        color = Colors.GREEN if check_result else Colors.RED
        
        print(f"  {color}{symbol}{Colors.RESET} {check_name:30} {status}")
        
        if check_result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{Colors.BOLD}Statistics:{Colors.RESET}")
    print(f"  Checks Passed: {Colors.GREEN}{passed}{Colors.RESET}/{passed + failed}")
    print(f"  Checks Failed: {Colors.RED}{failed}{Colors.RESET}/{passed + failed}")
    
    if results['test_count'] > 0:
        print(f"  Total Tests: {Colors.BLUE}{results['test_count']}{Colors.RESET}")
    
    # Determine overall result
    if failed == 0 and results['test_collection']:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ VERIFICATION PASSED{Colors.RESET}")
        print(f"{Colors.GREEN}Integration tests are ready to run!{Colors.RESET}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ VERIFICATION FAILED{Colors.RESET}")
        print(f"{Colors.RED}Please fix the issues above before running tests.{Colors.RESET}")
        return False

def print_next_steps():
    """Print next steps"""
    print_header("NEXT STEPS")
    
    print(f"{Colors.BOLD}To run the integration tests:{Colors.RESET}\n")
    
    print(f"{Colors.YELLOW}Option 1: Run all tests{Colors.RESET}")
    print(f"  $ pytest test_integration_flows.py -v\n")
    
    print(f"{Colors.YELLOW}Option 2: Run fast tests only{Colors.RESET}")
    print(f"  $ pytest test_integration_flows.py -m \"not slow\" -v\n")
    
    print(f"{Colors.YELLOW}Option 3: Run specific test suite{Colors.RESET}")
    print(f"  $ pytest test_integration_flows.py::TestEnrollmentFlowIntegration -v\n")
    
    print(f"{Colors.YELLOW}Option 4: Run with coverage report{Colors.RESET}")
    print(f"  $ pytest test_integration_flows.py --cov --cov-report=html\n")
    
    print(f"{Colors.YELLOW}Option 5: Run with HTML report{Colors.RESET}")
    print(f"  $ pytest test_integration_flows.py --html=report.html\n")
    
    print(f"{Colors.BOLD}For more information:{Colors.RESET}")
    print(f"  - Read: INTEGRATION_TESTS_QUICK_REFERENCE.md")
    print(f"  - Read: INTEGRATION_TESTS_DOCUMENTATION.md")
    print(f"  - Check: test_integration_flows.py (well-commented code)\n")

def print_troubleshooting():
    """Print troubleshooting tips"""
    print_header("TROUBLESHOOTING")
    
    print(f"{Colors.BOLD}Common Issues:{Colors.RESET}\n")
    
    print(f"{Colors.YELLOW}Issue: ModuleNotFoundError{Colors.RESET}")
    print(f"  Solution: pip install -r requirements-test.txt\n")
    
    print(f"{Colors.YELLOW}Issue: pytest not found{Colors.RESET}")
    print(f"  Solution: pip install pytest\n")
    
    print(f"{Colors.YELLOW}Issue: Tests hang/timeout{Colors.RESET}")
    print(f"  Solution: pytest test_integration_flows.py --timeout=60\n")
    
    print(f"{Colors.YELLOW}Issue: High memory usage{Colors.RESET}")
    print(f"  Solution: pytest test_integration_flows.py (no parallelization)\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main verification function"""
    print("\n")
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         INTEGRATION TESTS VERIFICATION SUITE                      ║")
    print("║         Voice Biometric Authentication System                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    # Run verification
    results = generate_verification_report()
    
    # Print summary
    success = print_summary(results)
    
    # Print next steps and troubleshooting
    print_next_steps()
    if not success:
        print_troubleshooting()
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
