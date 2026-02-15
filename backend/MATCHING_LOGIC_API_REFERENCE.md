# MATCHING LOGIC - API REFERENCE
Advanced Matching Strategies for Voice Verification

## Overview

The Matching Logic module provides sophisticated embedding comparison capabilities for voice verification with multiple matching strategies, confidence scoring, and comprehensive metrics calculation.

**Key Features:**
- 7 different matching strategies (cosine, euclidean, correlation, chebyshev, hybrid, statistical, adaptive)
- Confidence scoring based on metric consistency
- Comprehensive distance/similarity metrics
- Multi-embedding comparison support
- Adaptive thresholds based on data characteristics
- Error handling and validation
- Singleton pattern for efficient resource usage

## Installation

```python
# Import matching logic components
from matching_logic import (
    MatchingComparator,
    MatchingStrategy,
    MatchingResult,
    MatchingScore,
    MatchingMetrics,
    get_matching_comparator
)
```

## Enums

### MatchingStrategy

Available matching strategies for embedding comparison.

**Values:**
- `COSINE` - Cosine similarity (default, recommended for normalized embeddings)
- `EUCLIDEAN` - Euclidean distance (good for absolute differences)
- `CORRELATION` - Correlation-based matching (pattern matching)
- `CHEBYSHEV` - Chebyshev distance (maximum of absolute differences)
- `HYBRID` - Weighted combination of multiple strategies
- `STATISTICAL` - Statistical test-based matching (KS test)
- `ADAPTIVE` - Adaptive thresholding based on embedding variance

### MatchingResult

Result status of embedding comparison.

**Values:**
- `STRONG_MATCH` - High confidence match (score > threshold + 0.10)
- `WEAK_MATCH` - Borderline match (score >= threshold but < threshold + 0.10)
- `NO_MATCH` - Clear mismatch (score < threshold)
- `INCONCLUSIVE` - Insufficient data for decision
- `ERROR` - Processing error or invalid input

## Core Classes

### MatchingComparator

Main class for comparing embeddings with advanced matching strategies.

**Constructor:**
```python
MatchingComparator(
    primary_strategy: MatchingStrategy = MatchingStrategy.COSINE,
    similarity_threshold: float = 0.85,
    confidence_threshold: float = 0.70
)
```

**Parameters:**
- `primary_strategy`: Default matching strategy to use
- `similarity_threshold`: Threshold for positive match decision (0.0-1.0)
- `confidence_threshold`: Minimum confidence for reliable decisions (0.0-1.0)

**Example:**
```python
from matching_logic import MatchingComparator, MatchingStrategy

comparator = MatchingComparator(
    primary_strategy=MatchingStrategy.HYBRID,
    similarity_threshold=0.85
)
```

### MatchingScore

Complete matching result with scores, metrics, and confidence.

**Attributes:**
- `primary_score` (float): Score from primary strategy
- `final_score` (float): Final computed score
- `matching_result` (MatchingResult): Match status
- `strategy_used` (MatchingStrategy): Strategy applied
- `confidence` (float): Confidence level (0.0-1.0)
- `metrics` (MatchingMetrics): Comprehensive distance metrics
- `metadata` (Dict): Additional details and strategy-specific info
- `match_id` (str): Unique identifier for this matching
- `timestamp` (datetime): When comparison was performed

**Methods:**
```python
score.to_dict() -> Dict[str, Any]
# Convert to serializable dictionary
```

### MatchingMetrics

Comprehensive metrics for embedding comparison.

**Attributes:**
- `cosine_similarity`: Cosine similarity score (0.0-1.0)
- `euclidean_distance`: Euclidean distance between embeddings
- `correlation_distance`: Correlation distance
- `chebyshev_distance`: Chebyshev distance (max absolute difference)
- `entropy_distance`: Entropy distance between distributions
- `wasserstein_distance`: Wasserstein distance
- `statistical_p_value`: KS test p-value
- `vector_magnitude_ratio`: Ratio of test to reference magnitude
- `vector_angle_degrees`: Angle between vectors in degrees
- `embedding_norm_difference`: Difference in norms

