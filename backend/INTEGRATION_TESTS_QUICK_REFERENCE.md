"""
Integration Tests - Quick Reference Guide
==========================================

Fast lookup for common testing tasks
"""

# INTEGRATION TESTS QUICK REFERENCE

## 🚀 QUICK START (3 Steps)

### Step 1: Install
```bash
cd backend
pip install pytest pytest-cov pytest-html pytest-asyncio
```

### Step 2: Run Tests
```bash
# All integration tests
pytest test_integration_flows.py -v

# Quick tests only
pytest test_integration_flows.py -m "not slow" -v
```

### Step 3: View Results
```bash
# Check output
# Should see: "27 passed" or similar

# Generate report
pytest test_integration_flows.py --html=report.html
```

---

## 📋 TEST SUITES AT A GLANCE

| Suite | Tests | Purpose | Command |
|-------|-------|---------|---------|
| **Enrollment** | 5 | User enrollment flow | `pytest -m enrollment` |
| **Verification** | 4 | User verification flow | `pytest -m verification` |
| **Audio Pipeline** | 3 | Audio processing | `pytest -m audio_pipeline` |
| **Embedding** | 3 | Embedding generation & matching | `pytest -m embedding` |
| **Multi-Speaker** | 3 | Multiple speaker scenarios | `pytest -m multi_speaker` |
| **Error Handling** | 4 | Error recovery | `pytest -m error_handling` |
| **API Flow** | 3 | API endpoints | `pytest -m api_integration` |
| **Performance** | 2 | Load & stress | `pytest -m performance` |

---

## ⚡ COMMON COMMANDS

### Run All Integration Tests
```bash
pytest test_integration_flows.py -v
```
**Estimated time**: ~15 seconds

### Run Fast Tests Only
```bash
pytest test_integration_flows.py -m "not slow" -v
```
**Estimated time**: ~10 seconds

### Run Enrollment Tests
```bash
pytest test_integration_flows.py::TestEnrollmentFlowIntegration -v
```

### Run With Coverage Report
```bash
pytest test_integration_flows.py --cov --cov-report=html
```

### Run Single Test
```bash
pytest test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow -v
```

### Run With Detailed Output
```bash
pytest test_integration_flows.py -vv -s
```

### Run And Stop On First Failure
```bash
pytest test_integration_flows.py -x -v
```

### Run Parallel (Faster)
```bash
pytest test_integration_flows.py -n auto
```

---

## 🎯 TEST BY CATEGORY

### Enroll Someone
**File**: `TestEnrollmentFlowIntegration`

```bash
pytest test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow -v
```

**What it tests**: 
- ✅ Session created
- ✅ Chunks added
- ✅ Embeddings generated
- ✅ Data stored

### Verify Someone
**File**: `TestVerificationFlowIntegration`

```bash
pytest test_integration_flows.py::TestVerificationFlowIntegration::test_complete_verification_flow -v
```

**What it tests**:
- ✅ Embedding generated
- ✅ Similarity calculated
- ✅ Match determined

### Check Audio Processing
**File**: `TestAudioProcessingPipeline`

```bash
pytest test_integration_flows.py::TestAudioProcessingPipeline -v
```

**What it tests**:
- ✅ Chunking works
- ✅ Merging works
- ✅ Quality maintained

### Check Embeddings
**File**: `TestEmbeddingMatchingPipeline`

```bash
pytest test_integration_flows.py::TestEmbeddingMatchingPipeline -v
```

**What it tests**:
- ✅ Embedding generation
- ✅ Similarity calculation
- ✅ Matching logic

### Multi-Speaker Tests
**File**: `TestMultiSpeakerScenarios`

```bash
pytest test_integration_flows.py::TestMultiSpeakerScenarios -v
```

**What it tests**:
- ✅ Multiple enrollments
- ✅ Speaker identification
- ✅ Concurrent sessions

### Error Handling
**File**: `TestErrorHandlingAndRecovery`

```bash
pytest test_integration_flows.py::TestErrorHandlingAndRecovery -v
```

**What it tests**:
- ✅ Bad data handled
- ✅ Failures recovered
- ✅ System stable

### API Endpoints
**File**: `TestEndToEndAPIFlow`

```bash
pytest test_integration_flows.py::TestEndToEndAPIFlow -v
```

**What it tests**:
- ✅ /enroll endpoint
- ✅ /verify endpoint
- ✅ /health endpoint

### Performance
**File**: `TestPerformanceAndStress`

```bash
pytest test_integration_flows.py::TestPerformanceAndStress -v
```

**What it tests**:
- ✅ Rapid operations
- ✅ Batch processing
- ✅ Performance benchmarks

---

## 📊 EXPECTED OUTPUT

### Successful Run
```
test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow PASSED
test_integration_flows.py::TestEnrollmentFlowIntegration::test_enrollment_with_audio_chunking PASSED
...
========================= 27 passed in 15.23s =========================
```

### With Coverage
```
Name                           Stmts   Miss  Cover
--------------------------------------------------
enrollment_service.py           250    40   85%
voice_embedding.py              180    36   80%
matching_logic.py               220    55   75%
...
--------------------------------------------------
TOTAL                          1250   200   84%
```

---

## 🔧 DEBUGGING FAILED TESTS

### See Full Error
```bash
pytest test_integration_flows.py -vv --tb=long
```

### Show Print Statements
```bash
pytest test_integration_flows.py -s
```

### Run Specific Failing Test
```bash
pytest test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow -vv -s
```

