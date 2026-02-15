"""
Pytest Configuration and Shared Fixtures
Contains fixtures, hooks, and configuration shared across all tests
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import logging

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging for tests
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "edge_cases: mark test as an edge case test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as websocket-related"
    )
    config.addinivalue_line(
        "markers", "embedding: mark test as embedding-related"
    )
    config.addinivalue_line(
        "markers", "enrollment: mark test as enrollment-related"
    )
    config.addinivalue_line(
        "markers", "matching: mark test as matching-related"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test"
    )
    config.addinivalue_line(
        "markers", "requires_model: mark test as requiring pre-trained models"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Skip Windows-specific tests on non-Windows platforms
        if "skip_on_windows" in item.keywords:
            if os.name != 'nt':
                item.add_marker(pytest.mark.skip(reason="Windows-specific test"))
        
        # Mark tests without explicit markers as unit tests
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory"""
    test_dir = backend_dir / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session")
def results_dir():
    """Provide path to test results directory"""
    results_dir = backend_dir / "test_results"
    results_dir.mkdir(exist_ok=True)
    return results_dir


# ============================================================================
# AUDIO GENERATION FIXTURES
# ============================================================================

class AudioGenerator:
    """Utility for generating test audio"""
    
    @staticmethod
    def sine_wave(
        duration_ms: int = 1000,
        sample_rate: int = 16000,
        frequency: float = 440.0,
        amplitude: float = 0.1
    ) -> np.ndarray:
        """Generate sine wave audio"""
        num_samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, num_samples)
        audio = amplitude * np.sin(2 * np.pi * frequency * t)
        return audio.astype(np.float32)
    
    @staticmethod
    def white_noise(
        duration_ms: int = 1000,
        sample_rate: int = 16000,
        amplitude: float = 0.01
    ) -> np.ndarray:
        """Generate white noise audio"""
        num_samples = int(sample_rate * duration_ms / 1000)
        audio = amplitude * np.random.randn(num_samples)
        return audio.astype(np.float32)
    
    @staticmethod
    def silence(
        duration_ms: int = 1000,
        sample_rate: int = 16000
    ) -> np.ndarray:
        """Generate silence (all zeros)"""
        num_samples = int(sample_rate * duration_ms / 1000)
        return np.zeros(num_samples, dtype=np.float32)
    
    @staticmethod
    def sweep(
        duration_ms: int = 1000,
        sample_rate: int = 16000,
        start_freq: float = 20.0,
        end_freq: float = 20000.0,
        amplitude: float = 0.1
    ) -> np.ndarray:
        """Generate frequency sweep (chirp) audio"""
        num_samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, num_samples)
        
        # Linearly sweep frequency
        k = (end_freq - start_freq) / (duration_ms / 1000)
        phase = 2 * np.pi * (start_freq * t + 0.5 * k * t ** 2)
        audio = amplitude * np.sin(phase)
        
        return audio.astype(np.float32)
    
    @staticmethod
    def mixed_audio(
        duration_ms: int = 1000,
        sample_rate: int = 16000
    ) -> np.ndarray:
        """Generate mixed audio (sine + noise)"""
        sine = AudioGenerator.sine_wave(duration_ms, sample_rate, 440, 0.08)
        noise = AudioGenerator.white_noise(duration_ms, sample_rate, 0.02)
        return (sine + noise).astype(np.float32)


@pytest.fixture(scope="session")
def audio_generator():
    """Provide audio generator utility"""
    return AudioGenerator()


@pytest.fixture
def clean_audio(audio_generator):
    """Provide clean sine wave audio"""
    return audio_generator.sine_wave(duration_ms=1000)


@pytest.fixture
def noisy_audio(audio_generator):
    """Provide noisy audio"""
    return audio_generator.mixed_audio(duration_ms=1000)


@pytest.fixture
def silence_audio(audio_generator):
    """Provide silence audio"""
    return audio_generator.silence(duration_ms=1000)


@pytest.fixture
def long_audio(audio_generator):
    """Provide long duration audio"""
    return audio_generator.sine_wave(duration_ms=10000)


