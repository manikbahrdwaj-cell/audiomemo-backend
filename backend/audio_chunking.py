"""
Audio Chunking Module
Handles segmentation and processing of audio data with numpy
Supports overlapping chunks and multiple aggregation strategies
"""

import numpy as np
import torch
import logging
from typing import Tuple, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for audio chunking"""
    chunk_size: int = 16000  # 1 second at 16kHz
    overlap_ratio: float = 0.2  # 20% overlap between chunks
    min_chunk_duration_ms: int = 500  # Minimum 0.5 seconds
    max_chunk_duration_ms: int = 5000  # Maximum 5 seconds
    sample_rate: int = 16000
    
    def __post_init__(self):
        """Validate configuration"""
        if not 0 <= self.overlap_ratio < 1:
            raise ValueError("overlap_ratio must be between 0 and 1")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
    
    @property
    def overlap_samples(self) -> int:
        """Calculate overlap in samples"""
        return int(self.chunk_size * self.overlap_ratio)
    
    @property
    def stride_samples(self) -> int:
        """Calculate stride (hop size) in samples"""
        return self.chunk_size - self.overlap_samples


class AudioChunker:
    """
    Handles audio chunking and windowing with numpy
    
    Features:
    - Segment audio into overlapping chunks
    - Apply windowing functions (Hann, Hamming)
    - Configurable chunk size and overlap
    - Boundary handling
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize AudioChunker
        
        Args:
            config: ChunkConfig object with chunking parameters
        """
        self.config = config or ChunkConfig()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate chunking configuration"""
        min_samples = int(self.config.sample_rate * self.config.min_chunk_duration_ms / 1000)
        max_samples = int(self.config.sample_rate * self.config.max_chunk_duration_ms / 1000)
        
        if self.config.chunk_size < min_samples:
            logger.warning(
                f"Chunk size {self.config.chunk_size} is below minimum "
                f"{min_samples}. Adjusting..."
            )
            self.config.chunk_size = min_samples
        
        if self.config.chunk_size > max_samples:
            logger.warning(
                f"Chunk size {self.config.chunk_size} exceeds maximum "
                f"{max_samples}. Adjusting..."
            )
            self.config.chunk_size = max_samples
    
    def chunk(self, audio: Union[np.ndarray, torch.Tensor]) -> List[np.ndarray]:
        """
        Segment audio into overlapping chunks
        
        Args:
            audio: Audio waveform as numpy array or torch tensor of shape (n_samples,)
            
        Returns:
            List of audio chunks as numpy arrays
            
        Example:
            >>> chunker = AudioChunker()
            >>> audio = np.random.randn(48000)  # 3 seconds
            >>> chunks = chunker.chunk(audio)
            >>> print(len(chunks))  # Multiple chunks with overlap
        """
        # Convert to numpy if needed
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()
        
        if audio.ndim != 1:
            raise ValueError(f"Expected 1D audio, got shape {audio.shape}")
        
        # Handle short audio
        if len(audio) < self.config.chunk_size:
            logger.debug(f"Audio length {len(audio)} < chunk size {self.config.chunk_size}")
            return [audio]
        
        chunks = []
        stride = self.config.stride_samples
        
        # Generate chunks with overlap
        for start_idx in range(0, len(audio) - self.config.chunk_size + 1, stride):
            end_idx = start_idx + self.config.chunk_size
            chunk = audio[start_idx:end_idx]
            chunks.append(chunk)
        
        # Handle remaining samples if any
        remaining_start = len(chunks) * stride if chunks else 0
        if remaining_start < len(audio):
            last_chunk = audio[remaining_start:]
            if len(last_chunk) > self.config.chunk_size / 4:  # Keep if > 25% of chunk size
                chunks.append(last_chunk)
            elif chunks:  # Append to last chunk if too small
                # Pad last chunk with zeros if needed
                last_chunk_padded = np.pad(
                    last_chunk,
                    (0, self.config.chunk_size - len(last_chunk)),
                    mode='constant'
                )
                chunks[-1] = last_chunk_padded
        
        logger.debug(f"Created {len(chunks)} chunks from {len(audio)} samples")
        return chunks
    
    def apply_windowing(
        self,
        audio: np.ndarray,
        window: str = 'hann'
    ) -> np.ndarray:
        """
        Apply windowing function to audio
        
        Args:
            audio: Audio waveform as numpy array
            window: Window type ('hann', 'hamming', 'blackman', 'bartlett', 'nuttall')
            
        Returns:
            Windowed audio
            
        Example:
            >>> chunker = AudioChunker()
            >>> audio = np.random.randn(16000)
            >>> windowed = chunker.apply_windowing(audio, 'hann')
        """
        if audio.ndim != 1:
            raise ValueError(f"Expected 1D audio, got shape {audio.shape}")
        
        if window == 'hann':
            window_func = np.hanning(len(audio))
        elif window == 'hamming':
            window_func = np.hamming(len(audio))
        elif window == 'blackman':
            window_func = np.blackman(len(audio))
        elif window == 'bartlett':
            window_func = np.bartlett(len(audio))
        elif window == 'nuttall':
            window_func = np.nuttall(len(audio))
        else:
            raise ValueError(f"Unknown window type: {window}")
        
        return audio * window_func
    
    def normalize_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """
        Normalize audio chunk to [-1, 1] range
        
        Args:
            chunk: Audio chunk
            
        Returns:
            Normalized chunk
        """
        max_val = np.max(np.abs(chunk))
        if max_val > 0:
            return chunk / max_val
        return chunk
    
    def compute_chunk_features(self, chunk: np.ndarray) -> dict:
        """
        Compute basic features of audio chunk
        
        Args:
            chunk: Audio chunk
            
        Returns:
            Dictionary with chunk statistics
        """
        return {
            'length': len(chunk),
            'duration_ms': len(chunk) / self.config.sample_rate * 1000,
            'rms': float(np.sqrt(np.mean(chunk ** 2))),
            'peak': float(np.max(np.abs(chunk))),
            'mean': float(np.mean(chunk)),
            'std': float(np.std(chunk)),
            'energy': float(np.sum(chunk ** 2))
        }


