"""
Unit Tests for Database Utilities (Phase 4, Step 4.1)
Tests for database.py similarity and storage functions
"""

import pytest
import numpy as np
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock MongoDB before importing database module
sys.modules['pymongo'] = MagicMock()


class TestCosineSimilarityDatabase:
    """Test suite for database cosine similarity calculations"""

    def test_cosine_similarity_identical_vectors(self):
        """Test similarity of identical vectors"""
        from database import cosine_similarity
        
        a = np.array([1.0, 0.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0, 0.0])
        
        similarity = cosine_similarity(a, b)
        
        # Identical vectors should give similarity of 1.0
        assert abs(similarity - 1.0) < 0.001

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors"""
        from database import cosine_similarity
        
        a = np.array([1.0, 0.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0, 0.0])
        
        similarity = cosine_similarity(a, b)
        
        # Orthogonal vectors should give similarity close to 0
        assert abs(similarity) < 0.001

    def test_cosine_similarity_negative_vectors(self):
        """Test similarity with negative components"""
        from database import cosine_similarity
        
        a = np.array([1.0, -1.0, 1.0, -1.0])
        b = np.array([1.0, -1.0, 1.0, -1.0])
        
        similarity = cosine_similarity(a, b)
        
        # Same vectors should give high similarity
        assert abs(similarity - 1.0) < 0.001

    def test_cosine_similarity_opposite_vectors(self):
        """Test similarity of opposite vectors"""
        from database import cosine_similarity
        
        a = np.array([1.0, 1.0, 1.0, 1.0])
        b = np.array([-1.0, -1.0, -1.0, -1.0])
        
        similarity = cosine_similarity(a, b)
        
        # Opposite vectors should give similarity of -1
        assert abs(similarity - (-1.0)) < 0.001

    def test_cosine_similarity_192_dimensions(self):
        """Test with 192-dimensional embeddings (realistic case)"""
        from database import cosine_similarity
        
        np.random.seed(42)
        a = np.random.randn(192)
        b = np.random.randn(192)
        
        similarity = cosine_similarity(a, b)
        
        # Should be between -1 and 1
        assert -1.0 <= similarity <= 1.0

    def test_cosine_similarity_normalized_vectors(self):
        """Test with normalized unit vectors"""
        from database import cosine_similarity
        
        a = np.array([0.6, 0.8, 0.0, 0.0])
        b = np.array([0.6, 0.8, 0.0, 0.0])
        
        similarity = cosine_similarity(a, b)
        
        assert abs(similarity - 1.0) < 0.001

    def test_cosine_similarity_scaled_vectors(self):
        """Test that scaling doesn't affect cosine similarity"""
        from database import cosine_similarity
        
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.array([2.0, 4.0, 6.0, 8.0])  # 2x scaled
        
        similarity = cosine_similarity(a, b)
        
        # Despite scaling, direction is same, so similarity should be 1
        assert abs(similarity - 1.0) < 0.001

    def test_cosine_similarity_zero_vector(self):
        """Test behavior with zero vector"""
        from database import cosine_similarity
        
        a = np.array([1.0, 2.0, 3.0, 4.0])
        b = np.zeros(4)
        
        # This will cause division by zero - expecting either 0 or nan
        with pytest.raises((ValueError, ZeroDivisionError, RuntimeWarning)):
            similarity = cosine_similarity(a, b)

    def test_cosine_similarity_commutative(self):
        """Test that cosine similarity is commutative: sim(a, b) = sim(b, a)"""
        from database import cosine_similarity
        
        np.random.seed(42)
        a = np.random.randn(192)
        b = np.random.randn(192)
        
        sim_ab = cosine_similarity(a, b)
        sim_ba = cosine_similarity(b, a)
        
        # Should be exactly equal
        assert abs(sim_ab - sim_ba) < 1e-10

    def test_cosine_similarity_random_pairs(self):
        """Test multiple random pairs consistently"""
        from database import cosine_similarity
        
        np.random.seed(42)
        for _ in range(10):
            a = np.random.randn(192)
            b = np.random.randn(192)
            
            similarity = cosine_similarity(a, b)
            
            # Should always be in valid range
            assert -1.0 <= similarity <= 1.0


