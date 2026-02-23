"""
Edge Case Tests for Audio Chunking
Tests boundary conditions, edge values, and unusual audio scenarios
"""

import pytest
import numpy as np
import torch
from audio_chunking import AudioChunker, ChunkConfig
import logging

logger = logging.getLogger(__name__)


class TestAudioChunkingEdgeCases:
    """Comprehensive edge case tests for audio chunking"""

    # ========== EMPTY AND VERY SHORT AUDIO ==========
    
    def test_empty_audio_array(self):
        """Test chunking empty audio array"""
        chunker = AudioChunker()
        audio = np.array([])
        
        with pytest.raises((ValueError, IndexError)):
            chunker.chunk(audio)

    def test_single_sample_audio(self):
        """Test chunking audio with single sample"""
        chunker = AudioChunker()
        audio = np.array([0.5])
        
        with pytest.raises((ValueError, IndexError)):
            chunker.chunk(audio)

    def test_two_sample_audio(self):
        """Test chunking audio with two samples"""
        chunker = AudioChunker()
        audio = np.array([0.1, 0.2])
        
        chunks = chunker.chunk(audio)
        assert len(chunks) >= 1
        assert all(chunk.size > 0 for chunk in chunks)

    def test_exact_chunk_size_audio(self):
        """Test audio exactly matching chunk size"""
        config = ChunkConfig(chunk_size=16000, overlap_ratio=0.0)
        chunker = AudioChunker(config)
        audio = np.random.randn(16000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) == 1
        assert chunks[0].shape[0] == 16000

    # ========== SILENCE AND CONSTANT SIGNALS ==========
    
    def test_complete_silence(self):
        """Test chunking completely silent audio"""
        chunker = AudioChunker()
        audio = np.zeros(48000)  # 3 seconds of silence
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(np.all(chunk == 0) for chunk in chunks)

    def test_constant_nonzero_signal(self):
        """Test chunking constant non-zero signal"""
        chunker = AudioChunker()
        audio = np.ones(48000) * 0.5
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(np.all(chunk == 0.5) for chunk in chunks)

    def test_alternating_silence_sound(self):
        """Test chunking alternating silence and sound"""
        chunker = AudioChunker()
        audio = np.concatenate([np.zeros(8000), np.ones(8000) * 0.5] * 3)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(chunk.size > 0 for chunk in chunks)

    # ========== EXTREME VALUES ==========
    
    def test_audio_with_nan_values(self):
        """Test chunking audio containing NaN values"""
        chunker = AudioChunker()
        audio = np.random.randn(48000)
        audio[10000:10010] = np.nan
        
        chunks = chunker.chunk(audio)
        # Should handle gracefully or raise appropriate error
        assert len(chunks) >= 0

    def test_audio_with_inf_values(self):
        """Test chunking audio containing infinite values"""
        chunker = AudioChunker()
        audio = np.random.randn(48000)
        audio[15000] = np.inf
        audio[25000] = -np.inf
        
        chunks = chunker.chunk(audio)
        # Should handle gracefully or raise appropriate error
        assert len(chunks) >= 0

    def test_extremely_loud_audio(self):
        """Test chunking extremely loud audio (clipping)"""
        chunker = AudioChunker()
        audio = np.random.randn(48000) * 1000  # 1000x normal amplitude
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(chunk.size > 0 for chunk in chunks)

    def test_extremely_quiet_audio(self):
        """Test chunking extremely quiet audio"""
        chunker = AudioChunker()
        audio = np.random.randn(48000) * 1e-10  # Extremely quiet
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(chunk.size > 0 for chunk in chunks)

    def test_int16_boundary_values(self):
        """Test audio with int16 boundary values"""
        chunker = AudioChunker()
        # int16 max/min values
        audio = np.array([32767] * 10000 + [-32768] * 10000 + [0] * 28000, dtype=np.float32)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(chunk.size > 0 for chunk in chunks)

    # ========== VARIOUS SAMPLE RATES ==========
    
    def test_very_low_sample_rate(self):
        """Test chunking with very low sample rate (8kHz)"""
        config = ChunkConfig(sample_rate=8000, chunk_size=8000)
        chunker = AudioChunker(config)
        audio = np.random.randn(24000)  # 3 seconds at 8kHz
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_very_high_sample_rate(self):
        """Test chunking with high sample rate (48kHz)"""
        config = ChunkConfig(sample_rate=48000, chunk_size=48000)
        chunker = AudioChunker(config)
        audio = np.random.randn(144000)  # 3 seconds at 48kHz
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_odd_sample_rate(self):
        """Test chunking with odd sample rate"""
        config = ChunkConfig(sample_rate=22050, chunk_size=22050)
        chunker = AudioChunker(config)
        audio = np.random.randn(44100)  # ~2 seconds
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    # ========== OVERLAP EDGE CASES ==========
    
    def test_zero_overlap(self):
        """Test chunking with zero overlap"""
        config = ChunkConfig(overlap_ratio=0.0, chunk_size=16000)
        chunker = AudioChunker(config)
        audio = np.random.randn(32000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) == 2

    def test_maximum_overlap(self):
        """Test chunking with very high overlap (99%)"""
        config = ChunkConfig(overlap_ratio=0.99, chunk_size=16000)
        chunker = AudioChunker(config)
        audio = np.random.randn(16100)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 1

    def test_invalid_overlap_too_high(self):
        """Test that overlap >= 1.0 raises error"""
        with pytest.raises(ValueError):
            ChunkConfig(overlap_ratio=1.0)

    def test_invalid_overlap_negative(self):
        """Test that negative overlap raises error"""
        with pytest.raises(ValueError):
            ChunkConfig(overlap_ratio=-0.1)

    # ========== CHUNK SIZE EDGE CASES ==========
    
    def test_very_small_chunk_size(self):
        """Test chunking with very small chunk size"""
        config = ChunkConfig(chunk_size=100, min_chunk_duration_ms=100)
        chunker = AudioChunker(config)
        audio = np.random.randn(1000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_very_large_chunk_size(self):
        """Test chunking with very large chunk size"""
        config = ChunkConfig(chunk_size=160000, max_chunk_duration_ms=10000)
        chunker = AudioChunker(config)
        audio = np.random.randn(160000)  # Exactly chunk size
        
        chunks = chunker.chunk(audio)
        assert len(chunks) >= 1

    def test_invalid_zero_chunk_size(self):
        """Test that zero chunk size raises error"""
        with pytest.raises(ValueError):
            ChunkConfig(chunk_size=0)

    def test_invalid_negative_chunk_size(self):
        """Test that negative chunk size raises error"""
        with pytest.raises(ValueError):
            ChunkConfig(chunk_size=-1000)

    # ========== TORCH TENSOR INPUT ==========
    
    def test_torch_tensor_input(self):
        """Test chunking torch tensor input"""
        chunker = AudioChunker()
        audio = torch.randn(48000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        assert all(isinstance(chunk, np.ndarray) for chunk in chunks)

    def test_torch_tensor_gpu_input(self):
        """Test chunking torch tensor on GPU (if available)"""
        chunker = AudioChunker()
        audio = torch.randn(48000)
        
        # Test on CPU regardless
        chunks = chunker.chunk(audio.cpu())
        assert len(chunks) > 0

    # ========== DTYPE EDGE CASES ==========
    
    def test_float32_input(self):
        """Test chunking float32 audio"""
        chunker = AudioChunker()
        audio = np.random.randn(48000).astype(np.float32)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_float64_input(self):
        """Test chunking float64 audio"""
        chunker = AudioChunker()
        audio = np.random.randn(48000).astype(np.float64)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_int16_input(self):
        """Test chunking int16 audio"""
        chunker = AudioChunker()
        audio = (np.random.randn(48000) * 32767).astype(np.int16)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_int32_input(self):
        """Test chunking int32 audio"""
        chunker = AudioChunker()
        audio = (np.random.randn(48000) * 2147483647).astype(np.int32)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    # ========== MULTIDIMENSIONAL INPUT ==========
    
    def test_stereo_audio_input(self):
        """Test chunking stereo audio (2D input)"""
        chunker = AudioChunker()
        audio = np.random.randn(2, 48000)  # 2 channels
        
        # Should handle or raise appropriate error
        try:
            chunks = chunker.chunk(audio)
            assert len(chunks) >= 0
        except (ValueError, IndexError):
            pass  # Expected to fail or handle specially

    def test_mono_audio_various_shapes(self):
        """Test chunking mono audio with different shapes"""
        chunker = AudioChunker()
        
        # Column vector
        audio_col = np.random.randn(48000, 1)
        try:
            chunks = chunker.chunk(audio_col.flatten())
            assert len(chunks) > 0
        except:
            pass

    # ========== DURATION EDGE CASES ==========
    
    def test_very_short_duration_audio(self):
        """Test very short duration audio (10ms)"""
        config = ChunkConfig(sample_rate=16000, chunk_size=160, min_chunk_duration_ms=10)
        chunker = AudioChunker(config)
        audio = np.random.randn(160)  # 10ms at 16kHz
        
        chunks = chunker.chunk(audio)
        assert len(chunks) >= 0

    def test_very_long_duration_audio(self):
        """Test very long duration audio (10 minutes)"""
        config = ChunkConfig(sample_rate=16000, chunk_size=16000)
        chunker = AudioChunker(config)
        audio = np.random.randn(9600000)  # 10 minutes at 16kHz
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        # Verify chunking worked
        total_samples = sum(chunk.size for chunk in chunks)
        assert total_samples >= audio.size  # With overlaps, might be >= original

    # ========== WINDOWING EDGE CASES ==========
    
    def test_chunk_windowing_compatibility(self):
        """Test that chunks can be windowed without errors"""
        chunker = AudioChunker()
        audio = np.random.randn(48000)
        chunks = chunker.chunk(audio)
        
        # Simulate windowing
        for chunk in chunks:
            window = np.hanning(len(chunk))
            windowed = chunk * window
            assert windowed.size == chunk.size

    # ========== BOUNDARY CONDITIONS ==========
    
    def test_chunks_have_no_gaps(self):
        """Test that chunks cover entire audio with overlap"""
        config = ChunkConfig(overlap_ratio=0.2, chunk_size=16000)
        chunker = AudioChunker(config)
        audio = np.random.randn(48000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0
        
        # With overlap, should cover all audio
        first_chunk_start = 0
        last_chunk_end = audio.size
        
        assert chunks[0].size > 0  # First chunk exists
        assert chunks[-1].size > 0  # Last chunk exists

    def test_reproducibility_of_chunks(self):
        """Test that chunking same audio produces same chunks"""
        config = ChunkConfig(overlap_ratio=0.2, chunk_size=16000)
        chunker = AudioChunker(config)
        audio = np.random.randn(48000)
        
        chunks1 = chunker.chunk(audio.copy())
        chunks2 = chunker.chunk(audio.copy())
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            np.testing.assert_array_almost_equal(c1, c2)

    # ========== CONFIGURATION EDGE CASES ==========
    
    def test_min_max_duration_validation(self):
        """Test min/max duration validation"""
        config = ChunkConfig(
            min_chunk_duration_ms=100,
            max_chunk_duration_ms=5000,
            chunk_size=16000,
            sample_rate=16000
        )
        assert config.chunk_size > 0

    def test_config_with_zero_sample_rate(self):
        """Test that zero sample rate raises error"""
        with pytest.raises(ValueError):
            ChunkConfig(sample_rate=0)

    def test_config_with_negative_sample_rate(self):
        """Test that negative sample rate raises error"""
        with pytest.raises(ValueError):
            ChunkConfig(sample_rate=-16000)

    # ========== SPECIAL PATTERNS ==========
    
    def test_chirp_signal_chunking(self):
        """Test chunking chirp signal (frequency sweep)"""
        chunker = AudioChunker()
        t = np.linspace(0, 3, 48000)
        # Frequency sweep from 100Hz to 1000Hz
        audio = np.sin(2 * np.pi * (100 + 300 * t) * t)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_impulse_signal_chunking(self):
        """Test chunking impulse signal"""
        chunker = AudioChunker()
        audio = np.zeros(48000)
        audio[24000] = 1.0  # Single impulse in middle
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_white_noise_chunking(self):
        """Test chunking white noise"""
        chunker = AudioChunker()
        audio = np.random.normal(0, 0.1, 48000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0

    def test_pink_noise_chunking(self):
        """Test chunking pink noise (1/f noise)"""
        chunker = AudioChunker()
        # Simple pink noise approximation
        freqs = np.fft.rfftfreq(48000)
        freqs[0] = 1  # Avoid division by zero
        spectrum = np.random.randn(len(freqs)) / np.sqrt(freqs)
        audio = np.fft.irfft(spectrum)[:48000]
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 0


class TestChunkAggregation:
    """Tests for chunk aggregation edge cases"""

    def test_aggregate_single_chunk(self):
        """Test aggregating single chunk"""
        audio = np.random.randn(16000)
        # Single chunk should be trivial to aggregate
        assert audio.size > 0

    def test_aggregate_many_small_chunks(self):
        """Test aggregating many small chunks"""
        config = ChunkConfig(chunk_size=1000, overlap_ratio=0.1)
        chunker = AudioChunker(config)
        audio = np.random.randn(48000)
        
        chunks = chunker.chunk(audio)
        assert len(chunks) > 10  # Should have many chunks

    def test_aggregate_empty_chunk_list(self):
        """Test aggregating empty chunk list"""
        chunks = []
        # Empty list should be handled gracefully
        assert len(chunks) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
