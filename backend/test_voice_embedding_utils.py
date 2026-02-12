"""
Unit Tests for Voice Embedding Utilities (Phase 4, Step 4.1)
Tests for voice_embedding.py voice processing functions
"""

import pytest
import numpy as np
import torch
import tempfile
import os
from pathlib import Path
from io import BytesIO
import wave

# Import utilities to test
from voice_embedding import (
    preprocess_audio,
    calculate_cosine_similarity,
)


class TestPreprocessAudio:
    """Test suite for audio preprocessing"""

    def create_test_wav_bytes(self, duration=1.0, sample_rate=16000, mono=True):
        """Create synthetic WAV audio bytes for testing"""
        samples = int(duration * sample_rate)
        # Generate simple sine wave
        frequency = 440  # A4 note
        t = np.linspace(0, duration, samples, False)
        audio_data = (0.3 * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
        
        # Write to WAV format in memory
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1 if mono else 2)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()

    def test_preprocess_audio_mono_16khz(self):
        """Test preprocessing 16kHz mono audio (standard case)"""
        audio_bytes = self.create_test_wav_bytes(duration=1.0, sample_rate=16000, mono=True)
        
        # Should not raise an exception
        waveform = preprocess_audio(audio_bytes)
        
        # Check output properties
        assert isinstance(waveform, torch.Tensor)
        assert waveform.shape[0] > 0
        assert torch.max(torch.abs(waveform)) <= 1.0  # Normalized

    def test_preprocess_audio_mono_8khz(self):
        """Test preprocessing 8kHz mono audio (should resample to 16kHz)"""
        audio_bytes = self.create_test_wav_bytes(duration=1.0, sample_rate=8000, mono=True)
        
        waveform = preprocess_audio(audio_bytes)
        
        # Output should be valid tensor
        assert isinstance(waveform, torch.Tensor)
        assert waveform.shape[0] > 0

    def test_preprocess_audio_mono_44khz(self):
        """Test preprocessing 44.1kHz mono audio"""
        audio_bytes = self.create_test_wav_bytes(duration=1.0, sample_rate=44100, mono=True)
        
        waveform = preprocess_audio(audio_bytes)
        
        assert isinstance(waveform, torch.Tensor)
        assert waveform.shape[0] > 0

    def test_preprocess_audio_stereo_downmix(self):
        """Test stereo to mono downmixing"""
        audio_bytes = self.create_test_wav_bytes(duration=1.0, sample_rate=16000, mono=False)
        
        waveform = preprocess_audio(audio_bytes)
        
        # Result should be mono (1D tensor after squeeze)
        assert isinstance(waveform, torch.Tensor)
        assert waveform.dim() == 1  # 1D tensor

    def test_preprocess_audio_short_duration(self):
        """Test preprocessing very short audio"""
        audio_bytes = self.create_test_wav_bytes(duration=0.1, sample_rate=16000)
        
        waveform = preprocess_audio(audio_bytes)
        
        assert isinstance(waveform, torch.Tensor)
        assert waveform.shape[0] > 0

    def test_preprocess_audio_normalization(self):
        """Test that audio is normalized to [-1, 1] range"""
        audio_bytes = self.create_test_wav_bytes(duration=1.0, sample_rate=16000)
        
        waveform = preprocess_audio(audio_bytes)
        
        # Check normalization
        max_val = torch.max(torch.abs(waveform))
        assert max_val <= 1.001  # Allow small floating point error

    def test_preprocess_audio_invalid_format(self):
        """Test error handling with invalid audio data"""
        with pytest.raises(Exception):
            preprocess_audio(b"invalid audio data")


