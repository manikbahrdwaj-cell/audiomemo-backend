# Audio Chunking - Quick Reference Card

## One-Liner Usage

```python
# Most common: Auto-chunk if audio > 10 seconds
from voice_embedding import get_embedding_with_auto_chunking
embedding = get_embedding_with_auto_chunking(audio_bytes)
```

---

## The 4 Main Functions

### 1. Auto Chunking (RECOMMENDED) ⭐
```python
embedding = get_embedding_with_auto_chunking(
    audio_bytes,
    auto_chunk_threshold_seconds=10.0
)
```
**Use when:** You don't know if chunking is needed  
**Best for:** General-purpose enrollment/verification  

### 2. Full Control Chunking
```python
embedding = generate_embedding_with_chunking(
    audio_bytes,
    chunk_size_seconds=2.0,
    overlap_ratio=0.2,
    aggregation_method='energy_weighted',
    apply_windowing=True,
    normalize_chunks=True
)
```
**Use when:** You need fine-tuned control  
**Best for:** Optimization and testing  

### 3. Compare Methods
```python
results = compare_embeddings_with_chunks(audio_bytes)
# Returns dict of embeddings from all methods
```
**Use when:** Testing which method works best  

### 4. Direct Chunking (Advanced)
```python
from audio_chunking import ChunkProcessor, ChunkConfig

config = ChunkConfig(chunk_size=16000, overlap_ratio=0.2)
processor = ChunkProcessor(config)
embedding, metadata = processor.process_audio(
    audio, embedding_func, aggregation_method='mean'
)
```
**Use when:** Building custom pipelines  

---

## Aggregation Methods at a Glance

| Method | Code | When to Use |
|--------|------|-------------|
| Mean | `aggregation_method='mean'` | Default, balanced |
| Max | `aggregation_method='max'` | Emphasize peaks |
| Linear | `aggregation_method='weighted_linear'` | Increasing confidence |
| Inverse | `aggregation_method='weighted_inverse'` | Decreasing quality |
| Normalized | `aggregation_method='weighted_normalized'` | Stable middle |
| **Energy** ⭐ | `aggregation_method='energy_weighted'` | Variable quality |

---

## Configuration Parameters

### Chunk Size (seconds)
- `0.5` = 500ms chunks (too small, slow)
- `1.0` = 1 second (good detail) ✓
- `2.0` = 2 seconds (recommended) ✓✓
- `3.0+` = 3+ seconds (fewer chunks, less detail)

### Overlap Ratio (0.0-1.0)
- `0.1` = 10% overlap (fast)
- `0.2` = 20% overlap (recommended) ✓✓
- `0.3` = 30% overlap (better, slower)
- `0.5` = 50% overlap (very slow, not recommended)

### Auto Chunking Threshold (seconds)
- `5.0` = Chunk if audio > 5 seconds (aggressive)
- `10.0` = Chunk if audio > 10 seconds (recommended) ✓✓
- `30.0` = Chunk if audio > 30 seconds (conservative)

---

## FastAPI Integration Template

```python
from fastapi import FastAPI, File, UploadFile, Form
from voice_embedding import get_embedding_with_auto_chunking
from database import store_voice_embedding

app = FastAPI()

@app.post("/enroll")
async def enroll(phone_number: str = Form(...), audio: UploadFile = File(...)):
    embedding = get_embedding_with_auto_chunking(
        await audio.read(),
        auto_chunk_threshold_seconds=10.0
    )
    store_voice_embedding(phone_number, embedding)
    return {"success": True}

@app.post("/verify")
async def verify(phone_number: str = Form(...), audio: UploadFile = File(...)):
    embedding = get_embedding_with_auto_chunking(await audio.read())
    stored = get_voice_embedding(phone_number)
    similarity = calculate_cosine_similarity(embedding, stored)
    return {"is_match": similarity > 0.65, "score": similarity}
```

---

## Testing Locally

```bash
# Run all tests
cd backend
python test_audio_chunking.py

# Run examples
python audio_chunking_examples.py

# Test with specific audio
python -c "
from voice_embedding import get_embedding_with_auto_chunking
emb = get_embedding_with_auto_chunking(open('audio.wav', 'rb').read())
print(f'Embedding shape: {emb.shape}')
"
```

---

## Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| **Slow processing** | Reduce `chunk_size_seconds` to 1.0 or reduce `overlap_ratio` to 0.1 |
| **Out of memory** | Use auto_chunking; it streams one chunk at a time |
| **Lower similarity** | Try `aggregation_method='energy_weighted'` |
| **Different results each run** | Normal for chunked embeddings; use same method each time |
| **Different vs non-chunked** | Try `overlap_ratio=0.3` or `aggregation_method='mean'` |

