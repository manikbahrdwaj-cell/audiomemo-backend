#!/usr/bin/env python3
"""
Phase 4.4: Performance Report Generator

Generates comprehensive performance analysis reports from test results:
- Executive summary
- Detailed metrics breakdown
- Performance trends
- Bottleneck analysis
- Recommendations
- HTML and JSON report generation
"""

import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'


@dataclass
class PerformanceBenchmark:
    """Performance benchmark thresholds"""
    max_avg_response_time: float = 1.0  # seconds
    max_p99_response_time: float = 5.0  # seconds
    max_error_rate: float = 1.0  # percent
    min_throughput: float = 5.0  # requests per second
    max_cpu_usage: float = 80.0  # percent
    max_memory_usage: float = 85.0  # percent


class PerformanceReportGenerator:
    """Generate performance reports from test results"""
    
    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path(__file__).parent
        self.benchmarks = PerformanceBenchmark()
        self.load_test_results = []
        self.stress_test_results = []

    def load_results(self) -> bool:
        """Load test results from JSON files"""
        load_file = self.results_dir / "performance_test_results.json"
        stress_file = self.results_dir / "stress_test_results.json"
        
        try:
            if load_file.exists():
                with open(load_file, 'r') as f:
                    self.load_test_results = json.load(f)
                print(f"{Colors.GREEN}✓ Loaded performance test results{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠ Performance test results not found{Colors.END}")
            
            if stress_file.exists():
                with open(stress_file, 'r') as f:
                    self.stress_test_results = json.load(f)
                print(f"{Colors.GREEN}✓ Loaded stress test results{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠ Stress test results not found{Colors.END}")
            
            return len(self.load_test_results) > 0 or len(self.stress_test_results) > 0
        
        except Exception as e:
            print(f"{Colors.RED}✗ Error loading results: {e}{Colors.END}")
            return False

    def generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary"""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "load_tests_count": len(self.load_test_results),
            "stress_tests_count": len(self.stress_test_results),
            "overall_status": "PASS",
            "issues": [],
        }
        
        # Analyze load tests
        if self.load_test_results:
            successful = sum(m.get("successful_requests", 0) for m in self.load_test_results)
            total = sum(m.get("total_requests", 0) for m in self.load_test_results)
            
            summary["load_test_success_rate"] = (successful / total * 100) if total > 0 else 0
            
            # Check for issues
            for metric in self.load_test_results:
                if metric.get("error_rate", 0) > self.benchmarks.max_error_rate:
                    summary["overall_status"] = "WARN"
                    summary["issues"].append(
                        f"High error rate in {metric.get('test_name', 'unknown')}: "
                        f"{metric.get('error_rate', 0):.2f}%"
                    )
                
                if metric.get("avg_response_time", 0) > self.benchmarks.max_avg_response_time:
                    summary["overall_status"] = "WARN"
                    summary["issues"].append(
                        f"High response time in {metric.get('test_name', 'unknown')}: "
                        f"{metric.get('avg_response_time', 0)*1000:.2f}ms"
                    )
        
        # Analyze stress tests
        if self.stress_test_results:
            stress_passed = sum(1 for r in self.stress_test_results if r.get("status") == "PASS")
            summary["stress_test_pass_rate"] = (stress_passed / len(self.stress_test_results) * 100)
            
            for result in self.stress_test_results:
                if result.get("status") in ["FAIL", "WARN"]:
                    summary["overall_status"] = "WARN"
                    summary["issues"].append(
                        f"{result.get('status')}: {result.get('scenario_name', 'unknown')} - "
                        f"{result.get('error_message', 'See details')}"
                    )
        
        return summary

    def analyze_response_times(self) -> Dict[str, Any]:
        """Analyze response time metrics"""
        analysis = {
            "all_avg_response_times": [],
            "all_p99_response_times": [],
            "overall_avg": 0.0,
            "overall_min": float('inf'),
            "overall_max": 0.0,
            "endpoints": {}
        }
        
        for metric in self.load_test_results:
            test_name = metric.get("test_name", "unknown")
            endpoint = test_name.split("_")[0] if "_" in test_name else test_name
            
            avg = metric.get("avg_response_time", 0)
            p99 = metric.get("p99_response_time", 0)
            
            analysis["all_avg_response_times"].append(avg)
            analysis["all_p99_response_times"].append(p99)
            
            if endpoint not in analysis["endpoints"]:
                analysis["endpoints"][endpoint] = {
                    "tests": [],
                    "avg_response_time": 0.0,
                    "max_response_time": 0.0,
                }
            
            analysis["endpoints"][endpoint]["tests"].append({
                "name": test_name,
                "avg_response_time": avg,
                "p99_response_time": p99,
                "concurrent_users": metric.get("concurrent_users", 0),
            })
            
            analysis["overall_min"] = min(analysis["overall_min"], metric.get("min_response_time", 0))
            analysis["overall_max"] = max(analysis["overall_max"], metric.get("max_response_time", 0))
        
        if analysis["all_avg_response_times"]:
            analysis["overall_avg"] = statistics.mean(analysis["all_avg_response_times"])
        
        return analysis

    def analyze_throughput(self) -> Dict[str, Any]:
        """Analyze throughput metrics"""
        analysis = {
            "throughputs": [],
            "average_throughput": 0.0,
            "max_throughput": 0.0,
            "by_concurrency": {}
        }
        
        for metric in self.load_test_results:
            throughput = metric.get("throughput_rps", 0)
            concurrent_users = metric.get("concurrent_users", 0)
            
            analysis["throughputs"].append(throughput)
            analysis["max_throughput"] = max(analysis["max_throughput"], throughput)
            
            if concurrent_users not in analysis["by_concurrency"]:
                analysis["by_concurrency"][concurrent_users] = []
            
            analysis["by_concurrency"][concurrent_users].append({
                "test_name": metric.get("test_name"),
                "throughput_rps": throughput,
            })
        
        if analysis["throughputs"]:
            analysis["average_throughput"] = statistics.mean(analysis["throughputs"])
        
        return analysis

    def analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze resource usage"""
        analysis = {
            "cpu_usage": [],
            "memory_usage": [],
            "avg_cpu": 0.0,
            "avg_memory": 0.0,
            "max_cpu": 0.0,
            "max_memory": 0.0,
            "issues": []
        }
        
        for metric in self.load_test_results:
            cpu = metric.get("cpu_usage", 0)
            mem = metric.get("memory_usage", 0)
            
            analysis["cpu_usage"].append(cpu)
            analysis["memory_usage"].append(mem)
            analysis["max_cpu"] = max(analysis["max_cpu"], cpu)
            analysis["max_memory"] = max(analysis["max_memory"], mem)
            
            if cpu > self.benchmarks.max_cpu_usage:
                analysis["issues"].append(f"High CPU usage: {cpu:.2f}% in {metric.get('test_name')}")
            
            if mem > self.benchmarks.max_memory_usage:
                analysis["issues"].append(f"High memory usage: {mem:.2f}% in {metric.get('test_name')}")
        
        if analysis["cpu_usage"]:
            analysis["avg_cpu"] = statistics.mean(analysis["cpu_usage"])
        
        if analysis["memory_usage"]:
            analysis["avg_memory"] = statistics.mean(analysis["memory_usage"])
        
        return analysis

    def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Check response times
        response_times = self.analyze_response_times()
        if response_times["overall_avg"] > self.benchmarks.max_avg_response_time:
            bottlenecks.append({
                "type": "High Response Time",
                "severity": "HIGH",
                "metric": response_times["overall_avg"] * 1000,
                "unit": "ms",
                "threshold": self.benchmarks.max_avg_response_time * 1000,
                "recommendation": "Optimize API endpoints or database queries"
            })
        
        # Check error rates
        for metric in self.load_test_results:
            if metric.get("error_rate", 0) > self.benchmarks.max_error_rate:
                bottlenecks.append({
                    "type": "High Error Rate",
                    "severity": "HIGH",
                    "metric": metric.get("error_rate"),
                    "unit": "%",
                    "threshold": self.benchmarks.max_error_rate,
                    "test": metric.get("test_name"),
                    "recommendation": "Check server logs for errors and implement retry logic"
                })
        
        # Check resource usage
        resources = self.analyze_resource_usage()
        if resources["max_cpu"] > self.benchmarks.max_cpu_usage:
            bottlenecks.append({
                "type": "High CPU Usage",
                "severity": "MEDIUM",
                "metric": resources["max_cpu"],
                "unit": "%",
                "threshold": self.benchmarks.max_cpu_usage,
                "recommendation": "Profile code and optimize hot paths"
            })
        
        # Check throughput
        throughput = self.analyze_throughput()
        if throughput["average_throughput"] < self.benchmarks.min_throughput:
            bottlenecks.append({
                "type": "Low Throughput",
                "severity": "MEDIUM",
                "metric": throughput["average_throughput"],
                "unit": "req/s",
                "threshold": self.benchmarks.min_throughput,
                "recommendation": "Implement caching or increase server resources"
            })
        
        return bottlenecks

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        bottlenecks = self.identify_bottlenecks()
        
        # Add bottleneck-based recommendations
        for bottleneck in bottlenecks:
            if bottleneck["severity"] == "HIGH":
                recommendations.append(f"URGENT: {bottleneck['recommendation']} - {bottleneck['type']}")
            else:
                recommendations.append(bottleneck['recommendation'])
        
        # Add general recommendations
        if self.load_test_results:
            total_tests = len(self.load_test_results)
            
            # Check for scalability
            response_times = self.analyze_response_times()
            if response_times["overall_avg"] < 0.5:
                recommendations.append("System shows good scalability; consider increasing target load")
            
            throughput = self.analyze_throughput()
            if throughput["average_throughput"] > 50:
                recommendations.append("Excellent throughput achieved; consider stress testing with more concurrent users")
        
        # Stress test recommendations
        for result in self.stress_test_results:
            if result.get("status") == "WARN":
                recommendations.append(
                    f"Address warning in {result.get('scenario_name')}: "
                    f"Current performance may need optimization"
                )
        
        return recommendations

    def print_text_report(self) -> None:
        """Print formatted text report"""
        print(f"\n{Colors.MAGENTA}{'='*80}")
        print("  Phase 4.4: Performance Test Report")
        print(f"{'='*80}{Colors.END}\n")
        
        # Executive Summary
        summary = self.generate_executive_summary()
        print(f"{Colors.BLUE}{'█'*80}")
        print(f"{'EXECUTIVE SUMMARY':<80}")
        print(f"{'█'*80}{Colors.END}")
        print(f"Generated: {summary['generated_at']}")
        print(f"Status: {Colors.GREEN if summary['overall_status'] == 'PASS' else Colors.YELLOW}"
              f"{summary['overall_status']}{Colors.END}")
        print(f"Load Tests: {summary['load_tests_count']}")
        print(f"Stress Tests: {summary['stress_tests_count']}")
        
        if summary.get('load_test_success_rate'):
            print(f"Load Test Success Rate: {summary['load_test_success_rate']:.2f}%")
        
        if summary.get('stress_test_pass_rate'):
            print(f"Stress Test Pass Rate: {summary['stress_test_pass_rate']:.2f}%")
        
        if summary['issues']:
            print(f"\n{Colors.YELLOW}Issues Found:{Colors.END}")
            for issue in summary['issues']:
                print(f"  ⚠ {issue}")
        
        # Response Time Analysis
        print(f"\n{Colors.BLUE}{'█'*80}")
        print(f"{'RESPONSE TIME ANALYSIS':<80}")
        print(f"{'█'*80}{Colors.END}")
        
        response_analysis = self.analyze_response_times()
        print(f"Overall Average: {response_analysis['overall_avg']*1000:.2f}ms")
        print(f"Overall Min: {response_analysis['overall_min']*1000:.2f}ms")
        print(f"Overall Max: {response_analysis['overall_max']*1000:.2f}ms")
        print(f"Benchmark (max): {self.benchmarks.max_avg_response_time*1000:.2f}ms")
        
        status = Colors.GREEN if response_analysis['overall_avg'] <= self.benchmarks.max_avg_response_time else Colors.RED
        print(f"Status: {status}{'✓ PASS' if response_analysis['overall_avg'] <= self.benchmarks.max_avg_response_time else '✗ FAIL'}{Colors.END}")
        
        # Throughput Analysis
        print(f"\n{Colors.BLUE}{'█'*80}")
        print(f"{'THROUGHPUT ANALYSIS':<80}")
        print(f"{'█'*80}{Colors.END}")
        
        throughput_analysis = self.analyze_throughput()
        print(f"Average Throughput: {throughput_analysis['average_throughput']:.2f} req/s")
        print(f"Max Throughput: {throughput_analysis['max_throughput']:.2f} req/s")
        print(f"Benchmark (min): {self.benchmarks.min_throughput:.2f} req/s")
        
        status = Colors.GREEN if throughput_analysis['average_throughput'] >= self.benchmarks.min_throughput else Colors.RED
        print(f"Status: {status}{'✓ PASS' if throughput_analysis['average_throughput'] >= self.benchmarks.min_throughput else '✗ FAIL'}{Colors.END}")
        
        # Resource Usage Analysis
        print(f"\n{Colors.BLUE}{'█'*80}")
        print(f"{'RESOURCE USAGE ANALYSIS':<80}")
        print(f"{'█'*80}{Colors.END}")
        
        resources = self.analyze_resource_usage()
        print(f"Average CPU Usage: {resources['avg_cpu']:.2f}%")
        print(f"Max CPU Usage: {resources['max_cpu']:.2f}%")
        print(f"Benchmark (max): {self.benchmarks.max_cpu_usage:.2f}%")
        
        print(f"\nAverage Memory Usage: {resources['avg_memory']:.2f}%")
        print(f"Max Memory Usage: {resources['max_memory']:.2f}%")
        print(f"Benchmark (max): {self.benchmarks.max_memory_usage:.2f}%")
        
        if resources['issues']:
            print(f"\n{Colors.YELLOW}Resource Issues:{Colors.END}")
            for issue in resources['issues']:
                print(f"  ⚠ {issue}")
        
        # Bottleneck Analysis
        print(f"\n{Colors.BLUE}{'█'*80}")
        print(f"{'BOTTLENECK ANALYSIS':<80}")
        print(f"{'█'*80}{Colors.END}")
        
        bottlenecks = self.identify_bottlenecks()
        if bottlenecks:
            for bottleneck in bottlenecks:
                severity_color = Colors.RED if bottleneck['severity'] == 'HIGH' else Colors.YELLOW
                print(f"{severity_color}[{bottleneck['severity']}]{Colors.END} {bottleneck['type']}")
                print(f"  Metric: {bottleneck['metric']:.2f} {bottleneck['unit']}")
                print(f"  Threshold: {bottleneck['threshold']:.2f} {bottleneck['unit']}")
                print(f"  Recommendation: {bottleneck['recommendation']}\n")
        else:
            print(f"{Colors.GREEN}No significant bottlenecks detected✓{Colors.END}")
        
        # Stress Test Results
        if self.stress_test_results:
            print(f"\n{Colors.BLUE}{'█'*80}")
            print(f"{'STRESS TEST RESULTS':<80}")
            print(f"{'█'*80}{Colors.END}")
            
            for result in self.stress_test_results:
                status_color = Colors.GREEN if result['status'] == 'PASS' else Colors.YELLOW if result['status'] == 'WARN' else Colors.RED
                print(f"{status_color}[{result['status']}]{Colors.END} {result.get('scenario_name', 'Unknown')}")
                print(f"  Total Requests: {result.get('total_requests', 0)}")
                print(f"  Success Rate: {(result.get('successful_requests', 0) / result.get('total_requests', 1) * 100):.2f}%")
                print(f"  Avg Response: {result.get('avg_response_time', 0)*1000:.2f}ms\n")
        
        # Recommendations
        print(f"{Colors.BLUE}{'█'*80}")
        print(f"{'RECOMMENDATIONS':<80}")
        print(f"{'█'*80}{Colors.END}")
        
        recommendations = self.generate_recommendations()
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print(f"{Colors.GREEN}No critical recommendations - system performing well✓{Colors.END}")
        
        print(f"\n{Colors.MAGENTA}{'='*80}{Colors.END}\n")

    def generate_json_report(self, output_file: Path = None) -> None:
        """Generate JSON report"""
        if not output_file:
            output_file = self.results_dir / "performance_report.json"
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.generate_executive_summary(),
            "response_times": self.analyze_response_times(),
            "throughput": self.analyze_throughput(),
            "resources": self.analyze_resource_usage(),
            "bottlenecks": self.identify_bottlenecks(),
            "recommendations": self.generate_recommendations(),
            "benchmarks": {
                "max_avg_response_time": self.benchmarks.max_avg_response_time,
                "max_p99_response_time": self.benchmarks.max_p99_response_time,
                "max_error_rate": self.benchmarks.max_error_rate,
                "min_throughput": self.benchmarks.min_throughput,
                "max_cpu_usage": self.benchmarks.max_cpu_usage,
                "max_memory_usage": self.benchmarks.max_memory_usage,
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"{Colors.GREEN}✓ JSON report saved to: {output_file}{Colors.END}")

    def generate_html_report(self, output_file: Path = None) -> None:
        """Generate HTML report"""
        if not output_file:
            output_file = self.results_dir / "performance_report.html"
        
        summary = self.generate_executive_summary()
        response_analysis = self.analyze_response_times()
        throughput_analysis = self.analyze_throughput()
        resources = self.analyze_resource_usage()
        bottlenecks = self.identify_bottlenecks()
        recommendations = self.generate_recommendations()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report - Phase 4.4</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #0066cc;
            margin-top: 30px;
        }}
        .summary-card {{
            background-color: #f9f9f9;
            border-left: 4px solid #0066cc;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .metric {{
            display: inline-block;
            width: 48%;
            margin-right: 2%;
            padding: 15px;
            background-color: #f0f0f0;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        .metric-label {{
            font-weight: bold;
            color: #333;
        }}
        .metric-value {{
            font-size: 24px;
            color: #0066cc;
            margin-top: 5px;
        }}
        .status-pass {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-warn {{
            color: #ffc107;
            font-weight: bold;
        }}
        .status-fail {{
            color: #dc3545;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #0066cc;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .issue {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin-bottom: 10px;
        }}
        .bottleneck {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 10px;
            margin-bottom: 10px;
        }}
        .recommendation {{
            background-color: #d1ecf1;
            border-left: 4px solid #0c5460;
            padding: 10px;
            margin-bottom: 10px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Phase 4.4: Performance/Load Testing Report</h1>
        
        <div class="summary-card">
            <strong>Generated:</strong> {summary['generated_at']}<br>
            <strong>Status:</strong> <span class="status-{'pass' if summary['overall_status'] == 'PASS' else 'warn' if summary['overall_status'] == 'WARN' else 'fail'}">{summary['overall_status']}</span><br>
            <strong>Load Tests:</strong> {summary['load_tests_count']}<br>
            <strong>Stress Tests:</strong> {summary['stress_tests_count']}
        </div>
        
        <h2>Key Metrics</h2>
        <div class="metric">
            <div class="metric-label">Average Response Time</div>
            <div class="metric-value">{response_analysis['overall_avg']*1000:.2f}ms</div>
        </div>
        <div class="metric">
            <div class="metric-label">Average Throughput</div>
            <div class="metric-value">{throughput_analysis['average_throughput']:.2f} req/s</div>
        </div>
        <div class="metric">
            <div class="metric-label">Avg CPU Usage</div>
            <div class="metric-value">{resources['avg_cpu']:.2f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Avg Memory Usage</div>
            <div class="metric-value">{resources['avg_memory']:.2f}%</div>
        </div>
        
        <h2>Issues</h2>
        {"".join(f'<div class="issue">{issue}</div>' for issue in summary['issues']) if summary['issues'] else '<p class="status-pass">✓ No issues detected</p>'}
        
        <h2>Bottlenecks</h2>
        {"".join(f'<div class="bottleneck"><strong>{b["type"]}</strong> [{b["severity"]}]<br>Metric: {b["metric"]:.2f} {b["unit"]} (max: {b["threshold"]:.2f})<br>Recommendation: {b["recommendation"]}</div>' for b in bottlenecks) if bottlenecks else '<p class="status-pass">✓ No bottlenecks detected</p>'}
        
        <h2>Recommendations</h2>
        {"".join(f'<div class="recommendation">{i}. {rec}</div>' for i, rec in enumerate(recommendations, 1)) if recommendations else '<p class="status-pass">✓ No recommendations needed</p>'}
        
        <div class="footer">
            <p>This report was auto-generated by the Performance/Load Testing Suite (Phase 4.4)</p>
        </div>
    </div>
</body>
</html>"""
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        print(f"{Colors.GREEN}✓ HTML report saved to: {output_file}{Colors.END}")


def main():
    """Main report generator"""
    print(f"\n{Colors.MAGENTA}{'='*80}")
    print("  Phase 4.4: Performance Report Generator")
    print(f"{'='*80}{Colors.END}\n")
    
    generator = PerformanceReportGenerator()
    
    if not generator.load_results():
        print(f"\n{Colors.YELLOW}No test results found. Please run performance tests first.{Colors.END}")
        return
    
    # Generate reports
    generator.print_text_report()
    generator.generate_json_report()
    generator.generate_html_report()
    
    print(f"{Colors.GREEN}✓ Report generation complete{Colors.END}\n")


if __name__ == "__main__":
    main()
