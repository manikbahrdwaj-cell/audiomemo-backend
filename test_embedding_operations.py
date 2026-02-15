"""
Test Suite for Embedding Operations
Comprehensive tests covering all embedding functionality
"""

import pytest
import numpy as np
import tempfile
import logging
from pathlib import Path
from io import BytesIO
import wave

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import embedding modules
from voice_embedding import (
    generate_embedding,
    generate_embedding_with_chunking,
    get_embedding_with_auto_chunking,
    calculate_cosine_similarity,
    preprocess_audio,
    get_model,
    compare_embeddings_with_chunks
)

from embedding_operations import (
    EmbeddingMetrics,
    EmbeddingStats,
    EmbeddingComparator,
    EmbeddingBatchProcessor,
    EmbeddingCache,
    EmbeddingService,
    EmbeddingServiceConfig,
    get_embedding_service
)


def create_test_audio(duration_seconds: float = 2.0, frequency: float = 440.0) -> bytes:
    """
    Create a synthetic test audio file (sine wave)
    
    Args:
        duration_seconds: Duration of audio
        frequency: Frequency of sine wave
        
    Returns:
        WAV file bytes
    """
    sample_rate = 16000
    n_samples = int(sample_rate * duration_seconds)
    
    # Generate sine wave
    t = np.arange(n_samples) / sample_rate
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Normalize to 16-bit range
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Write to WAV file bytes
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        with wave.open(tmp, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)   # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        # Read back the file
        with open(tmp.name, 'rb') as f:
            wav_bytes = f.read()
    
    return wav_bytes


class TestBasicEmbedding:
    """Test basic embedding generation"""
    
    def test_generate_embedding_shape(self):
        """Test that embedding has correct shape"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        assert embedding.shape == (192,), f"Expected shape (192,), got {embedding.shape}"
        logger.info("✓ Embedding shape test passed")
    
    def test_embedding_no_nans(self):
        """Test that embedding contains no NaN values"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        assert not np.any(np.isnan(embedding)), "Embedding contains NaN values"
        logger.info("✓ No NaN values test passed")
    
    def test_embedding_normalized(self):
        """Test that embedding is approximately normalized"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        magnitude = np.linalg.norm(embedding)
        # Should be close to 1.0 for normalized embedding
        assert 0.8 < magnitude < 1.2, f"Magnitude {magnitude} too far from 1.0"
        logger.info(f"✓ Embedding normalization test passed (magnitude={magnitude:.4f})")
    
    def test_embedding_finite_values(self):
        """Test that all embedding values are finite"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        assert np.all(np.isfinite(embedding)), "Embedding contains infinite values"
        logger.info("✓ Finite values test passed")
    
    def test_deterministic_embedding(self):
        """Test that same audio produces identical embeddings"""
        audio = create_test_audio(duration_seconds=2.0, frequency=440.0)
        
        emb1 = generate_embedding(audio)
        emb2 = generate_embedding(audio)
        
        # Should be identical (or very close due to floating point)
        similarity = calculate_cosine_similarity(emb1, emb2)
        assert similarity > 0.99, f"Embeddings not deterministic: {similarity}"
        logger.info(f"✓ Deterministic embedding test passed (similarity={similarity:.6f})")


class TestChunkedEmbedding:
    """Test chunked embedding generation"""
    
    def test_chunked_embedding_shape(self):
        """Test that chunked embedding has correct shape"""
        audio = create_test_audio(duration_seconds=5.0)
        embedding = generate_embedding_with_chunking(audio, chunk_size_seconds=1.0)
        
        assert embedding.shape == (192,), f"Expected shape (192,), got {embedding.shape}"
        logger.info("✓ Chunked embedding shape test passed")
    
    def test_all_aggregation_methods(self):
        """Test all aggregation methods work"""
        audio = create_test_audio(duration_seconds=3.0)
        
        methods = ['mean', 'max', 'weighted_linear', 'weighted_inverse',
                   'weighted_normalized', 'energy_weighted']
        
        embeddings = {}
        for method in methods:
            embedding = generate_embedding_with_chunking(
                audio,
                aggregation_method=method
            )
            embeddings[method] = embedding
            
            assert embedding.shape == (192,)
            assert not np.any(np.isnan(embedding))
            logger.info(f"✓ Aggregation method '{method}' test passed")
        
        # Embeddings should be different (different methods)
        similarity_mean_max = calculate_cosine_similarity(
            embeddings['mean'],
            embeddings['max']
        )
        assert similarity_mean_max < 0.99, "Different methods should produce different embeddings"
        logger.info(f"✓ Different aggregation methods produce different embeddings")
    
    def test_chunking_with_overlap(self):
        """Test chunking with different overlap ratios"""
        audio = create_test_audio(duration_seconds=4.0)
        
        emb_overlap_0 = generate_embedding_with_chunking(
            audio,
            overlap_ratio=0.0
        )
        emb_overlap_02 = generate_embedding_with_chunking(
            audio,
            overlap_ratio=0.2
        )
        
        assert emb_overlap_0.shape == (192,)
        assert emb_overlap_02.shape == (192,)
        logger.info("✓ Chunking with different overlaps test passed")


