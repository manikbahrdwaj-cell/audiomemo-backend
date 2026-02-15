"""
Enrollment Service Testing Suite
Comprehensive tests for multi-chunk voice enrollment
"""

import pytest
import numpy as np
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from enrollment_service import (
    EnrollmentStatus,
    EnrollmentSessionConfig,
    EnrollmentSession,
    AudioChunkRecord,
    EnrollmentServiceManager,
    get_enrollment_manager,
    create_enrollment_session,
    get_enrollment_session,
    add_audio_chunk,
    finalize_enrollment,
    MergeMode
)


class TestAudioChunkRecord:
    """Test AudioChunkRecord functionality"""
    
    def test_chunk_creation(self):
        """Test creating a chunk record"""
        audio_data = np.random.randn(16000)
        chunk = AudioChunkRecord(
            chunk_id="test-123",
            timestamp=datetime.utcnow(),
            duration_seconds=1.0,
            audio_data=audio_data,
            sample_rate=16000
        )
        
        assert chunk.chunk_id == "test-123"
        assert chunk.duration_seconds == 1.0
        assert chunk.sample_rate == 16000
        assert chunk.has_embedding == None  # embedding is None
        
    def test_chunk_to_dict(self):
        """Test chunk serialization"""
        audio_data = np.random.randn(16000)
        chunk = AudioChunkRecord(
            chunk_id="test-123",
            timestamp=datetime.utcnow(),
            duration_seconds=1.0,
            audio_data=audio_data,
            sample_rate=16000,
            quality_score=0.95
        )
        
        chunk_dict = chunk.to_dict()
        assert chunk_dict["chunk_id"] == "test-123"
        assert chunk_dict["quality_score"] == 0.95
        assert chunk_dict["has_embedding"] == False
        assert "timestamp" in chunk_dict
        

class TestEnrollmentSessionConfig:
    """Test EnrollmentSessionConfig"""
    
    def test_valid_config(self):
        """Test creating valid configuration"""
        config = EnrollmentSessionConfig(
            max_chunks=10,
            min_chunks_required=2,
            quality_threshold=0.7
        )
        assert config.max_chunks == 10
        assert config.min_chunks_required == 2
        assert config.quality_threshold == 0.7
        
    def test_invalid_config_min_exceeds_max(self):
        """Test config validation: min > max"""
        with pytest.raises(ValueError):
            EnrollmentSessionConfig(
                max_chunks=3,
                min_chunks_required=5
            )
            
    def test_invalid_config_quality_threshold(self):
        """Test config validation: invalid quality threshold"""
        with pytest.raises(ValueError):
            EnrollmentSessionConfig(quality_threshold=1.5)
        
        with pytest.raises(ValueError):
            EnrollmentSessionConfig(quality_threshold=-0.1)


