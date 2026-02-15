"""
Comprehensive Embedding Operations Module
Provides advanced embedding management, batch processing, and quality metrics using SpeechBrain ECAPA-TDNN
Includes audio merging, chunking, and advanced audio processing
"""

import numpy as np
import torch
import logging
from typing import Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from enum import Enum
from io import BytesIO
from scipy.spatial.distance import cdist, cosine, pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from scipy import spatial

from voice_embedding import (
    generate_embedding,
    generate_embedding_with_chunking,
    get_embedding_with_auto_chunking,
    calculate_cosine_similarity,
    get_model,
    preprocess_audio
)

logger = logging.getLogger(__name__)


class MergeMode(Enum):
    """Audio merging modes"""
    CONCATENATE = "concatenate"  # Direct concatenation
    OVERLAP = "overlap"  # With overlapping regions
    CROSSFADE = "crossfade"  # Smooth crossfading between segments
    MIX = "mix"  # Mix audio (weighted sum)


@dataclass
class AudioMergeConfig:
    """Configuration for audio merging operations"""
    mode: MergeMode = MergeMode.CONCATENATE
    sample_rate: int = 16000
    crossfade_duration_ms: float = 100.0  # Duration of crossfade in milliseconds
    overlap_duration_ms: float = 100.0  # Duration of overlap in milliseconds
    crossfade_shape: str = "linear"  # "linear", "exponential", "logarithmic"
    normalize_segments: bool = True  # Normalize each segment before merging
    silence_between_ms: float = 0.0  # Add silence between segments
    pad_missing_sample_rate: bool = True  # Try to resample if needed
    
    def __post_init__(self):
        """Validate configuration"""
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.crossfade_duration_ms < 0:
            raise ValueError("crossfade_duration_ms must be non-negative")
        if self.overlap_duration_ms < 0:
            raise ValueError("overlap_duration_ms must be non-negative")
        if self.crossfade_shape not in ["linear", "exponential", "logarithmic"]:
            raise ValueError(f"Unknown crossfade_shape: {self.crossfade_shape}")
        if self.silence_between_ms < 0:
            raise ValueError("silence_between_ms must be non-negative")


