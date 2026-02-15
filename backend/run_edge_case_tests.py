#!/usr/bin/env python3
"""
Edge Case Testing Framework Runner
Executes all edge case tests with comprehensive reporting and metrics
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import argparse
from typing import Dict, List, Tuple


class EdgeCaseTestRunner:
    """Comprehensive test runner for edge case testing suite"""
    
    # Test files
    TEST_FILES = [
        'test_edge_cases_audio_chunking.py',
        'test_edge_cases_embeddings.py',
        'test_edge_cases_matching_logic.py',
        'test_edge_cases_enrollment.py',
        'test_edge_cases_database.py',
        'test_edge_cases_websocket.py',
    ]
    
    def __init__(self, workspace_path: str = None):
        """
        Initialize test runner
        
        Args:
            workspace_path: Path to backend directory
        """
        self.workspace_path = workspace_path or os.path.dirname(os.path.abspath(__file__))
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.failed_tests = []
        self.passed_tests = []
        self.skipped_tests = []
        
    def run_all_tests(self, verbose: bool = False, coverage: bool = False) -> int:
        """
        Run all edge case tests
        
        Args:
            verbose: Enable verbose output
            coverage: Generate coverage report
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        print("\n" + "=" * 80)
        print(" " * 15 + "EDGE CASE TESTING FRAMEWORK")
        print(" " * 20 + "COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print(f"\nWorkspace: {self.workspace_path}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Test Files: {len(self.TEST_FILES)}")
        print("-" * 80)
        
        self.start_time = time.time()
        
        for test_file in self.TEST_FILES:
            self.run_test_file(test_file, verbose, coverage)
        
        self.end_time = time.time()
        
        return self.generate_report()

    def run_test_file(self, test_file: str, verbose: bool = False, coverage: bool = False):
        """
        Run a single test file
        
        Args:
            test_file: Name of test file
            verbose: Enable verbose output
            coverage: Generate coverage report
        """
        test_path = os.path.join(self.workspace_path, test_file)
        
        if not os.path.exists(test_path):
            print(f"\n⚠ WARNING: Test file not found: {test_file}")
            self.results[test_file] = {
                'status': 'MISSING',
                'passed': 0,
                'failed': 0,
                'errors': ['Test file not found']
            }
            return
        
        print(f"\nRunning: {test_file}")
        print("-" * 80)
        
        cmd = [sys.executable, "-m", "pytest", test_path]
        
        if verbose:
            cmd.extend(["-v", "--tb=short"])
        else:
            cmd.extend(["-q", "--tb=line"])
        
        if coverage:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            test_output = result.stdout + result.stderr
            
            # Parse results
            self.parse_pytest_output(test_file, test_output, result.returncode)
            
            if result.returncode == 0:
                print(f"✓ {test_file}: PASSED")
            else:
                print(f"✗ {test_file}: FAILED")
                if verbose:
                    print(test_output)
                    
        except subprocess.TimeoutExpired:
            print(f"✗ {test_file}: TIMEOUT (>300s)")
            self.results[test_file] = {
                'status': 'TIMEOUT',
                'passed': 0,
                'failed': 0,
                'errors': ['Test execution timeout']
            }
        except Exception as e:
            print(f"✗ {test_file}: ERROR - {str(e)}")
            self.results[test_file] = {
                'status': 'ERROR',
                'passed': 0,
                'failed': 0,
                'errors': [str(e)]
            }

    def parse_pytest_output(self, test_file: str, output: str, returncode: int):
        """
        Parse pytest output to extract test results
        
        Args:
            test_file: Name of test file
            output: Pytest output
            returncode: Return code from pytest
        """
        results = {
            'status': 'PASSED' if returncode == 0 else 'FAILED',
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Try to extract pytest summary
        for line in output.split('\n'):
            if 'passed' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'passed' in part.lower() and i > 0:
                            results['passed'] = int(parts[i-1])
                except:
                    pass
            
            if 'failed' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'failed' in part.lower() and i > 0:
                            results['failed'] = int(parts[i-1])
                except:
                    pass
            
            if 'skipped' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'skipped' in part.lower() and i > 0:
                            results['skipped'] = int(parts[i-1])
                except:
                    pass
            
            if 'ERROR' in line or 'error' in line.lower():
                results['errors'].append(line.strip())
        
        self.results[test_file] = results

    def run_quick_tests(self) -> int:
        """
        Run quick edge case tests (basic smoke tests)
        
        Returns:
            Exit code
        """
        print("\n" + "=" * 80)
        print(" " * 25 + "QUICK TEST MODE")
        print(" " * 15 + "Running Essential Edge Cases Only")
        print("=" * 80)
        
        quick_tests = [
            ('test_edge_cases_audio_chunking.py', 
             'test_empty_audio_array test_complete_silence test_audio_with_nan_values'),
            ('test_edge_cases_embeddings.py',
             'test_empty_audio_embedding test_identical_embeddings_similarity test_audio_with_nan_values'),
            ('test_edge_cases_matching_logic.py',
             'test_perfect_match_identical_embeddings test_perfect_mismatch_orthogonal_embeddings'),
        ]
        
        self.start_time = time.time()
        
        for test_file, test_names in quick_tests:
            cmd = [sys.executable, "-m", "pytest", test_file, "-k", test_names, "-v"]
            
            print(f"\nQuick: {test_file}")
            try:
                result = subprocess.run(cmd, cwd=self.workspace_path, capture_output=True, timeout=60)
                print("✓ PASSED" if result.returncode == 0 else "✗ FAILED")
            except Exception as e:
                print(f"✗ ERROR: {e}")
        
        self.end_time = time.time()
        return self.generate_report()

    def run_specific_category(self, category: str) -> int:
        """
        Run tests for specific category
        
        Args:
            category: Test category (audio_chunking, embeddings, matching_logic, 
                     enrollment, database, websocket)
        
        Returns:
            Exit code
        """
        category_map = {
            'audio_chunking': 'test_edge_cases_audio_chunking.py',
            'embeddings': 'test_edge_cases_embeddings.py',
            'matching_logic': 'test_edge_cases_matching_logic.py',
            'enrollment': 'test_edge_cases_enrollment.py',
            'database': 'test_edge_cases_database.py',
            'websocket': 'test_edge_cases_websocket.py',
        }
        
        if category not in category_map:
            print(f"Unknown category: {category}")
            print(f"Available categories: {', '.join(category_map.keys())}")
            return 1
        
        test_file = category_map[category]
        
        print("\n" + "=" * 80)
        print(f" " * 20 + f"TESTING CATEGORY: {category.upper()}")
        print("=" * 80)
        
        self.start_time = time.time()
        self.run_test_file(test_file, verbose=True, coverage=False)
        self.end_time = time.time()
        
        return self.generate_report()

    def generate_report(self) -> int:
        """
        Generate comprehensive test report
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        print("\n" + "=" * 80)
        print(" " * 20 + "TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0
        
        print("\nResults by Category:")
        print("-" * 80)
        
        for test_file, results in self.results.items():
            category = test_file.replace('test_edge_cases_', '').replace('.py', '')
            status = results.get('status', 'UNKNOWN')
            passed = results.get('passed', 0)
            failed = results.get('failed', 0)
            skipped = results.get('skipped', 0)
            
            total_passed += passed
            total_failed += failed
            total_skipped += skipped
            total_tests += passed + failed + skipped
            
            if results.get('errors'):
                total_errors += len(results.get('errors', []))
            
            status_icon = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "⚠"
            print(f"{status_icon} {category:20} | Passed: {passed:4} | Failed: {failed:4} | "
                  f"Skipped: {skipped:4} | Status: {status}")
        
        print("-" * 80)
        print(f"Total Tests: {total_tests:4} | Passed: {total_passed:4} | Failed: {total_failed:4} | "
              f"Skipped: {total_skipped:4} | Errors: {total_errors:4}")
        
        # Execution time
        if self.start_time and self.end_time:
            elapsed = self.end_time - self.start_time
            print(f"\nExecution Time: {elapsed:.2f} seconds")
        
        # Overall status
        print("\n" + "=" * 80)
        if total_failed == 0 and total_errors == 0:
            print(" " * 20 + "✓ ALL TESTS PASSED")
            print("=" * 80)
            return 0
        else:
            print(" " * 15 + f"✗ TESTS FAILED: {total_failed} failed, {total_errors} errors")
            print("=" * 80)
            return 1

    def generate_json_report(self, output_file: str = "edge_case_test_results.json"):
        """
        Generate JSON report
        
        Args:
            output_file: Output file path
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_files': list(self.TEST_FILES),
            'results': self.results,
            'execution_time': (self.end_time - self.start_time) if (self.start_time and self.end_time) else None
        }
        
        output_path = os.path.join(self.workspace_path, output_file)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nJSON Report saved to: {output_path}")

    def list_test_files(self):
        """List all available test files"""
        print("\n" + "=" * 80)
        print(" " * 15 + "AVAILABLE EDGE CASE TEST FILES")
        print("=" * 80)
        
        for i, test_file in enumerate(self.TEST_FILES, 1):
            test_path = os.path.join(self.workspace_path, test_file)
            exists = "✓" if os.path.exists(test_path) else "✗"
            category = test_file.replace('test_edge_cases_', '').replace('.py', '')
            print(f"{exists} {i}. {category:20} ({test_file})")
        
        print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Edge Case Testing Framework for Voice Biometric System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_edge_case_tests.py --all              # Run all tests
  python run_edge_case_tests.py --quick            # Quick smoke tests
  python run_edge_case_tests.py --category audio_chunking  # Specific category
  python run_edge_case_tests.py --list             # List all tests
  python run_edge_case_tests.py --all --coverage   # All tests with coverage
        """
    )
    
    parser.add_argument('--all', action='store_true', help='Run all edge case tests')
    parser.add_argument('--quick', action='store_true', help='Run quick smoke tests only')
    parser.add_argument('--category', type=str, help='Run specific test category')
    parser.add_argument('--list', action='store_true', help='List all available tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--json-report', action='store_true', help='Generate JSON report')
    
    args = parser.parse_args()
    
    # Get workspace path
    workspace_path = os.path.dirname(os.path.abspath(__file__))
    runner = EdgeCaseTestRunner(workspace_path)
    
    # Execute requested action
    if args.list:
        runner.list_test_files()
        return 0
    
    elif args.quick:
        exit_code = runner.run_quick_tests()
    
    elif args.category:
        exit_code = runner.run_specific_category(args.category)
    
    elif args.all:
        exit_code = runner.run_all_tests(verbose=args.verbose, coverage=args.coverage)
    
    else:
        # Default: run all tests
        exit_code = runner.run_all_tests(verbose=args.verbose, coverage=args.coverage)
    
    # Generate JSON report if requested
    if args.json_report:
        runner.generate_json_report()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