@pytest.fixture
def short_audio(audio_generator):
    """Provide short duration audio"""
    return audio_generator.sine_wave(duration_ms=100)


# ============================================================================
# EMBEDDING FIXTURES
# ============================================================================

@pytest.fixture
def random_embedding():
    """Provide random normalized embedding"""
    emb = np.random.randn(192).astype(np.float32)
    return emb / np.linalg.norm(emb)


@pytest.fixture
def embedding_batch():
    """Provide batch of random embeddings"""
    embeddings = []
    for _ in range(10):
        emb = np.random.randn(192).astype(np.float32)
        embeddings.append(emb / np.linalg.norm(emb))
    return np.array(embeddings)


@pytest.fixture
def identical_embeddings():
    """Provide identical embeddings for testing similarity"""
    emb = np.random.randn(192).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    return emb, emb


@pytest.fixture
def orthogonal_embeddings():
    """Provide orthogonal embeddings"""
    emb1 = np.zeros(192, dtype=np.float32)
    emb1[0] = 1.0
    emb2 = np.zeros(192, dtype=np.float32)
    emb2[1] = 1.0
    return emb1, emb2


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_mongodb():
    """Provide mocked MongoDB connection"""
    with patch('database.MongoClient') as mock_client:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_db.__getitem__.side_effect = lambda x: MagicMock()
        
        yield {
            'client': mock_client,
            'db': mock_db,
            'collection': mock_collection
        }


@pytest.fixture
def mock_voice_embedding():
    """Provide mocked voice embedding module"""
    with patch('voice_embedding.get_model') as mock_get_model:
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        yield {
            'model': mock_model,
            'get_model': mock_get_model
        }


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

class TestData:
    """Test data configurations and constants"""
    
    # Standard configurations
    AUDIO_SAMPLE_RATE = 16000
    EMBEDDING_DIM = 192
    PHONE_NUMBERS = [
        "9876543210",
        "9876543211",
        "9876543212",
    ]
    
    # Test thresholds
    SIMILARITY_THRESHOLD = 0.6
    QUALITY_THRESHOLD = 0.7
    
    # Timeout values
    DEFAULT_TIMEOUT = 30
    LONG_TIMEOUT = 300


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration"""
    return TestData()


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture
def cleanup_temp_files():
    """Clean up temporary files after test"""
    temp_files = []
    
    yield temp_files
    
    # Cleanup
    import shutil
    for file_path in temp_files:
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
        except Exception:
            pass


# ============================================================================
# PERFORMANCE MEASUREMENT FIXTURES
# ============================================================================

@pytest.fixture
def measure_time():
    """Fixture to measure execution time of a function"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer


# ============================================================================
# PYTEST PLUGINS AND HOOKS
# ============================================================================

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test"""
    yield
    # Cleanup after test


def pytest_runtest_logreport(report):
    """Hook for test result reporting"""
    if report.when == "call":
        if report.outcome == "failed":
            # Could add custom failure handling here
            pass


# ============================================================================
# PARAMETRIZE FIXTURES
# ============================================================================

# Common test parameters
AUDIO_DURATIONS = [100, 500, 1000, 2000, 5000]
SAMPLE_RATES = [8000, 16000, 44100]
MATCHING_STRATEGIES = ["cosine", "euclidean", "correlation", "hybrid"]


@pytest.fixture(params=AUDIO_DURATIONS)
def audio_duration(request):
    """Parameterized fixture for audio durations"""
    return request.param


@pytest.fixture(params=SAMPLE_RATES)
def sample_rate(request):
    """Parameterized fixture for sample rates"""
    return request.param


@pytest.fixture(params=MATCHING_STRATEGIES)
def matching_strategy(request):
    """Parameterized fixture for matching strategies"""
    return request.param


# ============================================================================
# REPORT HOOKS
# ============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom summary to terminal output"""
    if exitstatus == 0:
        terminalreporter.write_sep("=", "All tests passed! ✓", green=True)
    else:
        terminalreporter.write_sep("=", "Some tests failed", red=True)
