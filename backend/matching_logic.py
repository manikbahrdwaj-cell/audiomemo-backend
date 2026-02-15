"""
Advanced Matching Logic Module
Implements multiple matching strategies for voice verification
Provides comprehensive similarity computation with adaptive thresholds
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from scipy.spatial.distance import cosine, euclidean, correlation, chebyshev
from scipy.stats import entropy, ks_2samp, wasserstein_distance

logger = logging.getLogger(__name__)


class MatchingStrategy(Enum):
    """Available matching strategies"""
    COSINE = "cosine"  # Cosine similarity (default)
    EUCLIDEAN = "euclidean"  # Euclidean distance
    CORRELATION = "correlation"  # Correlation-based
    CHEBYSHEV = "chebyshev"  # Chebyshev distance
    HYBRID = "hybrid"  # Weighted combination
    STATISTICAL = "statistical"  # Statistical test-based
    ADAPTIVE = "adaptive"  # Adaptive threshold based on variance


class MatchingResult(Enum):
    """Matching result status"""
    STRONG_MATCH = "strong_match"  # High confidence match
    WEAK_MATCH = "weak_match"  # Borderline match
    NO_MATCH = "no_match"  # Clear mismatch
    INCONCLUSIVE = "inconclusive"  # Insufficient data
    ERROR = "error"  # Processing error


@dataclass
class MatchingMetrics:
    """Comprehensive matching metrics"""
    cosine_similarity: float = 0.0
    euclidean_distance: float = 0.0
    correlation_distance: float = 0.0
    chebyshev_distance: float = 0.0
    entropy_distance: float = 0.0
    wasserstein_distance: float = 0.0
    statistical_p_value: float = 1.0
    vector_magnitude_ratio: float = 1.0
    vector_angle_degrees: float = 180.0
    embedding_norm_difference: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "cosine_similarity": float(self.cosine_similarity),
            "euclidean_distance": float(self.euclidean_distance),
            "correlation_distance": float(self.correlation_distance),
            "chebyshev_distance": float(self.chebyshev_distance),
            "entropy_distance": float(self.entropy_distance),
            "wasserstein_distance": float(self.wasserstein_distance),
            "statistical_p_value": float(self.statistical_p_value),
            "vector_magnitude_ratio": float(self.vector_magnitude_ratio),
            "vector_angle_degrees": float(self.vector_angle_degrees),
            "embedding_norm_difference": float(self.embedding_norm_difference)
        }


@dataclass
class MatchingScore:
    """Comprehensive matching score with confidence"""
    primary_score: float  # Score from primary strategy
    final_score: float  # Final computed score
    matching_result: MatchingResult
    strategy_used: MatchingStrategy
    confidence: float  # Confidence level (0.0-1.0)
    metrics: MatchingMetrics = field(default_factory=MatchingMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    match_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "match_id": self.match_id,
            "primary_score": float(self.primary_score),
            "final_score": float(self.final_score),
            "matching_result": self.matching_result.value,
            "strategy_used": self.strategy_used.value,
            "confidence": float(self.confidence),
            "metrics": self.metrics.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class MatchingComparator:
    """
    Advanced matching comparator for voice embeddings
    
    Features:
    - Multiple matching strategies (cosine, euclidean, correlation, etc.)
    - Hybrid matching with weighted strategies
    - Statistical testing for verification
    - Adaptive thresholding based on data characteristics
    - Confidence scoring
    - Comprehensive metrics calculation
    """
    
    def __init__(
        self,
        primary_strategy: MatchingStrategy = MatchingStrategy.COSINE,
        similarity_threshold: float = 0.85,
        confidence_threshold: float = 0.70
    ):
        """
        Initialize matching comparator
        
        Args:
            primary_strategy: Primary matching strategy to use
            similarity_threshold: Threshold for matching decision
            confidence_threshold: Minimum confidence for decision
        """
        self.primary_strategy = primary_strategy
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        
        # Strategy weights for hybrid matching
        self.strategy_weights = {
            MatchingStrategy.COSINE: 0.40,
            MatchingStrategy.EUCLIDEAN: 0.20,
            MatchingStrategy.CORRELATION: 0.20,
            MatchingStrategy.CHEBYSHEV: 0.10,
            MatchingStrategy.STATISTICAL: 0.10
        }
        
        logger.info(
            f"MatchingComparator initialized with strategy={primary_strategy.value}, "
            f"threshold={similarity_threshold}"
        )
    
    def compare_embeddings(
        self,
        reference_embedding: np.ndarray,
        test_embedding: np.ndarray,
        strategy: Optional[MatchingStrategy] = None
    ) -> MatchingScore:
        """
        Compare two embeddings using specified strategy
        
        Args:
            reference_embedding: Reference embedding (from enrollment)
            test_embedding: Test embedding (from verification)
            strategy: Optional strategy override
            
        Returns:
            MatchingScore with detailed results
        """
        strategy = strategy or self.primary_strategy
        
        try:
            # Validate embeddings
            if not self._validate_embeddings(reference_embedding, test_embedding):
                return MatchingScore(
                    primary_score=0.0,
                    final_score=0.0,
                    matching_result=MatchingResult.ERROR,
                    strategy_used=strategy,
                    confidence=0.0,
                    metadata={"error": "Invalid embeddings"}
                )
            
            # Calculate all metrics
            metrics = self._calculate_all_metrics(reference_embedding, test_embedding)
            
            # Compute score based on strategy
            if strategy == MatchingStrategy.COSINE:
                score = self._cosine_matching(reference_embedding, test_embedding, metrics)
            elif strategy == MatchingStrategy.EUCLIDEAN:
                score = self._euclidean_matching(reference_embedding, test_embedding, metrics)
            elif strategy == MatchingStrategy.CORRELATION:
                score = self._correlation_matching(reference_embedding, test_embedding, metrics)
            elif strategy == MatchingStrategy.CHEBYSHEV:
                score = self._chebyshev_matching(reference_embedding, test_embedding, metrics)
            elif strategy == MatchingStrategy.HYBRID:
                score = self._hybrid_matching(reference_embedding, test_embedding, metrics)
            elif strategy == MatchingStrategy.STATISTICAL:
                score = self._statistical_matching(reference_embedding, test_embedding, metrics)
            elif strategy == MatchingStrategy.ADAPTIVE:
                score = self._adaptive_matching(reference_embedding, test_embedding, metrics)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
            
            score.metrics = metrics
            return score
            
        except Exception as e:
            logger.error(f"Error in compare_embeddings: {e}")
            return MatchingScore(
                primary_score=0.0,
                final_score=0.0,
                matching_result=MatchingResult.ERROR,
                strategy_used=strategy,
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def _validate_embeddings(
        self,
        ref: np.ndarray,
        test: np.ndarray
    ) -> bool:
        """Validate embedding arrays"""
        if not isinstance(ref, np.ndarray) or not isinstance(test, np.ndarray):
            return False
        if len(ref.shape) != 1 or len(test.shape) != 1:
            return False
        if ref.shape[0] == 0 or test.shape[0] == 0:
            return False
        if ref.shape[0] != test.shape[0]:
            return False
        if np.any(np.isnan(ref)) or np.any(np.isnan(test)):
            return False
        return True
    
    def _calculate_all_metrics(
        self,
        reference: np.ndarray,
        test: np.ndarray
    ) -> MatchingMetrics:
        """Calculate all distance/similarity metrics"""
        metrics = MatchingMetrics()
        
        try:
            # Cosine similarity (1 - cosine distance)
            metrics.cosine_similarity = float(1.0 - cosine(reference, test))
            
            # Euclidean distance
            metrics.euclidean_distance = float(euclidean(reference, test))
            
            # Correlation distance
            metrics.correlation_distance = float(correlation(reference, test))
            
            # Chebyshev distance
            metrics.chebyshev_distance = float(chebyshev(reference, test))
            
            # Vector properties
            ref_norm = np.linalg.norm(reference)
            test_norm = np.linalg.norm(test)
            metrics.vector_magnitude_ratio = float(test_norm / (ref_norm + 1e-8))
            metrics.embedding_norm_difference = float(abs(ref_norm - test_norm))
            
            # Vector angle
            dot_product = np.dot(reference, test)
            cos_angle = dot_product / (ref_norm * test_norm + 1e-8)
            cos_angle = np.clip(cos_angle, -1, 1)
            metrics.vector_angle_degrees = float(np.degrees(np.arccos(cos_angle)))
            
            # Entropy distance
            ref_norm_vec = reference / (np.sum(np.abs(reference)) + 1e-8)
            test_norm_vec = test / (np.sum(np.abs(test)) + 1e-8)
            ref_norm_vec = np.abs(ref_norm_vec)
            test_norm_vec = np.abs(test_norm_vec)
            metrics.entropy_distance = float(entropy(ref_norm_vec + 1e-10, test_norm_vec + 1e-10))
            
            # Wasserstein distance
            metrics.wasserstein_distance = float(wasserstein_distance(reference, test))
            
            # Statistical test (KS test p-value)
            _, metrics.statistical_p_value = ks_2samp(reference, test)
            metrics.statistical_p_value = float(metrics.statistical_p_value)
            
        except Exception as e:
            logger.warning(f"Error calculating metrics: {e}")
        
        return metrics
    
    def _cosine_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Cosine similarity based matching"""
        score = metrics.cosine_similarity
        confidence = self._compute_confidence(score, metrics)
        
        if score >= self.similarity_threshold:
            result = MatchingResult.STRONG_MATCH if score >= self.similarity_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=score,
            final_score=score,
            matching_result=result,
            strategy_used=MatchingStrategy.COSINE,
            confidence=confidence,
            metadata={
                "threshold": self.similarity_threshold,
                "used_cosine_similarity": True
            }
        )
    
    def _euclidean_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Euclidean distance based matching"""
        # Convert distance to similarity (lower distance = higher similarity)
        max_distance = np.sqrt(len(reference) * 4)  # Approximate max for normalized vectors
        similarity = 1.0 - (metrics.euclidean_distance / (max_distance + 1e-8))
        similarity = np.clip(similarity, 0, 1)
        
        confidence = self._compute_confidence(similarity, metrics)
        
        if similarity >= self.similarity_threshold:
            result = MatchingResult.STRONG_MATCH if similarity >= self.similarity_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=similarity,
            final_score=similarity,
            matching_result=result,
            strategy_used=MatchingStrategy.EUCLIDEAN,
            confidence=confidence,
            metadata={
                "euclidean_distance": metrics.euclidean_distance,
                "max_distance": max_distance
            }
        )
    
    def _correlation_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Correlation-based matching"""
        # Convert correlation distance to similarity
        similarity = 1.0 - metrics.correlation_distance
        similarity = np.clip(similarity, 0, 1)
        
        confidence = self._compute_confidence(similarity, metrics)
        
        if similarity >= self.similarity_threshold:
            result = MatchingResult.STRONG_MATCH if similarity >= self.similarity_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=similarity,
            final_score=similarity,
            matching_result=result,
            strategy_used=MatchingStrategy.CORRELATION,
            confidence=confidence,
            metadata={
                "correlation_distance": metrics.correlation_distance
            }
        )
    
    def _chebyshev_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Chebyshev distance based matching"""
        # Convert distance to similarity
        max_chebyshev = 2.0  # Approximate max for normalized vectors
        similarity = 1.0 - (metrics.chebyshev_distance / (max_chebyshev + 1e-8))
        similarity = np.clip(similarity, 0, 1)
        
        confidence = self._compute_confidence(similarity, metrics)
        
        if similarity >= self.similarity_threshold:
            result = MatchingResult.STRONG_MATCH if similarity >= self.similarity_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=similarity,
            final_score=similarity,
            matching_result=result,
            strategy_used=MatchingStrategy.CHEBYSHEV,
            confidence=confidence,
            metadata={
                "chebyshev_distance": metrics.chebyshev_distance
            }
        )
    
    def _hybrid_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Hybrid matching combining multiple strategies"""
        # Normalize all metrics to 0-1 range
        cosine_sim = metrics.cosine_similarity
        euclidean_sim = 1.0 - np.clip(metrics.euclidean_distance / (np.sqrt(len(reference) * 4) + 1e-8), 0, 1)
        correlation_sim = 1.0 - np.clip(metrics.correlation_distance, 0, 1)
        chebyshev_sim = 1.0 - np.clip(metrics.chebyshev_distance / 2.0, 0, 1)
        statistical_sim = 1.0 - np.clip(metrics.statistical_p_value, 0, 1)
        
        # Weighted combination
        final_score = (
            self.strategy_weights[MatchingStrategy.COSINE] * cosine_sim +
            self.strategy_weights[MatchingStrategy.EUCLIDEAN] * euclidean_sim +
            self.strategy_weights[MatchingStrategy.CORRELATION] * correlation_sim +
            self.strategy_weights[MatchingStrategy.CHEBYSHEV] * chebyshev_sim +
            self.strategy_weights[MatchingStrategy.STATISTICAL] * statistical_sim
        )
        
        confidence = self._compute_confidence(final_score, metrics)
        
        if final_score >= self.similarity_threshold:
            result = MatchingResult.STRONG_MATCH if final_score >= self.similarity_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=cosine_sim,
            final_score=final_score,
            matching_result=result,
            strategy_used=MatchingStrategy.HYBRID,
            confidence=confidence,
            metadata={
                "cosine_component": cosine_sim,
                "euclidean_component": euclidean_sim,
                "correlation_component": correlation_sim,
                "chebyshev_component": chebyshev_sim,
                "statistical_component": statistical_sim
            }
        )
    
    def _statistical_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Statistical test-based matching"""
        # Use KS test p-value for similarity
        # Higher p-value = more similar distributions
        p_value = metrics.statistical_p_value
        
        # Convert p-value to similarity (higher p-value = higher similarity)
        similarity = 1.0 - np.clip(p_value, 0, 1)
        
        # Combine with cosine similarity for better balance
        combined_score = 0.7 * metrics.cosine_similarity + 0.3 * similarity
        
        confidence = self._compute_confidence(combined_score, metrics)
        
        if combined_score >= self.similarity_threshold:
            result = MatchingResult.STRONG_MATCH if combined_score >= self.similarity_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=combined_score,
            final_score=combined_score,
            matching_result=result,
            strategy_used=MatchingStrategy.STATISTICAL,
            confidence=confidence,
            metadata={
                "ks_test_p_value": p_value,
                "cosine_component": metrics.cosine_similarity,
                "statistical_component": similarity
            }
        )
    
    def _adaptive_matching(
        self,
        reference: np.ndarray,
        test: np.ndarray,
        metrics: MatchingMetrics
    ) -> MatchingScore:
        """Adaptive matching with dynamic threshold"""
        # Calculate variance in the embeddings
        ref_variance = np.var(reference)
        test_variance = np.var(test)
        avg_variance = (ref_variance + test_variance) / 2.0
        
        # Adjust threshold based on variance
        # Higher variance = lower threshold (less strict)
        adaptive_threshold = self.similarity_threshold - (avg_variance * 0.1)
        adaptive_threshold = np.clip(adaptive_threshold, 0.70, 0.99)
        
        # Use cosine similarity as base
        score = metrics.cosine_similarity
        confidence = self._compute_confidence(score, metrics)
        
        if score >= adaptive_threshold:
            result = MatchingResult.STRONG_MATCH if score >= adaptive_threshold + 0.10 else MatchingResult.WEAK_MATCH
        else:
            result = MatchingResult.NO_MATCH
        
        return MatchingScore(
            primary_score=score,
            final_score=score,
            matching_result=result,
            strategy_used=MatchingStrategy.ADAPTIVE,
            confidence=confidence,
            metadata={
                "adaptive_threshold": adaptive_threshold,
                "reference_variance": ref_variance,
                "test_variance": test_variance,
                "avg_variance": avg_variance
            }
        )
    
    def _compute_confidence(
        self,
        primary_score: float,
        metrics: MatchingMetrics
    ) -> float:
        """
        Compute confidence level
        Based on consistency across different metrics
        """
        # Check consistency across metrics
        cosine_score = metrics.cosine_similarity
        euclidean_score = 1.0 - np.clip(metrics.euclidean_distance / (np.sqrt(len(metrics.cosine_similarity).__sizeof__()) + 1e-8), 0, 1)
        correlation_score = 1.0 - np.clip(metrics.correlation_distance, 0, 1)
        
        # Calculate standard deviation of normalized scores
        scores = [cosine_score, euclidean_score, correlation_score]
        consistency = 1.0 - np.std(scores)
        consistency = np.clip(consistency, 0, 1)
        
        # Factor in magnitude ratio (should be close to 1.0)
        magnitude_consistency = 1.0 - abs(metrics.vector_magnitude_ratio - 1.0)
        magnitude_consistency = np.clip(magnitude_consistency, 0, 1)
        
        # Factor in angle (should be small)
        angle_consistency = 1.0 - (metrics.vector_angle_degrees / 180.0)
        angle_consistency = np.clip(angle_consistency, 0, 1)
        
        # Combine factors
        confidence = (
            0.4 * consistency +
            0.3 * magnitude_consistency +
            0.3 * angle_consistency
        )
        
        return float(np.clip(confidence, 0, 1))
    
    def compare_embedding_lists(
        self,
        reference_embeddings: List[np.ndarray],
        test_embeddings: List[np.ndarray],
        matching_strategy: str = 'best_match'
    ) -> Dict[str, Any]:
        """
        Compare lists of embeddings
        
        Args:
            reference_embeddings: List of reference embeddings
            test_embeddings: List of test embeddings
            matching_strategy: 'best_match', 'all_match', or 'weighted'
            
        Returns:
            Detailed comparison results
        """
        if not reference_embeddings or not test_embeddings:
            return {"error": "Empty embedding lists"}
        
        scores = []
        matches = []
        
        # Compare each test embedding with each reference embedding
        for test_emb in test_embeddings:
            best_score = 0.0
            for ref_emb in reference_embeddings:
                score = self.compare_embeddings(ref_emb, test_emb)
                scores.append(score.final_score)
                if score.final_score > best_score:
                    best_score = score.final_score
            matches.append(best_score)
        
        if matching_strategy == 'best_match':
            overall_score = max(matches) if matches else 0.0
        elif matching_strategy == 'all_match':
            overall_score = min(matches) if matches else 0.0
        else:  # weighted
            overall_score = np.mean(matches) if matches else 0.0
        
        return {
            "overall_score": float(overall_score),
            "individual_scores": [float(s) for s in matches],
            "strategy": matching_strategy,
            "num_comparisons": len(scores),
            "mean_score": float(np.mean(scores)) if scores else 0.0,
            "max_score": float(max(scores)) if scores else 0.0,
            "min_score": float(min(scores)) if scores else 0.0,
            "std_dev": float(np.std(scores)) if len(scores) > 1 else 0.0
        }
    
    def set_strategy_weights(self, weights: Dict[MatchingStrategy, float]):
        """Update strategy weights for hybrid matching"""
        if abs(sum(weights.values()) - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        self.strategy_weights = weights
        logger.info(f"Updated strategy weights: {weights}")


# Global comparator instance
_matching_comparator: Optional[MatchingComparator] = None


def get_matching_comparator(
    strategy: MatchingStrategy = MatchingStrategy.COSINE,
    similarity_threshold: float = 0.85
) -> MatchingComparator:
    """
    Get global matching comparator instance (singleton pattern)
    
    Args:
        strategy: Primary matching strategy
        similarity_threshold: Threshold for matching decision
        
    Returns:
        MatchingComparator instance
    """
    global _matching_comparator
    
    if _matching_comparator is None:
        _matching_comparator = MatchingComparator(
            primary_strategy=strategy,
            similarity_threshold=similarity_threshold
        )
        logger.info("Initialized global MatchingComparator")
    
    return _matching_comparator


def reset_matching_comparator():
    """Reset global matching comparator (useful for testing)"""
    global _matching_comparator
    _matching_comparator = None
    logger.info("Reset global MatchingComparator")