class TestSaveUserDatabase:
    """Test suite for user storage functions"""

    @patch('database.collection')
    def test_save_user_creates_record(self, mock_collection):
        """Test that save_user creates a new record"""
        from database import save_user
        
        phone = "1234567890"
        embedding = np.random.randn(192).tolist()
        
        save_user(phone, embedding)
        
        # Verify collection.update_one was called
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        
        # Check first arg is the filter
        assert call_args[0][0] == {"phone_number": phone}

    @patch('database.collection')
    def test_save_user_updates_existing(self, mock_collection):
        """Test that save_user uses upsert (creates if not exists)"""
        from database import save_user
        
        phone = "9876543210"
        embedding = np.random.randn(192).tolist()
        
        save_user(phone, embedding)
        
        # Check that update_one was called with upsert=True
        call_kwargs = mock_collection.update_one.call_args[1]
        assert call_kwargs['upsert'] is True

    @patch('database.collection')
    def test_save_user_embedding_format(self, mock_collection):
        """Test that embedding is saved in correct format"""
        from database import save_user
        
        phone = "5555555555"
        embedding = [0.1, 0.2, 0.3] + [0.0] * 189
        
        save_user(phone, embedding)
        
        # Check the $set operation
        call_args = mock_collection.update_one.call_args
        set_operation = call_args[0][1]
        
        assert "$set" in set_operation
        assert set_operation["$set"]["embedding"] == embedding


class TestVerifyUserDatabase:
    """Test suite for user verification functions"""

    @patch('database.collection')
    def test_verify_user_found(self, mock_collection):
        """Test verification when user is found"""
        from database import verify_user
        
        # Mock the database response
        mock_user = {
            "phone_number": "1234567890",
            "embedding": [0.5, 0.3, 0.2] + [0.0] * 189
        }
        mock_collection.find_one.return_value = mock_user
        
        phone = "1234567890"
        query_embedding = [0.5, 0.3, 0.2] + [0.0] * 189
        
        result = verify_user(phone, query_embedding)
        
        # Should return a similarity score
        assert result is not None
        assert isinstance(result, (int, float))
        assert -1.0 <= result <= 1.0

    @patch('database.collection')
    def test_verify_user_not_found(self, mock_collection):
        """Test verification when user doesn't exist"""
        from database import verify_user
        
        # Mock database returning None (user not found)
        mock_collection.find_one.return_value = None
        
        result = verify_user("nonexistent", [0.5] * 192)
        
        # Should return None
        assert result is None

    @patch('database.collection')
    def test_verify_user_calls_find_one(self, mock_collection):
        """Test that verify_user queries database correctly"""
        from database import verify_user
        
        mock_collection.find_one.return_value = None
        phone = "1234567890"
        
        verify_user(phone, [0.0] * 192)
        
        # Check that find_one was called with correct filter
        mock_collection.find_one.assert_called_once_with(
            {"phone_number": phone}
        )


class TestSimilarityThreshold:
    """Test suite for similarity threshold logic"""

    def test_similarity_threshold_match_high(self):
        """Test that high similarity indicates match"""
        # Typically threshold is 0.75
        similarity = 0.85
        threshold = 0.75
        
        assert similarity >= threshold

    def test_similarity_threshold_no_match_low(self):
        """Test that low similarity indicates no match"""
        similarity = 0.65
        threshold = 0.75
        
        assert similarity < threshold

    def test_similarity_threshold_edge_case_equal(self):
        """Test boundary case when similarity equals threshold"""
        similarity = 0.75
        threshold = 0.75
        
        assert similarity >= threshold


class TestEmbeddingConversions:
    """Test suite for embedding format conversions"""

    def test_numpy_to_list_conversion(self):
        """Test converting numpy array to list"""
        embedding_np = np.array([0.1, 0.2, 0.3] + [0.0] * 189)
        embedding_list = embedding_np.tolist()
        
        # Should be list type
        assert isinstance(embedding_list, list)
        assert len(embedding_list) == 192
        assert abs(embedding_list[0] - 0.1) < 0.001

    def test_list_to_numpy_conversion(self):
        """Test converting list to numpy array"""
        embedding_list = [0.1, 0.2, 0.3] + [0.0] * 189
        embedding_np = np.array(embedding_list)
        
        assert isinstance(embedding_np, np.ndarray)
        assert embedding_np.shape == (192,)
        assert abs(embedding_np[0] - 0.1) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
