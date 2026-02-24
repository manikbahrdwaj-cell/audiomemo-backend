"""
In-memory LRU-style cache for voice embeddings.
"""

import logging
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Simple cache for frequent embeddings"""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize embedding cache
        
        Args:
            max_size: Maximum number of embeddings to cache
        """
        self.cache: Dict[str, Tuple[np.ndarray, datetime]] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        logger.info(f"Initialized EmbeddingCache with max_size={max_size}")
    
    def get(self, key: str) -> Optional[np.ndarray]:
        """
        Get embedding from cache
        
        Args:
            key: Cache key (usually phone_number)
            
        Returns:
            Cached embedding or None if not found
        """
        if key in self.cache:
            embedding, timestamp = self.cache[key]
            self.hits += 1
            return embedding
        
        self.misses += 1
        return None
    
    def put(self, key: str, embedding: np.ndarray) -> None:
        """
        Store embedding in cache
        
        Args:
            key: Cache key
            embedding: Embedding vector
        """
        # Remove oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            logger.debug(f"Evicted oldest cache entry: {oldest_key}")
        
        self.cache[key] = (embedding, datetime.utcnow())
    
    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        logger.info("Cleared embedding cache")
    
    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        total_accesses = self.hits + self.misses
        hit_rate = self.hits / total_accesses if total_accesses > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }