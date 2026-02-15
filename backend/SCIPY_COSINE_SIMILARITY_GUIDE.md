# Embedding Operations - Cosine Similarity Implementation

## Overview

This document describes the comprehensive embedding similarity operations implementation using **SciPy** for optimal numerical stability and performance.

## Key Features

### 1. **SciPy-Based Cosine Similarity**
- Uses `scipy.spatial.distance.cosine()` for numerical stability
- Normalized output in range [0, 1]
- Handles edge cases (zero vectors, NaN values)

### 2. **Multiple Distance Metrics**
- **Cosine Similarity/Distance**: Angle-based similarity
- **Euclidean Distance**: L2 norm of difference
- **Correlation Distance**: Pearson correlation-based
- **Additional Metrics**: Braycurtis, Canberra, Chebyshev (via SciPy)

### 3. **Batch Operations**
- Compare one embedding against multiple embeddings
- Compute pairwise similarity matrices
- Batch statistical computations

### 4. **Advanced Features**
- Hierarchical clustering of embeddings
- Find most similar/dissimilar embeddings
- Statistical analysis of embedding sets
- Comprehensive result objects with metadata

## Implementation Details

### File Structure

```
backend/
├── voice_embedding.py                      # Updated with scipy.spatial.distance imports
├── embedding_operations.py                 # Updated with scipy imports
└── embedding_similarity_operations.py      # NEW: Comprehensive similarity operations
```

### Module: `embedding_similarity_operations.py`

#### Main Classes

**1. `EmbeddingSimilarityCalculator`**
```python
calculator = EmbeddingSimilarityCalculator(metric='cosine')

# Single comparisons
similarity = calculator.cosine_similarity(emb1, emb2)
distance = calculator.cosine_distance(emb1, emb2)
eucl_dist = calculator.euclidean_distance(emb1, emb2)

# Comprehensive comparison
result = calculator.compare(emb1, emb2, threshold=0.6)

# Batch operations
results = calculator.batch_compare(query_emb, [emb1, emb2, ...])

# Advanced operations
similar = calculator.find_most_similar(query, embeddings, top_k=5)
dissimilar = calculator.find_most_dissimilar(query, embeddings, top_k=5)

# Clustering
clusters = calculator.cluster_embeddings(embeddings, threshold=0.3)

# Similarity matrix
sim_matrix = calculator.compute_similarity_matrix(embeddings)
```

**2. `SimilarityResult`**
```python
@dataclass
class SimilarityResult:
    embedding1_id: str
    embedding2_id: str
    cosine_similarity: float          # [0, 1]
    cosine_distance: float            # [0, 1]
    euclidean_distance: float         # >= 0
    correlation_distance: float       # [0, 1]
    is_match: bool
    confidence: float                 # [0, 1]
    metadata: Optional[Dict]
```

**3. `SimilarityMatrix`**
```python
@dataclass
class SimilarityMatrix:
    embeddings: np.ndarray            # (n, embedding_dim)
    similarity_matrix: np.ndarray     # (n, n), values in [-1, 1]
    distance_matrix: np.ndarray       # (n, n), Euclidean distances
    labels: Optional[List[str]]
    embedding_dim: int
```

#### Convenience Functions

```python
# Batch similarity computation
similarities = batch_cosine_similarity(embeddings1, embeddings2)

# Statistical analysis
stats = compute_embedding_statistics(embeddings)
```

## Usage Examples

### 1. Basic Cosine Similarity

```python
from embedding_similarity_operations import EmbeddingSimilarityCalculator
import numpy as np

calculator = EmbeddingSimilarityCalculator()

# Two embeddings
emb1 = np.random.randn(192).astype(np.float32)
emb2 = np.random.randn(192).astype(np.float32)

# Calculate similarity
similarity = calculator.cosine_similarity(emb1, emb2)
print(f"Cosine Similarity: {similarity:.4f}")  # 0.0 - 1.0
```

### 2. Comprehensive Comparison

```python
result = calculator.compare(
    emb1, emb2,
    emb1_id="speaker_001",
    emb2_id="speaker_002",
    threshold=0.6
)

print(f"Match: {result.is_match}")
print(f"Confidence: {result.confidence:.4f}")
print(f"Cosine Similarity: {result.cosine_similarity:.4f}")
print(f"Euclidean Distance: {result.euclidean_distance:.4f}")
```

### 3. Batch Voice Comparison

