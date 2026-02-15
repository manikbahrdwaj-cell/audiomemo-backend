"""
MongoDB-Backed Enrollment Service
Persists enrollment sessions and audio chunks to MongoDB
Extends the in-memory enrollment service with database persistence
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import numpy as np
from dataclasses import asdict

from enrollment_service import (
    EnrollmentSession,
    EnrollmentStatus,
    AudioChunkRecord,
    EnrollmentSessionConfig,
    EnrollmentServiceManager,
    get_enrollment_manager
)
from database import (
    save_enrollment_session,
    get_enrollment_session as db_get_enrollment_session,
    update_enrollment_session,
    delete_enrollment_session,
    get_enrollment_sessions_for_phone,
    get_active_enrollment_sessions,
    cleanup_expired_enrollment_sessions,
    save_audio_chunk,
    get_audio_chunks_for_session,
    save_enrollment_history,
    get_enrollment_history_for_phone,
    get_recent_enrollments,
    get_enrollment_stats,
    get_voice_embedding
)

logger = logging.getLogger(__name__)


class MongoDBEnrollmentService:
    """
    MongoDB-backed enrollment service
    
    Features:
    - Persist enrollment sessions to MongoDB
    - Track audio chunks in database
    - Maintain enrollment history
    - Session recovery from database
    - Automatic session cleanup
    """
    
    def __init__(self):
        """Initialize the MongoDB enrollment service"""
        self.in_memory_manager = get_enrollment_manager()
        logger.info("MongoDB Enrollment Service initialized")
    
    def create_session(
        self,
        phone_number: str,
        config: Optional[EnrollmentSessionConfig] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create and persist a new enrollment session
        
        Args:
            phone_number: Phone number for enrollment
            config: Optional session configuration
            
        Returns:
            Tuple of (session_id, session_data)
        """
        # Create in-memory session using existing manager
        session = self.in_memory_manager.create_session(phone_number, config)
        
        # Persist to MongoDB
        session_data = self._serialize_session(session)
        doc_id = save_enrollment_session(session_data)
        
        logger.info(
            f"Created and persisted enrollment session {session.session_id[:8]} "
            f"for {phone_number}"
        )
        
        return session.session_id, session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session from database
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session data or None if not found
        """
        session_data = db_get_enrollment_session(session_id)
        
        if session_data:
            logger.info(f"Retrieved session {session_id[:8]} from database")
        else:
            logger.warning(f"Session {session_id[:8]} not found in database")
        
        return session_data
    
    def add_audio_chunk(
        self,
        session_id: str,
        audio_data: np.ndarray,
        duration_seconds: float,
        sample_rate: int = 16000,
        quality_score: float = 1.0
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Add audio chunk to session and persist
        
        Args:
            session_id: Session ID
            audio_data: Audio samples as numpy array
            duration_seconds: Duration of audio in seconds
            sample_rate: Sample rate of audio
            quality_score: Quality confidence score
            
        Returns:
            Tuple of (success, message, chunk_id)
        """
        # Get session from in-memory manager
        session = self.in_memory_manager.get_session(session_id)
        
        if not session:
            error_msg = f"Session {session_id} not found"
            logger.error(error_msg)
            return False, error_msg, None
        
        try:
            # Add chunk to in-memory session
            chunk = session.add_chunk(
                audio_data,
                duration_seconds,
                sample_rate,
                quality_score
            )
            
            # Persist chunk metadata to database (not audio_data due to size)
            chunk_data = {
                "chunk_id": chunk.chunk_id,
                "session_id": session_id,
                "phone_number": session.phone_number,
                "timestamp": chunk.timestamp.isoformat(),
                "duration_seconds": chunk.duration_seconds,
                "sample_rate": chunk.sample_rate,
                "audio_data": audio_data,  # Will be filtered out by save_audio_chunk
                "quality_score": chunk.quality_score,
                "audio_samples": len(audio_data) if audio_data is not None else 0,
                "audio_data_size": audio_data.nbytes if audio_data is not None else 0
            }
            
            chunk_db_id = save_audio_chunk(chunk_data)
            
            # Update session in database
            update_enrollment_session(session_id, {
                "chunks_collected": len(session.chunks),
                "status": session.status.value,
                "last_chunk_at": datetime.utcnow().isoformat()
            })
            
            success_msg = (
                f"Chunk added ({len(session.chunks)}/{session.config.max_chunks}) "
                f"and persisted to database"
            )
            
            logger.info(f"Session {session_id[:8]}: {success_msg}")
            
            return True, success_msg, chunk.chunk_id
            
        except Exception as e:
            error_msg = f"Error adding audio chunk: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def finalize_enrollment(
        self,
        session_id: str,
        force_single: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Finalize enrollment and persist result
        
        Args:
            session_id: Session ID to finalize
            force_single: Use single best embedding if merge fails
            
        Returns:
            Tuple of (success, message, vector_id)
        """
        # Get session from in-memory manager
        session = self.in_memory_manager.get_session(session_id)
        
        if not session:
            error_msg = f"Session {session_id} not found"
            logger.error(error_msg)
            return False, error_msg, None
        
        try:
            # Finalize using existing session method
            success, message, embedding = session.finalize_enrollment(force_single)
            
            # Get vector ID if successful
            vector_id = None
            if success:
                embedding_doc = get_voice_embedding(session.phone_number)
                if embedding_doc:
                    vector_id = embedding_doc.get("_id")
            
            # Save enrollment history
            history_data = {
                "session_id": session_id,
                "phone_number": session.phone_number,
                "status": session.status.value,
                "chunks_collected": len(session.chunks),
                "embeddings_generated": len(session.embeddings),
                "merge_strategy": "audio_merge" if session.config.merge_audio else "embedding_merge",
                "vector_id": vector_id,
                "completed_at": datetime.utcnow().isoformat(),
                "duration_seconds": (datetime.utcnow() - session.created_at).total_seconds()
                    if session.completed_at else None,
                "error_message": session.error_message
            }
            
            history_id = save_enrollment_history(history_data)
            
            # Update session status in database
            update_enrollment_session(session_id, {
                "status": session.status.value,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "embeddings_generated": len(session.embeddings),
                "vector_id": vector_id,
                "merged_embedding_available": session.merged_embedding is not None,
                "error_message": session.error_message
            })
            
            if success:
                logger.info(
                    f"✓ Enrollment finalized for session {session_id[:8]} ({session.phone_number}). "
                    f"Vector ID: {vector_id[:8] if vector_id else 'N/A'}. "
                    f"History ID: {history_id[:8]}"
                )
            else:
                logger.error(f"Enrollment finalization failed: {message}")
            
            return success, message, vector_id
            
        except Exception as e:
            error_msg = f"Error finalizing enrollment: {str(e)}"
            logger.error(error_msg)
            
            # Update session with error
            update_enrollment_session(session_id, {
                "status": EnrollmentStatus.ERROR.value,
                "error_message": error_msg
            })
            
            return False, error_msg, None
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive session summary
        
        Args:
            session_id: Session ID
            
        Returns:
            Session summary or None if not found
        """
        session_data = self.get_session(session_id)
        
        if not session_data:
            return None
        
        # Get audio chunks
        chunks = get_audio_chunks_for_session(session_id)
        
        return {
            **session_data,
            "chunks": chunks,
            "chunk_stats": {
                "total_saved": len(chunks),
                "total_samples": sum(c.get("audio_samples", 0) for c in chunks),
                "total_duration_seconds": sum(c.get("duration_seconds", 0) for c in chunks)
            }
        }
    
    def get_sessions_for_phone(
        self,
        phone_number: str,
        limit: int = 10,
        include_chunks: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all enrollment sessions for a phone number
        
        Args:
            phone_number: Phone number to search
            limit: Maximum sessions to return
            include_chunks: Include audio chunk details
            
        Returns:
            List of session summaries
        """
        sessions = get_enrollment_sessions_for_phone(phone_number, limit)
        
        if include_chunks:
            for session in sessions:
                session["chunks"] = get_audio_chunks_for_session(session["session_id"])
        
        logger.info(f"Retrieved {len(sessions)} sessions for phone {phone_number}")
        
        return sessions
    
    def get_active_sessions(
        self,
        phone_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active enrollment sessions
        
        Args:
            phone_number: Optional filter by phone number
            
        Returns:
            List of active sessions
        """
        sessions = get_active_enrollment_sessions(phone_number)
        logger.info(f"Retrieved {len(sessions)} active enrollment sessions")
        return sessions
    
    def get_enrollment_history(
        self,
        phone_number: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get enrollment history for a phone number
        
        Args:
            phone_number: Phone number to search
            limit: Maximum records to return
            
        Returns:
            List of enrollment history records
        """
        history = get_enrollment_history_for_phone(phone_number, limit)
        logger.info(f"Retrieved {len(history)} enrollment records for phone {phone_number}")
        return history
    
    def get_recent_enrollments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent enrollment completions
        
        Args:
            limit: Maximum records to return
            
        Returns:
            List of recent enrollments
        """
        enrollments = get_recent_enrollments(limit)
        logger.info(f"Retrieved {len(enrollments)} recent enrollment completions")
        return enrollments
    
    def get_stats(self, phone_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Get enrollment statistics
        
        Args:
            phone_number: Optional filter by phone number
            
        Returns:
            Dictionary with statistics
        """
        stats = get_enrollment_stats(phone_number)
        logger.info(f"Generated enrollment statistics: {stats}")
        return stats
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired sessions from database
        
        Args:
            max_age_seconds: Maximum session age
            
        Returns:
            Number of sessions cleaned up
        """
        count = cleanup_expired_enrollment_sessions(max_age_seconds)
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired enrollment sessions")
        
        return count
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete an enrollment session
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if successful
        """
        # Remove from in-memory manager
        self.in_memory_manager.remove_session(session_id)
        
        # Delete from database
        success = delete_enrollment_session(session_id)
        
        if success:
            logger.info(f"Deleted enrollment session {session_id[:8]}")
        
        return success
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _serialize_session(session: EnrollmentSession) -> Dict[str, Any]:
        """
        Serialize an EnrollmentSession to a dictionary for MongoDB storage
        
        Args:
            session: EnrollmentSession to serialize
            
        Returns:
            Dictionary representation
        """
        return {
            "session_id": session.session_id,
            "phone_number": session.phone_number,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "chunks_collected": len(session.chunks),
            "max_chunks": session.config.max_chunks,
            "embeddings_generated": len(session.embeddings),
            "min_chunks_required": session.config.min_chunks_required,
            "auto_process": session.config.auto_process,
            "merge_embeddings": session.config.merge_embeddings,
            "merge_mode": session.config.merge_mode.value,
            "quality_threshold": session.config.quality_threshold,
            "merge_audio": session.config.merge_audio,
            "audio_merge_mode": session.config.audio_merge_mode.value,
            "audio_merge_crossfade_ms": session.config.audio_merge_crossfade_ms,
            "has_merged_embedding": session.merged_embedding is not None,
            "has_merged_audio": session.merged_audio is not None,
            "merged_audio_duration_seconds": (
                len(session.merged_audio) / session.merged_audio_sample_rate
                if session.merged_audio is not None else None
            ),
            "error_message": session.error_message
        }


# Global MongoDB enrollment service instance
_mongodb_service: Optional[MongoDBEnrollmentService] = None


def get_mongodb_enrollment_service() -> MongoDBEnrollmentService:
    """
    Get or create the global MongoDB enrollment service
    
    Returns:
        MongoDBEnrollmentService instance
    """
    global _mongodb_service
    
    if _mongodb_service is None:
        _mongodb_service = MongoDBEnrollmentService()
    
    return _mongodb_service


# Convenience functions

def create_enrollment_session(
    phone_number: str,
    config: Optional[EnrollmentSessionConfig] = None
) -> Tuple[str, Dict[str, Any]]:
    """Create and persist an enrollment session"""
    service = get_mongodb_enrollment_service()
    return service.create_session(phone_number, config)


def get_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
    """Get enrollment session summary"""
    service = get_mongodb_enrollment_service()
    return service.get_session_summary(session_id)


def add_audio_chunk(
    session_id: str,
    audio_data: np.ndarray,
    duration_seconds: float,
    sample_rate: int = 16000,
    quality_score: float = 1.0
) -> Tuple[bool, str, Optional[str]]:
    """Add audio chunk to session and persist"""
    service = get_mongodb_enrollment_service()
    return service.add_audio_chunk(
        session_id,
        audio_data,
        duration_seconds,
        sample_rate,
        quality_score
    )


def finalize_enrollment(session_id: str, force_single: bool = False) -> Tuple[bool, str, Optional[str]]:
    """Finalize enrollment and persist result"""
    service = get_mongodb_enrollment_service()
    return service.finalize_enrollment(session_id, force_single)


def get_enrollment_history(phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get enrollment history for a phone number"""
    service = get_mongodb_enrollment_service()
    return service.get_enrollment_history(phone_number, limit)


def get_recent_completions(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent enrollment completions"""
    service = get_mongodb_enrollment_service()
    return service.get_recent_enrollments(limit)


def get_enrollment_statistics(phone_number: Optional[str] = None) -> Dict[str, Any]:
    """Get enrollment statistics"""
    service = get_mongodb_enrollment_service()
    return service.get_stats(phone_number)
