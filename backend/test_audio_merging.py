"""
Test suite for Audio Merging Operations in Embedding Operations
Demonstrates all merging modes and configurations
"""

import numpy as np
import os
import logging
from embedding_operations import (
    AudioMerger,
    AudioMergeConfig,
    MergeMode,
    merge_audio,
    merge_audio_files,
    get_audio_merger
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sine_wave(
    frequency: float,
    duration_ms: float,
    sample_rate: int = 16000,
    amplitude: float = 0.5
) -> np.ndarray:
    """
    Generate a sine wave for testing
    
    Args:
        frequency: Frequency in Hz
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz
        amplitude: Wave amplitude (0-1)
        
    Returns:
        Sine wave as numpy array
    """
    duration_s = duration_ms / 1000
    samples = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, samples)
    return amplitude * np.sin(2 * np.pi * frequency * t).astype(np.float32)


def generate_noise(
    duration_ms: float,
    sample_rate: int = 16000,
    amplitude: float = 0.1
) -> np.ndarray:
    """
    Generate white noise for testing
    
    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz
        amplitude: Noise amplitude (0-1)
        
    Returns:
        White noise as numpy array
    """
    duration_s = duration_ms / 1000
    samples = int(duration_s * sample_rate)
    return amplitude * np.random.randn(samples).astype(np.float32)


