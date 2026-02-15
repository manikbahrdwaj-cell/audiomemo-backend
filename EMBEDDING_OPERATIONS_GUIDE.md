# Embedding Operations Implementation Guide

## Overview

This guide covers the complete implementation of Embedding Operations using SpeechBrain's ECAPA-TDNN model for voice biometric authentication. The system generates 192-dimensional speaker embeddings that uniquely identify speakers.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Embedding Operations                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           EmbeddingService (High-Level API)                │ │
│  │  - Caching                                                 │ │
│  │  - Quality Management                                      │ │
│  │  - Batch Processing                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                       │
│         ┌─────────────────┼─────────────────┐                    │
│         ▼                 ▼                 ▼                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Embedding    │  │ Embedding    │  │ Embedding    │           │
│  │ Cache        │  │ Comparator   │  │ Batch        │           │
│  │              │  │              │  │ Processor    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         │                 │                 │                    │
│         └─────────────────┼─────────────────┘                    │
│                           ▼                                       │
│                               │                                   │
│         ┌─────────────────────┼─────────────────────┐            │
│         ▼                     ▼                     ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ SpeechBrain  │    │ Audio        │    │ Embedding    │       │
│  │ ECAPA-TDNN   │    │ Preprocessing│    │ Stats        │       │
│  │ Model        │    │              │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                                       │                │
│         └───────────────────┬───────────────────┘                │
│                             ▼                                     │
│                     ┌──────────────────────┐                     │
│                     │  Core Embedding Ops  │                     │
│                     │ (voice_embedding.py) │                     │
│                     └──────────────────────┘                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
   MongoDB Database (Vector Storage)
```

## Core Components

### 1. Voice Embedding Module (`voice_embedding.py`)

Handles low-level embedding generation using SpeechBrain.

**Key Functions:**

```python
# Basic embedding generation
embedding = generate_embedding(audio_bytes)
# Returns: np.ndarray of shape (192,)

# Chunked embedding generation
embedding = generate_embedding_with_chunking(
    audio_bytes,
    chunk_size_seconds=1.0,
    overlap_ratio=0.2,
    aggregation_method='energy_weighted'
)

# Auto-chunking based on audio length
embedding = get_embedding_with_auto_chunking(
    audio_bytes,
    auto_chunk_threshold_seconds=10.0
)

# Cosine similarity between embeddings
score = calculate_cosine_similarity(embedding1, embedding2)
# Returns: float between 0 and 1
```

**Aggregation Methods for Chunked Embedding:**

1. **mean** - Simple average of chunk embeddings
2. **max** - Maximum values across all chunks
3. **weighted_linear** - Linear increasing weights
4. **weighted_inverse** - Linear decreasing weights
5. **weighted_normalized** - Higher weights on middle chunks
6. **energy_weighted** - Weight by RMS energy (Recommended)

### 2. Embedding Operations Module (`embedding_operations.py`)

High-level API with advanced features.

#### EmbeddingService

Main service class providing unified interface:

```python
from embedding_operations import EmbeddingService, EmbeddingServiceConfig

# Create service with custom config
config = EmbeddingServiceConfig(
    generation_method='auto',  # 'standard', 'chunked', or 'auto'
    use_cache=True,
    cache_size=100,
    similarity_threshold=0.75,
    enable_quality_check=True,
    min_quality_score=0.5
)

service = EmbeddingService(config)

# Generate embedding
embedding, metrics = service.generate(audio_bytes, phone_number)

# Compare embeddings
comparison = service.compare(
    query_embedding,
    stored_embedding,
    query_phone,
    stored_phone
)

# Batch process multiple files
results = service.batch_generate({
    'user1': audio_bytes_1,
    'user2': audio_bytes_2,
    'user3': audio_bytes_3
})

