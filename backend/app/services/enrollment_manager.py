"""
Manager for multiple enrollment sessions.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from app.services.enrollment_session import EnrollmentSession
from app.services.enrollment_config import EnrollmentSessionConfig
from app.services.enrollment_status import EnrollmentStatus
import uuid
import logging

logger = logging.getLogger(__name__)

class EnrollmentServiceManager:
    """
    Manages multiple enrollment sessions
    """
    def __init__(self):
        self.sessions: Dict[str, EnrollmentSession] = {}
        logger.info("Enrollment Service Manager initialized")

    def create_session(self, phone_number: str, config: Optional[EnrollmentSessionConfig] = None) -> EnrollmentSession:
        if config is None:
            config = EnrollmentSessionConfig()
        session_id = str(uuid.uuid4())
        session = EnrollmentSession(session_id=session_id, phone_number=phone_number, config=config)
        session.status = EnrollmentStatus.ACTIVE
        session.started_at = datetime.utcnow()
        self.sessions[session_id] = session
        logger.info(f"Created enrollment session {session_id[:8]} for {phone_number}")
        return session

    def get_session(self, session_id: str) -> Optional[EnrollmentSession]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            session.cleanup()
            logger.info(f"Removed enrollment session {session_id[:8]}")
            return True
        return False

    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
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
        return {
            sid: s for sid, s in self.sessions.items()
            if s.status in [EnrollmentStatus.ACTIVE, EnrollmentStatus.COLLECTING, EnrollmentStatus.PROCESSING]
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [session.get_summary() for session in self.sessions.values()]

    def find_session_by_phone(self, phone_number: str) -> Optional[EnrollmentSession]:
        for session in self.sessions.values():
            if session.phone_number == phone_number and session.status in [
                EnrollmentStatus.ACTIVE,
                EnrollmentStatus.COLLECTING,
                EnrollmentStatus.PROCESSING
            ]:
                return session
        return None

# Global enrollment service manager instance
_enrollment_manager: Optional[EnrollmentServiceManager] = None

def get_enrollment_manager() -> EnrollmentServiceManager:
    global _enrollment_manager
    if _enrollment_manager is None:
        _enrollment_manager = EnrollmentServiceManager()
    return _enrollment_manager

def create_enrollment_session(phone_number: str, config: Optional[EnrollmentSessionConfig] = None) -> EnrollmentSession:
    manager = get_enrollment_manager()
    return manager.create_session(phone_number, config)

def get_enrollment_session(session_id: str) -> Optional[EnrollmentSession]:
    manager = get_enrollment_manager()
    return manager.get_session(session_id)

def remove_session(session_id: str) -> bool:
    manager = get_enrollment_manager()
    return manager.remove_session(session_id)

def list_sessions() -> List[Dict[str, Any]]:
    manager = get_enrollment_manager()
    return manager.list_sessions()

def find_session_by_phone(phone_number: str) -> Optional[EnrollmentSession]:
    manager = get_enrollment_manager()
    return manager.find_session_by_phone(phone_number)

def cleanup_expired_sessions(max_age_seconds: int = 3600) -> int:
    manager = get_enrollment_manager()
    return manager.cleanup_expired_sessions(max_age_seconds)

def get_active_sessions() -> Dict[str, EnrollmentSession]:
    manager = get_enrollment_manager()
    return manager.get_active_sessions()
