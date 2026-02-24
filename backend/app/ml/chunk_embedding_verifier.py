"""
Chunk Embedding Verifier Module
Handles advanced verification using chunk-level embedding comparison
Provides granular analysis of audio segments for robust voice verification
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from app.ml.embedding import generate_embedding_with_chunking, calculate_cosine_similarity
from app.ml.chunking import AudioChunker, ChunkConfig
from embedding_similarity_operations import EmbeddingSimilarityCalculator, SimilarityResult

logger = logging.getLogger(__name__)


class ChunkMatchStatus(Enum):
    """Status of chunk matching"""
    MATCH = "match"
    PARTIAL_MATCH = "partial_match"
    MISMATCH = "mismatch"
    LOW_CONFIDENCE = "low_confidence"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class ChunkEmbedding:
    """Represents embedding for a single audio chunk"""
    chunk_id: str
    chunk_index: int
    embedding: np.ndarray  # Shape: (embedding_dim,)
    start_time_ms: float
    end_time_ms: float
    duration_ms: float
    chunk_data: Optional[np.ndarray] = None  # Optional raw chunk data
    confidence: float = 1.0  # Confidence in the embedding quality
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "start_time_ms": self.start_time_ms,
            "end_time_ms": self.end_time_ms,
            "duration_ms": self.duration_ms,
            "confidence": float(self.confidence),
            "embedding_dim": len(self.embedding),
            "metadata": self.metadata
        }


@dataclass
class ChunkComparisonResult:
    """Result of comparing two chunks"""
    reference_chunk_id: str
    verification_chunk_id: str
    reference_chunk_index: int
    verification_chunk_index: int
    cosine_similarity: float
    euclidean_distance: float
    correlation_distance: float
    is_match: bool
    confidence: float
    status: ChunkMatchStatus
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "reference_chunk_id": self.reference_chunk_id,
            "verification_chunk_id": self.verification_chunk_id,
            "reference_chunk_index": self.reference_chunk_index,
            "verification_chunk_index": self.verification_chunk_index,
            "cosine_similarity": float(self.cosine_similarity),
            "euclidean_distance": float(self.euclidean_distance),
            "correlation_distance": float(self.correlation_distance),
            "is_match": self.is_match,
            "confidence": float(self.confidence),
            "status": self.status.value,
            "details": self.details
        }


@dataclass
class ChunkVerificationResult:
    """Complete result of chunk-based verification"""
    verification_id: str
    timestamp: datetime
    total_reference_chunks: int
    total_verification_chunks: int
    matched_chunks: int
    partial_matched_chunks: int
    unmatched_chunks: int
    average_chunk_similarity: float
    overall_confidence: float
    verification_status: ChunkMatchStatus
    chunk_comparisons: List[ChunkComparisonResult] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "verification_id": self.verification_id,
            "timestamp": self.timestamp.isoformat(),
            "total_reference_chunks": self.total_reference_chunks,
            "total_verification_chunks": self.total_verification_chunks,
            "matched_chunks": self.matched_chunks,
            "partial_matched_chunks": self.partial_matched_chunks,
            "unmatched_chunks": self.unmatched_chunks,
            "average_chunk_similarity": float(self.average_chunk_similarity),
            "overall_confidence": float(self.overall_confidence),
            "verification_status": self.verification_status.value,
            "chunk_count": len(self.chunk_comparisons),
            "statistics": self.statistics
        }


class ChunkEmbeddingVerifier:
    """
    Advanced verification using chunk-level embedding comparison
    
    Features:
    - Generate embeddings for individual audio chunks
    - Compare chunk embeddings with advanced metrics
    - Statistical analysis of chunk similarities
    - Confidence scoring based on multiple chunks
    - Flexible matching strategies
    """
    
    def __init__(
        self,
        chunk_config: Optional[ChunkConfig] = None,
        similarity_threshold: float = 0.75,
        confidence_threshold: float = 0.70,
        metric: str = 'cosine'
    ):
        """
        Initialize chunk embedding verifier
        
        Args:
            chunk_config: Audio chunking configuration
            similarity_threshold: Minimum similarity for chunk match
            confidence_threshold: Minimum confidence for verification decision
            metric: Distance metric for similarity calculations
        """
        self.chunk_config = chunk_config or ChunkConfig()
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.metric = metric
        self.chunker = AudioChunker(self.chunk_config)
        self.similarity_calculator = EmbeddingSimilarityCalculator(metric=metric)
        
        logger.info(
            f"Initialized ChunkEmbeddingVerifier: threshold={similarity_threshold}, "
            f"confidence={confidence_threshold}, metric={metric}"
        )
    
    def generate_chunk_embeddings(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        store_chunk_data: bool = False
    ) -> List[ChunkEmbedding]:
        """
        Generate embeddings for audio chunks
        
        Args:
            audio_data: Audio waveform
            sample_rate: Sample rate of audio
            store_chunk_data: Whether to store raw chunk data (for analysis)
            
        Returns:
            List of ChunkEmbedding objects
            
        Raises:
            ValueError: If audio_data is invalid
        """
        if audio_data is None or len(audio_data) == 0:
            raise ValueError("Invalid audio_data")
        
        logger.info(f"Generating chunk embeddings for audio ({len(audio_data)} samples, {sample_rate}Hz)")
        
        # Chunk the audio
        chunks, chunk_info = self.chunker.chunk_audio(audio_data)
        
        if not chunks:
            raise ValueError("No valid chunks generated from audio")
        
        chunk_embeddings = []
        
        for i, (chunk_data, info) in enumerate(zip(chunks, chunk_info)):
            try:
                # Generate embedding for chunk
                embedding = generate_embedding(chunk_data, sample_rate)
                
                if embedding is None:
                    logger.warning(f"Failed to generate embedding for chunk {i}, skipping")
                    continue
                
                # Create ChunkEmbedding
                chunk_emb = ChunkEmbedding(
                    chunk_id=str(uuid.uuid4()),
                    chunk_index=i,
                    embedding=embedding,
                    start_time_ms=info['start_time_ms'],
                    end_time_ms=info['end_time_ms'],
                    duration_ms=info['duration_ms'],
                    chunk_data=chunk_data if store_chunk_data else None,
                    confidence=1.0,
                    metadata={
                        'sample_rate': sample_rate,
                        'num_samples': len(chunk_data),
                        'generated_at': datetime.utcnow().isoformat()
                    }
                )
                
                chunk_embeddings.append(chunk_emb)
                logger.debug(f"Generated embedding for chunk {i}: {info}")
                
            except Exception as e:
                logger.warning(f"Error generating embedding for chunk {i}: {e}")
                continue
        
        if not chunk_embeddings:
            raise ValueError("Failed to generate embeddings for any chunks")
        
        logger.info(f"Generated {len(chunk_embeddings)} chunk embeddings from {len(chunks)} chunks")
        return chunk_embeddings
    
    def compare_chunk_embeddings(
        self,
        reference_chunk: ChunkEmbedding,
        verification_chunk: ChunkEmbedding,
        use_dynamic_threshold: bool = False
    ) -> ChunkComparisonResult:
        """
        Compare two chunk embeddings
        
        Args:
            reference_chunk: Reference ChunkEmbedding (from enrollment)
            verification_chunk: Verification ChunkEmbedding (from user attempt)
            use_dynamic_threshold: Adjust threshold based on chunk quality
            
        Returns:
            ChunkComparisonResult
        """
        # Determine threshold
        threshold = self.similarity_threshold
        if use_dynamic_threshold:
            # Adjust threshold based on chunk confidence
            avg_confidence = (reference_chunk.confidence + verification_chunk.confidence) / 2
            threshold = threshold * avg_confidence
        
        # Compare using similarity calculator
        similarity_result = self.similarity_calculator.compare(
            reference_chunk.embedding,
            verification_chunk.embedding,
            emb1_id=reference_chunk.chunk_id,
            emb2_id=verification_chunk.chunk_id,
            threshold=threshold
        )
        
        # Determine match status
        if similarity_result.cosine_similarity >= threshold:
            status = ChunkMatchStatus.MATCH
        elif similarity_result.cosine_similarity >= (threshold - 0.1):
            status = ChunkMatchStatus.PARTIAL_MATCH
        else:
            status = ChunkMatchStatus.MISMATCH
        
        # Calculate confidence
        confidence = max(0.0, (similarity_result.cosine_similarity - threshold) / (1.0 - threshold))
        confidence = min(1.0, confidence)
        
        # Create result
        result = ChunkComparisonResult(
            reference_chunk_id=reference_chunk.chunk_id,
            verification_chunk_id=verification_chunk.chunk_id,
            reference_chunk_index=reference_chunk.chunk_index,
            verification_chunk_index=verification_chunk.chunk_index,
            cosine_similarity=similarity_result.cosine_similarity,
            euclidean_distance=similarity_result.euclidean_distance,
            correlation_distance=similarity_result.correlation_distance or 0.0,
            is_match=similarity_result.is_match,
            confidence=confidence,
            status=status,
            details={
                'threshold_used': threshold,
                'reference_duration_ms': reference_chunk.duration_ms,
                'verification_duration_ms': verification_chunk.duration_ms,
                'reference_confidence': reference_chunk.confidence,
                'verification_confidence': verification_chunk.confidence
            }
        )
        
        logger.debug(
            f"Chunk comparison: idx {reference_chunk.chunk_index} vs {verification_chunk.chunk_index}, "
            f"similarity={result.cosine_similarity:.4f}, status={status.value}"
        )
        
        return result
    
    def match_chunks(
        self,
        reference_chunks: List[ChunkEmbedding],
        verification_chunks: List[ChunkEmbedding],
        matching_strategy: str = 'best_match'
    ) -> List[ChunkComparisonResult]:
        """
        Match and compare reference chunks with verification chunks
        
        Matching strategies:
        - 'best_match': Each reference chunk matched to best verification chunk (default)
        - 'strict_order': Match chunks by index order
        - 'all_pairs': Compare all pairs (expensive)
        
        Args:
            reference_chunks: List of reference ChunkEmbedding objects
            verification_chunks: List of verification ChunkEmbedding objects
            matching_strategy: Strategy for matching chunks
            
        Returns:
            List of ChunkComparisonResult objects
        """
        if not reference_chunks or not verification_chunks:
            raise ValueError("Both reference and verification chunks are required")
        
        logger.info(
            f"Matching chunks: {len(reference_chunks)} reference vs {len(verification_chunks)} verification "
            f"(strategy={matching_strategy})"
        )
        
        results = []
        
        if matching_strategy == 'best_match':
            # Match each reference chunk to its best match in verification chunks
            for ref_chunk in reference_chunks:
                best_result = None
                best_similarity = -1.0
                
                for verif_chunk in verification_chunks:
                    result = self.compare_chunk_embeddings(ref_chunk, verif_chunk)
                    if result.cosine_similarity > best_similarity:
                        best_similarity = result.cosine_similarity
                        best_result = result
                
                if best_result:
                    results.append(best_result)
        
        elif matching_strategy == 'strict_order':
            # Match chunks by index order (one-to-one if same length)
            min_chunks = min(len(reference_chunks), len(verification_chunks))
            for i in range(min_chunks):
                result = self.compare_chunk_embeddings(
                    reference_chunks[i],
                    verification_chunks[i]
                )
                results.append(result)
        
        elif matching_strategy == 'all_pairs':
            # Compare all pairs (expensive but comprehensive)
            for ref_chunk in reference_chunks:
                for verif_chunk in verification_chunks:
                    result = self.compare_chunk_embeddings(ref_chunk, verif_chunk)
                    results.append(result)
        
        else:
            raise ValueError(f"Unknown matching_strategy: {matching_strategy}")
        
        logger.info(f"Generated {len(results)} chunk comparison results")
        return results
    
    def verify_with_chunks(
        self,
        reference_chunks: List[ChunkEmbedding],
        verification_chunks: List[ChunkEmbedding],
        matching_strategy: str = 'best_match',
        use_dynamic_threshold: bool = False
    ) -> ChunkVerificationResult:
        """
        Perform comprehensive chunk-based verification
        
        Args:
            reference_chunks: List of reference ChunkEmbedding objects
            verification_chunks: List of verification ChunkEmbedding objects
            matching_strategy: Strategy for matching chunks
            use_dynamic_threshold: Use dynamic threshold based on chunk quality
            
        Returns:
            ChunkVerificationResult with detailed analysis
        """
        logger.info(f"Starting chunk-based verification")
        
        # Temporarily override dynamic threshold if specified
        original_threshold = self.similarity_threshold
        if use_dynamic_threshold:
            self.similarity_threshold = original_threshold  # Will be adjusted per comparison
        
        try:
            # Match chunks
            chunk_comparisons = self.match_chunks(
                reference_chunks,
                verification_chunks,
                matching_strategy
            )
            
            if not chunk_comparisons:
                raise ValueError("No chunk comparisons generated")
            
            # Calculate statistics
            similarities = [c.cosine_similarity for c in chunk_comparisons]
            matched = sum(1 for c in chunk_comparisons if c.status == ChunkMatchStatus.MATCH)
            partial_matched = sum(1 for c in chunk_comparisons if c.status == ChunkMatchStatus.PARTIAL_MATCH)
            unmatched = sum(1 for c in chunk_comparisons if c.status == ChunkMatchStatus.MISMATCH)
            
            avg_similarity = float(np.mean(similarities))
            max_similarity = float(np.max(similarities))
            min_similarity = float(np.min(similarities))
            
            # Calculate overall confidence
            match_rate = (matched + partial_matched * 0.5) / len(chunk_comparisons)
            overall_confidence = match_rate * np.mean([c.confidence for c in chunk_comparisons])
            
            # Determine verification status
            if match_rate >= 0.8 and overall_confidence >= self.confidence_threshold:
                verification_status = ChunkMatchStatus.MATCH
            elif match_rate >= 0.5:
                verification_status = ChunkMatchStatus.PARTIAL_MATCH
            elif overall_confidence < 0.3:
                verification_status = ChunkMatchStatus.LOW_CONFIDENCE
            else:
                verification_status = ChunkMatchStatus.MISMATCH
            
            # Create result
            result = ChunkVerificationResult(
                verification_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                total_reference_chunks=len(reference_chunks),
                total_verification_chunks=len(verification_chunks),
                matched_chunks=matched,
                partial_matched_chunks=partial_matched,
                unmatched_chunks=unmatched,
                average_chunk_similarity=avg_similarity,
                overall_confidence=float(overall_confidence),
                verification_status=verification_status,
                chunk_comparisons=chunk_comparisons,
                statistics={
                    'max_similarity': float(max_similarity),
                    'min_similarity': float(min_similarity),
                    'std_dev': float(np.std(similarities)),
                    'match_rate': float(match_rate),
                    'total_comparisons': len(chunk_comparisons),
                    'matching_strategy': matching_strategy,
                    'threshold_used': self.similarity_threshold,
                    'confidence_threshold': self.confidence_threshold
                }
            )
            
            logger.info(
                f"Chunk verification complete: matched={matched}/{len(chunk_comparisons)}, "
                f"avg_similarity={avg_similarity:.4f}, confidence={overall_confidence:.4f}, "
                f"status={verification_status.value}"
            )
            
            return result
        
        finally:
            self.similarity_threshold = original_threshold
    
    def analyze_chunk_variance(
        self,
        chunk_embeddings: List[ChunkEmbedding]
    ) -> Dict[str, Any]:
        """
        Analyze variance and quality of chunk embeddings
        
        Args:
            chunk_embeddings: List of ChunkEmbedding objects
            
        Returns:
            Dictionary with variance analysis
        """
        if not chunk_embeddings or len(chunk_embeddings) < 2:
            return {
                'insufficient_data': True,
                'min_chunks_required': 2
            }
        
        embeddings_array = np.array([c.embedding for c in chunk_embeddings])
        
        # Compute pairwise similarity
        n_chunks = len(chunk_embeddings)
        similarities = []
        
        for i in range(n_chunks):
            for j in range(i + 1, n_chunks):
                sim = calculate_cosine_similarity(
                    chunk_embeddings[i].embedding,
                    chunk_embeddings[j].embedding
                )
                similarities.append(sim)
        
        if not similarities:
            return {'error': 'Could not compute similarities'}
        
        analysis = {
            'num_chunks': n_chunks,
            'num_comparisons': len(similarities),
            'mean_chunk_similarity': float(np.mean(similarities)),
            'std_chunk_similarity': float(np.std(similarities)),
            'min_chunk_similarity': float(np.min(similarities)),
            'max_chunk_similarity': float(np.max(similarities)),
            'variance': float(np.var(similarities)),
            'homogeneity': float(1.0 - np.std(similarities)),  # Higher = more similar chunks
            'embedding_mean': embeddings_array.mean(axis=0).tolist()[:10],  # First 10 values
            'embedding_std': embeddings_array.std(axis=0).tolist()[:10]
        }
        
        logger.debug(f"Chunk variance analysis: homogeneity={analysis['homogeneity']:.4f}")
        return analysis


# Convenience function for chunk embedding generation
def generate_embedding(audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """Generate embedding (local wrapper for import convenience)"""
    from app.ml.embedding import generate_embedding as gen_emb
    return gen_emb(audio_data, sample_rate)