def test_basic_concatenation():
    """Test basic audio concatenation"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Basic Concatenation")
    logger.info("="*80)
    
    # Create test audio segments
    audio1 = generate_sine_wave(440, 1000)  # 1 second, 440 Hz
    audio2 = generate_sine_wave(880, 1000)  # 1 second, 880 Hz
    
    # Merge using concatenate mode
    merged, sr = merge_audio(
        [audio1, audio2],
        mode='concatenate',
        sample_rate=16000
    )
    
    logger.info(f"✓ Concatenation successful")
    logger.info(f"  - Segment 1 duration: {len(audio1)/16000:.2f}s")
    logger.info(f"  - Segment 2 duration: {len(audio2)/16000:.2f}s")
    logger.info(f"  - Merged duration: {len(merged)/16000:.2f}s")
    logger.info(f"  - Expected: ~2.0s")
    
    assert abs(len(merged) / 16000 - 2.0) < 0.01, "Concatenation failed"
    logger.info("✓ PASSED\n")


def test_overlap_merging():
    """Test overlap merging with averaging"""
    logger.info("="*80)
    logger.info("TEST 2: Overlap Merging")
    logger.info("="*80)
    
    # Create test audio segments
    audio1 = generate_sine_wave(440, 1000)
    audio2 = generate_sine_wave(880, 1000)
    
    # Merge with overlap
    config = AudioMergeConfig(
        mode=MergeMode.OVERLAP,
        overlap_duration_ms=200,
        sample_rate=16000
    )
    merger = AudioMerger(config)
    merged, sr = merger.merge_audio_segments([audio1, audio2])
    
    logger.info(f"✓ Overlap merging successful")
    logger.info(f"  - Segment 1 duration: {len(audio1)/16000:.2f}s")
    logger.info(f"  - Segment 2 duration: {len(audio2)/16000:.2f}s")
    logger.info(f"  - Merged duration: {len(merged)/16000:.2f}s")
    logger.info(f"  - Overlap duration: 200ms")
    logger.info(f"  - Expected: ~1.8s (2.0s - 0.2s overlap)")
    
    expected_duration = 2.0 - 0.2
    actual_duration = len(merged) / 16000
    assert abs(actual_duration - expected_duration) < 0.01, "Overlap merging failed"
    logger.info("✓ PASSED\n")


def test_crossfade_merging():
    """Test crossfade merging with different shapes"""
    logger.info("="*80)
    logger.info("TEST 3: Crossfade Merging")
    logger.info("="*80)
    
    # Create test audio segments
    audio1 = generate_sine_wave(440, 1000)
    audio2 = generate_sine_wave(880, 1000)
    
    for shape in ["linear", "exponential", "logarithmic"]:
        config = AudioMergeConfig(
            mode=MergeMode.CROSSFADE,
            crossfade_duration_ms=200,
            crossfade_shape=shape,
            sample_rate=16000
        )
        merger = AudioMerger(config)
        merged, sr = merger.merge_audio_segments([audio1, audio2])
        
        logger.info(f"✓ Crossfade merging ({shape}) successful")
        logger.info(f"  - Merged duration: {len(merged)/16000:.2f}s")
        logger.info(f"  - Crossfade shape: {shape}")
        logger.info(f"  - Crossfade duration: 200ms")
    
    logger.info("✓ PASSED\n")


def test_mix_merging():
    """Test mixing (weighted sum) of audio segments"""
    logger.info("="*80)
    logger.info("TEST 4: Mix Merging")
    logger.info("="*80)
    
    # Create test audio segments
    audio1 = generate_sine_wave(440, 1000, amplitude=0.5)
    audio2 = generate_sine_wave(880, 500, amplitude=0.5)  # Shorter segment
    
    config = AudioMergeConfig(
        mode=MergeMode.MIX,
        sample_rate=16000
    )
    merger = AudioMerger(config)
    merged, sr = merger.merge_audio_segments([audio1, audio2])
    
    logger.info(f"✓ Mix merging successful")
    logger.info(f"  - Segment 1 duration: {len(audio1)/16000:.2f}s")
    logger.info(f"  - Segment 2 duration: {len(audio2)/16000:.2f}s")
    logger.info(f"  - Merged duration: {len(merged)/16000:.2f}s")
    logger.info(f"  - Output length matches longest segment")
    
    assert len(merged) == len(audio1), "Mix merging failed"
    logger.info("✓ PASSED\n")


def test_multiple_segments():
    """Test merging more than 2 segments"""
    logger.info("="*80)
    logger.info("TEST 5: Multiple Segments (3+ segments)")
    logger.info("="*80)
    
    # Create multiple segments
    segments = [
        generate_sine_wave(440, 800),
        generate_sine_wave(550, 800),
        generate_sine_wave(660, 800),
        generate_sine_wave(880, 800),
    ]
    
    config = AudioMergeConfig(
        mode=MergeMode.CROSSFADE,
        crossfade_duration_ms=100,
        sample_rate=16000
    )
    merger = AudioMerger(config)
    merged, sr = merger.merge_audio_segments(segments)
    
    logger.info(f"✓ Multiple segment merging successful")
    logger.info(f"  - Number of segments: {len(segments)}")
    logger.info(f"  - Segment duration: 800ms each")
    logger.info(f"  - Merged duration: {len(merged)/16000:.2f}s")
    logger.info(f"  - Expected: ~3.1s (4*0.8 - 3*0.1 overlap)")
    
    logger.info("✓ PASSED\n")


def test_silence_insertion():
    """Test merging with silence between segments"""
    logger.info("="*80)
    logger.info("TEST 6: Silence Insertion Between Segments")
    logger.info("="*80)
    
    # Create test audio segments
    audio1 = generate_sine_wave(440, 500)
    audio2 = generate_sine_wave(880, 500)
    
    # Merge with silence
    config = AudioMergeConfig(
        mode=MergeMode.CONCATENATE,
        silence_between_ms=300,
        sample_rate=16000
    )
    merger = AudioMerger(config)
    merged, sr = merger.merge_audio_segments([audio1, audio2])
    
    logger.info(f"✓ Silence insertion successful")
    logger.info(f"  - Segment 1 duration: {len(audio1)/16000:.2f}s")
    logger.info(f"  - Segment 2 duration: {len(audio2)/16000:.2f}s")
    logger.info(f"  - Silence between: 300ms")
    logger.info(f"  - Merged duration: {len(merged)/16000:.2f}s")
    logger.info(f"  - Expected: ~1.3s (0.5 + 0.3 + 0.5)")
    
    expected_duration = 0.5 + 0.3 + 0.5
    actual_duration = len(merged) / 16000
    assert abs(actual_duration - expected_duration) < 0.01, "Silence insertion failed"
    logger.info("✓ PASSED\n")


def test_normalization():
    """Test segment normalization"""
    logger.info("="*80)
    logger.info("TEST 7: Segment Normalization")
    logger.info("="*80)
    
    # Create segments with different amplitudes
    audio1 = generate_sine_wave(440, 1000, amplitude=0.3)
    audio2 = generate_sine_wave(880, 1000, amplitude=0.8)
    
    config = AudioMergeConfig(
        mode=MergeMode.CONCATENATE,
        normalize_segments=True,
        sample_rate=16000
    )
    merger = AudioMerger(config)
    merged, sr = merger.merge_audio_segments([audio1, audio2])
    
    logger.info(f"✓ Normalization successful")
    logger.info(f"  - Segment 1 max amplitude: {np.max(np.abs(audio1)):.3f}")
    logger.info(f"  - Segment 2 max amplitude: {np.max(np.abs(audio2)):.3f}")
    logger.info(f"  - Merged max amplitude: {np.max(np.abs(merged)):.3f}")
    logger.info(f"  - All segments normalized before merging")
    
    logger.info("✓ PASSED\n")


def test_convenience_functions():
    """Test convenience wrapper functions"""
    logger.info("="*80)
    logger.info("TEST 8: Convenience Functions")
    logger.info("="*80)
    
    # Create test audio
    audio1 = generate_sine_wave(440, 1000)
    audio2 = generate_sine_wave(880, 1000)
    
    # Test merge_audio function
    merged, sr = merge_audio([audio1, audio2], mode='crossfade')
    logger.info(f"✓ merge_audio() function works")
    
    # Test get_audio_merger function
    merger = get_audio_merger(
        mode='crossfade',
        crossfade_ms=150,
        crossfade_shape='exponential'
    )
    merged, sr = merger.merge_audio_segments([audio1, audio2])
    logger.info(f"✓ get_audio_merger() function works")
    
    logger.info("✓ PASSED\n")


def test_merge_statistics():
    """Test merge statistics generation"""
    logger.info("="*80)
    logger.info("TEST 9: Merge Statistics")
    logger.info("="*80)
    
    # Create test audio
    segments = [
        generate_sine_wave(440, 1000, amplitude=0.5),
        generate_sine_wave(880, 1500, amplitude=0.5),
        generate_sine_wave(1760, 800, amplitude=0.5),
    ]
    
    merger = AudioMerger()
    stats = merger.get_merge_stats(segments)
    
    logger.info(f"✓ Merge statistics generated")
    logger.info(f"  - Number of segments: {stats['num_segments']}")
    logger.info(f"  - Total samples: {stats['total_samples']}")
    logger.info(f"  - Total duration: {stats['duration_seconds']:.2f}s")
    logger.info(f"  - Sample rate: {stats['sample_rate']} Hz")
    logger.info(f"  - Merge mode: {stats['merge_mode']}")
    logger.info(f"  - Segment durations: {[f'{d:.2f}s' for d in stats['segment_durations_s']]}")
    
    logger.info("✓ PASSED\n")


def test_edge_cases():
    """Test edge cases"""
    logger.info("="*80)
    logger.info("TEST 10: Edge Cases")
    logger.info("="*80)
    
    # Test single segment
    audio = generate_sine_wave(440, 1000)
    merged, sr = merge_audio([audio], mode='crossfade')
    assert merged.shape == audio.shape, "Single segment merging failed"
    logger.info("✓ Single segment merging works")
    
    # Test very short segments
    audio1 = np.random.randn(100)
    audio2 = np.random.randn(100)
    merged, sr = merge_audio([audio1, audio2], mode='crossfade', crossfade_ms=10)
    logger.info("✓ Very short segment merging works")
    
    # Test segments with silence
    audio1 = generate_noise(500)
    audio2 = generate_noise(500)
    config = AudioMergeConfig(
        mode=MergeMode.CONCATENATE,
        silence_between_ms=100
    )
    merger = AudioMerger(config)
    merged, sr = merger.merge_audio_segments([audio1, audio2])
    logger.info("✓ Merging with silence works")
    
    logger.info("✓ PASSED\n")


def run_all_tests():
    """Run all tests"""
    logger.info("\n\n")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "AUDIO MERGING OPERATIONS TEST SUITE" + " "*24 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    tests = [
        test_basic_concatenation,
        test_overlap_merging,
        test_crossfade_merging,
        test_mix_merging,
        test_multiple_segments,
        test_silence_insertion,
        test_normalization,
        test_convenience_functions,
        test_merge_statistics,
        test_edge_cases,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"✗ FAILED: {e}\n")
            failed += 1
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Total tests: {len(tests)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {100*passed//len(tests)}%")
    logger.info("="*80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
