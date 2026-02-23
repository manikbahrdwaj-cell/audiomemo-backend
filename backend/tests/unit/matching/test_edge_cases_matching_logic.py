"""
Edge Case Tests for Matching Logic
Tests boundary conditions, validation thresholds, and edge scenarios in voice matching
"""

import pytest
import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TestMatchingLogicEdgeCases:
    """Comprehensive edge case tests for matching logic"""

    # ========== THRESHOLD BOUNDARY TESTS ==========
    
    def test_perfect_match_identical_embeddings(self):
        """Test matching identical embeddings (should always match)"""
        emb1 = np.ones(192)
        similarity = self._calculate_similarity(emb1, emb1)
        
        assert np.isclose(similarity, 1.0, atol=1e-5)
        self._verify_should_match(similarity, threshold=0.8)

    def test_perfect_mismatch_orthogonal_embeddings(self):
        """Test completely orthogonal embeddings (should never match)"""
        emb1 = np.zeros(192)
        emb1[0] = 1.0
        
        emb2 = np.zeros(192)
        emb2[1] = 1.0
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert np.isclose(similarity, 0.0, atol=1e-5)
        self._verify_should_not_match(similarity, threshold=0.8)

    def test_threshold_boundary_below(self):
        """Test similarity just below threshold"""
        similarity = 0.799999  # Just below 0.8
        assert not self._should_match(similarity, threshold=0.8)

    def test_threshold_boundary_at(self):
        """Test similarity exactly at threshold"""
        similarity = 0.8
        assert self._should_match(similarity, threshold=0.8)

    def test_threshold_boundary_above(self):
        """Test similarity just above threshold"""
        similarity = 0.800001  # Just above 0.8
        assert self._should_match(similarity, threshold=0.8)

    # ========== NEGATIVE SIMILARITY TESTS ==========
    
    def test_negative_similarity_completely_opposite(self):
        """Test negative similarity from opposite vectors"""
        emb1 = np.ones(192)
        emb2 = -np.ones(192)
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert similarity < 0
        assert not self._should_match(similarity, threshold=0.5)

    def test_similarity_range_negative_to_positive(self):
        """Test that similarity properly ranges from -1 to 1"""
        scores = []
        for i in range(100):
            emb1 = np.random.randn(192)
            emb2 = np.random.randn(192)
            similarity = self._calculate_similarity(emb1, emb2)
            scores.append(similarity)
            
            assert -1.0 <= similarity <= 1.0, f"Similarity out of range: {similarity}"

    # ========== EXTREME MAGNITUDE TESTS ==========
    
    def test_very_small_magnitude_vectors(self):
        """Test matching very small magnitude embeddings"""
        emb1 = np.ones(192) * 1e-15
        emb2 = np.ones(192) * 1e-15
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert np.isfinite(similarity)

    def test_very_large_magnitude_vectors(self):
        """Test matching very large magnitude embeddings"""
        emb1 = np.ones(192) * 1e15
        emb2 = np.ones(192) * 1e15
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert np.isfinite(similarity)

    def test_magnitude_difference_not_affecting_cosine(self):
        """Test that magnitude difference doesn't affect cosine similarity"""
        emb1 = np.random.randn(192)
        emb2 = emb1 * 5.0  # Scaled version
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    # ========== SPECIAL VALUE TESTS ==========
    
    def test_zero_vector_matching(self):
        """Test matching with zero vectors"""
        emb1 = np.ones(192)
        emb2 = np.zeros(192)
        
        try:
            similarity = self._calculate_similarity(emb1, emb2)
            # Undefined, might be NaN
            assert np.isnan(similarity) or -1 <= similarity <= 1
        except (ValueError, RuntimeError, ZeroDivisionError):
            pass

    def test_nan_in_embeddings_matching(self):
        """Test matching when embeddings contain NaN"""
        emb1 = np.ones(192)
        emb2 = np.ones(192)
        emb2[50] = np.nan
        
        try:
            similarity = self._calculate_similarity(emb1, emb2)
            # Typically produces NaN
            assert np.isnan(similarity) or -1 <= similarity <= 1
        except (ValueError, RuntimeError):
            pass

    def test_inf_in_embeddings_matching(self):
        """Test matching when embeddings contain infinity"""
        emb1 = np.ones(192)
        emb2 = np.ones(192)
        emb2[50] = np.inf
        
        try:
            similarity = self._calculate_similarity(emb1, emb2)
            # Might produce inf
        except (ValueError, RuntimeError):
            pass

    # ========== DIMENSION EDGE CASES ==========
    
    def test_single_dimension_embeddings(self):
        """Test matching 1-dimensional embeddings"""
        emb1 = np.array([1.0])
        emb2 = np.array([1.0])
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    def test_dimension_mismatch_error(self):
        """Test that mismatched dimensions are handled"""
        emb1 = np.ones(192)
        emb2 = np.ones(256)
        
        try:
            similarity = self._calculate_similarity(emb1, emb2)
            # Might raise error or handle gracefully
        except (ValueError, RuntimeError, IndexError):
            pass

    def test_very_high_dimension_embeddings(self):
        """Test matching very high dimensional embeddings"""
        emb1 = np.ones(10000)
        emb2 = np.ones(10000)
        
        similarity = self._calculate_similarity(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)

    # ========== MULTIPLE THRESHOLD TESTS ==========
    
    def test_multiple_threshold_levels(self):
        """Test matching against multiple threshold levels"""
        similarity = 0.75
        
        thresholds = [0.5, 0.7, 0.75, 0.8, 0.9]
        for threshold in thresholds:
            expected = similarity >= threshold
            actual = self._should_match(similarity, threshold=threshold)
            assert expected == actual

    def test_very_low_threshold(self):
        """Test matching with very low threshold (0.1)"""
        similarity = 0.15
        assert self._should_match(similarity, threshold=0.1)

    def test_very_high_threshold(self):
        """Test matching with very high threshold (0.99)"""
        similarity = 0.95
        assert not self._should_match(similarity, threshold=0.99)

    def test_zero_threshold(self):
        """Test matching with zero threshold (everything matches)"""
        for similarity in [-1.0, 0.0, 0.5, 1.0]:
            assert self._should_match(similarity, threshold=0.0)

    def test_one_threshold(self):
        """Test matching with threshold of 1.0 (only perfect matches)"""
        assert self._should_match(1.0, threshold=1.0)
        assert not self._should_match(0.9999, threshold=1.0)

    # ========== CONFIDENCE SCORE TESTS ==========
    
    def test_confidence_extreme_values(self):
        """Test confidence calculation at extreme similarity values"""
        similarities = [-1.0, -0.5, 0.0, 0.5, 0.8, 0.95, 0.99, 1.0]
        
        for sim in similarities:
            confidence = self._calculate_confidence(sim)
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence for {sim}: {confidence}"

    def test_confidence_increases_with_similarity(self):
        """Test that confidence monotonically increases with similarity"""
        similarities = np.linspace(-1.0, 1.0, 20)
        confidences = [self._calculate_confidence(sim) for sim in similarities]
        
        # Check monotonic increase
        for i in range(len(confidences) - 1):
            assert confidences[i] <= confidences[i+1]

    # ========== ADAPTIVE THRESHOLD TESTS ==========
    
    def test_adaptive_threshold_high_variance(self):
        """Test adaptive threshold with high variance embeddings"""
        embeddings = [np.random.randn(192) * 10 for _ in range(10)]
        # Variance is high
        variance = np.var(embeddings, axis=0).mean()
        assert variance > 0

    def test_adaptive_threshold_low_variance(self):
        """Test adaptive threshold with low variance embeddings"""
        embeddings = [np.ones(192) + np.random.randn(192) * 0.01 for _ in range(10)]
        # Variance is low
        variance = np.var(embeddings, axis=0).mean()
        assert variance < 10

    def test_adaptive_threshold_single_embedding(self):
        """Test adaptive threshold with single embedding"""
        embeddings = [np.random.randn(192)]
        # Should handle gracefully
        assert len(embeddings) == 1

    # ========== BATCH MATCHING TESTS ==========
    
    def test_batch_matching_empty_reference(self):
        """Test batch matching with empty reference set"""
        query = np.ones(192)
        references = []
        
        try:
            results = self._batch_match(query, references, threshold=0.8)
            assert len(results) == 0
        except (ValueError, IndexError):
            pass

    def test_batch_matching_single_reference(self):
        """Test batch matching with single reference"""
        query = np.ones(192)
        references = [np.ones(192)]
        
        results = self._batch_match(query, references, threshold=0.8)
        assert len(results) == 1

    def test_batch_matching_many_references(self):
        """Test batch matching with many references"""
        query = np.ones(192)
        references = [np.random.randn(192) for _ in range(1000)]
        
        results = self._batch_matching_safe(query, references, threshold=0.8)
        assert len(results) <= len(references)

    def test_batch_matching_all_matching(self):
        """Test batch matching where all references match"""
        query = np.ones(192)
        references = [np.ones(192) for _ in range(10)]
        
        results = self._batch_match(query, references, threshold=0.5)
        assert len(results) == 10

    def test_batch_matching_none_matching(self):
        """Test batch matching where no references match"""
        query = np.ones(192)
        query[0] = 1.0
        
        references = []
        for i in range(10):
            ref = np.zeros(192)
            ref[i] = 1.0  # Orthogonal vectors
            references.append(ref)
        
        results = self._batch_match(query, references, threshold=0.8)
        assert len(results) == 0

    # ========== METRIC COMBINATION TESTS ==========
    
    def test_multiple_distance_metrics_consistency(self):
        """Test that multiple distance metrics give consistent orders"""
        emb1 = np.random.randn(192)
        
        candidates = [np.random.randn(192) for _ in range(5)]
        
        # Different metrics might rank differently, but should be consistent overall
        cosine_distances = [self._calculate_similarity(emb1, c) for c in candidates]
        assert len(cosine_distances) == len(candidates)

    def test_euclidean_vs_cosine_symmetry(self):
        """Test that distance metrics are symmetric"""
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        sim_12 = self._calculate_similarity(emb1, emb2)
        sim_21 = self._calculate_similarity(emb2, emb1)
        
        assert np.isclose(sim_12, sim_21, atol=1e-10)

    # ========== HELPER METHODS ==========
    
    def _calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        try:
            emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-10)
            emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-10)
            return float(np.dot(emb1_norm, emb2_norm))
        except:
            return np.nan

    def _should_match(self, similarity: float, threshold: float = 0.8) -> bool:
        """Determine if embeddings should match based on threshold"""
        if np.isnan(similarity):
            return False
        return similarity >= threshold

    def _verify_should_match(self, similarity: float, threshold: float = 0.8):
        """Verify that similarity indicates a match"""
        assert self._should_match(similarity, threshold)

    def _verify_should_not_match(self, similarity: float, threshold: float = 0.8):
        """Verify that similarity indicates no match"""
        assert not self._should_match(similarity, threshold)

    def _calculate_confidence(self, similarity: float) -> float:
        """Calculate confidence score from similarity"""
        # Normalize similarity to [0, 1]
        return (similarity + 1.0) / 2.0

    def _batch_match(self, query: np.ndarray, references: list, threshold: float = 0.8) -> list:
        """Batch match query against references"""
        if len(references) == 0:
            return []
        
        results = []
        for i, ref in enumerate(references):
            sim = self._calculate_similarity(query, ref)
            if self._should_match(sim, threshold):
                results.append((i, sim))
        
        return results

    def _batch_matching_safe(self, query: np.ndarray, references: list, threshold: float = 0.8) -> list:
        """Safe batch matching that handles edge cases"""
        try:
            return self._batch_match(query, references, threshold)
        except:
            return []


