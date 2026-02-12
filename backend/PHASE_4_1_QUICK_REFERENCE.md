# Phase 4.1 Testing - Quick Reference Guide

## Quick Start

### Run All Tests
```bash
# Python
cd c:\Users\manik.bhardwaj\.vscode\voice\
pytest

# JavaScript
cd c:\Users\manik.bhardwaj\.vscode\voice\reactapp\backend
npm test
```

### Run Specific Tests

**Python:**
```bash
# Run single test file
pytest test_voice_embedding_utils.py -v

# Run single test class
pytest test_database_utils.py::TestSaveUserDatabase -v

# Run single test function
pytest test_voice_embedding_utils.py::TestPreprocessAudio::test_preprocess_audio_mono_16khz -v

# With coverage
pytest --cov=. --cov-report=html
```

**JavaScript:**
```bash
# Run single test file
jest test_similarity_checker.test.js

# Run specific test suite
jest test_similarity_checker.test.js -t "SimilarityChecker - validateEmbedding"

# Watch mode
jest --watch

# With coverage
jest --coverage
```

## Test Files Overview

### Python Tests (Root Directory)

| File | Tests | Purpose |
|------|-------|---------|
| `test_voice_embedding_utils.py` | 20 | Audio preprocessing and embedding calculations |
| `test_database_utils.py` | 21 | Database operations and storage |
| `test_utilities.py` | - | Fixtures, mocks, helpers |

### JavaScript Tests (Backend Directory)

| File | Tests | Purpose |
|------|-------|---------|
| `test_similarity_checker.test.js` | 56 | Embedding comparison and validation |
| `test_utilities.js` | - | Fixtures, mocks, helpers |

## Utility Classes & Functions

### Python Utilities (test_utilities.py)

**EmbeddingFixtures**
```python
from test_utilities import EmbeddingFixtures

# Generate test embeddings
embedding = EmbeddingFixtures.valid_embedding_192d()
zero_emb = EmbeddingFixtures.zero_embedding_192d()
```

**AudioFixtures**
```python
from test_utilities import AudioFixtures

# Generate test audio
sine_wave = AudioFixtures.create_sine_wave_bytes(frequency=440)
noise = AudioFixtures.create_white_noise_bytes()
silent = AudioFixtures.create_silent_audio_bytes()
```

**MockDatabase**
```python
from test_utilities import MockDatabase

db = MockDatabase()
db.save_user("1234567890", embedding)
user = db.get_user("1234567890")
```

### JavaScript Utilities (test_utilities.js)

**EmbeddingFixtures**
```javascript
const { EmbeddingFixtures } = require('./test_utilities');

// Generate test embeddings
const embedding = EmbeddingFixtures.validEmbedding192d();
const unitVec = EmbeddingFixtures.unitVectorEmbedding();
```

**TestData**
```javascript
const { TestData } = require('./test_utilities');

// Get test cases
const cases = TestData.similarityTestCases();
const thresholds = TestData.thresholdTestCases();
```

**Performance Utilities**
```javascript
const { PerformanceUtils } = require('./test_utilities');

// Benchmark operation
const results = await PerformanceUtils.benchmark(async () => {
    return calculator.calculateSimilarity(emb1, emb2);
}, 1000);
```

## Common Test Patterns

### Python Test Pattern
```python
import pytest
from voice_embedding import preprocess_audio

class TestFeature:
    def test_happy_path(self):
        # Arrange
        audio_bytes = self.create_test_audio()
        
        # Act
        result = preprocess_audio(audio_bytes)
        
        # Assert
        assert isinstance(result, torch.Tensor)
    
    def test_error_handling(self):
        with pytest.raises(Exception):
            preprocess_audio(b"invalid")
```

### JavaScript Test Pattern
```javascript
const SimilarityChecker = require('./similarity-checker');

describe('Feature', () => {
    let checker;
    
    beforeEach(() => {
        checker = new SimilarityChecker();
    });
    
    test('happy path', () => {
        const embedding = Array(192).fill(0.5);
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(true);
    });
    
    test('error handling', () => {
        const result = checker.validateEmbedding(null);
        expect(result.isValid).toBe(false);
    });
});
```

## Configuration

### pytest.ini Settings
```ini
# Run specific markers
pytest -m unit              # Run only unit tests
pytest -m "embedding"       # Run embedding tests
pytest -m "not slow"        # Skip slow tests
```

### jest.config.js Settings
```javascript
// Run specific test suites
jest --testNamePattern="validateEmbedding"

// Run with custom coverage threshold
jest --coverage --collectCoverageFrom="*.js"
```

## Troubleshooting

### Python Tests
| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Run `pip install -r requirements.txt` |
| Import errors | Set PYTHONPATH or use `pytest` from project root |
| Torch not available | Install PyTorch: `pip install torch torchaudio` |
| MongoDB connection errors | Tests use mocks, no actual MongoDB needed |

### JavaScript Tests
| Issue | Solution |
|-------|----------|
| jest not found | Run `npm install` in backend directory |
| Module not found | Check relative paths in `jest.config.js` |
| Test timeout | Increase timeout: `jest --testTimeout=30000` |

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Python tests
        run: pytest --cov=. --cov-report=xml
      - name: Setup Node
        uses: actions/setup-node@v2
      - name: Run JS tests
        run: npm test -- --coverage
```

## Writing New Tests

### Python Test Template
```python
import pytest
from module import function_to_test
from test_utilities import EmbeddingFixtures

class TestNewFeature:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.fixtures = EmbeddingFixtures()
    
    def test_new_case(self):
        # Arrange
        input_data = self.fixtures.valid_embedding_192d()
        
        # Act
        result = function_to_test(input_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, expected_type)
```

### JavaScript Test Template
```javascript
const { EmbeddingFixtures, Assertions } = require('./test_utilities');

describe('New Feature', () => {
    test('new case', () => {
        // Arrange
        const embedding = EmbeddingFixtures.validEmbedding192d();
        
        // Act
        const result = performOperation(embedding);
        
        // Assert
        expect(result).toBeDefined();
        Assertions.assertValid192dEmbedding(result);
    });
});
```

## Coverage Reports

### Generate Python Coverage
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html
```

### Generate JavaScript Coverage
```bash
npm run test:coverage
# Open coverage/lcov-report/index.html
```

## Performance Testing

### Python Performance
```python
from test_utilities import MetricsCollector

metrics = MetricsCollector()

for i in range(1000):
    start = time.time()
    result = calculate_similarity(emb1, emb2)
    elapsed = time.time() - start
    metrics.record_metric('similarity_calc', elapsed)

print(f"Average: {metrics.get_average('similarity_calc')}ms")
```

### JavaScript Performance
```javascript
const { PerformanceUtils } = require('./test_utilities');

const results = await PerformanceUtils.benchmark(
    () => checker.calculateSimilarity(emb1, emb2),
    1000,
    'Similarity Calculation'
);

console.log(`Average: ${results.avg}ms`);
```

## Resources

- **Documentation:** [PHASE_4_1_TESTING_GUIDE.md](./PHASE_4_1_TESTING_GUIDE.md)
- **Pytest Docs:** https://docs.pytest.org/
- **Jest Docs:** https://jestjs.io/
- **Test Coverage:** Configured in `pytest.ini` and `jest.config.js`

## Support

For issues or questions:
1. Check test output for specific errors
2. Review test utilities for helper functions
3. Refer to individual test files for patterns
4. Check configuration files for settings
