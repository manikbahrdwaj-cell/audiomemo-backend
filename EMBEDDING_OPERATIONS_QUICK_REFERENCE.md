# Embedding Operations - Quick Reference

## Quick Start

### 1. Basic Embedding Generation

```python
from voice_embedding import generate_embedding
import numpy as np

# Load audio file
with open("audio.wav", "rb") as f:
    audio_bytes = f.read()

# Generate embedding
embedding = generate_embedding(audio_bytes)
# Result: np.ndarray of shape (192,)
```

### 2. Voice Verification

```python
from embedding_operations import EmbeddingService, EmbeddingServiceConfig
from database import get_voice_embedding
import numpy as np

# Initialize service
service = EmbeddingService()

# Load verification audio
with open("verify.wav", "rb") as f:
    verify_audio = f.read()

# Generate verification embedding
verify_emb, verify_metrics = service.generate(verify_audio, "verify")

# Get enrolled embedding
stored_doc = get_voice_embedding("+1234567890")
stored_emb = np.array(stored_doc["embedding"])

# Compare
comparison = service.compare(verify_emb, stored_emb, "verify", "+1234567890")

if comparison.is_match:
    print(f"✓ MATCH (confidence: {comparison.confidence:.1%})")
else:
    print(f"✗ NO MATCH (similarity: {comparison.cosine_similarity:.4f})")
```

### 3. Batch Enrollment

```python
from embedding_operations import EmbeddingService
from database import store_voice_embedding

service = EmbeddingService()

# Load multiple audio files
audio_files = {
    "+1111111111": open("user1.wav", "rb").read(),
    "+2222222222": open("user2.wav", "rb").read(),
    "+3333333333": open("user3.wav", "rb").read(),
}

# Batch generate
results = service.batch_generate(audio_files)

# Store results
for phone, (embedding, metrics) in results.items():
    if embedding is not None:
        store_voice_embedding(phone, embedding)
        print(f"✓ {phone}: enrolled")
```

## Common Operations

### Generate with Chunking (for long audio)

```python
from voice_embedding import generate_embedding_with_chunking

embedding = generate_embedding_with_chunking(
    audio_bytes,
    chunk_size_seconds=1.0,
    aggregation_method='energy_weighted'
)
```

### Auto Chunking (automatic for long audio)

```python
from voice_embedding import get_embedding_with_auto_chunking

embedding = get_embedding_with_auto_chunking(
    audio_bytes,
    auto_chunk_threshold_seconds=10.0
)
```

### Calculate Similarity

```python
from voice_embedding import calculate_cosine_similarity

similarity = calculate_cosine_similarity(emb1, emb2)
# Returns: float between 0 and 1
```

### Advanced Comparison

```python
from embedding_operations import EmbeddingComparator

# Single comparison
comparison = EmbeddingComparator.compare(
    query_emb, stored_emb,
    "query_user", "stored_user",
    threshold=0.75
)

# Batch comparison
comparisons = EmbeddingComparator.batch_compare(
    query_emb,
    {"user1": emb1, "user2": emb2, "user3": emb3}
)
```

### Embedding Statistics

```python
from embedding_operations import EmbeddingStats

metrics = EmbeddingStats.calculate_metrics(
    embedding,
    "emb_id",
    "+1234567890",
    generation_method="auto"
)

quality = EmbeddingStats.calculate_embedding_quality(embedding)
print(f"Quality Score: {quality:.3f}")
```

### Caching

```python
from embedding_operations import EmbeddingCache

cache = EmbeddingCache(max_size=100)

# Store
cache.put("+1234567890", embedding)

# Retrieve
embedding = cache.get("+1234567890")

# Statistics
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']:.1%}")
```

## Configuration Options

### EmbeddingServiceConfig

```python
config = EmbeddingServiceConfig(
    generation_method='auto',      # 'standard', 'chunked', 'auto'
    use_cache=True,                # Enable caching
    cache_size=100,                # Cache size
    similarity_threshold=0.75,     # Match threshold
    enable_quality_check=True,     # Check quality
    min_quality_score=0.5          # Min acceptable quality
)

service = EmbeddingService(config)
```

### Generation Methods

| Method | Use Case | Notes |
|--------|----------|-------|
| `standard` | Quick enrollment | Fast, single pass |
| `chunked` | Long audio (>10s) | More stable, slower |
| `auto` | Variable length | Automatic decision |

### Aggregation Methods (for chunked)

| Method | Description |
|--------|-------------|
| `mean` | Simple average |
| `max` | Max pooling |
| `weighted_linear` | Linear increasing weights |
| `weighted_inverse` | Linear decreasing weights |
| `weighted_normalized` | Higher weights on middle |
| `energy_weighted` | Weight by audio energy (→ Recommended) |

## Threshold Tuning

```
Security-focused       Threshold = 0.80-0.85
Balanced (default)     Threshold = 0.75-0.80
Convenience-focused    Threshold = 0.70-0.75
```

