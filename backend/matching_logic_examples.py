"""
Matching Logic Examples
Comprehensive examples demonstrating advanced matching strategies for voice verification
"""

import numpy as np
from matching_logic import (
    MatchingComparator,
    MatchingStrategy,
    get_matching_comparator
)
from verification_service import (
    get_verification_manager,
    VerificationSessionConfig,
    reset_verification_manager
)


def example_1_basic_cosine_matching():
    """Example 1: Basic cosine similarity matching"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Cosine Similarity Matching")
    print("="*70)
    
    # Create two embeddings (192-dimensional voice embeddings)
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.1  # Similar embedding
    
    # Initialize comparator
    comparator = MatchingComparator(
        primary_strategy=MatchingStrategy.COSINE,
        similarity_threshold=0.85
    )
    
    # Compare embeddings
    score = comparator.compare_embeddings(reference, test)
    
    print(f"✓ Primary Score: {score.primary_score:.4f}")
    print(f"✓ Final Score: {score.final_score:.4f}")
    print(f"✓ Matching Result: {score.matching_result.value}")
    print(f"✓ Confidence: {score.confidence:.4f}")
    print(f"✓ Strategy Used: {score.strategy_used.value}")


def example_2_hybrid_matching():
    """Example 2: Hybrid matching combining multiple strategies"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Hybrid Matching Strategy")
    print("="*70)
    
    # Create two embeddings
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.15
    
    # Initialize comparator with hybrid strategy
    comparator = MatchingComparator(
        primary_strategy=MatchingStrategy.HYBRID,
        similarity_threshold=0.85
    )
    
    # Compare embeddings
    score = comparator.compare_embeddings(reference, test)
    
    print(f"✓ Final Score (Hybrid): {score.final_score:.4f}")
    print(f"✓ Matching Result: {score.matching_result.value}")
    print(f"\nComponent Scores:")
    print(f"  - Cosine: {score.metadata['cosine_component']:.4f}")
    print(f"  - Euclidean: {score.metadata['euclidean_component']:.4f}")
    print(f"  - Correlation: {score.metadata['correlation_component']:.4f}")
    print(f"  - Chebyshev: {score.metadata['chebyshev_component']:.4f}")
    print(f"  - Statistical: {score.metadata['statistical_component']:.4f}")


def example_3_multiple_strategies():
    """Example 3: Compare embeddings using multiple strategies"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Comparing Multiple Matching Strategies")
    print("="*70)
    
    # Create two embeddings
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.15
    
    # Initialize comparator
    comparator = MatchingComparator(similarity_threshold=0.85)
    
    # Test all strategies
    strategies = [
        MatchingStrategy.COSINE,
        MatchingStrategy.EUCLIDEAN,
        MatchingStrategy.CORRELATION,
        MatchingStrategy.CHEBYSHEV,
        MatchingStrategy.HYBRID,
        MatchingStrategy.STATISTICAL,
        MatchingStrategy.ADAPTIVE
    ]
    
    results = {}
    for strategy in strategies:
        score = comparator.compare_embeddings(reference, test, strategy=strategy)
        results[strategy.value] = {
            "score": score.final_score,
            "result": score.matching_result.value,
            "confidence": score.confidence
        }
    
    print("Strategy Comparison Results:")
    print(f"{'Strategy':<15} {'Score':<10} {'Result':<15} {'Confidence':<12}")
    print("-" * 52)
    
    for strategy_name, result in results.items():
        print(f"{strategy_name:<15} {result['score']:<10.4f} {result['result']:<15} {result['confidence']:<12.4f}")


def example_4_adaptive_threshold():
    """Example 4: Adaptive matching with dynamic thresholds"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Adaptive Matching with Dynamic Thresholds")
    print("="*70)
    
    # Create embeddings with different variance patterns
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.2
    
    # Initialize with adaptive strategy
    comparator = MatchingComparator(
        primary_strategy=MatchingStrategy.ADAPTIVE,
        similarity_threshold=0.85
    )
    
    # Compare
    score = comparator.compare_embeddings(reference, test)
    
    print(f"✓ Final Score: {score.final_score:.4f}")
    print(f"✓ Matching Result: {score.matching_result.value}")
    print(f"✓ Confidence: {score.confidence:.4f}")
    print(f"\nAdaptive Details:")
    print(f"  - Adaptive Threshold: {score.metadata['adaptive_threshold']:.4f}")
    print(f"  - Reference Variance: {score.metadata['reference_variance']:.6f}")
    print(f"  - Test Variance: {score.metadata['test_variance']:.6f}")
    print(f"  - Average Variance: {score.metadata['avg_variance']:.6f}")


