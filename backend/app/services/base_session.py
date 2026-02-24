"""
Base classes for voice session management (enrollment/verification).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class BaseVoiceSession(ABC):
    def __init__(self, session_id: str, phone_number: str):
        self.session_id = session_id
        self.phone_number = phone_number
        self.created_at = datetime.utcnow()
        self.last_active = self.created_at
        self.audio_chunks: List = []

    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        return (datetime.utcnow() - self.last_active).total_seconds() > max_age_seconds

    def update_activity(self):
        self.last_active = datetime.utcnow()

class BaseSessionManager(ABC):
    def __init__(self):
        self._sessions: Dict[str, BaseVoiceSession] = {}

    def get_session(self, session_id: str) -> Optional[BaseVoiceSession]:
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired(max_age_seconds)]
        for sid in expired:
            self.remove_session(sid)
        return len(expired)
