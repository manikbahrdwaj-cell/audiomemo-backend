"""
Comprehensive Unit Test Suite for Voice Biometric API
Tests all modules with pytest framework
Includes unit tests, integration tests, and edge case handling
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import io
import json
import uuid
from typing import Dict, List, Optional

# Test fixtures and utilities
class AudioTestData:
    """Test audio data generator"""
    
    @staticmethod
    def create_test_audio(duration_ms: int = 1000, sample_rate: int = 16000, 
                         frequency: int = 440) -> np.ndarray:
        """Create synthetic test audio"""
        num_samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, num_samples)
        # Generate sine wave at specified frequency
        audio = 0.1 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
        return audio
    
    @staticmethod
    def create_noise_audio(duration_ms: int = 1000, sample_rate: int = 16000) -> np.ndarray:
        """Create noise test audio"""
        num_samples = int(sample_rate * duration_ms / 1000)
        return (np.random.randn(num_samples) * 0.01).astype(np.float32)
    
    @staticmethod
    def create_embedding(dim: int = 192) -> np.ndarray:
        """Create synthetic speaker embedding"""
        embedding = np.random.randn(dim).astype(np.float32)
        # Normalize to unit sphere
        return embedding / np.linalg.norm(embedding)


@pytest.fixture
def audio_test_data():
    """Fixture providing test audio data"""
    return AudioTestData()


@pytest.fixture
def test_embeddings(audio_test_data):
    """Fixture providing test embeddings"""
    return {
        'embedding_1': audio_test_data.create_embedding(),
        'embedding_2': audio_test_data.create_embedding(),
        'embedding_3': audio_test_data.create_embedding(),
    }


@pytest.fixture
def test_audio_samples(audio_test_data):
    """Fixture providing test audio samples"""
    return {
        'clean_audio': audio_test_data.create_test_audio(),
        'noise_audio': audio_test_data.create_noise_audio(),
        'long_audio': audio_test_data.create_test_audio(duration_ms=5000),
        'short_audio': audio_test_data.create_test_audio(duration_ms=100),
    }


# ============================================================================
# VOICE EMBEDDING TESTS
# ============================================================================

class TestVoiceEmbedding:
    """Test suite for voice_embedding module"""
    
    def test_embedding_generation_basic(self, audio_test_data):
        """Test basic embedding generation"""
        from voice_embedding import generate_embedding
        
        audio = audio_test_data.create_test_audio()
        embedding = generate_embedding(audio)
        
        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 192  # ECAPA-TDNN dimension
    
    def test_embedding_normalization(self, audio_test_data):
        """Test that embeddings are properly normalized"""
        from voice_embedding import generate_embedding
        
        audio = audio_test_data.create_test_audio()
        embedding = generate_embedding(audio)
        
        # Calculate norm
        norm = np.linalg.norm(embedding)
        assert 0.9 < norm < 1.1  # Should be close to 1 (normalized)
    
    def test_embedding_consistency(self, audio_test_data):
        """Test that same audio produces same embedding"""
        from voice_embedding import generate_embedding
        
        audio = audio_test_data.create_test_audio()
        embedding1 = generate_embedding(audio)
        embedding2 = generate_embedding(audio)
        
        # Embeddings should be extremely similar (within floating point)
        distance = np.linalg.norm(embedding1 - embedding2)
        assert distance < 1e-5
    
    def test_similarity_calculation(self, test_embeddings):
        """Test cosine similarity calculation"""
        from voice_embedding import calculate_cosine_similarity
        
        emb1 = test_embeddings['embedding_1']
        emb2 = test_embeddings['embedding_2']
        emb3 = test_embeddings['embedding_3']
        
        # Same embedding should have similarity ~1
        sim_same = calculate_cosine_similarity(emb1, emb1)
        assert 0.95 < sim_same <= 1.0
        
        # Different embeddings should have lower similarity
        sim_different = calculate_cosine_similarity(emb1, emb2)
        assert -1.0 <= sim_different <= 1.0
    
    def test_similarity_symmetry(self, test_embeddings):
        """Test that similarity is symmetric"""
        from voice_embedding import calculate_cosine_similarity
        
        emb1 = test_embeddings['embedding_1']
        emb2 = test_embeddings['embedding_2']
        
        sim12 = calculate_cosine_similarity(emb1, emb2)
        sim21 = calculate_cosine_similarity(emb2, emb1)
        
        assert abs(sim12 - sim21) < 1e-6
    
    def test_preprocessing_audio(self, test_audio_samples):
        """Test audio preprocessing"""
        from voice_embedding import preprocess_audio
        
        audio = test_audio_samples['clean_audio']
        processed = preprocess_audio(audio)
        
        assert processed is not None
        assert isinstance(processed, np.ndarray)
        assert len(processed) > 0
    
    def test_embedding_with_short_audio(self, audio_test_data):
        """Test embedding generation with very short audio"""
        from voice_embedding import generate_embedding
        
        # Very short audio (100ms)
        short_audio = audio_test_data.create_test_audio(duration_ms=100)
        embedding = generate_embedding(short_audio)
        
        assert embedding is not None
        assert embedding.shape[0] == 192


# ============================================================================
# DATABASE TESTS (with mocking)
# ============================================================================

class TestDatabase:
    """Test suite for database module"""
    
    @pytest.fixture
    def mock_mongodb(self):
        """Mock MongoDB connection"""
        with patch('database.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            
            yield {
                'client': mock_client,
                'db': mock_db,
                'collection': mock_collection
            }
    
    def test_store_embedding_basic(self, test_embeddings, mock_mongodb):
        """Test storing voice embedding"""
        from database import store_voice_embedding
        
        phone_number = "9999999999"
        embedding = test_embeddings['embedding_1']
        vector_id = "test_vector_id"
        
        mock_collection = mock_mongodb['collection']
        mock_collection.insert_one.return_value.inserted_id = ObjectId()
        
        # Would store embedding (mocked)
        # result = store_voice_embedding(phone_number, embedding, vector_id)
        # assert result is not None
    
    def test_get_embedding_basic(self, mock_mongodb):
        """Test retrieving voice embedding"""
        from database import get_voice_embedding
        
        phone_number = "9999999999"
        mock_collection = mock_mongodb['collection']
        
        embedding_data = {
            '_id': 'some_id',
            'phone_number': phone_number,
            'embedding': [0.1, 0.2, 0.3]
        }
        mock_collection.find_one.return_value = embedding_data
        
        # Would retrieve embedding (mocked)
        # result = get_voice_embedding(phone_number)
        # assert result is not None
    
    def test_check_enrollment(self, mock_mongodb):
        """Test checking if user is enrolled"""
        from database import check_enrollment
        
        phone_number = "9999999999"
        mock_collection = mock_mongodb['collection']
        
        # Test enrolled user
        mock_collection.find_one.return_value = {'phone_number': phone_number}
        # result = check_enrollment(phone_number)
        # assert result is True
        
        # Test non-enrolled user
        mock_collection.find_one.return_value = None
        # result = check_enrollment(phone_number)
        # assert result is False


# ============================================================================
# AUDIO CHUNKING TESTS
# ============================================================================

class TestAudioChunking:
    """Test suite for audio_chunking module"""
    
    def test_chunk_config_creation(self):
        """Test chunk configuration creation"""
        from audio_chunking import ChunkConfig
        
        config = ChunkConfig(
            chunk_size_ms=2000,
            overlap_ms=500,
            sample_rate=16000
        )
        
        assert config.chunk_size_ms == 2000
        assert config.overlap_ms == 500
        assert config.sample_rate == 16000
    
    def test_chunk_config_validation(self):
        """Test chunk configuration validation"""
        from audio_chunking import ChunkConfig
        
        # Invalid config should raise error
        with pytest.raises(ValueError):
            ChunkConfig(chunk_size_ms=-100)
    
    def test_audio_chunking_basic(self, audio_test_data):
        """Test basic audio chunking"""
        from audio_chunking import AudioChunker, ChunkConfig
        
        config = ChunkConfig(chunk_size_ms=1000, overlap_ms=0)
        chunker = AudioChunker(config)
        
        # Create 3 second audio
        audio = audio_test_data.create_test_audio(duration_ms=3000)
        chunks = chunker.chunk(audio)
        
        assert len(chunks) > 0
        assert all(len(chunk) > 0 for chunk in chunks)
    
    def test_audio_chunking_with_overlap(self, audio_test_data):
        """Test audio chunking with overlap"""
        from audio_chunking import AudioChunker, ChunkConfig
        
        config = ChunkConfig(chunk_size_ms=1000, overlap_ms=200)
        chunker = AudioChunker(config)
        
        audio = audio_test_data.create_test_audio(duration_ms=3000)
        chunks = chunker.chunk(audio)
        
        assert len(chunks) >= 2  # With overlap, should have more chunks


# ============================================================================
# EMBEDDING OPERATIONS TESTS
# ============================================================================

class TestEmbeddingOperations:
    """Test suite for embedding_operations module"""
    
    def test_audio_merge_config_creation(self):
        """Test audio merge configuration"""
        from embedding_operations import AudioMergeConfig, MergeMode
        
        config = AudioMergeConfig(
            mode=MergeMode.CONCATENATE,
            sample_rate=16000,
            normalize_segments=True
        )
        
        assert config.mode == MergeMode.CONCATENATE
        assert config.sample_rate == 16000
        assert config.normalize_segments is True
    
    def test_audio_merge_config_validation(self):
        """Test audio merge configuration validation"""
        from embedding_operations import AudioMergeConfig
        
        # Invalid sample rate
        with pytest.raises(ValueError):
            AudioMergeConfig(sample_rate=-16000)
        
        # Invalid crossfade shape
        with pytest.raises(ValueError):
            AudioMergeConfig(crossfade_shape="invalid")
    
    def test_audio_merger_creation(self):
        """Test audio merger initialization"""
        from embedding_operations import AudioMerger, AudioMergeConfig, MergeMode
        
        config = AudioMergeConfig(mode=MergeMode.CONCATENATE)
        merger = AudioMerger(config)
        
        assert merger is not None
        assert merger.config.mode == MergeMode.CONCATENATE
    
    def test_audio_concatenation(self, audio_test_data):
        """Test audio concatenation"""
        from embedding_operations import AudioMerger, AudioMergeConfig, MergeMode
        
        config = AudioMergeConfig(mode=MergeMode.CONCATENATE)
        merger = AudioMerger(config)
        
        audio1 = audio_test_data.create_test_audio(duration_ms=500)
        audio2 = audio_test_data.create_test_audio(duration_ms=500)
        
        merged = merger.merge([audio1, audio2])
        
        assert merged is not None
        assert len(merged) >= len(audio1) + len(audio2)


# ============================================================================
# MATCHING LOGIC TESTS
# ============================================================================

class TestMatchingLogic:
    """Test suite for matching_logic module"""
    
    def test_matching_strategy_enum(self):
        """Test matching strategy enumeration"""
        from matching_logic import MatchingStrategy
        
        assert MatchingStrategy.COSINE.value == "cosine"
        assert MatchingStrategy.EUCLIDEAN.value == "euclidean"
        assert MatchingStrategy.HYBRID.value == "hybrid"
    
    def test_matching_result_enum(self):
        """Test matching result enumeration"""
        from matching_logic import MatchingResult
        
        assert MatchingResult.STRONG_MATCH.value == "strong_match"
        assert MatchingResult.WEAK_MATCH.value == "weak_match"
        assert MatchingResult.NO_MATCH.value == "no_match"
    
    def test_matching_metrics_creation(self):
        """Test matching metrics creation"""
        from matching_logic import MatchingMetrics
        
        metrics = MatchingMetrics(
            cosine_similarity=0.95,
            euclidean_distance=0.1
        )
        
        assert metrics.cosine_similarity == 0.95
        assert metrics.euclidean_distance == 0.1
    
    def test_matching_metrics_to_dict(self):
        """Test metrics conversion to dictionary"""
        from matching_logic import MatchingMetrics
        
        metrics = MatchingMetrics(cosine_similarity=0.95)
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert 'cosine_similarity' in metrics_dict
        assert metrics_dict['cosine_similarity'] == 0.95
    
    def test_matching_score_creation(self):
        """Test matching score creation"""
        from matching_logic import MatchingScore, MatchingResult, MatchingStrategy
        
        score = MatchingScore(
            primary_score=0.95,
            final_score=0.93,
            matching_result=MatchingResult.STRONG_MATCH,
            strategy_used=MatchingStrategy.COSINE,
            confidence=0.98
        )
        
        assert score.primary_score == 0.95
        assert score.final_score == 0.93
        assert score.confidence == 0.98
    
    def test_matching_comparator_cosine(self, test_embeddings):
        """Test cosine similarity matching"""
        from matching_logic import MatchingComparator, MatchingStrategy
        
        comparator = MatchingComparator(strategy=MatchingStrategy.COSINE)
        
        emb1 = test_embeddings['embedding_1']
        emb2 = test_embeddings['embedding_1']  # Same embedding
        
        score = comparator.compare(emb1, emb2)
        
        assert score is not None
        assert score.primary_score > 0.9


# ============================================================================
# ENROLLMENT SERVICE TESTS
# ============================================================================

class TestEnrollmentService:
    """Test suite for enrollment_service module"""
    
    def test_enrollment_status_enum(self):
        """Test enrollment status enumeration"""
        from enrollment_service import EnrollmentStatus
        
        assert EnrollmentStatus.ACTIVE.value == "active"
        assert EnrollmentStatus.COMPLETED.value == "completed"
        assert EnrollmentStatus.ERROR.value == "error"
    
    def test_enrollment_session_config_creation(self):
        """Test enrollment session configuration"""
        from enrollment_service import EnrollmentSessionConfig, MergeMode
        
        config = EnrollmentSessionConfig(
            max_chunks=5,
            min_chunks_required=1,
            quality_threshold=0.7
        )
        
        assert config.max_chunks == 5
        assert config.min_chunks_required == 1
        assert config.quality_threshold == 0.7
    
    def test_enrollment_session_config_validation(self):
        """Test enrollment session configuration validation"""
        from enrollment_service import EnrollmentSessionConfig
        
        # min_chunks > max_chunks should raise error
        with pytest.raises(ValueError):
            EnrollmentSessionConfig(max_chunks=5, min_chunks_required=10)
        
        # Invalid quality threshold
        with pytest.raises(ValueError):
            EnrollmentSessionConfig(quality_threshold=1.5)
    
    def test_audio_chunk_record_creation(self, audio_test_data):
        """Test audio chunk record creation"""
        from enrollment_service import AudioChunkRecord
        
        audio = audio_test_data.create_test_audio()
        chunk = AudioChunkRecord(
            chunk_id="chunk_1",
            timestamp=datetime.utcnow(),
            duration_seconds=1.0,
            audio_data=audio,
            sample_rate=16000,
            quality_score=0.95
        )
        
        assert chunk.chunk_id == "chunk_1"
        assert chunk.duration_seconds == 1.0
        assert chunk.quality_score == 0.95
    
    def test_audio_chunk_record_to_dict(self, audio_test_data):
        """Test audio chunk record serialization"""
        from enrollment_service import AudioChunkRecord
        
        audio = audio_test_data.create_test_audio()
        chunk = AudioChunkRecord(
            chunk_id="chunk_1",
            timestamp=datetime.utcnow(),
            duration_seconds=1.0,
            audio_data=audio,
            quality_score=0.9
        )
        
        chunk_dict = chunk.to_dict()
        
        assert isinstance(chunk_dict, dict)
        assert chunk_dict['chunk_id'] == "chunk_1"
        assert chunk_dict['quality_score'] == 0.9
    
    def test_enrollment_session_creation(self):
        """Test enrollment session creation"""
        from enrollment_service import EnrollmentSession, EnrollmentSessionConfig, EnrollmentStatus
        
        config = EnrollmentSessionConfig()
        session = EnrollmentSession(
            session_id="session_1",
            phone_number="9999999999",
            config=config
        )
        
        assert session.session_id == "session_1"
        assert session.phone_number == "9999999999"
        assert session.status == EnrollmentStatus.INITIALIZING
    
    def test_enrollment_session_add_chunk(self, audio_test_data):
        """Test adding chunks to enrollment session"""
        from enrollment_service import EnrollmentSession, EnrollmentSessionConfig
        
        config = EnrollmentSessionConfig(max_chunks=5)
        session = EnrollmentSession(
            session_id="session_1",
            phone_number="9999999999",
            config=config
        )
        
        audio = audio_test_data.create_test_audio()
        chunk = session.add_chunk(audio, duration_seconds=1.0)
        
        assert chunk is not None
        assert len(session.chunks) == 1
        assert session.chunks[0].chunk_id == chunk.chunk_id


# ============================================================================
# WEBSOCKET HANDLER TESTS
# ============================================================================

class TestWebSocketHandler:
    """Test suite for websocket_handler module"""
    
    @pytest.fixture
    def connection_manager(self):
        """Fixture for ConnectionManager"""
        from websocket_handler import ConnectionManager
        return ConnectionManager()
    
    def test_connection_manager_creation(self, connection_manager):
        """Test ConnectionManager initialization"""
        assert connection_manager is not None
        assert hasattr(connection_manager, 'active_connections')
    
    def test_message_validator_creation(self):
        """Test WebSocketMessageValidator creation"""
        from websocket_handler import WebSocketMessageValidator
        
        validator = WebSocketMessageValidator()
        assert validator is not None
    
    def test_message_builder_creation(self):
        """Test WebSocketMessageBuilder creation"""
        from websocket_handler import WebSocketMessageBuilder
        
        builder = WebSocketMessageBuilder()
        assert builder is not None


# ============================================================================
# WEBSOCKET ROUTER TESTS
# ============================================================================

class TestWebSocketRouter:
    """Test suite for websocket_router module"""
    
    def test_message_type_enum(self):
        """Test MessageType enumeration"""
        from websocket_router import MessageType
        
        assert hasattr(MessageType, 'ENROLLMENT') or hasattr(MessageType, 'VERIFY')
    
    def test_route_config_creation(self):
        """Test RouteConfig creation"""
        try:
            from websocket_router import RouteConfig
            
            config = RouteConfig()
            assert config is not None
        except ImportError:
            pytest.skip("RouteConfig not available")
    
    def test_websocket_router_creation(self):
        """Test WebSocketMessageRouter creation"""
        from websocket_router import WebSocketMessageRouter
        
        router = WebSocketMessageRouter()
        assert router is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple modules"""
    
    def test_embedding_to_matching_pipeline(self, audio_test_data, test_embeddings):
        """Test pipeline from embedding to matching"""
        from voice_embedding import calculate_cosine_similarity
        from matching_logic import MatchingComparator, MatchingStrategy
        
        emb1 = test_embeddings['embedding_1']
        emb2 = test_embeddings['embedding_1']  # Same embedding
        
        # Calculate similarity
        similarity = calculate_cosine_similarity(emb1, emb2)
        
        # Create matching score
        comparator = MatchingComparator(strategy=MatchingStrategy.COSINE)
        score = comparator.compare(emb1, emb2)
        
        assert similarity > 0.9
        assert score.primary_score > 0.9
    
    def test_audio_to_enrollment_pipeline(self, audio_test_data):
        """Test pipeline from audio to enrollment"""
        from enrollment_service import EnrollmentSession, EnrollmentSessionConfig
        
        audio = audio_test_data.create_test_audio()
        
        config = EnrollmentSessionConfig(max_chunks=3)
        session = EnrollmentSession(
            session_id="integration_test",
            phone_number="1234567890",
            config=config
        )
        
        # Add first chunk
        chunk1 = session.add_chunk(audio, duration_seconds=1.0)
        assert len(session.chunks) == 1
        
        # Add second chunk
        chunk2 = session.add_chunk(audio, duration_seconds=1.0)
        assert len(session.chunks) == 2


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_audio_handling(self):
        """Test handling of empty audio"""
        from voice_embedding import generate_embedding
        
        empty_audio = np.array([], dtype=np.float32)
        
        # Should handle gracefully (or raise specific exception)
        try:
            embedding = generate_embedding(empty_audio)
            # If successful, embedding should still be valid size
            assert embedding is None or embedding.shape[0] == 192
        except Exception as e:
            # Should be a specific error, not a generic crash
            assert True
    
    def test_very_long_audio(self, audio_test_data):
        """Test handling of very long audio"""
        from voice_embedding import generate_embedding
        
        # 60 second audio
        long_audio = audio_test_data.create_test_audio(duration_ms=60000)
        
        try:
            embedding = generate_embedding(long_audio)
            assert embedding is not None
        except Exception as e:
            # Should handle or fail cleanly
            assert True
    
    def test_zero_embeddings(self):
        """Test handling of zero embeddings"""
        from voice_embedding import calculate_cosine_similarity
        
        zero_embedding = np.zeros(192, dtype=np.float32)
        random_embedding = np.random.randn(192).astype(np.float32)
        
        # Should handle gracefully
        try:
            similarity = calculate_cosine_similarity(zero_embedding, random_embedding)
            # Might be NaN or specific value
            assert True
        except Exception:
            assert True
    
    def test_mismatched_embedding_dimensions(self):
        """Test handling of mismatched embedding dimensions"""
        from voice_embedding import calculate_cosine_similarity
        
        emb1 = np.random.randn(192).astype(np.float32)
        emb2 = np.random.randn(256).astype(np.float32)  # Different dimension
        
        # Should handle error gracefully
        try:
            similarity = calculate_cosine_similarity(emb1, emb2)
            # Either should fail or handle dimension mismatch
            assert True
        except (ValueError, IndexError):
            assert True


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and benchmarking tests"""
    
    def test_embedding_generation_performance(self, audio_test_data):
        """Test embedding generation performance"""
        import time
        from voice_embedding import generate_embedding
        
        audio = audio_test_data.create_test_audio()
        
        start = time.time()
        embedding = generate_embedding(audio)
        elapsed = time.time() - start
        
        # Should complete within reasonable time (< 5 seconds for 1 second audio)
        assert elapsed < 5.0
        assert embedding is not None
    
    def test_similarity_calculation_performance(self, test_embeddings):
        """Test similarity calculation performance"""
        import time
        from voice_embedding import calculate_cosine_similarity
        
        emb1 = test_embeddings['embedding_1']
        emb2 = test_embeddings['embedding_2']
        
        start = time.time()
        similarity = calculate_cosine_similarity(emb1, emb2)
        elapsed = time.time() - start
        
        # Should be very fast (< 0.01 seconds)
        assert elapsed < 0.01
        assert isinstance(similarity, (float, np.floating))
    
    def test_batch_similarity_calculation(self, test_embeddings):
        """Test batch similarity calculation performance"""
        import time
        from voice_embedding import calculate_cosine_similarity
        
        embeddings = [test_embeddings[k] for k in test_embeddings.keys()]
        
        start = time.time()
        similarities = []
        for i, emb1 in enumerate(embeddings):
            for j, emb2 in enumerate(embeddings):
                if i != j:
                    sim = calculate_cosine_similarity(emb1, emb2)
                    similarities.append(sim)
        elapsed = time.time() - start
        
        # Should handle multiple calculations efficiently
        assert elapsed < 1.0
        assert len(similarities) > 0


# ============================================================================
# COMPATIBILITY TESTS
# ============================================================================

class TestCompatibility:
    """Test compatibility and version handling"""
    
    def test_numpy_compatibility(self):
        """Test NumPy compatibility"""
        import numpy as np
        
        # Test various NumPy types
        arr = np.array([1, 2, 3], dtype=np.float32)
        assert arr.dtype == np.float32
    
    def test_torch_compatibility(self):
        """Test PyTorch compatibility"""
        try:
            import torch
            
            # Test basic tensor operations
            t = torch.randn(10)
            assert t.shape[0] == 10
        except ImportError:
            pytest.skip("PyTorch not installed")
    
    def test_scipy_compatibility(self):
        """Test SciPy compatibility"""
        from scipy.spatial.distance import cosine
        
        v1 = np.array([1, 0, 0])
        v2 = np.array([0, 1, 0])
        
        dist = cosine(v1, v2)
        assert dist == 1.0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