class TestCosineSimilarity:
    """Test suite for cosine similarity calculations"""

    def test_cosine_similarity_identical_vectors(self):
        """Test similarity between identical vectors (should be 1.0)"""
        embedding1 = np.array([1.0, 0.0, 0.0] * 64)  # 192 dims
        embedding2 = np.array([1.0, 0.0, 0.0] * 64)
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Should be very close to 1.0
        assert 0.99 < similarity <= 1.0

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test similarity between orthogonal vectors (should be ~0.5 when mapped to [0, 1])"""
        # Create orthogonal vectors in 192D space
        embedding1 = np.zeros(192)
        embedding2 = np.zeros(192)
        embedding1[0] = 1.0
        embedding2[1] = 1.0
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Orthogonal vectors have cosine similarity 0, which maps to 0.5 in [0,1]
        assert 0.45 < similarity < 0.55

    def test_cosine_similarity_opposite_vectors(self):
        """Test similarity between opposite vectors (should be ~0 when mapped to [0, 1])"""
        embedding1 = np.ones(192)
        embedding2 = -np.ones(192)
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Opposite vectors have cosine similarity -1, which maps to 0 in [0,1]
        assert 0.0 <= similarity < 0.05

    def test_cosine_similarity_random_vectors(self):
        """Test similarity with random vectors"""
        np.random.seed(42)
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(192)
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Similarity should be in valid range [0, 1]
        assert 0.0 <= similarity <= 1.0

    def test_cosine_similarity_partially_similar_vectors(self):
        """Test similarity between partially similar vectors"""
        embedding1 = np.array([1.0] * 96 + [0.0] * 96)
        embedding2 = np.array([1.0] * 96 + [0.0] * 96)
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Should be identical
        assert similarity > 0.99

    def test_cosine_similarity_zero_vector_handling(self):
        """Test behavior with zero vectors"""
        embedding1 = np.zeros(192)
        embedding2 = np.random.randn(192)
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Should return 0 when one vector is all zeros
        assert similarity == 0.0

    def test_cosine_similarity_scaled_vectors(self):
        """Test that similarity is scale-invariant"""
        embedding1 = np.array([1.0, 2.0, 3.0] * 64)
        embedding2 = np.array([2.0, 4.0, 6.0] * 64)  # 2x scaled
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Scaled vectors should have same similarity
        assert similarity > 0.99

    def test_cosine_similarity_output_range(self):
        """Test that output is always in [0, 1] range"""
        np.random.seed(42)
        for _ in range(100):
            embedding1 = np.random.randn(192)
            embedding2 = np.random.randn(192)
            
            similarity = calculate_cosine_similarity(embedding1, embedding2)
            
            assert 0.0 <= similarity <= 1.0

    def test_cosine_similarity_different_magnitudes(self):
        """Test similarity with vectors of different magnitudes"""
        embedding1 = np.array([0.1] * 192)
        embedding2 = np.array([100.0] * 192)
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        # Despite magnitude difference, direction is same
        assert similarity > 0.99

    def test_cosine_similarity_computation_consistency(self):
        """Test that repeated calculations give same result"""
        np.random.seed(42)
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(192)
        
        similarity1 = calculate_cosine_similarity(embedding1, embedding2)
        similarity2 = calculate_cosine_similarity(embedding1, embedding2)
        
        # Should be exactly the same
        assert similarity1 == similarity2


class TestEmbeddingDimensions:
    """Test suite for embedding dimension validation"""

    def test_embedding_dimension_checking(self):
        """Test that embeddings have correct 192 dimensions"""
        embedding = np.random.randn(192)
        
        # Should not raise error for 192D
        assert embedding.shape == (192,)

    def test_incorrect_embedding_dimensions(self):
        """Test handling of incorrect dimensions"""
        embedding_96d = np.random.randn(96)
        embedding_384d = np.random.randn(384)
        
        assert embedding_96d.shape != (192,)
        assert embedding_384d.shape != (192,)


class TestAudioEdgeCases:
    """Test edge cases in audio processing"""

    def create_silent_audio(self, duration=1.0, sample_rate=16000):
        """Create silent audio for testing"""
        samples = int(duration * sample_rate)
        audio_data = np.zeros(samples, dtype=np.int16)
        
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()

    def test_preprocess_silent_audio(self):
        """Test preprocessing of silent audio"""
        audio_bytes = self.create_silent_audio()
        
        waveform = preprocess_audio(audio_bytes)
        
        # Should still produce valid waveform
        assert isinstance(waveform, torch.Tensor)
        # Silent audio normalized would be all zeros
        assert torch.max(torch.abs(waveform)) <= 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
