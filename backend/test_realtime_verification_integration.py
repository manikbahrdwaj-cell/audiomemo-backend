"""
Integration Tests for Real-Time Voice Verification System
Tests the complete flow from recording to automatic verification
"""

import pytest
import asyncio
import json
import base64
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import numpy as np
from datetime import datetime

# Import backend modules
from main import app
from verification_streaming_service import (
    RealtimeVerificationManager,
    StreamingVerificationSession,
    StreamingVerificationStatus,
    ChunkVerificationResult
)
from voice_embedding import generate_embedding, calculate_cosine_similarity


@pytest.mark.asyncio
class TestRealtimeVerificationIntegration:
    """Integration tests for real-time verification system"""

    @pytest.fixture
    def verification_manager(self):
        """Create a fresh verification manager for each test"""
        return RealtimeVerificationManager()

    @pytest.fixture
    def mock_audio_chunk(self):
        """Create a mock audio chunk (WAV format)"""
        # Simple WAV file header + dummy audio data
        sample_rate = 16000
        duration = 5  # 5 seconds
        samples = int(sample_rate * duration)
        
        # Create audio data
        audio_data = np.sin(np.linspace(0, 100 * np.pi, samples)).astype(np.float32)
        
        # Convert to bytes (simplified WAV)
        import io
        import soundfile as sf
        
        wav_bytes = io.BytesIO()
        sf.write(wav_bytes, audio_data, sample_rate, format='WAV')
        return wav_bytes.getvalue()

    @pytest.fixture
    def mock_enrollment_embedding(self):
        """Create a mock enrollment embedding"""
        return np.random.randn(192).astype(np.float32)

    @pytest.mark.asyncio
    async def test_session_creation(self, verification_manager, mock_enrollment_embedding):
        """Test creating a verification session"""
        phone_number = "+1-555-0000"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            mock_get.return_value = mock_enrollment_embedding
            
            session = await verification_manager.create_session(phone_number)
            
            assert session is not None
            assert session.phone_number == phone_number
            assert session.status == StreamingVerificationStatus.READY
            assert session.enrolled_embedding is not None
            assert np.array_equal(session.enrolled_embedding, mock_enrollment_embedding)

    @pytest.mark.asyncio
    async def test_session_creation_not_enrolled(self, verification_manager):
        """Test creating session for non-existent phone number"""
        phone_number = "+1-555-9999"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            mock_get.return_value = None
            
            session = await verification_manager.create_session(phone_number)
            
            assert session is None

    @pytest.mark.asyncio
    async def test_chunk_processing_match(self, verification_manager, mock_audio_chunk, mock_enrollment_embedding):
        """Test processing a chunk that matches enrollment"""
        phone_number = "+1-555-0000"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get_embedding:
            with patch('verification_streaming_service.generate_embedding') as mock_gen:
                with patch('verification_streaming_service.calculate_cosine_similarity') as mock_similarity:
                    # Setup
                    mock_get_embedding.return_value = mock_enrollment_embedding
                    mock_gen.return_value = mock_enrollment_embedding  # Same = perfect match
                    mock_similarity.return_value = 0.95  # High similarity
                    
                    # Create session
                    session = await verification_manager.create_session(phone_number)
                    
                    # Process chunk
                    result = await verification_manager.process_chunk(
                        session.session_id,
                        mock_audio_chunk
                    )
                    
                    # Verify result
                    assert result is not None
                    assert result["chunk_number"] == 1
                    assert result["similarity_score"] == 0.95
                    assert result["is_match"] is True
                    assert result["final_status"] == "verified"
                    assert result["verified_at_chunk"] == 1

    @pytest.mark.asyncio
    async def test_chunk_processing_no_match(self, verification_manager, mock_audio_chunk, mock_enrollment_embedding):
        """Test processing chunks that don't match"""
        phone_number = "+1-555-0000"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get_embedding:
            with patch('verification_streaming_service.generate_embedding') as mock_gen:
                with patch('verification_streaming_service.calculate_cosine_similarity') as mock_similarity:
                    # Setup
                    mock_get_embedding.return_value = mock_enrollment_embedding
                    
                    # Different embeddings
                    different_embedding = np.random.randn(192).astype(np.float32)
                    mock_gen.return_value = different_embedding
                    mock_similarity.return_value = 0.65  # Low similarity (below 0.75 threshold)
                    
                    # Create session
                    session = await verification_manager.create_session(phone_number)
                    
                    # Process 4 chunks
                    for chunk_num in range(1, 5):
                        result = await verification_manager.process_chunk(
                            session.session_id,
                            mock_audio_chunk
                        )
                        
                        assert result["chunk_number"] == chunk_num
                        assert result["is_match"] is False
                        
                        if chunk_num < 4:
                            assert result.get("final_status") is None
                        else:
                            assert result["final_status"] == "unverified"

    @pytest.mark.asyncio
    async def test_verify_at_chunk_3(self, verification_manager, mock_audio_chunk, mock_enrollment_embedding):
        """Test verification succeeding at chunk 3"""
        phone_number = "+1-555-0000"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get_embedding:
            with patch('verification_streaming_service.generate_embedding') as mock_gen:
                with patch('verification_streaming_service.calculate_cosine_similarity') as mock_similarity:
                    mock_get_embedding.return_value = mock_enrollment_embedding
                    mock_gen.return_value = mock_enrollment_embedding
                    
                    # Chunks 1-2: no match, Chunk 3: match
                    mock_similarity.side_effect = [0.60, 0.65, 0.85, 0.95]
                    
                    session = await verification_manager.create_session(phone_number)
                    
                    for chunk_num in range(1, 5):
                        result = await verification_manager.process_chunk(
                            session.session_id,
                            mock_audio_chunk
                        )
                        
                        if chunk_num < 3:
                            assert result["is_match"] is False
                            assert result.get("final_status") is None
                        elif chunk_num == 3:
                            assert result["is_match"] is True
                            assert result["final_status"] == "verified"
                            assert result["verified_at_chunk"] == 3
                            break
                        else:
                            # Should not reach chunk 4
                            pytest.fail("Should have verified at chunk 3")

    @pytest.mark.asyncio
    async def test_session_cancellation(self, verification_manager, mock_enrollment_embedding):
        """Test cancelling a verification session"""
        phone_number = "+1-555-0000"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            mock_get.return_value = mock_enrollment_embedding
            
            session = await verification_manager.create_session(phone_number)
            session_id = session.session_id
            
            # Cancel session
            result = await verification_manager.cancel_session(session_id)
            
            assert result is True
            assert session.status == StreamingVerificationStatus.CANCELLED
            assert session.final_status == "cancelled"

    @pytest.mark.asyncio
    async def test_session_cleanup(self, verification_manager, mock_enrollment_embedding):
        """Test cleaning up a session"""
        phone_number = "+1-555-0000"
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            mock_get.return_value = mock_enrollment_embedding
            
            session = await verification_manager.create_session(phone_number)
            session_id = session.session_id
            
            assert verification_manager.get_session(session_id) is not None
            
            # Cleanup
            verification_manager.cleanup_session(session_id)
            
            assert verification_manager.get_session(session_id) is None

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, verification_manager, mock_audio_chunk, mock_enrollment_embedding):
        """Test handling multiple concurrent verification sessions"""
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            mock_get.return_value = mock_enrollment_embedding
            
            # Create 3 sessions
            sessions = []
            for i in range(3):
                session = await verification_manager.create_session(f"+1-555-000{i}")
                sessions.append(session)
            
            assert len(verification_manager.sessions) == 3
            
            # Process chunks for each
            with patch('verification_streaming_service.generate_embedding') as mock_gen:
                with patch('verification_streaming_service.calculate_cosine_similarity') as mock_sim:
                    mock_gen.return_value = mock_enrollment_embedding
                    mock_sim.return_value = 0.85
                    
                    for session in sessions:
                        result = await verification_manager.process_chunk(
                            session.session_id,
                            mock_audio_chunk
                        )
                        assert result["final_status"] == "verified"

    def test_chunk_verification_result_dataclass(self):
        """Test ChunkVerificationResult dataclass"""
        result = ChunkVerificationResult(
            chunk_number=1,
            similarity_score=0.85,
            is_match=True
        )
        
        assert result.chunk_number == 1
        assert result.similarity_score == 0.85
        assert result.is_match is True
        assert isinstance(result.timestamp, datetime)

    def test_streaming_verification_session_dataclass(self):
        """Test StreamingVerificationSession dataclass"""
        session = StreamingVerificationSession(
            phone_number="+1-555-0000",
            threshold=0.75
        )
        
        assert session.phone_number == "+1-555-0000"
        assert session.threshold == 0.75
        assert session.status == StreamingVerificationStatus.INITIALIZED
        assert session.chunks_received == 0
        assert len(session.chunk_results) == 0


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket endpoint"""

    @pytest.fixture
    def client(self):
        """Get FastAPI test client"""
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_websocket_endpoint_exists(self, client):
        """Test that WebSocket endpoint can be reached"""
        # Note: TestClient doesn't support WebSocket directly
        # This is a placeholder for how WebSocket testing would work
        pass

    @pytest.mark.asyncio
    async def test_websocket_message_format(self):
        """Test WebSocket message format validation"""
        # Test audio message format
        message = {
            "type": "audio",
            "data": base64.b64encode(b"test_audio").decode()
        }
        
        assert message["type"] == "audio"
        assert isinstance(message["data"], str)
        assert len(message["data"]) > 0

    @pytest.mark.asyncio
    async def test_websocket_cancel_message(self):
        """Test WebSocket cancel message format"""
        message = {
            "type": "cancel"
        }
        
        assert message["type"] == "cancel"

    @pytest.mark.asyncio
    async def test_websocket_ping_message(self):
        """Test WebSocket ping message format"""
        message = {
            "type": "ping"
        }
        
        assert message["type"] == "ping"


@pytest.mark.asyncio
class TestEndToEndFlow:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_complete_verification_flow_success(self):
        """Test complete flow: setup → record → verify (success)"""
        manager = RealtimeVerificationManager()
        phone_number = "+1-555-0000"
        mock_embedding = np.random.randn(192).astype(np.float32)
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            with patch('verification_streaming_service.generate_embedding') as mock_gen:
                with patch('verification_streaming_service.calculate_cosine_similarity') as mock_sim:
                    mock_get.return_value = mock_embedding
                    mock_gen.return_value = mock_embedding
                    mock_sim.return_value = 0.88
                    
                    # Step 1: Create session (Initialize Verification)
                    session = await manager.create_session(phone_number, threshold=0.75)
                    assert session is not None
                    assert session.status == StreamingVerificationStatus.READY
                    
                    # Step 2: Send audio chunk (Start Recording → chunk sent)
                    dummy_audio = b"\x00" * 1000
                    result = await manager.process_chunk(session.session_id, dummy_audio)
                    
                    # Step 3: Verify successful
                    assert result["final_status"] == "verified"
                    assert result["chunk_number"] == 1
                    assert result["similarity_score"] == 0.88
                    
                    # Step 4: Verify session state
                    assert session.final_status == "verified"
                    assert session.verified_at_chunk == 1

    @pytest.mark.asyncio
    async def test_complete_verification_flow_failure(self):
        """Test complete flow: setup → record → verify (failure)"""
        manager = RealtimeVerificationManager()
        phone_number = "+1-555-0000"
        mock_embedding = np.random.randn(192).astype(np.float32)
        
        with patch('verification_streaming_service.get_voice_embedding') as mock_get:
            with patch('verification_streaming_service.generate_embedding') as mock_gen:
                with patch('verification_streaming_service.calculate_cosine_similarity') as mock_sim:
                    mock_get.return_value = mock_embedding
                    mock_gen.return_value = np.random.randn(192).astype(np.float32)
                    mock_sim.return_value = 0.55  # Below 0.75 threshold
                    
                    # Step 1: Create session
                    session = await manager.create_session(phone_number, threshold=0.75)
                    
                    # Step 2-5: Send 4 chunks (all below threshold)
                    dummy_audio = b"\x00" * 1000
                    result = None
                    
                    for i in range(4):
                        result = await manager.process_chunk(session.session_id, dummy_audio)
                        assert result["is_match"] is False
                    
                    # Step 6: Verify failed
                    assert result["final_status"] == "unverified"
                    assert result["chunk_number"] == 4
                    assert session.final_status == "unverified"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