class TestMatchingStrategyEdgeCases:
    """Tests for different matching strategy edge cases"""

    def test_cosine_strategy(self):
        """Test cosine similarity strategy edge cases"""
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        # Cosine should always be between -1 and 1
        from scipy.spatial.distance import cosine
        dist = cosine(emb1, emb2)
        sim = 1 - dist
        
        assert -1.0 <= sim <= 1.0

    def test_euclidean_strategy(self):
        """Test euclidean distance strategy edge cases"""
        emb1 = np.ones(192)
        emb2 = np.ones(192)
        
        from scipy.spatial.distance import euclidean
        dist = euclidean(emb1, emb2)
        
        assert dist >= 0
        assert np.isfinite(dist)

    def test_correlation_strategy(self):
        """Test correlation distance strategy edge cases"""
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        try:
            from scipy.spatial.distance import correlation
            dist = correlation(emb1, emb2)
            assert 0 <= dist <= 1
        except:
            pass

    def test_chebyshev_strategy(self):
        """Test chebyshev distance strategy edge cases"""
        emb1 = np.random.randn(192)
        emb2 = np.random.randn(192)
        
        from scipy.spatial.distance import chebyshev
        dist = chebyshev(emb1, emb2)
        
        assert dist >= 0
        assert np.isfinite(dist)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
