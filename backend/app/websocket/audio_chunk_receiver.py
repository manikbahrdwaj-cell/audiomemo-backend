"""
Audio Chunk Receiver and Merger Service
Receives audio chunks from WebSocket, buffers them, merges into seamless audio,
and generates single embedding from combined audio
"""

import numpy as np
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from app.ml.chunking import AudioChunker, ChunkConfig
from app.ml.embedding import generate_embedding

logger = logging.getLogger(__name__)


class ChunkReceiverStatus(Enum):
    """Status of chunk receiving session"""
    CREATED = "created"
    ACTIVE = "active"
    RECEIVING_CHUNKS = "receiving_chunks"
    MERGING = "merging"
    GENERATING_EMBEDDING = "generating_embedding"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ReceivedChunk:
    """Record of a received audio chunk"""
    chunk_id: str
    chunk_number: int
    audio_data: np.ndarray  # Audio samples
    sample_rate: int = 16000
    duration_ms: float = 0.0
    received_at: datetime = field(default_factory=datetime.utcnow)
    is_valid: bool = True
    error: Optional[str] = None
    
    def __repr__(self) -> str:
        return (
            f"ReceivedChunk(#{self.chunk_number}, "
            f"samples={len(self.audio_data)}, "
            f"duration={self.duration_ms:.0f}ms, "
            f"valid={self.is_valid})"
        )


@dataclass
class ChunkReceiverSession:
    """Session for receiving and merging audio chunks"""
    session_id: str
    phone_number: str
    mode: str  # 'enrollment' or 'verification'
    status: ChunkReceiverStatus = ChunkReceiverStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Chunk tracking
    chunks_received: List[ReceivedChunk] = field(default_factory=list)
    chunks_expected: Optional[int] = None
    
    # Merged result
    merged_audio: Optional[np.ndarray] = None
    merged_sample_rate: int = 16000
    merged_duration_ms: float = 0.0
    
    # Embedding result
    embedding: Optional[np.ndarray] = None
    embedding_dim: int = 0
    
    # Metadata
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    
    def __repr__(self) -> str:
        return (
            f"ChunkReceiverSession(id={self.session_id[:8]}, "
            f"phone={self.phone_number}, "
            f"mode={self.mode}, "
            f"chunks={len(self.chunks_received)}, "
            f"status={self.status.value})"
        )