```python
query_embedding = generate_embedding(audio_bytes)
stored_embeddings = [emb1, emb2, emb3, emb4, emb5]
speaker_ids = ["alice", "bob", "charlie", "diana", "eve"]

results = calculator.batch_compare(
    query_embedding,
    stored_embeddings,
    embedding_ids=speaker_ids,
    threshold=0.6
)

for result in results:
    if result.is_match:
        print(f"✓ Match found: {result.embedding2_id} "
              f"(confidence: {result.confidence:.2%})")
```

### 4. Find Most Similar Speakers

```python
similar = calculator.find_most_similar(
    query_embedding,
    all_embeddings,
    embedding_ids=all_speaker_ids,
    top_k=5
)

print("Top 5 most similar speakers:")
for rank, (speaker_id, similarity) in enumerate(similar, 1):
    print(f"{rank}. {speaker_id}: {similarity:.4f}")
```

### 5. Clustering Similar Embeddings

```python
# Get embeddings from multiple speakers
embeddings = [generate_embedding(audio) for audio in audio_files]
speaker_ids = ["speaker_001", "speaker_002", ...]

# Cluster by similarity
clusters = calculator.cluster_embeddings(
    np.array(embeddings),
    labels=speaker_ids,
    threshold=0.3,  # Distance threshold
    method='average'
)

for cluster_id, members in clusters.items():
    print(f"Cluster {cluster_id}:")
    for speaker_id, _ in members:
        print(f"  - {speaker_id}")
```

### 6. Similarity Matrix for Analysis

```python
sim_matrix = calculator.compute_similarity_matrix(
    np.array(embeddings),
    labels=speaker_ids,
    metric='cosine'
)

# Access the similarity matrix
print(f"Matrix shape: {sim_matrix.similarity_matrix.shape}")
print(f"All similarities between 0-1: {sim_matrix.similarity_matrix.min():.4f} - "
      f"{sim_matrix.similarity_matrix.max():.4f}")

# Get similarity between specific embeddings
sim_between_0_1 = sim_matrix.similarity_matrix[0, 1]
print(f"Similarity between speaker 0 and 1: {sim_between_0_1:.4f}")
```

### 7. Batch Similarity Matrix

```python
# Compare multiple embeddings with multiple embeddings
set1 = np.random.randn(10, 192)  # 10 embeddings
set2 = np.random.randn(5, 192)   # 5 embeddings

# Compute all pairwise similarities
sim_matrix = batch_cosine_similarity(set1, set2)
print(f"Result shape: {sim_matrix.shape}")  # (10, 5)
```

### 8. Embedding Statistics

```python
stats = compute_embedding_statistics(embeddings)

print(f"Number of embeddings: {stats['n_embeddings']}")
print(f"Embedding dimension: {stats['embedding_dim']}")
print(f"Mean pairwise distance: {stats['mean_pairwise_distance']:.4f}")
print(f"Std pairwise distance: {stats['std_pairwise_distance']:.4f}")
print(f"Min pairwise distance: {stats['min_pairwise_distance']:.4f}")
print(f"Max pairwise distance: {stats['max_pairwise_distance']:.4f}")
```

## Mathematical Details

### Cosine Similarity Using SciPy

The implementation uses `scipy.spatial.distance.cosine()`:

1. **SciPy returns cosine distance** = $1 - \cos(\theta)$ in range [0, 2]
2. **Normalization**: Convert to [0, 1] range using formula:
   - $\text{similarity} = 1.0 - \text{distance}/2.0$
   - Result: 1.0 = identical, 0.5 = orthogonal, 0.0 = opposite

### Distance Metrics

All distance metrics are computed using SciPy's `cdist()`:

| Metric | Formula | Range | Use Case |
|--------|---------|-------|----------|
| Cosine | $1 - \frac{A \cdot B}{\|A\|\|B\|}$ | [0, 2] | Angle between vectors |
| Euclidean | $\sqrt{\sum(a_i - b_i)^2}$ | [0, ∞] | Absolute distance |
| Correlation | $1 - \rho(A,B)$ | [0, 1] | Pattern similarity |

## Performance Characteristics

### Advantages of SciPy Implementation

1. **Numerical Stability**: Optimized C implementations
2. **Performance**: Vectorized operations for batch processing
3. **Accuracy**: Handles edge cases (zero vectors, NaN)
4. **Compatibility**: Industry-standard distance metrics

### Time Complexity

| Operation | Complexity |
|-----------|------------|
| Single similarity | O(d) where d = embedding_dim |
| Batch similarity (n vs m) | O(n × m × d) |
| Similarity matrix (n embeddings) | O(n² × d) |
| Clustering (n embeddings) | O(n² log n) |

### Space Complexity

| Data Structure | Complexity |
|---------|---------|
| Single comparison | O(d) |
| Similarity matrix | O(n²) |
| Batch results | O(n) |