**Methods:**
```python
metrics.to_dict() -> Dict[str, float]
# Convert all metrics to dictionary
```

## Methods

### compare_embeddings

Compare two embeddings using specified strategy.

```python
score = comparator.compare_embeddings(
    reference_embedding: np.ndarray,
    test_embedding: np.ndarray,
    strategy: Optional[MatchingStrategy] = None
) -> MatchingScore
```

**Parameters:**
- `reference_embedding`: Reference embedding (192-dimensional)
- `test_embedding`: Test/verification embedding (192-dimensional)
- `strategy`: Optional strategy override (uses primary_strategy if None)

**Returns:**
- `MatchingScore` with comparison results

**Example:**
```python
import numpy as np

reference = np.random.randn(192).astype(np.float32)
test = reference + np.random.randn(192).astype(np.float32) * 0.1

score = comparator.compare_embeddings(
    reference_embedding=reference,
    test_embedding=test,
    strategy=MatchingStrategy.HYBRID
)

print(f"Score: {score.final_score:.4f}")
print(f"Result: {score.matching_result.value}")
print(f"Confidence: {score.confidence:.4f}")
```

### compare_embedding_lists

Compare multiple embeddings (useful for chunk-based verification).

```python
result = comparator.compare_embedding_lists(
    reference_embeddings: List[np.ndarray],
    test_embeddings: List[np.ndarray],
    matching_strategy: str = 'best_match'
) -> Dict[str, Any]
```

**Parameters:**
- `reference_embeddings`: List of reference embeddings
- `test_embeddings`: List of test embeddings
- `matching_strategy`: Comparison strategy
  - `'best_match'`: Use maximum similarity (best case)
  - `'all_match'`: Use minimum similarity (worst case)
  - `'weighted'`: Use mean similarity

**Returns:**
- Dictionary with:
  - `overall_score`: Final score from strategy
  - `individual_scores`: Per-embedding scores
  - `mean_score`: Mean across all comparisons
  - `max_score`: Maximum score
  - `min_score`: Minimum score
  - `std_dev`: Standard deviation

**Example:**
```python
# 3 chunks each
references = [np.random.randn(192).astype(np.float32) for _ in range(3)]
tests = [ref + np.random.randn(192).astype(np.float32) * 0.1 for ref in references]

result = comparator.compare_embedding_lists(
    references, tests,
    matching_strategy='best_match'
)

print(f"Overall Score (best): {result['overall_score']:.4f}")
print(f"Mean Score: {result['mean_score']:.4f}")
```

### set_strategy_weights

Customize weights for hybrid matching strategy.

```python
comparator.set_strategy_weights(weights: Dict[MatchingStrategy, float])
```

**Parameters:**
- `weights`: Dictionary mapping strategies to weights
  - Must sum to 1.0
  - Example: `{COSINE: 0.4, EUCLIDEAN: 0.3, ...}`

**Example:**
```python
from matching_logic import MatchingStrategy

# Emphasize cosine similarity
custom_weights = {
    MatchingStrategy.COSINE: 0.60,
    MatchingStrategy.EUCLIDEAN: 0.15,
    MatchingStrategy.CORRELATION: 0.15,
    MatchingStrategy.CHEBYSHEV: 0.05,
    MatchingStrategy.STATISTICAL: 0.05
}

comparator.set_strategy_weights(custom_weights)
```

## Strategies Guide

### COSINE Strategy
**Best for:** General-purpose voice verification with normalized embeddings

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.COSINE
)
```

- Fast computation
- Works well with normalized embeddings
- Recommended for voice embeddings
- Default strategy

### EUCLIDEAN Strategy
**Best for:** Detecting magnitude changes and absolute differences

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.EUCLIDEAN
)
```

- Sensitive to magnitude variations
- Useful for quality assessment
- More computationally intensive than cosine

