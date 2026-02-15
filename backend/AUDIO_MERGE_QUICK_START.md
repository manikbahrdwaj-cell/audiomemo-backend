# Audio Merge & Embedding Generation - Quick Reference

## What's New?

The Enrollment Service now supports **audio merging** and **embedding generation from merged audio**.

## Quick Start

### Option 1: Use Merged Audio (Recommended)

```python
from enrollment_service import create_enrollment_session, EnrollmentSessionConfig, MergeMode

# Configure to merge audio
config = EnrollmentSessionConfig(
    max_chunks=5,
    merge_audio=True,              # Enable audio merging
    audio_merge_mode=MergeMode.CROSSFADE,
    merge_embeddings=False,        # Don't merge embeddings
    auto_process=False             # Skip per-chunk embeddings
)

# Create session
session = create_enrollment_session("+1-555-0123", config)

# Add audio chunks
for audio_file in ["chunk1.wav", "chunk2.wav", "chunk3.wav"]:
    audio = load_audio(audio_file)
    session.add_chunk(audio, duration_seconds=2.0)

# Finalize - automatically merges audio and generates embedding
success, message, embedding = session.finalize_enrollment()
```

### Option 2: Default (Separate Embeddings)

```python
# Default config - generates embedding per chunk, then merges them
config = EnrollmentSessionConfig(
    max_chunks=5,
    merge_audio=False,             # Don't merge audio (default)
    merge_embeddings=True          # Merge embeddings instead
)

session = create_enrollment_session("+1-555-0123", config)
# ... add chunks and finalize
```

## Available Merge Modes

| Mode | Best For | Notes |
|------|----------|-------|
| `CONCATENATE` | Simple joining | Fastest, no smoothing |
| `OVERLAP` | Continuous speech | Averaging in overlap regions |
| `CROSSFADE` | High quality | Smooth fading (recommended) |
| `MIX` | Special cases | Weighted averaging |

## API Functions

```python
from enrollment_service import (
    create_enrollment_session,
    merge_audio_chunks,
    generate_embedding_from_merged_audio,
    merge_and_generate_embedding
)

# Manual step-by-step control:
success, msg, audio = merge_audio_chunks(session_id)
success, msg, embedding = generate_embedding_from_merged_audio(session_id)

# Or all-in-one:
success, msg, embedding = merge_and_generate_embedding(session_id)
```

## Session Configuration

```python
from enrollment_service import EnrollmentSessionConfig, MergeMode

config = EnrollmentSessionConfig(
    # Basic settings
    max_chunks=5,
    min_chunks_required=2,
    
    # NEW: Audio merge options
    merge_audio=True,                      # Enable audio merging
    audio_merge_mode=MergeMode.OVERLAP,    # Merge strategy
    audio_merge_crossfade_ms=100.0,        # Fade duration (if CROSSFADE)
    
    # Optional: Also generate per-chunk embeddings
    merge_embeddings=False,                # Don't merge embeddings
    auto_process=False                     # Don't auto-generate per-chunk
)
```

## Examples

### Example 1: Real-time Enrollment

```python
config = EnrollmentSessionConfig(
    merge_audio=True,
    audio_merge_mode=MergeMode.CROSSFADE,
    max_chunks=4
)

session = create_enrollment_session(phone_number, config)

for live_chunk in audio_stream:
    session.add_chunk(live_chunk.audio, live_chunk.duration)
    
    if len(session.chunks) >= 3:
        # User says "done", finalize
        success, msg, _ = session.finalize_enrollment()
        break
```

### Example 2: Batch Enrollment

```python
audio_files = ["voice1.wav", "voice2.wav", "voice3.wav"]

session = create_enrollment_session(
    "+1-555-0001",
    EnrollmentSessionConfig(merge_audio=True)
)

for audio_file in audio_files:
    audio, sr = load_audio_file(audio_file)
    session.add_chunk(audio, duration_seconds=len(audio) / sr)

success, msg, _ = session.finalize_enrollment()
print(f"✓ Enrollment complete: {msg}")
```

### Example 3: Manual Control

```python
session = create_enrollment_session(phone_number)

# Collect chunks
for chunk in chunks:
    session.add_chunk(chunk.audio, chunk.duration)

# Manually merge
success, msg, merged = merge_audio_chunks(session.session_id)
print(f"Merged audio: {len(merged)} samples ({len(merged)/16000:.2f}s)")

# Manually generate embedding
success, msg, emb = generate_embedding_from_merged_audio(session.session_id)
print(f"Embedding shape: {emb.shape}")
```

## Key Benefits

✅ **Better Representation** - Single embedding from natural continuous audio  
✅ **Flexible** - Choose between audio merge or embedding merge  
✅ **Configurable** - Multiple merge modes and parameters  
✅ **Backward Compatible** - Existing code continues to work  
✅ **Better Quality** - Crossfade mode provides smooth transitions  

## Session Summary

After finalization, check the summary:

```python
summary = session.get_summary()

print(f"Status: {summary['status']}")
print(f"Chunks: {summary['chunks_collected']}")
print(f"Merged audio: {summary['has_merged_audio']}")
print(f"Merged audio duration: {summary['merged_audio_duration_seconds']:.2f}s")
print(f"Audio merge mode: {summary['audio_merge_mode']}")
```

## Troubleshooting

**Q: No merged audio?**
```python
if not session.merged_audio:
    success, msg, audio = merge_audio_chunks(session.session_id)
```

**Q: Want per-chunk embeddings too?**
```python
config = EnrollmentSessionConfig(
    merge_audio=True,           # Merge audio
    auto_process=True,          # Also generate per-chunk embeddings
    merge_embeddings=True       # And merge them too
)
```

**Q: How to debug?**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Now see detailed logs of merge operations
```

## Performance

- Merge 3 audio chunks: ~50ms
- Generate embedding: ~200ms
- Total workflow: ~250ms

## Next Steps

- See `AUDIO_MERGE_EMBEDDING_GUIDE.md` for detailed documentation
- Run `enrollment_audio_merge_demo.py` for live examples
- Check `test_enrollment_service.py` for test cases