class AudioMerger:
    """
    Advanced audio merging and concatenation with multiple strategies
    
    Features:
    - Multiple merge modes (concatenate, overlap, crossfade, mix)
    - Sample rate handling and resampling
    - Crossfading with different shapes
    - Silence insertion
    - Normalization
    - Quality preservation
    """
    
    def __init__(self, config: Optional[AudioMergeConfig] = None):
        """
        Initialize AudioMerger
        
        Args:
            config: AudioMergeConfig object with merge parameters
        """
        self.config = config or AudioMergeConfig()
        logger.info(f"Initialized AudioMerger with mode={self.config.mode.value}")
    
    @staticmethod
    def _get_sample_rate_from_bytes(audio_bytes: bytes) -> Optional[int]:
        """
        Extract sample rate from audio bytes
        
        Args:
            audio_bytes: Audio file bytes
            
        Returns:
            Sample rate in Hz or None if unable to determine
        """
        try:
            audio_tensor, sample_rate = preprocess_audio(audio_bytes)
            return sample_rate
        except Exception as e:
            logger.warning(f"Could not determine sample rate from audio bytes: {e}")
            return None
    
    @staticmethod
    def _resample_audio(
        audio: np.ndarray,
        orig_sample_rate: int,
        target_sample_rate: int
    ) -> np.ndarray:
        """
        Resample audio to target sample rate
        
        Args:
            audio: Audio waveform
            orig_sample_rate: Original sample rate
            target_sample_rate: Target sample rate
            
        Returns:
            Resampled audio
        """
        if orig_sample_rate == target_sample_rate:
            return audio
        
        # Calculate resampling ratio
        ratio = target_sample_rate / orig_sample_rate
        new_length = int(len(audio) * ratio)
        
        # Simple linear interpolation for resampling
        old_indices = np.arange(len(audio))
        new_indices = np.linspace(0, len(audio) - 1, new_length)
        resampled = np.interp(new_indices, old_indices, audio)
        
        logger.debug(
            f"Resampled audio from {orig_sample_rate}Hz to {target_sample_rate}Hz "
            f"({len(audio)} -> {len(resampled)} samples)"
        )
        
        return resampled
    
    @staticmethod
    def _create_crossfade_envelope(
        length: int,
        shape: str = "linear"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create crossfade envelopes (fade out, fade in)
        
        Args:
            length: Length of fade in samples
            shape: Fade shape ('linear', 'exponential', 'logarithmic')
            
        Returns:
            Tuple of (fade_out, fade_in) arrays
        """
        if shape == "linear":
            fade_out = np.linspace(1.0, 0.0, length)
            fade_in = np.linspace(0.0, 1.0, length)
        
        elif shape == "exponential":
            # Exponential curve (e^(-x) style)
            x = np.linspace(0, 5, length)
            fade_out = np.exp(-x) * np.exp(-0)  # Normalize
            fade_in = 1.0 - fade_out
        
        elif shape == "logarithmic":
            # Logarithmic curve
            fade_out = np.log(np.linspace(np.e, 1, length))
            fade_in = 1.0 - fade_out
        
        else:
            logger.warning(f"Unknown shape '{shape}', using linear")
            fade_out = np.linspace(1.0, 0.0, length)
            fade_in = np.linspace(0.0, 1.0, length)
        
        # Normalize to [0, 1]
        fade_out = np.clip(fade_out, 0, 1)
        fade_in = np.clip(fade_in, 0, 1)
        
        return fade_out, fade_in
    
    def merge_audio_segments(
        self,
        audio_segments: List[Union[np.ndarray, bytes]],
        sample_rates: Optional[List[int]] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Merge multiple audio segments according to configured mode
        
        Args:
            audio_segments: List of audio arrays or bytes
            sample_rates: List of sample rates (auto-detected if None)
            
        Returns:
            Tuple of (merged_audio, sample_rate)
            
        Raises:
            ValueError: If segments list is empty or invalid
        """
        if not audio_segments:
            raise ValueError("audio_segments cannot be empty")
        
        if len(audio_segments) == 1:
            if isinstance(audio_segments[0], bytes):
                audio, sr = preprocess_audio(audio_segments[0])
                return audio.numpy(), sr
            return audio_segments[0], self.config.sample_rate
        
        logger.info(
            f"Merging {len(audio_segments)} audio segments "
            f"(mode={self.config.mode.value}, sample_rate={self.config.sample_rate})"
        )
        
        # Convert all segments to numpy arrays and handle sample rates
        audio_arrays = []
        segment_sample_rates = []
        
        for idx, segment in enumerate(audio_segments):
            if isinstance(segment, bytes):
                audio_tensor, sr = preprocess_audio(segment)
                audio = audio_tensor.numpy()
                segment_sr = sr
            else:
                audio = segment
                segment_sr = sample_rates[idx] if sample_rates else self.config.sample_rate
            
            # Resample if needed
            if segment_sr != self.config.sample_rate:
                if self.config.pad_missing_sample_rate:
                    audio = self._resample_audio(audio, segment_sr, self.config.sample_rate)
                    segment_sr = self.config.sample_rate
                else:
                    logger.warning(
                        f"Segment {idx} has sample rate {segment_sr}, "
                        f"expected {self.config.sample_rate}"
                    )
            
            # Normalize segment if configured
            if self.config.normalize_segments:
                max_val = np.max(np.abs(audio))
                if max_val > 0:
                    audio = audio / max_val
            
            audio_arrays.append(audio)
            segment_sample_rates.append(segment_sr)
        
        # Merge based on mode
        if self.config.mode == MergeMode.CONCATENATE:
            merged = self._concatenate(audio_arrays)
        
        elif self.config.mode == MergeMode.OVERLAP:
            merged = self._merge_with_overlap(audio_arrays)
        
        elif self.config.mode == MergeMode.CROSSFADE:
            merged = self._merge_with_crossfade(audio_arrays)
        
        elif self.config.mode == MergeMode.MIX:
            merged = self._merge_with_mix(audio_arrays)
        
        else:
            raise ValueError(f"Unknown merge mode: {self.config.mode}")
        
        # Normalize final output
        max_val = np.max(np.abs(merged))
        if max_val > 1.0:
            merged = merged / (max_val * 1.05)  # 5% safety margin
        
        logger.info(
            f"✓ Merged {len(audio_arrays)} segments into {len(merged)} samples "
            f"(duration: {len(merged) / self.config.sample_rate:.2f}s)"
        )
        
        return merged, self.config.sample_rate
    
    def _concatenate(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Simple concatenation of audio segments
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Concatenated audio
        """
        parts = []
        
        for idx, audio in enumerate(audio_arrays):
            parts.append(audio)
            
            # Add silence between segments if configured
            if self.config.silence_between_ms > 0 and idx < len(audio_arrays) - 1:
                silence_samples = int(
                    self.config.silence_between_ms * self.config.sample_rate / 1000
                )
                silence = np.zeros(silence_samples)
                parts.append(silence)
        
        merged = np.concatenate(parts)
        logger.debug(f"Concatenated {len(audio_arrays)} segments")
        
        return merged
    
    def _merge_with_overlap(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Merge audio segments with overlap (simple averaging in overlap region)
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Merged audio with overlapping regions
        """
        overlap_samples = int(
            self.config.overlap_duration_ms * self.config.sample_rate / 1000
        )
        
        if overlap_samples == 0:
            return self._concatenate(audio_arrays)
        
        # Calculate output length
        output_length = len(audio_arrays[0])
        for audio in audio_arrays[1:]:
            output_length += len(audio) - overlap_samples
        
        merged = np.zeros(output_length)
        position = 0
        
        for idx, audio in enumerate(audio_arrays):
            if idx == 0:
                # First segment - copy as is
                merged[position:position + len(audio)] = audio
                position += len(audio)
            else:
                # Overlapping regions - average
                overlap_start = position - overlap_samples
                
                # Average in overlap region
                for i in range(overlap_samples):
                    if overlap_start + i < len(merged):
                        merged[overlap_start + i] = (
                            merged[overlap_start + i] + audio[i]
                        ) / 2.0
                
                # Copy rest of segment
                remaining = len(audio) - overlap_samples
                if remaining > 0:
                    start_pos = overlap_start + overlap_samples
                    merged[start_pos:start_pos + remaining] = audio[overlap_samples:]
                    position = start_pos + remaining
        
        logger.debug(f"Merged {len(audio_arrays)} segments with {overlap_samples} sample overlap")
        
        return merged
    
    def _merge_with_crossfade(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Merge audio segments with smooth crossfading
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Merged audio with crossfades between segments
        """
        crossfade_samples = int(
            self.config.crossfade_duration_ms * self.config.sample_rate / 1000
        )
        
        if crossfade_samples == 0:
            return self._concatenate(audio_arrays)
        
        # Build output
        parts = []
        
        for idx, audio in enumerate(audio_arrays):
            if idx == 0:
                # First segment - include full segment
                parts.append(audio)
            else:
                # Get previous segment
                prev_audio = audio_arrays[idx - 1]
                
                # Get crossfade envelopes
                fade_out, fade_in = self._create_crossfade_envelope(
                    crossfade_samples,
                    self.config.crossfade_shape
                )
                
                # Extract regions to crossfade
                prev_end_start = max(0, len(prev_audio) - crossfade_samples)
                prev_fade_region = prev_audio[prev_end_start:]
                
                # Pad if needed
                if len(prev_fade_region) < crossfade_samples:
                    prev_fade_region = np.pad(
                        prev_fade_region,
                        (crossfade_samples - len(prev_fade_region), 0),
                        mode='edge'
                    )
                
                curr_fade_region = audio[:min(len(audio), crossfade_samples)]
                
                # Pad if needed
                if len(curr_fade_region) < crossfade_samples:
                    curr_fade_region = np.pad(
                        curr_fade_region,
                        (0, crossfade_samples - len(curr_fade_region)),
                        mode='edge'
                    )
                
                # Apply crossfade
                crossfaded = (
                    prev_fade_region[:crossfade_samples] * fade_out +
                    curr_fade_region[:crossfade_samples] * fade_in
                )
                
                # Remove the fade region from previous segment
                prev_without_fade = prev_audio[:prev_end_start]
                if len(prev_without_fade) > 0:
                    parts[-1] = prev_without_fade
                
                # Add crossfaded region
                parts.append(crossfaded)
                
                # Add remainder of current segment
                if len(audio) > crossfade_samples:
                    parts.append(audio[crossfade_samples:])
        
        merged = np.concatenate(parts)
        logger.debug(
            f"Merged {len(audio_arrays)} segments with {crossfade_samples} sample crossfade "
            f"({self.config.crossfade_shape})"
        )
        
        return merged
    
    def _merge_with_mix(self, audio_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Merge audio segments by mixing (weighted sum)
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Mixed audio
        """
        # Use maximum length for output
        max_length = max(len(audio) for audio in audio_arrays)
        mixed = np.zeros(max_length)
        
        # Equal weighting for all segments
        weight = 1.0 / len(audio_arrays)
        
        for audio in audio_arrays:
            # Pad audio to max length if needed
            if len(audio) < max_length:
                audio = np.pad(audio, (0, max_length - len(audio)), mode='constant')
            
            mixed += audio * weight
        
        logger.debug(f"Mixed {len(audio_arrays)} segments with equal weight ({weight:.3f})")
        
        return mixed
    
    def merge_from_files(
        self,
        file_paths: List[str]
    ) -> Tuple[np.ndarray, int]:
        """
        Merge audio from multiple files
        
        Args:
            file_paths: List of paths to audio files
            
        Returns:
            Tuple of (merged_audio, sample_rate)
        """
        audio_segments = []
        
        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    audio_bytes = f.read()
                audio_segments.append(audio_bytes)
                logger.debug(f"Loaded audio from {file_path}")
            except Exception as e:
                logger.error(f"Failed to load audio from {file_path}: {e}")
                raise
        
        return self.merge_audio_segments(audio_segments)
    
    def save_merged_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        output_path: str,
        format: str = "wav"
    ) -> None:
        """
        Save merged audio to file
        
        Args:
            audio: Audio waveform
            sample_rate: Sample rate
            output_path: Path to save file
            format: Audio format ('wav', 'mp3', 'flac')
        """
        try:
            import torchaudio
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float()
            if audio_tensor.ndim == 1:
                audio_tensor = audio_tensor.unsqueeze(0)
            
            # Save
            torchaudio.save(output_path, audio_tensor, sample_rate)
            logger.info(f"✓ Saved merged audio to {output_path} ({format})")
            
        except Exception as e:
            logger.error(f"Failed to save audio to {output_path}: {e}")
            raise
    
    def get_merge_stats(self, audio_arrays: List[np.ndarray]) -> Dict[str, any]:
        """
        Get statistics about audio segments before merging
        
        Args:
            audio_arrays: List of audio arrays
            
        Returns:
            Dictionary with statistics
        """
        total_samples = sum(len(audio) for audio in audio_arrays)
        duration_s = total_samples / self.config.sample_rate
        
        return {
            "num_segments": len(audio_arrays),
            "total_samples": total_samples,
            "duration_seconds": duration_s,
            "sample_rate": self.config.sample_rate,
            "merge_mode": self.config.mode.value,
            "segment_lengths": [len(audio) for audio in audio_arrays],
            "segment_durations_s": [len(audio) / self.config.sample_rate for audio in audio_arrays]
        }



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

# ============================================================================
# Audio Merging Convenience Functions
# ============================================================================

def merge_audio(
    audio_segments: List[Union[np.ndarray, bytes]],
    mode: str = "concatenate",
    sample_rate: int = 16000,
    crossfade_ms: float = 100.0
) -> Tuple[np.ndarray, int]:
    """
    Convenience function to merge multiple audio segments
    
    Args:
        audio_segments: List of audio arrays or bytes
        mode: Merge mode ('concatenate', 'overlap', 'crossfade', 'mix')
        sample_rate: Sample rate in Hz
        crossfade_ms: Crossfade duration in milliseconds (for crossfade mode)
        
    Returns:
        Tuple of (merged_audio, sample_rate)
        
    Example:
        >>> audio1 = np.random.randn(16000)
        >>> audio2 = np.random.randn(16000)
        >>> merged, sr = merge_audio([audio1, audio2], mode='crossfade')
        >>> print(f"Merged audio duration: {len(merged) / sr:.2f}s")
    """
    try:
        merge_mode = MergeMode(mode)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: "
            f"{', '.join([m.value for m in MergeMode])}"
        )
    
    config = AudioMergeConfig(
        mode=merge_mode,
        sample_rate=sample_rate,
        crossfade_duration_ms=crossfade_ms
    )
    
    merger = AudioMerger(config)
    return merger.merge_audio_segments(audio_segments)


def merge_audio_files(
    file_paths: List[str],
    mode: str = "concatenate",
    sample_rate: int = 16000,
    crossfade_ms: float = 100.0,
    output_path: Optional[str] = None
) -> Tuple[np.ndarray, int]:
    """
    Merge audio from multiple files
    
    Args:
        file_paths: List of paths to audio files
        mode: Merge mode ('concatenate', 'overlap', 'crossfade', 'mix')
        sample_rate: Target sample rate
        crossfade_ms: Crossfade duration in milliseconds
        output_path: Optional path to save merged audio
        
    Returns:
        Tuple of (merged_audio, sample_rate)
        
    Example:
        >>> merged, sr = merge_audio_files(
        ...     ['audio1.wav', 'audio2.wav'],
        ...     mode='crossfade',
        ...     output_path='merged.wav'
        ... )
    """
    try:
        merge_mode = MergeMode(mode)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: "
            f"{', '.join([m.value for m in MergeMode])}"
        )
    
    config = AudioMergeConfig(
        mode=merge_mode,
        sample_rate=sample_rate,
        crossfade_duration_ms=crossfade_ms
    )
    
    merger = AudioMerger(config)
    merged_audio, sr = merger.merge_from_files(file_paths)
    
    if output_path:
        merger.save_merged_audio(merged_audio, sr, output_path)
    
    return merged_audio, sr


