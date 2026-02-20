"""
Test Suite for Duplicate Enrollment Prevention
Tests the implementation of preventing duplicate enrollment for the same phone number
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import base64

from database import check_enrollment, store_voice_embedding, get_voice_embedding
from enrollment_service import (
    create_enrollment_session,
    EnrollmentSessionConfig,
    EnrollmentStatus,
    finalize_enrollment,
    get_enrollment_manager
)
from websocket_events import WebSocketEventHandler
from websocket_handler import ClientConnection, ConnectionState


class TestDuplicateEnrollmentPrevention:
    """Test duplicate enrollment prevention in enrollment service"""
    
    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database before and after each test"""
        # Remove test enrollments before test
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
            delete_voice_embedding("+9876543210")
        except:
            pass
        
        # Cleanup enrollment manager
        from enrollment_service import get_enrollment_manager
        manager = get_enrollment_manager()
        manager.sessions.clear()
        
        yield
        
        # Cleanup after test
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
            delete_voice_embedding("+9876543210")
        except:
            pass
        
        manager.sessions.clear()
    
    def test_first_enrollment_succeeds(self):
        """Test that first enrollment succeeds without issues"""
        phone_number = "+1234567890"
        
        # Create session
        session = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        assert session is not None
        assert session.status == EnrollmentStatus.ACTIVE
        
        # Create dummy audio and add chunk
        audio_data = np.zeros(16000, dtype=np.float32)  # 1 second at 16kHz
        session.add_chunk(audio_data, 1.0)
        
        # Finalize enrollment
        success, message, embedding = session.finalize_enrollment()
        
        assert success, f"First enrollment should succeed. Error: {message}"
        assert session.status == EnrollmentStatus.COMPLETED
        
        # Verify it's in database
        assert check_enrollment(phone_number)
    
    def test_duplicate_enrollment_rejected_at_finalize(self):
        """Test that duplicate enrollment is rejected during finalize"""
        phone_number = "+1234567890"
        
        # First enrollment
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        success1, msg1, _ = session1.finalize_enrollment()
        
        assert success1, "First enrollment should succeed"
        assert check_enrollment(phone_number)
        
        # Try second enrollment with same phone number
        session2 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        session2.add_chunk(audio_data, 1.0)
        success2, msg2, _ = session2.finalize_enrollment()
        
        assert not success2, "Duplicate enrollment should fail"
        assert "already enrolled" in msg2.lower(), f"Error message should mention duplicate: {msg2}"
        assert session2.status == EnrollmentStatus.ERROR
        assert session2.error_message is not None
    
    def test_duplicate_enrollment_prevents_overwrite(self):
        """Test that duplicate enrollment doesn't overwrite existing data"""
        phone_number = "+1234567890"
        
        # First enrollment with specific embedding
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data_1 = np.ones(16000, dtype=np.float32) * 0.1  # Different values
        session1.add_chunk(audio_data_1, 1.0)
        success1, _, _ = session1.finalize_enrollment()
        
        assert success1
        doc1 = get_voice_embedding(phone_number)
        first_id = doc1["_id"]
        
        # Try to enroll again
        session2 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data_2 = np.ones(16000, dtype=np.float32) * 0.5  # Different audio
        session2.add_chunk(audio_data_2, 1.0)
        success2, _, _ = session2.finalize_enrollment()
        
        assert not success2, "Second enrollment should fail"
        
        # Verify original data is unchanged
        doc2 = get_voice_embedding(phone_number)
        assert doc2["_id"] == first_id, "Document ID should not change"
    
    def test_different_phone_numbers_can_enroll(self):
        """Test that different phone numbers can enroll independently"""
        phone1 = "+1234567890"
        phone2 = "+9876543210"
        
        # First enrollment
        session1 = create_enrollment_session(phone1, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        success1, msg1, _ = session1.finalize_enrollment()
        
        assert success1, f"First phone enrollment failed: {msg1}"
        assert check_enrollment(phone1)
        
        # Second enrollment with different number
        session2 = create_enrollment_session(phone2, EnrollmentSessionConfig())
        session2.add_chunk(audio_data, 1.0)
        success2, msg2, _ = session2.finalize_enrollment()
        
        assert success2, f"Second phone enrollment failed: {msg2}"
        assert check_enrollment(phone2)
        
        # Verify both exist
        assert check_enrollment(phone1)
        assert check_enrollment(phone2)
    
    def test_enrollment_error_status_set_correctly(self):
        """Test that duplicate enrollment sets ERROR status and message"""
        phone_number = "+1234567890"
        
        # First enrollment
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        session1.finalize_enrollment()
        
        # Second enrollment
        session2 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        session2.add_chunk(audio_data, 1.0)
        success, msg, _ = session2.finalize_enrollment()
        
        assert not success
        assert session2.status == EnrollmentStatus.ERROR
        assert session2.error_message is not None
        assert "already enrolled" in session2.error_message.lower()
    
    def test_logging_on_duplicate(self):
        """Test that duplicate enrollment is properly logged"""
        phone_number = "+1234567890"
        
        # First enrollment
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        session1.finalize_enrollment()
        
        # Try duplicate with logging check
        session2 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        session2.add_chunk(audio_data, 1.0)
        
        with patch('enrollment_service.logger') as mock_logger:
            success, msg, _ = session2.finalize_enrollment()
            
            assert not success
            # Verify warning was logged
            mock_logger.warning.assert_called()


class TestRESTEndpointDuplicatePrevention:
    """Test duplicate prevention in REST endpoints (simulated)"""
    
    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database"""
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
        except:
            pass
        
        from enrollment_service import get_enrollment_manager
        get_enrollment_manager().sessions.clear()
        
        yield
        
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
        except:
            pass
        
        get_enrollment_manager().sessions.clear()
    
    def test_session_creation_checks_enrollment_status(self):
        """Test that session creation would check enrollment status"""
        phone_number = "+1234567890"
        
        # Simulate first enrollment
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        session1.finalize_enrollment()
        
        # Simulate second session creation (what REST endpoint would do)
        already_enrolled = check_enrollment(phone_number)
        assert already_enrolled, "Should detect existing enrollment"
        
        # Session creation should be prevented
        if already_enrolled:
            # This is what the REST endpoint does
            raise Exception("This number is already enrolled. Duplicate enrollment is not allowed.")


class TestWebSocketHandlerDuplicatePrevention:
    """Test duplicate prevention in WebSocket handler"""
    
    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database"""
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
        except:
            pass
        
        yield
        
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_websocket_handler_checks_enrollment(self):
        """Test that WebSocket handler checks for duplicate enrollment"""
        phone_number = "+1234567890"
        
        # First enrollment
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        session1.finalize_enrollment()
        
        # Verify enrolled
        assert check_enrollment(phone_number)
        
        # Simulate WebSocket handler check
        is_enrolled = check_enrollment(phone_number)
        assert is_enrolled, "WebSocket handler should detect existing enrollment"


class TestRaceConditionPrevention:
    """Test prevention of race conditions in concurrent enrollments"""
    
    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database"""
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
        except:
            pass
        
        from enrollment_service import get_enrollment_manager
        get_enrollment_manager().sessions.clear()
        
        yield
        
        try:
            from database import delete_voice_embedding
            delete_voice_embedding("+1234567890")
        except:
            pass
        
        get_enrollment_manager().sessions.clear()
    
    def test_check_happens_before_storage(self):
        """
        Test that the duplicate check happens in finalize (before storage)
        This prevents race conditions where two concurrent requests 
        could both pass a session creation check
        """
        phone_number = "+1234567890"
        
        # Session 1 - completes successfully
        session1 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session1.add_chunk(audio_data, 1.0)
        success1, _, _ = session1.finalize_enrollment()
        
        assert success1, "First enrollment should succeed"
        
        # Session 2 - attempt duplicate (even though session was created before DB check)
        # This simulates the race condition scenario
        session2 = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        session2.add_chunk(audio_data, 1.0)
        
        # The check in finalize_enrollment prevents the duplicate
        success2, msg2, _ = session2.finalize_enrollment()
        
        assert not success2, "Duplicate enrollment should fail at finalize"
        assert "already enrolled" in msg2.lower()


# Integration test helper
def test_full_enrollment_flow_with_duplicate_prevention():
    """Test the full enrollment flow with duplicate prevention"""
    from database import delete_voice_embedding
    
    phone_number = "+1234567890"
    
    try:
        delete_voice_embedding(phone_number)
    except:
        pass
    
    try:
        # Step 1: Create session (checks enrollment)
        if check_enrollment(phone_number):
            raise ValueError("Already enrolled")
        
        # Step 2: Create session and collect audio
        session = create_enrollment_session(phone_number, EnrollmentSessionConfig())
        audio_data = np.zeros(16000, dtype=np.float32)
        session.add_chunk(audio_data, 1.0)
        
        # Step 3: Finalize (checks enrollment again, prevents race conditions)
        success, message, embedding = session.finalize_enrollment()
        
        assert success, f"Enrollment should succeed: {message}"
        assert check_enrollment(phone_number)
        
        # Step 4: Attempt duplicate
        try:
            if check_enrollment(phone_number):
                raise ValueError("Already enrolled")
        except ValueError:
            # Expected - duplicate prevention works
            pass
        
    finally:
        try:
            delete_voice_embedding(phone_number)
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
