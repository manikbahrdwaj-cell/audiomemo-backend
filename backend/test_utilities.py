"""
Test Utilities and Fixtures for Unit Tests (Phase 4, Step 4.1)
Provides reusable test helpers, mocks, and fixtures for all unit tests
"""

import numpy as np
import pytest
from unittest.mock import Mock, MagicMock
from io import BytesIO
import wave


class EmbeddingFixtures:
    """Fixtures for embedding-related tests"""
    
    @staticmethod
    def valid_embedding_192d():
        """Generate a valid 192-dimensional embedding"""
        return np.random.randn(192)
    
    @staticmethod
    def zero_embedding_192d():
        """Generate a zero 192-dimensional embedding"""
        return np.zeros(192)
    
    @staticmethod
    def ones_embedding_192d():
        """Generate an embedding of all ones"""
        return np.ones(192)
    
    @staticmethod
    def unit_vector_embedding():
        """Generate a normalized unit vector embedding"""
        embedding = np.random.randn(192)
        return embedding / np.linalg.norm(embedding)
    
    @staticmethod
    def embedding_with_nan():
        """Generate embedding with NaN values"""
        embedding = np.random.randn(192)
        embedding[50] = np.nan
        return embedding
    
    @staticmethod
    def embedding_with_infinity():
        """Generate embedding with Infinity values"""
        embedding = np.random.randn(192)
        embedding[75] = np.inf
        return embedding
    
    @staticmethod
    def similar_embeddings_pair(similarity_level=0.95):
        """Generate two similar embeddings"""
        base = np.random.randn(192)
        noise = np.random.randn(192) * (1 - similarity_level)
        return base, base + noise
    
    @staticmethod
    def batch_embeddings(count=100):
        """Generate batch of embeddings"""
        return [np.random.randn(192) for _ in range(count)]


class AudioFixtures:
    """Fixtures for audio-related tests"""
    
    @staticmethod
    def create_sine_wave_bytes(frequency=440, duration=1.0, sample_rate=16000):
        """Create synthetic sine wave audio bytes"""
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples, False)
        audio_data = (0.3 * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
        
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    
    @staticmethod
    def create_white_noise_bytes(duration=1.0, sample_rate=16000):
        """Create white noise audio bytes"""
        samples = int(duration * sample_rate)
        audio_data = (0.1 * np.random.randn(samples)).astype(np.int16)
        
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    
    @staticmethod
    def create_silent_audio_bytes(duration=1.0, sample_rate=16000):
        """Create silent audio bytes"""
        samples = int(duration * sample_rate)
        audio_data = np.zeros(samples, dtype=np.int16)
        
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    
    @staticmethod
    def create_stereo_audio_bytes(duration=1.0, sample_rate=16000):
        """Create stereo audio bytes"""
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples, False)
        left_channel = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
        right_channel = (0.3 * np.sin(2 * np.pi * 880 * t)).astype(np.int16)
        
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            audio_data = np.column_stack((left_channel, right_channel))
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()


class MockDatabase:
    """Mock MongoDB database for testing"""
    
    def __init__(self):
        self.users = {}
    
    def save_user(self, phone_number, embedding):
        """Mock save_user function"""
        self.users[phone_number] = {
            "phone_number": phone_number,
            "embedding": embedding
        }
    
    def get_user(self, phone_number):
        """Mock user retrieval"""
        return self.users.get(phone_number)
    
    def verify_user(self, phone_number, query_embedding):
        """Mock user verification"""
        if phone_number not in self.users:
            return None
        
        stored_embedding = np.array(self.users[phone_number]["embedding"])
        query_array = np.array(query_embedding)
        
        # Simple cosine similarity
        score = float(np.dot(stored_embedding, query_array) / 
                     (np.linalg.norm(stored_embedding) * np.linalg.norm(query_array)))
        return score
    
    def clear(self):
        """Clear all data"""
        self.users.clear()


class ComparisonTestData:
    """Test data for comparison operations"""
    
    @staticmethod
    def similarity_test_cases():
        """Return test cases for similarity calculations"""
        np.random.seed(42)
        return [
            {
                'name': 'identical_vectors',
                'embedding1': np.ones(192),
                'embedding2': np.ones(192),
                'expected_range': (0.95, 1.0)
            },
            {
                'name': 'orthogonal_vectors',
                'embedding1': np.concatenate([np.ones(96), np.zeros(96)]),
                'embedding2': np.concatenate([np.zeros(96), np.ones(96)]),
                'expected_range': (0.3, 0.7)
            },
            {
                'name': 'random_vectors',
                'embedding1': np.random.randn(192),
                'embedding2': np.random.randn(192),
                'expected_range': (0.0, 1.0)
            }
        ]
    
    @staticmethod
    def batch_comparison_test_cases():
        """Return test cases for batch comparisons"""
        np.random.seed(42)
        base_embedding = np.random.randn(192)
        
        return {
            'enrolled': [
                base_embedding,
                base_embedding + 0.1 * np.random.randn(192),
                base_embedding + 0.2 * np.random.randn(192)
            ],
            'verification': base_embedding,
            'expected_matches': 1  # At least one should match
        }


class MetricsCollector:
    """Collect and analyze test metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_metric(self, name, value):
        """Record a metric value"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_average(self, name):
        """Get average of metric values"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return sum(self.metrics[name]) / len(self.metrics[name])
    
    def get_max(self, name):
        """Get maximum of metric values"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return max(self.metrics[name])
    
    def get_min(self, name):
        """Get minimum of metric values"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return min(self.metrics[name])
    
    def get_summary(self):
        """Get summary of all metrics"""
        summary = {}
        for name in self.metrics:
            summary[name] = {
                'count': len(self.metrics[name]),
                'average': self.get_average(name),
                'min': self.get_min(name),
                'max': self.get_max(name)
            }
        return summary


# Pytest Fixtures
@pytest.fixture
def embedding_fixtures():
    """Provide embedding fixtures"""
    return EmbeddingFixtures()


@pytest.fixture
def audio_fixtures():
    """Provide audio fixtures"""
    return AudioFixtures()


@pytest.fixture
def mock_database():
    """Provide mock database"""
    return MockDatabase()


@pytest.fixture
def metrics_collector():
    """Provide metrics collector"""
    return MetricsCollector()


@pytest.fixture
def test_data():
    """Provide comparison test data"""
    return ComparisonTestData()
