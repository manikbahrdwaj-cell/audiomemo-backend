"""
Verification Service for Voice Biometric Authentication
Handles multi-chunk verification with 5-second audio chunks
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from enum import Enum
import numpy as np
import io
from dataclasses import dataclass, field

from voice_embedding import generate_embedding, generate_embedding_with_chunking, calculate_cosine_similarity

logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========

class VerificationStatus(Enum):
    """Status of verification session"""
    CREATED = "created"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class VerificationSessionConfig:
    """Configuration for verification sessions"""
    max_chunks: int = 3           # Maximum chunks to collect
    chunk_timeout_seconds: int = 30  # Timeout per chunk
    verification_threshold: float = 0.75  # Similarity threshold for verification
    auto_process: bool = True      # Auto-process chunks
    aggregation_method: str = 'mean'  # How to combine chunk embeddings


# ========== DATA MODELS ==========

@dataclass
class VerificationChunk:
    """Represents a single audio chunk in verification"""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chunk_number: int = 0
    audio_data: Optional[np.ndarray] = None
    sample_rate: int = 16000
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    quality_score: float = 1.0    # 0-1 quality metric
    embedding: Optional[np.ndarray] = None
    embedding_timestamp: Optional[datetime] = None

    def __repr__(self) -> str:
        return (
            f"VerificationChunk(#{self.chunk_number}, "
            f"duration={self.duration_seconds:.2f}s, "
            f"has_embedding={self.embedding is not None})"
        )

    def to_dict(self) -> dict:
        """Convert chunk to dictionary for serialization"""
        return {
            "chunk_id": self.chunk_id,
            "chunk_number": self.chunk_number,
            "sample_rate": self.sample_rate,
            "duration_seconds": float(self.duration_seconds),
            "quality_score": float(self.quality_score),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "embedding_timestamp": self.embedding_timestamp.isoformat() if self.embedding_timestamp else None,
            "has_embedding": self.embedding is not None,
        }


@dataclass
class VerificationSession:
    """Complete verification session with multi-chunk support"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str = ""
    enrolled_embedding: Optional[np.ndarray] = None
    
    # Status tracking
    status: VerificationStatus = VerificationStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuration
    config: VerificationSessionConfig = field(default_factory=VerificationSessionConfig)
    
    # Chunks and embeddings
    chunks: List[VerificationChunk] = field(default_factory=list)
    embeddings: List[np.ndarray] = field(default_factory=list)
    
    # Merged audio
    merged_audio: Optional[np.ndarray] = None
    merged_audio_sample_rate: int = 16000
    merged_audio_embedding: Optional[np.ndarray] = None
    
    # Verification results
    similarity_scores: List[float] = field(default_factory=list)
    final_similarity_score: Optional[float] = None
    verification_result: Optional[bool] = None
    
    def __repr__(self) -> str:
        return (
            f"VerificationSession(id={self.session_id[:8]}, "
            f"phone={self.phone_number}, "
            f"status={self.status.value}, "
            f"chunks={len(self.chunks)}/{self.config.max_chunks})"
        )

    def add_chunk(self, audio_data: np.ndarray, duration_seconds: float, 
                  sample_rate: int = 16000, quality_score: float = 1.0) -> VerificationChunk:
        """
        Add an audio chunk to the verification session
        
        Args:
            audio_data: Audio samples as numpy array
            duration_seconds: Duration of audio chunk
            sample_rate: Sample rate of audio
            quality_score: Quality metric (0-1)
            
        Returns:
            VerificationChunk instance
        """
        if len(self.chunks) >= self.config.max_chunks:
            raise ValueError(f"Maximum chunks ({self.config.max_chunks}) reached")
        
        if self.status not in [VerificationStatus.CREATED, VerificationStatus.ACTIVE]:
            raise ValueError(f"Cannot add chunks to session in {self.status.value} state")
        
        # Update status to ACTIVE on first chunk
        if self.status == VerificationStatus.CREATED:
            self.status = VerificationStatus.ACTIVE
            self.started_at = datetime.utcnow()
        
        # Create chunk
        chunk = VerificationChunk(
            chunk_id=str(uuid.uuid4()),
            chunk_number=len(self.chunks) + 1,
            audio_data=audio_data.copy() if isinstance(audio_data, np.ndarray) else audio_data,
            sample_rate=sample_rate,
            duration_seconds=duration_seconds,
            quality_score=max(0.0, min(1.0, quality_score))
        )
        
        self.chunks.append(chunk)
        logger.info(f"Added chunk {chunk.chunk_number} to verification session {self.session_id[:8]}")
        
        return chunk

    def process_chunk(self, chunk_idx: int) -> Optional[np.ndarray]:
        """
        Generate embedding for a specific chunk using 5-second chunks
        
        Verification uses 5-second audio chunks (80,000 samples at 16kHz)
        to capture broader voice patterns suitable for comparison
        
        Args:
            chunk_idx: Index of chunk to process
            
        Returns:
            Generated embedding or None if failed
        """
        if chunk_idx >= len(self.chunks):
            raise IndexError(f"Chunk index {chunk_idx} out of range")
        
        chunk = self.chunks[chunk_idx]
        
        try:
            # Convert numpy array to bytes for embedding generation
            audio_bytes = io.BytesIO()
            import soundfile as sf
            sf.write(audio_bytes, chunk.audio_data, chunk.sample_rate, format='WAV')
            audio_bytes.seek(0)
            
            # Generate embedding with 5-second chunks for verification
            # 5-second chunks = 80,000 samples at 16kHz
            embedding = generate_embedding_with_chunking(
                audio_bytes.read(),
                chunk_size_seconds=5.0,          # 5-second chunks
                overlap_ratio=0.2,               # 20% overlap
                aggregation_method='mean'        # Average chunk embeddings
            )
            
            chunk.embedding = embedding
            chunk.embedding_timestamp = datetime.utcnow()
            
            self.embeddings.append(embedding)
            
            logger.info(
                f"Processed verification chunk {chunk_idx + 1}/{len(self.chunks)} "
                f"for session {self.session_id[:8]}: "
                f"embedding shape {embedding.shape} "
                f"(5-second chunking mode)"
            )
            
            return embedding
            
        except Exception as e:
            error_msg = f"Error processing verification chunk {chunk_idx}: {str(e)}"
            logger.error(error_msg)
            return None

    def merge_audio_chunks(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Merge all collected audio chunks into single audio stream
        
        Returns:
            Tuple of (success, message, merged_audio)
        """
        if not self.chunks:
            return False, "No audio chunks to merge", None
        
        try:
            logger.info(
                f"Merging {len(self.chunks)} verification chunks "
                f"for session {self.session_id[:8]}"
            )
            
            # All chunks should have same sample rate
            sample_rate = self.chunks[0].sample_rate
            
            # Concatenate all audio data
            audio_list = []
            for i, chunk in enumerate(self.chunks):
                if chunk.audio_data is None:
                    logger.warning(f"Chunk {i} has no audio data, skipping")
                    continue
                
                # Resample if needed
                if chunk.sample_rate != sample_rate:
                    logger.warning(
                        f"Chunk {i} has different sample rate "
                        f"({chunk.sample_rate} vs {sample_rate}), resampling"
                    )
                    # Apply simple resampling
                    ratio = chunk.sample_rate / sample_rate
                    chunk_resampled = np.interp(
                        np.linspace(0, len(chunk.audio_data), int(len(chunk.audio_data) / ratio)),
                        np.arange(len(chunk.audio_data)),
                        chunk.audio_data
                    )
                    audio_list.append(chunk_resampled)
                else:
                    audio_list.append(chunk.audio_data)
            
            if not audio_list:
                return False, "No valid audio chunks to merge", None
            
            merged_audio = np.concatenate(audio_list)
            self.merged_audio = merged_audio
            self.merged_audio_sample_rate = sample_rate
            
            logger.info(
                f"✓ Merged {len(audio_list)} audio chunks: "
                f"{len(merged_audio)} samples ({len(merged_audio)/sample_rate:.2f}s) "
                f"at {sample_rate}Hz"
            )
            
            return True, "Audio merged successfully", merged_audio
            
        except Exception as e:
            error_msg = f"Error merging audio chunks: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None

    def generate_merged_embedding(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Generate single embedding from merged audio
        
        Returns:
            Tuple of (success, message, embedding)
        """
        if self.merged_audio is None:
            return False, "No merged audio available - merge chunks first", None
        
        try:
            logger.info(
                f"Generating embedding from merged verification audio "
                f"({len(self.merged_audio)} samples, {self.merged_audio_sample_rate} Hz)"
            )
            
            # Convert audio to WAV bytes for embedding generation
            audio_bytes = io.BytesIO()
            import soundfile as sf
            sf.write(
                audio_bytes,
                self.merged_audio,
                self.merged_audio_sample_rate,
                format='WAV'
            )
            audio_bytes.seek(0)
            
            # Generate embedding with 5-second chunks for verification
            embedding = generate_embedding_with_chunking(
                audio_bytes.read(),
                chunk_size_seconds=5.0,          # 5-second chunks
                overlap_ratio=0.2,               # 20% overlap
                aggregation_method='mean'        # Average chunk embeddings
            )
            
            self.merged_audio_embedding = embedding
            
            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                self.merged_audio_embedding = embedding / norm
            
            logger.info(
                f"✓ Generated embedding from merged verification audio: "
                f"shape {self.merged_audio_embedding.shape}"
            )
            
            return True, "Embedding generated successfully", self.merged_audio_embedding
            
        except Exception as e:
            error_msg = f"Error generating embedding from merged audio: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None

    def verify_against_enrolled(self) -> Tuple[bool, float, str]:
        """
        Verify collected chunks against enrolled embedding
        
        Returns:
            Tuple of (verified, similarity_score, message)
        """
        if self.enrolled_embedding is None:
            return False, 0.0, "No enrolled embedding available"
        
        if self.merged_audio_embedding is None:
            return False, 0.0, "No verification embedding generated"
        
        try:
            # Calculate similarity
            similarity = calculate_cosine_similarity(
                self.enrolled_embedding,
                self.merged_audio_embedding
            )
            
            self.final_similarity_score = similarity
            verified = similarity >= self.config.verification_threshold
            self.verification_result = verified
            self.status = VerificationStatus.VERIFIED if verified else VerificationStatus.REJECTED
            
            message = (
                f"Verification {'PASSED' if verified else 'FAILED'}: "
                f"similarity {similarity:.4f} "
                f"(threshold: {self.config.verification_threshold})"
            )
            
            logger.info(message)
            return verified, similarity, message
            
        except Exception as e:
            error_msg = f"Error during verification: {str(e)}"
            logger.error(error_msg)
            return False, 0.0, error_msg

    def merge_and_verify(self) -> Tuple[bool, float, str]:
        """
        Complete workflow: merge audio chunks and verify against enrolled embedding
        
        Returns:
            Tuple of (verified, similarity_score, message)
        """
        logger.info(
            f"Starting merge and verify workflow for session {self.session_id[:8]}"
        )
        
        self.status = VerificationStatus.PROCESSING
        
        # Step 1: Merge audio chunks
        success, message, merged_audio = self.merge_audio_chunks()
        if not success:
            self.status = VerificationStatus.FAILED
            return False, 0.0, message
        
        # Step 2: Generate embedding from merged audio
        success, message, embedding = self.generate_merged_embedding()
        if not success:
            self.status = VerificationStatus.FAILED
            return False, 0.0, message
        
        # Step 3: Verify against enrolled embedding
        verified, similarity, message = self.verify_against_enrolled()
        
        self.completed_at = datetime.utcnow()
        
        return verified, similarity, message

    def to_dict(self) -> dict:
        """Convert verification session to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "similarity_scores": [float(s) for s in self.similarity_scores],
            "final_similarity_score": float(self.final_similarity_score) if self.final_similarity_score is not None else None,
            "verification_result": self.verification_result,
        }


# ========== SESSION MANAGEMENT ==========

# Global verification sessions storage (in production, use database)
_verification_sessions: dict = {}


def get_verification_manager() -> dict:
    """Get verification sessions manager"""
    return _verification_sessions


def create_verification_session(phone_number: str, config: Optional[VerificationSessionConfig] = None) -> VerificationSession:
    """
    Create a new verification session
    
    Args:
        phone_number: Phone number to verify
        config: Optional session configuration
        
    Returns:
        VerificationSession instance
    """
    from database import get_voice_embedding
    
    session = VerificationSession(
        phone_number=phone_number,
        config=config or VerificationSessionConfig()
    )
    
    # Get enrolled embedding
    enrolled_embedding = get_voice_embedding(phone_number)
    if enrolled_embedding is not None:
        session.enrolled_embedding = np.array(enrolled_embedding)
    
    _verification_sessions[session.session_id] = session
    
    logger.info(f"Created verification session {session.session_id[:8]} for {phone_number}")
    return session


def get_verification_session(session_id: str) -> Optional[VerificationSession]:
    """
    Get verification session by ID
    
    Args:
        session_id: Session ID
        
    Returns:
        VerificationSession or None
    """
    return _verification_sessions.get(session_id)


def find_verification_session_by_phone(phone_number: str) -> Optional[VerificationSession]:
    """
    Find an active verification session by phone number
    
    Args:
        phone_number: Phone number to search for
        
    Returns:
        VerificationSession if found and active, None otherwise
    """
    for session in _verification_sessions.values():
        if session.phone_number == phone_number and session.status in [
            VerificationStatus.CREATED,
            VerificationStatus.ACTIVE,
            VerificationStatus.PROCESSING
        ]:
            return session
    return None


def add_verification_chunk(
    session_id: str,
    audio_data: np.ndarray,
    duration_seconds: float,
    sample_rate: int = 16000,
    quality_score: float = 1.0
) -> Tuple[bool, str, Optional[VerificationChunk]]:
    """
    Add audio chunk to verification session
    
    Args:
        session_id: Session ID
        audio_data: Audio samples
        duration_seconds: Duration of audio
        sample_rate: Sample rate
        quality_score: Quality metric
        
    Returns:
        Tuple of (success, message, chunk)
    """
    session = get_verification_session(session_id)
    if not session:
        return False, f"Session {session_id} not found", None
    
    try:
        chunk = session.add_chunk(audio_data, duration_seconds, sample_rate, quality_score)
        return True, "Chunk added successfully", chunk
    except Exception as e:
        error_msg = f"Error adding chunk: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, None


def process_verification_session(session_id: str) -> Tuple[bool, float, str]:
    """
    Process verification session (merge and verify)
    
    Args:
        session_id: Session ID
        
    Returns:
        Tuple of (verified, similarity_score, message)
    """
    session = get_verification_session(session_id)
    if not session:
        return False, 0.0, f"Session {session_id} not found"
    
    return session.merge_and_verify()
