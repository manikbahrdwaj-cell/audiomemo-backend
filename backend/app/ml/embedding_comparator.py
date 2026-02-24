"""
Embedding comparison utilities using multiple distance metrics.
"""

import numpy as np
import logging
from typing import Dict, List
from app.ml.embedding import calculate_cosine_similarity
from app.ml.embedding_metrics import EmbeddingComparison
logger = logging.getLogger(__name__)


class EmbeddingComparator:
    """Advanced embedding comparison with multiple distance metrics"""
    
    @staticmethod
    def compare(
        query_embedding: np.ndarray,
        stored_embedding: np.ndarray,
        query_phone: str,
        stored_phone: str,
        threshold: float = 0.75
    ) -> EmbeddingComparison:
        """
        Compare two embeddings using multiple distance metrics
        
        Args:
            query_embedding: Query embedding vector
            stored_embedding: Stored embedding vector to compare against
            query_phone: Phone number of query
            stored_phone: Phone number of stored embedding
            threshold: Similarity threshold for match determination
            
        Returns:
            EmbeddingComparison with multiple similarity scores
        """
        # Cosine similarity
        cosine_sim = calculate_cosine_similarity(query_embedding, stored_embedding)
        
        # Euclidean distance
        euclidean = float(np.linalg.norm(query_embedding - stored_embedding))
        
        # Manhattan distance
        manhattan = float(np.sum(np.abs(query_embedding - stored_embedding)))
        
        # Chebyshev distance (max absolute difference)
        chebyshev = float(np.max(np.abs(query_embedding - stored_embedding)))
        
        # Determine match and confidence
        is_match = cosine_sim >= threshold
        
        # Calculate confidence as deviation from threshold
        if is_match:
            confidence = min(1.0, (cosine_sim - threshold) / (1.0 - threshold))
        else:
            confidence = max(0.0, cosine_sim / threshold)
        
        return EmbeddingComparison(
            query_phone=query_phone,
            enrolled_phone=stored_phone,
            cosine_similarity=cosine_sim,
            euclidean_distance=euclidean,
            manhattan_distance=manhattan,
            chebyshev_distance=chebyshev,
            is_match=is_match,
            confidence=confidence,
            threshold=threshold
        )
    
    @staticmethod
    def batch_compare(
        query_embedding: np.ndarray,
        stored_embeddings: Dict[str, np.ndarray],
        threshold: float = 0.75
    ) -> List[EmbeddingComparison]:
        """
        Compare a query embedding against multiple stored embeddings
        
        Args:
            query_embedding: Query embedding vector
            stored_embeddings: Dict mapping phone_number -> embedding
            threshold: Similarity threshold
            
        Returns:
            List of EmbeddingComparison results, sorted by similarity
        """
        results = []
        
        for phone_number, embedding in stored_embeddings.items():
            comparison = EmbeddingComparator.compare(
                query_embedding,
                embedding,
                "query",
                phone_number,
                threshold
            )
            results.append(comparison)
        
        # Sort by cosine similarity (descending)
        results.sort(key=lambda x: x.cosine_similarity, reverse=True)
        
        return results