def example_5_detailed_metrics():
    """Example 5: Get comprehensive matching metrics"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Comprehensive Matching Metrics")
    print("="*70)
    
    # Create embeddings
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.1
    
    # Compare
    comparator = MatchingComparator()
    score = comparator.compare_embeddings(reference, test)
    
    # Display all metrics
    metrics = score.metrics
    print("Distance/Similarity Metrics:")
    print(f"  - Cosine Similarity: {metrics.cosine_similarity:.6f}")
    print(f"  - Euclidean Distance: {metrics.euclidean_distance:.6f}")
    print(f"  - Correlation Distance: {metrics.correlation_distance:.6f}")
    print(f"  - Chebyshev Distance: {metrics.chebyshev_distance:.6f}")
    print(f"  - Wasserstein Distance: {metrics.wasserstein_distance:.6f}")
    
    print(f"\nVector Properties:")
    print(f"  - Vector Angle: {metrics.vector_angle_degrees:.2f}°")
    print(f"  - Magnitude Ratio: {metrics.vector_magnitude_ratio:.6f}")
    print(f"  - Norm Difference: {metrics.embedding_norm_difference:.6f}")
    
    print(f"\nStatistical Properties:")
    print(f"  - KS Test P-value: {metrics.statistical_p_value:.6f}")
    print(f"  - Entropy Distance: {metrics.entropy_distance:.6f}")


def example_6_verification_with_advanced_matching():
    """Example 6: Voice verification with advanced matching strategies"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Voice Verification with Advanced Matching")
    print("="*70)
    
    # Initialize verification manager with advanced matching
    reset_verification_manager()
    
    config = VerificationSessionConfig(
        similarity_threshold=0.85,
        matching_strategy='hybrid',  # Use hybrid matching
        use_advanced_matching=True,
        compute_confidence=True
    )
    
    manager = get_verification_manager(config)
    
    print("✓ Verification Manager Initialized")
    print(f"  - Matching Strategy: {config.matching_strategy}")
    print(f"  - Similarity Threshold: {config.similarity_threshold}")
    print(f"  - Advanced Matching Enabled: {config.use_advanced_matching}")
    print(f"  - Confidence Computation: {config.compute_confidence}")