# Check cache statistics
stats = service.get_cache_stats()
```

#### EmbeddingMetrics

Detailed metrics for each embedding:

```python
@dataclass
class EmbeddingMetrics:
    embedding_id: str                # Unique identifier
    phone_number: str               # Associated phone number
    dimensions: int                 # Should be 192
    magnitude: float                # L2 norm of embedding
    mean_value: float               # Mean of values
    std_value: float                # Standard deviation
    min_value: float                # Minimum value
    max_value: float                # Maximum value
    timestamp: datetime             # When generated
    generation_method: str          # standard/chunked/auto
    audio_duration_ms: Optional[float]  # Audio length
    n_chunks: Optional[int]         # If chunked method
    quality_score: Optional[float]  # 0-1 quality metric
```

#### EmbeddingComparison

Detailed comparison result with multiple distance metrics:

```python
@dataclass
class EmbeddingComparison:
    query_phone: str                # Query phone number
    enrolled_phone: str             # Enrolled phone number
    cosine_similarity: float        # Main metric (0-1)
    euclidean_distance: float       # L2 distance
    manhattan_distance: float       # L1 distance
    chebyshev_distance: float       # Max absolute difference
    is_match: bool                  # Based on threshold
    confidence: float               # 0-1 confidence
    threshold: float                # Similarity threshold used
```

#### EmbeddingStats

Statistical analysis of embeddings:

```python
from embedding_operations import EmbeddingStats

# Calculate comprehensive metrics
metrics = EmbeddingStats.calculate_metrics(
    embedding=embedding_vector,
    embedding_id="emb_123",
    phone_number="+1234567890",
    generation_method="auto",
    audio_duration_ms=5000.5,
    n_chunks=5
)

# Calculate quality score (0-1)
quality = EmbeddingStats.calculate_embedding_quality(embedding)
```

#### EmbeddingComparator

Compare single or multiple embeddings:

```python
from embedding_operations import EmbeddingComparator

# Compare two embeddings
comparison = EmbeddingComparator.compare(
    query_embedding=query_emb,
    stored_embedding=stored_emb,
    query_phone="user_query",
    stored_phone="user_enrolled",
    threshold=0.75
)

# Batch compare against multiple stored embeddings
results = EmbeddingComparator.batch_compare(
    query_embedding=query_emb,
    stored_embeddings={
        "user1": emb1,
        "user2": emb2,
        "user3": emb3
    },
    threshold=0.75
)
# Returns: list sorted by similarity (descending)
```

#### EmbeddingBatchProcessor

Process multiple audio files:

```python
from embedding_operations import EmbeddingBatchProcessor

def progress_callback(current, total):
    print(f"Progress: {current}/{total}")

results = EmbeddingBatchProcessor.process_batch(
    audio_bytes_dict={
        "user1": audio_bytes_1,
        "user2": audio_bytes_2,
        "user3": audio_bytes_3
    },
    generation_method='auto',
    use_progress_callback=progress_callback
)

# Results: Dict[identifier -> (embedding, metrics)]
for identifier, (embedding, metrics) in results.items():
    if embedding is not None:
        print(f"{identifier}: quality={metrics.quality_score:.3f}")
```

#### EmbeddingCache

Caching for frequently accessed embeddings:

```python
from embedding_operations import EmbeddingCache

cache = EmbeddingCache(max_size=100)

# Store embedding
cache.put("user_123", embedding_vector)

# Retrieve embedding
embedding = cache.get("user_123")

# Get statistics
stats = cache.get_stats()
# Returns: {
#   "size": int,
#   "max_size": int,
#   "hits": int,
#   "misses": int,
#   "hit_rate": float
# }

# Clear cache
cache.clear()
```

## Usage Examples

### Example 1: Basic Enrollment

```python
from voice_embedding import generate_embedding
from database import store_voice_embedding

# Load audio file
with open("enrollment_audio.wav", "rb") as f:
    audio_bytes = f.read()

# Generate embedding
embedding = generate_embedding(audio_bytes)

