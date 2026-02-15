# Chunk Embedding Verifier - API Quick Reference

## Quick Start

### 1. Basic Chunk Verification
```python
from chunk_embedding_verifier import ChunkEmbeddingVerifier
import numpy as np

# Create verifier
verifier = ChunkEmbeddingVerifier(
    similarity_threshold=0.75,
    confidence_threshold=0.70
)

# Generate chunk embeddings
ref_chunks = verifier.generate_chunk_embeddings(reference_audio)
ver_chunks = verifier.generate_chunk_embeddings(verification_audio)

# Perform verification
result = verifier.verify_with_chunks(ref_chunks, ver_chunks)

# Check result
if result.verification_status.value == "match":
    print(f"✓ Verified! Confidence: {result.overall_confidence:.2%}")
else:
    print(f"✗ Not verified. Status: {result.verification_status.value}")
```

### 2. With Verification Service
```python
from verification_service import (
    VerificationManager,
    VerificationSessionConfig
)

# Configure with chunk verification
config = VerificationSessionConfig(
    max_attempts=3,
    use_chunk_verification=True,
    chunk_similarity_threshold=0.75,
    chunk_confidence_threshold=0.70
)

# Create manager
manager = VerificationManager(config)

# Create and verify session
session = manager.create_session("+1234567890")
result, score, error, chunk_result = manager.verify_with_chunks(
    session.session_id,
    verification_audio
)

print(f"Result: {result.value}")
print(f"Score: {score:.4f}")
print(f"Matched Chunks: {chunk_result.matched_chunks}/{chunk_result.total_reference_chunks}")
```

---

## Core Classes

### ChunkEmbeddingVerifier

```python
class ChunkEmbeddingVerifier:
    def __init__(
        self,
        chunk_config: Optional[ChunkConfig] = None,
        similarity_threshold: float = 0.75,
        confidence_threshold: float = 0.70,
        metric: str = 'cosine'
    )
    
    def generate_chunk_embeddings(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        store_chunk_data: bool = False
    ) -> List[ChunkEmbedding]
    
    def compare_chunk_embeddings(
        self,
        reference_chunk: ChunkEmbedding,
        verification_chunk: ChunkEmbedding,
        use_dynamic_threshold: bool = False
    ) -> ChunkComparisonResult
    
    def match_chunks(
        self,
        reference_chunks: List[ChunkEmbedding],
        verification_chunks: List[ChunkEmbedding],
        matching_strategy: str = 'best_match'
    ) -> List[ChunkComparisonResult]
    
    def verify_with_chunks(
        self,
        reference_chunks: List[ChunkEmbedding],
        verification_chunks: List[ChunkEmbedding],
        matching_strategy: str = 'best_match',
        use_dynamic_threshold: bool = False
    ) -> ChunkVerificationResult
    
    def analyze_chunk_variance(
        self,
        chunk_embeddings: List[ChunkEmbedding]
    ) -> Dict[str, Any]
```

### VerificationManager (Enhanced)

```python
class VerificationManager:
    def verify_with_chunks(
        self,
        session_id: str,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> Tuple[VerificationResult, float, Optional[str], Optional[ChunkVerificationResult]]
    
    def analyze_chunk_variance(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]
```

---

## Enums

### ChunkMatchStatus
```python
class ChunkMatchStatus(Enum):
    MATCH = "match"                    # Chunks match
    PARTIAL_MATCH = "partial_match"    # Partial match
    MISMATCH = "mismatch"              # No match
    LOW_CONFIDENCE = "low_confidence"  # Low confidence
    INSUFFICIENT_DATA = "insufficient_data"
```

### Matching Strategies
- **'best_match'**: Each reference chunk → best verification match (default)
- **'strict_order'**: One-to-one matching by index
- **'all_pairs'**: All reference vs all verification pairs

---

## Data Objects

### ChunkEmbedding
```python
chunk.chunk_id          # str: Unique identifier
chunk.chunk_index       # int: Chunk index
chunk.embedding         # np.ndarray: Embedding vector (192 dims)
chunk.start_time_ms     # float: Start time
chunk.end_time_ms       # float: End time
chunk.duration_ms       # float: Duration
chunk.confidence        # float: Confidence [0-1]
chunk.metadata          # dict: Additional info
```

### ChunkVerificationResult
```python
result.verification_id              # str: Unique ID
result.timestamp                    # datetime: When verified
result.total_reference_chunks       # int: Number of reference chunks
result.total_verification_chunks    # int: Number of verification chunks
result.matched_chunks               # int: Number matched
result.partial_matched_chunks       # int: Number partially matched
result.unmatched_chunks             # int: Number unmatched
result.average_chunk_similarity     # float: Average similarity [0-1]
result.overall_confidence           # float: Overall confidence [0-1]
result.verification_status          # ChunkMatchStatus: Overall status
result.chunk_comparisons            # List: Per-chunk comparison results
result.statistics                   # dict: Detailed statistics
result.to_dict()                    # dict: Serializable representation
```

