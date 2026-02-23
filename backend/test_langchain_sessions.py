"""
Test Suite for LangChain Session Management
Tests creation, storage, and lifecycle management of LangChain sessions
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from langchain_session_service import (
    LangChainSessionManager,
    LangChainSessionMetadata,
    LangChainSession,
    LangChainSessionStatus,
    get_langchain_session_manager
)
from langchain_session_integration import (
    LangChainSessionIntegration,
    get_langchain_session_integration
)


class TestLangChainSessionMetadata:
    """Test LangChainSessionMetadata class"""
    
    def test_metadata_creation(self):
        """Test creating metadata"""
        metadata = LangChainSessionMetadata(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        assert metadata.phone_number == "+1-555-0123"
        assert metadata.verification_score == 0.92
        assert metadata.session_status == LangChainSessionStatus.CREATED.value
        assert metadata.session_id.startswith("lg_session_")
        assert metadata.langgraph_thread_id.startswith("thread_")
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dict"""
        metadata = LangChainSessionMetadata(
            phone_number="+1-555-0123",
            verification_score=0.95
        )
        
        data = metadata.to_dict()
        
        assert data["phone_number"] == "+1-555-0123"
        assert data["verification_score"] == 0.95
        assert "session_id" in data
        assert "timestamp" in data
    
    def test_metadata_from_dict(self):
        """Test creating metadata from dict"""
        original_data = {
            "phone_number": "+1-555-0123",
            "verification_score": 0.90,
            "session_id": "lg_session_test",
            "langgraph_thread_id": "thread_test"
        }
        
        metadata = LangChainSessionMetadata.from_dict(original_data)
        
        assert metadata.phone_number == "+1-555-0123"
        assert metadata.verification_score == 0.90


class TestLangChainSessionManager:
    """Test LangChainSessionManager class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manager = LangChainSessionManager(default_ttl_seconds=3600)
    
    def test_create_session(self):
        """Test creating a session"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        assert session is not None
        assert session.metadata.phone_number == "+1-555-0123"
        assert session.metadata.verification_score == 0.92
        assert session.metadata.session_status == LangChainSessionStatus.ACTIVE.value
        assert session.config is not None
    
    def test_get_session(self):
        """Test retrieving a session"""
        created = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        retrieved = self.manager.get_session(created.metadata.session_id)
        
        assert retrieved is not None
        assert retrieved.metadata.session_id == created.metadata.session_id
    
    def test_get_nonexistent_session(self):
        """Test retrieving nonexistent session"""
        session = self.manager.get_session("nonexistent_id")
        assert session is None
    
    def test_update_session_activity(self):
        """Test updating last activity"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        old_activity = session.metadata.last_activity
        import time
        time.sleep(0.1)
        
        result = self.manager.update_session_activity(session.metadata.session_id)
        
        assert result is True
        assert session.metadata.last_activity > old_activity
    
    def test_add_conversation_turn(self):
        """Test adding conversation turns"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        result = self.manager.add_conversation_turn(
            session.metadata.session_id,
            role="user",
            content="Hello"
        )
        
        assert result is True
        assert len(session.metadata.conversation_history) == 1
        assert session.metadata.current_turn == 1
        assert session.metadata.conversation_history[0]["role"] == "user"
    
    def test_multiple_conversation_turns(self):
        """Test adding multiple turns"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        self.manager.add_conversation_turn(session.metadata.session_id, "user", "Hello")
        self.manager.add_conversation_turn(session.metadata.session_id, "assistant", "Hi!")
        self.manager.add_conversation_turn(session.metadata.session_id, "user", "How are you?")
        
        assert session.metadata.current_turn == 3
        assert len(session.metadata.conversation_history) == 3
    
    def test_is_session_valid(self):
        """Test session validity check"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        assert self.manager.is_session_valid(session.metadata.session_id) is True
    
    def test_is_session_expired(self):
        """Test expired session detection"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        # Manually set as expired
        session.metadata.session_status = LangChainSessionStatus.EXPIRED.value
        
        assert self.manager.is_session_valid(session.metadata.session_id) is False
    
    def test_pause_session(self):
        """Test pausing a session"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        result = self.manager.pause_session(session.metadata.session_id)
        
        assert result is True
        assert session.metadata.session_status == LangChainSessionStatus.PAUSED.value
    
    def test_resume_session(self):
        """Test resuming a session"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        self.manager.pause_session(session.metadata.session_id)
        result = self.manager.resume_session(session.metadata.session_id)
        
        assert result is True
        assert session.metadata.session_status == LangChainSessionStatus.ACTIVE.value
    
    def test_terminate_session(self):
        """Test terminating a session"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        result = self.manager.terminate_session(session.metadata.session_id)
        
        assert result is True
        assert session.metadata.session_status == LangChainSessionStatus.TERMINATED.value
        assert session.metadata.end_time is not None
    
    def test_get_session_summary(self):
        """Test getting session summary"""
        session = self.manager.create_session(
            phone_number="+1-555-0123",
            verification_score=0.92
        )
        
        self.manager.add_conversation_turn(session.metadata.session_id, "user", "Hello")
        self.manager.add_conversation_turn(session.metadata.session_id, "assistant", "Hi")
        
        summary = self.manager.get_session_summary(session.metadata.session_id)
        
        assert summary["session_id"] == session.metadata.session_id
        assert summary["phone_number"] == "+1-555-0123"
        assert summary["conversation_turns"] == 2
        assert summary["messages_count"] == 2
    
    def test_get_all_active_sessions(self):
        """Test getting all active sessions"""
        # Create multiple sessions
        session1 = self.manager.create_session("+1-555-0001", 0.92)
        session2 = self.manager.create_session("+1-555-0002", 0.95)
        
        # Terminate one
        self.manager.terminate_session(session1.metadata.session_id)
        
        active = self.manager.get_all_active_sessions()
        
        assert len(active) == 1
        assert session2.metadata.session_id in active
    
    def test_clear_expired_sessions(self):
        """Test clearing expired sessions"""
        session = self.manager.create_session("+1-555-0123", 0.92)
        
        # Force expiration
        session.metadata.session_status = LangChainSessionStatus.EXPIRED.value
        
        count = self.manager.clear_expired_sessions()
        
        assert count == 1
        assert self.manager.get_session(session.metadata.session_id) is None
    
    def test_get_session_config(self):
        """Test getting session RunnableConfig"""
        session = self.manager.create_session("+1-555-0123", 0.92)
        
        config = self.manager.get_session_config(session.metadata.session_id)
        
        assert config is not None
        assert config.configurable["phone_number"] == "+1-555-0123"


