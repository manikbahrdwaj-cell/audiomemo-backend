"""
Test Suite for Chunk Embedding Verifier
Comprehensive tests for chunk-based voice verification
"""

import numpy as np
import logging
from pathlib import Path
from typing import List, Tuple

from chunk_embedding_verifier import (
    ChunkEmbeddingVerifier,
    ChunkEmbedding,
    ChunkMatchStatus,
    ChunkComparisonResult,
    ChunkVerificationResult
)
from audio_chunking import AudioChunker, ChunkConfig
from verification_service import (
    VerificationManager,
    VerificationSessionConfig,
    VerificationResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_audio(duration_seconds: float = 3.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate synthetic test audio"""
    t = np.linspace(0, duration_seconds, int(duration_seconds * sample_rate))
    # Combine multiple frequencies to simulate speech-like patterns
    audio = (
        0.3 * np.sin(2 * np.pi * 200 * t) +  # Fundamental frequency
        0.1 * np.sin(2 * np.pi * 400 * t) +  # 1st harmonic
        0.05 * np.sin(2 * np.pi * 600 * t)   # 2nd harmonic
    )
    # Add noise
    noise = 0.02 * np.random.randn(len(audio))
    audio = audio + noise
    # Normalize
    audio = audio / np.max(np.abs(audio))
    return audio.astype(np.float32)


def generate_similar_audio(reference_audio: np.ndarray, noise_level: float = 0.1) -> np.ndarray:
    """Generate audio similar to reference with added noise"""
    noise = noise_level * np.random.randn(len(reference_audio))
    similar_audio = reference_audio + noise
    similar_audio = similar_audio / np.max(np.abs(similar_audio))
    return similar_audio.astype(np.float32)


def test_chunk_embeddings_generation():
    """Test generation of chunk embeddings"""
    logger.info("=" * 60)
    logger.info("TEST: Chunk Embeddings Generation")
    logger.info("=" * 60)
    
    try:
        # Create verifier
        chunk_config = ChunkConfig(
            chunk_size=16000,  # 1 second
            overlap_ratio=0.2
        )
        verifier = ChunkEmbeddingVerifier(chunk_config=chunk_config)
        
        # Generate test audio
        audio = generate_test_audio(duration_seconds=5.0)
        logger.info(f"Generated test audio: {len(audio)} samples (5 seconds)")
        
        # Generate chunk embeddings
        chunk_embeddings = verifier.generate_chunk_embeddings(audio, sample_rate=16000)
        
        logger.info(f"✓ Generated {len(chunk_embeddings)} chunk embeddings")
        for i, chunk in enumerate(chunk_embeddings):
            logger.info(
                f"  Chunk {i}: duration={chunk.duration_ms:.0f}ms, "
                f"time={chunk.start_time_ms:.0f}-{chunk.end_time_ms:.0f}ms, "
                f"emb_dim={len(chunk.embedding)}, confidence={chunk.confidence:.2f}"
            )
        
        return True, chunk_embeddings
    
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False, None


def test_chunk_comparison(chunk_embeddings: List[ChunkEmbedding]):
    """Test chunk embedding comparison"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Chunk Embedding Comparison")
    logger.info("=" * 60)
    
    try:
        if not chunk_embeddings or len(chunk_embeddings) < 2:
            logger.warning("Not enough chunks for comparison test")
            return False, []
        
        verifier = ChunkEmbeddingVerifier(
            similarity_threshold=0.75,
            confidence_threshold=0.70
        )
        
        # Compare first two chunks
        result = verifier.compare_chunk_embeddings(
            chunk_embeddings[0],
            chunk_embeddings[1]
        )
        
        logger.info(f"✓ Compared chunk embeddings")
        logger.info(f"  Cosine Similarity: {result.cosine_similarity:.4f}")
        logger.info(f"  Euclidean Distance: {result.euclidean_distance:.4f}")
        logger.info(f"  Correlation Distance: {result.correlation_distance:.4f}")
        logger.info(f"  Status: {result.status.value}")
        logger.info(f"  Match: {result.is_match}")
        logger.info(f"  Confidence: {result.confidence:.4f}")
        
        return True, result
    
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False, None


def test_chunk_matching_strategies(reference_chunks: List[ChunkEmbedding]):
    """Test different chunk matching strategies"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Chunk Matching Strategies")
    logger.info("=" * 60)
    
    try:
        if not reference_chunks or len(reference_chunks) < 2:
            logger.warning("Not enough chunks for matching test")
            return False, {}
        
        # Generate verification chunks (similar but with noise)
        audio = generate_test_audio(duration_seconds=5.0)
        similar_audio = generate_similar_audio(audio, noise_level=0.05)
        
        verifier = ChunkEmbeddingVerifier(similarity_threshold=0.75)
        verification_chunks = verifier.generate_chunk_embeddings(similar_audio, sample_rate=16000)
        
        strategies = ['best_match', 'strict_order', 'all_pairs']
        results = {}
        
        for strategy in strategies:
            try:
                matched = verifier.match_chunks(
                    reference_chunks[:3],  # Use first 3 chunks
                    verification_chunks[:3],
                    matching_strategy=strategy
                )
                results[strategy] = matched
                
                logger.info(f"✓ Strategy '{strategy}': {len(matched)} comparisons")
                
                matched_count = sum(1 for c in matched if c.status == ChunkMatchStatus.MATCH)
                avg_similarity = np.mean([c.cosine_similarity for c in matched])
                logger.info(f"  Matched: {matched_count}/{len(matched)}, Avg Similarity: {avg_similarity:.4f}")
            
            except Exception as e:
                logger.warning(f"  Strategy '{strategy}' failed: {e}")
        
        return True, results
    
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False, {}


def test_chunk_verification(reference_chunks: List[ChunkEmbedding]):
    """Test complete chunk-based verification"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Complete Chunk-Based Verification")
    logger.info("=" * 60)
    
    try:
        if not reference_chunks:
            logger.warning("No reference chunks available")
            return False, None
        
        # Generate similar audio for verification
        audio = generate_test_audio(duration_seconds=5.0)
        similar_audio = generate_similar_audio(audio, noise_level=0.05)
        
        verifier = ChunkEmbeddingVerifier(
            similarity_threshold=0.75,
            confidence_threshold=0.70
        )
        
        verification_chunks = verifier.generate_chunk_embeddings(similar_audio, sample_rate=16000)
        
        # Perform verification
        result = verifier.verify_with_chunks(
            reference_chunks,
            verification_chunks,
            matching_strategy='best_match',
            use_dynamic_threshold=False
        )
        
        logger.info(f"✓ Chunk-based verification complete")
        logger.info(f"  Verification ID: {result.verification_id}")
        logger.info(f"  Reference Chunks: {result.total_reference_chunks}")
        logger.info(f"  Verification Chunks: {result.total_verification_chunks}")
        logger.info(f"  Matched Chunks: {result.matched_chunks}")
        logger.info(f"  Partial Matched: {result.partial_matched_chunks}")
        logger.info(f"  Unmatched: {result.unmatched_chunks}")
        logger.info(f"  Average Similarity: {result.average_chunk_similarity:.4f}")
        logger.info(f"  Overall Confidence: {result.overall_confidence:.4f}")
        logger.info(f"  Verification Status: {result.verification_status.value}")
        logger.info(f"  Statistics:")
        for key, value in result.statistics.items():
            if isinstance(value, float):
                logger.info(f"    {key}: {value:.4f}")
            else:
                logger.info(f"    {key}: {value}")
        
        return True, result
    
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False, None