# Store in database
vector_id = store_voice_embedding("+1234567890", embedding)
print(f"Enrollment successful: {vector_id}")
```

### Example 2: Voice Verification with Quality Check

```python
from embedding_operations import EmbeddingService, EmbeddingServiceConfig
from database import get_voice_embedding

# Create service with quality checks enabled
config = EmbeddingServiceConfig(
    generation_method='auto',
    similarity_threshold=0.80,
    enable_quality_check=True,
    min_quality_score=0.6
)
service = EmbeddingService(config)

# Load verification audio
with open("verification_audio.wav", "rb") as f:
    audio_bytes = f.read()

# Generate query embedding
query_emb, query_metrics = service.generate(audio_bytes, "query")

# Get stored embedding
stored_record = get_voice_embedding("+1234567890")
stored_emb = np.array(stored_record["embedding"])

# Compare
comparison = service.compare(
    query_emb, stored_emb,
    "query", "+1234567890"
)

print(f"Match: {comparison.is_match}")
print(f"Similarity: {comparison.cosine_similarity:.4f}")
print(f"Confidence: {comparison.confidence:.4f}")
print(f"Query Quality: {query_metrics.quality_score:.4f}")
```

### Example 3: Batch Enrollment

```python
from embedding_operations import EmbeddingService
import os

service = EmbeddingService()

# Load multiple audio files
audio_files = {}
for phone in ["+1111111111", "+2222222222", "+3333333333"]:
    with open(f"audio/{phone}.wav", "rb") as f:
        audio_files[phone] = f.read()

# Progress callback
def progress(current, total):
    print(f"Processing: {current}/{total}")

# Batch generate
results = service.batch_generate(audio_files, progress)

# Store results
from database import store_voice_embedding
for phone, (embedding, metrics) in results.items():
    if embedding is not None:
        store_voice_embedding(phone, embedding)
        print(f"✓ {phone}: quality={metrics.quality_score:.3f}")
    else:
        print(f"✗ {phone}: generation failed")
```

### Example 4: Identifying Speaker from Multiple Candidates

```python
from embedding_operations import EmbeddingComparator
from database import find_nearest_embedding

# Load unknown audio
with open("unknown_speaker.wav", "rb") as f:
    audio_bytes = f.read()

query_emb, _ = service.generate(audio_bytes, "query")

# Find all similar speakers
candidates = find_nearest_embedding(
    query_embedding=query_emb,
    limit=5  # Top 5 matches
)

# Get full embeddings for detailed comparison
stored_embeddings = {}
for candidate in candidates:
    doc = get_voice_embedding(candidate["phone_number"])
    stored_embeddings[candidate["phone_number"]] = np.array(doc["embedding"])

# Detailed batch comparison
comparisons = EmbeddingComparator.batch_compare(
    query_emb, stored_embeddings, threshold=0.75
)

for comp in comparisons:
    print(f"{comp.enrolled_phone}: "
          f"similarity={comp.cosine_similarity:.4f}, "
          f"match={comp.is_match}")
```

### Example 5: Comparing Different Generation Methods

```python
from voice_embedding import compare_embeddings_with_chunks

# Compare different aggregation methods
embeddings = compare_embeddings_with_chunks(
    audio_bytes,
    aggregation_methods=['mean', 'max', 'energy_weighted']
)

# Compare results
from database import get_voice_embedding
stored = np.array(get_voice_embedding("+1234567890")["embedding"])

for method, emb in embeddings.items():
    if emb is not None:
        sim = calculate_cosine_similarity(emb, stored)
        print(f"{method}: similarity={sim:.4f}")
