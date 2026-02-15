#!/usr/bin/env python3
"""
Testing Framework Initialization & Verification Script
Verifies that all testing dependencies are installed and configured correctly
"""

import subprocess
import sys
from pathlib import Path
import importlib.util

class TestingSetupVerifier:
    """Verifies testing framework installation and configuration"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.all_passed = True
        self.results = []
    
    def check(self, name: str, condition: bool, message: str = ""):
        """Record a check result"""
        status = "[OK]" if condition else "[FAIL]"
        self.results.append((status, name, message if not condition else "OK"))
        if not condition:
            self.all_passed = False
            print(f"{status} {name}: {message}")
        else:
            print(f"{status} {name}")
    
    def check_module(self, module_name: str, package_name: str = None):
        """Check if a Python module is installed"""
        if package_name is None:
            package_name = module_name
        
        spec = importlib.util.find_spec(module_name)
        is_installed = spec is not None
        self.check(f"Module: {package_name}", is_installed, 
                  f"Install with: pip install {package_name}")
        return is_installed
    
    def check_file(self, filepath: str, description: str = ""):
        """Check if a file exists"""
        path = self.backend_dir / filepath
        exists = path.exists()
        msg = f" ({description})" if description else ""
        self.check(f"File: {filepath}{msg}", exists,
                  f"File not found: {path}")
        return exists
    
    def run_command(self, cmd: list, description: str = ""):
        """Run a command and check if it succeeds"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                capture_output=True,
                timeout=10
            )
            success = result.returncode == 0
            self.check(f"Command: {' '.join(cmd[:2])}", success,
                      f"Failed: {result.stderr.decode()[:50]}")
            return success
        except subprocess.TimeoutExpired:
            self.check(f"Command: {' '.join(cmd[:2])}", False,
                      "Command timed out")
            return False
        except Exception as e:
            self.check(f"Command: {' '.join(cmd[:2])}", False,
                      f"Error: {str(e)[:50]}")
            return False
    
    def verify_installation(self):
        """Verify testing framework installation"""
        print("\n" + "="*60)
        print("TESTING FRAMEWORK VERIFICATION")
        print("="*60 + "\n")
        
        print("1. Checking Core Testing Dependencies...")
        print("-" * 40)
        
        core_packages = [
            ("pytest", "pytest"),
            ("pytest_cov", "pytest-cov"),
            ("pytest_mock", "pytest-mock"),
            ("unittest.mock", "unittest.mock (built-in)"),
            ("numpy", "numpy"),
            ("scipy", "scipy"),
        ]
        
        for module, package in core_packages:
            self.check_module(module, package)
        
        print("\n2. Checking Optional Testing Tools...")
        print("-" * 40)
        
        optional_packages = [
            ("pytest_xdist", "pytest-xdist"),
            ("pytest_html", "pytest-html"),
            ("pytest_benchmark", "pytest-benchmark"),
            ("pytest_json_report", "pytest-json-report"),
        ]
        
        for module, package in optional_packages:
            self.check_module(module, package)
        
        print("\n3. Checking Test Files...")
        print("-" * 40)
        
        test_files = [
            ("test_suite_complete.py", "Main test suite"),
            ("conftest.py", "Pytest configuration"),
            ("pytest.ini", "Pytest settings"),
            ("run_tests.py", "Test runner script"),
            ("requirements-test.txt", "Test dependencies"),
            ("TESTING_GUIDE_COMPREHENSIVE.md", "Testing guide"),
        ]
        
        for filepath, description in test_files:
            self.check_file(filepath, description)
        
        print("\n4. Checking Python Syntax...")
        print("-" * 40)
        
        self.run_command([sys.executable, "-m", "py_compile", "test_suite_complete.py"],
                        "Test suite syntax")
        self.run_command([sys.executable, "-m", "py_compile", "conftest.py"],
                        "Conftest syntax")
        self.run_command([sys.executable, "-m", "py_compile", "run_tests.py"],
                        "Runner script syntax")
        
        print("\n5. Checking Pytest Installation...")
        print("-" * 40)
        
        self.run_command([sys.executable, "-m", "pytest", "--version"],
                        "Pytest version")
        
        print("\n6. Checking Test Collection...")
        print("-" * 40)
        
        self.run_command([sys.executable, "-m", "pytest", 
                         "test_suite_complete.py", "--collect-only", "-q"],
                        "Test collection")
        
        return self.all_passed
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60 + "\n")
        
        if self.all_passed:
            print("[OK] All checks passed!")
            print("\nYou can now run tests with:")
            print("  python run_tests.py --all")
            print("  python run_tests.py --quick")
            print("  python run_tests.py --coverage")
            print("\nOr use pytest directly:")
            print("  python -m pytest test_suite_complete.py -v")
            print("  python -m pytest -m unit -v")
            return 0
        else:
            print("[FAIL] Some checks failed")
            print("\nFailing checks:")
            for status, name, message in self.results:
                if status == "[FAIL]":
                    print(f"  [FAIL] {name}: {message}")
            
            print("\nTo fix, run:")
            print("  pip install -r requirements-test.txt")
            return 1
    
    def run(self):
        """Run complete verification"""
        try:
            self.verify_installation()
            return self.print_summary()
        except Exception as e:
            print(f"\n[FAIL] Verification failed: {e}")
            return 1


def main():
    """Main entry point"""
    verifier = TestingSetupVerifier()
    return verifier.run()


if __name__ == "__main__":
    sys.exit(main())