def test_chunk_variance_analysis(chunk_embeddings: List[ChunkEmbedding]):
    """Test chunk variance analysis"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Chunk Variance Analysis")
    logger.info("=" * 60)
    
    try:
        if not chunk_embeddings or len(chunk_embeddings) < 2:
            logger.warning("Not enough chunks for variance analysis")
            return False, None
        
        verifier = ChunkEmbeddingVerifier()
        analysis = verifier.analyze_chunk_variance(chunk_embeddings)
        
        logger.info(f"✓ Chunk variance analysis complete")
        logger.info(f"  Number of Chunks: {analysis.get('num_chunks', 'N/A')}")
        logger.info(f"  Comparisons: {analysis.get('num_comparisons', 'N/A')}")
        logger.info(f"  Mean Chunk Similarity: {analysis.get('mean_chunk_similarity', 'N/A'):.4f}")
        logger.info(f"  Std Dev: {analysis.get('std_chunk_similarity', 'N/A'):.4f}")
        logger.info(f"  Homogeneity: {analysis.get('homogeneity', 'N/A'):.4f}")
        logger.info(f"  Variance: {analysis.get('variance', 'N/A'):.6f}")
        
        return True, analysis
    
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False, None


def test_verification_service_with_chunks():
    """Test integration with VerificationService"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Verification Service with Chunk Support")
    logger.info("=" * 60)
    
    try:
        # Create config with chunk verification enabled
        config = VerificationSessionConfig(
            max_attempts=3,
            similarity_threshold=0.85,
            use_chunk_verification=True,
            chunk_similarity_threshold=0.75,
            chunk_confidence_threshold=0.70,
            chunk_matching_strategy='best_match'
        )
        
        logger.info(f"✓ Created VerificationSessionConfig")
        logger.info(f"  Chunk Verification: {config.use_chunk_verification}")
        logger.info(f"  Chunk Similarity Threshold: {config.chunk_similarity_threshold}")
        logger.info(f"  Chunk Confidence Threshold: {config.chunk_confidence_threshold}")
        logger.info(f"  Matching Strategy: {config.chunk_matching_strategy}")
        
        # Create manager
        manager = VerificationManager(config)
        logger.info(f"✓ Created VerificationManager with chunk support")
        logger.info(f"  Chunk Verifier Initialized: {manager.chunk_verifier is not None}")
        logger.info(f"  Default Threshold: {manager.chunk_verifier.similarity_threshold:.4f}")
        
        return True, (config, manager)
    
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False, None


def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "=" * 80)
    logger.info("CHUNK EMBEDDING VERIFIER - COMPREHENSIVE TEST SUITE")
    logger.info("=" * 80 + "\n")
    
    test_results = {}
    chunk_embeddings = None
    
    # Test 1: Generate chunks
    success, chunk_embeddings = test_chunk_embeddings_generation()
    test_results['chunk_generation'] = success
    
    if chunk_embeddings:
        # Test 2: Compare chunks
        success, _ = test_chunk_comparison(chunk_embeddings)
        test_results['chunk_comparison'] = success
        
        # Test 3: Matching strategies
        success, _ = test_chunk_matching_strategies(chunk_embeddings)
        test_results['matching_strategies'] = success
        
        # Test 4: Full verification
        success, _ = test_chunk_verification(chunk_embeddings)
        test_results['full_verification'] = success
        
        # Test 5: Variance analysis
        success, _ = test_chunk_variance_analysis(chunk_embeddings)
        test_results['variance_analysis'] = success
    
    # Test 6: Verification service integration
    success, _ = test_verification_service_with_chunks()
    test_results['verification_service'] = success
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for v in test_results.values() if v)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ ALL TESTS PASSED!")
    else:
        logger.info(f"\n✗ {total - passed} test(s) failed")
    
    return test_results


if __name__ == "__main__":
    test_results = run_all_tests()
    
    # Exit with appropriate code
    import sys
    sys.exit(0 if all(test_results.values()) else 1)