### CORRELATION Strategy
**Best for:** Pattern-based matching

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.CORRELATION
)
```

- Focuses on pattern similarity
- Invariant to linear scaling
- Good for comparing shapes of embeddings

### CHEBYSHEV Strategy
**Best for:** Maximum similarity guarantee

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.CHEBYSHEV
)
```

- Uses maximum absolute difference
- Stricter matching requirement
- Useful for security-critical applications

### HYBRID Strategy
**Best for:** Balanced, robust matching with multiple perspectives

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.HYBRID
)
```

- Combines 5 different metrics
- Configurable weights
- Default weights: Cosine(0.4), Euclidean(0.2), Correlation(0.2), Chebyshev(0.1), Statistical(0.1)
- Recommended for production systems

### STATISTICAL Strategy
**Best for:** Distribution-based comparison

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.STATISTICAL
)
```

- Uses Kolmogorov-Smirnov test
- Tests if distributions are different
- Combines KS test with cosine similarity

### ADAPTIVE Strategy
**Best for:** Data-driven adjustments

```python
score = comparator.compare_embeddings(
    reference, test,
    strategy=MatchingStrategy.ADAPTIVE
)
```

- Automatically adjusts threshold based on variance
- Higher variance → lower threshold (more lenient)
- Lower variance → higher threshold (stricter)
- Self-adjusting to data characteristics

## Integration with Verification Service

### Using Advanced Matching in Verification

```python
from verification_service import (
    get_verification_manager,
    VerificationSessionConfig
)

# Configure verification with advanced matching
config = VerificationSessionConfig(
    matching_strategy='hybrid',  # Use hybrid matching
    use_advanced_matching=True,
    similarity_threshold=0.85,
    compute_confidence=True
)

manager = get_verification_manager(config)

# Create session and verify
session = manager.create_session("+1-234-567-8900")
result, score, error = await manager.verify(
    session.session_id,
    audio_data,
    sample_rate
)

# Access detailed matching metrics
metrics = manager.get_matching_metrics(session.session_id)
print(f"Matching Score: {metrics['matching_score']['final_score']:.4f}")
print(f"Confidence: {metrics['matching_score']['confidence']:.4f}")
```

### Compare Using Different Strategies

```python
# Test different strategies on same session
cosine_score = manager.compare_with_strategy(
    session.session_id,
    MatchingStrategy.COSINE
)

hybrid_score = manager.compare_with_strategy(
    session.session_id,
    MatchingStrategy.HYBRID
)

print(f"Cosine: {cosine_score.final_score:.4f}")
print(f"Hybrid: {hybrid_score.final_score:.4f}")
```

### Get Strategy Comparison Report

```python
# Compare embeddings using all strategies
comparison = manager.get_strategy_comparison(session.session_id)

for strategy, result in comparison['strategy_results'].items():
    print(f"{strategy}: {result['score']:.4f} ({result['result']})")
```

## Confidence Scoring

Confidence is calculated based on consistency across metrics:

```
confidence = 0.4 * consistency + 0.3 * magnitude_consistency + 0.3 * angle_consistency
```

- **Consistency**: Standard deviation of normalized scores across similar metrics
- **Magnitude Consistency**: How close magnitude ratios are to 1.0
- **Angle Consistency**: How small the angle between vectors is

Higher confidence indicates more reliable results.

**Interpreting Confidence:**
- 0.90-1.00: Very high confidence (production-ready)
- 0.70-0.89: Good confidence (acceptable)
- 0.50-0.69: Medium confidence (marginal)
- Below 0.50: Low confidence (unreliable)

## Examples

### Example 1: Basic Matching

```python
import numpy as np
from matching_logic import MatchingComparator, MatchingStrategy

# Create embeddings
reference = np.random.randn(192).astype(np.float32)
test = reference + np.random.randn(192).astype(np.float32) * 0.1

# Compare
comparator = MatchingComparator(similarity_threshold=0.85)
score = comparator.compare_embeddings(reference, test)

print(f"Match: {score.matching_result.value}")
print(f"Score: {score.final_score:.4f}")
print(f"Confidence: {score.confidence:.4f}")
```

