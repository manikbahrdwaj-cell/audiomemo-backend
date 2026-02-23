"""
Test Matching Logic
Comprehensive tests for advanced matching strategies
"""

import numpy as np
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from matching.matching_logic import (
    MatchingComparator,
    MatchingStrategy,
    MatchingResult,
    get_matching_comparator,
    reset_matching_comparator
)
from services.verification import (
    get_verification_manager,
    VerificationSessionConfig,
    VerificationResult,
    reset_verification_manager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_matching_comparator_initialization():
    """Test 1: Matching comparator initialization"""
    print("\n" + "="*60)
    print("TEST 1: Matching Comparator Initialization")
    print("="*60)
    
    try:
        reset_matching_comparator()
        comparator = get_matching_comparator()
        
        print("✓ Comparator initialized successfully")
        print(f"✓ Default strategy: {comparator.primary_strategy.value}")
        print(f"✓ Default threshold: {comparator.similarity_threshold}")
        print(f"✓ Confidence threshold: {comparator.confidence_threshold}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_cosine_matching():
    """Test 2: Cosine similarity matching"""
    print("\n" + "="*60)
    print("TEST 2: Cosine Similarity Matching")
    print("="*60)
    
    try:
        # Create two similar embeddings
        reference = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
        test = np.array([1.1, 2.1, 3.1, 4.1, 5.1], dtype=np.float32)
        
        comparator = MatchingComparator(
            primary_strategy=MatchingStrategy.COSINE,
            similarity_threshold=0.85
        )
        
        score = comparator.compare_embeddings(reference, test)
        
        print(f"✓ Cosine similarity: {score.primary_score:.4f}")
        print(f"✓ Final score: {score.final_score:.4f}")
        print(f"✓ Matching result: {score.matching_result.value}")
        print(f"✓ Confidence: {score.confidence:.4f}")
        
        # Test with dissimilar embeddings
        dissimilar = np.array([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float32)
        score2 = comparator.compare_embeddings(reference, dissimilar)
        
        print(f"\n✓ Dissimilar embedding similarity: {score2.primary_score:.4f}")
        print(f"✓ Result: {score2.matching_result.value}")
        
        if score.final_score > score2.final_score:
            print("✓ Correctly ranks similar vs dissimilar embeddings")
            return True
        else:
            print("✗ Failed to rank embeddings correctly")
            return False
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_euclidean_matching():
    """Test 3: Euclidean distance matching"""
    print("\n" + "="*60)
    print("TEST 3: Euclidean Distance Matching")
    print("="*60)
    
    try:
        reference = np.random.randn(192).astype(np.float32)
        test = reference + np.random.randn(192).astype(np.float32) * 0.1
        
        comparator = MatchingComparator(
            primary_strategy=MatchingStrategy.EUCLIDEAN,
            similarity_threshold=0.85
        )
        
        score = comparator.compare_embeddings(reference, test)
        
        print(f"✓ Euclidean distance: {score.metrics.euclidean_distance:.4f}")
        print(f"✓ Converted similarity: {score.final_score:.4f}")
        print(f"✓ Matching result: {score.matching_result.value}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_hybrid_matching():
    """Test 4: Hybrid matching strategy"""
    print("\n" + "="*60)
    print("TEST 4: Hybrid Matching Strategy")
    print("="*60)
    
    try:
        reference = np.random.randn(192).astype(np.float32)
        test = reference + np.random.randn(192).astype(np.float32) * 0.1
        
        comparator = MatchingComparator(
            primary_strategy=MatchingStrategy.HYBRID,
            similarity_threshold=0.85
        )
        
        score = comparator.compare_embeddings(reference, test)
        
        print(f"✓ Hybrid matching performed")
        print(f"✓ Final score: {score.final_score:.4f}")
        print(f"✓ Strategy: {score.strategy_used.value}")
        print(f"\nComponent breakdown:")
        for key, value in score.metadata.items():
            if 'component' in key:
                print(f"  - {key}: {value:.4f}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_all_matching_strategies():
    """Test 5: All matching strategies"""
    print("\n" + "="*60)
    print("TEST 5: All Matching Strategies")
    print("="*60)
    
    try:
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
        
        scores = {}
        for strategy in strategies:
            score = comparator.compare_embeddings(reference, test, strategy=strategy)
            scores[strategy.value] = {
                "score": score.final_score,
                "result": score.matching_result.value,
                "confidence": score.confidence
            }
        
        print(f"Strategy Comparison:\n")
        successful = 0
        for strategy_name, result in scores.items():
            print(f"✓ {strategy_name}: score={result['score']:.4f}, confidence={result['confidence']:.4f}")
            successful += 1
        
        return successful == len(strategies)
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_confidence_scoring():
    """Test 6: Confidence scoring"""
    print("\n" + "="*60)
    print("TEST 6: Confidence Scoring")
    print("="*60)
    
    try:
        comparator = MatchingComparator()
        
        # Test 1: Very similar embeddings (high confidence expected)
        similar_ref = np.random.randn(192).astype(np.float32)
        similar_test = similar_ref + np.random.randn(192).astype(np.float32) * 0.01
        
        score1 = comparator.compare_embeddings(similar_ref, similar_test)
        
        # Test 2: Moderately different embeddings (medium confidence)
        different_test = similar_ref + np.random.randn(192).astype(np.float32) * 0.3
        score2 = comparator.compare_embeddings(similar_ref, different_test)
        
        print(f"Very similar embeddings:")
        print(f"  ✓ Score: {score1.final_score:.4f}")
        print(f"  ✓ Confidence: {score1.confidence:.4f}")
        
        print(f"\nDifferent embeddings:")
        print(f"  ✓ Score: {score2.final_score:.4f}")
        print(f"  ✓ Confidence: {score2.confidence:.4f}")
        
        if score1.confidence > score2.confidence:
            print(f"\n✓ Confidence correctly higher for similar embeddings")
            return True
        else:
            print(f"\n✗ Confidence ordering incorrect")
            return False
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_error_handling():
    """Test 7: Error handling for invalid inputs"""
    print("\n" + "="*60)
    print("TEST 7: Error Handling")
    print("="*60)
    
    try:
        comparator = MatchingComparator()
        valid_emb = np.random.randn(192).astype(np.float32)
        
        tests_passed = 0
        
        # Test 1: Wrong dimension
        print("\nTest 1: Wrong dimension")
        wrong_dim = np.random.randn(100).astype(np.float32)
        score = comparator.compare_embeddings(wrong_dim, valid_emb)
        
        if score.matching_result == MatchingResult.ERROR:
            print("✓ Correctly rejected mismatched dimensions")
            tests_passed += 1
        else:
            print("✗ Failed to reject mismatched dimensions")
        
        # Test 2: NaN values
        print("\nTest 2: NaN values")
        nan_emb = np.random.randn(192).astype(np.float32)
        nan_emb[0] = np.nan
        score = comparator.compare_embeddings(nan_emb, valid_emb)
        
        if score.matching_result == MatchingResult.ERROR:
            print("✓ Correctly rejected NaN values")
            tests_passed += 1
        else:
            print("✗ Failed to reject NaN values")
        
        # Test 3: Empty embedding
        print("\nTest 3: Empty embedding")
        empty_emb = np.array([], dtype=np.float32)
        score = comparator.compare_embeddings(empty_emb, valid_emb)
        
        if score.matching_result == MatchingResult.ERROR:
            print("✓ Correctly rejected empty embedding")
            tests_passed += 1
        else:
            print("✗ Failed to reject empty embedding")
        
        return tests_passed == 3
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_multi_embedding_comparison():
    """Test 8: Multi-embedding comparison"""
    print("\n" + "="*60)
    print("TEST 8: Multi-Embedding Comparison")
    print("="*60)
    
    try:
        # Create embedding lists
        reference_embeddings = [
            np.random.randn(192).astype(np.float32) for _ in range(3)
        ]
        test_embeddings = [
            reference_embeddings[i] + np.random.randn(192).astype(np.float32) * 0.1
            for i in range(3)
        ]
        
        comparator = MatchingComparator()
        
        # Test different strategies
        strategies = ['best_match', 'all_match', 'weighted']
        results = {}
        
        for strat in strategies:
            result = comparator.compare_embedding_lists(
                reference_embeddings,
                test_embeddings,
                matching_strategy=strat
            )
            results[strat] = result
            print(f"\n✓ {strat.upper()} strategy:")
            print(f"  Overall score: {result['overall_score']:.4f}")
            print(f"  Mean score: {result['mean_score']:.4f}")
            print(f"  Comparisons: {result['num_comparisons']}")
        
        # Verify best_match >= all_match (best_match uses max, all_match uses min)
        if results['best_match']['overall_score'] >= results['all_match']['overall_score']:
            print(f"\n✓ Strategy scores in expected order (best >= all)")
            return True
        else:
            print(f"\n✗ Strategy scores not in expected order")
            return False
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_advanced_matching_in_verification():
    """Test 9: Advanced matching in verification service"""
    print("\n" + "="*60)
    print("TEST 9: Advanced Matching in Verification Service")
    print("="*60)
    
    try:
        reset_verification_manager()
        
        # Create config with advanced matching
        config = VerificationSessionConfig(
            similarity_threshold=0.85,
            matching_strategy='hybrid',
            use_advanced_matching=True,
            compute_confidence=True
        )
        
        manager = get_verification_manager(config)
        
        print("✓ Manager initialized with advanced matching")
        print(f"✓ Matching strategy: {config.matching_strategy}")
        print(f"✓ Advanced matching enabled: {config.use_advanced_matching}")
        print(f"✓ Confidence computation: {config.compute_confidence}")
        
        # Verify the manager has a matching comparator
        if hasattr(manager, 'matching_comparator'):
            print("✓ Matching comparator attached to manager")
            return True
        else:
            print("✗ No matching comparator in manager")
            return False
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_strategy_weights():
    """Test 10: Custom strategy weights"""
    print("\n" + "="*60)
    print("TEST 10: Custom Strategy Weights")
    print("="*60)
    
    try:
        comparator = MatchingComparator(
            primary_strategy=MatchingStrategy.HYBRID
        )
        
        # Set custom weights
        custom_weights = {
            MatchingStrategy.COSINE: 0.70,
            MatchingStrategy.EUCLIDEAN: 0.10,
            MatchingStrategy.CORRELATION: 0.10,
            MatchingStrategy.CHEBYSHEV: 0.05,
            MatchingStrategy.STATISTICAL: 0.05
        }
        
        comparator.set_strategy_weights(custom_weights)
        print("✓ Custom weights set successfully")
        
        # Test with custom weights
        reference = np.random.randn(192).astype(np.float32)
        test = reference + np.random.randn(192).astype(np.float32) * 0.1
        
        score = comparator.compare_embeddings(reference, test)
        
        print(f"✓ Comparison with custom weights: {score.final_score:.4f}")
        
        # Test invalid weights (don't sum to 1.0)
        try:
            bad_weights = {
                MatchingStrategy.COSINE: 0.5,
                MatchingStrategy.EUCLIDEAN: 0.3,
                MatchingStrategy.CORRELATION: 0.1,
                MatchingStrategy.CHEBYSHEV: 0.05,
                MatchingStrategy.STATISTICAL: 0.05
            }
            comparator.set_strategy_weights(bad_weights)
            print("✗ Failed to reject invalid weights")
            return False
        except ValueError:
            print("✓ Correctly rejected invalid weights (don't sum to 1.0)")
            return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("MATCHING LOGIC TEST SUITE")
    print("="*70)
    
    tests = [
        test_matching_comparator_initialization,
        test_cosine_matching,
        test_euclidean_matching,
        test_hybrid_matching,
        test_all_matching_strategies,
        test_confidence_scoring,
        test_error_handling,
        test_multi_embedding_comparison,
        test_advanced_matching_in_verification,
        test_strategy_weights
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        result = test()
        if result:
            passed += 1
        else:
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✓ Passed: {passed}/{len(tests)}")
    print(f"✗ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
    else:
        print(f"\n✗ {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