---

## File Locations

```
backend/
├── voice_embedding.py          ← Main functions here
├── audio_chunking.py           ← Core implementation
├── audio_chunking_examples.py  ← 9 examples
└── test_audio_chunking.py      ← Run tests
```

---

## Common Patterns

### Pattern 1: Adaptive Endpoint
```python
@app.post("/smart-enroll")
async def enroll(phone: str = Form(...), audio: UploadFile = File(...)):
    # Automatically chunks if needed
    embedding = get_embedding_with_auto_chunking(
        await audio.read()
    )
    store_voice_embedding(phone, embedding)
    return {"success": True}
```

### Pattern 2: Robust Endpoint
```python
@app.post("/robust-verify")
async def verify(phone: str = Form(...), audio: UploadFile = File(...)):
    # Always use energy-weighted chunking
    embedding = generate_embedding_with_chunking(
        await audio.read(),
        chunk_size_seconds=2.0,
        aggregation_method='energy_weighted'
    )
    stored = get_voice_embedding(phone)
    return {"match": similarity(embedding, stored) > 0.65}
```

### Pattern 3: Fast Endpoint
```python
@app.post("/fast-check")
async def check(phone: str = Form(...), audio: UploadFile = File(...)):
    # Minimal chunking, fast response
    embedding = generate_embedding_with_chunking(
        await audio.read(),
        chunk_size_seconds=1.0,
        overlap_ratio=0.1,
        aggregation_method='mean'
    )
    # ...
```

---

## Performance Expectations

- **Short audio (< 5s):** ~0.8 seconds (non-chunked)
- **Medium audio (5-10s):** ~1.0 second  
- **Long audio (10-30s):** ~2-6 seconds (chunked)
- **Very long audio (30+s):** ~10+ seconds (chunked)

**Times include model inference (~0.5s-1.0s base overhead)**

---

## Import Cheat Sheet

```python
# Most common imports
from voice_embedding import (
    generate_embedding_with_chunking,
    get_embedding_with_auto_chunking,
    calculate_cosine_similarity
)

# For advanced use
from audio_chunking import (
    ChunkConfig,
    AudioChunker,
    EmbeddingAggregator,
    ChunkProcessor
)

# For testing
from voice_embedding import compare_embeddings_with_chunks
```

---

## Default Recommended Setup

```python
# Best balance of speed, accuracy, and simplicity
embedding = get_embedding_with_auto_chunking(
    audio_bytes,
    auto_chunk_threshold_seconds=10.0,
    # Additional kwargs passed to chunking:
    # chunk_size_seconds=2.0,          (default)
    # overlap_ratio=0.2,                (default)
    # aggregation_method='mean'         (default)
)
```

**Why this works:**
- ✅ Auto-chunks only when needed (efficient)
- ✅ 2-second chunks strike good balance
- ✅ 20% overlap reduces edge artifacts
- ✅ Mean pooling fast and robust
- ✅ Seamless integration

---

## Decision Tree

```
Is audio > 10 seconds?
├─ NO  → use get_embedding_with_auto_chunking() ✓
└─ YES
   ├─ Variable quality? → use aggregation_method='energy_weighted'
   ├─ Consistent quality? → use aggregation_method='mean'
   └─ Unsure? → use aggregation_method='weighted_normalized'
```

---

## Debugging Commands

```python
# Check if chunking is being used
from audio_chunking import AudioChunker, ChunkConfig
chunker = AudioChunker()
chunks = chunker.chunk(audio)
print(f"Created {len(chunks)} chunks")

# Compare methods
from voice_embedding import compare_embeddings_with_chunks
results = compare_embeddings_with_chunks(audio_bytes)
for method in results:
    print(f"{method}: ✓ generated" if results[method] is not None else f"{method}: ✗ failed")

# Check audio duration
duration_ms = len(audio) / 16000 * 1000
print(f"Audio duration: {duration_ms:.0f}ms")
threshold_ms = 10000
print(f"Will chunk: {duration_ms > threshold_ms}")
```

---

## Summary

| What | Where |
|------|-------|
| **Start here** | `AUDIO_CHUNKING_README.md` |
| **One-liner** | `get_embedding_with_auto_chunking(audio_bytes)` |
| **Examples** | `audio_chunking_examples.py` |
| **Integration** | `AUDIO_CHUNKING_INTEGRATION.py` |
| **API docs** | `AUDIO_CHUNKING_README.md` → API Reference |
| **Run tests** | `python test_audio_chunking.py` |

---

**Remember:** Start simple with `get_embedding_with_auto_chunking()` - it handles most cases!