class TestLangChainSessionIntegration:
    """Test LangChainSessionIntegration class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.integration = LangChainSessionIntegration()
    
    def test_create_session_on_voice_match(self):
        """Test creating session after voice match"""
        result = self.integration.create_session_on_voice_match(
            phone_number="+1-555-0123",
            verification_score=0.92,
            similarity_metrics={
                "cosine_similarity": 0.92,
                "confidence": 92.0
            }
        )
        
        assert result["success"] is True
        assert result["phone_number"] == "+1-555-0123"
        assert result["verification_score"] == 0.92
        assert result["status"] == "active"
        assert "session_id" in result
        assert "thread_id" in result
    
    def test_add_message_to_session(self):
        """Test adding message to session"""
        result = self.integration.create_session_on_voice_match(
            phone_number="+1-555-0123",
            verification_score=0.92,
            similarity_metrics={"cosine_similarity": 0.92}
        )
        
        session_id = result["session_id"]
        
        success = self.integration.add_message_to_session(
            session_id=session_id,
            role="user",
            content="Hello"
        )
        
        assert success is True
    
    def test_get_session_info(self):
        """Test getting session info"""
        result = self.integration.create_session_on_voice_match(
            phone_number="+1-555-0123",
            verification_score=0.92,
            similarity_metrics={"cosine_similarity": 0.92}
        )
        
        session_id = result["session_id"]
        
        info = self.integration.get_session_info(session_id)
        
        assert info is not None
        assert info["session_id"] == session_id
        assert info["phone_number"] == "+1-555-0123"
        assert info["status"] == "active"
    
    def test_pause_and_resume(self):
        """Test pausing and resuming session"""
        result = self.integration.create_session_on_voice_match(
            phone_number="+1-555-0123",
            verification_score=0.92,
            similarity_metrics={"cosine_similarity": 0.92}
        )
        
        session_id = result["session_id"]
        
        # Pause
        paused = self.integration.pause_session(session_id)
        assert paused is True
        
        info = self.integration.get_session_info(session_id)
        assert info["status"] == "paused"
        
        # Resume
        resumed = self.integration.resume_session(session_id)
        assert resumed is True
        
        info = self.integration.get_session_info(session_id)
        assert info["status"] == "active"
    
    def test_terminate_session(self):
        """Test terminating a session"""
        result = self.integration.create_session_on_voice_match(
            phone_number="+1-555-0123",
            verification_score=0.92,
            similarity_metrics={"cosine_similarity": 0.92}
        )
        
        session_id = result["session_id"]
        
        terminated = self.integration.terminate_session(session_id)
        assert terminated is True
        
        info = self.integration.get_session_info(session_id)
        assert info["status"] == "terminated"


class TestGlobalInstances:
    """Test global instance management"""
    
    def test_get_langchain_session_manager(self):
        """Test getting global session manager"""
        manager1 = get_langchain_session_manager()
        manager2 = get_langchain_session_manager()
        
        assert manager1 is manager2  # Should be same instance
    
    def test_get_langchain_session_integration(self):
        """Test getting global integration"""
        integration1 = get_langchain_session_integration()
        integration2 = get_langchain_session_integration()
        
        assert integration1 is integration2  # Should be same instance


# Run tests
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
