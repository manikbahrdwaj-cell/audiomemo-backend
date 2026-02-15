# Edge Case Testing - Quick Reference

## 🚀 Quick Start (2 minutes)

### Install Dependencies
```bash
cd backend
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests
```bash
python run_edge_case_tests.py --all
```

### Run Specific Category
```bash
python run_edge_case_tests.py --category audio_chunking
python run_edge_case_tests.py --category embeddings
python run_edge_case_tests.py --category matching_logic
python run_edge_case_tests.py --category enrollment
python run_edge_case_tests.py --category database
python run_edge_case_tests.py --category websocket
```

### Quick Tests Only
```bash
python run_edge_case_tests.py --quick
```

---

## 📁 Test Files Overview

### 1. `test_edge_cases_audio_chunking.py`
**Purpose:** Audio segmentation boundary conditions  
**Tests:** 68  
**Key Classes:**
- `TestAudioChunkingEdgeCases` - Chunking scenarios
- `TestChunkAggregation` - Chunk combination

**Critical Tests:**
- `test_empty_audio_array` - Empty input handling
- `test_audio_with_nan_values` - NaN detection
- `test_zero_overlap` / `test_maximum_overlap` - Overlap validation

---

### 2. `test_edge_cases_embeddings.py`
**Purpose:** Embedding generation and similarity  
**Tests:** 72  
**Key Classes:**
- `TestEmbeddingGenerationEdgeCases` - Generation scenarios
- `TestEmbeddingSimilarityEdgeCases` - Similarity calculations
- `TestEmbeddingBatchProcessingEdgeCases` - Batch operations
- `TestEmbeddingAggregationEdgeCases` - Aggregation strategies

**Critical Tests:**
- `test_empty_audio_embedding` - No-input handling
- `test_identical_embeddings_similarity` - Perfect match (should be 1.0)
- `test_embedding_finite_values` - Numerical stability

---

### 3. `test_edge_cases_matching_logic.py`
**Purpose:** Similarity scoring and thresholds  
**Tests:** 65  
**Key Classes:**
- `TestMatchingLogicEdgeCases` - Matching scenarios
- `TestMatchingStrategyEdgeCases` - Strategy comparison

**Critical Tests:**
- `test_perfect_match_identical_embeddings` - 100% similarity
- `test_threshold_boundary_*` - Threshold edge cases
- `test_batch_matching_*` - Batch matching scenarios

---

### 4. `test_edge_cases_enrollment.py`
**Purpose:** Enrollment workflow edge cases  
**Tests:** 78  
**Key Classes:**
- `TestEnrollmentSessionEdgeCases` - Session management
- `TestEnrollmentValidationEdgeCases` - Data validation

**Critical Tests:**
- `test_create_enrollment_with_empty_user_id` - ID validation
- `test_max_chunks_*` - Chunk limit enforcement
- `test_add_empty_audio_chunk` - Empty chunk rejection

---

### 5. `test_edge_cases_database.py`
**Purpose:** Database operation safety  
**Tests:** 82  
**Key Classes:**
- `TestDatabaseEdgeCases` - Database operations
- `TestDatabaseTransactionEdgeCases` - Transaction handling

**Critical Tests:**
- `test_lookup_user_null_id` - Null ID handling
- `test_store_embedding_with_nan` - NaN rejection
- `test_concurrent_writes_same_user` - Concurrency safety

---

### 6. `test_edge_cases_websocket.py`
**Purpose:** WebSocket communication safety  
**Tests:** 75  
**Key Classes:**
- `TestWebSocketEdgeCases` - Connection & messaging
- `TestWebSocketAuthenticationEdgeCases` - Authentication

**Critical Tests:**
- `test_connection_immediate_disconnect` - Lifecycle
- `test_send_invalid_json` - Format validation
- `test_audio_chunk_missing_data` - Required fields

---

## 🧪 Test Execution Options

### By Scope
```bash
python run_edge_case_tests.py --all              # All tests
python run_edge_case_tests.py --quick            # Essential only
python run_edge_case_tests.py --category <name>  # Specific category
```

### By Output
```bash
python run_edge_case_tests.py --all --verbose    # Detailed output
python run_edge_case_tests.py --all --json-report  # JSON results
python run_edge_case_tests.py --list             # List all tests
```

### By Coverage
```bash
python run_edge_case_tests.py --all --coverage   # Coverage report
pytest --cov=. test_edge_cases_*.py              # Direct pytest
```

### Direct pytest
```bash
pytest test_edge_cases_audio_chunking.py -v      # Single file
pytest test_edge_cases_embeddings.py::TestEmbeddingGenerationEdgeCases -v  # Class
pytest -k "test_empty" -v                         # By name pattern
pytest -x -v                                      # Stop on first failure
```

---

## 📊 Test Summary

| Category | Tests | Focus Areas |
|----------|-------|-------------|
| **Audio Chunking** | 68 | Empty input, extreme values, sample rates, overlap, windowing |
| **Embeddings** | 72 | Empty audio, special signals, data types, similarity, aggregation |
| **Matching Logic** | 65 | Thresholds, similarity ranges, batch matching, metrics |
| **Enrollment** | 78 | IDs, timeouts, chunks, quality, finalization |
| **Database** | 82 | User lookup, storage, retrieval, matching, transactions |
| **WebSocket** | 75 | Connections, messages, formats, authentication, recovery |
| **TOTAL** | **440** | Comprehensive system validation |

---

## ✅ Expected Outcomes

**All Tests Should Pass ✓**

### Audio Chunking
- ✓ Handles empty/null inputs
- ✓ Produces consistent chunks
- ✓ Validates configuration
- ✓ Supports various sample rates

### Embeddings
- ✓ Generates valid embeddings
- ✓ All values finite (no NaN/Inf)
- ✓ Consistent for identical input
- ✓ Proper dimension handling

### Matching Logic
- ✓ Similarity in [-1, 1] range
- ✓ Symmetric results
- ✓ Proper thresholds
- ✓ Edge case handling

### Enrollment
- ✓ Validates user IDs
- ✓ Enforces limits
- ✓ Respects timeouts
- ✓ Handles errors gracefully

### Database
- ✓ Atomic transactions
- ✓ Thread-safe operations
- ✓ Data integrity checks
- ✓ Consistent retrieval

### WebSocket
- ✓ Message validation
- ✓ Connection lifecycle
- ✓ Error recovery
- ✓ Concurrent handling

---

## 🔍 Common Test Patterns

### 1. **Null/Empty Input Testing**
```python
def test_null_input(self):
    """Test handling of null/empty values"""
    result = operation(None)
    assert result is None or result == False
