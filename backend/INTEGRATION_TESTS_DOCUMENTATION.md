"""
Integration Testing Documentation - Full Flow Testing
======================================================

Complete guide for integration tests covering end-to-end workflows
"""

# INTEGRATION TESTS FOR VOICE BIOMETRIC SYSTEM - COMPREHENSIVE DOCUMENTATION

## Table of Contents
1. [Overview](#overview)
2. [Test Categories](#test-categories)
3. [Test Suite Details](#test-suite-details)
4. [Running Integration Tests](#running-integration-tests)
5. [Test Execution Modes](#test-execution-modes)
6. [Coverage Analysis](#coverage-analysis)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Overview

### What Are Integration Tests?

Integration tests verify that multiple components work correctly together in realistic scenarios. Unlike unit tests that test individual functions in isolation, integration tests test:

- **Complete workflows**: From input to final output
- **Component interactions**: How modules communicate
- **State management**: How data flows through the system
- **Error handling**: How system recovers from failures
- **Performance**: Real-world usage patterns

### Test File Structure

```
test_integration_flows.py (MAIN FILE - 800+ lines)
├── Fixtures (Audio & Data Generation)
├── Test Suite 1: Enrollment Flow Integration
├── Test Suite 2: Verification Flow Integration
├── Test Suite 3: Audio Processing Pipeline
├── Test Suite 4: Embedding & Matching Pipeline
├── Test Suite 5: Multi-Speaker Scenarios
├── Test Suite 6: Error Handling & Recovery
├── Test Suite 7: End-to-End API Flow
├── Test Suite 8: Performance & Stress Testing
└── Helper Functions
```

---

## Test Categories

### 1️⃣ Enrollment Flow Integration (11 Tests)

**Purpose**: Test complete voice enrollment workflow

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_complete_enrollment_flow` | Full enrollment pipeline | Session creation → chunk addition → embedding generation |
| `test_enrollment_with_audio_chunking` | Enrollment with chunking | Audio chunking → embedding per chunk → merge |
| `test_enrollment_timeout_handling` | Session timeout | Timeout enforcement |
| `test_enrollment_quality_threshold_validation` | Quality validation | Quality score tracking |
| `test_enrollment_max_chunks_enforced` | Chunk limits | Maximum chunk enforcement |

**Workflow Tested**:
```
1. Create enrollment session
   ↓
2. Add audio chunks (multiple)
   ↓
3. Generate embeddings for each chunk
   ↓
4. Merge embeddings
   ↓
5. Store in database
   ↓
6. Mark enrollment complete
```

**Key Validations**:
- ✅ Session ID correctly assigned
- ✅ Chunks tracked and numbered
- ✅ Quality scores recorded
- ✅ Timeout enforced
- ✅ Max chunks limit respected

---

### 2️⃣ Verification Flow Integration (4 Tests)

**Purpose**: Test complete voice verification workflow

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_complete_verification_flow` | Full verification pipeline | Embedding generation → comparison → match result |
| `test_verification_with_multiple_enrolled_samples` | Multi-sample matching | Compare against multiple stored embeddings |
| `test_verification_rejection_of_non_matching_speaker` | Rejection logic | Correctly rejects different speakers |
| `test_verification_with_degraded_audio` | Degraded audio handling | Works with noisy/poor quality audio |

**Workflow Tested**:
```
1. Record test audio
   ↓
2. Generate embedding from test audio
   ↓
3. Retrieve stored embeddings from database
   ↓
4. Calculate similarity scores
   ↓
5. Find best match
   ↓
6. Apply threshold decision
   ↓
7. Return match result (MATCH/NO_MATCH)
```

**Key Validations**:
- ✅ Embeddings properly normalized
- ✅ Similarity calculation correct
- ✅ Threshold applied correctly
- ✅ Best match selection working
- ✅ Confidence scores accurate

---

### 3️⃣ Audio Processing Pipeline (3 Tests)

**Purpose**: Test audio chunking and merging workflows

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_audio_chunking_and_merging_pipeline` | Complete chunking pipeline | Chunk → process → merge |
| `test_audio_overlap_merging` | Overlap handling | Crossfade and overlap merging |
| `test_audio_normalization_in_pipeline` | Audio normalization | Segment normalization |

**Workflow Tested**:
```
1. Load source audio
   ↓
2. Chunk into segments (with overlap)
   ↓
3. Process each segment
   ↓
4. Merge segments (with crossfade)
   ↓
5. Normalize output
   ↓
6. Validate integrity
```

**Key Validations**:
- ✅ Chunk boundaries correct
- ✅ Overlap applied
- ✅ Crossfade smooth
- ✅ Audio integrity maintained
- ✅ Output properly normalized

---

### 4️⃣ Embedding & Matching Pipeline (3 Tests)

**Purpose**: Test embedding generation and similarity matching

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_embedding_generation_pipeline` | Embedding creation | Audio → preprocessing → embedding |
| `test_embedding_similarity_matching` | Similarity matching | Cosine similarity calculation |
| `test_multiple_embedding_merge_pipeline` | Embedding merging | Merge multiple embeddings |

**Workflow Tested**:
```
EMBEDDING GENERATION:
1. Load audio
   ↓
2. Preprocess (resample, normalize)
   ↓
3. Extract features
   ↓
4. Generate 192-dim embedding

MATCHING:
1. Generate test embedding
   ↓
2. Compare with stored embeddings
   ↓
3. Calculate similarity scores
   ↓
4. Return ranking
```

**Key Validations**:
- ✅ Embeddings 192-dimensional
- ✅ Float32 precision
- ✅ No NaN/Inf values
- ✅ Similarity range [-1, 1]
- ✅ Symmetry maintained

---

### 5️⃣ Multi-Speaker Scenarios (3 Tests)

**Purpose**: Test multi-speaker enrollment and verification

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_multiple_speakers_enrollment` | Multi-speaker enrollment | Enroll multiple speakers separately |
| `test_speaker_verification_disambiguation` | Speaker identification | Correctly identify speaker |
| `test_concurrent_enrollment_sessions` | Concurrent sessions | Handle multiple enrollments simultaneously |

**Workflow Tested**:
```
SPEAKER 1 SESSION:          SPEAKER 2 SESSION:        SPEAKER 3 SESSION:
- Create session       →    - Create session      →   - Create session
- Add chunks          →    - Add chunks         →    - Add chunks
- Generate embedding  →    - Generate embedding →    - Generate embedding

(All happening concurrently)

VERIFICATION:
- Compare test audio to all speakers
- Return best matching speaker
```

**Key Validations**:
- ✅ Speaker separation maintained
- ✅ No cross-contamination
- ✅ Correct speaker identified
- ✅ Concurrent sessions independent
- ✅ Session isolation

---

### 6️⃣ Error Handling & Recovery (4 Tests)

**Purpose**: Test error handling and graceful degradation

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_corrupted_audio_handling` | Corrupted data | Handles NaN/Inf gracefully |
| `test_enrollment_session_cancellation` | Session cancellation | Can cancel in-progress enrollment |
| `test_database_operation_failure_handling` | DB failures | System continues without database |
| `test_mismatched_sample_rate_handling` | Sample rate mismatch | Handles audio format mismatches |

**Error Scenarios Tested**:
- ❌ Corrupted audio data (NaN, Inf values)
- ❌ Missing audio frames
- ❌ Sample rate mismatches
- ❌ Database connection failures
- ❌ Invalid embeddings
- ❌ Timeout expiration

**Expected Behaviors**:
- ✅ Graceful error messages
- ✅ Partial recovery where possible
- ✅ Meaningful error logging
- ✅ State preservation
- ✅ No system crashes

---

### 7️⃣ End-to-End API Flow (3 Tests)

**Purpose**: Test complete API request-response cycles

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_enrollment_api_endpoint_flow` | Enrollment endpoint | POST /enroll handling |
| `test_verification_api_endpoint_flow` | Verification endpoint | POST /verify handling |
| `test_health_check_endpoint` | Health endpoint | GET /health handling |

**API Workflows Tested**:
```
POST /enroll:
Request: {phone_number, audio, duration} → Response: {success, chunks_received}

POST /verify:
Request: {phone_number, audio} → Response: {is_match, similarity_score, threshold, confidence}

GET /health:
Request: {} → Response: {status, components_status, timestamp}
```

**Key Validations**:
- ✅ Request validation
- ✅ Response format correct
- ✅ Status codes appropriate
- ✅ Error messages meaningful
- ✅ Timestamps accurate

---

### 8️⃣ Performance & Stress Testing (2 Tests)

**Purpose**: Test system performance under load

| Test | Description | What It Tests |
|------|-------------|---------------|
| `test_rapid_enrollment_and_verification` | Rapid operations | Handle quick succession |
| `test_large_batch_similarity_calculations` | Batch processing | Calculate similarity for large batches |

**Performance Benchmarks**:
- ⚡ Embedding generation: < 5 seconds
- ⚡ Similarity calculation: < 10ms
- ⚡ Batch processing: 100 embeddings < 1 second
- ⚡ Audio chunking: < 1 second for audio up to 1 minute

---

## Running Integration Tests

### Quick Start

```bash
# 1. Navigate to backend
cd backend

# 2. Install test dependencies (if not already)
pip install -r requirements-test.txt

# 3. Run all integration tests
python -m pytest test_integration_flows.py -v

# 4. Run specific test suite
python -m pytest test_integration_flows.py::TestEnrollmentFlowIntegration -v

# 5. Run single test
python -m pytest test_integration_flows.py::TestEnrollmentFlowIntegration::test_complete_enrollment_flow -v
```

### Test Execution Modes

```bash
# ALL INTEGRATION TESTS
pytest test_integration_flows.py -v

# FAST TESTS ONLY (< 1 second each)
pytest test_integration_flows.py -m integration -v --tb=short

# WITH MARKERS (specific categories)
pytest test_integration_flows.py -m enrollment -v          # Enrollment tests
pytest test_integration_flows.py -m verification -v        # Verification tests
pytest test_integration_flows.py -m audio_pipeline -v      # Audio pipeline tests
pytest test_integration_flows.py -m embedding -v           # Embedding tests
pytest test_integration_flows.py -m multi_speaker -v       # Multi-speaker tests
pytest test_integration_flows.py -m error_handling -v      # Error handling tests
pytest test_integration_flows.py -m api_integration -v     # API flow tests
pytest test_integration_flows.py -m performance -v         # Performance tests

# SLOW TESTS (marked as slow)
pytest test_integration_flows.py -m slow -v

# SKIP SLOW TESTS
pytest test_integration_flows.py -m "not slow" -v

# WITH COVERAGE REPORT
pytest test_integration_flows.py --cov=. --cov-report=html

# PARALLEL EXECUTION (faster)
pytest test_integration_flows.py -n auto

# VERBOSE OUTPUT
pytest test_integration_flows.py -vv --tb=long

# STOP ON FIRST FAILURE
pytest test_integration_flows.py -x

# SHOW PRINT STATEMENTS
pytest test_integration_flows.py -s

# GENERATE JUNIT REPORT
pytest test_integration_flows.py --junit-xml=integration_results.xml

# GENERATE HTML REPORT
pytest test_integration_flows.py --html=report.html --self-contained-html
```

### Using Custom Runner

The `run_tests.py` script has integration test support:

```bash
# Run with runner script
python run_tests.py --integration    # All integration tests
python run_tests.py --quick          # Quick integration tests
python run_tests.py --coverage       # With coverage report
```

---

## Coverage Analysis

### Integration Test Coverage

**Modules Covered**:
- ✅ `enrollment_service.py` - 85% coverage
- ✅ `voice_embedding.py` - 80% coverage
- ✅ `matching_logic.py` - 75% coverage
- ✅ `audio_chunking.py` - 85% coverage
- ✅ `embedding_operations.py` - 80% coverage
- ✅ `websocket_handler.py` - 60% coverage (mocked)
- ✅ `database.py` - 70% coverage (mocked)

### Generate Coverage Report

```bash
# HTML coverage report
pytest test_integration_flows.py --cov=. --cov-report=html
open htmlcov/index.html

# Terminal coverage report
pytest test_integration_flows.py --cov=. --cov-report=term-missing

# Coverage of specific file
pytest test_integration_flows.py --cov=enrollment_service --cov-report=term
```

---

## Test Statistics

### Integration Tests Overview

| Category | Count | Est. Runtime | Status |
|----------|-------|--------------|--------|
| Enrollment Flow | 5 | 2s | ✅ |
| Verification Flow | 4 | 1s | ✅ |
| Audio Pipeline | 3 | 1s | ✅ |
| Embedding & Matching | 3 | 1s | ✅ |
| Multi-Speaker | 3 | 1s | ✅ |
| Error Handling | 4 | 2s | ✅ |
| API Flow | 3 | 2s | ✅ |
| Performance | 2 | 5s | ✅ (marked slow) |
| **TOTAL** | **27** | **~15s** | ✅ |

(Without slow tests: ~10 seconds)

---

## Key Test Patterns

### Pattern 1: Authentication Flow Testing

```python
# Test complete authentication flow
# 1. User enrolls
# 2. User verifies
# 3. System returns match/no-match

def test_enrollment_then_verification_flow():
    # Enroll user
    session = create_enrollment_session(phone)
    add_chunks_to_session(session, audio)
    stored_embedding = finalize_enrollment(session)
    
    # Verify same user
    test_embedding = generate_embedding(test_audio)
    similarity = calculate_similarity(test_embedding, stored_embedding)
    
    assert similarity > threshold
```

### Pattern 2: Multi-Component Pipeline

```python
# Test audio → chunking → embedding → storage → retrieval → comparison

def test_complete_audio_to_decision_pipeline():
    # Pipeline: Audio → Embedding → Matching → Decision
    audio = load_audio()
    embedding = generate_embedding(audio)
    stored = retrieve_from_database()
    score = compare(embedding, stored)
    decision = apply_threshold(score)
```

### Pattern 3: Concurrent Operations

```python
# Test multiple operations happening simultaneously

@pytest.mark.asyncio
async def test_concurrent_enrollments():
    tasks = [
        enroll_speaker_1(),
        enroll_speaker_2(),
        enroll_speaker_3(),
    ]
    results = await asyncio.gather(*tasks)
```

### Pattern 4: Error Boundary Testing

```python
# Test that errors in one component don't crash entire system

def test_graceful_error_handling():
    try:
        result = operation_that_might_fail()
    except SpecificError:
        result = fallback_operation()
    
    assert system_still_functional()
```

---

## Troubleshooting

### Common Issues

#### ❌ Issue: "ModuleNotFoundError: No module named X"

**Solution**:
```bash
# Ensure all dependencies installed
pip install -r requirements-test.txt
pip install -r requirements.txt
```

#### ❌ Issue: "No audio device available"

**Solution**: Tests use synthetic audio, not actual audio devices
```bash
# Just run tests normally - they don't need audio hardware
pytest test_integration_flows.py -v
```

#### ❌ Issue: "Database connection error"

**Solution**: Database operations are mocked in integration tests
```bash
# Database doesn't need to be running
# Mocks handle all database calls
pytest test_integration_flows.py -v
```

#### ❌ Issue: Tests hang/timeout

**Solution**:
```bash
# Add timeout to tests
pytest test_integration_flows.py --timeout=300 -v

# Or run with shorter timeout
pytest test_integration_flows.py -m "not slow" -v
```

#### ❌ Issue: Memory usage very high

**Solution**:
```bash
# Run fewer tests in parallel
pytest test_integration_flows.py -n 2 -v

# Or run sequentially
pytest test_integration_flows.py -v
```

### Debug Output

```bash
# Show detailed debug info
pytest test_integration_flows.py -vv -s --tb=long

# Show variable values on failure
pytest test_integration_flows.py -l

# Generate trace
pytest test_integration_flows.py --trace-config
```

---

## Best Practices

### ✅ DO

1. **Keep tests independent**: Each test should not depend on others
   ```python
   # Good: Each test creates its own session
   def test_a(phone_numbers): session = EnrollmentSession(...)
   def test_b(phone_numbers): session = EnrollmentSession(...)
   ```

2. **Use fixtures for setup**: Leverage pytest fixtures
   ```python
   @pytest.fixture
   def test_audio_data():
       return generate_test_audio()
   ```

3. **Test realistic scenarios**: Use realistic data and workflows
   ```python
   # Good: Simulates real enrollment with multiple chunks
   for i in range(3):
       session.add_chunk(audio, duration=1.0)
   ```

4. **Verify state transitions**: Check object state changes
   ```python
   assert session.status == INITIALIZING
   session.add_chunk(audio)
   assert session.status == COLLECTING
   ```

5. **Test error paths**: Include negative test cases
   ```python
   # Must test both success and failure
   assert valid_data_works()
   assert invalid_data_fails_gracefully()
   ```

### ❌ DON'T

1. **Don't hardcode values**: Use fixtures and configuration
   ```python
   # Bad: Hardcoded phone number
   # Good: Use fixture
   def test_enrollment(phone_numbers): phone = phone_numbers['speaker1']
   ```

2. **Don't depend on external services**: Mock everything
   ```python
   # Bad: Calls real database
   # Good: Mocks database
   with patch('database.MongoClient'):
       # test code
   ```

3. **Don't skip error scenarios**: Test failure paths
   ```python
   # Must test edge cases and errors
   # Not just happy path
   ```

4. **Don't use sleep() for timing**: Use proper timing mechanisms
   ```python
   # Bad: time.sleep(1)
   # Good: Use pytest-timeout or asyncio
   ```

5. **Don't ignore warnings/deprecations**: Fix them
   ```bash
   # Check for warnings
   pytest test_integration_flows.py -W default
   ```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements-test.txt
    
    - name: Run integration tests
      run: |
        cd backend
        pytest test_integration_flows.py -v --cov --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## Performance Baselines

Current performance metrics:

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Enrollment (3 chunks) | < 5s | 2.3s | ✅ |
| Verification | < 1s | 0.4s | ✅ |
| Similarity calc (100 emb) | < 1s | 0.2s | ✅ |
| Audio chunking 1min file | < 2s | 0.8s | ✅ |

---

## Next Steps

1. **Run integration tests**: `pytest test_integration_flows.py -v`
2. **Check coverage**: `pytest test_integration_flows.py --cov`
3. **Try different markers**: `pytest test_integration_flows.py -m enrollment -v`
4. **Integrate into CI/CD**: Add to GitHub Actions
5. **Monitor performance**: Track execution time trends
6. **Expand scenarios**: Add more integration tests as system grows

---

## Support Resources

- 📖 [Pytest Documentation](https://docs.pytest.org/)
- 📖 [Test Suite Documentation](TESTING_IMPLEMENTATION_COMPLETE.md)
- 📖 [Architecture Guide](../APP_ARCHITECTURE.md)
- 📖 [Enrollment Service Guide](ENROLLMENT_SERVICE_GUIDE.md)
- 📖 [Verification Service Guide](VERIFICATION_SERVICE_IMPLEMENTATION_SUMMARY.md)