Experiment with your data:
```python
from database import find_nearest_embedding

query_emb, _ = service.generate(audio, "query")
results = find_nearest_embedding(query_emb, limit=1)

for threshold in [0.70, 0.75, 0.80, 0.85]:
    is_match = results[0]["similarity_score"] >= threshold
    print(f"Threshold {threshold}: {'MATCH' if is_match else 'REJECT'}")
```

## API Endpoints

### REST API

```bash
# Enroll
POST /enroll
  phone_number: str
  file: WAV

# Verify
POST /verify
  phone_number: str
  file: WAV

# Check enrollment
GET /check/{phone_number}
```

### WebSocket API

```javascript
// Audio chunk
{
  "type": "audio",
  "data": "base64_encoded_audio"
}

// Enrollment
{
  "type": "enroll",
  "phone_number": "+1234567890"
}

// Verification
{
  "type": "verify",
  "phone_number": "+1234567890"
}

// Ping (keep-alive)
{
  "type": "ping"
}
```

## Quality Scores

| Score Range | Quality | Action |
|------------|---------|--------|
| 0.8-1.0 | Excellent | Accept |
| 0.6-0.8 | Good | Accept |
| 0.5-0.6 | Acceptable | Caution |
| 0.0-0.5 | Poor | Reject, re-record |

## Distance Metrics

```python
comparison = EmbeddingComparator.compare(...)

# Primary metric (recommended)
sim = comparison.cosine_similarity  # 0-1, higher is better

# Supplementary metrics
euc = comparison.euclidean_distance  # 0-∞, lower is better
man = comparison.manhattan_distance  # 0-∞, lower is better
cheb = comparison.chebyshev_distance # 0-∞, lower is better

is_match = comparison.is_match      # Boolean match decision
confidence = comparison.confidence  # 0-1 match confidence
```

## Error Handling

```python
try:
    embedding, metrics = service.generate(audio, phone)
    
    if metrics.quality_score < 0.5:
        print("Warning: Low quality - request re-recording")
    
    if embedding is None:
        print("Error: Failed to generate embedding")
        
except Exception as e:
    print(f"Embedding generation error: {e}")
```

## Performance Tips

1. **Enable caching** for repeated access to same embedding
2. **Use GPU** (CUDA) for faster processing
3. **Use chunking** for audio longer than 10 seconds
4. **Batch process** for enrollment of many users
5. **Pre-load model** to avoid initialization overhead

## Model Info

- **Architecture**: ECAPA-TDNN
- **Embedding Size**: 192 dimensions
- **Input**: 16kHz mono audio
- **Recommended Duration**: 2-5 seconds enrollment, 1-3 seconds verification
- **Framework**: SpeechBrain
- **Training Data**: VoxCeleb (1M+ speakers)

## Troubleshooting

### Low Quality Score
- Use longer audio (3-5 seconds)
- Record in quiet environment
- Use better microphone/clear speech

### Poor Verification Accuracy
- Lower threshold if too many rejections (0.70-0.75)
- Raise threshold if too many acceptances (0.80-0.85)
- Use multiple enrollment samples for consistency

### Slow Processing
- Enable GPU (CUDA) if available
- Use standard method instead of chunked
- Reduce cache size if memory is limited

## File Structure

```
backend/
├── voice_embedding.py          # Core embedding generation
├── embedding_operations.py     # High-level API (NEW)
├── database.py                 # MongoDB storage
├── main.py                     # REST API endpoints
├── websocket_handler.py        # WebSocket handlers
├── requirements.txt            # Dependencies
└── pretrained_models/
    └── spkrec-ecapa-voxceleb/  # ECAPA-TDNN model
        ├── embedding_model.ckpt
        ├── hyperparams.yaml
        └── ...
```

## Testing

```bash
# Run comprehensive test suite
python test_embedding_operations.py

# Test with custom audio
python -c "
from test_embedding_operations import create_test_audio
from voice_embedding import generate_embedding

audio = create_test_audio(duration_seconds=2.0, frequency=440.0)
emb = generate_embedding(audio)
print(f'Embedding shape: {emb.shape}')
print(f'Magnitude: {np.linalg.norm(emb):.4f}')
"
```

## References

- **Full Guide**: See `EMBEDDING_OPERATIONS_GUIDE.md`
- **Tests**: See `test_embedding_operations.py`
- **SpeechBrain**: https://speechbrain.github.io/
- **ECAPA-TDNN Paper**: https://arxiv.org/abs/2005.07143

## Key Statistics

- Current Model: ECAPA-TDNN (SpeechBrain)
- Embedding Dimension: 192
- Similarity Threshold (default): 0.75
- Quality Score Range: 0.0-1.0
- Cache Size (default): 100 embeddings
- Recommended Audio Duration: 2-5 seconds
- Max Audio Duration: 30 seconds (with chunking)
- Processing Time: ~100ms per second of audio (CPU), ~10ms (GPU)
