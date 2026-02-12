# Phase 4.3: E2E Testing Quick Reference

**Quick commands and checklist for end-to-end testing**

---

## 🚀 5-Minute Quick Start

```bash
# 1. Generate test audio (one-time setup)
python generate_comprehensive_audio.py

# 2. Start backend in separate terminal
cd backend && python run.py

# 3. Run workflow tests
python test_e2e_workflows.py

# 4. Run scenario tests
python test_e2e_scenarios.py

# 5. Review results
cat e2e_test_results.json
cat e2e_stress_test_results.json
```

**Expected Time:** ~4-5 minutes total

---

## ✅ Pre-Test Checklist

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Backend dependencies installed (`pip list | grep fastapi`)
- [ ] MongoDB running (`netstat -ano | findstr 27017`)
- [ ] Test audio generated (`ls test_audio_files/` shows files)
- [ ] No other process on port 8000 (`netstat -ano | findstr :8000`)

---

## 📋 Test Commands Quick Reference

```bash
# Generate test audio (required once)
python generate_comprehensive_audio.py

# Start backend (in new terminal)
cd backend && python run.py

# Run all E2E tests
python test_e2e_workflows.py
python test_e2e_scenarios.py

# View results
cat e2e_test_results.json
cat e2e_stress_test_results.json

# Check test status (while running)
curl http://localhost:8000/

# Stop backend
# Ctrl+C in backend terminal
```

---

## 🎯 Test Scenarios Quick Overview

| Scenario | File | Duration | Focus |
|----------|------|----------|-------|
| Workflows | test_e2e_workflows.py | ~90s | Core functionality |
| High Load | test_e2e_scenarios.py | ~150s | Stress testing |

---

## ⚡ Common Commands

```bash
# One-liner to run everything (Linux/macOS)
python generate_comprehensive_audio.py && \
cd backend && python run.py & \
sleep 5 && cd .. && \
python test_e2e_workflows.py && \
python test_e2e_scenarios.py

# Batch file for Windows (save as run_tests.bat)
@echo off
python generate_comprehensive_audio.py
cd backend
start python run.py
cd ..
timeout /t 5
python test_e2e_workflows.py
python test_e2e_scenarios.py
pause
```

---

## 🔍 Troubleshooting Quick Tips

| Issue | Quick Fix |
|-------|-----------|
| API not running | `cd backend && python run.py` |
| No test audio | `python generate_comprehensive_audio.py` |
| MongoDB error | Start MongoDB locally or in Docker |
| Port 8000 busy | `netstat -ano | findstr :8000` then kill process |
| Test timeout | Increase timeout value in test file |

---

## 📊 Result Interpretation

**PASS:** ✅ Test succeeded, all checks passed  
**FAIL:** ❌ Test failed, assertion not met  
**SKIP:** ⊘ Test skipped, missing dependencies  

**Pass Rate Meaning:**
- 100% = Perfect, ready for production
- 95%+ = Good, minor issues only
- 90%+ = Acceptable, needs investigation
- <90% = Needs fixing before deployment

---

## 📁 Files Created

```
reactapp/
├── test_e2e_workflows.py           ← Main E2E tests
├── test_e2e_scenarios.py           ← Stress tests
├── PHASE_4_3_COMPLETION_REPORT.md  ← Full documentation
├── PHASE_4_3_E2E_TESTING_GUIDE.md  ← User guide
├── PHASE_4_3_QUICK_REFERENCE.md    ← This file
├── e2e_test_results.json           ← Generated results
└── e2e_stress_test_results.json    ← Generated stress results
```

---

## 🔧 Configuration

**Default Timeouts:**
```python
ENROLLMENT_TIMEOUT = 30  # seconds
VERIFICATION_TIMEOUT = 30  # seconds
API_TIMEOUT = 5  # seconds
```

**Default Test Users:**
```
user_001: 9876543210 (Alice)
user_002: 8765432109 (Bob)
user_003: 7654321098 (Charlie)
```

**Default API Endpoint:**
```
http://localhost:8000
```

---

## 📈 Performance Targets

**Expected Response Times:**
```
Enrollment:    1-5 seconds
Verification:  1-3 seconds
Status Check:  <1 second
```

**Expected Pass Rates:**
```
Workflow Tests:    100%
Scenario Tests:    95%+
Overall:           >95%
```

---

## 🚨 Alert Conditions

Stop testing and investigate if:
- [ ] Pass rate < 90%
- [ ] Response time > 10s
- [ ] Memory usage > 80%
- [ ] Multiple concurrent failures
- [ ] Cross-user verification matches

---

## 💡 Tips & Tricks

```bash
# Monitor backend while tests run
tail -f backend/logs/app.log

# Run with verbose output
python -u test_e2e_workflows.py

# Profile test execution
python -m cProfile -s cumulative test_e2e_workflows.py

# Run only specific test
# (Edit test file and comment out other tests)

# Save detailed report
python test_e2e_workflows.py > test_run_$(date +%Y%m%d_%H%M%S).log
```

---

## 📚 Related Documentation

- **Phase 4.3 Completion Report:** PHASE_4_3_COMPLETION_REPORT.md
- **Full Testing Guide:** PHASE_4_3_E2E_TESTING_GUIDE.md
- **Architecture:** APP_ARCHITECTURE.md
- **Testing Overview:** TESTING_GUIDE.md

---

## 🎓 Understanding Test Output

### Success Example
```
╔─ Test 2: Single User Complete Workflow
  ✓ User enrollment                                  [PASS] Phone: 9876543210
  ...
╔─ E2E TEST SUMMARY
  Total Tests:  9
  Passed:    9
  Failed:    0
  Skipped:   0
  Pass Rate:   100.0%
```

### Failure Example
```
╔─ Test 3: Multi-User Isolation
  ✗ Cross-user rejection                           [FAIL] Score: 0.88 (should not match)

✗ Cross-user rejection: Score 0.88 (should not match)
```

**What to do:** Increase threshold in backend/main.py (line 170)

---

## 🔐 Security Checks

These tests verify:
- ✅ Cross-user verification fails
- ✅ Unenrolled users cannot verify
- ✅ Invalid inputs handled safely
- ✅ Data isolation maintained
- ✅ Concurrent access is thread-safe

---

## 📈 CI/CD Integration

**GitHub Actions:**
```yaml
- name: Run E2E Tests
  run: |
    python test_e2e_workflows.py
    python test_e2e_scenarios.py
```

**GitLab CI:**
```yaml
e2e-tests:
  script:
    - python test_e2e_workflows.py
    - python test_e2e_scenarios.py
```

---

## ⏱️ Expected Execution Times

```
Setup:                    ~1 minute
Workflow Tests:           ~90 seconds
Scenario Tests:           ~150 seconds
Results Processing:       ~10 seconds
─────────────────────────────────────
Total:                    ~4 minutes
```

---

## ✨ Success Criteria Checklist

After running tests, verify:

- [ ] e2e_test_results.json exists
- [ ] e2e_stress_test_results.json exists
- [ ] Workflow tests: 100% pass (9/9)
- [ ] Scenario tests: 95%+ pass
- [ ] No security violations reported
- [ ] Response times acceptable
- [ ] Data consistency verified
- [ ] No errors in logs

✅ **If all checked:** Ready for next phase!

---

## 🎯 Next Steps

1. Review test results
2. Check e2e_test_results.json for details
3. Investigate any failures
4. Optimize as needed
5. Proceed to Phase 4.4 (Advanced Integration Tests)

---

**Last Updated:** February 12, 2026  
**Version:** 1.0
