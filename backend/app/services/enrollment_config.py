"""
Configuration for enrollment sessions.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from app.ml.audio_merger import MergeMode


@dataclass
class EnrollmentSessionConfig:
    """Configuration for enrollment session"""
    max_chunks: int = 10  # Maximum number of chunks per session
    chunk_timeout_seconds: int = 30  # Max time to collect one chunk
    session_timeout_seconds: int = 300  # Max time for entire session
    min_chunks_required: int = 1  # Minimum chunks for enrollment
    auto_process: bool = True  # Auto-generate embeddings for each chunk
    merge_embeddings: bool = True  # Merge multiple embeddings
    merge_mode: MergeMode = MergeMode.CONCATENATE  # How to merge embeddings
    store_chunks: bool = True  # Store raw chunks (memory intensive)
    quality_threshold: float = 0.7  # Min quality score
    # Audio merging configuration
    merge_audio: bool = False  # Merge audio chunks before embedding generation
    audio_merge_mode: MergeMode = MergeMode.OVERLAP  # How to merge audio chunks
    audio_merge_crossfade_ms: float = 100.0  # Crossfade duration in milliseconds
    auto_merge_threshold: int = 2  # Minimum chunks to trigger auto-merge
    
    def __post_init__(self):
        """Validate configuration"""
        if self.min_chunks_required > self.max_chunks:
            raise ValueError("min_chunks_required cannot exceed max_chunks")
        if self.quality_threshold < 0 or self.quality_threshold > 1:
            raise ValueError("quality_threshold must be between 0 and 1")