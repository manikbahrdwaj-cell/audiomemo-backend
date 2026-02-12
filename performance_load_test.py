#!/usr/bin/env python3
"""
Phase 4.4: Performance/Load Testing Suite

Comprehensive performance and load testing for voice biometric API:
- Concurrent user simulations
- Endpoint stress testing
- Resource utilization monitoring
- Throughput benchmarking
- Response time analysis
- Database connection pool testing
- WebSocket scalability testing
"""

import concurrent.futures
import time
import requests
import json
import os
import sys
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import threading
import psutil
import numpy as np
from dataclasses import dataclass, asdict, field

# Add backend to path
BACKEND_DIR = Path(__file__).parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'


@dataclass
class PerformanceMetrics:
    """Performance metrics data class"""
    test_name: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    response_times: List[float] = field(default_factory=list)
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    median_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    throughput_rps: float = 0.0  # Requests per second
    error_rate: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    total_duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def calculate_statistics(self) -> None:
        """Calculate response time statistics"""
        if self.response_times:
            self.min_response_time = min(self.response_times)
            self.max_response_time = max(self.response_times)
            self.avg_response_time = statistics.mean(self.response_times)
            self.median_response_time = statistics.median(self.response_times)
            
            sorted_times = sorted(self.response_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            self.p95_response_time = sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0
            self.p99_response_time = sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0
        
        if self.total_requests > 0:
            self.error_rate = (self.failed_requests / self.total_requests) * 100
        
        if self.total_duration > 0:
            self.throughput_rps = self.total_requests / self.total_duration


class ResourceMonitor:
    """Monitor system resources during load tests"""
    
    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.samples: List[Dict[str, float]] = []
        self.monitoring = False
        self.thread = None

    def start(self) -> None:
        """Start monitoring in background"""
        self.monitoring = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop monitoring"""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=2)

    def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self.monitoring:
            try:
                sample = {
                    'timestamp': time.time(),
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'memory_mb': psutil.virtual_memory().used / (1024 * 1024),
                }
                self.samples.append(sample)
                time.sleep(self.sample_interval)
            except Exception as e:
                print(f"Monitor error: {e}")

    def get_avg_cpu(self) -> float:
        """Get average CPU usage"""
        if not self.samples:
            return 0.0
        cpu_values = [s['cpu_percent'] for s in self.samples]
        return statistics.mean(cpu_values) if cpu_values else 0.0

    def get_avg_memory(self) -> float:
        """Get average memory usage"""
        if not self.samples:
            return 0.0
        mem_values = [s['memory_percent'] for s in self.samples]
        return statistics.mean(mem_values) if mem_values else 0.0

    def get_peak_memory_mb(self) -> float:
        """Get peak memory usage in MB"""
        if not self.samples:
            return 0.0
        mem_mb_values = [s['memory_mb'] for s in self.samples]
        return max(mem_mb_values) if mem_mb_values else 0.0


class LoadTestRunner:
    """Main load testing runner"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.monitor = ResourceMonitor()
        self.test_audio_file = self._get_test_audio()

    def _get_test_audio(self) -> bytes:
        """Get test audio file"""
        audio_dir = Path(__file__).parent / "test_audio_files"
        test_files = list(audio_dir.glob("*.wav"))
        
        if not test_files:
            raise FileNotFoundError(f"No test audio files in {audio_dir}")
        
        with open(test_files[0], 'rb') as f:
            return f.read()

    def _single_enrollment(self, user_id: int) -> Tuple[bool, float]:
        """Single enrollment request"""
        start_time = time.time()
        try:
            files = {'file': ('test.wav', self.test_audio_file, 'audio/wav')}
            data = {'phone_number': f'1234567890{user_id % 1000:03d}'}
            
            response = self.session.post(
                f"{self.base_url}/enroll",
                files=files,
                data=data,
                timeout=30
            )
            
            duration = time.time() - start_time
            success = response.status_code == 200
            return success, duration
        except Exception as e:
            duration = time.time() - start_time
            return False, duration

    def _single_verification(self, user_id: int) -> Tuple[bool, float]:
        """Single verification request"""
        start_time = time.time()
        try:
            files = {'file': ('test.wav', self.test_audio_file, 'audio/wav')}
            data = {'phone_number': f'1234567890{user_id % 1000:03d}'}
            
            response = self.session.post(
                f"{self.base_url}/verify",
                files=files,
                data=data,
                timeout=30
            )
            
            duration = time.time() - start_time
            success = response.status_code == 200
            return success, duration
        except Exception as e:
            duration = time.time() - start_time
            return False, duration

    def benchmark_enrollment_requests(
        self,
        num_requests: int = 50,
        concurrent_users: int = 5
    ) -> PerformanceMetrics:
        """Benchmark enrollment endpoint"""
        print(f"\n{Colors.CYAN}=== Enrollment Endpoint Stress Test ==={Colors.END}")
        print(f"Total requests: {num_requests}, Concurrent users: {concurrent_users}")
        
        metrics = PerformanceMetrics(
            test_name="enrollment_stress_test",
            concurrent_users=concurrent_users,
            total_requests=num_requests
        )
        
        self.monitor.start()
        start_time = time.time()
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [
                    executor.submit(self._single_enrollment, i)
                    for i in range(num_requests)
                ]
                
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        success, duration = future.result()
                        metrics.response_times.append(duration)
                        if success:
                            metrics.successful_requests += 1
                        else:
                            metrics.failed_requests += 1
                        
                        if (i + 1) % 10 == 0:
                            print(f"  Progress: {i + 1}/{num_requests} requests completed")
                    except Exception as e:
                        metrics.failed_requests += 1
                        print(f"  {Colors.RED}Request failed: {e}{Colors.END}")
        finally:
            metrics.total_duration = time.time() - start_time
            self.monitor.stop()
        
        metrics.cpu_usage = self.monitor.get_avg_cpu()
        metrics.memory_usage = self.monitor.get_avg_memory()
        metrics.calculate_statistics()
        
        self._print_metrics(metrics)
        return metrics

    def benchmark_verification_requests(
        self,
        num_requests: int = 50,
        concurrent_users: int = 5
    ) -> PerformanceMetrics:
        """Benchmark verification endpoint"""
        print(f"\n{Colors.CYAN}=== Verification Endpoint Stress Test ==={Colors.END}")
        print(f"Total requests: {num_requests}, Concurrent users: {concurrent_users}")
        
        metrics = PerformanceMetrics(
            test_name="verification_stress_test",
            concurrent_users=concurrent_users,
            total_requests=num_requests
        )
        
        self.monitor.start()
        start_time = time.time()
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [
                    executor.submit(self._single_verification, i)
                    for i in range(num_requests)
                ]
                
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        success, duration = future.result()
                        metrics.response_times.append(duration)
                        if success:
                            metrics.successful_requests += 1
                        else:
                            metrics.failed_requests += 1
                        
                        if (i + 1) % 10 == 0:
                            print(f"  Progress: {i + 1}/{num_requests} requests completed")
                    except Exception as e:
                        metrics.failed_requests += 1
                        print(f"  {Colors.RED}Request failed: {e}{Colors.END}")
        finally:
            metrics.total_duration = time.time() - start_time
            self.monitor.stop()
        
        metrics.cpu_usage = self.monitor.get_avg_cpu()
        metrics.memory_usage = self.monitor.get_avg_memory()
        metrics.calculate_statistics()
        
        self._print_metrics(metrics)
        return metrics

    def benchmark_mixed_workload(
        self,
        num_requests: int = 100,
        concurrent_users: int = 10,
        enroll_ratio: float = 0.3
    ) -> PerformanceMetrics:
        """Benchmark mixed enrollment/verification workload"""
        print(f"\n{Colors.CYAN}=== Mixed Workload Stress Test ==={Colors.END}")
        print(f"Total requests: {num_requests}, Concurrent users: {concurrent_users}")
        print(f"Enrollment ratio: {enroll_ratio*100:.1f}%, Verification ratio: {(1-enroll_ratio)*100:.1f}%")
        
        metrics = PerformanceMetrics(
            test_name="mixed_workload_stress_test",
            concurrent_users=concurrent_users,
            total_requests=num_requests
        )
        
        self.monitor.start()
        start_time = time.time()
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                for i in range(num_requests):
                    if i % 10 < (enroll_ratio * 10):
                        futures.append(executor.submit(self._single_enrollment, i))
                    else:
                        futures.append(executor.submit(self._single_verification, i))
                
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        success, duration = future.result()
                        metrics.response_times.append(duration)
                        if success:
                            metrics.successful_requests += 1
                        else:
                            metrics.failed_requests += 1
                        
                        if (i + 1) % 20 == 0:
                            print(f"  Progress: {i + 1}/{num_requests} requests completed")
                    except Exception as e:
                        metrics.failed_requests += 1
        finally:
            metrics.total_duration = time.time() - start_time
            self.monitor.stop()
        
        metrics.cpu_usage = self.monitor.get_avg_cpu()
        metrics.memory_usage = self.monitor.get_avg_memory()
        metrics.calculate_statistics()
        
        self._print_metrics(metrics)
        return metrics

    def benchmark_concurrent_ramp_up(
        self,
        max_concurrent_users: int = 20,
        requests_per_level: int = 10
    ) -> List[PerformanceMetrics]:
        """Ramp up test - gradually increase concurrent users"""
        print(f"\n{Colors.CYAN}=== Concurrent Ramp-Up Test ==={Colors.END}")
        print(f"Starting at 1 user, ramping to {max_concurrent_users} users")
        
        all_metrics = []
        
        for concurrent_users in range(1, max_concurrent_users + 1, 2):
            print(f"\n  Level: {concurrent_users} concurrent users")
            metrics = PerformanceMetrics(
                test_name=f"ramp_up_level_{concurrent_users}",
                concurrent_users=concurrent_users,
                total_requests=requests_per_level
            )
            
            self.monitor.start()
            start_time = time.time()
            
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                    futures = [
                        executor.submit(self._single_verification, i)
                        for i in range(requests_per_level)
                    ]
                    
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            success, duration = future.result()
                            metrics.response_times.append(duration)
                            if success:
                                metrics.successful_requests += 1
                            else:
                                metrics.failed_requests += 1
                        except Exception as e:
                            metrics.failed_requests += 1
            finally:
                metrics.total_duration = time.time() - start_time
                self.monitor.stop()
            
            metrics.cpu_usage = self.monitor.get_avg_cpu()
            metrics.memory_usage = self.monitor.get_avg_memory()
            metrics.calculate_statistics()
            all_metrics.append(metrics)
            
            print(f"    Avg response: {metrics.avg_response_time*1000:.2f}ms, "
                  f"Success: {metrics.successful_requests}/{metrics.total_requests}")

        return all_metrics

    def benchmark_sustained_load(
        self,
        concurrent_users: int = 5,
        duration_seconds: int = 30,
        requests_per_second: float = 10.0
    ) -> PerformanceMetrics:
        """Sustained load test for specified duration"""
        print(f"\n{Colors.CYAN}=== Sustained Load Test ==={Colors.END}")
        print(f"Concurrent users: {concurrent_users}, Duration: {duration_seconds}s, "
              f"Target RPS: {requests_per_second}")
        
        metrics = PerformanceMetrics(
            test_name="sustained_load_test",
            concurrent_users=concurrent_users,
            total_requests=0
        )
        
        self.monitor.start()
        start_time = time.time()
        request_count = 0
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                next_request_time = start_time
                
                while time.time() - start_time < duration_seconds:
                    now = time.time()
                    
                    # Submit new requests if scheduled
                    while next_request_time <= now:
                        if request_count % 2 == 0:
                            future = executor.submit(self._single_enrollment, request_count)
                        else:
                            future = executor.submit(self._single_verification, request_count)
                        futures.append(future)
                        request_count += 1
                        next_request_time += 1.0 / requests_per_second
                    
                    # Check completed futures
                    completed_futures = []
                    for future in futures:
                        if future.done():
                            try:
                                success, duration = future.result()
                                metrics.response_times.append(duration)
                                if success:
                                    metrics.successful_requests += 1
                                else:
                                    metrics.failed_requests += 1
                            except Exception:
                                metrics.failed_requests += 1
                            completed_futures.append(future)
                    
                    for future in completed_futures:
                        futures.remove(future)
                    
                    time.sleep(0.1)
                
                # Wait for remaining futures
                for future in concurrent.futures.as_completed(futures, timeout=10):
                    try:
                        success, duration = future.result()
                        metrics.response_times.append(duration)
                        if success:
                            metrics.successful_requests += 1
                        else:
                            metrics.failed_requests += 1
                    except Exception:
                        metrics.failed_requests += 1
        finally:
            metrics.total_duration = time.time() - start_time
            metrics.total_requests = request_count
            self.monitor.stop()
        
        metrics.cpu_usage = self.monitor.get_avg_cpu()
        metrics.memory_usage = self.monitor.get_avg_memory()
        metrics.calculate_statistics()
        
        self._print_metrics(metrics)
        return metrics

    def _print_metrics(self, metrics: PerformanceMetrics) -> None:
        """Print formatted metrics"""
        print(f"\n{Colors.GREEN}Test Results:{Colors.END}")
        print(f"  Total requests:        {metrics.total_requests}")
        print(f"  Successful:            {metrics.successful_requests}")
        print(f"  Failed:                {metrics.failed_requests}")
        print(f"  Error rate:            {metrics.error_rate:.2f}%")
        print(f"  Duration:              {metrics.total_duration:.2f}s")
        print(f"  Throughput (RPS):      {metrics.throughput_rps:.2f}")
        print(f"\n{Colors.GREEN}Response Times:{Colors.END}")
        print(f"  Min:                   {metrics.min_response_time*1000:.2f}ms")
        print(f"  Max:                   {metrics.max_response_time*1000:.2f}ms")
        print(f"  Average:               {metrics.avg_response_time*1000:.2f}ms")
        print(f"  Median:                {metrics.median_response_time*1000:.2f}ms")
        print(f"  P95:                   {metrics.p95_response_time*1000:.2f}ms")
        print(f"  P99:                   {metrics.p99_response_time*1000:.2f}ms")
        print(f"\n{Colors.GREEN}Resource Usage:{Colors.END}")
        print(f"  Avg CPU:               {metrics.cpu_usage:.2f}%")
        print(f"  Avg Memory:            {metrics.memory_usage:.2f}%")
        print(f"  Peak Memory:           {self.monitor.get_peak_memory_mb():.2f}MB")


def main():
    """Main test runner"""
    print(f"\n{Colors.MAGENTA}{'='*80}")
    print("  Phase 4.4: Performance/Load Testing Suite")
    print(f"{'='*80}{Colors.END}\n")
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/docs", timeout=2)
        print(f"{Colors.GREEN}✓ Server is running{Colors.END}")
    except:
        print(f"{Colors.RED}✗ Server is not running. Start the backend server first.{Colors.END}")
        sys.exit(1)
    
    runner = LoadTestRunner()
    all_metrics = []
    
    try:
        # Test 1: Enrollment stress test
        metrics1 = runner.benchmark_enrollment_requests(
            num_requests=50,
            concurrent_users=5
        )
        all_metrics.append(metrics1)
        time.sleep(2)
        
        # Test 2: Verification stress test
        metrics2 = runner.benchmark_verification_requests(
            num_requests=50,
            concurrent_users=5
        )
        all_metrics.append(metrics2)
        time.sleep(2)
        
        # Test 3: Mixed workload
        metrics3 = runner.benchmark_mixed_workload(
            num_requests=100,
            concurrent_users=10,
            enroll_ratio=0.3
        )
        all_metrics.append(metrics3)
        time.sleep(2)
        
        # Test 4: Ramp up test
        ramp_metrics = runner.benchmark_concurrent_ramp_up(
            max_concurrent_users=15,
            requests_per_level=10
        )
        all_metrics.extend(ramp_metrics)
        time.sleep(2)
        
        # Test 5: Sustained load test
        metrics5 = runner.benchmark_sustained_load(
            concurrent_users=5,
            duration_seconds=30,
            requests_per_second=10.0
        )
        all_metrics.append(metrics5)
        
        # Save results
        results_file = Path(__file__).parent / "performance_test_results.json"
        with open(results_file, 'w') as f:
            json.dump([asdict(m) for m in all_metrics], f, indent=2)
        
        print(f"\n{Colors.GREEN}✓ Results saved to: {results_file}{Colors.END}")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}✗ Test failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
