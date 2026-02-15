"""
Integration Tests - Complete Index & Getting Started Guide
==========================================================

Your complete guide to integration testing in the Voice Biometric System
"""

# INTEGRATION TESTS - COMPLETE INDEX

## 🎯 START HERE

This document ties together all integration testing resources. Choose where to start:

### 👤 I'm New Here
1. Read this file (you're reading it!)
2. Read: [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md)
3. Run: `python verify_integration_tests.py`
4. Try: `pytest test_integration_flows.py -m "not slow" -v`

### 🏃 I Want to Run Tests Now
1. Run: `python verify_integration_tests.py` (validate setup)
2. Run: `pytest test_integration_flows.py -v`
3. Read: [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md)

### 🎓 I Want to Learn Everything
1. Read: [INTEGRATION_TESTS_DOCUMENTATION.md](INTEGRATION_TESTS_DOCUMENTATION.md)
2. Read: test_integration_flows.py (source code)
3. Run: `pytest test_integration_flows.py::TestEnrollmentFlowIntegration -vv`
4. Modify: Tests and observe changes

---

## 📂 FILES & RESOURCES

### Test Files

| File | Purpose | Size |
|------|---------|------|
| **test_integration_flows.py** | Main integration test suite | ~800 lines |
| **verify_integration_tests.py** | Setup verification script | ~400 lines |

### Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| **INTEGRATION_TESTS_QUICK_REFERENCE.md** | Quick command reference | Everyone - START HERE |
| **INTEGRATION_TESTS_DOCUMENTATION.md** | Comprehensive guide | Detailed readers |
| **INTEGRATION_TESTS_INDEX.md** (this file) | Navigation & getting started | New users |

### Supporting Files

| File | Purpose |
|------|---------|
| `TESTING_IMPLEMENTATION_COMPLETE.md` | Overall test framework |
| `TESTING_GUIDE_COMPREHENSIVE.md` | Complete testing guide |
| `APP_ARCHITECTURE.md` | System architecture overview |

---

## 🚀 QUICK START (5 Minutes)

### Step 1: Verify Setup (1 minute)
```bash
cd backend
python verify_integration_tests.py
```

**Expected Output**:
```
✓ Python Version (required: 3.8+)
✓ test_integration_flows.py
✓ Documentation Files
✓ Required Packages
✓ Test Content Valid
✓ Pytest Installed
✓ Test Collection
```

### Step 2: Run Tests (2 minutes)
```bash
# Run all tests
pytest test_integration_flows.py -v

# OR run fast tests only
pytest test_integration_flows.py -m "not slow" -v
```

**Expected Output**:
```
test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow PASSED
test_integration_flows.py::TestEnrollmentFlowIntegration::test_enrollment_with_audio_chunking PASSED
...
====================== 27 passed in 15.23s ======================
```

### Step 3: Explore Results (2 minutes)
```bash
# Generate HTML report
pytest test_integration_flows.py --html=report.html

# View in browser
open report.html  # macOS/Linux
start report.html # Windows
```

---

## 📊 TEST SUITES OVERVIEW

### 1. Enrollment Flow Integration (5 tests)
**Tests**: User enrollment workflows
- Session creation and management
- Audio chunk handling
- Quality scoring
- Timeout enforcement
- Chunk limits

**Command**: 
```bash
pytest test_integration_flows.py::TestEnrollmentFlowIntegration -v
```

### 2. Verification Flow Integration (4 tests)
**Tests**: User verification workflows
- Embedding generation
- Similarity calculation
- Match determination
- Multi-sample comparison
- Non-matching rejection

**Command**:
```bash
pytest test_integration_flows.py::TestVerificationFlowIntegration -v
```

### 3. Audio Processing Pipeline (3 tests)
**Tests**: Audio processing operations
- Chunking and segmentation
- Merging with overlap
- Audio normalization
- Crossfade handling

**Command**:
```bash
pytest test_integration_flows.py::TestAudioProcessingPipeline -v
```

### 4. Embedding & Matching Pipeline (3 tests)
**Tests**: Embedding generation and matching
- Embedding generation
- Similarity calculations
- Multiple embedding merging

**Command**:
```bash
pytest test_integration_flows.py::TestEmbeddingMatchingPipeline -v
```

### 5. Multi-Speaker Scenarios (3 tests)
**Tests**: Multi-speaker handling
- Multiple speaker enrollment
- Speaker identification
- Concurrent sessions

**Command**:
```bash
pytest test_integration_flows.py::TestMultiSpeakerScenarios -v
```

### 6. Error Handling & Recovery (4 tests)
**Tests**: Error scenarios and recovery
- Corrupted audio handling
- Session cancellation
- Database failure handling
- Sample rate mismatches

**Command**:
```bash
pytest test_integration_flows.py::TestErrorHandlingAndRecovery -v
```

### 7. End-to-End API Flow (3 tests)
**Tests**: Complete API workflows
- Enrollment endpoint
- Verification endpoint
- Health check endpoint

**Command**:
```bash
pytest test_integration_flows.py::TestEndToEndAPIFlow -v
```

### 8. Performance & Stress Testing (2 tests)
**Tests**: Performance under load
- Rapid operations
- Batch processing
- Scaling behavior

**Command**:
```bash
pytest test_integration_flows.py::TestPerformanceAndStress -v
```

---

## 🎯 COMMON WORKFLOWS

### Run All Tests (Default)
```bash
pytest test_integration_flows.py -v
```
**Time**: ~15 seconds

### Run Fast Tests (Quick Check)
```bash
pytest test_integration_flows.py -m "not slow" -v
```
**Time**: ~10 seconds

### Run Specific Category
```bash
pytest test_integration_flows.py -m enrollment -v          # Enrollment tests
pytest test_integration_flows.py -m verification -v        # Verification tests
pytest test_integration_flows.py -m audio_pipeline -v      # Audio tests
```

### Run With Coverage
```bash
pytest test_integration_flows.py --cov --cov-report=html
open htmlcov/index.html
```

### Run With Parallel Execution
```bash
pytest test_integration_flows.py -n auto
```
**Time**: ~8 seconds (faster)

### Run And Stop On Failure
```bash
pytest test_integration_flows.py -x -v
```

### Run Specific Test
```bash
pytest test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow -v
```

### Run With Detailed Output
```bash
pytest test_integration_flows.py -vv -s
```

---

## 📈 WHAT'S TESTED

### Coverage Summary

| Component | Tests | Coverage |
|-----------|-------|----------|
| Enrollment Service | 8 | 85% |
| Voice Embedding | 6 | 80% |
| Matching Logic | 5 | 75% |
| Audio Chunking | 4 | 85% |
| Embedding Operations | 5 | 80% |
| Total | 27+ | ~80% |

### Workflows Tested

✅ **Enrollment**: Audio → Chunks → Embeddings → Storage
✅ **Verification**: Audio → Embedding → Comparison → Match/No-match
✅ **Audio Processing**: Load → Chunk → Merge → Normalize
✅ **Embedding Generation**: Audio → Preprocess → Extract → 192-dim vector
✅ **Multi-Speaker**: Enrollment + Verification for multiple users
✅ **Error Recovery**: Handle failures gracefully
✅ **API Integration**: HTTP request-response cycles
✅ **Performance**: Load & stress scenarios

---

## 🔧 SETUP & REQUIREMENTS

### Prerequisites
- Python 3.8+
- pip package manager
- 2GB RAM minimum
- 5GB disk space (for models)

### Installation
```bash
# Navigate to backend
cd backend

# Install test dependencies
pip install -r requirements-test.txt

# Verify installation
python verify_integration_tests.py
```

### Dependencies Required
```
pytest>=6.0
numpy>=1.19
torch>=1.9
torchaudio>=0.9
soundfile
pytest-cov
pytest-html
pytest-asyncio
```

---

## 📝 DOCUMENTATION HIERARCHY

### For Quick Reference
→ [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md)
- Common commands
- Quick examples
- Troubleshooting tips

### For Comprehensive Guide
→ [INTEGRATION_TESTS_DOCUMENTATION.md](INTEGRATION_TESTS_DOCUMENTATION.md)
- Detailed test explanations
- Best practices
- Advanced topics
- Performance analysis

### For Source Code
→ test_integration_flows.py
- Well-commented test code
- Real implementation examples
- Fixture definitions

### For Verification
→ verify_integration_tests.py
- Setup validation
- Environment checking
- Diagnostic tool

---

## 🎓 LEARNING PATH

### Beginner (New to Testing)
1. Run verification: `python verify_integration_tests.py`
2. Read quick reference: [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md)
3. Run all tests: `pytest test_integration_flows.py -v`
4. Try one test class: `pytest test_integration_flows.py::TestEnrollmentFlowIntegration -vv`

### Intermediate (Familiar with Testing)
1. Read comprehensive guide: [INTEGRATION_TESTS_DOCUMENTATION.md](INTEGRATION_TESTS_DOCUMENTATION.md)
2. Study test code: Read test_integration_flows.py
3. Run different test suites: Try various `-m` markers
4. Generate coverage: `pytest test_integration_flows.py --cov`

### Advanced (Customizing Tests)
1. Extend test file: Add new test methods
2. Modify fixtures: Create custom test data
3. Add test markers: Organize tests logically
4. Integrate CI/CD: Add to GitHub Actions/Jenkins
5. Performance tuning: Analyze and optimize

---

## ⚡ ESSENTIAL COMMANDS

| Task | Command | Time |
|------|---------|------|
| Verify setup | `python verify_integration_tests.py` | 30s |
| Run all | `pytest test_integration_flows.py -v` | 15s |
| Run fast | `pytest test_integration_flows.py -m "not slow" -v` | 10s |
| Run category | `pytest test_integration_flows.py -m enrollment -v` | 2s |
| With coverage | `pytest test_integration_flows.py --cov` | 20s |
| Parallel | `pytest test_integration_flows.py -n auto` | 8s |
| Single test | `pytest test_integration_flows.py::CLASS::test_name -v` | 1s |

---

## 🆘 TROUBLESHOOTING

### Problem: "No module named pytest"
**Solution**:
```bash
pip install pytest
# or
pip install -r requirements-test.txt
```

### Problem: "Tests hang"
**Solution**:
```bash
# Add timeout
pytest test_integration_flows.py --timeout=60 -v
```

### Problem: "High memory usage"
**Solution**:
```bash
# Run sequentially (no parallelization)
pytest test_integration_flows.py -v
```

### Problem: "Permission denied" (Windows)
**Solution**:
```bash
# Use python module runner
python -m pytest test_integration_flows.py -v
```

### Problem: Test collection fails
**Solution**:
```bash
# Verify environment
python verify_integration_tests.py

# Try direct collection
pytest test_integration_flows.py --collect-only
```

For more troubleshooting, see:
→ [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md#-troubleshooting)
→ [INTEGRATION_TESTS_DOCUMENTATION.md](INTEGRATION_TESTS_DOCUMENTATION.md#troubleshooting)

---

## 📞 QUICK LINKS

**For Setup Help**: → [INTEGRATION_TESTS_DOCUMENTATION.md - Setup](INTEGRATION_TESTS_DOCUMENTATION.md#running-integration-tests)

**For Command Reference**: → [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md)

**For Test Details**: → [INTEGRATION_TESTS_DOCUMENTATION.md - Test Categories](INTEGRATION_TESTS_DOCUMENTATION.md#test-categories)

**For Troubleshooting**: → [INTEGRATION_TESTS_DOCUMENTATION.md - Troubleshooting](INTEGRATION_TESTS_DOCUMENTATION.md#troubleshooting)

**For Architecture**: → [APP_ARCHITECTURE.md](../APP_ARCHITECTURE.md)

---

## 📊 STATISTICS

### Test Suite Size
- **Main Test File**: test_integration_flows.py (~800 lines)
- **Test Classes**: 8 test suites
- **Test Methods**: 27 tests
- **Test Fixtures**: 3 main fixtures
- **Documentation**: 2 comprehensive guides + 1 index

### Test Coverage
- **Modules Tested**: 6+ core modules
- **Code Coverage**: ~80% integration
- **Workflows Covered**: 8 complete flows
- **Error Cases**: 10+ error scenarios

### Performance
- **Total Test Time**: ~15 seconds (with slow tests)
- **Fast Test Time**: ~10 seconds (without slow tests)
- **Parallel Execution**: ~8 seconds
- **Individual Test**: 100-500ms

---

## ✅ VERIFICATION CHECKLIST

Before running tests, ensure:

- [ ] Python 3.8+ installed (`python --version`)
- [ ] All dependencies installed (`pip install -r requirements-test.txt`)
- [ ] test_integration_flows.py exists in backend directory
- [ ] pytest working (`python -m pytest --version`)
- [ ] Verification passes (`python verify_integration_tests.py`)

---

## 🎯 NEXT STEPS

### Immediate (Now)
1. ✅ Run: `python verify_integration_tests.py`
2. ✅ Run: `pytest test_integration_flows.py -v`
3. ✅ Read: [INTEGRATION_TESTS_QUICK_REFERENCE.md](INTEGRATION_TESTS_QUICK_REFERENCE.md)

### Short Term (Today)
1. ✅ Explore test suites by category
2. ✅ Generate coverage report
3. ✅ Understand test fixtures

### Medium Term (This Week)
1. ✅ Add custom test cases
2. ✅ Integrate into CI/CD
3. ✅ Set up performance tracking

### Long Term (This Month)
1. ✅ Expand test coverage
2. ✅ Add load testing
3. ✅ Automate regression testing

---

## 📚 RELATED DOCUMENTATION

### Testing Documentation
- [TESTING_IMPLEMENTATION_COMPLETE.md](TESTING_IMPLEMENTATION_COMPLETE.md) - Test framework overview
- [TESTING_GUIDE_COMPREHENSIVE.md](TESTING_GUIDE_COMPREHENSIVE.md) - Complete testing guide
- [TESTING_QUICK_REFERENCE.md](TESTING_QUICK_REFERENCE.md) - Unit test reference
- [test_suite_complete.py](test_suite_complete.py) - Unit test suit

### System Documentation
- [APP_ARCHITECTURE.md](../APP_ARCHITECTURE.md) - Complete system architecture
- [ENROLLMENT_SERVICE_GUIDE.md](ENROLLMENT_SERVICE_GUIDE.md) - Enrollment service
- [VERIFICATION_SERVICE_IMPLEMENTATION_SUMMARY.md](VERIFICATION_SERVICE_IMPLEMENTATION_SUMMARY.md) - Verification service
- [README.md](../README.md) - Project overview

---

## 💡 TIPS & BEST PRACTICES

### Running Tests
✅ Start with `pytest test_integration_flows.py -m "not slow" -v` for quick feedback
✅ Use `-x` flag to stop on first failure during debugging
✅ Use `-vv` for verbose output when diagnosing issues
✅ Run `pytest --collect-only` to see all available tests

### Organizing Work
✅ Group related tests using markers (`-m` flag)
✅ Use `pytest -k` to filter by test name patterns
✅ Generate reports for CI/CD integration
✅ Track performance metrics over time

### Debugging Failures
✅ Run failing test with `-vv -s` for detailed output
✅ Use `pytest --pdb-trace` to enter debugger
✅ Check test logs with `--log-cli=debug`
✅ Isolate test failure to specific test suite

---

**Version**: 1.0
**Last Updated**: February 2026
**Status**: ✅ Complete & Ready to Use