```

### 2. **Boundary Value Testing**
```python
def test_boundary_threshold(self):
    """Test exactly at threshold"""
    similarity = 0.8
    assert self._should_match(similarity, threshold=0.8)
```

### 3. **Invalid Input Testing**
```python
def test_invalid_format(self):
    """Test rejection of invalid formats"""
    try:
        result = operation(invalid_input)
        assert result is None or result == False
    except (ValueError, TypeE rror):
        pass  # Expected
```

### 4. **Edge Value Testing**
```python
def test_extreme_values(self):
    """Test with extreme values"""
    for val in [0, 1, -1, 1e10, 1e-10, np.inf, np.nan]:
        result = operation(val)
        # Validate result
```

### 5. **Special Case Testing**
```python
def test_special_signal(self):
    """Test with special signal types"""
    audio = generate_chirp() # or sine, square, noise, etc.
    result = operation(audio)
    assert result is not None
```

---

## 🐛 Troubleshooting

### Tests Fail with Import Errors
```bash
# Install missing dependencies
pip install -r requirements-test.txt
pip install -r requirements.txt
```

### Tests Timeout
```bash
# Increase timeout
pytest --timeout=600 test_edge_cases_*.py
```

### Out of Memory
```bash
# Run tests sequentially (not parallel)
pytest test_edge_cases_*.py  # Remove -n auto
```

### Model Not Found
```bash
# Download model
python -c "from voice_embedding import get_model; get_model()"
```

### Database Connection Failed
```bash
# Start MongoDB
mongod
# Or check .env for connection string
cat .env | grep MONGO
```

---

## 📈 Performance Expectations

| Operation | Timeout | Notes |
|-----------|---------|-------|
| Single category test | 60-90s | 60-80 tests |
| All tests quick | 10-15s | 20-25 essential tests |
| All tests full | 5-10 min | 440 tests |
| With coverage | 10-15 min | Includes coverage report |

---

## 🎯 Test Execution Workflow

### Pre-Commit Check
```bash
python run_edge_case_tests.py --quick
```

### Development Testing
```bash
python run_edge_case_tests.py --category <changed_module>
```

### Full Validation
```bash
python run_edge_case_tests.py --all --coverage
```

### CI/CD Pipeline
```bash
python run_edge_case_tests.py --all --json-report
# Push results to artifact storage
```

---

## 📚 Key Concepts

### Edge Case Types

1. **Boundary Conditions** - Min/max values, 0, empty, null
2. **Type Variations** - Different data types, encodings, formats
3. **Extreme Values** - Very large/small numbers, infinity, NaN
4. **Special Patterns** - Silence, noise, structured signals
5. **Concurrent Access** - Race conditions, deadlocks, consistency
6. **Resource Limits** - Memory exhaustion, timeout, overflow
7. **Invalid Input** - Malformed data, wrong types, security threats
8. **Error Conditions** - Expected failures, recovery paths

### Test Independence

Each test should:
- ✓ Not depend on other tests
- ✓ Clean up resources (isolation)
- ✓ Be deterministic (same result every run)
- ✓ Test one thing (single responsibility)

### Assertion Best Practices

```python
# ✓ Good - Specific and clear
assert len(chunks) == 2
assert np.isclose(similarity, 1.0, atol=1e-5)
assert result is None or result.get('success') == True

# ✗ Bad - Too broad or unclear
assert chunks  # Could be anything truthy
assert similarity  # Not verifying correctness
assert result  # Vague assertion
```

---

## 📞 Support

**For Test Failures:**
1. Read test name (describes what's tested)
2. Check test comments (why it matters)
3. Review assertion (what's expected)
4. Run with `--verbose` flag for details
5. Check system logs for errors

**Common Failure Causes:**
- Missing dependencies → Install requirements
- Model not loaded → Run download script
- Database not running → Start MongoDB
- Wrong working directory → cd to backend/
- Timeout → Increase timeout or clear resources

---

## 🔗 Related Documentation

- `EDGE_CASE_TESTING_GUIDE.md` - Comprehensive guide
- `TESTING_GUIDE_COMPREHENSIVE.md` - General testing info
- `README.md` - System overview
- `APP_ARCHITECTURE.md` - System architecture

---

**Last Updated:** February 2026  
**Status:** ✓ Ready for Use  
**Test Coverage:** 440+ edge cases across 6 categories
