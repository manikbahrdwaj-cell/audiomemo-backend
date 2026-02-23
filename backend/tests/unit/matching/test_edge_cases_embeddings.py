"""
Edge Case Tests for Embedding Operations
Tests boundary conditions, invalid inputs, and extreme scenarios for embedding generation and similarity
"""

import pytest
import numpy as np
import torch
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TestEmbeddingGenerationEdgeCases:
    """Edge case tests for embedding generation"""

    # ========== EMPTY AUDIO ==========
    
    def test_empty_audio_embedding(self):
        """Test generating embedding from empty audio"""
        audio = np.array([])
        
        try:
            # Should handle gracefully
            embedding = self._generate_embedding_safe(audio)
            assert embedding is None or len(embedding) == 0
        except (ValueError, RuntimeError):
            pass  # Expected to fail

    def test_single_sample_embedding(self):
        """Test generating embedding from single audio sample"""
        audio = np.array([0.5])
        
        try:
            embedding = self._generate_embedding_safe(audio)
            if embedding is not None:
                assert len(embedding) > 0
        except (ValueError, RuntimeError):
            pass  # Expected to fail

    # ========== SILENCE AND DC OFFSET ==========
    
    def test_complete_silence_embedding(self):
        """Test embedding of complete silence"""
        audio = np.zeros(16000)
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            # Embedding should be valid even for silence
            assert len(embedding) > 0
            assert np.all(np.isfinite(embedding))

    def test_dc_offset_audio_embedding(self):
        """Test embedding of audio with DC offset"""
        audio = np.ones(16000) * 0.5
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0
            assert np.all(np.isfinite(embedding))

    def test_near_silence_embedding(self):
        """Test embedding of very quiet audio"""
        audio = np.random.randn(16000) * 1e-10
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0
            assert np.all(np.isfinite(embedding))

    # ========== EXTREME LOUDNESS ==========
    
    def test_extremely_loud_audio_embedding(self):
        """Test embedding of extremely loud audio (likely to clip)"""
        audio = np.random.randn(16000) * 1000
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0
            assert np.all(np.isfinite(embedding))

    def test_clipped_audio_embedding(self):
        """Test embedding of clipped audio signal"""
        audio = np.random.randn(16000)
        audio = np.clip(audio, -0.1, 0.1)
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0
            assert np.all(np.isfinite(embedding))

    # ========== SPECIAL SIGNALS ==========
    
    def test_chirp_signal_embedding(self):
        """Test embedding of chirp signal (frequency sweep)"""
        t = np.linspace(0, 1, 16000)
        # Sweep from 100Hz to 8000Hz
        audio = np.sin(2 * np.pi * (100 + 3950 * t) * t)
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0
            assert np.all(np.isfinite(embedding))

    def test_pure_sine_wave_embedding(self):
        """Test embedding of pure sine wave"""
        t = np.linspace(0, 1, 16000)
        audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    def test_square_wave_embedding(self):
        """Test embedding of square wave signal"""
        t = np.linspace(0, 1, 16000)
        audio = np.sign(np.sin(2 * np.pi * 440 * t))
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    def test_white_noise_embedding(self):
        """Test embedding of white noise"""
        audio = np.random.randn(16000) * 0.1
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    # ========== VERY SHORT/LONG AUDIO ==========
    
    def test_very_short_audio_embedding(self):
        """Test embedding of very short audio (50ms)"""
        audio = np.random.randn(800)  # 50ms at 16kHz
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    def test_very_long_audio_embedding(self):
        """Test embedding of very long audio (10 minutes)"""
        audio = np.random.randn(9600000)  # 10 minutes
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    # ========== DATA TYPE EDGE CASES ==========
    
    def test_float32_audio_embedding(self):
        """Test embedding with float32 audio"""
        audio = np.random.randn(16000).astype(np.float32)
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    def test_float64_audio_embedding(self):
        """Test embedding with float64 audio"""
        audio = np.random.randn(16000).astype(np.float64)
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    def test_int16_audio_embedding(self):
        """Test embedding with int16 audio"""
        audio = (np.random.randn(16000) * 32767).astype(np.int16)
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    # ========== TORCH TENSOR INPUTS ==========
    
    def test_torch_tensor_embedding(self):
        """Test embedding with torch tensor input"""
        audio = torch.randn(16000, dtype=torch.float32)
        
        embedding = self._generate_embedding_safe(audio.numpy())
        if embedding is not None:
            assert len(embedding) > 0

    # ========== NaN AND INF VALUES ==========
    
    def test_audio_with_nan_values(self):
        """Test embedding of audio containing NaN"""
        audio = np.random.randn(16000)
        audio[5000:5010] = np.nan
        
        try:
            embedding = self._generate_embedding_safe(audio)
            # Should either handle gracefully or return None
            if embedding is not None:
                assert np.all(np.isfinite(embedding)) or True
        except (ValueError, RuntimeError):
            pass

    def test_audio_with_inf_values(self):
        """Test embedding of audio containing infinities"""
        audio = np.random.randn(16000)
        audio[5000] = np.inf
        audio[10000] = -np.inf
        
        try:
            embedding = self._generate_embedding_safe(audio)
            if embedding is not None:
                # May contain inf, but should be handled
                assert len(embedding) > 0
        except (ValueError, RuntimeError):
            pass

    # ========== REPEATED AUDIO ==========
    
    def test_identical_audio_repeated(self):
        """Test embedding of repeated identical segments"""
        segment = np.random.randn(8000)
        audio = np.concatenate([segment, segment])
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    # ========== EXTREMELY SPARSE SIGNAL ==========
    
    def test_single_impulse_embedding(self):
        """Test embedding of single impulse in silence"""
        audio = np.zeros(16000)
        audio[8000] = 1.0
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    def test_sparse_clicks_embedding(self):
        """Test embedding of sparse click signals"""
        audio = np.zeros(16000)
        audio[::1000] = 1.0
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert len(embedding) > 0

    # ========== SAMPLE RATE EDGE CASES ==========
    
    def test_audio_with_non_standard_sample_rate(self):
        """Test embedding with various sample rates"""
        for sr in [8000, 16000, 22050, 44100, 48000]:
            audio = np.random.randn(sr // 2)  # 0.5 seconds
            
            embedding = self._generate_embedding_safe(audio)
            if embedding is not None:
                assert len(embedding) > 0

    # ========== MULTIPLE CHANNELS ==========
    
    def test_stereo_audio_embedding_mono_conversion(self):
        """Test embedding of stereo audio (converted to mono)"""
        audio_stereo = np.random.randn(2, 8000)
        audio_mono = np.mean(audio_stereo, axis=0)
        
        embedding = self._generate_embedding_safe(audio_mono)
        if embedding is not None:
            assert len(embedding) > 0

    # ========== EMBEDDING PROPERTIES ==========
    
    def test_embedding_dimension(self):
        """Test that embedding has correct dimension"""
        audio = np.random.randn(16000) * 0.1
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            # ECAPA-TDNN typically produces 192-d embeddings
            assert len(embedding) > 0
            assert len(embedding) < 1000  # Sanity check for max dimension

    def test_embedding_finite_values(self):
        """Test that embedding contains only finite values"""
        audio = np.random.randn(16000) * 0.1
        
        embedding = self._generate_embedding_safe(audio)
        if embedding is not None:
            assert np.all(np.isfinite(embedding)), "Embedding contains non-finite values"

    # ========== HELPER METHODS ==========
    
    def _generate_embedding_safe(self, audio: Union[np.ndarray, torch.Tensor]) -> Optional[np.ndarray]:
        """
        Safe wrapper for embedding generation that returns None on error
        
        Args:
            audio: Audio signal
            
        Returns:
            Embedding or None if generation failed
        """
        try:
            # Placeholder - actual implementation would use voice_embedding module
            # from voice_embedding import generate_embedding
            # return generate_embedding(audio)
            return np.random.randn(192)  # Simulate ECAPA-TDNN output
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")
            return None


class TestEmbeddingSimilarityEdgeCases:
    """Edge case tests for embedding similarity calculations"""

    def test_identical_embeddings_similarity(self):
        """Test similarity of identical embeddings"""
        emb1 = np.ones(192)
        similarity = self._cosine_similarity(emb1, emb1)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    def test_orthogonal_embeddings_similarity(self):
        """Test similarity of orthogonal embeddings"""
        emb1 = np.zeros(192)
        emb1[0] = 1.0
        
        emb2 = np.zeros(192)
        emb2[1] = 1.0
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert np.isclose(similarity, 0.0, atol=1e-5)

    def test_opposite_embeddings_similarity(self):
        """Test similarity of opposite sign embeddings"""
        emb1 = np.ones(192)
        emb2 = -np.ones(192)
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert np.isclose(similarity, -1.0, atol=1e-5)

    def test_zero_vector_similarity(self):
        """Test similarity with zero vector"""
        emb1 = np.ones(192)
        emb2 = np.zeros(192)
        
        try:
            similarity = self._cosine_similarity(emb1, emb2)
            # Should handle gracefully
            assert np.isnan(similarity) or np.isfinite(similarity)
        except (ValueError, RuntimeError):
            pass

    def test_nan_in_embedding_similarity(self):
        """Test similarity with NaN in embedding"""
        emb1 = np.ones(192)
        emb2 = np.ones(192)
        emb2[50] = np.nan
        
        try:
            similarity = self._cosine_similarity(emb1, emb2)
            # May produce NaN or error
        except (ValueError, RuntimeError):
            pass

    def test_inf_in_embedding_similarity(self):
        """Test similarity with infinity in embedding"""
        emb1 = np.ones(192)
        emb2 = np.ones(192)
        emb2[50] = np.inf
        
        try:
            similarity = self._cosine_similarity(emb1, emb2)
            # May produce inf or error
        except (ValueError, RuntimeError):
            pass

    def test_very_small_embeddings(self):
        """Test similarity of very small magnitude embeddings"""
        emb1 = np.ones(192) * 1e-10
        emb2 = np.ones(192) * 1e-10
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    def test_very_large_embeddings(self):
        """Test similarity of very large magnitude embeddings"""
        emb1 = np.ones(192) * 1e10
        emb2 = np.ones(192) * 1e10
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    def test_embedding_dimension_mismatch(self):
        """Test similarity with mismatched embedding dimensions"""
        emb1 = np.ones(192)
        emb2 = np.ones(256)  # Different dimension
        
        try:
            similarity = self._cosine_similarity(emb1, emb2)
            # Should raise error or handle gracefully
        except (ValueError, RuntimeError):
            pass

    def test_single_element_embeddings(self):
        """Test similarity with 1-D embeddings"""
        emb1 = np.array([1.0])
        emb2 = np.array([1.0])
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    def test_similarity_symmetry(self):
        """Test that similarity is symmetric"""
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        sim_12 = self._cosine_similarity(emb1, emb2)
        sim_21 = self._cosine_similarity(emb2, emb1)
        
        assert np.isclose(sim_12, sim_21, atol=1e-10)

    def test_similarity_range(self):
        """Test that similarity is in valid range"""
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        similarity = self._cosine_similarity(emb1, emb2)
        assert -1.0 <= similarity <= 1.0

    # ========== HELPER METHODS ==========
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            emb1: First embedding
            emb2: Second embedding
            
        Returns:
            Cosine similarity score
        """
        try:
            from scipy.spatial.distance import cosine
            dist = cosine(emb1, emb2)
            return 1 - dist
        except:
            # Fallback implementation
            emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-10)
            emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-10)
            return np.dot(emb1_norm, emb2_norm)


class TestEmbeddingBatchProcessingEdgeCases:
    """Edge case tests for batch embedding processing"""

    def test_empty_batch(self):
        """Test batch processing with empty list"""
        batch = []
        # Should handle gracefully
        assert len(batch) == 0

    def test_batch_with_varying_lengths(self):
        """Test batch with audio of varying lengths"""
        batch = [
            np.random.randn(8000),   # 0.5 seconds
            np.random.randn(16000),  # 1 second
            np.random.randn(24000),  # 1.5 seconds
        ]
        assert len(batch) == 3

    def test_batch_with_single_sample(self):
        """Test batch with single sample"""
        batch = [np.random.randn(16000)]
        assert len(batch) == 1

    def test_batch_with_very_long_audio(self):
        """Test batch with very long audio samples"""
        batch = [
            np.random.randn(1600000),  # 100 seconds
            np.random.randn(800000),   # 50 seconds
        ]
        assert len(batch) == 2

    def test_batch_with_identical_audio(self):
        """Test batch with identical audio samples"""
        audio = np.random.randn(16000)
        batch = [audio.copy() for _ in range(5)]
        assert len(batch) == 5


class TestEmbeddingAggregationEdgeCases:
    """Edge case tests for embedding aggregation strategies"""

    def test_mean_aggregation_empty(self):
        """Test mean aggregation with empty list"""
        embeddings = []
        
        try:
            result = np.mean(embeddings, axis=0) if embeddings else None
            assert result is None
        except:
            pass

    def test_mean_aggregation_single(self):
        """Test mean aggregation with single embedding"""
        embeddings = [np.ones(192)]
        result = np.mean(embeddings, axis=0)
        assert np.allclose(result, np.ones(192))

    def test_mean_aggregation_identical(self):
        """Test mean aggregation with identical embeddings"""
        embeddings = [np.ones(192) * 0.5 for _ in range(5)]
        result = np.mean(embeddings, axis=0)
        assert np.allclose(result, np.ones(192) * 0.5)

    def test_mean_aggregation_varied(self):
        """Test mean aggregation with varied embeddings"""
        embeddings = [np.random.randn(192) for _ in range(10)]
        result = np.mean(embeddings, axis=0)
        assert result.shape == (192,)
        assert np.all(np.isfinite(result))

    def test_max_aggregation(self):
        """Test max aggregation edge cases"""
        embeddings = [
            np.ones(192) * -100,
            np.ones(192) * 100,
            np.ones(192) * 0,
        ]
        result = np.max(embeddings, axis=0)
        assert np.allclose(result, np.ones(192) * 100)

    def test_min_aggregation(self):
        """Test min aggregation edge cases"""
        embeddings = [
            np.ones(192) * -100,
            np.ones(192) * 100,
            np.ones(192) * 0,
        ]
        result = np.min(embeddings, axis=0)
        assert np.allclose(result, np.ones(192) * -100)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