def example_7_multi_embedding_comparison():
    """Example 7: Compare multiple embeddings (chunk-based)"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Multi-Embedding Comparison")
    print("="*70)
    
    # Create reference and test embedding lists (e.g., from audio chunks)
    reference_embeddings = [
        np.random.randn(192).astype(np.float32) for _ in range(3)
    ]
    test_embeddings = [
        reference_embeddings[i] + np.random.randn(192).astype(np.float32) * 0.1
        for i in range(3)
    ]
    
    # Compare multiple embeddings
    comparator = MatchingComparator()
    
    # Best match strategy
    result = comparator.compare_embedding_lists(
        reference_embeddings,
        test_embeddings,
        matching_strategy='best_match'
    )
    
    print(f"✓ Best Match Strategy:")
    print(f"  - Overall Score: {result['overall_score']:.4f}")
    print(f"  - Mean Score: {result['mean_score']:.4f}")
    print(f"  - Max Score: {result['max_score']:.4f}")
    print(f"  - Min Score: {result['min_score']:.4f}")
    print(f"  - Std Dev: {result['std_dev']:.4f}")
    
    # All match strategy
    result_all = comparator.compare_embedding_lists(
        reference_embeddings,
        test_embeddings,
        matching_strategy='all_match'
    )
    
    print(f"\n✓ All Match Strategy:")
    print(f"  - Overall Score: {result_all['overall_score']:.4f}")
    
    # Weighted strategy
    result_weighted = comparator.compare_embedding_lists(
        reference_embeddings,
        test_embeddings,
        matching_strategy='weighted'
    )
    
    print(f"\n✓ Weighted Strategy:")
    print(f"  - Overall Score: {result_weighted['overall_score']:.4f}")


def example_8_custom_strategy_weights():
    """Example 8: Customize hybrid strategy weights"""
    print("\n" + "="*70)
    print("EXAMPLE 8: Custom Strategy Weights for Hybrid Matching")
    print("="*70)
    
    from matching_logic import MatchingStrategy
    
    # Create embeddings
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.1
    
    # Initialize comparator
    comparator = MatchingComparator(primary_strategy=MatchingStrategy.HYBRID)
    
    # Update weights - emphasize cosine similarity
    custom_weights = {
        MatchingStrategy.COSINE: 0.60,      # Increased from 0.40
        MatchingStrategy.EUCLIDEAN: 0.15,   # Decreased from 0.20
        MatchingStrategy.CORRELATION: 0.15,  # Decreased from 0.20
        MatchingStrategy.CHEBYSHEV: 0.05,    # Decreased from 0.10
        MatchingStrategy.STATISTICAL: 0.05   # Same
    }
    
    comparator.set_strategy_weights(custom_weights)
    print("✓ Custom weights set:")
    for strategy, weight in custom_weights.items():
        print(f"  - {strategy.value}: {weight:.2f}")
    
    # Compare with custom weights
    score = comparator.compare_embeddings(reference, test)
    
    print(f"\n✓ Matching Result with Custom Weights:")
    print(f"  - Final Score: {score.final_score:.4f}")
    print(f"  - Matching Result: {score.matching_result.value}")
    print(f"  - Confidence: {score.confidence:.4f}")


def example_9_error_handling():
    """Example 9: Error handling for invalid inputs"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Error Handling")
    print("="*70)
    
    comparator = MatchingComparator()
    
    # Test 1: Invalid embedding (wrong dimension)
    print("\nTest 1: Invalid embedding dimension")
    invalid_emb1 = np.random.randn(100)
    invalid_emb2 = np.random.randn(192)
    
    score = comparator.compare_embeddings(invalid_emb1, invalid_emb2)
    print(f"✓ Result: {score.matching_result.value}")
    print(f"✓ Error (if any): {score.metadata.get('error', 'None')}")
    
    # Test 2: NaN values
    print("\nTest 2: NaN values in embedding")
    emb_with_nan = np.random.randn(192)
    emb_with_nan[0] = np.nan
    valid_emb = np.random.randn(192)
    
    score = comparator.compare_embeddings(emb_with_nan, valid_emb)
    print(f"✓ Result: {score.matching_result.value}")
    print(f"✓ Error detected: {'error' in score.metadata}")
    
    # Test 3: Empty embedding
    print("\nTest 3: Empty embedding")
    empty_emb = np.array([])
    
    score = comparator.compare_embeddings(empty_emb, valid_emb)
    print(f"✓ Result: {score.matching_result.value}")
    print(f"✓ Error detected: {'error' in score.metadata}")


def example_10_performance_comparison():
    """Example 10: Performance comparison of strategies"""
    print("\n" + "="*70)
    print("EXAMPLE 10: Strategy Performance Comparison")
    print("="*70)
    
    import time
    
    # Create larger embeddings to measure timing
    reference = np.random.randn(192).astype(np.float32)
    test = reference + np.random.randn(192).astype(np.float32) * 0.15
    
    comparator = MatchingComparator()
    strategies = [
        MatchingStrategy.COSINE,
        MatchingStrategy.EUCLIDEAN,
        MatchingStrategy.CORRELATION,
        MatchingStrategy.CHEBYSHEV,
        MatchingStrategy.HYBRID,
        MatchingStrategy.STATISTICAL,
        MatchingStrategy.ADAPTIVE
    ]
    
    print(f"\n{'Strategy':<15} {'Time (ms)':<12} {'Score':<10} {'Confidence':<12}")
    print("-" * 49)
    
    for strategy in strategies:
        start = time.time()
        score = comparator.compare_embeddings(reference, test, strategy=strategy)
        elapsed = (time.time() - start) * 1000  # Convert to milliseconds
        
        print(f"{strategy.value:<15} {elapsed:<12.4f} {score.final_score:<10.4f} {score.confidence:<12.4f}")


def run_all_examples():
    """Run all examples"""
    print("\n" + "="*70)
    print("MATCHING LOGIC - COMPREHENSIVE EXAMPLES")
    print("="*70)
    print("Demonstrating advanced matching strategies for voice verification")
    
    example_1_basic_cosine_matching()
    example_2_hybrid_matching()
    example_3_multiple_strategies()
    example_4_adaptive_threshold()
    example_5_detailed_metrics()
    example_6_verification_with_advanced_matching()
    example_7_multi_embedding_comparison()
    example_8_custom_strategy_weights()
    example_9_error_handling()
    example_10_performance_comparison()
    
    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
    print("="*70)


if __name__ == "__main__":
    run_all_examples()