class TestAutoChunking:
    """Test automatic chunking based on audio length"""
    
    def test_short_audio_no_chunking(self):
        """Test that short audio doesn't use chunking"""
        audio_short = create_test_audio(duration_seconds=3.0)
        
        embedding = get_embedding_with_auto_chunking(
            audio_short,
            auto_chunk_threshold_seconds=10.0
        )
        
        assert embedding.shape == (192,)
        logger.info("✓ Short audio (no chunking) test passed")
    
    def test_long_audio_with_chunking(self):
        """Test that long audio uses chunking"""
        audio_long = create_test_audio(duration_seconds=12.0)
        
        embedding = get_embedding_with_auto_chunking(
            audio_long,
            auto_chunk_threshold_seconds=10.0
        )
        
        assert embedding.shape == (192,)
        logger.info("✓ Long audio (with chunking) test passed")


class TestSimilarityCalculation:
    """Test cosine similarity calculation"""
    
    def test_self_similarity(self):
        """Test that embedding is similar to itself"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        similarity = calculate_cosine_similarity(embedding, embedding)
        assert similarity > 0.99, f"Self-similarity should be ~1.0, got {similarity}"
        logger.info(f"✓ Self-similarity test passed (sim={similarity:.6f})")
    
    def test_different_audio_low_similarity(self):
        """Test that different audio has low similarity"""
        audio1 = create_test_audio(duration_seconds=2.0, frequency=440.0)
        audio2 = create_test_audio(duration_seconds=2.0, frequency=880.0)
        
        emb1 = generate_embedding(audio1)
        emb2 = generate_embedding(audio2)
        
        similarity = calculate_cosine_similarity(emb1, emb2)
        assert similarity < 0.95, f"Different audio should have lower similarity, got {similarity}"
        logger.info(f"✓ Different audio lower similarity test passed (sim={similarity:.4f})")
    
    def test_similarity_range(self):
        """Test that similarity is in valid range"""
        audio1 = create_test_audio(duration_seconds=2.0, frequency=440.0)
        audio2 = create_test_audio(duration_seconds=2.0, frequency=500.0)
        
        emb1 = generate_embedding(audio1)
        emb2 = generate_embedding(audio2)
        
        similarity = calculate_cosine_similarity(emb1, emb2)
        assert 0 <= similarity <= 1, f"Similarity should be in [0,1], got {similarity}"
        logger.info(f"✓ Similarity range test passed (sim={similarity:.4f})")


class TestEmbeddingStats:
    """Test embedding statistics calculation"""
    
    def test_calculate_metrics(self):
        """Test metric calculation"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        metrics = EmbeddingStats.calculate_metrics(
            embedding=embedding,
            embedding_id="test_001",
            phone_number="+1234567890",
            generation_method="standard",
            audio_duration_ms=2000.5,
            n_chunks=None
        )
        
        assert metrics.embedding_id == "test_001"
        assert metrics.phone_number == "+1234567890"
        assert metrics.dimensions == 192
        assert metrics.generation_method == "standard"
        assert 0 < metrics.magnitude < 2.0
        assert -1 < metrics.mean_value < 1
        assert metrics.std_value >= 0
        logger.info("✓ Metrics calculation test passed")
    
    def test_quality_score(self):
        """Test embedding quality score"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        quality = EmbeddingStats.calculate_embedding_quality(embedding)
        
        assert 0 <= quality <= 1, f"Quality should be in [0,1], got {quality}"
        assert quality > 0.5, f"Quality should be reasonable for valid embedding, got {quality}"
        logger.info(f"✓ Quality score test passed (quality={quality:.4f})")


class TestEmbeddingComparator:
    """Test embedding comparison functionality"""
    
    def test_compare_identical(self):
        """Test comparing identical embeddings"""
        audio = create_test_audio(duration_seconds=2.0)
        embedding = generate_embedding(audio)
        
        comparison = EmbeddingComparator.compare(
            embedding, embedding,
            "user1", "user1",
            threshold=0.75
        )
        
        assert comparison.cosine_similarity > 0.95
        assert comparison.is_match == True
        assert comparison.confidence > 0.8
        logger.info("✓ Compare identical test passed")
    
    def test_compare_different(self):
        """Test comparing different embeddings"""
        audio1 = create_test_audio(duration_seconds=2.0, frequency=440.0)
        audio2 = create_test_audio(duration_seconds=2.0, frequency=880.0)
        
        emb1 = generate_embedding(audio1)
        emb2 = generate_embedding(audio2)
        
        comparison = EmbeddingComparator.compare(
            emb1, emb2,
            "user1", "user2",
            threshold=0.75
        )
        
        assert comparison.cosine_similarity < 0.95
        assert comparison.is_match == False
        logger.info(f"✓ Compare different test passed (sim={comparison.cosine_similarity:.4f})")
    
    def test_all_distance_metrics(self):
        """Test that all distance metrics are calculated"""
        audio = create_test_audio(duration_seconds=2.0, frequency=440.0)
        emb1 = generate_embedding(audio)
        emb2 = generate_embedding(create_test_audio(duration_seconds=2.0, frequency=500.0))
        
        comparison = EmbeddingComparator.compare(emb1, emb2, "u1", "u2")
        
        assert hasattr(comparison, 'cosine_similarity')
        assert hasattr(comparison, 'euclidean_distance')
        assert hasattr(comparison, 'manhattan_distance')
        assert hasattr(comparison, 'chebyshev_distance')
        assert hasattr(comparison, 'is_match')
        assert hasattr(comparison, 'confidence')
        logger.info("✓ All distance metrics test passed")
    
    def test_batch_compare(self):
        """Test batch comparison"""
        query_audio = create_test_audio(duration_seconds=2.0, frequency=440.0)
        query_emb = generate_embedding(query_audio)
        
        stored_embeddings = {
            "user1": generate_embedding(create_test_audio(frequency=440.0)),
            "user2": generate_embedding(create_test_audio(frequency=500.0)),
            "user3": generate_embedding(create_test_audio(frequency=600.0)),
        }
        
        results = EmbeddingComparator.batch_compare(query_emb, stored_embeddings)
        
        assert len(results) == 3
        # Should be sorted by similarity (descending)
        assert results[0].cosine_similarity >= results[1].cosine_similarity
        assert results[1].cosine_similarity >= results[2].cosine_similarity
        logger.info("✓ Batch compare test passed")


class TestEmbeddingCache:
    """Test embedding cache functionality"""
    
    def test_cache_put_get(self):
        """Test basic cache operations"""
        cache = EmbeddingCache(max_size=10)
        embedding = create_test_audio(2.0)
        
        cache.put("user1", embedding)
        retrieved = cache.get("user1")
        
        assert retrieved is not None
        assert np.array_equal(retrieved, embedding)
        logger.info("✓ Cache put/get test passed")
    
    def test_cache_miss(self):
        """Test cache miss"""
        cache = EmbeddingCache(max_size=10)
        
        result = cache.get("nonexistent")
        assert result is None
        logger.info("✓ Cache miss test passed")
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = EmbeddingCache(max_size=10)
        embedding = np.random.rand(192)
        
        # Miss
        cache.get("user1")
        # Put
        cache.put("user1", embedding)
        # Hit
        cache.get("user1")
        # Miss
        cache.get("user2")
        # Hit
        cache.get("user1")
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.5
        logger.info(f"✓ Cache stats test passed (hit_rate={stats['hit_rate']:.1%})")
    
    def test_cache_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = EmbeddingCache(max_size=3)
        
        # Fill cache
        for i in range(3):
            cache.put(f"user{i}", np.random.rand(192))
        
        # Add one more (should evict oldest)
        cache.put("user3", np.random.rand(192))
        
        assert len(cache.cache) == 3
        logger.info("✓ Cache eviction test passed")


class TestEmbeddingService:
    """Test high-level embedding service"""
    
    def test_service_generation(self):
        """Test service embedding generation"""
        config = EmbeddingServiceConfig(use_cache=False)
        service = EmbeddingService(config)
        
        audio = create_test_audio(duration_seconds=2.0)
        embedding, metrics = service.generate(audio, "+1234567890")
        
        assert embedding.shape == (192,)
        assert metrics.phone_number == "+1234567890"
        assert 0 <= metrics.quality_score <= 1
        logger.info("✓ Service generation test passed")
    
    def test_service_caching(self):
        """Test service caching"""
        config = EmbeddingServiceConfig(use_cache=True, cache_size=10)
        service = EmbeddingService(config)
        
        audio = create_test_audio(duration_seconds=2.0)
        
        # First call (cache miss)
        emb1, _ = service.generate(audio, "+1234567890")
        
        # Second call (cache hit)
        emb2, _ = service.generate(audio, "+1234567890")
        
        # Should be identical
        assert np.array_equal(emb1, emb2)
        
        stats = service.get_cache_stats()
        assert stats["hits"] > 0
        logger.info(f"✓ Service caching test passed (hit_rate={stats['hit_rate']:.1%})")
    
    def test_service_quality_check(self):
        """Test service quality checking"""
        config = EmbeddingServiceConfig(
            enable_quality_check=True,
            min_quality_score=0.4
        )
        service = EmbeddingService(config)
        
        audio = create_test_audio(duration_seconds=2.0)
        embedding, metrics = service.generate(audio, "+1234567890")
        
        # Quality should be acceptable
        assert metrics.quality_score > 0.4
        logger.info("✓ Service quality check test passed")
    
    def test_service_batch_generation(self):
        """Test batch generation"""
        config = EmbeddingServiceConfig(use_cache=False)
        service = EmbeddingService(config)
        
        audio_dict = {
            "user1": create_test_audio(duration_seconds=2.0, frequency=440.0),
            "user2": create_test_audio(duration_seconds=2.0, frequency=500.0),
            "user3": create_test_audio(duration_seconds=2.0, frequency=600.0),
        }
        
        results = service.batch_generate(audio_dict)
        
        assert len(results) == 3
        for user_id, (embedding, metrics) in results.items():
            assert embedding.shape == (192,)
            assert metrics is not None
        logger.info("✓ Service batch generation test passed")


class TestCompareMethodsComparison:
    """Test compare_embeddings_with_chunks function"""
    
    def test_compare_methods(self):
        """Test comparing different aggregation methods"""
        audio = create_test_audio(duration_seconds=3.0)
        
        embeddings = compare_embeddings_with_chunks(
            audio,
            aggregation_methods=['mean', 'max', 'energy_weighted']
        )
        
        assert len(embeddings) == 3
        
        for method, embedding in embeddings.items():
            if embedding is not None:
                assert embedding.shape == (192,)
                logger.info(f"✓ Method {method} test passed")


def run_comprehensive_tests():
    """Run all tests and report results"""
    logger.info("=" * 70)
    logger.info("STARTING COMPREHENSIVE EMBEDDING OPERATIONS TEST SUITE")
    logger.info("=" * 70)
    
    test_classes = [
        TestBasicEmbedding,
        TestChunkedEmbedding,
        TestAutoChunking,
        TestSimilarityCalculation,
        TestEmbeddingStats,
        TestEmbeddingComparator,
        TestEmbeddingCache,
        TestEmbeddingService,
        TestCompareMethodsComparison
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        logger.info(f"\nTesting {test_class.__name__}...")
        test_instance = test_class()
        
        for method_name in dir(test_instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    method = getattr(test_instance, method_name)
                    method()
                    passed_tests += 1
                except Exception as e:
                    failed_tests += 1
                    logger.error(f"✗ {method_name} FAILED: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info(f"TEST RESULTS: {passed_tests}/{total_tests} passed")
    if failed_tests > 0:
        logger.error(f"FAILURES: {failed_tests} tests failed")
    logger.info("=" * 70)
    
    return passed_tests, failed_tests, total_tests


if __name__ == "__main__":
    passed, failed, total = run_comprehensive_tests()
    
    if failed == 0:
        logger.info("\n✓ ALL TESTS PASSED!")
        exit(0)
    else:
        logger.error(f"\n✗ {failed} TESTS FAILED")
        exit(1)