class EmbeddingAggregator:
    """
    Aggregates embeddings from multiple audio chunks
    
    Strategies:
    - Mean pooling
    - Max pooling
    - Weighted average (linear weights)
    - Weighted average (energy-based weights)
    """
    
    @staticmethod
    def mean_pool(embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Average embeddings across chunks
        
        Args:
            embeddings: List of embedding vectors (shape: n_chunks x embedding_dim)
            
        Returns:
            Averaged embedding (shape: embedding_dim,)
        """
        if not embeddings:
            raise ValueError("No embeddings provided")
        
        embeddings_array = np.array(embeddings)
        return np.mean(embeddings_array, axis=0)
    
    @staticmethod
    def max_pool(embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Select maximum value per dimension across chunks
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Max-pooled embedding
        """
        if not embeddings:
            raise ValueError("No embeddings provided")
        
        embeddings_array = np.array(embeddings)
        return np.max(embeddings_array, axis=0)
    
    @staticmethod
    def weighted_average(
        embeddings: List[np.ndarray],
        weights: Optional[np.ndarray] = None,
        weight_type: str = 'linear'
    ) -> np.ndarray:
        """
        Weighted average of embeddings
        
        Args:
            embeddings: List of embedding vectors
            weights: Custom weights for embeddings. If None, computed based on weight_type
            weight_type: 'linear' (increases), 'inverse' (decreases), 'energy' (energy-based),
                        'normalized' (centers on middle chunks)
            
        Returns:
            Weighted-averaged embedding
        """
        if not embeddings:
            raise ValueError("No embeddings provided")
        
        n_embeddings = len(embeddings)
        
        if weights is None:
            if weight_type == 'linear':
                # Linear increasing weights
                weights = np.linspace(1, n_embeddings, n_embeddings)
            elif weight_type == 'inverse':
                # Linear decreasing weights
                weights = np.linspace(n_embeddings, 1, n_embeddings)
            elif weight_type == 'normalized':
                # Center more weight on middle chunks
                center = n_embeddings / 2
                distances = np.abs(np.arange(n_embeddings) - center)
                weights = 1 / (1 + distances)
            elif weight_type == 'energy':
                # Weights based on energy (will be set later with chunk data)
                weights = np.ones(n_embeddings)
            else:
                raise ValueError(f"Unknown weight_type: {weight_type}")
        
        # Normalize weights
        weights = np.array(weights)
        if len(weights) != n_embeddings:
            raise ValueError(f"Number of weights ({len(weights)}) != number of embeddings ({n_embeddings})")
        
        weights = weights / np.sum(weights)
        
        # Compute weighted average
        weighted_sum = np.zeros_like(embeddings[0])
        for embedding, weight in zip(embeddings, weights):
            weighted_sum += embedding * weight
        
        return weighted_sum
    
    @staticmethod
    def weighted_average_by_energy(
        embeddings: List[np.ndarray],
        chunks: List[np.ndarray]
    ) -> np.ndarray:
        """
        Weighted average based on chunk energy (RMS)
        
        Args:
            embeddings: List of embedding vectors
            chunks: List of audio chunks
            
        Returns:
            Energy-weighted embedding
        """
        if not embeddings or not chunks:
            raise ValueError("Embeddings and chunks lists cannot be empty")
        
        if len(embeddings) != len(chunks):
            raise ValueError("Number of embeddings must match number of chunks")
        
        # Compute energy for each chunk
        energies = np.array([np.sqrt(np.mean(chunk ** 2)) for chunk in chunks])
        
        # Normalize energies to weights
        weights = energies / np.sum(energies)
        
        return EmbeddingAggregator.weighted_average(embeddings, weights)
    
    @staticmethod
    def variance_weighted_average(embeddings: List[np.ndarray]) -> np.ndarray:
        """
        Weight embeddings inversely by their variance (more stable chunks weighted more)
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Variance-weighted embedding
        """
        if not embeddings:
            raise ValueError("No embeddings provided")
        
        embeddings_array = np.array(embeddings)
        
        # Compute variance for each embedding along dimensions
        variances = np.var(embeddings_array, axis=1)
        
        # Inverse variance weighting (more stable = less variance = higher weight)
        # Add small epsilon to avoid division by zero
        weights = 1.0 / (variances + 1e-10)
        weights = weights / np.sum(weights)
        
        return EmbeddingAggregator.weighted_average(embeddings, weights)


class ChunkProcessor:
    """
    High-level interface for processing chunks and aggregating results
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize ChunkProcessor
        
        Args:
            config: ChunkConfig object
        """
        self.chunker = AudioChunker(config)
        self.aggregator = EmbeddingAggregator()
    
    def process_audio(
        self,
        audio: Union[np.ndarray, torch.Tensor],
        embedding_func,
        aggregation_method: str = 'mean',
        apply_window: bool = True,
        window_type: str = 'hann',
        normalize: bool = True
    ) -> Tuple[np.ndarray, dict]:
        """
        Process audio through chunking and embedding aggregation
        
        Args:
            audio: Audio waveform
            embedding_func: Function that takes audio chunk and returns embedding vector
            aggregation_method: 'mean', 'max', 'weighted_linear', 'weighted_inverse',
                              'weighted_normalized', or 'energy_weighted'
            apply_window: Whether to apply windowing to chunks
            window_type: Type of window to apply
            normalize: Whether to normalize chunks
            
        Returns:
            Tuple of (aggregated_embedding, metadata_dict)
            
        Example:
            >>> def my_embedding_func(audio): return np.random.randn(192)
            >>> processor = ChunkProcessor()
            >>> audio = np.random.randn(48000)
            >>> embedding, meta = processor.process_audio(audio, my_embedding_func)
        """
        # Split audio into chunks
        chunks = self.chunker.chunk(audio)
        
        logger.info(f"Processing audio with {len(chunks)} chunks")
        
        # Process each chunk
        embeddings = []
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            # Apply window if requested
            if apply_window:
                chunk = self.chunker.apply_windowing(chunk, window_type)
            
            # Normalize if requested
            if normalize:
                chunk = self.chunker.normalize_chunk(chunk)
            
            # Generate embedding
            try:
                embedding = embedding_func(chunk)
                embeddings.append(embedding)
                processed_chunks.append(chunk)
                logger.debug(f"Chunk {i}: embedding shape {embedding.shape}")
            except Exception as e:
                logger.warning(f"Failed to process chunk {i}: {e}")
                continue
        
        if not embeddings:
            raise ValueError("No embeddings generated from chunks")
        
        # Aggregate embeddings
        if aggregation_method == 'mean':
            aggregated = self.aggregator.mean_pool(embeddings)
        elif aggregation_method == 'max':
            aggregated = self.aggregator.max_pool(embeddings)
        elif aggregation_method == 'weighted_linear':
            aggregated = self.aggregator.weighted_average(
                embeddings,
                weight_type='linear'
            )
        elif aggregation_method == 'weighted_inverse':
            aggregated = self.aggregator.weighted_average(
                embeddings,
                weight_type='inverse'
            )
        elif aggregation_method == 'weighted_normalized':
            aggregated = self.aggregator.weighted_average(
                embeddings,
                weight_type='normalized'
            )
        elif aggregation_method == 'energy_weighted':
            aggregated = self.aggregator.weighted_average_by_energy(
                embeddings,
                processed_chunks
            )
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation_method}")
        
        # Prepare metadata
        metadata = {
            'n_chunks': len(embeddings),
            'total_duration_ms': len(audio) / self.chunker.config.sample_rate * 1000,
            'chunk_size_ms': self.chunker.config.chunk_size / self.chunker.config.sample_rate * 1000,
            'overlap_ratio': self.chunker.config.overlap_ratio,
            'aggregation_method': aggregation_method,
            'window_type': window_type if apply_window else 'none',
            'normalized': normalize,
            'chunk_features': [self.chunker.compute_chunk_features(chunk) for chunk in processed_chunks]
        }
        
        return aggregated, metadata


def create_default_chunker() -> AudioChunker:
    """
    Create audio chunker with default configuration
    
    Returns:
        AudioChunker instance with reasonable defaults
    """
    config = ChunkConfig(
        chunk_size=16000,      # 1 second
        overlap_ratio=0.2,     # 20% overlap
        sample_rate=16000
    )
    return AudioChunker(config)


def create_default_processor() -> ChunkProcessor:
    """
    Create chunk processor with default configuration
    
    Returns:
        ChunkProcessor instance with reasonable defaults
    """
    return ChunkProcessor()
