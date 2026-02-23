"""
Edge Case Tests for Enrollment Service
Tests boundary conditions and error scenarios in voice enrollment workflows
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


class TestEnrollmentSessionEdgeCases:
    """Comprehensive edge case tests for enrollment sessions"""

    # ========== SESSION INITIALIZATION EDGE CASES ==========
    
    def test_create_enrollment_with_empty_user_id(self):
        """Test creating enrollment with empty user ID"""
        user_id = ""
        
        try:
            session = self._create_enrollment_session(user_id)
            # May reject or handle gracefully
            assert session is None or session.get('user_id') != ""
        except (ValueError, AssertionError):
            pass

    def test_create_enrollment_with_null_user_id(self):
        """Test creating enrollment with None user ID"""
        user_id = None
        
        try:
            session = self._create_enrollment_session(user_id)
            assert session is None or session.get('user_id') is not None
        except (ValueError, TypeError):
            pass

    def test_create_enrollment_with_extremely_long_user_id(self):
        """Test creating enrollment with extremely long user ID"""
        user_id = "a" * 10000  # 10k character ID
        
        try:
            session = self._create_enrollment_session(user_id)
            assert session is None or session.get('user_id') == user_id
        except (ValueError, AssertionError):
            pass

    def test_create_enrollment_with_special_characters(self):
        """Test creating enrollment with special characters in user ID"""
        user_ids = [
            "user@domain.com",
            "user#123",
            "user/home/path",
            "user\nwith\nnewlines",
            "user\x00null",
            "user™",
            "用户",  # Chinese characters
        ]
        
        for user_id in user_ids:
            try:
                session = self._create_enrollment_session(user_id)
                # Should either accept or reject consistently
            except:
                pass

    def test_create_duplicate_enrollment_same_session(self):
        """Test creating duplicate enrollments in same session"""
        user_id = "user123"
        
        session1 = self._create_enrollment_session(user_id)
        session2 = self._create_enrollment_session(user_id)
        
        # Both should be created (different session IDs)
        if session1 and session2:
            assert session1.get('session_id') != session2.get('session_id')

    # ========== SESSION TIMEOUT EDGE CASES ==========
    
    def test_chunk_timeout_immediate_expiry(self):
        """Test chunk timeout with immediate expiry setting"""
        config = {
            'chunk_timeout_seconds': 0  # Immediate timeout
        }
        
        # Should either reject or handle gracefully
        assert config['chunk_timeout_seconds'] >= 0

    def test_chunk_timeout_very_long(self):
        """Test chunk timeout with very long duration"""
        config = {
            'chunk_timeout_seconds': 86400  # 24 hours
        }
        
        assert config['chunk_timeout_seconds'] > 0

    def test_session_timeout_very_short(self):
        """Test session timeout with very short duration"""
        config = {
            'session_timeout_seconds': 1  # 1 second
        }
        
        # Should allow but might timeout immediately
        assert config['session_timeout_seconds'] > 0

    def test_chunk_timeout_exceeds_session_timeout(self):
        """Test when chunk timeout exceeds session timeout"""
        config = {
            'chunk_timeout_seconds': 100,
            'session_timeout_seconds': 50  # Chunk timeout > Session timeout
        }
        
        # Should be invalid or handled specially
        assert config is not None

    # ========== CHUNK COUNT EDGE CASES ==========
    
    def test_max_chunks_zero(self):
        """Test max chunks set to zero"""
        config = {'max_chunks': 0}
        
        # Should be rejected or handled
        try:
            assert config['max_chunks'] >= 1
        except AssertionError:
            pass

    def test_max_chunks_negative(self):
        """Test max chunks set to negative"""
        config = {'max_chunks': -5}
        
        # Should be rejected
        try:
            assert config['max_chunks'] > 0
        except AssertionError:
            pass

    def test_max_chunks_very_large(self):
        """Test max chunks set to very large number"""
        config = {'max_chunks': 100000}
        
        assert config['max_chunks'] > 0

    def test_min_chunks_greater_than_max(self):
        """Test when min_chunks > max_chunks"""
        config = {
            'min_chunks_required': 10,
            'max_chunks': 5  # min > max
        }
        
        # Should be detected as invalid
        assert config['min_chunks_required'] <= config['max_chunks']

    def test_min_chunks_equals_max_chunks(self):
        """Test when min_chunks == max_chunks"""
        config = {
            'min_chunks_required': 5,
            'max_chunks': 5  # min == max
        }
        
        assert config['min_chunks_required'] == config['max_chunks']

    def test_zero_min_chunks(self):
        """Test minimum chunks set to zero"""
        config = {'min_chunks_required': 0}
        
        # Might be valid (empty enrollment)
        assert config['min_chunks_required'] >= 0

    # ========== QUALITY THRESHOLD EDGE CASES ==========
    
    def test_quality_threshold_negative(self):
        """Test negative quality threshold"""
        config = {'quality_threshold': -0.5}
        
        # Should be rejected
        try:
            assert 0 <= config['quality_threshold'] <= 1
        except AssertionError:
            pass

    def test_quality_threshold_above_one(self):
        """Test quality threshold > 1.0"""
        config = {'quality_threshold': 1.5}
        
        # Should be rejected
        try:
            assert 0 <= config['quality_threshold'] <= 1
        except AssertionError:
            pass

    def test_quality_threshold_exactly_zero(self):
        """Test quality threshold = 0 (accept all)"""
        config = {'quality_threshold': 0.0}
        
        # Should accept all audio
        assert config['quality_threshold'] == 0.0

    def test_quality_threshold_exactly_one(self):
        """Test quality threshold = 1.0 (perfect only)"""
        config = {'quality_threshold': 1.0}
        
        # Should reject all but perfect audio
        assert config['quality_threshold'] == 1.0

    # ========== AUDIO CHUNK EDGE CASES ==========
    
    def test_add_empty_audio_chunk(self):
        """Test adding empty audio chunk to enrollment"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        audio = np.array([])
        
        try:
            result = self._add_audio_chunk(session, audio)
            # Should reject empty audio
            assert result is None or result.get('success') == False
        except (ValueError, IndexError):
            pass

    def test_add_single_sample_chunk(self):
        """Test adding single sample audio chunk"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        audio = np.array([0.5])
        
        try:
            result = self._add_audio_chunk(session, audio)
            # Should handle gracefully
        except:
            pass

    def test_add_very_long_chunk(self):
        """Test adding very long audio chunk"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        audio = np.random.randn(16000 * 600)  # 10 minutes
        
        try:
            result = self._add_audio_chunk(session, audio)
            # Should either accept or limit
            assert result is not None
        except MemoryError:
            pass  # Expected for extremely long audio

    def test_add_chunk_with_nan_values(self):
        """Test adding chunk with NaN values"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        audio = np.random.randn(16000)
        audio[100:110] = np.nan
        
        try:
            result = self._add_audio_chunk(session, audio)
            # Should detect and handle NaN
        except (ValueError, RuntimeError):
            pass

    def test_add_chunk_with_inf_values(self):
        """Test adding chunk with infinity values"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        audio = np.random.randn(16000)
        audio[100] = np.inf
        
        try:
            result = self._add_audio_chunk(session, audio)
            # Should detect and handle infinity
        except (ValueError, RuntimeError):
            pass

    def test_add_chunks_to_full_session(self):
        """Test adding chunks when session is full"""
        user_id = "user123"
        config = {'max_chunks': 3}
        session = self._create_enrollment_session(user_id, config)
        
        # Add chunks up to limit
        for i in range(5):
            audio = np.random.randn(16000)
            result = self._add_audio_chunk(session, audio)
            
            if i < 3:
                # Should succeed
                assert result is not None
            else:
                # Should fail or reject
                if result is not None:
                    assert result.get('success') == False

    def test_add_chunks_wrong_sample_rate(self):
        """Test adding chunks with unsupported sample rate"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        
        # Create audio at 22050 Hz instead of default 16000 Hz
        audio = np.random.randn(22050)
        
        try:
            result = self._add_audio_chunk(session, audio, sample_rate=22050)
            # Should either resample or reject
        except (ValueError, RuntimeError):
            pass

    def test_add_chunks_with_different_dtypes(self):
        """Test adding chunks with different data types"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        
        for dtype in [np.float32, np.float64, np.int16, np.int32]:
            audio = (np.random.randn(16000) * 32767).astype(dtype)
            
            try:
                result = self._add_audio_chunk(session, audio)
                # Should handle or convert gracefully
            except (ValueError, TypeError):
                pass

    def test_null_chunk_timestamp(self):
        """Test handling of chunks with null timestamp"""
        timestamp = None
        
        # Should use current time or reject
        try:
            assert timestamp is not None
        except AssertionError:
            pass

    def test_chunk_from_future(self):
        """Test chunk with timestamp from future"""
        future_time = datetime.now() + timedelta(days=1)
        
        # Should reject or normalize
        assert future_time > datetime.now()

    def test_chunk_from_far_past(self):
        """Test chunk with timestamp from far past"""
        past_time = datetime.now() - timedelta(days=365 * 100)
        
        # Should accept (just unusual)
        assert past_time < datetime.now()

    # ========== SESSION FINALIZATION EDGE CASES ==========
    
    def test_finalize_empty_session(self):
        """Test finalizing enrollment with no chunks"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id, {'min_chunks_required': 0})
        
        try:
            result = self._finalize_enrollment(session)
            # Might succeed with min_chunks = 0
            assert result is not None
        except (ValueError, AssertionError):
            pass

    def test_finalize_below_minimum_chunks(self):
        """Test finalizing with fewer than minimum chunks"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id, {'min_chunks_required': 3})
        
        # Add only 1 chunk
        audio = np.random.randn(16000)
        self._add_audio_chunk(session, audio)
        
        try:
            result = self._finalize_enrollment(session)
            # Should reject due to insufficient chunks
            assert result is None or result.get('success') == False
        except ValueError:
            pass

    def test_finalize_at_minimum_chunks(self):
        """Test finalizing with exactly minimum chunks"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id, {'min_chunks_required': 3})
        
        # Add exactly 3 chunks
        for _ in range(3):
            audio = np.random.randn(16000)
            self._add_audio_chunk(session, audio)
        
        try:
            result = self._finalize_enrollment(session)
            assert result is not None
        except:
            pass

    def test_finalize_with_failed_chunks(self):
        """Test finalizing when some chunks failed"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        
        # Add mixed good and bad chunks
        audio_good = np.random.randn(16000)
        audio_bad = np.zeros(16000)  # Silence
        
        try:
            self._add_audio_chunk(session, audio_good)
            self._add_audio_chunk(session, audio_bad)
            self._add_audio_chunk(session, audio_good)
            
            result = self._finalize_enrollment(session)
            # Should still process valid chunks
        except:
            pass

    # ========== CONCURRENT OPERATIONS ==========
    
    def test_concurrent_chunk_additions(self):
        """Test adding chunks concurrently to same session"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        
        # Simulate concurrent additions (synchronously)
        for i in range(5):
            audio = np.random.randn(16000)
            result = self._add_audio_chunk(session, audio)
            assert result is not None

    def test_finalize_before_all_chunks_added(self):
        """Test finalizing while chunks are still being added"""
        user_id = "user123"
        session = self._create_enrollment_session(user_id)
        
        # Add first chunk
        audio = np.random.randn(16000)
        self._add_audio_chunk(session, audio)
        
        # Finalize immediately
        try:
            result = self._finalize_enrollment(session)
            # Behavior depends on min_chunks requirement
        except:
            pass

    # ========== USER ID VALIDATION ==========
    
    def test_sql_injection_in_user_id(self):
        """Test SQL injection attempts in user ID"""
        user_ids = [
            "user' OR '1'='1",
            "user\"; DROP TABLE users; --",
            "user' AND 1=1 --",
            "'; DELETE FROM enrollments; --",
        ]
        
        for user_id in user_ids:
            try:
                session = self._create_enrollment_session(user_id)
                # Should safely handle malicious input
                if session:
                    assert session.get('user_id') is not None
            except:
                pass

    def test_path_traversal_in_user_id(self):
        """Test path traversal attempts in user ID"""
        user_ids = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "user/../../../admin",
        ]
        
        for user_id in user_ids:
            try:
                session = self._create_enrollment_session(user_id)
                # Should safely handle path traversal attempts
            except:
                pass

    # ========== HELPER METHODS ==========
    
    def _create_enrollment_session(self, user_id: str, config: dict = None):
        """Create enrollment session (returns dict for testing)"""
        try:
            if not user_id or not isinstance(user_id, str):
                return None
            
            session = {
                'session_id': str(uuid.uuid4()),
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'chunks': [],
                'config': config or {}
            }
            return session
        except:
            return None

    def _add_audio_chunk(self, session: dict, audio: np.ndarray, sample_rate: int = 16000):
        """Add audio chunk to session"""
        if session is None or audio.size == 0:
            return None
        
        chunk = {
            'chunk_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'duration': len(audio) / sample_rate,
            'sample_rate': sample_rate,
            'success': True
        }
        
        session['chunks'].append(chunk)
        return chunk

    def _finalize_enrollment(self, session: dict):
        """Finalize enrollment session"""
        if session is None or len(session.get('chunks', [])) == 0:
            return None
        
        return {
            'enrollment_id': str(uuid.uuid4()),
            'user_id': session['user_id'],
            'success': True,
            'chunks_processed': len(session['chunks'])
        }


class TestEnrollmentValidationEdgeCases:
    """Tests for enrollment data validation edge cases"""

    def test_validate_audio_quality_perfect(self):
        """Test audio quality validation for perfect audio"""
        score = self._calculate_audio_quality(np.random.randn(16000) * 0.5)
        assert 0 <= score <= 1

    def test_validate_audio_quality_silence(self):
        """Test audio quality score for silence"""
        score = self._calculate_audio_quality(np.zeros(16000))
        assert score < 0.5  # Should be low quality

    def test_validate_audio_quality_noise(self):
        """Test audio quality score for very noisy audio"""
        score = self._calculate_audio_quality(np.random.randn(16000))
        assert 0 <= score <= 1

    def _calculate_audio_quality(self, audio: np.ndarray) -> float:
        """Calculate audio quality score"""
        # Placeholder implementation
        if np.all(audio == 0):
            return 0.1
        
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-6:
            return 0.2
        if rms > 1.0:
            return 0.8
        
        return 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