```

## SpeechBrain Model Details

### ECAPA-TDNN Architecture

The ECAPA-TDNN (Emphasizing Channel and Phonetic Attention, Time Delay Neural Network) model is optimized for speaker recognition:

- **Input**: 16kHz mono audio (2-10 seconds recommended)
- **Output**: 192-dimensional speaker embedding
- **Framework**: SpeechBrain (PyTorch-based)
- **Training Data**: VoxCeleb dataset (1+ million speakers)

### Model Location

```
backend/pretrained_models/spkrec-ecapa-voxceleb/
├── custom.py
├── embedding_model.ckpt        # Main model weights
├── classifier.ckpt
├── label_encoder.ckpt
├── mean_var_norm_emb.ckpt     # Normalization parameters
├── label_encoder.txt
└── hyperparams.yaml            # Model configuration
```

### Loading the Model

```python
from voice_embedding import get_model

# Model is cached after first load
model = get_model()

# Device (CUDA if available, else CPU)
# Use GPU for faster processing of multiple embeddings
```

## Quality Metrics

### Embedding Quality Score

Quality is calculated from three factors:

1. **Magnitude Score** (40% weight)
   - Embeddings should normalize to magnitude ~1.0
   - Score penalizes large deviations

2. **Variance Score** (30% weight)
   - Good embeddings have reasonable standard deviation
   - Indicates the model found distinguishing features

3. **Range Score** (30% weight)
   - Values should span a useful range
   - Too narrow range indicates poor discrimination

**Quality Score Range:**
- 0.0-0.3: Poor quality (likely generation failure)
- 0.3-0.6: Acceptable (noisy or short audio)
- 0.6-0.8: Good (normal enrollment)
- 0.8-1.0: Excellent (clear, long audio)

### Distance Metrics

Multiple metrics are available for comparison:

1. **Cosine Similarity** (Recommended)
   - Range: 0-1 (1 = identical)
   - Best for normalized vectors
   - Recommended threshold: 0.75-0.80

2. **Euclidean Distance**
   - Range: 0-∞ (0 = identical)
   - Sensitive to magnitude
   - Useful for outlier detection

3. **Manhattan Distance**
   - Range: 0-∞ (0 = identical)
   - Less sensitive to outliers

4. **Chebyshev Distance**
   - Range: 0-∞ (0 = identical)
   - Maximum absolute difference
   - Quick outlier detection

## Performance Considerations

### Chunking for Long Audio

For audio longer than 10 seconds:
- Use chunking to improve stability
- Recommended chunk size: 1-2 seconds
- Overlap: 0.1-0.3 (10-30%)
- Aggregation: 'energy_weighted' (recommended)

```python
# Automatically chunk long audio
embedding = get_embedding_with_auto_chunking(
    audio_bytes,
    auto_chunk_threshold_seconds=10.0
)
```

### Caching

Enable caching for frequently accessed embeddings:

```python
config = EmbeddingServiceConfig(
    use_cache=True,
    cache_size=100  # Store last 100 unique embeddings
)
service = EmbeddingService(config)

# First access: Generate embedding
embedding1, _ = service.generate(audio, "user1")

# Second access: Retrieved from cache
embedding2, _ = service.generate(audio, "user1")  # Fast!

# Check cache efficiency
stats = service.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

### GPU Acceleration

The system automatically uses GPU (CUDA) if available:

```python
import torch

# Check GPU availability
print(f"CUDA available: {torch.cuda.is_available()}")

# Model will automatically use GPU for faster processing
model = get_model()  # Uses GPU if available
```

## Threshold Tuning

### Fine-tuning Similarity Threshold

The similarity threshold determines match/no-match decision:

```python
# More strict (fewer false positives)
threshold=0.85  # Fewer matches, higher security

# Balanced (recommended)
threshold=0.75-0.80  # Good balance

# More lenient (fewer false negatives)
threshold=0.70  # More matches, more convenience

# Experiment to find optimal threshold
from database import find_nearest_embedding

query_emb, _ = service.generate(audio_bytes, "query")
results = find_nearest_embedding(query_emb, limit=1)

for threshold in [0.70, 0.75, 0.80, 0.85]:
    is_match = results[0]["similarity_score"] >= threshold
    print(f"Threshold {threshold}: {'MATCH' if is_match else 'NO MATCH'}")
```

## Error Handling

