"""
Embedding quality metrics and statistics.
"""

import numpy as np
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingMetrics:
    """Metrics and metadata for an embedding"""
    embedding_id: str
    phone_number: str
    dimensions: int
    magnitude: float
    mean_value: float
    std_value: float
    min_value: float
    max_value: float
    timestamp: datetime
    generation_method: str  # 'standard', 'chunked', 'auto'
    audio_duration_ms: Optional[float] = None
    n_chunks: Optional[int] = None
    quality_score: Optional[float] = None


@dataclass
class EmbeddingComparison:
    """Result of comparing two embeddings"""
    query_phone: str
    enrolled_phone: str
    cosine_similarity: float
    euclidean_distance: float
    manhattan_distance: float
    chebyshev_distance: float
    is_match: bool
    confidence: float
    threshold: float


class EmbeddingStats:
    """Calculate statistics for embeddings"""
    
    @staticmethod
    def calculate_metrics(embedding: np.ndarray, 
                         embedding_id: str,
                         phone_number: str,
                         generation_method: str = 'standard',
                         audio_duration_ms: Optional[float] = None,
                         n_chunks: Optional[int] = None) -> EmbeddingMetrics:
        """
        Calculate comprehensive metrics for an embedding
        
        Args:
            embedding: 192-dimensional embedding vector
            embedding_id: Unique identifier for this embedding
            phone_number: Associated phone number
            generation_method: How the embedding was generated
            audio_duration_ms: Audio duration in milliseconds
            n_chunks: Number of chunks used if chunked method
            
        Returns:
            EmbeddingMetrics object with all calculated metrics
        """
        return EmbeddingMetrics(
            embedding_id=embedding_id,
            phone_number=phone_number,
            dimensions=len(embedding),
            magnitude=float(np.linalg.norm(embedding)),
            mean_value=float(np.mean(embedding)),
            std_value=float(np.std(embedding)),
            min_value=float(np.min(embedding)),
            max_value=float(np.max(embedding)),
            timestamp=datetime.utcnow(),
            generation_method=generation_method,
            audio_duration_ms=audio_duration_ms,
            n_chunks=n_chunks,
            quality_score=None  # Will be set if quality check is performed
        )
    
    @staticmethod
    def calculate_embedding_quality(embedding: np.ndarray) -> float:
        """
        Calculate quality score for an embedding (0-1)
        
        Based on:
        - Magnitude (should be well-normalized, typically 1.0)
        - Distribution (std dev indicates good variance)
        - Range (should use reasonable portion of numeric range)
        
        Args:
            embedding: The embedding vector
            
        Returns:
            Quality score between 0 and 1
        """
        # Check magnitude (should be close to 1.0 for normalized embeddings)
        magnitude = np.linalg.norm(embedding)
        magnitude_score = 1.0 - abs(magnitude - 1.0)  # Penalize deviation from 1.0
        magnitude_score = max(0.5, magnitude_score)  # At least 0.5 if magnitude is reasonable
        
        # Check distribution variance (should have reasonable std dev)
        std_dev = np.std(embedding)
        variance_score = min(1.0, std_dev * 2)  # Higher std is better, but cap at 1.0
        variance_score = max(0.5, variance_score)  # At least 0.5
        
        # Check range usage (should use reasonable range)
        range_val = np.max(embedding) - np.min(embedding)
        range_score = min(1.0, range_val / 5.0)  # Expect range of ~5
        range_score = max(0.5, range_score)  # At least 0.5
        
        # Weighted average
        quality = (magnitude_score * 0.4 + variance_score * 0.3 + range_score * 0.3)
        
        return float(quality)