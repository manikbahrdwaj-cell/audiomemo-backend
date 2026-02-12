# Phase 4.4: Performance/Load Testing - Quick Reference

## 🚀 Quick Start (2 minutes)

### 1. Start Server
```bash
cd reactapp/backend
python main.py
```

### 2. Run Tests
```bash
cd reactapp
python run_performance_tests_complete.py
```

### 3. View Report
```bash
# Open in browser
performance_report.html
```

---

## 📊 Test Suite Overview

| Test Type | File | Tests | Purpose | Duration |
|-----------|------|-------|---------|----------|
| Load Tests | `performance_load_test.py` | 5 | Endpoint scalability | ~5 min |
| Stress Tests | `stress_test_scenarios.py` | 6 | Real-world scenarios | ~10 min |
| Reports | `performance_report_generator.py` | 3 formats | Analysis & recommendations | ~1 min |

---

## 🎯 Key Metrics

### Response Times
```
Average:    < 1000ms  ✓
P95:        < 2000ms  ✓
P99:        < 5000ms  ✓
```

### Throughput
```
Minimum:    > 5 req/s
Ideal:      > 10 req/s
Peak:       > 50 req/s
```

### Resources
```
CPU:        < 80%
Memory:     < 85%
Leak:       < 50% over 500 req
```

---

## 📋 Individual Test Commands

### Load Tests Only
```bash
python performance_load_test.py
```
**Output**: `performance_test_results.json`
**Time**: ~5 minutes
**Tests**: 5 scenarios with increasing load

### Stress Tests Only
```bash
python stress_test_scenarios.py
```
**Output**: `stress_test_results.json`
**Time**: ~10 minutes
**Tests**: 6 real-world scenarios

### Generate Reports
```bash
python performance_report_generator.py
```
**Output**: 
- `performance_report.json` (machine-readable)
- `performance_report.html` (interactive)
- Console text report

### All Tests + Report
```bash
python run_performance_tests_complete.py
```
**Output**: All above files
**Time**: ~15-20 minutes

---

## 🔍 Performance Tests Explained

### Load Test 1: Enrollment Stress
```
Requests:     50
Concurrency:  5
Endpoint:     /enroll
Purpose:      Measure enrollment scalability
```

### Load Test 2: Verification Stress
```
Requests:     50
Concurrency:  5
Endpoint:     /verify
Purpose:      Measure verification performance
```

### Load Test 3: Mixed Workload
```
Requests:     100
Concurrency:  10
Mix:          70% verify, 30% enroll
Purpose:      Realistic traffic pattern
```

### Load Test 4: Ramp-Up Test
```
Concurrency:  1 → 15 users (ramping)
Per Level:    10 requests
Purpose:      Find breaking point
```

### Load Test 5: Sustained Load
```
Duration:     30 seconds
Concurrency:  5
Target RPS:   10 requests/second
Purpose:      Stability measurement
```

---

## 💥 Stress Tests Explained

### Scenario 1: Peak Hour
```
Workload:     200 req/minute spike
Description:  Handle sudden traffic surge
Pass Rate:    > 95% expected
```

### Scenario 2: Failure Recovery
```
Phase 1:      50 rapid requests
Phase 2:      5-sec recovery
Phase 3:      50 verification requests
Purpose:      Recovery capability
```

### Scenario 3: Memory Leaks
```
Requests:     500 (10 batches)
Duration:     ~2 minutes
Purpose:      Detect long-term leaks
Threshold:    < 50% degradation
```

### Scenario 4: Rapid Fire
```
Requests:     1000 sequential
Purpose:      Max throughput
Measure:      req/second sustained
```

### Scenario 5: Connection Pool
```
Connections:  50 concurrent
Per conn:     4 requests
Total:        200 requests
Purpose:      Connection handling
```

### Scenario 6: Burst Traffic
```
Pattern:      Burst-Wait-Burst-Wait-Burst
Bursts:       100 requests each
Wait:         10 seconds between
Purpose:      Pattern handling
```

---

## 📊 Understanding Results

