"""
Batch processing of multiple audio files for embedding generation.
"""

import logging
from typing import Callable, Dict, Optional, Tuple
import numpy as np
from app.ml.embedding import generate_embedding, generate_embedding_with_chunking, get_embedding_with_auto_chunking
from app.ml.embedding_metrics import EmbeddingMetrics, EmbeddingStats

logger = logging.getLogger(__name__)


class EmbeddingBatchProcessor:
    """Process multiple audio files for batch embedding generation"""
    
    @staticmethod
    def process_batch(
        audio_bytes_dict: Dict[str, bytes],
        generation_method: str = 'auto',
        use_progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Tuple[np.ndarray, EmbeddingMetrics]]:
        """
        Process multiple audio files and generate embeddings
        
        Args:
            audio_bytes_dict: Dict mapping identifier -> audio_bytes
            generation_method: 'standard', 'chunked', or 'auto'
            use_progress_callback: Optional callback(current, total) for progress
            
        Returns:
            Dict mapping identifier -> (embedding, metrics)
        """
        results = {}
        total = len(audio_bytes_dict)
        
        logger.info(f"Starting batch processing of {total} audio files (method={generation_method})")
        
        for idx, (identifier, audio_bytes) in enumerate(audio_bytes_dict.items()):
            if use_progress_callback:
                use_progress_callback(idx, total)
            
            try:
                # Generate embedding based on method
                if generation_method == 'chunked':
                    embedding = generate_embedding_with_chunking(audio_bytes)
                elif generation_method == 'auto':
                    embedding = get_embedding_with_auto_chunking(audio_bytes)
                else:  # 'standard'
                    embedding = generate_embedding(audio_bytes)
                
                # Calculate metrics
                metrics = EmbeddingStats.calculate_metrics(
                    embedding=embedding,
                    embedding_id=identifier,
                    phone_number=identifier,
                    generation_method=generation_method
                )
                
                # Calculate quality
                metrics.quality_score = EmbeddingStats.calculate_embedding_quality(embedding)
                
                results[identifier] = (embedding, metrics)
                logger.info(f"✓ Processed {identifier}: quality_score={metrics.quality_score:.3f}")
                
            except Exception as e:
                logger.error(f"✗ Failed to process {identifier}: {e}")
                results[identifier] = (None, None)
        
        if use_progress_callback:
            use_progress_callback(total, total)
        
        logger.info(f"Batch processing complete: {len([r for r in results.values() if r[0] is not None])}/{total} successful")
        
        return results