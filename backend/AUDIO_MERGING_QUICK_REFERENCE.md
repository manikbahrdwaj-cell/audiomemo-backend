# Audio Merging - Quick Reference

## Installation

Already integrated into `embedding_operations.py`. Just import:

```python
from embedding_operations import merge_audio, AudioMerger, get_audio_merger
```

## Common Patterns

### Pattern 1: Simple Concatenation
```python
from embedding_operations import merge_audio

merged, sr = merge_audio([audio1, audio2])
# Duration: duration1 + duration2
```

### Pattern 2: Professional Crossfade
```python
from embedding_operations import merge_audio

merged, sr = merge_audio(
    [audio1, audio2],
    mode='crossfade',
    crossfade_ms=150
)
# Creates smooth transition with 150ms crossfade
```

### Pattern 3: Multiple Files
```python
from embedding_operations import merge_audio_files

merged, sr = merge_audio_files(
    ['audio1.wav', 'audio2.wav', 'audio3.wav'],
    mode='crossfade',
    output_path='merged.wav'
)
```

### Pattern 4: Custom Configuration
```python
from embedding_operations import get_audio_merger

merger = get_audio_merger(
    mode='crossfade',
    sample_rate=16000,
    crossfade_ms=200,
    crossfade_shape='exponential',
    normalize=True,
    silence_between_ms=100
)

merged, sr = merger.merge_audio_segments([audio1, audio2, audio3])
```

### Pattern 5: Full Control with Statistics
```python
from embedding_operations import AudioMerger, AudioMergeConfig, MergeMode

config = AudioMergeConfig(
    mode=MergeMode.CROSSFADE,
    sample_rate=16000,
    crossfade_duration_ms=200
)
merger = AudioMerger(config)

# Check stats before merging
segments = [audio1, audio2, audio3]
stats = merger.get_merge_stats(segments)
print(f"Output duration: ~{stats['duration_seconds']:.2f}s")

# Perform merge
merged, sr = merger.merge_audio_segments(segments)

# Save result
merger.save_merged_audio(merged, sr, 'output.wav')
```

## Mode Comparison

| Mode | Use Case | Duration | Quality | Speed |
|------|----------|----------|---------|-------|
| **concatenate** | Quick merge, acceptable boundaries | sum | ⭐⭐ | ⭐⭐⭐ |
| **overlap** | Simple smoothing | sum - overlap | ⭐⭐⭐ | ⭐⭐⭐ |
| **crossfade** | Professional audio, voice | sum - crossfade | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **mix** | Layering, multiple speakers | max(lengths) | ⭐⭐⭐ | ⭐⭐⭐ |

## Parameter Guide

```python
merge_audio(
    audio_segments,              # List of np.ndarray or bytes
    mode='concatenate',          # 'concatenate', 'overlap', 'crossfade', 'mix'
    sample_rate=16000,           # Target sample rate (Hz)
    crossfade_ms=100             # Crossfade/overlap duration (milliseconds)
)
```

```python
get_audio_merger(
    mode='concatenate',          # Merge strategy
    sample_rate=16000,           # Target sample rate
    crossfade_ms=100,            # Crossfade duration
    overlap_ms=100,              # Overlap duration
    crossfade_shape='linear',    # 'linear', 'exponential', 'logarithmic'
    normalize=True,              # Normalize segments
    silence_between_ms=0         # Insert silence between segments
)
```

## Crossfade Shapes

**Linear** (default)
- Constant slope fade
- Most natural sounding for most audio

**Exponential**
- Faster fade-in, slower fade-out
- Good for percussive sounds
- Reduces low-amplitude noise bleed

**Logarithmic**
- Slower fade-in, faster fade-out
- Good for sustained sounds
- Smooth human hearing perception

## Typical Configurations

### Voice Merging (Embeddings)
```python
merger = get_audio_merger(
    mode='crossfade',
    crossfade_ms=150,
    crossfade_shape='linear'
)
```

### Music Concatenation
```python
merger = get_audio_merger(
    mode='crossfade',
    crossfade_ms=300,  # Longer fade for music
    crossfade_shape='exponential'
)
```

### Rapid Consecutive Segments
```python
merger = get_audio_merger(
    mode='overlap',
    overlap_ms=50  # Short overlap
)
```

### Embedding with Silence
```python
merger = get_audio_merger(
    mode='concatenate',
    silence_between_ms=200  # Separate segments
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Clicks/pops at boundaries | Use `crossfade` mode instead of `concatenate` |
| Audio clipping | Enable `normalize=True` |
| Wrong duration | Check `mode` (affects output length) |
| Different sample rates | Specify explicit `sample_rates` parameter |
| Memory usage | Use concatenate mode; avoid mix mode for long audio |

## Integration with Embeddings

```python
from embedding_operations import merge_audio, get_embedding_service

# 1. Merge multiple audio segments
merged, sr = merge_audio(
    [audio1, audio2, audio3],
    mode='crossfade',
    crossfade_ms=150
)

# 2. Generate embedding from merged audio
service = get_embedding_service()
embedding, metrics = service.generate(merged, "user_id")

# 3. Use for voice verification
comparison = service.compare(embedding, enrolled_embedding, "user_id", "enrolled_id")
print(f"Match: {comparison.is_match}, Confidence: {comparison.confidence:.3f}")
```

## Performance Tips

1. **Use concatenate mode** when audio quality isn't critical
2. **Batch process** multiple merge operations
3. **Cache merged results** if reused frequently
4. **Specify sample rates** explicitly to avoid auto-detection overhead
5. **Normalize before merging** to prevent clipping computations

## Testing

Run comprehensive tests:
```bash
python test_audio_merging.py
```

Current status: **10/10 tests passing** ✅

## API Summary

| Function | Purpose |
|----------|---------|
| `merge_audio(...)` | Quick merge function |
| `merge_audio_files(...)` | Merge from files |
| `get_audio_merger(...)` | Get configured merger |
| `AudioMerger.merge_audio_segments(...)` | Main merge method |
| `AudioMerger.merge_from_files(...)` | Merge files |
| `AudioMerger.save_merged_audio(...)` | Save to file |
| `AudioMerger.get_merge_stats(...)` | Get statistics |

## Examples by Use Case

### ✅ Speaker Embedding
```python
merged, sr = merge_audio(segments, mode='crossfade', crossfade_ms=150)
embedding, metrics = get_embedding_service().generate(merged, "user_id")
```

### ✅ Multi-turn Conversation
```python
merger = get_audio_merger(mode='concatenate', silence_between_ms=200)
merged, sr = merger.merge_audio_segments(turn_segments)
```

### ✅ Data Augmentation
```python
merger = get_audio_merger(mode='mix')
augmented, sr = merger.merge_audio_segments([audio1, audio2])
```

### ✅ Audio Concatenation
```python
merged, sr = merge_audio_files(file_list, output_path='output.wav')
```

---

**Last Updated:** February 14, 2026
**Status:** ✅ Fully Implemented and Tested
