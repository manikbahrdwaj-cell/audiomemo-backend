"""
Advanced Embedding Similarity Operations using SciPy
Provides comprehensive similarity metrics, batch operations, and clustering functionality
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from scipy.spatial.distance import cdist, cosine, pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from scipy import spatial

from app.ml.embedding import calculate_cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class SimilarityResult:
    """Result of a similarity comparison"""
    embedding1_id: str
    embedding2_id: str
    cosine_similarity: float
    cosine_distance: float
    euclidean_distance: float
    correlation_distance: Optional[float] = None
    is_match: bool = False
    confidence: float = 0.0
    metadata: Optional[Dict] = None


@dataclass
class SimilarityMatrix:
    """Represents a matrix of similarities between embeddings"""
    embeddings: np.ndarray  # Shape: (n, embedding_dim)
    similarity_matrix: np.ndarray  # Shape: (n, n), values in [-1, 1]
    distance_matrix: np.ndarray  # Shape: (n, n), Euclidean distances
    labels: Optional[List[str]] = None  # Labels for each embedding
    embedding_dim: int = 192


class EmbeddingSimilarityCalculator:
    """
    Advanced embedding similarity calculations using scipy
    
    Computes various distance and similarity metrics:
    - Cosine similarity/distance
    - Euclidean distance
    - Correlation distance
    - Bhattacharyya distance
    - Batch operations on multiple embeddings
    """
    
    def __init__(self, metric: str = 'cosine'):
        """
        Initialize the calculator
        
        Args:
            metric: Default distance metric ('cosine', 'euclidean', 'correlation')
        """
        self.metric = metric
        self.valid_metrics = ['cosine', 'euclidean', 'correlation', 'braycurtis', 'canberra', 'chebyshev']
        
        if metric not in self.valid_metrics:
            raise ValueError(f"Invalid metric '{metric}'. Choose from: {self.valid_metrics}")
        
        logger.info(f"Initialized EmbeddingSimilarityCalculator with metric={metric}")
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Returns a score between 0 and 1:
        - 1.0: identical embeddings
        - 0.5: orthogonal embeddings
        - 0.0: opposite embeddings
        """
        return calculate_cosine_similarity(emb1, emb2)
    
    def cosine_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate cosine distance between two embeddings
        
        Distance = 1 - similarity
        Returns a score between 0 and 1
        """
        try:
            emb1 = np.asarray(emb1, dtype=np.float32)
            emb2 = np.asarray(emb2, dtype=np.float32)
            
            if emb1.size == 0 or emb2.size == 0:
                return 1.0
            
            # scipy's cosine returns distance in [0, 2]
            distance = cosine(emb1, emb2)
            # Normalize to [0, 1]
            return float(np.clip(distance / 2.0, 0.0, 1.0))
        except Exception as e:
            logger.warning(f"Error calculating cosine distance: {e}")
            return 1.0
    
    def euclidean_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate Euclidean distance between two embeddings
        
        Returns the L2 norm of the difference vector
        """
        try:
            emb1 = np.asarray(emb1, dtype=np.float32)
            emb2 = np.asarray(emb2, dtype=np.float32)
            
            if emb1.size == 0 or emb2.size == 0:
                return float('inf')
            
            distance = np.linalg.norm(emb1 - emb2)
            return float(distance)
        except Exception as e:
            logger.warning(f"Error calculating Euclidean distance: {e}")
            return float('inf')
    
    def correlation_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate correlation distance between two embeddings
        
        Based on Pearson correlation coefficient
        """
        try:
            emb1 = np.asarray(emb1, dtype=np.float32)
            emb2 = np.asarray(emb2, dtype=np.float32)
            
            if emb1.size == 0 or emb2.size == 0:
                return 1.0
            
            # Correlation distance = 1 - correlation
            distance = spatial.distance.correlation(emb1, emb2)
            return float(np.clip(distance, 0.0, 1.0))
        except Exception as e:
            logger.warning(f"Error calculating correlation distance: {e}")
            return 1.0
    
    def compare(
        self,
        emb1: np.ndarray,
        emb2: np.ndarray,
        emb1_id: str = "emb1",
        emb2_id: str = "emb2",
        threshold: float = 0.6
    ) -> SimilarityResult:
        """
        Compare two embeddings and return comprehensive result
        
        Args:
            emb1: First embedding
            emb2: Second embedding
            emb1_id: Label for first embedding
            emb2_id: Label for second embedding
            threshold: Similarity threshold for match determination
            
        Returns:
            SimilarityResult with all metrics
        """
        cos_sim = self.cosine_similarity(emb1, emb2)
        cos_dist = self.cosine_distance(emb1, emb2)
        eucl_dist = self.euclidean_distance(emb1, emb2)
        corr_dist = self.correlation_distance(emb1, emb2)
        
        is_match = cos_sim >= threshold
        confidence = min(1.0, max(0.0, (cos_sim - threshold) / (1.0 - threshold)))
        
        return SimilarityResult(
            embedding1_id=emb1_id,
            embedding2_id=emb2_id,
            cosine_similarity=cos_sim,
            cosine_distance=cos_dist,
            euclidean_distance=eucl_dist,
            correlation_distance=corr_dist,
            is_match=is_match,
            confidence=confidence
        )
    
    def batch_compare(
        self,
        query_embedding: np.ndarray,
        embeddings: List[np.ndarray],
        embedding_ids: Optional[List[str]] = None,
        threshold: float = 0.6
    ) -> List[SimilarityResult]:
        """
        Compare one query embedding against multiple embeddings
        
        Args:
            query_embedding: Query embedding
            embeddings: List of embeddings to compare against
            embedding_ids: List of IDs for the embeddings
            threshold: Similarity threshold
            
        Returns:
            List of SimilarityResult objects, sorted by similarity (descending)
        """
        if not embeddings:
            return []
        
        if embedding_ids is None:
            embedding_ids = [f"emb_{i}" for i in range(len(embeddings))]
        
        results = []
        for emb, emb_id in zip(embeddings, embedding_ids):
            result = self.compare(
                query_embedding,
                emb,
                emb1_id="query",
                emb2_id=emb_id,
                threshold=threshold
            )
            results.append(result)
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x.cosine_similarity, reverse=True)
        
        logger.debug(f"Batch compared 1 query against {len(embeddings)} embeddings")
        return results
    
    def compute_similarity_matrix(
        self,
        embeddings: np.ndarray,
        labels: Optional[List[str]] = None,
        metric: str = 'cosine'
    ) -> SimilarityMatrix:
        """
        Compute similarity matrix for multiple embeddings
        
        Args:
            embeddings: Array of shape (n, embedding_dim)
            labels: Optional labels for each embedding
            metric: Distance metric to use
            
        Returns:
            SimilarityMatrix object
        """
        embeddings = np.asarray(embeddings, dtype=np.float32)
        
        if embeddings.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {embeddings.shape}")
        
        n_embeddings, embedding_dim = embeddings.shape
        
        # Compute pairwise distances using scipy
        distances = cdist(embeddings, embeddings, metric=metric)
        
        # Convert to similarity matrix
        if metric == 'cosine':
            # Cosine distance in [0, 2], convert to similarity in [0, 1]
            similarities = 1.0 - distances / 2.0
        else:
            # For other metrics, use 1 / (1 + distance) for rough similarity
            similarities = 1.0 / (1.0 + distances)
        
        logger.info(f"Computed similarity matrix for {n_embeddings} embeddings (metric={metric})")
        
        return SimilarityMatrix(
            embeddings=embeddings,
            similarity_matrix=similarities,
            distance_matrix=distances,
            labels=labels,
            embedding_dim=embedding_dim
        )
    
    def cluster_embeddings(
        self,
        embeddings: np.ndarray,
        labels: Optional[List[str]] = None,
        threshold: float = 0.6,
        method: str = 'average'
    ) -> Dict[int, List[Tuple[str, np.ndarray]]]:
        """
        Cluster embeddings based on similarity using hierarchical clustering
        
        Args:
            embeddings: Array of shape (n, embedding_dim)
            labels: Optional labels for each embedding
            threshold: Distance threshold for cluster cutoff
            method: Linkage method ('average', 'single', 'complete', 'ward')
            
        Returns:
            Dictionary mapping cluster ID to list of (label, embedding) tuples
        """
        if len(embeddings) < 2:
            if len(embeddings) == 1:
                label = labels[0] if labels else "emb_0"
                return {0: [(label, embeddings[0])]}
            return {}
        
        embeddings = np.asarray(embeddings, dtype=np.float32)
        
        # Compute pairwise distances
        pdistances = pdist(embeddings, metric='cosine')
        
        # Normalize cosine distance to [0, 2] -> [0, 1]
        pdistances = pdistances / 2.0
        
        # Perform hierarchical clustering
        Z = linkage(pdistances, method=method)
        
        # Cut the dendrogram at the threshold
        cluster_labels = fcluster(Z, threshold, criterion='distance')
        
        # Group embeddings by cluster
        clusters = {}
        for idx, (cluster_id, emb) in enumerate(zip(cluster_labels, embeddings)):
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            
            label = labels[idx] if labels else f"emb_{idx}"
            clusters[cluster_id].append((label, emb))
        
        logger.info(f"Clustered {len(embeddings)} embeddings into {len(clusters)} clusters")
        return clusters
    
    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        embeddings: List[np.ndarray],
        embedding_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find the k most similar embeddings to a query
        
        Args:
            query_embedding: Query embedding
            embeddings: List of candidate embeddings
            embedding_ids: List of IDs for embeddings
            top_k: Number of results to return
            
        Returns:
            List of (embedding_id, similarity) tuples, sorted by similarity (descending)
        """
        if not embeddings:
            return []
        
        similarities = []
        for i, emb in enumerate(embeddings):
            similarity = self.cosine_similarity(query_embedding, emb)
            emb_id = embedding_ids[i] if embedding_ids else f"emb_{i}"
            similarities.append((emb_id, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def find_most_dissimilar(
        self,
        query_embedding: np.ndarray,
        embeddings: List[np.ndarray],
        embedding_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find the k most dissimilar embeddings to a query
        
        Returns embeddings with LOWEST similarity scores (most different)
        
        Args:
            query_embedding: Query embedding
            embeddings: List of candidate embeddings
            embedding_ids: List of IDs for embeddings
            top_k: Number of results to return
            
        Returns:
            List of (embedding_id, similarity) tuples, sorted by similarity (ascending)
        """
        if not embeddings:
            return []
        
        similarities = []
        for i, emb in enumerate(embeddings):
            similarity = self.cosine_similarity(query_embedding, emb)
            emb_id = embedding_ids[i] if embedding_ids else f"emb_{i}"
            similarities.append((emb_id, similarity))
        
        # Sort by similarity (ascending) to get most dissimilar
        similarities.sort(key=lambda x: x[1])
        
        return similarities[:top_k]


# Convenience functions for direct use

def batch_cosine_similarity(
    embeddings1: Union[np.ndarray, List[np.ndarray]],
    embeddings2: Union[np.ndarray, List[np.ndarray]]
) -> np.ndarray:
    """
    Calculate pairwise cosine similarities between two sets of embeddings
    
    Args:
        embeddings1: Array of shape (n, d) or list of n embeddings
        embeddings2: Array of shape (m, d) or list of m embeddings
        
    Returns:
        Similarity matrix of shape (n, m), values in [0, 1]
    """
    embeddings1 = np.asarray(embeddings1, dtype=np.float32)
    embeddings2 = np.asarray(embeddings2, dtype=np.float32)
    
    if embeddings1.ndim == 1:
        embeddings1 = embeddings1.reshape(1, -1)
    if embeddings2.ndim == 1:
        embeddings2 = embeddings2.reshape(1, -1)
    
    # Compute cosine distances
    distances = cdist(embeddings1, embeddings2, metric='cosine')
    
    # Convert to similarities [0, 1]
    similarities = 1.0 - distances / 2.0
    
    return np.clip(similarities, 0.0, 1.0)


def compute_embedding_statistics(
    embeddings: np.ndarray,
    labels: Optional[List[str]] = None
) -> Dict:
    """
    Compute statistics for a set of embeddings
    
    Args:
        embeddings: Array of shape (n, embedding_dim)
        labels: Optional labels for each embedding
        
    Returns:
        Dictionary with statistical metrics
    """
    embeddings = np.asarray(embeddings, dtype=np.float32)
    
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    
    n_embeddings, embedding_dim = embeddings.shape
    
    # Compute mean and std
    mean_embedding = np.mean(embeddings, axis=0)
    std_embedding = np.std(embeddings, axis=0)
    
    # Compute pairwise similarities
    distances = pdist(embeddings, metric='cosine')
    
    if len(distances) > 0:
        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        min_distance = np.min(distances)
        max_distance = np.max(distances)
    else:
        mean_distance = std_distance = min_distance = max_distance = 0.0
    
    stats = {
        'n_embeddings': n_embeddings,
        'embedding_dim': embedding_dim,
        'mean_embedding': mean_embedding,
        'std_embedding': std_embedding,
        'mean_pairwise_distance': mean_distance,
        'std_pairwise_distance': std_distance,
        'min_pairwise_distance': min_distance,
        'max_pairwise_distance': max_distance,
    }
    
    logger.debug(f"Computed statistics for {n_embeddings} embeddings")
    return stats
