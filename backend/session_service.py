"""
Session Service Module
Manages verified session creation and LangChain session integration
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from langchain_session_service import (
    get_langchain_session_manager,
    LangChainSession,
    LangChainSessionManager
)

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Status of a verified session"""
    CREATED = "created"
    VERIFIED = "verified"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class VerifiedSession:
    """Represents a verified session after successful voice authentication"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str = ""
    verification_score: float = 0.0
    session_status: str = SessionStatus.VERIFIED.value
    created_at: datetime = field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # LangChain integration
    langgraph_session_id: Optional[str] = None  # Reference to LangChain session
    
    # Verification details
    embedded_phone_number: Optional[str] = None  # The embedded phone number used for comparison
    similarity_score: float = 0.0
    cosine_similarity: float = 0.0
    cosine_distance: float = 0.0
    euclidean_distance: float = 0.0
    correlation_distance: Optional[float] = None
    confidence: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "verification_score": self.verification_score,
            "session_status": self.session_status,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
            "expires_at": self.expires_at,
            "langgraph_session_id": self.langgraph_session_id,
            "embedded_phone_number": self.embedded_phone_number,
            "similarity_score": self.similarity_score,
            "cosine_similarity": self.cosine_similarity,
            "cosine_distance": self.cosine_distance,
            "euclidean_distance": self.euclidean_distance,
            "correlation_distance": self.correlation_distance,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class VerifiedSessionManager:
    """Manager for creating and managing verified sessions"""
    
    def __init__(self, session_timeout_seconds: int = 3600):
        """
        Initialize VerifiedSessionManager
        
        Args:
            session_timeout_seconds: How long sessions remain valid (default 1 hour)
        """
        self.session_timeout_seconds = session_timeout_seconds
        self.sessions: Dict[str, VerifiedSession] = {}
    
    def create_verified_session(
        self,
        phone_number: str,
        verification_score: float,
        similarity_metrics: Dict[str, Any]
    ) -> VerifiedSession:
        """
        Create a new verified session after successful voice authentication
        
        Args:
            phone_number: The matched phone number
            verification_score: The similarity score (0-1)
            similarity_metrics: Dictionary with similarity metrics
            
        Returns:
            VerifiedSession instance
        """
        session = VerifiedSession(
            session_id=str(uuid.uuid4()),
            phone_number=phone_number,
            verification_score=verification_score,
            session_status=SessionStatus.VERIFIED.value,
            created_at=datetime.utcnow(),
            verified_at=datetime.utcnow(),
            similarity_score=verification_score,
            cosine_similarity=similarity_metrics.get("cosine_similarity", 0.0),
            cosine_distance=similarity_metrics.get("cosine_distance", 0.0),
            euclidean_distance=similarity_metrics.get("euclidean_distance", 0.0),
            correlation_distance=similarity_metrics.get("correlation_distance"),
            confidence=similarity_metrics.get("confidence", 0.0)
        )
        
        # Store in memory cache
        self.sessions[session.session_id] = session
        
        logger.info(
            f"Created verified session {session.session_id[:8]} "
            f"for phone {phone_number} with score {verification_score:.4f}"
        )
        
        return session
    
    def create_langgraph_session(self, verified_session: VerifiedSession) -> str:
        """
        Create a LangChain/LangGraph session for the verified user
        
        Args:
            verified_session: The verified session
            
        Returns:
            LangGraph session ID
        """
        try:
            # Get LangChain session manager
            lc_manager = get_langchain_session_manager()
            
            # Create LangChain session with verification details
            lc_session = lc_manager.create_session(
                phone_number=verified_session.phone_number,
                verification_score=verified_session.verification_score,
                session_status="active",
                custom_metadata={
                    "voice_verified": True,
                    "verification_timestamp": verified_session.verified_at.isoformat() if verified_session.verified_at else None,
                    "initial_verification_score": verified_session.verification_score,
                    "cosine_similarity": verified_session.cosine_similarity,
                    "confidence": verified_session.confidence
                }
            )
            
            # Update verified session with LangChain session ID
            verified_session.langgraph_session_id = lc_session.metadata.session_id
            verified_session.session_status = SessionStatus.ACTIVE.value
            
            logger.info(
                f"Created LangChain session {lc_session.metadata.session_id[:16]} "
                f"(thread: {lc_session.metadata.langgraph_thread_id[:16]}) "
                f"for verified session {verified_session.session_id[:8]}"
            )
            
            return lc_session.metadata.session_id
        
        except Exception as e:
            logger.error(f"Error creating LangChain session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[VerifiedSession]:
        """
        Retrieve a verified session by ID
        
        Args:
            session_id: The session ID
            
        Returns:
            VerifiedSession or None if not found
        """
        return self.sessions.get(session_id)
    
    def is_session_valid(self, session_id: str) -> bool:
        """
        Check if a session is still valid
        
        Args:
            session_id: The session ID
            
        Returns:
            True if session is valid and not expired
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session.session_status == SessionStatus.EXPIRED.value:
            return False
        
        if session.session_status == SessionStatus.REVOKED.value:
            return False
        
        return True
    
    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a verified session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if revoked, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.session_status = SessionStatus.REVOKED.value
        logger.info(f"Revoked verified session {session_id[:8]}")
        return True
    
    def clear_expired_sessions(self) -> int:
        """
        Clear expired sessions
        
        Returns:
            Number of sessions cleared
        """
        now = datetime.utcnow()
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if session.expires_at and session.expires_at < now
        ]
        
        for sid in expired_sessions:
            del self.sessions[sid]
        
        if expired_sessions:
            logger.info(f"Cleared {len(expired_sessions)} expired verified sessions")
        
        return len(expired_sessions)


# Global instance
_verified_session_manager: Optional[VerifiedSessionManager] = None


def get_verified_session_manager() -> VerifiedSessionManager:
    """Get or create global VerifiedSessionManager instance"""
    global _verified_session_manager
    
    if _verified_session_manager is None:
        _verified_session_manager = VerifiedSessionManager()
        logger.info("Initialized global VerifiedSessionManager")
    
    return _verified_session_manager