### Example 2: All Strategies Comparison

```python
strategies = [
    MatchingStrategy.COSINE,
    MatchingStrategy.EUCLIDEAN,
    MatchingStrategy.CORRELATION,
    MatchingStrategy.CHEBYSHEV,
    MatchingStrategy.HYBRID,
    MatchingStrategy.STATISTICAL,
    MatchingStrategy.ADAPTIVE
]

comparator = MatchingComparator()

for strategy in strategies:
    score = comparator.compare_embeddings(reference, test, strategy=strategy)
    print(f"{strategy.value:<15} Score: {score.final_score:.4f}")
```

### Example 3: Custom Hybrid Weights

```python
from matching_logic import MatchingStrategy

# Create more lenient hybrid (emphasize patterns)
custom_weights = {
    MatchingStrategy.COSINE: 0.30,
    MatchingStrategy.EUCLIDEAN: 0.10,
    MatchingStrategy.CORRELATION: 0.40,  # Increased
    MatchingStrategy.CHEBYSHEV: 0.10,
    MatchingStrategy.STATISTICAL: 0.10
}

comparator = MatchingComparator(primary_strategy=MatchingStrategy.HYBRID)
comparator.set_strategy_weights(custom_weights)

score = comparator.compare_embeddings(reference, test)
```

## Error Handling

### Invalid Embeddings

```python
# Wrong dimension
invalid = np.random.randn(100).astype(np.float32)
score = comparator.compare_embeddings(invalid, test)

if score.matching_result == MatchingResult.ERROR:
    print(f"Error: {score.metadata['error']}")
```

### Handling Results

```python
score = comparator.compare_embeddings(reference, test)

if score.matching_result == MatchingResult.STRONG_MATCH:
    print("✓ Verified!")
elif score.matching_result == MatchingResult.WEAK_MATCH:
    print("Borderline match - may need additional verification")
elif score.matching_result == MatchingResult.NO_MATCH:
    print("✗ Not verified")
elif score.matching_result == MatchingResult.ERROR:
    print(f"Error: {score.metadata.get('error')}")
```

## Performance Characteristics

**Computation Time (per comparison):**
- Cosine: ~0.1 ms (fastest)
- Euclidean: ~0.15 ms
- Correlation: ~0.2 ms
- Chebyshev: ~0.1 ms
- Hybrid: ~0.8 ms (slowest, comprehensive)
- Statistical: ~0.5 ms
- Adaptive: ~0.1 ms

**Memory Usage:**
- All metrics calculated simultaneously
- No additional memory beyond input embeddings
- Singleton pattern reduces overhead

## Best Practices

1. **Default Strategy**: Use COSINE or HYBRID for most applications
2. **Threshold Selection**:
   - 0.95+: Very strict (biometric security)
   - 0.85-0.90: Balanced (recommended)
   - 0.70-0.85: Lenient (user-friendly)
3. **Confidence Consideration**: Always check confidence score before critical decisions
4. **Adaptive Strategy**: Use ADAPTIVE for unknown data distributions
5. **Multi-Strategy**: Use HYBRID for production systems requiring robustness
6. **Custom Weights**: Adjust weights based on domain-specific testing

## Troubleshooting

**Issue: Very low similarity scores**
- Solution: Check embedding quality and normalization
- Try different strategies to confirm

**Issue: Inconsistent results across strategies**
- Solution: Check embedding diversity and quality
- Use confidence scores to assess reliability

**Issue: High false negatives (legitimate users rejected)**
- Solution: Lower similarity threshold or use ADAPTIVE strategy
- Verify embedding generation quality

**Issue: High false positives (non-users accepted)**
- Solution: Raise similarity threshold or use stricter strategy (CHEBYSHEV)
- Consider using HYBRID for balanced approach

## References

- [Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
- [Euclidean Distance](https://en.wikipedia.org/wiki/Euclidean_distance)
- [Kolmogorov–Smirnov Test](https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test)
- [Wasserstein Distance](https://en.wikipedia.org/wiki/Wasserstein_distance)
