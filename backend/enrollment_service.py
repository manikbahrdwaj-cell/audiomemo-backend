"""
Enrollment Service Module
Handles multi-chunk voice enrollment with session management
"""

import numpy as np
import torch
import logging
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import io

from voice_embedding import generate_embedding, get_embedding_with_auto_chunking, generate_embedding_with_chunking
from database import store_voice_embedding, get_voice_embedding
from embedding_operations import AudioMerger, AudioMergeConfig, MergeMode
from audio_chunking import AudioChunker, ChunkConfig

logger = logging.getLogger(__name__)


class EnrollmentStatus(Enum):
    """Enrollment session status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    COLLECTING = "collecting"  # Collecting audio chunks
    PROCESSING = "processing"  # Processing chunks into embeddings
    FINALIZING = "finalizing"  # Merging embeddings
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


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


@dataclass
class EnrollmentSession:
    """Session for managing voice enrollment with multiple chunks"""
    session_id: str
    phone_number: str
    config: EnrollmentSessionConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: EnrollmentStatus = EnrollmentStatus.INITIALIZING
    error_message: Optional[str] = None
    
    # Audio chunks collected during session
    chunks: List[AudioChunkRecord] = field(default_factory=list)
    
    # Aggregated embeddings
    embeddings: List[np.ndarray] = field(default_factory=list)
    merged_embedding: Optional[np.ndarray] = None
    
    # Audio merging fields
    merged_audio: Optional[np.ndarray] = None  # Merged audio from all chunks
    merged_audio_sample_rate: int = 16000
    merged_audio_timestamp: Optional[datetime] = None
    merged_audio_embedding: Optional[np.ndarray] = None  # Embedding from merged audio
    
    # Session metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_chunk(self, audio_data: np.ndarray, duration_seconds: float, 
                  sample_rate: int = 16000, quality_score: float = 1.0) -> AudioChunkRecord:
        """
        Add an audio chunk to the session
        
        Args:
            audio_data: Audio waveform as numpy array
            duration_seconds: Duration of the audio in seconds
            sample_rate: Sample rate of the audio
            quality_score: Quality confidence score (0-1)
            
        Returns:
            AudioChunkRecord with chunk details
            
        Raises:
            ValueError: If session is full or invalid state
        """
        if self.status not in [EnrollmentStatus.ACTIVE, EnrollmentStatus.COLLECTING]:
            raise ValueError(f"Cannot add chunks in {self.status} state")
        
        if len(self.chunks) >= self.config.max_chunks:
            raise ValueError(f"Session has reached max chunks limit ({self.config.max_chunks})")
        
        if quality_score < self.config.quality_threshold:
            logger.warning(f"Audio quality score {quality_score} below threshold {self.config.quality_threshold}")
        
        # Create chunk record
        chunk = AudioChunkRecord(
            chunk_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            duration_seconds=duration_seconds,
            audio_data=audio_data,
            sample_rate=sample_rate,
            quality_score=quality_score
        )
        
        self.chunks.append(chunk)
        self.status = EnrollmentStatus.COLLECTING
        
        logger.info(
            f"Added chunk {len(self.chunks)}/{self.config.max_chunks} "
            f"to session {self.session_id[:8]}: {duration_seconds:.2f}s"
        )
        
        return chunk
    
    def process_chunk(self, chunk_idx: int) -> Optional[np.ndarray]:
        """
        Generate embedding for a specific chunk
        
        Uses 1-second audio chunks (16,000 samples at 16kHz) for enrollment
        to capture fine-grained voice characteristics
        
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
            # For embedding generation, we need WAV format
            # Create a simple WAV header and append the audio data
            import soundfile as sf
            sf.write(audio_bytes, chunk.audio_data, chunk.sample_rate, format='WAV')
            audio_bytes.seek(0)
            
            # Generate embedding with 1-second chunks for enrollment
            # 1-second chunks = 16,000 samples at 16kHz
            embedding = generate_embedding_with_chunking(
                audio_bytes.read(),
                chunk_size_seconds=1.0,          # 1-second chunks
                overlap_ratio=0.2,               # 20% overlap
                aggregation_method='mean'        # Average chunk embeddings
            )
            
            chunk.embedding = embedding
            chunk.embedding_timestamp = datetime.utcnow()
            
            self.embeddings.append(embedding)
            
            logger.info(
                f"Processed chunk {chunk_idx + 1}/{len(self.chunks)} "
                f"for session {self.session_id[:8]}: "
                f"embedding shape {embedding.shape} "
                f"(1-second chunking mode)"
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx}: {str(e)}")
            chunk.error = str(e)
            return None
    
    def process_all_chunks(self) -> List[np.ndarray]:
        """
        Process all chunks in the session
        
        Returns:
            List of generated embeddings
        """
        logger.info(f"Processing {len(self.chunks)} chunks for session {self.session_id[:8]}")
        
        self.status = EnrollmentStatus.PROCESSING
        
        processed = []
        for idx in range(len(self.chunks)):
            embedding = self.process_chunk(idx)
            if embedding is not None:
                processed.append(embedding)
        
        logger.info(f"Successfully processed {len(processed)}/{len(self.chunks)} chunks")
        
        return processed
    
    def merge_audio_chunks(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Merge all collected audio chunks into a single audio file
        
        Returns:
            Tuple of (success, message, merged_audio)
        """
        if not self.chunks:
            return False, "No audio chunks to merge", None
        
        if len(self.chunks) == 1:
            # Single chunk - no merge needed
            self.merged_audio = self.chunks[0].audio_data
            self.merged_audio_sample_rate = self.chunks[0].sample_rate
            self.merged_audio_timestamp = datetime.utcnow()
            logger.info(f"Single chunk detected - no merge needed")
            return True, "Single chunk (no merge required)", self.merged_audio
        
        try:
            logger.info(
                f"Merging {len(self.chunks)} audio chunks for session {self.session_id[:8]} "
                f"using {self.config.audio_merge_mode.value} mode"
            )
            
            # Create audio merger with configured settings
            merge_config = AudioMergeConfig(
                mode=self.config.audio_merge_mode,
                sample_rate=16000,
                crossfade_duration_ms=self.config.audio_merge_crossfade_ms,
                overlap_duration_ms=self.config.audio_merge_crossfade_ms
            )
            
            merger = AudioMerger(merge_config)
            
            # Extract audio data and sample rates from chunks
            audio_segments = [chunk.audio_data for chunk in self.chunks]
            sample_rates = [chunk.sample_rate for chunk in self.chunks]
            
            # Merge audio segments
            merged_audio, sample_rate = merger.merge_audio_segments(
                audio_segments,
                sample_rates
            )
            
            self.merged_audio = merged_audio
            self.merged_audio_sample_rate = sample_rate
            self.merged_audio_timestamp = datetime.utcnow()
            
            total_duration = len(merged_audio) / sample_rate
            orig_duration = sum(chunk.duration_seconds for chunk in self.chunks)
            
            logger.info(
                f"✓ Successfully merged {len(self.chunks)} chunks into {len(merged_audio)} samples "
                f"({total_duration:.2f}s, original total: {orig_duration:.2f}s)"
            )
            
            return True, f"Merged {len(self.chunks)} chunks successfully", merged_audio
            
        except Exception as e:
            error_msg = f"Error merging audio chunks: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def generate_embedding_from_merged_audio(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Generate embedding from merged audio
        
        Returns:
            Tuple of (success, message, embedding)
        """
        if self.merged_audio is None:
            return False, "No merged audio available - merge chunks first", None
        
        try:
            logger.info(
                f"Generating embedding from merged audio "
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
            
            # Generate embedding with 1-second chunks for enrollment
            # 1-second chunks = 16,000 samples at 16kHz
            embedding = generate_embedding_with_chunking(
                audio_bytes.read(),
                chunk_size_seconds=1.0,          # 1-second chunks
                overlap_ratio=0.2,               # 20% overlap
                aggregation_method='mean'        # Average chunk embeddings
            )
            
            self.merged_audio_embedding = embedding
            
            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                self.merged_audio_embedding = embedding / norm
            
            logger.info(
                f"✓ Generated embedding from merged audio: shape {self.merged_audio_embedding.shape}"
            )
            
            return True, "Embedding generated successfully", self.merged_audio_embedding
            
        except Exception as e:
            error_msg = f"Error generating embedding from merged audio: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def merge_and_generate_embedding(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Complete workflow: merge audio chunks and generate single embedding
        
        Returns:
            Tuple of (success, message, embedding)
        """
        logger.info(
            f"Starting merge and generate workflow for session {self.session_id[:8]}"
        )
        
        self.status = EnrollmentStatus.PROCESSING
        
        # Step 1: Merge audio chunks
        success, message, merged_audio = self.merge_audio_chunks()
        if not success:
            logger.error(f"Failed to merge audio: {message}")
            return False, f"Audio merge failed: {message}", None
        
        # Step 2: Generate embedding from merged audio
        success, message, embedding = self.generate_embedding_from_merged_audio()
        if not success:
            logger.error(f"Failed to generate embedding: {message}")
            return False, f"Embedding generation failed: {message}", None
        
        logger.info(
            f"✓ Merge and generate workflow completed successfully"
        )
        
        return True, "Merge and embedding generation successful", embedding
    
    def merge_embeddings_strategy(self) -> Optional[np.ndarray]:
        """
        Merge multiple embeddings using configured strategy
        
        Returns:
            Merged embedding or None if failed
        """
        if not self.embeddings:
            logger.warning("No embeddings to merge")
            return None
        
        if len(self.embeddings) == 1:
            self.merged_embedding = self.embeddings[0]
            return self.merged_embedding
        
        try:
            # Stack embeddings for averaging
            embedding_matrix = np.array(self.embeddings)  # Shape: (n_chunks, 192)
            
            if self.config.merge_mode == MergeMode.CONCATENATE:
                # Average embeddings (most common for voice biometrics)
                self.merged_embedding = np.mean(embedding_matrix, axis=0)
                logger.info(f"Merged {len(self.embeddings)} embeddings using averaging")
                
            elif self.config.merge_mode == MergeMode.OVERLAP:
                # Weighted average giving more weight to recent chunks
                weights = np.linspace(0.5, 1.0, len(self.embeddings))
                weights = weights / weights.sum()
                self.merged_embedding = np.average(embedding_matrix, axis=0, weights=weights)
                logger.info(f"Merged {len(self.embeddings)} embeddings with time-weighted averaging")
                
            elif self.config.merge_mode == MergeMode.MIX:
                # Simple averaging (same as CONCATENATE for embeddings)
                self.merged_embedding = np.mean(embedding_matrix, axis=0)
                logger.info(f"Merged {len(self.embeddings)} embeddings using averaging")
            
            else:
                # Default to averaging
                self.merged_embedding = np.mean(embedding_matrix, axis=0)
                logger.info(f"Merged {len(self.embeddings)} embeddings using default averaging")
            
            # Normalize the merged embedding
            norm = np.linalg.norm(self.merged_embedding)
            if norm > 0:
                self.merged_embedding = self.merged_embedding / norm
            
            return self.merged_embedding
            
        except Exception as e:
            logger.error(f"Error merging embeddings: {str(e)}")
            return None
    
    def finalize_enrollment(self, force_single: bool = False) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Finalize enrollment by storing the merged embedding
        Supports both embedding merging and audio merging strategies
        
        Args:
            force_single: Use single best embedding if merge fails
            
        Returns:
            Tuple of (success, message, final_embedding)
        """
        self.status = EnrollmentStatus.FINALIZING
        
        # Check minimum chunks requirement
        if len(self.chunks) < self.config.min_chunks_required:
            return False, f"Insufficient chunks. Need {self.config.min_chunks_required}, got {len(self.chunks)}", None
        
        final_embedding = None
        embedding_source = None
        
        # Strategy 1: Use merged audio embedding if configured and chunks > 1
        if self.config.merge_audio and len(self.chunks) > 1:
            logger.info("Using audio merge strategy")
            success, message, embedding = self.merge_and_generate_embedding()
            if success and embedding is not None:
                final_embedding = embedding
                embedding_source = f"merged_audio({len(self.chunks)}_chunks)"
                logger.info(f"✓ Using embedding from merged audio ({len(self.chunks)} chunks)")
            else:
                logger.warning(f"Audio merge strategy failed: {message}. Falling back to embedding merge.")
        
        # Strategy 2: Use merged embeddings if audio merge failed or not configured
        if final_embedding is None:
            # Process any unprocessed chunks
            if len(self.embeddings) < len(self.chunks):
                self.process_all_chunks()
            
            # Check if we have any valid embeddings
            if not self.embeddings:
                return False, "No valid embeddings generated", None
            
            # Merge embeddings if configured
            if self.config.merge_embeddings and len(self.embeddings) > 1:
                final_embedding = self.merge_embeddings_strategy()
                
                if final_embedding is None and not force_single:
                    return False, "Failed to merge embeddings", None
                elif final_embedding is None:
                    # Fall back to best embedding
                    final_embedding = self.embeddings[0]
                    embedding_source = "best_single_embedding"
                    logger.warning("Using single best embedding due to merge failure")
                else:
                    embedding_source = f"merged_embeddings({len(self.embeddings)}_embeddings)"
            else:
                # Use first (or only) embedding
                final_embedding = self.embeddings[0]
                embedding_source = "single_embedding"
        
        # Store in database
        try:
            vector_id = store_voice_embedding(self.phone_number, final_embedding)
            
            self.merged_embedding = final_embedding
            self.status = EnrollmentStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            
            logger.info(
                f"✓ Enrollment completed for {self.phone_number}. "
                f"Session: {self.session_id[:8]}, Vector ID: {vector_id[:8]}, "
                f"Chunks: {len(self.chunks)}, Source: {embedding_source}"
            )
            
            return True, f"Enrollment completed with {len(self.chunks)} chunk(s) - {embedding_source}", final_embedding
            
        except Exception as e:
            error_msg = f"Failed to store embedding: {str(e)}"
            logger.error(error_msg)
            self.status = EnrollmentStatus.ERROR
            self.error_message = error_msg
            return False, error_msg, None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "chunks_collected": len(self.chunks),
            "max_chunks": self.config.max_chunks,
            "embeddings_generated": len(self.embeddings),
            "has_merged_embedding": self.merged_embedding is not None,
            "has_merged_audio": self.merged_audio is not None,
            "merged_audio_duration_seconds": len(self.merged_audio) / self.merged_audio_sample_rate if self.merged_audio is not None else None,
            "has_merged_audio_embedding": self.merged_audio_embedding is not None,
            "merged_audio_timestamp": self.merged_audio_timestamp.isoformat() if self.merged_audio_timestamp else None,
            "merge_audio_enabled": self.config.merge_audio,
            "audio_merge_mode": self.config.audio_merge_mode.value,
            "error_message": self.error_message,
            "chunks": [chunk.to_dict() for chunk in self.chunks]
        }
    
    def cleanup(self) -> None:
        """Clean up session resources (especially audio data if not storing)"""
        if not self.config.store_chunks:
            for chunk in self.chunks:
                chunk.audio_data = None
            logger.info(f"Cleaned up audio data for session {self.session_id[:8]}")


class EnrollmentServiceManager:
    """
    Manages multiple enrollment sessions
    
    Features:
    - Create and track enrollment sessions
    - Automatic session cleanup
    - Session timeout management
    """
    
    def __init__(self):
        """Initialize the enrollment service manager"""
        self.sessions: Dict[str, EnrollmentSession] = {}
        logger.info("Enrollment Service Manager initialized")
    
    def create_session(
        self, 
        phone_number: str,
        config: Optional[EnrollmentSessionConfig] = None
    ) -> EnrollmentSession:
        """
        Create a new enrollment session
        
        Args:
            phone_number: Phone number for enrollment
            config: Optional session configuration
            
        Returns:
            Created EnrollmentSession
        """
        if config is None:
            config = EnrollmentSessionConfig()
        
        session_id = str(uuid.uuid4())
        session = EnrollmentSession(
            session_id=session_id,
            phone_number=phone_number,
            config=config
        )
        session.status = EnrollmentStatus.ACTIVE
        session.started_at = datetime.utcnow()
        
        self.sessions[session_id] = session
        
        logger.info(f"Created enrollment session {session_id[:8]} for {phone_number}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[EnrollmentSession]:
        """Get an enrollment session"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """Remove an enrollment session"""
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            session.cleanup()
            logger.info(f"Removed enrollment session {session_id[:8]}")
            return True
        return False
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired sessions
        
        Args:
            max_age_seconds: Maximum age for a session
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            age_seconds = (now - session.created_at).total_seconds()
            
            if age_seconds > max_age_seconds:
                expired_sessions.append(session_id)
        
        cleanup_count = 0
        for session_id in expired_sessions:
            if self.remove_session(session_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired enrollment sessions")
        
        return cleanup_count
    
    def get_active_sessions(self) -> Dict[str, EnrollmentSession]:
        """Get all active sessions"""
        return {
            sid: s for sid, s in self.sessions.items()
            if s.status in [EnrollmentStatus.ACTIVE, EnrollmentStatus.COLLECTING, EnrollmentStatus.PROCESSING]
        }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with summaries"""
        return [session.get_summary() for session in self.sessions.values()]


# Global enrollment service manager instance
_enrollment_manager: Optional[EnrollmentServiceManager] = None


def get_enrollment_manager() -> EnrollmentServiceManager:
    """Get or create the global enrollment service manager"""
    global _enrollment_manager
    
    if _enrollment_manager is None:
        _enrollment_manager = EnrollmentServiceManager()
    
    return _enrollment_manager


# Helper functions for easy access

def create_enrollment_session(
    phone_number: str,
    config: Optional[EnrollmentSessionConfig] = None
) -> EnrollmentSession:
    """Create a new enrollment session"""
    manager = get_enrollment_manager()
    return manager.create_session(phone_number, config)


def get_enrollment_session(session_id: str) -> Optional[EnrollmentSession]:
    """Get an enrollment session"""
    manager = get_enrollment_manager()
    return manager.get_session(session_id)


def add_audio_chunk(
    session_id: str,
    audio_data: np.ndarray,
    duration_seconds: float,
    sample_rate: int = 16000,
    quality_score: float = 1.0
) -> Tuple[bool, str, Optional[AudioChunkRecord]]:
    """
    Add audio chunk to an enrollment session
    
    Returns:
        Tuple of (success, message, chunk_record)
    """
    session = get_enrollment_session(session_id)
    
    if not session:
        return False, f"Session {session_id} not found", None
    
    try:
        chunk = session.add_chunk(audio_data, duration_seconds, sample_rate, quality_score)
        return True, f"Chunk added ({len(session.chunks)}/{session.config.max_chunks})", chunk
    except ValueError as e:
        return False, str(e), None


def finalize_enrollment(session_id: str, force_single: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Finalize an enrollment session
    
    Returns:
        Tuple of (success, message, vector_id)
    """
    session = get_enrollment_session(session_id)
    
    if not session:
        return False, f"Session {session_id} not found", None
    
    success, message, embedding = session.finalize_enrollment(force_single)
    
    # Get vector ID from database
    vector_id = None
    if success:
        enrollment_doc = get_voice_embedding(session.phone_number)
        if enrollment_doc:
            vector_id = enrollment_doc.get("_id")
    
    return success, message, vector_id

def merge_audio_chunks(session_id: str) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Merge audio chunks in an enrollment session
    
    Returns:
        Tuple of (success, message, merged_audio)
    """
    session = get_enrollment_session(session_id)
    
    if not session:
        return False, f"Session {session_id} not found", None
    
    try:
        success, message, merged_audio = session.merge_audio_chunks()
        return success, message, merged_audio
    except Exception as e:
        return False, f"Error merging audio: {str(e)}", None


def generate_embedding_from_merged_audio(session_id: str) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Generate embedding from merged audio in a session
    
    Returns:
        Tuple of (success, message, embedding)
    """
    session = get_enrollment_session(session_id)
    
    if not session:
        return False, f"Session {session_id} not found", None
    
    try:
        success, message, embedding = session.generate_embedding_from_merged_audio()
        return success, message, embedding
    except Exception as e:
        return False, f"Error generating embedding: {str(e)}", None


def merge_and_generate_embedding(session_id: str) -> Tuple[bool, str, Optional[np.ndarray]]:
    """
    Complete workflow: merge audio chunks and generate single embedding
    
    Returns:
        Tuple of (success, message, embedding)
    """
    session = get_enrollment_session(session_id)
    
    if not session:
        return False, f"Session {session_id} not found", None
    
    try:
        success, message, embedding = session.merge_and_generate_embedding()
        return success, message, embedding
    except Exception as e:
        return False, f"Error in merge and generate workflow: {str(e)}", None


# ============================================================================
# ENROLLMENT CONFIRMATION SERVICE
# ============================================================================

class EnrollmentConfirmationService:
    """
    Service for managing enrollment confirmations via WebSocket
    Sends confirmation messages to clients when enrollment is completed
    """
    
    def __init__(self):
        """Initialize the confirmation service"""
        self.session_clients: Dict[str, str] = {}  # Maps session_id to client_id
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}  # Pending confirmations
        self.sent_confirmations: List[Dict[str, Any]] = []  # History of sent confirmations
        self.connection_manager = None  # Will be set by main.py
        logger.info("Enrollment Confirmation Service initialized")
    
    def set_connection_manager(self, manager):
        """Set the WebSocket connection manager"""
        self.connection_manager = manager
        logger.info("Connection manager set for confirmation service")
    
    def register_session_client(self, session_id: str, client_id: str) -> bool:
        """
        Register a client for an enrollment session
        When enrollment completes, confirmation will be sent to this client
        
        Args:
            session_id: The enrollment session ID
            client_id: The WebSocket client ID
            
        Returns:
            True if registered successfully
        """
        self.session_clients[session_id] = client_id
        logger.info(f"Registered client {client_id} for session {session_id[:8]}")
        return True
    
    def unregister_session(self, session_id: str) -> bool:
        """Unregister a session (when it's cancelled)"""
        if session_id in self.session_clients:
            del self.session_clients[session_id]
            logger.info(f"Unregistered session {session_id[:8]}")
            return True
        return False
    
    async def send_enrollment_confirmation(
        self, 
        session_id: str,
        phone_number: str,
        vector_id: str,
        chunks_processed: int,
        success: bool = True,
        message: str = ""
    ) -> Tuple[bool, str]:
        """
        Send enrollment confirmation to the client
        
        Args:
            session_id: Enrollment session ID
            phone_number: Phone number that was enrolled
            vector_id: The embedding vector ID in the database
            chunks_processed: Number of chunks processed
            success: Whether enrollment was successful
            message: Additional message
            
        Returns:
            Tuple of (sent_successfully, confirmation_id)
        """
        if not self.connection_manager:
            logger.warning("Connection manager not set - cannot send confirmation")
            return False, ""
        
        client_id = self.session_clients.get(session_id)
        if not client_id:
            logger.warning(f"No client registered for session {session_id[:8]}")
            return False, ""
        
        connection = self.connection_manager.get_connection(client_id)
        if not connection:
            logger.warning(f"Client {client_id} not found in active connections")
            return False, ""
        
        try:
            confirmation_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            confirmation_message = {
                "type": "enrollment_confirmed",
                "status": "success" if success else "error",
                "confirmation_id": confirmation_id,
                "timestamp": timestamp,
                "data": {
                    "session_id": session_id,
                    "phone_number": phone_number,
                    "vector_id": vector_id,
                    "chunks_processed": chunks_processed,
                    "message": message or ("Enrollment completed successfully" if success else "Enrollment failed")
                }
            }
            
            # Send the confirmation
            success_sent = await connection.send_json(confirmation_message)
            
            if success_sent:
                # Record in history
                confirmation_record = {
                    "confirmation_id": confirmation_id,
                    "session_id": session_id,
                    "client_id": client_id,
                    "phone_number": phone_number,
                    "timestamp": timestamp,
                    "chunks_processed": chunks_processed
                }
                self.sent_confirmations.append(confirmation_record)
                
                # Clean up
                self.unregister_session(session_id)
                
                logger.info(
                    f"✓ Sent enrollment confirmation {confirmation_id[:8]} "
                    f"to client {client_id[:8]} for session {session_id[:8]}"
                )
                
                return True, confirmation_id
            else:
                logger.error(f"Failed to send confirmation to client {client_id}")
                return False, ""
        
        except Exception as e:
            logger.error(f"Error sending confirmation: {str(e)}")
            return False, ""
    
    def get_confirmation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of sent confirmations"""
        return self.sent_confirmations[-limit:]
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get registration info for a session"""
        if session_id in self.session_clients:
            return {
                "session_id": session_id,
                "client_id": self.session_clients[session_id],
                "has_pending": session_id in self.pending_confirmations
            }
        return None
    
    def cleanup_expired_registrations(self, max_age_seconds: int = 3600) -> int:
        """Clean up old registrations"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        count = 0
        
        # Note: In a production system, you'd track registration times
        # For now, we just clean up sessions that no longer exist
        sessions_to_remove = []
        for session_id in self.session_clients:
            if get_enrollment_session(session_id) is None:
                sessions_to_remove.append(session_id)
                count += 1
        
        for session_id in sessions_to_remove:
            del self.session_clients[session_id]
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired confirmation registrations")
        
        return count


# Global confirmation service instance
confirmation_service = EnrollmentConfirmationService()


def get_confirmation_service() -> EnrollmentConfirmationService:
    """Get the global confirmation service"""
    return confirmation_service