class TestEnrollmentSession:
    """Test EnrollmentSession functionality"""
    
    def test_session_creation(self):
        """Test creating an enrollment session"""
        config = EnrollmentSessionConfig()
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        
        assert session.session_id == "test-session"
        assert session.phone_number == "1234567890"
        assert session.status == EnrollmentStatus.INITIALIZING
        assert len(session.chunks) == 0
        
    def test_add_chunk_success(self):
        """Test adding a chunk to session"""
        config = EnrollmentSessionConfig(max_chunks=5)
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        session.status = EnrollmentStatus.ACTIVE
        
        audio_data = np.random.randn(16000)
        chunk = session.add_chunk(audio_data, 1.0, quality_score=0.9)
        
        assert chunk is not None
        assert len(session.chunks) == 1
        assert session.status == EnrollmentStatus.COLLECTING
        
    def test_add_chunk_max_reached(self):
        """Test error when max chunks reached"""
        config = EnrollmentSessionConfig(max_chunks=2)
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        session.status = EnrollmentStatus.ACTIVE
        
        audio_data = np.random.randn(16000)
        session.add_chunk(audio_data, 1.0)
        session.add_chunk(audio_data, 1.0)
        
        # Third chunk should fail
        with pytest.raises(ValueError):
            session.add_chunk(audio_data, 1.0)
            
    def test_add_chunk_wrong_state(self):
        """Test error when adding chunk in wrong state"""
        config = EnrollmentSessionConfig()
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        session.status = EnrollmentStatus.COMPLETED
        
        audio_data = np.random.randn(16000)
        with pytest.raises(ValueError):
            session.add_chunk(audio_data, 1.0)
            
    def test_low_quality_chunk(self):
        """Test adding low-quality chunk"""
        config = EnrollmentSessionConfig(quality_threshold=0.8)
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        session.status = EnrollmentStatus.ACTIVE
        
        audio_data = np.random.randn(16000)
        chunk = session.add_chunk(audio_data, 1.0, quality_score=0.5)
        
        # Should still add but with warning
        assert len(session.chunks) == 1
        assert chunk.quality_score == 0.5
        
    def test_merge_single_embedding(self):
        """Test merging with single embedding"""
        config = EnrollmentSessionConfig()
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        
        # Add single embedding
        embedding = np.random.randn(192)
        session.embeddings.append(embedding)
        
        merged = session.merge_embeddings_strategy()
        
        assert merged is not None
        assert merged.shape == (192,)
        # Should normalize
        norm = np.linalg.norm(merged)
        assert np.isclose(norm, 1.0)
        
    def test_merge_multiple_embeddings_concatenate(self):
        """Test merging multiple embeddings with CONCATENATE mode"""
        config = EnrollmentSessionConfig(
            merge_embeddings=True,
            merge_mode=MergeMode.CONCATENATE
        )
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        
        # Add multiple embeddings
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(192)
        embedding3 = np.random.randn(192)
        
        session.embeddings = [embedding1, embedding2, embedding3]
        
        merged = session.merge_embeddings_strategy()
        
        assert merged is not None
        assert merged.shape == (192,)
        
        # Should be average of the three
        expected = np.mean([embedding1, embedding2, embedding3], axis=0)
        expected = expected / np.linalg.norm(expected)
        assert np.allclose(merged, expected, atol=1e-6)
        
    def test_merge_multiple_embeddings_overlap(self):
        """Test merging with OVERLAP (weighted) mode"""
        config = EnrollmentSessionConfig(
            merge_embeddings=True,
            merge_mode=MergeMode.OVERLAP
        )
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        
        # Add embeddings
        embeddings = [np.random.randn(192) for _ in range(3)]
        session.embeddings = embeddings
        
        merged = session.merge_embeddings_strategy()
        
        assert merged is not None
        assert merged.shape == (192,)
        
    def test_get_summary(self):
        """Test getting session summary"""
        config = EnrollmentSessionConfig()
        session = EnrollmentSession(
            session_id="test-session",
            phone_number="1234567890",
            config=config
        )
        
        summary = session.get_summary()
        
        assert summary["session_id"] == "test-session"
        assert summary["phone_number"] == "1234567890"
        assert summary["chunks_collected"] == 0
        assert summary["embeddings_generated"] == 0
        

