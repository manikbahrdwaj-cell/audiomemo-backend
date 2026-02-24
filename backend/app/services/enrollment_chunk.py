"""
Audio chunk record for enrollment sessions.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import numpy as np


@dataclass
class AudioChunkRecord:
    """Record of a single audio chunk during enrollment"""
    chunk_id: str
    timestamp: datetime
    duration_seconds: float
    audio_data: np.ndarray  # Raw audio samples
    sample_rate: int = 16000
    embedding: Optional[np.ndarray] = None
    embedding_timestamp: Optional[datetime] = None
    quality_score: float = 1.0  # 0-1 quality confidence
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "chunk_id": self.chunk_id,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "has_embedding": self.embedding is not None,
            "quality_score": self.quality_score,
            "error": self.error,
            "embedding_timestamp": self.embedding_timestamp.isoformat() if self.embedding_timestamp else None
        }