"""
High-level embedding service with caching, quality management, and batch support.
"""

import logging
import numpy as np
from typing import Callable, Dict, Optional, Tuple
from app.ml.embedding import generate_embedding, generate_embedding_with_chunking, get_embedding_with_auto_chunking
from app.ml.embedding_metrics import EmbeddingMetrics, EmbeddingComparison, EmbeddingStats
from app.ml.embedding_comparator import EmbeddingComparator
from app.ml.embedding_batch import EmbeddingBatchProcessor
from app.ml.embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)


class EmbeddingServiceConfig:
    """Configuration for embedding service"""
    
    def __init__(self,
                 generation_method: str = 'auto',
                 use_cache: bool = True,
                 cache_size: int = 100,
                 similarity_threshold: float = 0.75,
                 enable_quality_check: bool = True,
                 min_quality_score: float = 0.5):
        """
        Initialize configuration
        
        Args:
            generation_method: 'standard', 'chunked', or 'auto'
            use_cache: Whether to use embedding cache
            cache_size: Size of embedding cache
            similarity_threshold: Threshold for positive match
            enable_quality_check: Check embedding quality
            min_quality_score: Minimum acceptable quality score
        """
        self.generation_method = generation_method
        self.use_cache = use_cache
        self.cache_size = cache_size
        self.similarity_threshold = similarity_threshold
        self.enable_quality_check = enable_quality_check
        self.min_quality_score = min_quality_score
        
        logger.info(f"EmbeddingServiceConfig initialized: method={generation_method}, threshold={similarity_threshold}")


class EmbeddingService:
    """High-level embedding service with caching and quality management"""
    
    def __init__(self, config: Optional[EmbeddingServiceConfig] = None):
        """
        Initialize embedding service
        
        Args:
            config: EmbeddingServiceConfig (uses defaults if None)
        """
        self.config = config or EmbeddingServiceConfig()
        self.cache = EmbeddingCache(self.config.cache_size) if self.config.use_cache else None
        self.comparator = EmbeddingComparator()
        self.stats = EmbeddingStats()
        self.batch_processor = EmbeddingBatchProcessor()
        
        logger.info("EmbeddingService initialized")
    
    def generate(self, audio_bytes: bytes, phone_number: str) -> Tuple[np.ndarray, EmbeddingMetrics]:
        """
        Generate embedding with caching and quality checks
        
        Args:
            audio_bytes: Audio file bytes
            phone_number: Associated phone number
            
        Returns:
            Tuple of (embedding, metrics)
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(phone_number)
            if cached is not None:
                logger.debug(f"Retrieved cached embedding for {phone_number}")
                metrics = self.stats.calculate_metrics(
                    cached, phone_number, phone_number, "cached"
                )
                return cached, metrics
        
        # Generate embedding
        if self.config.generation_method == 'chunked':
            embedding = generate_embedding_with_chunking(audio_bytes)
            method = 'chunked'
        elif self.config.generation_method == 'auto':
            embedding = get_embedding_with_auto_chunking(audio_bytes)
            method = 'auto'
        else:
            embedding = generate_embedding(audio_bytes)
            method = 'standard'
        
        # Calculate metrics
        metrics = self.stats.calculate_metrics(
            embedding, phone_number, phone_number, method
        )
        
        # Check quality
        metrics.quality_score = self.stats.calculate_embedding_quality(embedding)
        
        if self.config.enable_quality_check:
            if metrics.quality_score < self.config.min_quality_score:
                logger.warning(
                    f"Low quality embedding for {phone_number}: {metrics.quality_score:.3f} "
                    f"< {self.config.min_quality_score}"
                )
        
        # Store in cache
        if self.cache:
            self.cache.put(phone_number, embedding)
        
        logger.info(f"Generated embedding for {phone_number} (quality={metrics.quality_score:.3f})")
        
        return embedding, metrics
    
    def compare(self,
                query_embedding: np.ndarray,
                stored_embedding: np.ndarray,
                query_phone: str,
                stored_phone: str) -> EmbeddingComparison:
        """
        Compare two embeddings
        
        Args:
            query_embedding: Query embedding
            stored_embedding: Stored embedding
            query_phone: Query phone number
            stored_phone: Stored phone number
            
        Returns:
            EmbeddingComparison result
        """
        return self.comparator.compare(
            query_embedding,
            stored_embedding,
            query_phone,
            stored_phone,
            self.config.similarity_threshold
        )
    
    def batch_generate(self,
                       audio_bytes_dict: Dict[str, bytes],
                       progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Tuple[np.ndarray, EmbeddingMetrics]]:
        """
        Generate embeddings for multiple audio files
        
        Args:
            audio_bytes_dict: Dict mapping identifier -> audio_bytes
            progress_callback: Optional progress callback
            
        Returns:
            Dict mapping identifier -> (embedding, metrics)
        """
        return self.batch_processor.process_batch(
            audio_bytes_dict,
            self.config.generation_method,
            progress_callback
        )
    
    def get_cache_stats(self) -> Optional[Dict[str, any]]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self) -> None:
        """Clear the embedding cache"""
        if self.cache:
            self.cache.clear()


# Global service instance
_service: Optional[EmbeddingService] = None


def get_embedding_service(config: Optional[EmbeddingServiceConfig] = None) -> EmbeddingService:
    """
    Get or create the global embedding service
    
    Args:
        config: Optional config for initialization
        
    Returns:
        EmbeddingService instance
    """
    global _service
    
    if _service is None:
        _service = EmbeddingService(config)
    
    return _service