### Success Indicators
- ✅ Status: PASS
- ✅ Error rate < 1%
- ✅ Avg response < 1000ms
- ✅ CPU < 80%
- ✅ Memory < 85%

### Warning Indicators
- ⚠️ Status: WARN
- ⚠️ Error rate 1-5%
- ⚠️ Avg response 1-2 seconds
- ⚠️ CPU 80-90%
- ⚠️ Memory 85-95%

### Failure Indicators
- ❌ Status: FAIL
- ❌ Error rate > 5%
- ❌ Avg response > 2 seconds
- ❌ CPU > 90%
- ❌ Memory > 95%

---

## 🔧 Customization Examples

### Increase Load
```python
# In performance_load_test.py

# More requests
runner.benchmark_enrollment_requests(
    num_requests=100,  # Changed from 50
    concurrent_users=5
)

# More concurrency
runner.benchmark_enrollment_requests(
    num_requests=50,
    concurrent_users=20  # Changed from 5
)
```

### Extend Duration
```python
# In performance_load_test.py

# Longer sustained test
runner.benchmark_sustained_load(
    concurrent_users=5,
    duration_seconds=60,  # Changed from 30
    requests_per_second=10
)
```

### Change Benchmarks
```python
# In performance_report_generator.py

self.benchmarks = PerformanceBenchmark(
    max_avg_response_time=0.5,    # Stricter (0.5s)
    max_error_rate=0.5,            # Stricter (0.5%)
    min_throughput=20.0,           # Higher target
)
```

---

## ⚡ Performance Tips

1. **Reduce Audio Size**
   - Use smaller test audio files
   - Decreases upload/processing time

2. **Increase Concurrency Gradually**
   - Start at 5 users
   - Move to 10, then 20
   - Identify breaking point

3. **Monitor Resources**
   - Check CPU with `psutil`
   - Watch memory in Task Manager
   - Identify resource bottlenecks

4. **Database Optimization**
   - Index frequently queried fields
   - Use connection pooling
   - Cache embeddings

5. **API Optimization**
   - Profile hot paths with cProfile
   - Cache voice embeddings
   - Implement request queuing

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Server not running | `cd backend && python main.py` |
| No test audio | `python generate_comprehensive_audio.py` |
| psutil error | `pip install psutil` |
| High timeouts | Reduce concurrent users |
| Memory spikes | Use smaller audio files |
| CPU maxed out | Profile code with cProfile |

---

## 📈 Report Files

### .json (Machine-readable)
```
{
  "summary": {...},
  "response_times": {...},
  "throughput": {...},
  "resources": {...},
  "bottlenecks": [...],
  "recommendations": [...]
}
```

### .html (Visual report)
- Interactive display
- Color-coded status
- Executive summary
- Bottleneck details
- Recommendations

### Console output
- Real-time progress
- Per-test metrics
- Issues flagged immediately

---

## 🎯 Next Steps

1. ✅ Run complete test suite
2. ✅ Review performance metrics
3. ✅ Identify bottlenecks
4. ✅ Implement optimizations
5. ✅ Re-test to verify improvements

---

## 📞 File Reference

```
performance_load_test.py              [~750 lines]
├─ LoadTestRunner class
├─ ResourceMonitor thread
└─ 5 benchmark tests

stress_test_scenarios.py              [~650 lines]
├─ StressTestScenarios class
└─ 6 stress scenarios

performance_report_generator.py       [~550 lines]
├─ Report generation
└─ Analysis tools

run_performance_tests_complete.py     [~250 lines]
└─ Master orchestrator
```

---

## ✅ Checklist

- [ ] Install dependencies: `pip install requests psutil numpy`
- [ ] Start backend server: `python backend/main.py`
- [ ] Generate test audio: `python generate_comprehensive_audio.py`
- [ ] Run tests: `python run_performance_tests_complete.py`
- [ ] Review HTML report: `performance_report.html`
- [ ] Address HIGH severity issues
- [ ] Re-test and verify improvements

---

**Phase 4.4 Status: ✅ COMPLETE & READY**
