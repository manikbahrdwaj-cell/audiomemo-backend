# Audio Merging Operations Guide

## Overview

The **Audio Merging** functionality provides advanced capabilities for concatenating and merging multiple audio segments with various strategies. This is particularly useful for embedding operations where you need to combine audio from multiple sources, handle different sample rates, and apply smooth transitions between segments.

## Features

✅ **Multiple Merge Modes**
- **Concatenate**: Direct concatenation of segments
- **Overlap**: Automatic overlap with averaging
- **Crossfade**: Smooth transitions with customizable fade shapes
- **Mix**: Audio mixing (weighted sum)

✅ **Advanced Audio Processing**
- Automatic sample rate detection and resampling
- Segment normalization to prevent clipping
- Silence insertion between segments
- Crossfade shape options (linear, exponential, logarithmic)

✅ **Quality Preservation**
- Dynamic normalization with clipping prevention
- Support for both numpy arrays and audio bytes
- Configurable overlap and crossfade durations
- Statistics and metadata tracking

## Quick Start

### Basic Concatenation

```python
from embedding_operations import merge_audio
import numpy as np

# Create two audio segments
audio1 = np.random.randn(16000)  # 1 second at 16kHz
audio2 = np.random.randn(16000)

# Simple concatenation
merged_audio, sample_rate = merge_audio([audio1, audio2], mode='concatenate')
print(f"Merged duration: {len(merged_audio) / sample_rate:.2f}s")  # ~2.0s
```

### Smooth Crossfading

```python
from embedding_operations import merge_audio

# Merge with crossfade
merged_audio, sr = merge_audio(
    [audio1, audio2],
    mode='crossfade',
    crossfade_ms=200  # 200ms crossfade
)
print(f"Merged duration: {len(merged_audio) / sr:.2f}s")  # ~1.8s
```

### Advanced Configuration

```python
from embedding_operations import get_audio_merger, MergeMode

# Create a configured merger
merger = get_audio_merger(
    mode='crossfade',
    sample_rate=16000,
    crossfade_ms=150,
    crossfade_shape='exponential',
    normalize=True,
    silence_between_ms=100
)

# Use the merger
merged_audio, sr = merger.merge_audio_segments([audio1, audio2, audio3])
```

## API Reference

### Main Classes

#### `AudioMergeConfig`

Configuration dataclass for audio merging operations.

**Parameters:**
- `mode` (MergeMode, default=CONCATENATE): Merge strategy to use
- `sample_rate` (int, default=16000): Target sample rate in Hz
- `crossfade_duration_ms` (float, default=100): Duration of crossfade in milliseconds
- `overlap_duration_ms` (float, default=100): Duration of overlap in milliseconds
- `crossfade_shape` (str, default="linear"): Fade curve shape
  - `"linear"`: Linear interpolation
  - `"exponential"`: e^(-x) style curve
  - `"logarithmic"`: Logarithmic curve
- `normalize_segments` (bool, default=True): Normalize each segment before merging
- `silence_between_ms` (float, default=0): Add silence between segments
- `pad_missing_sample_rate` (bool, default=True): Auto-resample if needed

**Example:**
```python
from embedding_operations import AudioMergeConfig, MergeMode

config = AudioMergeConfig(
    mode=MergeMode.CROSSFADE,
    sample_rate=16000,
    crossfade_duration_ms=200,
    crossfade_shape='exponential'
)
```

#### `AudioMerger`

Main class for audio merging operations.

**Methods:**

##### `__init__(config: Optional[AudioMergeConfig] = None)`

Initialize an AudioMerger with optional configuration.

```python
from embedding_operations import AudioMerger, AudioMergeConfig, MergeMode

config = AudioMergeConfig(mode=MergeMode.CROSSFADE)
merger = AudioMerger(config)
```

##### `merge_audio_segments(audio_segments, sample_rates=None) -> Tuple[np.ndarray, int]`

Merge multiple audio segments according to configured mode.

**Parameters:**
- `audio_segments` (List[Union[np.ndarray, bytes]]): Audio data to merge
- `sample_rates` (Optional[List[int]]): Sample rates for each segment (auto-detected if None)