```python
from embedding_operations import EmbeddingService

service = EmbeddingService()

try:
    embedding, metrics = service.generate(audio_bytes, phone_number)
    
    if metrics.quality_score < 0.5:
        print("Warning: Low quality embedding")
        print("Recommend: Longer, clearer audio")
    else:
        print(f"Quality: {metrics.quality_score:.3f}")
        
except Exception as e:
    print(f"Generation failed: {e}")
    # Fallback: Prompt for re-recording
```

## Testing Embeddings

### Unit Tests

```python
import numpy as np
from voice_embedding import generate_embedding, calculate_cosine_similarity

# Test basic embedding generation
audio_bytes = b"..."  # Load test audio
embedding = generate_embedding(audio_bytes)

assert embedding.shape == (192,), "Wrong embedding dimension"
assert not np.any(np.isnan(embedding)), "Contains NaN values"
assert np.abs(np.linalg.norm(embedding) - 1.0) < 0.1, "Not normalized"

# Test similarity calculation
emb1 = generate_embedding(audio1)
emb2 = generate_embedding(audio2)

similarity = calculate_cosine_similarity(emb1, emb2)
assert 0 <= similarity <= 1, "Similarity out of range"

# Test identical samples (should have high similarity)
similarity_same = calculate_cosine_similarity(embedding, embedding)
assert similarity_same > 0.99, f"Self-similarity should be near 1.0, got {similarity_same}"
```

## Best Practices

1. **Audio Quality**
   - Use clear, noise-free audio
   - 16kHz mono is optimal
   - 2-5 seconds is ideal for enrollment
   - Longer audio (5-10s) improves stability

2. **Threshold Selection**
   - Start with default 0.75-0.80
   - Tune based on your False Positive/Negative Rate (FPR/FNR) requirements
   - Security-critical: use 0.80-0.85
   - Convenience-focused: use 0.70-0.75

3. **Quality Management**
   - Always check embedding quality scores
   - Reject low-quality embeddings (<0.5)
   - Request re-recording if quality is poor

4. **Caching**
   - Enable caching for high-frequency lookups
   - Monitor hit rates
   - Clear cache periodically if needed

5. **Batch Processing**
   - Use for bulk enrollment
   - Monitor progress
   - Handle failures gracefully

6. **Monitoring**
   - Track quality metrics over time
   - Monitor similarity score distributions
   - Alert on unexpected patterns

## Troubleshooting

### Low Quality Embeddings

**Symptoms:** Quality score < 0.5

**Causes:**
- Very short audio (<1 second)
- High background noise
- Distorted audio quality
- Non-speech audio

**Solutions:**
- Request longer recording (3-5 seconds)
- Record in quiet environment
- Use better microphone
- Verify audio is speech, not noise

### High False Rejection Rate

**Symptoms:** Legitimate users not matching

**Causes:**
- Threshold too high
- Different recording conditions
- Vocal variation (cold, emotion, etc.)

**Solutions:**
- Lower threshold to 0.70-0.75
- Use multiple enrollment samples
- Consider user variability

### High False Acceptance Rate

**Symptoms:** Different speakers matching

**Causes:**
- Threshold too low
- Similar voice characteristics
- Very short audio

**Solutions:**
- Raise threshold to 0.80-0.85
- Use longer audio samples
- Consider additional verification factors

## Integration with API

The embedding operations are used in:

1. **POST /enroll** - Store voice embedding
2. **POST /verify** - Compare voice against enrollment
3. **GET /check/{phone_number}** - Check enrollment status
4. **WebSocket /ws/voice** - Real-time voice streaming

All use the underlying embedding operations.

## References

- **SpeechBrain**: https://speechbrain.github.io/
- **ECAPA-TDNN**: https://arxiv.org/abs/2005.07143
- **VoxCeleb Dataset**: http://www.voxceleb.org/
- **PyTorch Audio**: https://pytorch.org/audio/stable/index.html