class AudioChunkReceiver:
    """
    Receives audio chunks from WebSocket connections
    Buffers them and provides merging functionality
    """
    
    def __init__(self):
        """Initialize chunk receiver"""
        self.sessions: Dict[str, ChunkReceiverSession] = {}
        self.chunker = AudioChunker()
        
        logger.info("AudioChunkReceiver initialized")
    
    def create_session(
        self,
        phone_number: str,
        mode: str = 'enrollment',
        chunks_expected: Optional[int] = None
    ) -> ChunkReceiverSession:
        """
        Create a new chunk receiving session
        
        Args:
            phone_number: User's phone number
            mode: 'enrollment' or 'verification'
            chunks_expected: Expected number of chunks (optional)
            
        Returns:
            ChunkReceiverSession instance
        """
        session_id = str(uuid.uuid4())
        session = ChunkReceiverSession(
            session_id=session_id,
            phone_number=phone_number,
            mode=mode,
            chunks_expected=chunks_expected
        )
        
        self.sessions[session_id] = session
        logger.info(
            f"Created chunk receiver session: {session_id} "
            f"({phone_number}, {mode})"
        )
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ChunkReceiverSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def add_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        duration_ms: float = 0.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Add a received chunk to session
        
        Args:
            session_id: Session identifier
            chunk_number: Chunk sequence number
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate (default 16000 Hz)
            duration_ms: Duration in milliseconds
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        session = self.get_session(session_id)
        if not session:
            return False, f"Session {session_id} not found"
        
        try:
            if session.status == ChunkReceiverStatus.COMPLETED:
                return False, "Session already completed"
            
            # Update status if first chunk
            if session.status == ChunkReceiverStatus.CREATED:
                session.status = ChunkReceiverStatus.ACTIVE
                session.started_at = datetime.utcnow()
            
            # Validate audio data
            if not isinstance(audio_data, np.ndarray):
                return False, "Audio data must be numpy array"
            
            if audio_data.ndim != 1:
                return False, f"Expected 1D audio, got shape {audio_data.shape}"
            
            if len(audio_data) == 0:
                return False, "Empty audio data"
            
            if sample_rate != 16000:
                logger.warning(f"Unexpected sample rate: {sample_rate}")
            
            # Create chunk record
            chunk = ReceivedChunk(
                chunk_id=f"{session_id}_{chunk_number}",
                chunk_number=chunk_number,
                audio_data=audio_data,
                sample_rate=sample_rate,
                duration_ms=duration_ms or len(audio_data) / sample_rate * 1000
            )
            
            session.chunks_received.append(chunk)
            session.status = ChunkReceiverStatus.RECEIVING_CHUNKS
            
            logger.debug(
                f"Added chunk #{chunk_number} to session {session_id}: "
                f"{len(audio_data)} samples, {chunk.duration_ms:.0f}ms"
            )
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error adding chunk: {str(e)}"
            logger.error(error_msg)
            session.error_message = error_msg
            session.status = ChunkReceiverStatus.ERROR
            return False, error_msg
    
    def merge_chunks(self, session_id: str) -> Tuple[bool, Optional[np.ndarray], Optional[str]]:
        """
        Merge all received chunks into single audio array
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (success: bool, merged_audio: Optional[np.ndarray], error: Optional[str])
        """
        session = self.get_session(session_id)
        if not session:
            return False, None, f"Session {session_id} not found"
        
        try:
            session.status = ChunkReceiverStatus.MERGING
            
            if not session.chunks_received:
                error = "No chunks received"
                session.error_message = error
                session.status = ChunkReceiverStatus.ERROR
                return False, None, error
            
            logger.info(
                f"Merging {len(session.chunks_received)} chunks "
                f"from session {session_id}"
            )
            
            # Sort chunks by chunk number to ensure correct order
            sorted_chunks = sorted(
                session.chunks_received,
                key=lambda x: x.chunk_number
            )
            
            # Concatenate all audio chunks
            audio_arrays = [chunk.audio_data for chunk in sorted_chunks]
            merged_audio = np.concatenate(audio_arrays)
            
            # Store result
            session.merged_audio = merged_audio
            session.merged_sample_rate = 16000
            session.merged_duration_ms = len(merged_audio) / 16000 * 1000
            
            logger.info(
                f"Merged audio: {len(merged_audio)} samples, "
                f"{session.merged_duration_ms:.0f}ms"
            )
            
            return True, merged_audio, None
            
        except Exception as e:
            error_msg = f"Error merging chunks: {str(e)}"
            logger.error(error_msg, exc_info=True)
            session.error_message = error_msg
            session.status = ChunkReceiverStatus.ERROR
            return False, None, error_msg
    
    def generate_embedding(self, session_id: str) -> Tuple[bool, Optional[np.ndarray], Optional[str]]:
        """
        Generate single embedding from merged audio
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (success: bool, embedding: Optional[np.ndarray], error: Optional[str])
        """
        session = self.get_session(session_id)
        if not session:
            return False, None, f"Session {session_id} not found"
        
        try:
            session.status = ChunkReceiverStatus.GENERATING_EMBEDDING
            
            # Merge chunks if not already done
            if session.merged_audio is None:
                success, merged, error = self.merge_chunks(session_id)
                if not success:
                    return False, None, error
            
            logger.info(
                f"Generating embedding from {len(session.merged_audio)} samples "
                f"({session.merged_duration_ms:.0f}ms)"
            )
            
            # Generate embedding from merged audio
            embedding = generate_embedding(session.merged_audio)
            
            if embedding is None:
                error = "Failed to generate embedding"
                session.error_message = error
                session.status = ChunkReceiverStatus.ERROR
                return False, None, error
            
            # Store result
            session.embedding = embedding
            session.embedding_dim = len(embedding) if hasattr(embedding, '__len__') else 1
            session.status = ChunkReceiverStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            
            # Calculate processing time
            session.processing_time_ms = (
                (session.completed_at - session.created_at).total_seconds() * 1000
            )
            
            logger.info(
                f"Embedding generated: shape={embedding.shape}, "
                f"processing_time={session.processing_time_ms:.0f}ms"
            )
            
            return True, embedding, None
            
        except Exception as e:
            error_msg = f"Error generating embedding: {str(e)}"
            logger.error(error_msg, exc_info=True)
            session.error_message = error_msg
            session.status = ChunkReceiverStatus.ERROR
            return False, None, error_msg
    
    def process_session(self, session_id: str) -> Tuple[bool, Optional[np.ndarray], Optional[str]]:
        """
        Complete workflow: merge chunks and generate embedding
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (success: bool, embedding: Optional[np.ndarray], error: Optional[str])
        """
        success, embedding, error = self.generate_embedding(session_id)
        return success, embedding, error
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information as dictionary"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "phone_number": session.phone_number,
            "mode": session.mode,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "chunks_received": len(session.chunks_received),
            "chunks_expected": session.chunks_expected,
            "merged_duration_ms": session.merged_duration_ms,
            "embedding_dim": session.embedding_dim,
            "processing_time_ms": session.processing_time_ms,
            "error": session.error_message,
            "chunks": [
                {
                    "chunk_number": chunk.chunk_number,
                    "samples": len(chunk.audio_data),
                    "duration_ms": chunk.duration_ms,
                    "valid": chunk.is_valid,
                }
                for chunk in session.chunks_received
            ],
        }
    
    def cleanup_session(self, session_id: str) -> bool:
        """Clean up session and free memory"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions.pop(session_id)
        logger.info(f"Cleaned up session {session_id}")
        return True
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old completed sessions
        
        Args:
            max_age_seconds: Sessions older than this are cleaned up
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        sessions_to_remove = []
        
        for session_id, session in self.sessions.items():
            if session.completed_at is None:
                continue
            
            age_seconds = (now - session.completed_at).total_seconds()
            if age_seconds > max_age_seconds:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.cleanup_session(session_id)
        
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
        return len(sessions_to_remove)
    
    def get_stats(self) -> Dict:
        """Get receiver statistics"""
        total_sessions = len(self.sessions)
        active_sessions = sum(
            1 for s in self.sessions.values()
            if s.status != ChunkReceiverStatus.COMPLETED
        )
        completed_sessions = sum(
            1 for s in self.sessions.values()
            if s.status == ChunkReceiverStatus.COMPLETED
        )
        error_sessions = sum(
            1 for s in self.sessions.values()
            if s.status == ChunkReceiverStatus.ERROR
        )
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "error_sessions": error_sessions,
        }


# Global instance
_chunk_receiver = None


def get_chunk_receiver() -> AudioChunkReceiver:
    """Get or create global chunk receiver instance"""
    global _chunk_receiver
    if _chunk_receiver is None:
        _chunk_receiver = AudioChunkReceiver()
    return _chunk_receiver