def get_audio_merger(
    mode: str = "concatenate",
    sample_rate: int = 16000,
    crossfade_ms: float = 100.0,
    overlap_ms: float = 100.0,
    crossfade_shape: str = "linear",
    normalize: bool = True,
    silence_between_ms: float = 0.0
) -> AudioMerger:
    """
    Get a configured AudioMerger instance
    
    Args:
        mode: Merge mode ('concatenate', 'overlap', 'crossfade', 'mix')
        sample_rate: Sample rate in Hz
        crossfade_ms: Crossfade duration in milliseconds
        overlap_ms: Overlap duration in milliseconds
        crossfade_shape: Shape of crossfade ('linear', 'exponential', 'logarithmic')
        normalize: Whether to normalize segments
        silence_between_ms: Silence duration between segments
        
    Returns:
        Configured AudioMerger instance
        
    Example:
        >>> merger = get_audio_merger(mode='crossfade', crossfade_ms=200)
        >>> merged_audio, sr = merger.merge_audio_segments([audio1, audio2])
    """
    try:
        merge_mode = MergeMode(mode)
    except ValueError:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: "
            f"{', '.join([m.value for m in MergeMode])}"
        )
    
    config = AudioMergeConfig(
        mode=merge_mode,
        sample_rate=sample_rate,
        crossfade_duration_ms=crossfade_ms,
        overlap_duration_ms=overlap_ms,
        crossfade_shape=crossfade_shape,
        normalize_segments=normalize,
        silence_between_ms=silence_between_ms
    )
    
    return AudioMerger(config)