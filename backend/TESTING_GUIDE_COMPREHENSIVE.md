# Comprehensive Testing & Validation Guide

## Overview

This document provides a complete guide to testing and validating the Voice Biometric Authentication API using pytest and comprehensive unit test suites.

## Table of Contents

1. [Testing Framework Setup](#testing-framework-setup)
2. [Test Suite Organization](#test-suite-organization)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Mock Testing](#mock-testing)
6. [Integration Testing](#integration-testing)
7. [Performance Testing](#performance-testing)
8. [CI/CD Integration](#cicd-integration)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Testing Framework Setup

### Prerequisites

Ensure you have pytest and related packages installed:

```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio pytest-timeout
```

Optional packages for enhanced functionality:

```bash
# For parallel test execution
pip install pytest-xdist

# For HTML reports
pip install pytest-html

# For performance profiling
pip install pytest-benchmark pytest-profiling

# For JUnit XML reports
pip install pytest-junit-xml

# For test result statistics
pip install pytest-json-report
```

### Installation

To install all testing dependencies:

```bash
pip install -r requirements-test.txt
```

---

## Test Suite Organization

### Main Test Files

The testing infrastructure consists of:

- **`test_suite_complete.py`** - Comprehensive unit test suite for all modules
- **`test_*.py`** - Individual module test files (existing tests)
- **`conftest.py`** - Pytest configuration and fixtures
- **`pytest.ini`** - Pytest configuration
- **`run_tests.py`** - Test runner script with various execution modes

### Test Categories

Tests are organized by marker:

| Marker | Description |
|--------|-------------|
| `unit` | Unit tests for individual functions |
| `integration` | Integration tests combining modules |
| `performance` | Performance and benchmark tests |
| `edge_cases` | Edge case and error handling |
| `slow` | Tests taking significant time |
| `database` | Database operation tests |
| `websocket` | WebSocket functionality tests |
| `embedding` | Embedding operations tests |
| `enrollment` | Enrollment service tests |
| `matching` | Matching logic tests |
| `smoke` | Quick smoke tests |

---

## Running Tests

### Basic Test Execution

#### Run All Tests
```bash
python -m pytest
python -m pytest -v  # Verbose output
python run_tests.py --all
```

#### Run Quick Smoke Tests
```bash
python -m pytest -m smoke
python run_tests.py --quick
```

#### Run Only Fast Tests (Exclude Slow)
```bash
python -m pytest -m "not slow"
python run_tests.py --fast
```

#### Run Specific Test Category
```bash
# Unit tests only
python -m pytest -m unit -v

# Integration tests
python -m pytest -m integration -v

# Embedding tests
python -m pytest -m embedding -v

# Run via runner script
python run_tests.py --marker unit
```

#### Run Specific Test File
```bash
python -m pytest test_suite_complete.py -v
python run_tests.py --specific test_suite_complete.py
```

#### Run Specific Test Class
```bash
python -m pytest test_suite_complete.py::TestVoiceEmbedding -v
```

#### Run Specific Test Function
```bash
python -m pytest test_suite_complete.py::TestVoiceEmbedding::test_embedding_generation_basic -v
python run_tests.py --specific "test_suite_complete.py::TestVoiceEmbedding::test_embedding_generation_basic"
```

### Advanced Test Execution

#### Run with Coverage Report
```bash
python -m pytest --cov=. --cov-report=html --cov-report=term-missing
python run_tests.py --coverage
```

This generates:
- Terminal output with coverage statistics
- HTML report in `htmlcov/index.html`

#### Run Tests in Parallel
```bash
python -m pytest -n auto  # Auto-detect number of cores
python -m pytest -n 4     # Use 4 workers
python run_tests.py --parallel 4
```

#### Generate JUnit XML Report
```bash
python -m pytest --junit-xml=test_results.xml
python run_tests.py --junit test_results.xml
```

#### Generate HTML Report
```bash
python -m pytest --html=test_results.html --self-contained-html
python run_tests.py --html
```

#### Save Output to File
```bash
python -m pytest -v > test_results.txt 2>&1
python run_tests.py --output test_results.txt
```

#### Run with Custom Configuration
```bash
# Timeout for each test (requires pytest-timeout)
python -m pytest --timeout=300 -v

# Maximum failures before stopping
python -m pytest -x  # Stop on first failure
python -m pytest --maxfail=3  # Stop after 3 failures

# Show extra test summary
python -m pytest -ra  # Show all summary info
python -m pytest -rf  # Show only failed tests
```

---

## Test Coverage

### Coverage Analysis

#### Generate Coverage Report
```bash
python -m pytest --cov=. --cov-report=html
```

This creates an HTML report in `htmlcov/` showing:
- Line coverage percentage for each file
- Uncovered code lines highlighted
- Branch coverage statistics

#### View Coverage Report
```bash
# Open in browser (Linux/Mac)
open htmlcov/index.html

# Open in browser (Windows)
start htmlcov/index.html

# Or view in terminal
python -m pytest --cov=. --cov-report=term-missing
```

#### Coverage Minimum Enforcement
```bash
python -m pytest --cov=. --cov-fail-under=80
```

Fails if coverage drops below 80%.

### Target Coverage

Recommended coverage targets:

- **Unit tests**: > 90% coverage
- **Integration tests**: > 70% coverage
- **Overall**: > 85% coverage

---

## Mock Testing

### Mocking Database Operations

```python
from unittest.mock import Mock, patch, MagicMock

def test_store_embedding(mock_mongodb):
    """Test with mocked MongoDB"""
    from database import store_voice_embedding
    
    mock_collection = mock_mongodb['collection']
    mock_collection.insert_one.return_value.inserted_id = "test_id"
    
    # Your test code here
    pass
```

### Mocking External Services

```python
@patch('requests.get')
def test_external_api_call(mock_get):
    """Test with mocked HTTP call"""
    mock_get.return_value.json.return_value = {'key': 'value'}
    
    # Your test code here
    pass
```

### Using Fixtures for Mock Setup

```python
@pytest.fixture
def mock_mongodb():
    """Fixture providing mocked MongoDB"""
    with patch('database.MongoClient') as mock_client:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        yield {
            'client': mock_client,
            'db': mock_db,
            'collection': mock_collection
        }
```

---

## Integration Testing

### Integration Test Example

```python
@pytest.mark.integration
def test_full_enrollment_flow():
    """Test complete enrollment flow"""
    # 1. Create enrollment session
    session = create_enrollment_session("1234567890")
    
    # 2. Add audio chunks
    for i in range(3):
        audio = generate_test_audio()
        session.add_chunk(audio)
    
    # 3. Finalize enrollment
    result = finalize_enrollment(session)
    
    # 4. Verify result
    assert result.success
    assert result.embedding is not None
```

### Running Integration Tests

```bash
python -m pytest -m integration -v
python run_tests.py --marker integration
```

---

## Performance Testing

### Benchmarking with pytest-benchmark

```python
@pytest.mark.performance
def test_embedding_performance(benchmark):
    """Benchmark embedding generation"""
    audio = create_test_audio()
    
    result = benchmark(generate_embedding, audio)
    
    assert result is not None
```

Run performance tests:

```bash
python -m pytest -m performance -v
python run_tests.py --profile
```

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Embedding Generation | < 2s per second of audio | On GPU-enabled system |
| Similarity Calculation | < 1ms | For single pair |
| Batch Similarity (1000 pairs) | < 1s | Vectorized operations |

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        python -m pytest test_suite_complete.py -v --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        files: ./coverage.xml
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
test:
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - pip install -r requirements-test.txt
    - python -m pytest test_suite_complete.py -v --cov=. --junit-xml=report.xml
  artifacts:
    reports:
      junit: report.xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

---

## Best Practices

### 1. Test Organization

✅ DO:
- One test per function/scenario
- Descriptive test names
- Clear setup/teardown
- Group related tests in classes

❌ DON'T:
- Test multiple unrelated things in one test
- Rely on test execution order
- Leave tests in broken state

### 2. Fixtures and Setup

```python
@pytest.fixture
def sample_audio():
    """Provide test audio"""
    return create_test_audio()

def test_with_fixture(sample_audio):
    """Use fixture"""
    embedding = generate_embedding(sample_audio)
    assert embedding is not None
```

### 3. Assertions

✅ Good:
```python
assert embedding is not None
assert len(embedding) == 192
assert 0.9 < similarity <= 1.0
```

❌ Poor:
```python
assert embedding  # Too vague
assert len(embedding) > 0  # Not specific enough
```

### 4. Error Testing

```python
def test_error_handling():
    """Test error cases"""
    with pytest.raises(ValueError):
        create_enrollment_session_invalid_config()
```

### 5. Parameterized Tests

```python
@pytest.mark.parametrize("duration_ms", [100, 500, 1000, 5000])
def test_embedding_various_durations(duration_ms):
    """Test with multiple duration values"""
    audio = create_test_audio(duration_ms=duration_ms)
    embedding = generate_embedding(audio)
    assert embedding is not None
```

---

## Troubleshooting

### Common Issues

#### Issue: Import Errors
```
ModuleNotFoundError: No module named 'module_name'
```

**Solution:**
```bash
pip install -r requirements.txt
PYTHONPATH="${PYTHONPATH}:$(pwd)" python -m pytest
```

#### Issue: MongoDB Connection Failed
```
pymongo.errors.ServerSelectionTimeoutError
```

**Solution:**
```bash
# Ensure MongoDB is running
# For Windows: net start MongoDB
# For Linux: sudo systemctl start mongodb

# Or skip database tests
python -m pytest -m "not database"
```

#### Issue: Tests Fail Due to Missing Model
```
FileNotFoundError: pretrained model not found
```

**Solution:**
```bash
# Download models
python -c "from voice_embedding import get_model; get_model()"

# Or skip model-requiring tests
python -m pytest -m "not requires_model"
```

#### Issue: Tests Timeout

**Solution:**
```bash
# Increase timeout
python -m pytest --timeout=600

# Run without timing constraint
python -m pytest -m "not slow"
```

#### Issue: Parallel Test Failures

**Solution:**
```bash
# Run serially to debug
python -m pytest -n0  # or just python -m pytest

# Check for test interdependencies
```

### Debug Mode

```bash
# Show print statements and debug info
python -m pytest -s -v

# Drop into debugger on failure
python -m pytest --pdb

# Show local variables on failure
python -m pytest -l
```

---

## Test Results Reporting

### View Test Results

#### Terminal Report
```bash
python -m pytest -v
```

#### HTML Report
```bash
python -m pytest --html=report.html --self-contained-html
open report.html
```

#### JUnit XML Report
```bash
python -m pytest --junit-xml=report.xml
# Open in CI/CD system
```

#### JSON Report
```bash
python -m pytest --json-report --json-report-file=report.json
```

### Test Statistics

After running tests, you'll see:

```
=================== test session starts ====================
tests/test_suite_complete.py::TestVoiceEmbedding::
    test_embedding_generation_basic PASSED              [10%]
...
================== 45 passed in 2.35s =====================
```

- **PASSED**: Test succeeded
- **FAILED**: Test failed with assertion error
- **SKIPPED**: Test was skipped
- **XFAIL**: Expected failure
- **ERROR**: Test error (not assertion)

---

## Continuous Monitoring

### Watch Mode (requires pytest-watch)

```bash
pip install pytest-watch
ptw  # Reruns tests when files change
```

### Performance Monitoring

```bash
python -m pytest --benchmark-only
python -m pytest --benchmark-min-rounds=5
```

---

## Next Steps

1. Run quick smoke tests: `python run_tests.py --quick`
2. Run full test suite: `python run_tests.py --all`
3. Generate coverage report: `python run_tests.py --coverage`
4. Check specific module: `python run_tests.py --module embedding_operations`
5. Set up CI/CD integration

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Mock Testing Guide](https://docs.python.org/3/library/unittest.mock.html)

---

## Support

For issues or questions about testing:

1. Check this guide's troubleshooting section
2. Run tests with `-v -s` flags for debug output
3. Check test logs in `test_results.xml` or HTML reports
4. Verify all dependencies are installed: `pip list | grep pytest`

---

**Last Updated**: 2026-02-14
**Test Suite Version**: 1.0.0
**Python Version**: 3.9+
