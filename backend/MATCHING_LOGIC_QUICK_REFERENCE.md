# MATCHING LOGIC - QUICK REFERENCE

Fast-track guide to advanced matching strategies for voice verification.

## 5-Minute Setup

### 1. Basic Usage

```python
from matching_logic import MatchingComparator, MatchingStrategy
import numpy as np

# Initialize
comparator = MatchingComparator(
    primary_strategy=MatchingStrategy.COSINE,
    similarity_threshold=0.85
)

# Compare embeddings
reference = np.random.randn(192).astype(np.float32)
test = reference + np.random.randn(192).astype(np.float32) * 0.1

score = comparator.compare_embeddings(reference, test)

# Check result
if score.matching_result.value == "strong_match":
    print("✓ Verified!")
print(f"Confidence: {score.confidence:.4f}")
```

### 2. With Verification Service

```python
from verification_service import (
    get_verification_manager,
    VerificationSessionConfig
)

config = VerificationSessionConfig(
    matching_strategy='hybrid',
    use_advanced_matching=True,
    similarity_threshold=0.85
)

manager = get_verification_manager(config)
```

## Strategies at a Glance

| Strategy | Best For | Speed | Strictness |
|----------|----------|-------|-----------|
| **COSINE** | General voice verification | ⚡⚡⚡ | Medium |
| **EUCLIDEAN** | Magnitude changes | ⚡⚡ | Medium |
| **CORRELATION** | Pattern matching | ⚡⚡ | Medium |
| **CHEBYSHEV** | Security-critical | ⚡⚡⚡ | High |
| **HYBRID** | Production systems | ⚡ | Balanced |
| **STATISTICAL** | Distribution testing | ⚡⚡ | Medium |
| **ADAPTIVE** | Unknown data | ⚡⚡⚡ | Dynamic |

## Common Tasks

### Task 1: Compare Embeddings

```python
score = comparator.compare_embeddings(reference, test)
print(f"Score: {score.final_score:.4f}")
print(f"Result: {score.matching_result.value}")
```

### Task 2: Try Multiple Strategies

```python
for strategy in [
    MatchingStrategy.COSINE,
    MatchingStrategy.HYBRID,
    MatchingStrategy.ADAPTIVE
]:
    score = comparator.compare_embeddings(reference, test, strategy=strategy)
    print(f"{strategy.value}: {score.final_score:.4f}")
```

### Task 3: Get Detailed Metrics

```python
score = comparator.compare_embeddings(reference, test)
metrics = score.metrics

print(f"Cosine Similarity: {metrics.cosine_similarity:.4f}")
print(f"Euclidean Distance: {metrics.euclidean_distance:.4f}")
print(f"Vector Angle: {metrics.vector_angle_degrees:.2f}°")
```

### Task 4: Compare Multiple Chunks

```python
refs = [np.random.randn(192).astype(np.float32) for _ in range(3)]
tests = [r + np.random.randn(192).astype(np.float32) * 0.1 for r in refs]

result = comparator.compare_embedding_lists(
    refs, tests,
    matching_strategy='best_match'
)

print(f"Overall Score: {result['overall_score']:.4f}")
```

### Task 5: Custom Weights for Hybrid

```python
custom_weights = {
    MatchingStrategy.COSINE: 0.60,
    MatchingStrategy.EUCLIDEAN: 0.15,
    MatchingStrategy.CORRELATION: 0.15,
    MatchingStrategy.CHEBYSHEV: 0.05,
    MatchingStrategy.STATISTICAL: 0.05
}

comparator.set_strategy_weights(custom_weights)
```

### Task 6: Use Different Strategies in Verification

```python
# Get strategy comparison
comparison = manager.get_strategy_comparison(session.session_id)

for strategy, result in comparison['strategy_results'].items():
    print(f"{strategy}: {result['score']:.4f}")
```

## Result Interpretation

### Matching Result Values

- **strong_match**: Score > threshold + 0.10 (high confidence)
- **weak_match**: threshold <= score <= threshold + 0.10 (borderline)
- **no_match**: Score < threshold (rejected)
- **inconclusive**: Insufficient data
- **error**: Processing error