**Returns:**
- Tuple of (merged_audio_array, sample_rate)

**Example:**
```python
merger = AudioMerger()
merged_audio, sr = merger.merge_audio_segments([audio1, audio2])
```

##### `merge_from_files(file_paths: List[str]) -> Tuple[np.ndarray, int]`

Merge audio from multiple files directly.

**Parameters:**
- `file_paths` (List[str]): Paths to audio files

**Returns:**
- Tuple of (merged_audio_array, sample_rate)

**Example:**
```python
merged_audio, sr = merger.merge_from_files(['audio1.wav', 'audio2.wav', 'audio3.wav'])
```

##### `save_merged_audio(audio, sample_rate, output_path, format='wav')`

Save merged audio to a file.

**Parameters:**
- `audio` (np.ndarray): Audio waveform
- `sample_rate` (int): Sample rate
- `output_path` (str): Path to save file
- `format` (str): Audio format ('wav', 'mp3', 'flac')

**Example:**
```python
merged_audio, sr = merger.merge_audio_segments([audio1, audio2])
merger.save_merged_audio(merged_audio, sr, 'output.wav')
```

##### `get_merge_stats(audio_arrays: List[np.ndarray]) -> Dict[str, any]`

Get statistics about audio segments before merging.

**Returns:**
Dictionary with keys:
- `num_segments`: Number of segments
- `total_samples`: Total sample count
- `duration_seconds`: Total duration
- `sample_rate`: Sample rate
- `merge_mode`: Current merge mode
- `segment_lengths`: List of segment lengths in samples
- `segment_durations_s`: List of segment durations in seconds

**Example:**
```python
stats = merger.get_merge_stats([audio1, audio2, audio3])
print(f"Total duration: {stats['duration_seconds']:.2f}s")
```

### Convenience Functions

#### `merge_audio(audio_segments, mode='concatenate', sample_rate=16000, crossfade_ms=100) -> Tuple[np.ndarray, int]`

Quick function to merge audio segments without creating a AudioMerger instance.

```python
merged, sr = merge_audio([audio1, audio2], mode='crossfade', crossfade_ms=150)
```

#### `merge_audio_files(file_paths, mode='concatenate', sample_rate=16000, crossfade_ms=100, output_path=None) -> Tuple[np.ndarray, int]`

Quick function to merge audio from files.

```python
merged, sr = merge_audio_files(
    ['audio1.wav', 'audio2.wav'],
    mode='crossfade',
    output_path='merged.wav'
)
```

#### `get_audio_merger(mode='concatenate', sample_rate=16000, ...) -> AudioMerger`

Get a pre-configured AudioMerger instance.

```python
merger = get_audio_merger(
    mode='crossfade',
    crossfade_ms=200,
    crossfade_shape='exponential'
)
```

### Enumerations

#### `MergeMode`

Audio merging mode enumeration.

**Values:**
- `CONCATENATE`: Direct concatenation
- `OVERLAP`: With overlapping regions
- `CROSSFADE`: Smooth crossfading
- `MIX`: Mixing (weighted sum)

```python
from embedding_operations import MergeMode

print(MergeMode.CROSSFADE.value)  # "crossfade"
```

## Merge Mode Details

### 1. Concatenate Mode

Direct concatenation of audio segments end-to-end.

**Characteristics:**
- Fastest merge operation
- Direct adjacency (can create clicks at boundaries)
- Optional silence insertion between segments
- Output duration = sum of all segment durations + silence

**Use Cases:**
- Combining pre-recorded segments where boundaries are acceptable
- Building audio databases
- Sequential concatenation without smoothing

**Example:**
```python
merged, sr = merge_audio([audio1, audio2], mode='concatenate')
```

### 2. Overlap Mode

Merges segments with overlapping regions using simple averaging.

**Characteristics:**
- Overlapping regions are averaged
- Reduces clicks at boundaries
- Output duration = sum - overlap * (n_segments - 1)
- Configurable overlap duration

**Use Cases:**
- Smooth merging without sophisticated crossfading
- When segments have natural overlap region
- Fast boundary smoothing

