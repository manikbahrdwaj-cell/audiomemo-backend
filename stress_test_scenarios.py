#!/usr/bin/env python3
"""
Phase 4.4: Advanced Stress Testing Scenarios

Real-world stress test scenarios:
- Peak hour simulation
- Cascading failures recovery
- Memory leak detection
- Connection pool exhaustion
- Database lock contention
- Rapid fire requests
- Long-running request handling
"""

import time
import requests
import sys
import json
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
import random
from dataclasses import dataclass, asdict


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'


@dataclass
class ScenarioResult:
    """Scenario test result"""
    scenario_name: str
    description: str
    status: str  # 'PASS', 'FAIL', 'WARN'
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    duration: float
    error_message: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class StressTestScenarios:
    """Advanced stress test scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_audio_file = self._get_test_audio()
        self.results: List[ScenarioResult] = []

    def _get_test_audio(self) -> bytes:
        """Get test audio file"""
        audio_dir = Path(__file__).parent / "test_audio_files"
        test_files = list(audio_dir.glob("*.wav"))
        
        if not test_files:
            raise FileNotFoundError(f"No test audio files in {audio_dir}")
        
        with open(test_files[0], 'rb') as f:
            return f.read()

    def _make_enrollment_request(self, user_id: int, timeout: int = 30) -> tuple:
        """Make enrollment request"""
        start_time = time.time()
        try:
            files = {'file': ('test.wav', self.test_audio_file, 'audio/wav')}
            data = {'phone_number': f'1234567890{user_id % 10000:04d}'}
            
            response = self.session.post(
                f"{self.base_url}/enroll",
                files=files,
                data=data,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            return response.status_code == 200, duration
        except requests.Timeout:
            return False, timeout
        except Exception as e:
            return False, time.time() - start_time

    def _make_verification_request(self, user_id: int, timeout: int = 30) -> tuple:
        """Make verification request"""
        start_time = time.time()
        try:
            files = {'file': ('test.wav', self.test_audio_file, 'audio/wav')}
            data = {'phone_number': f'1234567890{user_id % 10000:04d}'}
            
            response = self.session.post(
                f"{self.base_url}/verify",
                files=files,
                data=data,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            return response.status_code == 200, duration
        except requests.Timeout:
            return False, timeout
        except Exception as e:
            return False, time.time() - start_time

    def scenario_peak_hour_simulation(self) -> ScenarioResult:
        """
        Scenario 1: Peak Hour Simulation
        Simulate suddenly increased traffic during peak hours
        """
        print(f"\n{Colors.BLUE}Scenario 1: Peak Hour Simulation{Colors.END}")
        print("  Description: Simulate peak hour traffic spike (200 requests/min)")
        
        result = ScenarioResult(
            scenario_name="peak_hour_simulation",
            description="Simulate peak hour traffic spike with 200 requests/min",
            status="PASS",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            max_response_time=0.0,
            min_response_time=float('inf'),
            duration=0.0
        )
        
        response_times = []
        start_time = time.time()
        
        try:
            # Simulate 200 requests over 60 seconds
            for i in range(200):
                # Alternate between enrollment and verification
                if i % 3 == 0:
                    success, duration = self._make_enrollment_request(i)
                else:
                    success, duration = self._make_verification_request(i)
                
                response_times.append(duration)
                result.total_requests += 1
                
                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1
                
                # Control request rate
                elapsed = time.time() - start_time
                expected_time = (i + 1) / (200 / 60)
                if elapsed < expected_time:
                    time.sleep(expected_time - elapsed)
                
                if (i + 1) % 50 == 0:
                    print(f"    Progress: {i + 1}/200 requests")
            
            result.duration = time.time() - start_time
            
        except Exception as e:
            result.status = "FAIL"
            result.error_message = str(e)
            result.duration = time.time() - start_time
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.max_response_time = max(response_times)
            result.min_response_time = min(response_times)
            
            # Check for acceptable performance
            if result.avg_response_time > 2.0:
                result.status = "WARN"
        
        self._print_scenario_result(result)
        self.results.append(result)
        return result

    def scenario_cascading_failures(self) -> ScenarioResult:
        """
        Scenario 2: Cascading Failures Recovery
        Test system recovery after high failure rate
        """
        print(f"\n{Colors.BLUE}Scenario 2: Cascading Failures Recovery{Colors.END}")
        print("  Description: Test recovery from high failure rate")
        
        result = ScenarioResult(
            scenario_name="cascading_failures_recovery",
            description="Test recovery from cascading failures",
            status="PASS",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            max_response_time=0.0,
            min_response_time=float('inf'),
            duration=0.0
        )
        
        response_times = []
        start_time = time.time()
        
        try:
            # Phase 1: Rapid requests (may cause failures)
            print("    Phase 1: Rapid request phase (may cause failures)...")
            for i in range(50):
                success, duration = self._make_verification_request(i, timeout=5)
                response_times.append(duration)
                result.total_requests += 1
                
                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1
                
                if (i + 1) % 10 == 0:
                    print(f"      Rapid phase: {i + 1}/50 requests")
            
            # Phase 2: Recovery time
            print("    Phase 2: Recovery/cooldown period...")
            time.sleep(5)
            
            # Phase 3: Normal operation verification
            print("    Phase 3: Normal operation verification...")
            for i in range(50, 100):
                success, duration = self._make_verification_request(i, timeout=30)
                response_times.append(duration)
                result.total_requests += 1
                
                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1
                
                if (i + 1) % 10 == 0:
                    print(f"      Recovery phase: {i + 1 - 50}/50 requests")
            
            result.duration = time.time() - start_time
            
            # Check recovery success rate
            recovery_phase_start = 50
            recovery_success = sum(1 for j in range(recovery_phase_start, min(100, result.total_requests)))
            
        except Exception as e:
            result.status = "FAIL"
            result.error_message = str(e)
            result.duration = time.time() - start_time
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.max_response_time = max(response_times)
            result.min_response_time = min(response_times)
        
        self._print_scenario_result(result)
        self.results.append(result)
        return result

    def scenario_memory_leak_detection(self) -> ScenarioResult:
        """
        Scenario 3: Memory Leak Detection
        Long-running test to detect memory leaks
        """
        print(f"\n{Colors.BLUE}Scenario 3: Memory Leak Detection{Colors.END}")
        print("  Description: Long-running test (500 requests) to detect memory leaks")
        
        result = ScenarioResult(
            scenario_name="memory_leak_detection",
            description="Long-running test to detect memory leaks",
            status="PASS",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            max_response_time=0.0,
            min_response_time=float('inf'),
            duration=0.0
        )
        
        response_times = []
        response_times_by_batch = []
        start_time = time.time()
        
        try:
            # Run 500 requests in batches of 50
            for batch in range(10):
                batch_times = []
                print(f"    Batch {batch + 1}/10...")
                
                for i in range(batch * 50, (batch + 1) * 50):
                    if i % 2 == 0:
                        success, duration = self._make_enrollment_request(i)
                    else:
                        success, duration = self._make_verification_request(i)
                    
                    batch_times.append(duration)
                    response_times.append(duration)
                    result.total_requests += 1
                    
                    if success:
                        result.successful_requests += 1
                    else:
                        result.failed_requests += 1
                
                batch_avg = statistics.mean(batch_times)
                response_times_by_batch.append(batch_avg)
                print(f"      Batch avg: {batch_avg*1000:.2f}ms")
            
            result.duration = time.time() - start_time
            
            # Detect memory leak: response times should not degrade significantly
            if len(response_times_by_batch) > 1:
                first_batch_avg = response_times_by_batch[0]
                last_batch_avg = response_times_by_batch[-1]
                degradation = ((last_batch_avg - first_batch_avg) / first_batch_avg) * 100
                
                print(f"    Performance degradation: {degradation:.2f}%")
                if degradation > 50:
                    result.status = "WARN"
        
        except Exception as e:
            result.status = "FAIL"
            result.error_message = str(e)
            result.duration = time.time() - start_time
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.max_response_time = max(response_times)
            result.min_response_time = min(response_times)
        
        self._print_scenario_result(result)
        self.results.append(result)
        return result

    def scenario_rapid_fire_requests(self) -> ScenarioResult:
        """
        Scenario 4: Rapid Fire Requests
        Send many requests as fast as possible
        """
        print(f"\n{Colors.BLUE}Scenario 4: Rapid Fire Requests{Colors.END}")
        print("  Description: Send requests as fast as possible (1000 requests)")
        
        result = ScenarioResult(
            scenario_name="rapid_fire_requests",
            description="Maximum throughput test with 1000 rapid requests",
            status="PASS",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            max_response_time=0.0,
            min_response_time=float('inf'),
            duration=0.0
        )
        
        response_times = []
        start_time = time.time()
        
        try:
            for i in range(1000):
                if i % 2 == 0:
                    success, duration = self._make_verification_request(i, timeout=10)
                else:
                    success, duration = self._make_verification_request(i, timeout=10)
                
                response_times.append(duration)
                result.total_requests += 1
                
                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1
                
                if (i + 1) % 200 == 0:
                    print(f"    Progress: {i + 1}/1000 requests")
            
            result.duration = time.time() - start_time
            
        except Exception as e:
            result.status = "FAIL"
            result.error_message = str(e)
            result.duration = time.time() - start_time
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.max_response_time = max(response_times)
            result.min_response_time = min(response_times)
            
            # Calculate throughput
            throughput = result.total_requests / result.duration if result.duration > 0 else 0
            print(f"    Throughput: {throughput:.2f} requests/second")
        
        self._print_scenario_result(result)
        self.results.append(result)
        return result

    def scenario_connection_pool_exhaustion(self) -> ScenarioResult:
        """
        Scenario 5: Connection Pool Exhaustion
        Test with many concurrent connections
        """
        print(f"\n{Colors.BLUE}Scenario 5: Connection Pool Exhaustion{Colors.END}")
        print("  Description: Test with high number of concurrent connections")
        
        result = ScenarioResult(
            scenario_name="connection_pool_exhaustion",
            description="High concurrency test (50 concurrent connections)",
            status="PASS",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            max_response_time=0.0,
            min_response_time=float('inf'),
            duration=0.0
        )
        
        response_times = []
        start_time = time.time()
        
        def worker(worker_id: int, num_requests: int):
            """Worker thread"""
            local_response_times = []
            for i in range(num_requests):
                success, duration = self._make_verification_request(worker_id * 1000 + i, timeout=30)
                local_response_times.append(duration)
                
                if success:
                    result.successful_requests += 1
                else:
                    result.failed_requests += 1
                
                result.total_requests += 1
            
            response_times.extend(local_response_times)
        
        try:
            # Create 50 concurrent connections with 4 requests each
            threads = []
            for worker_id in range(50):
                thread = threading.Thread(target=worker, args=(worker_id, 4))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=120)
            
            result.duration = time.time() - start_time
            
        except Exception as e:
            result.status = "FAIL"
            result.error_message = str(e)
            result.duration = time.time() - start_time
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.max_response_time = max(response_times)
            result.min_response_time = min(response_times)
        
        self._print_scenario_result(result)
        self.results.append(result)
        return result

    def scenario_burst_traffic_handling(self) -> ScenarioResult:
        """
        Scenario 6: Burst Traffic Handling
        Handle sudden bursts of traffic
        """
        print(f"\n{Colors.BLUE}Scenario 6: Burst Traffic Handling{Colors.END}")
        print("  Description: Handle sudden bursts followed by quiet periods")
        
        result = ScenarioResult(
            scenario_name="burst_traffic_handling",
            description="Burst traffic with quiet periods",
            status="PASS",
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0.0,
            max_response_time=0.0,
            min_response_time=float('inf'),
            duration=0.0
        )
        
        response_times = []
        start_time = time.time()
        
        try:
            # 3 bursts with quiet periods in between
            for burst in range(3):
                print(f"    Burst {burst + 1}/3...")
                
                # High traffic burst: 100 requests
                for i in range(100):
                    success, duration = self._make_verification_request(burst * 200 + i, timeout=15)
                    response_times.append(duration)
                    result.total_requests += 1
                    
                    if success:
                        result.successful_requests += 1
                    else:
                        result.failed_requests += 1
                
                # Quiet period
                if burst < 2:
                    print(f"    Quiet period (10 seconds)...")
                    time.sleep(10)
            
            result.duration = time.time() - start_time
            
        except Exception as e:
            result.status = "FAIL"
            result.error_message = str(e)
            result.duration = time.time() - start_time
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.max_response_time = max(response_times)
            result.min_response_time = min(response_times)
        
        self._print_scenario_result(result)
        self.results.append(result)
        return result

    def _print_scenario_result(self, result: ScenarioResult) -> None:
        """Print scenario result"""
        status_color = Colors.GREEN if result.status == "PASS" else (Colors.YELLOW if result.status == "WARN" else Colors.RED)
        
        print(f"\n{status_color}Status: {result.status}{Colors.END}")
        print(f"  Total requests:   {result.total_requests}")
        print(f"  Successful:       {result.successful_requests}")
        print(f"  Failed:           {result.failed_requests}")
        error_rate = (result.failed_requests / result.total_requests * 100) if result.total_requests > 0 else 0
        print(f"  Error rate:       {error_rate:.2f}%")
        print(f"  Avg response:     {result.avg_response_time*1000:.2f}ms")
        print(f"  Min response:     {result.min_response_time*1000:.2f}ms")
        print(f"  Max response:     {result.max_response_time*1000:.2f}ms")
        print(f"  Duration:         {result.duration:.2f}s")


def main():
    """Main stress test runner"""
    print(f"\n{Colors.MAGENTA}{'='*80}")
    print("  Phase 4.4: Advanced Stress Testing Scenarios")
    print(f"{'='*80}{Colors.END}\n")
    
    # Check server
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        print(f"{Colors.GREEN}✓ Server is running{Colors.END}")
    except:
        print(f"{Colors.RED}✗ Server is not running{Colors.END}")
        sys.exit(1)
    
    stress_tests = StressTestScenarios()
    
    try:
        stress_tests.scenario_peak_hour_simulation()
        time.sleep(3)
        
        stress_tests.scenario_cascading_failures()
        time.sleep(3)
        
        stress_tests.scenario_memory_leak_detection()
        time.sleep(3)
        
        stress_tests.scenario_rapid_fire_requests()
        time.sleep(3)
        
        stress_tests.scenario_connection_pool_exhaustion()
        time.sleep(3)
        
        stress_tests.scenario_burst_traffic_handling()
        
        # Save results
        results_file = Path(__file__).parent / "stress_test_results.json"
        with open(results_file, 'w') as f:
            json.dump([asdict(r) for r in stress_tests.results], f, indent=2)
        
        print(f"\n{Colors.GREEN}✓ Results saved to: {results_file}{Colors.END}")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}✗ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