### Confidence Levels

- 0.90-1.00: Very High (✓✓✓ Production-ready)
- 0.70-0.89: Good (✓✓ Acceptable)
- 0.50-0.69: Medium (✓ Marginal)
- Below 0.50: Low (✗ Unreliable)

## Threshold Guidelines

| Use Case | Threshold | Strategy |
|----------|-----------|----------|
| Banking/Finance | 0.90-0.95 | HYBRID or CHEBYSHEV |
| General Voice Auth | 0.85-0.90 | HYBRID (default) |
| User-Friendly App | 0.75-0.85 | ADAPTIVE or COSINE |
| Security Critical | 0.95+ | CHEBYSHEV |
| Unknown Data | 0.85 | ADAPTIVE |

## Performance Tips

1. **Speed**: Use COSINE for fastest comparison
2. **Accuracy**: Use HYBRID for best overall performance
3. **Robustness**: Use ADAPTIVE for varying data
4. **Security**: Use CHEBYSHEV for strictest matching

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Low scores | Verify embedding quality and normalization |
| Inconsistent results | Use HYBRID strategy, check confidence |
| Too many rejections | Lower threshold or use ADAPTIVE |
| Too many false acceptances | Raise threshold or use CHEBYSHEV |

## Class Hierarchy

```
MatchingComparator
├─ compare_embeddings()
├─ compare_embedding_lists()
└─ set_strategy_weights()

MatchingScore
├─ final_score: float
├─ matching_result: MatchingResult
├─ confidence: float
├─ metrics: MatchingMetrics
└─ metadata: Dict

MatchingMetrics
├─ cosine_similarity
├─ euclidean_distance
├─ vector_angle_degrees
└─ ... 7 more metrics

MatchingStrategy (Enum)
├─ COSINE
├─ EUCLIDEAN
├─ CORRELATION
├─ CHEBYSHEV
├─ HYBRID
├─ STATISTICAL
└─ ADAPTIVE

MatchingResult (Enum)
├─ STRONG_MATCH
├─ WEAK_MATCH
├─ NO_MATCH
├─ INCONCLUSIVE
└─ ERROR
```

## Integration Checklist

- [ ] Import MatchingComparator and MatchingStrategy
- [ ] Initialize comparator with desired strategy
- [ ] Create VerificationSessionConfig with `use_advanced_matching=True`
- [ ] Pass config to get_verification_manager()
- [ ] Verify using manager.verify() with advanced matching
- [ ] Check matching_score and confidence in results
- [ ] Implement error handling for ERROR result status
- [ ] Test with different strategies for your use case
- [ ] Calibrate threshold based on false positive/negative rates
- [ ] Monitor confidence scores in production

## One-Liners

```python
# Quick comparison
score = MatchingComparator().compare_embeddings(ref, test)

# With specific strategy
score = MatchingComparator().compare_embeddings(ref, test, strategy=MatchingStrategy.HYBRID)

# All metrics
metrics = MatchingComparator().compare_embeddings(ref, test).metrics.to_dict()

# Multiple embeddings
result = MatchingComparator().compare_embedding_lists(refs, tests)

# Adaptive matching
score = MatchingComparator(MatchingStrategy.ADAPTIVE).compare_embeddings(ref, test)
```

## Common Errors

**Error: "Invalid embeddings"**
- Check embedding dimensions match (should be 192)
- Verify no NaN or Inf values
- Ensure arrays are numpy float32

**Error: "Weights must sum to 1.0"**
- Verify custom weights sum to exactly 1.0
- Use `sum(weights.values())` to check

**Error: "Unknown strategy"**
- Use MatchingStrategy enum values
- Valid: COSINE, EUCLIDEAN, CORRELATION, CHEBYSHEV, HYBRID, STATISTICAL, ADAPTIVE

## Links

- [Full API Reference](MATCHING_LOGIC_API_REFERENCE.md)
- [Examples](matching_logic_examples.py)
- [Test Suite](test_matching_logic.py)
- [Verification Service Integration](VERIFICATION_SERVICE_API_REFERENCE.md)