class TestEnrollmentServiceManager:
    """Test EnrollmentServiceManager"""
    
    def test_manager_creation(self):
        """Test creating service manager"""
        manager = EnrollmentServiceManager()
        assert manager is not None
        assert len(manager.sessions) == 0
        
    def test_create_session(self):
        """Test creating a new session"""
        manager = EnrollmentServiceManager()
        session = manager.create_session("1234567890")
        
        assert session is not None
        assert session.phone_number == "1234567890"
        assert session.status == EnrollmentStatus.ACTIVE
        assert session.session_id in manager.sessions
        
    def test_get_session(self):
        """Test retrieving a session"""
        manager = EnrollmentServiceManager()
        created_session = manager.create_session("1234567890")
        
        retrieved_session = manager.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        
    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session"""
        manager = EnrollmentServiceManager()
        session = manager.get_session("fake-id")
        assert session is None
        
    def test_remove_session(self):
        """Test removing a session"""
        manager = EnrollmentServiceManager()
        session = manager.create_session("1234567890")
        session_id = session.session_id
        
        success = manager.remove_session(session_id)
        
        assert success
        assert manager.get_session(session_id) is None
        
    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        manager = EnrollmentServiceManager()
        
        # Create sessions
        session1 = manager.create_session("1234567890")
        session2 = manager.create_session("0987654321")
        
        # Manually set one as "old"
        session1.created_at = datetime.utcnow() - timedelta(hours=2)
        
        # Cleanup sessions older than 1 hour
        cleanup_count = manager.cleanup_expired_sessions(max_age_seconds=3600)
        
        assert cleanup_count == 1
        assert manager.get_session(session1.session_id) is None
        assert manager.get_session(session2.session_id) is not None
        
    def test_get_active_sessions(self):
        """Test getting active sessions"""
        manager = EnrollmentServiceManager()
        
        session1 = manager.create_session("1111111111")
        session2 = manager.create_session("2222222222")
        
        # Mark one as completed
        session2.status = EnrollmentStatus.COMPLETED
        
        active = manager.get_active_sessions()
        
        assert len(active) == 1
        assert session1.session_id in active
        
    def test_list_sessions(self):
        """Test listing all sessions"""
        manager = EnrollmentServiceManager()
        
        manager.create_session("1111111111")
        manager.create_session("2222222222")
        manager.create_session("3333333333")
        
        sessions = manager.list_sessions()
        
        assert len(sessions) == 3
        for session_summary in sessions:
            assert "session_id" in session_summary
            assert "phone_number" in session_summary
            

class TestHelperFunctions:
    """Test module-level helper functions"""
    
    def test_get_enrollment_manager(self):
        """Test getting enrollment manager"""
        manager = get_enrollment_manager()
        assert manager is not None
        assert isinstance(manager, EnrollmentServiceManager)
        
        # Should return same instance
        manager2 = get_enrollment_manager()
        assert manager is manager2
        
    def test_create_enrollment_session_helper(self):
        """Test create_enrollment_session helper"""
        session = create_enrollment_session("1234567890")
        
        assert session is not None
        assert session.phone_number == "1234567890"
        
    def test_get_enrollment_session_helper(self):
        """Test get_enrollment_session helper"""
        created = create_enrollment_session("1234567890")
        retrieved = get_enrollment_session(created.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == created.session_id


class TestEnrollmentIntegration:
    """Integration tests for enrollment flow"""
    
    @patch('enrollment_service.store_voice_embedding')
    @patch('enrollment_service.generate_embedding')
    def test_complete_enrollment_flow(self, mock_generate_embedding, mock_store):
        """Test complete enrollment from session creation to finalization"""
        # Setup mocks
        mock_embedding = np.random.randn(192)
        mock_generate_embedding.return_value = mock_embedding
        mock_store.return_value = "mongodb-id-123"
        
        # Create session
        session = create_enrollment_session("1234567890", EnrollmentSessionConfig(max_chunks=3))
        assert session.status == EnrollmentStatus.ACTIVE
        
        # Add chunks
        for i in range(3):
            audio_data = np.random.randn(16000)
            success, message, chunk = add_audio_chunk(
                session.session_id,
                audio_data,
                1.0,
                quality_score=0.9 + i*0.01
            )
            assert success
            assert chunk is not None
            
        # Check session has chunks
        retrieved_session = get_enrollment_session(session.session_id)
        assert len(retrieved_session.chunks) == 3
        
        # Finalize
        success, message, vector_id = finalize_enrollment(session.session_id)
        assert success
        assert vector_id == "mongodb-id-123"
        
        # Verify store was called
        mock_store.assert_called_once()


# ============================================================================
# Test Fixtures and Utilities
# ============================================================================

@pytest.fixture
def sample_audio():
    """Create sample audio data"""
    return np.random.randn(16000)  # 1 second at 16kHz


@pytest.fixture
def sample_embedding():
    """Create sample embedding"""
    return np.random.randn(192)  # ECAPA-TDNN embedding


@pytest.fixture
def enrollment_manager():
    """Create fresh enrollment manager for each test"""
    return EnrollmentServiceManager()


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance and load tests"""
    
    def test_many_chunks(self):
        """Test handling many chunks"""
        session = create_enrollment_session("1234567890", EnrollmentSessionConfig(max_chunks=100))
        
        for i in range(100):
            audio_data = np.random.randn(16000)
            success, _, _ = add_audio_chunk(session.session_id, audio_data, 1.0)
            assert success
            
    def test_many_sessions(self):
        """Test handling many concurrent sessions"""
        manager = EnrollmentServiceManager()
        
        for i in range(50):
            session = manager.create_session(f"phone_{i:04d}")
            assert session is not None
            
        assert len(manager.sessions) == 50
        
    def test_large_audio_chunk(self):
        """Test handling large audio chunk"""
        session = create_enrollment_session("1234567890")
        
        # 30 seconds of audio
        large_audio = np.random.randn(16000 * 30)
        success, _, _ = add_audio_chunk(session.session_id, large_audio, 30.0)
        assert success


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