### Check for Warnings
```bash
pytest test_integration_flows.py -W default
```

---

## 📈 PERFORMANCE METRICS

Current benchmarks:

| Operation | Time | Status |
|-----------|------|--------|
| Enrollment (3 chunks) | ~2.3s | ✅ Fast |
| Verification | ~0.4s | ✅ Very Fast |
| Embedding generation | ~1.8s | ✅ Fast |
| Audio chunking | ~0.8s | ✅ Very Fast |
| **Total Suite** | ~15s | ✅ Acceptable |
| **Quick Suite** | ~10s | ✅ Fast |

---

## 🆘 TROUBLESHOOTING

### ❌ "ModuleNotFoundError"
```bash
pip install -r requirements-test.txt
```

### ❌ "No module named pytest"
```bash
pip install pytest pytest-cov
```

### ❌ Tests hang
```bash
# Add timeout
pytest test_integration_flows.py --timeout=60
```

### ❌ High memory usage
```bash
# Run without parallelization
pytest test_integration_flows.py -v  # (no -n flag)
```

### ❌ Permission denied (Windows)
```bash
# Run as administrator or use python -m
python -m pytest test_integration_flows.py -v
```

---

## 📝 MARKER REFERENCE

**Use markers to run specific test types**:

```bash
# By category
pytest test_integration_flows.py -m enrollment        # Enrollment tests only
pytest test_integration_flows.py -m verification      # Verification tests only
pytest test_integration_flows.py -m audio_pipeline    # Audio pipeline tests
pytest test_integration_flows.py -m embedding         # Embedding tests
pytest test_integration_flows.py -m multi_speaker     # Multi-speaker tests
pytest test_integration_flows.py -m error_handling    # Error handling tests
pytest test_integration_flows.py -m api_integration   # API tests
pytest test_integration_flows.py -m performance       # Performance tests

# By speed
pytest test_integration_flows.py -m "not slow"        # Skip slow tests
pytest test_integration_flows.py -m slow              # Only slow tests

# Combinations
pytest test_integration_flows.py -m "enrollment and not slow"
pytest test_integration_flows.py -m "error_handling or edge_cases"
```

---

## 🎓 LEARNING RESOURCES

### Understand Integration Tests
1. Read: `INTEGRATION_TESTS_DOCUMENTATION.md`
2. Look at: `test_integration_flows.py` (well-commented)
3. Run: Individual tests and examine output
4. Modify: Change test parameters and see effects

### Understand Full Testing
1. Read: `TESTING_IMPLEMENTATION_COMPLETE.md`
2. Read: `TESTING_GUIDE_COMPREHENSIVE.md`
3. View: `test_suite_complete.py` (unit tests)
4. Check: Individual module tests

### Understand System
1. Read: `APP_ARCHITECTURE.md`
2. Read: `ENROLLMENT_SERVICE_GUIDE.md`
3. Read: `VERIFICATION_SERVICE_IMPLEMENTATION_SUMMARY.md`
4. Try: Running `main.py` and interacting with API

---

## 💡 TIPS & TRICKS

### Running Tests Faster
```bash
# Skip slow tests
pytest test_integration_flows.py -m "not slow" -v

# Parallel execution
pytest test_integration_flows.py -n auto

# Stop on first failure
pytest test_integration_flows.py -x
```

### Better Test Output
```bash
# Colored output
pytest test_integration_flows.py -v --color=yes

# Summary only
pytest test_integration_flows.py --tb=no

# Full traceback
pytest test_integration_flows.py --tb=long
```

### Generate Reports
```bash
# HTML report
pytest test_integration_flows.py --html=report.html

# JUnit XML (for CI/CD)
pytest test_integration_flows.py --junit-xml=results.xml

# Coverage HTML
pytest test_integration_flows.py --cov --cov-report=html
```

### Filter Tests
```bash
# Run tests containing "enrollment"
pytest test_integration_flows.py -k "enrollment"

# Run tests NOT containing "slow"
pytest test_integration_flows.py -k "not slow"
```

---

## 📞 QUICK HELP

### Most Common Tasks

| Task | Command |
|------|---------|
| Run all tests | `pytest test_integration_flows.py -v` |
| Run fast only | `pytest test_integration_flows.py -m "not slow" -v` |
| One test | `pytest test_integration_flows.py::CLASS::test_name -v` |
| With coverage | `pytest test_integration_flows.py --cov` |
| With report | `pytest test_integration_flows.py --html=report.html` |
| Parallel | `pytest test_integration_flows.py -n auto` |
| Verbose | `pytest test_integration_flows.py -vv -s` |
| Specific marker | `pytest test_integration_flows.py -m enrollment -v` |

---

## 🎯 NEXT STEPS

1. ✅ **Run tests**: `pytest test_integration_flows.py -v`
2. ✅ **View results**: Check output and pass/fail count
3. ✅ **Generate report**: `pytest test_integration_flows.py --html=report.html`
4. ✅ **Read failures**: If any fail, investigate with `-vv`
5. ✅ **Understand flows**: Read test code to understand workflows
6. ✅ **Integrate CI/CD**: Add to GitHub Actions or Jenkins

---

## 📚 DOCUMENTATION FILES

- **INTEGRATION_TESTS_DOCUMENTATION.md** - Complete detailed guide
- **TESTING_IMPLEMENTATION_COMPLETE.md** - Overall testing framework
- **TESTING_GUIDE_COMPREHENSIVE.md** - All testing information
- **test_integration_flows.py** - The actual test code