**Example:**
```python
merger = get_audio_merger(
    mode='overlap',
    overlap_ms=200
)
merged, sr = merger.merge_audio_segments([audio1, audio2])
```

### 3. Crossfade Mode

Smooth transitions between segments using envelope crossfading.

**Characteristics:**
- Clean transitions with customizable envelope shapes
- Three fade curve options: linear, exponential, logarithmic
- Output duration = sum - crossfade * (n_segments - 1)
- Professional-grade audio merging

**Use Cases:**
- Voice/speech merging for embeddings
- Music concatenation
- Professional audio post-processing
- Building high-quality training data

**Example:**
```python
merger = get_audio_merger(
    mode='crossfade',
    crossfade_ms=150,
    crossfade_shape='exponential'
)
merged, sr = merger.merge_audio_segments([audio1, audio2])
```

### 4. Mix Mode

Combines segments by mixing (weighted sum).

**Characteristics:**
- Equal weighting for all segments
- Output duration = max segment duration
- Shorter segments padded with zeros
- Creates overlayed audio

**Use Cases:**
- Combining multiple speaker voices
- Audio layering and blending
- Building composite audio samples
- Parallel speaker embeddings

**Example:**
```python
merged, sr = merge_audio([audio1, audio2], mode='mix')
```

## Advanced Usage

### Working with Different Sample Rates

```python
from embedding_operations import AudioMerger

# Audio segments with different sample rates
audio1_16k = np.random.randn(16000)  # 16 kHz
audio2_8k = np.random.randn(8000)    # 8 kHz

merger = AudioMerger()
# Automatically resamples audio2 to 16 kHz
merged, sr = merger.merge_audio_segments(
    [audio1_16k, audio2_8k],
    sample_rates=[16000, 8000]
)
```

### Adding Silence Between Segments

```python
from embedding_operations import get_audio_merger

merger = get_audio_merger(
    mode='concatenate',
    silence_between_ms=500  # 500ms silence
)
merged, sr = merger.merge_audio_segments([audio1, audio2, audio3])
```

### Custom Crossfade Shapes

```python
from embedding_operations import get_audio_merger

# Linear crossfade (standard)
merger_linear = get_audio_merger(
    mode='crossfade',
    crossfade_shape='linear',
    crossfade_ms=200
)

# Exponential crossfade (faster transition in)
merger_exp = get_audio_merger(
    mode='crossfade',
    crossfade_shape='exponential',
    crossfade_ms=200
)

# Logarithmic crossfade (slower transition in)
merger_log = get_audio_merger(
    mode='crossfade',
    crossfade_shape='logarithmic',
    crossfade_ms=200
)
```

### Batch Merging with Statistics

```python
from embedding_operations import AudioMerger

merger = AudioMerger()

# Get pre-merge statistics
segments = [audio1, audio2, audio3]
stats = merger.get_merge_stats(segments)

print(f"Segments: {stats['num_segments']}")
print(f"Total duration: {stats['duration_seconds']:.2f}s")
print(f"Segment durations: {stats['segment_durations_s']}")

# Perform merge
merged, sr = merger.merge_audio_segments(segments)
```

### Save Merged Audio

```python
from embedding_operations import AudioMerger

merger = AudioMerger()
merged, sr = merger.merge_audio_segments([audio1, audio2])

# Save in different formats
merger.save_merged_audio(merged, sr, 'output.wav', format='wav')
merger.save_merged_audio(merged, sr, 'output.mp3', format='mp3')
merger.save_merged_audio(merged, sr, 'output.flac', format='flac')
```

## Integration with Embedding Operations

### Merging Audio Before Embedding

```python
from embedding_operations import merge_audio, get_embedding_service

# Merge multiple audio segments
merged_audio, sr = merge_audio(
    [audio1, audio2, audio3],
    mode='crossfade'
)

# Generate embedding from merged audio
service = get_embedding_service()
embedding, metrics = service.generate(merged_audio, "user_123")

print(f"Embedding quality: {metrics.quality_score:.3f}")
```

### Processing Multiple Audio Sources

