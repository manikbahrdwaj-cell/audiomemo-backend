"""
Test suite for audio chunk receiver
Verifies chunk merging and embedding generation
"""

import numpy as np
import pytest
from audio.audio_chunk_receiver import (
    AudioChunkReceiver,
    ChunkReceiverSession,
    ChunkReceiverStatus,
    get_chunk_receiver,
)


class TestAudioChunkReceiver:
    """Test cases for audio chunk receiver"""
    
    def setup_method(self):
        """Setup for each test"""
        self.receiver = AudioChunkReceiver()
    
    def test_create_session(self):
        """Test creating a receiver session"""
        session = self.receiver.create_session(
            phone_number='+1234567890',
            mode='enrollment',
            chunks_expected=5
        )
        
        assert session is not None
        assert session.phone_number == '+1234567890'
        assert session.mode == 'enrollment'
        assert session.chunks_expected == 5
        assert session.status == ChunkReceiverStatus.CREATED
    
    def test_get_session(self):
        """Test retrieving a session"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        retrieved = self.receiver.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
    
    def test_add_single_chunk(self):
        """Test adding a single audio chunk"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Create audio data
        audio_data = np.random.randn(16000).astype(np.float32)
        
        # Add chunk
        success, error = self.receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=1,
            audio_data=audio_data,
            sample_rate=16000,
            duration_ms=1000
        )
        
        assert success is True
        assert error is None
        assert len(session.chunks_received) == 1
        assert session.status == ChunkReceiverStatus.RECEIVING_CHUNKS
    
    def test_add_multiple_chunks(self):
        """Test adding multiple chunks in sequence"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add 5 chunks
        for i in range(5):
            audio_data = np.random.randn(16000).astype(np.float32)
            success, error = self.receiver.add_chunk(
                session_id=session.session_id,
                chunk_number=i,
                audio_data=audio_data
            )
            assert success is True
        
        assert len(session.chunks_received) == 5
    
    def test_add_chunk_invalid_session(self):
        """Test adding chunk to non-existent session"""
        audio_data = np.random.randn(16000).astype(np.float32)
        
        success, error = self.receiver.add_chunk(
            session_id='invalid_id',
            chunk_number=1,
            audio_data=audio_data
        )
        
        assert success is False
        assert error is not None
    
    def test_add_chunk_empty_audio(self):
        """Test adding chunk with empty audio"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        audio_data = np.array([], dtype=np.float32)
        
        success, error = self.receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=1,
            audio_data=audio_data
        )
        
        assert success is False
        assert 'empty' in error.lower()
    
    def test_add_chunk_wrong_dimensions(self):
        """Test adding chunk with wrong audio dimensions"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # 2D audio (wrong)
        audio_data = np.random.randn(16000, 2).astype(np.float32)
        
        success, error = self.receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=1,
            audio_data=audio_data
        )
        
        assert success is False
        assert 'dimension' in error.lower() or 'shape' in error.lower()
    
    def test_merge_chunks(self):
        """Test merging multiple chunks"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add 3 chunks
        chunk_data = []
        for i in range(3):
            audio_data = np.random.randn(16000).astype(np.float32)
            chunk_data.append(audio_data)
            self.receiver.add_chunk(
                session_id=session.session_id,
                chunk_number=i,
                audio_data=audio_data
            )
        
        # Merge
        success, merged, error = self.receiver.merge_chunks(session.session_id)
        
        assert success is True
        assert error is None
        assert merged is not None
        assert len(merged) == 16000 * 3  # All chunks concatenated
        assert session.status == ChunkReceiverStatus.MERGING
    
    def test_merge_chunks_preserves_order(self):
        """Test that merged chunks maintain order"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add chunks in sequence with distinguishable data
        chunks = []
        for i in range(3):
            # Create audio with a distinct value
            audio_data = np.full(16000, float(i), dtype=np.float32)
            chunks.append(audio_data)
            self.receiver.add_chunk(
                session_id=session.session_id,
                chunk_number=i,
                audio_data=audio_data
            )
        
        # Merge
        success, merged, error = self.receiver.merge_chunks(session.session_id)
        
        assert success is True
        
        # Verify order
        for i, chunk in enumerate(chunks):
            start = i * 16000
            end = start + 16000
            section = merged[start:end]
            assert np.allclose(section, float(i))
    
    def test_merge_empty_session(self):
        """Test merging with no chunks"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        success, merged, error = self.receiver.merge_chunks(session.session_id)
        
        assert success is False
        assert error is not None
        assert 'no chunks' in error.lower()
    
    def test_generate_embedding(self):
        """Test generating embedding from chunks"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add chunks
        for i in range(2):
            audio_data = np.random.randn(16000).astype(np.float32)
            self.receiver.add_chunk(
                session_id=session.session_id,
                chunk_number=i,
                audio_data=audio_data
            )
        
        # Generate embedding
        success, embedding, error = self.receiver.generate_embedding(session.session_id)
        
        assert success is True
        assert error is None
        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert session.status == ChunkReceiverStatus.COMPLETED
        assert session.embedding is not None
    
    def test_process_session_complete_flow(self):
        """Test complete session processing flow"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add multiple chunks
        for i in range(3):
            audio_data = np.random.randn(16000).astype(np.float32)
            self.receiver.add_chunk(
                session_id=session.session_id,
                chunk_number=i,
                audio_data=audio_data
            )
        
        # Process session (merge + generate embedding)
        success, embedding, error = self.receiver.process_session(session.session_id)
        
        assert success is True
        assert error is None
        assert embedding is not None
        assert len(embedding) > 0  # Should have embedding dimension
        assert session.merged_audio is not None
        assert session.embedded is not None
    
    def test_get_session_info(self):
        """Test getting session information"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add a chunk
        audio_data = np.random.randn(16000).astype(np.float32)
        self.receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=1,
            audio_data=audio_data
        )
        
        # Get info
        info = self.receiver.get_session_info(session.session_id)
        
        assert info is not None
        assert info['session_id'] == session.session_id
        assert info['phone_number'] == '+1234567890'
        assert info['chunks_received'] == 1
        assert info['status'] == 'receiving_chunks'
    
    def test_cleanup_session(self):
        """Test cleaning up a session"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        success = self.receiver.cleanup_session(session.session_id)
        assert success is True
        
        # Verify session is gone
        retrieved = self.receiver.get_session(session.session_id)
        assert retrieved is None
    
    def test_cleanup_nonexistent_session(self):
        """Test cleaning up non-existent session"""
        success = self.receiver.cleanup_session('invalid_id')
        assert success is False
    
    def test_global_instance(self):
        """Test global receiver instance"""
        receiver1 = get_chunk_receiver()
        receiver2 = get_chunk_receiver()
        
        # Should be the same instance
        assert receiver1 is receiver2
    
    def test_get_stats(self):
        """Test getting receiver statistics"""
        # Create a few sessions
        session1 = self.receiver.create_session('+1111111111', 'enrollment')
        session2 = self.receiver.create_session('+2222222222', 'verification')
        
        stats = self.receiver.get_stats()
        
        assert stats['total_sessions'] == 2
        assert stats['active_sessions'] == 2
        assert stats['completed_sessions'] == 0
        assert stats['error_sessions'] == 0
    
    def test_enrollment_vs_verification_modes(self):
        """Test both enrollment and verification modes"""
        # Enrollment
        enroll_session = self.receiver.create_session('+1234567890', 'enrollment')
        assert enroll_session.mode == 'enrollment'
        
        # Verification
        verify_session = self.receiver.create_session('+1234567890', 'verification')
        assert verify_session.mode == 'verification'
    
    def test_chunk_duration_calculation(self):
        """Test chunk duration is calculated correctly"""
        session = self.receiver.create_session('+1234567890', 'enrollment')
        
        # Add chunk with explicit duration
        audio_data = np.random.randn(16000).astype(np.float32)
        self.receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=1,
            audio_data=audio_data,
            duration_ms=1000
        )
        
        chunk = session.chunks_received[0]
        assert chunk.duration_ms == 1000


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