## Integration with Existing Code

### Updated `voice_embedding.py`

```python
# NEW IMPORTS
from scipy.spatial.distance import cosine
from scipy.spatial import distance

# UPDATED FUNCTION
def calculate_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Uses scipy.spatial.distance.cosine() internally"""
    ...
```

### Updated `embedding_operations.py`

```python
# NEW IMPORTS
from scipy.spatial.distance import cdist, cosine, pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from scipy import spatial
```

## Testing

### Verification Tests

Run the verification script:
```bash
python verify_scipy_similarity.py
```

Expected output:
```
✓ Module imported successfully
✓ Calculator initialized
✓ Identical embeddings test passed: 1.0000
✓ Orthogonal embeddings test passed: 0.5000
✓ Opposite embeddings test passed: 0.0000
✓ 192-D identical embeddings test passed: 1.0000
✓ Distance metrics test passed (cosine=0.5248, euclidean=19.9359)

✓ ALL SCIPY COSINE SIMILARITY TESTS PASSED!
```

### Comprehensive Test Suite

Run full tests:
```bash
python test_embedding_similarity.py
```

Tests include:
- ✓ SciPy cosine similarity calculations
- ✓ Distance metrics (cosine, Euclidean, correlation)
- ✓ Comprehensive embedding comparison
- ✓ Batch similarity operations
- ✓ Similarity matrix computation
- ✓ Find most/least similar embeddings
- ✓ Embedding clustering
- ✓ Batch similarity matrix
- ✓ Statistical analysis

## Best Practices

### 1. Choose Appropriate Thresholds

```python
# For speaker verification
threshold = 0.6  # Moderate threshold

# For speaker identification (stricter matching)
threshold = 0.7  # Strict threshold

# For similarity-based clustering
threshold = 0.3  # Distance threshold
```

### 2. Handle Edge Cases

```python
# Empty or zero embeddings
if embedding.size == 0 or np.allclose(embedding, 0):
    return None  # Skip

# NaN or Inf values
if not np.isfinite(embedding).all():
    embedding = np.nan_to_num(embedding)
```

### 3. Batch Processing for Efficiency

```python
# Instead of:
for emb in embeddings:
    similarity = calculate_cosine_similarity(query, emb)

# Use:
similarities = batch_cosine_similarity(query, embeddings)
```

### 4. Normalize Before Clustering

```python
# Normalize embeddings before clustering
normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
calculator.cluster_embeddings(normalized)
```

## Troubleshooting

### Issue: Similarity always 0.5

**Cause**: Zero or nan embeddings  
**Solution**: Check embedding generation and normalization

### Issue: All similarities the same

**Cause**: Embeddings not properly normalized  
**Solution**: Verify embedding generation uses proper normalization

### Issue: Clustering produces no clusters

**Cause**: Threshold too low  
**Solution**: Increase threshold value

## Requirements

- scipy >= 1.11.4
- numpy >= 1.24.3
- torch >= 2.2.0
- torchaudio >= 2.2.0

All dependencies are in `backend/requirements.txt`

## Related Files

- [voice_embedding.py](voice_embedding.py) - Core embedding generation
- [embedding_operations.py](embedding_operations.py) - Embedding management
- [embedding_similarity_operations.py](embedding_similarity_operations.py) - THIS MODULE
- [verify_scipy_similarity.py](verify_scipy_similarity.py) - Quick verification
- [test_embedding_similarity.py](test_embedding_similarity.py) - Full test suite

## References

- **SciPy Distance**: https://docs.scipy.org/doc/scipy/reference/spatial.distance.html
- **Cosine Similarity**: https://en.wikipedia.org/wiki/Cosine_similarity
- **Hierarchical Clustering**: https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html

## API Summary

### Main Functions

| Function | Purpose |
|----------|---------|
| `cosine_similarity()` | Single similarity calculation |
| `cosine_distance()` | Distance metric version |
| `euclidean_distance()` | L2 norm distance |
| `correlation_distance()` | Pearson correlation-based |
| `compare()` | Comprehensive pairwise comparison |
| `batch_compare()` | Compare one vs many |
| `compute_similarity_matrix()` | Pairwise matrix computation |
| `cluster_embeddings()` | Hierarchical clustering |
| `find_most_similar()` | Top-k similar embeddings |
| `find_most_dissimilar()` | Top-k dissimilar embeddings |
| `batch_cosine_similarity()` | Vectorized pairwise similarities |
| `compute_embedding_statistics()` | Statistical analysis |

---

**Implementation Date**: February 2026  
**Version**: 1.0  
**Status**: ✓ Complete and Tested