```python
from embedding_operations import AudioMerger, AudioMergeConfig, MergeMode, merge_audio_files

# Merge audio files from different sources
config = AudioMergeConfig(
    mode=MergeMode.CROSSFADE,
    crossfade_duration_ms=200,
    normalize_segments=True
)

merger = AudioMerger(config)

# Merge from files
merged_audio, sr = merger.merge_from_files([
    'speaker1_segment1.wav',
    'speaker1_segment2.wav',
    'speaker1_segment3.wav'
])

# Save merged audio
merger.save_merged_audio(merged_audio, sr, 'speaker1_merged.wav')

# Can now be used for embedding generation
```

## Best Practices

1. **Choose Appropriate Merge Mode**
   - Use `concatenate` for speed with acceptable boundaries
   - Use `overlap` for simple boundary smoothing
   - Use `crossfade` for professional-quality audio
   - Use `mix` for audio layering and blending

2. **Handle Sample Rates**
   - Always specify target sample rate to avoid confusion
   - Audio Merger can auto-resample, but explicit is safer
   - Keep sample rates consistent within embedding workflows

3. **Normalize Segments**
   - Enable `normalize_segments=True` to prevent clipping
   - AudioMerger automatically handles final normalization
   - Monitor for clipping in output

4. **Crossfade Durations**
   - Typical range: 100-300ms for voice audio
   - Longer fades = smoother transitions but reduced total content
   - Exponential/logarithmic shapes work better for voice

5. **Quality Assurance**
   - Use `get_merge_stats()` to verify expected output
   - Check final audio for clipping or artifacts
   - Validate embeddings after merging with quality metrics

## Performance Considerations

- **Concatenate**: O(n) - linear time, minimal memory
- **Overlap**: O(n) - linear time with averaging overhead
- **Crossfade**: O(n) - linear time with envelope computation
- **Mix**: O(n) - linear memory for max-length output

For large-scale operations, consider:
- Batch processing with multiple workers
- Caching common merges
- Using concatenate mode when professional audio quality isn't critical

## Troubleshooting

### Audio Clipping After Merge

**Problem:** Output audio has clipping/distortion

**Solution:**
1. Enable segment normalization: `normalize_segments=True`
2. AudioMerger applies 5% safety margin automatically
3. Check individual segment amplitudes
4. Use lower amplitude in mix mode

### Boundary Clicks

**Problem:** Hearing clicks/pops at segment boundaries

**Solution:**
1. Switch from concatenate to crossfade: `mode='crossfade'`
2. Increase crossfade duration: `crossfade_ms=200+`
3. Try exponential or logarithmic fade shapes
4. Ensure consistent audio properties in segments

### Sample Rate Mismatches

**Problem:** Unexpected output duration or quality issues

**Solution:**
1. Enable auto-resampling: `pad_missing_sample_rate=True` (default)
2. Explicitly specify segment sample rates
3. Ensure consistent sample rate configuration
4. Check audio file properties before merging

### Memory Usage

**Problem:** High memory consumption with large files

**Solution:**
1. Process files in batches
2. Use streaming approach if available
3. Consider lower sample rate for non-critical applications
4. Monitor peak memory with `get_merge_stats()`

## Testing

Comprehensive test suite available in `test_audio_merging.py`:

```bash
python test_audio_merging.py
```

Tests cover:
- ✅ Basic concatenation (Test 1)
- ✅ Overlap merging (Test 2)
- ✅ Crossfade with different shapes (Test 3)
- ✅ Mix merging (Test 4)
- ✅ Multiple segments (Test 5)
- ✅ Silence insertion (Test 6)
- ✅ Segment normalization (Test 7)
- ✅ Convenience functions (Test 8)
- ✅ Merge statistics (Test 9)
- ✅ Edge cases (Test 10)

**Current Status:** 10/10 tests passing (100% success rate)

## See Also

- [Embedding Operations Guide](EMBEDDING_OPERATIONS_GUIDE.md)
- [Audio Chunking Documentation](AUDIO_CHUNKING_README.md)
- [Voice Embedding Module](voice_embedding.py)
- [WebSocket Routing Guide](WEBSOCKET_ROUTING_GUIDE.md)
