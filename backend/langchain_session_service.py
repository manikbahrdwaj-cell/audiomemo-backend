"""
LangChain Session Service Module
Manages LangChain/LangGraph sessions for voice-authenticated users
Integrates with MongoDB for persistent session storage
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from langchain_core.runnables import RunnableConfig
import json

logger = logging.getLogger(__name__)


class RunnableConfigWrapper:
    """
    Wrapper for RunnableConfig that provides attribute access to configurable dict
    """
    def __init__(self, config: RunnableConfig):
        """Initialize wrapper with RunnableConfig"""
        self._config = config
        self.configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    
    def __getitem__(self, key):
        """Support dict-like access"""
        return self._config[key]
    
    def get(self, key, default=None):
        """Support dict-like get"""
        return self._config.get(key, default)
    
    def __repr__(self):
        return repr(self._config)


class LangChainSessionStatus(Enum):
    """Status of a LangChain session"""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"
    TERMINATED = "terminated"


@dataclass
class LangChainSessionMetadata:
    """Metadata for LangChain session"""
    session_id: str = field(default_factory=lambda: f"lg_session_{uuid.uuid4()}")
    phone_number: str = ""
    verification_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_status: str = LangChainSessionStatus.CREATED.value
    langgraph_thread_id: str = field(default_factory=lambda: f"thread_{uuid.uuid4()}")
    
    # Session configuration
    ttl_seconds: int = 3600  # 1 hour default
    max_turns: int = 100  # Maximum conversation turns
    current_turn: int = 0
    
    # Authentication details
    voice_verified: bool = True
    verification_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Session history
    conversation_history: list = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # Custom metadata
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "verification_score": self.verification_score,
            "timestamp": self.timestamp,
            "session_status": self.session_status,
            "langgraph_thread_id": self.langgraph_thread_id,
            "ttl_seconds": self.ttl_seconds,
            "max_turns": self.max_turns,
            "current_turn": self.current_turn,
            "voice_verified": self.voice_verified,
            "verification_timestamp": self.verification_timestamp,
            "conversation_history": self.conversation_history,
            "start_time": self.start_time,
            "last_activity": self.last_activity,
            "end_time": self.end_time,
            "custom_metadata": self.custom_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LangChainSessionMetadata":
        """Create instance from dictionary"""
        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


@dataclass
class LangChainSession:
    """Complete LangChain session for voice-authenticated user"""
    metadata: LangChainSessionMetadata = field(default_factory=LangChainSessionMetadata)
    config: Optional[RunnableConfig] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "config": dict(self.config) if self.config else None
        }


class LangChainSessionManager:
    """Manager for creating and managing LangChain sessions"""
    
    def __init__(self, default_ttl_seconds: int = 3600):
        """
        Initialize LangChainSessionManager
        
        Args:
            default_ttl_seconds: Default time-to-live for sessions (1 hour)
        """
        self.default_ttl_seconds = default_ttl_seconds
        self.sessions: Dict[str, LangChainSession] = {}
        logger.info(f"Initialized LangChainSessionManager with TTL={default_ttl_seconds}s")
    
    def create_session(
        self,
        phone_number: str,
        verification_score: float,
        session_status: str = LangChainSessionStatus.ACTIVE.value,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> LangChainSession:
        """
        Create a new LangChain session after voice verification
        
        Args:
            phone_number: Verified phone number
            verification_score: Voice similarity score (0-1)
            session_status: Initial session status
            custom_metadata: Optional custom metadata
            
        Returns:
            LangChainSession instance
        """
        try:
            # Create session metadata
            metadata = LangChainSessionMetadata(
                session_id=f"lg_session_{uuid.uuid4()}",
                phone_number=phone_number,
                verification_score=verification_score,
                timestamp=datetime.utcnow(),
                session_status=session_status,
                langgraph_thread_id=f"thread_{uuid.uuid4()}",
                ttl_seconds=self.default_ttl_seconds,
                voice_verified=True,
                verification_timestamp=datetime.utcnow(),
                custom_metadata=custom_metadata or {}
            )
            
            # Create Runnable config for LangChain
            config = RunnableConfig(
                configurable={
                    "session_id": metadata.session_id,
                    "phone_number": phone_number,
                    "thread_id": metadata.langgraph_thread_id,
                    "user_id": phone_number,
                }
            )
            
            # Create session instance
            session = LangChainSession(
                metadata=metadata,
                config=config
            )
            
            # Store in memory cache
            self.sessions[metadata.session_id] = session
            
            logger.info(
                f"✓ Created LangChain session {metadata.session_id[:16]} "
                f"for {phone_number} "
                f"(thread: {metadata.langgraph_thread_id[:16]})"
            )
            
            return session
        
        except Exception as e:
            logger.error(f"Failed to create LangChain session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[LangChainSession]:
        """
        Retrieve a LangChain session by ID
        
        Args:
            session_id: The session ID
            
        Returns:
            LangChainSession or None if not found
        """
        return self.sessions.get(session_id)
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Update last activity timestamp for a session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if updated, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.metadata.last_activity = datetime.utcnow()
        logger.debug(f"Updated activity for session {session_id[:16]}")
        return True
    
    def add_conversation_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a conversation turn to session history
        
        Args:
            session_id: The session ID
            role: Role of speaker ("user" or "assistant")
            content: Message content
            metadata: Optional metadata about the turn
            
        Returns:
            True if added, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id[:16]} not found for conversation turn")
            return False
        
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "turn_number": session.metadata.current_turn + 1,
            "metadata": metadata or {}
        }
        
        session.metadata.conversation_history.append(turn)
        session.metadata.current_turn += 1
        session.metadata.last_activity = datetime.utcnow()
        
        logger.debug(
            f"Added conversation turn to session {session_id[:16]} "
            f"(turn #{session.metadata.current_turn})"
        )
        
        return True
    
    def is_session_valid(self, session_id: str) -> bool:
        """
        Check if a session is still valid (not expired/terminated)
        
        Args:
            session_id: The session ID
            
        Returns:
            True if session is valid
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Check status
        if session.metadata.session_status in [
            LangChainSessionStatus.EXPIRED.value,
            LangChainSessionStatus.TERMINATED.value
        ]:
            return False
        
        # Check expiration
        elapsed = (datetime.utcnow() - session.metadata.start_time).total_seconds()
        if elapsed > session.metadata.ttl_seconds:
            session.metadata.session_status = LangChainSessionStatus.EXPIRED.value
            session.metadata.end_time = datetime.utcnow()
            logger.info(f"Session {session_id[:16]} expired after {elapsed}s")
            return False
        
        return True
    
    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if terminated, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.metadata.session_status = LangChainSessionStatus.TERMINATED.value
        session.metadata.end_time = datetime.utcnow()
        
        logger.info(
            f"Terminated LangChain session {session_id[:16]} "
            f"(turns: {session.metadata.current_turn})"
        )
        
        return True
    
    def pause_session(self, session_id: str) -> bool:
        """
        Pause a session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if paused, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.metadata.session_status = LangChainSessionStatus.PAUSED.value
        logger.info(f"Paused LangChain session {session_id[:16]}")
        return True
    
    def resume_session(self, session_id: str) -> bool:
        """
        Resume a paused session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if resumed, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session.metadata.session_status == LangChainSessionStatus.PAUSED.value:
            session.metadata.session_status = LangChainSessionStatus.ACTIVE.value
            session.metadata.last_activity = datetime.utcnow()
            logger.info(f"Resumed LangChain session {session_id[:16]}")
            return True
        
        return False
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of session activity
        
        Args:
            session_id: The session ID
            
        Returns:
            Session summary dict or None if not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        duration = (
            (session.metadata.end_time or datetime.utcnow()) - 
            session.metadata.start_time
        ).total_seconds()
        
        return {
            "session_id": session.metadata.session_id,
            "phone_number": session.metadata.phone_number,
            "status": session.metadata.session_status,
            "is_valid": self.is_session_valid(session_id),
            "verification_score": session.metadata.verification_score,
            "thread_id": session.metadata.langgraph_thread_id,
            "duration_seconds": duration,
            "conversation_turns": session.metadata.current_turn,
            "messages_count": len(session.metadata.conversation_history),
            "started_at": session.metadata.start_time.isoformat(),
            "last_activity": session.metadata.last_activity.isoformat(),
            "verified": session.metadata.voice_verified
        }
    
    def clear_expired_sessions(self) -> int:
        """
        Clear expired sessions
        
        Returns:
            Number of sessions cleared
        """
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            elapsed = (now - session.metadata.start_time).total_seconds()
            # Mark as expired if either TTL exceeded or status is EXPIRED
            is_expired = (elapsed > session.metadata.ttl_seconds or 
                         session.metadata.session_status == LangChainSessionStatus.EXPIRED.value)
            
            if is_expired:
                expired_sessions.append(session_id)
                session.metadata.session_status = LangChainSessionStatus.EXPIRED.value
        
        # Delete expired sessions
        count = 0
        for session_id in expired_sessions:
            del self.sessions[session_id]
            count += 1
        
        if expired_sessions:
            logger.info(f"Cleared {count} expired LangChain sessions")
        
        return count
    
    def get_all_active_sessions(self) -> Dict[str, LangChainSession]:
        """
        Get all active sessions
        
        Returns:
            Dictionary of active sessions
        """
        return {
            sid: session for sid, session in self.sessions.items()
            if self.is_session_valid(sid)
        }
    
    def get_session_config(self, session_id: str) -> Optional[Any]:
        """
        Get LangChain RunnableConfig for a session
        
        Args:
            session_id: The session ID
            
        Returns:
            RunnableConfigWrapper or None
        """
        session = self.get_session(session_id)
        if session and session.config:
            return RunnableConfigWrapper(session.config)
        return None


# Global instance
_langchain_session_manager: Optional[LangChainSessionManager] = None


def get_langchain_session_manager() -> LangChainSessionManager:
    """Get or create global LangChainSessionManager instance"""
    global _langchain_session_manager
    
    if _langchain_session_manager is None:
        _langchain_session_manager = LangChainSessionManager(default_ttl_seconds=3600)
        logger.info("Initialized global LangChainSessionManager")
    
    return _langchain_session_manager