### ChunkComparisonResult
```python
comparison.cosine_similarity        # float: Cosine similarity
comparison.euclidean_distance       # float: Euclidean distance
comparison.correlation_distance     # float: Correlation distance
comparison.is_match                 # bool: Threshold match
comparison.confidence               # float: Confidence score
comparison.status                   # ChunkMatchStatus: Match status
comparison.to_dict()                # dict: Serializable representation
```

---

## Common Patterns

### Pattern: Similarity Analysis
```python
# Get detailed metrics between two audio samples
ref_chunks = verifier.generate_chunk_embeddings(ref_audio)
ver_chunks = verifier.generate_chunk_embeddings(ver_audio)

result = verifier.verify_with_chunks(ref_chunks, ver_chunks)

print(f"Matches: {result.matched_chunks}/{result.total_reference_chunks}")
print(f"Average similarity: {result.average_chunk_similarity:.4f}")
print(f"Confidence: {result.overall_confidence:.4f}")

for chunk_comp in result.chunk_comparisons:
    print(f"  Chunk {chunk_comp.reference_chunk_index}: "
          f"{chunk_comp.cosine_similarity:.4f} - {chunk_comp.status.value}")
```

### Pattern: Variance Check
```python
# Analyze consistency of chunk embeddings
chunks = verifier.generate_chunk_embeddings(audio)
analysis = verifier.analyze_chunk_variance(chunks)

print(f"Homogeneity: {analysis['homogeneity']:.4f}")  # 1.0 = perfect consistency
print(f"Variance: {analysis['variance']:.6f}")        # Lower = more consistent

if analysis['homogeneity'] < 0.7:
    print("⚠ Low homogeneity - audio may be noisy")
```

### Pattern: Strategy Comparison
```python
# Compare different matching strategies
for strategy in ['best_match', 'strict_order', 'all_pairs']:
    result = verifier.verify_with_chunks(
        ref_chunks,
        ver_chunks,
        matching_strategy=strategy
    )
    print(f"{strategy}: {result.matched_chunks} matches, "
          f"confidence {result.overall_confidence:.2%}")
```

### Pattern: Threshold Tuning
```python
# Test different thresholds
thresholds = [0.70, 0.75, 0.80, 0.85]

for threshold in thresholds:
    verifier = ChunkEmbeddingVerifier(similarity_threshold=threshold)
    result = verifier.verify_with_chunks(ref_chunks, ver_chunks)
    print(f"Threshold {threshold}: {result.verification_status.value}")
```

---

## Configuration Presets

### Conservative (High Security)
```python
config = VerificationSessionConfig(
    chunk_similarity_threshold=0.80,
    chunk_confidence_threshold=0.80,
    chunk_matching_strategy='all_pairs'
)
```

### Balanced (Default)
```python
config = VerificationSessionConfig(
    chunk_similarity_threshold=0.75,
    chunk_confidence_threshold=0.70,
    chunk_matching_strategy='best_match'
)
```

### Permissive (High Usability)
```python
config = VerificationSessionConfig(
    chunk_similarity_threshold=0.70,
    chunk_confidence_threshold=0.60,
    chunk_matching_strategy='best_match'
)
```

---

## Error Handling

```python
try:
    chunks = verifier.generate_chunk_embeddings(audio)
    result = verifier.verify_with_chunks(ref_chunks, chunks)
    
    if result.verification_status == ChunkMatchStatus.MATCH:
        print("✓ Verified")
    elif result.verification_status == ChunkMatchStatus.LOW_CONFIDENCE:
        print("? Low confidence")
    else:
        print("✗ Not verified")

except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Verification error: {e}")
```

---

## Performance Tips

1. **Cache chunk embeddings** - Don't regenerate if unchanged
2. **Use best_match strategy** - Balanced performance/accuracy
3. **Adjust overlap ratio** - Lower = faster, higher = more accurate
4. **Disable chunk_data storage** - Save memory in production
5. **Monitor homogeneity** - Detect anomalies early

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Low scores | Improve audio quality, lower threshold |
| High memory | Disable chunk_data, reduce overlap |
| Slow verification | Use 'best_match' strategy |
| Inconsistent results | Check audio preprocessing |

---

## Testing

```bash
# Run comprehensive tests
python test_chunk_embedding_verifier.py

# Expected output:
# ✓ PASS: chunk_generation
# ✓ PASS: chunk_comparison
# ✓ PASS: matching_strategies
# ✓ PASS: full_verification
# ✓ PASS: variance_analysis
# ✓ PASS: verification_service
```

---

## Files and Modules

| File | Purpose |
|------|---------|
| `chunk_embedding_verifier.py` | Core chunk verification |
| `verification_service.py` | Integrated service |
| `test_chunk_embedding_verifier.py` | Test suite |
| `CHUNK_EMBEDDING_VERIFIER_GUIDE.md` | Full documentation |
| `CHUNK_EMBEDDING_VERIFIER_IMPLEMENTATION_SUMMARY.md` | Implementation details |

---

For complete documentation, see **CHUNK_EMBEDDING_VERIFIER_GUIDE.md**
