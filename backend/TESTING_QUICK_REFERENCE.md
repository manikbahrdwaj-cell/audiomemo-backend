# Testing Quick Reference Guide

## Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

## Running Tests - Quick Commands

### Absolute Basics
```bash
# Run all tests
python -m pytest test_suite_complete.py -v

# Run with coverage
python -m pytest test_suite_complete.py --cov=. --cov-report=html

# Use runner script (easier)
python run_tests.py --all
```

### Quick Test Runs
```bash
# Smoke tests (< 5 seconds)
python run_tests.py --quick

# Fast tests only (exclude slow)
python run_tests.py --fast

# Specific category
python -m pytest -m unit -v          # Unit tests
python -m pytest -m integration -v   # Integration tests
python -m pytest -m performance -v   # Performance tests
python -m pytest -m embedding -v     # Embedding tests
```

### Focused Testing
```bash
# Specific test file
python -m pytest test_suite_complete.py -v

# Specific test class
python -m pytest test_suite_complete.py::TestVoiceEmbedding -v

# Specific test function
python -m pytest test_suite_complete.py::TestVoiceEmbedding::test_embedding_generation_basic -v

# Shorthand
pytest test_suite_complete.py::TestVoiceEmbedding::test_embedding_generation_basic -v
```

### Advanced Execution
```bash
# Parallel execution (4 workers)
python run_tests.py --parallel 4

# With output file
python run_tests.py --output results.txt

# Generate HTML report
python run_tests.py --html

# Generate JUnit XML
python run_tests.py --junit test_results.xml

# With coverage
python run_tests.py --coverage
```

## Coverage Report

```bash
# Generate and view coverage
python run_tests.py --coverage
open htmlcov/index.html           # macOS
start htmlcov/index.html          # Windows
xdg-open htmlcov/index.html       # Linux
```

## Test Markers

```bash
# Run tests with specific marker
pytest -m unit              # Unit tests
pytest -m integration       # Integration tests  
pytest -m embedding         # Embedding tests
pytest -m enrollment        # Enrollment tests
pytest -m performance       # Performance tests
pytest -m slow              # Slow tests

# Exclude certain tests
pytest -m "not slow"        # Exclude slow tests
pytest -m "not performance" # Exclude performance tests
```

## Debugging Tests

```bash
# Show print statements
pytest -s test_suite_complete.py

# Show local variables on failure
pytest -l test_suite_complete.py

# Drop into debugger on failure
pytest --pdb test_suite_complete.py

# Increased verbosity
pytest -v -s test_suite_complete.py

# Show test collection
pytest --collect-only test_suite_complete.py
```

## Available Test Classes

```
TestVoiceEmbedding         - Embedding generation, similarity
TestDatabase               - Database operations (mocked)
TestAudioChunking          - Audio chunking and configuration
TestEmbeddingOperations    - Audio merging and advanced ops
TestMatchingLogic          - Matching strategies and scoring
TestEnrollmentService      - Enrollment session management
TestWebSocketHandler       - WebSocket connection handling
TestWebSocketRouter        - WebSocket message routing
TestIntegration            - End-to-end pipelines
TestEdgeCases              - Error handling and edge cases
TestPerformance            - Performance benchmarking
TestCompatibility          - Framework compatibility
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Import errors | `pip install -r requirements-test.txt` |
| MongoDB not found | `pytest -m "not database"` |
| Tests timeout | `pytest --timeout=600` |
| Module not found | `PYTHONPATH="${PYTHONPATH}:$(pwd)" pytest` |
| Tests fail randomly | Run serially: `pytest -n0` |

## Test Structure

```
test_suite_complete.py
├── Fixtures (AudioTestData, test_embeddings, etc.)
├── TestVoiceEmbedding
│   ├── test_embedding_generation_basic
│   ├── test_embedding_normalization
│   ├── test_similarity_calculation
│   └── ...
├── TestDatabase
├── TestAudioChunking
├── TestMatchingLogic
├── TestEnrollmentService
├── TestIntegration
├── TestEdgeCases
├── TestPerformance
└── TestCompatibility
```

## Useful Pytest Options

```bash
pytest -v        # Verbose output
pytest -q        # Quiet output
pytest -s        # Show print statements
pytest -x        # Stop on first failure
pytest --maxfail=3  # Stop after 3 failures
pytest -l        # Show local variables
pytest --tb=short   # Short traceback format
pytest --tb=long    # Long traceback format
pytest -r a      # Show all test summary
pytest --co      # Collect only (show tests, don't run)
```

## Performance Testing

```bash
# Time how long tests take
pytest --durations=10 test_suite_complete.py
pytest --benchmark-disable  # Disable benchmarks

# Show slowest tests
pytest --durations=5
```

## Fixture Usage

```python
# Use in test
def test_with_audio(clean_audio):
    embedding = generate_embedding(clean_audio)
    assert embedding is not None

# Available fixtures
clean_audio           # Sine wave audio
noisy_audio          # Mixed audio
long_audio           # 10 seconds
short_audio          # 100ms
random_embedding     # Single embedding
embedding_batch      # Multiple embeddings
identical_embeddings # For similarity tests
audio_generator      # Audio utility
measure_time         # Performance timer
mock_mongodb         # Mocked database
```

## Runner Script Commands

```bash
python run_tests.py --help       # Show all options
python run_tests.py --all        # Run all tests
python run_tests.py --quick      # Smoke tests
python run_tests.py --fast       # Exclude slow
python run_tests.py --coverage   # With coverage
python run_tests.py --marker integration  # By marker
python run_tests.py --module embedding_operations  # By module
python run_tests.py --specific "test_file.py::TestClass::test_func"
python run_tests.py --parallel 4  # Parallel execution
python run_tests.py --html       # HTML report
python run_tests.py --junit results.xml  # JUnit report
```

## Test Results

### Successful Run
```
====================== test session starts =======================
collected 95 items

test_suite_complete.py::TestVoiceEmbedding::test_embedding_generation_basic PASSED [1%]
...
test_suite_complete.py::TestCompatibility::test_scipy_compatibility PASSED [100%]

======================== 95 passed in 15.23s ======================
```

### With Coverage
```
TOTAL  ................................ 85%
```

### Failed Test
```
FAILED test_suite_complete.py::TestVoiceEmbedding::test_embedding_generation_basic
AssertionError: assert None is not None
```

## Report Locations

- **HTML Coverage**: `htmlcov/index.html`
- **JUnit XML**: `test_results.xml`
- **HTML Report**: `test_results.html`
- **Text Output**: `test_results.txt` (if saved)

## Writing a New Test

```python
@pytest.mark.unit  # Add marker
def test_my_feature(self, clean_audio):  # Use fixture
    """Test description"""
    # Arrange
    expected = 192
    
    # Act
    result = some_function(clean_audio)
    
    # Assert
    assert result is not None
    assert len(result) == expected
```

## CI/CD Integration

### GitHub Actions
```yaml
- run: python -m pytest test_suite_complete.py --cov=.
```

### GitLab CI
```yaml
- python -m pytest test_suite_complete.py --junit-xml=report.xml
```

---

## Quick Help

```bash
# All available pytest help
pytest --help

# Help for specific option
pytest --fixtures  # Show available fixtures
pytest --markers   # Show available markers
pytest --version   # Show pytest version
pytest --setup-only  # Show what fixtures will be used
```

---

**Last Updated**: 2026-02-14  
**Framework**: pytest 7.0+
**Status**: Ready to Use
