#!/usr/bin/env python3
"""
Test Runner Script
Provides convenient ways to run pytest with various configurations
"""

import subprocess
import sys
import argparse
from pathlib import Path


class TestRunner:
    """Manages test execution with different configurations"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        
    def run_all_tests(self, verbose=True):
        """Run all tests"""
        cmd = ["python", "-m", "pytest"]
        if verbose:
            cmd.append("-v")
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_tests_by_marker(self, marker, verbose=True):
        """Run tests with specific marker"""
        cmd = ["python", "-m", "pytest", "-m", marker]
        if verbose:
            cmd.append("-v")
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_tests_by_module(self, module_name, verbose=True):
        """Run tests for specific module"""
        cmd = ["python", "-m", "pytest", f"test_{module_name}.py"]
        if verbose:
            cmd.append("-v")
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_tests_with_coverage(self):
        """Run tests with coverage reporting"""
        cmd = [
            "python", "-m", "pytest",
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "-v"
        ]
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_quick_smoke_tests(self):
        """Run quick smoke tests"""
        cmd = ["python", "-m", "pytest", "-m", "smoke", "-v"]
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_fast_tests(self):
        """Run only fast tests (exclude slow tests)"""
        cmd = ["python", "-m", "pytest", "-m", "not slow", "-v"]
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_specific_test(self, test_path, verbose=True):
        """Run specific test file or test function"""
        cmd = ["python", "-m", "pytest", test_path]
        if verbose:
            cmd.append("-v")
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_with_output_file(self, output_file="test_results.txt"):
        """Run tests and save output to file"""
        with open(output_file, 'w') as f:
            cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
            return subprocess.run(cmd, cwd=self.backend_dir, stdout=f, stderr=subprocess.STDOUT)
    
    def run_with_junit_report(self, report_file="test_results.xml"):
        """Run tests and generate JUnit XML report"""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            f"--junit-xml={report_file}",
            "--tb=short"
        ]
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_with_html_report(self, report_file="test_results.html"):
        """Run tests and generate HTML report"""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            f"--html={report_file}",
            "--self-contained-html",
            "--tb=short"
        ]
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_parallel_tests(self, num_workers=4):
        """Run tests in parallel"""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "-n", str(num_workers),
            "--tb=short"
        ]
        return subprocess.run(cmd, cwd=self.backend_dir)
    
    def run_with_profiling(self):
        """Run tests with performance profiling"""
        cmd = [
            "python", "-m", "pytest",
            "-v",
            "--profile",
            "--profile-svg",
            "--tb=short"
        ]
        return subprocess.run(cmd, cwd=self.backend_dir)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test runner for Voice Biometric API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --quick           # Run quick smoke tests
  python run_tests.py --coverage        # Run with coverage
  python run_tests.py --marker unit     # Run unit tests only
  python run_tests.py --module embedding_operations
  python run_tests.py --specific test_voice_embedding.py::TestVoiceEmbedding::test_embedding_generation_basic
  python run_tests.py --parallel 4      # Run 4 tests in parallel
  python run_tests.py --html            # Generate HTML report
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (default)"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick smoke tests"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run fast tests (exclude slow tests)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    parser.add_argument(
        "--marker",
        type=str,
        help="Run tests with specific marker"
    )
    
    parser.add_argument(
        "--module",
        type=str,
        help="Run tests for specific module"
    )
    
    parser.add_argument(
        "--specific",
        type=str,
        help="Run specific test (file or test path)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Save output to file"
    )
    
    parser.add_argument(
        "--junit",
        type=str,
        help="Generate JUnit XML report"
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML report"
    )
    
    parser.add_argument(
        "--parallel",
        type=int,
        metavar="N",
        help="Run tests in parallel with N workers"
    )
    
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run with performance profiling"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.quick:
            print("Running quick smoke tests...")
            result = runner.run_quick_smoke_tests()
        
        elif args.fast:
            print("Running fast tests (excluding slow tests)...")
            result = runner.run_fast_tests()
        
        elif args.coverage:
            print("Running tests with coverage reporting...")
            result = runner.run_tests_with_coverage()
        
        elif args.marker:
            print(f"Running tests with marker: {args.marker}")
            result = runner.run_tests_by_marker(args.marker)
        
        elif args.module:
            print(f"Running tests for module: {args.module}")
            result = runner.run_tests_by_module(args.module)
        
        elif args.specific:
            print(f"Running specific test: {args.specific}")
            result = runner.run_specific_test(args.specific)
        
        elif args.parallel:
            print(f"Running tests in parallel with {args.parallel} workers...")
            result = runner.run_parallel_tests(args.parallel)
        
        elif args.profile:
            print("Running tests with profiling...")
            result = runner.run_with_profiling()
        
        elif args.html:
            print("Running tests with HTML report...")
            result = runner.run_with_html_report()
        
        elif args.junit:
            print(f"Running tests with JUnit report: {args.junit}")
            result = runner.run_with_junit_report(args.junit)
        
        elif args.output:
            print(f"Running tests with output to: {args.output}")
            result = runner.run_with_output_file(args.output)
        
        else:
            print("Running all tests...")
            result = runner.run_all_tests()
        
        return result.returncode
    
    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
