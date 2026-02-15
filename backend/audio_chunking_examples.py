"""
Audio Chunking Examples and Usage Guide
Demonstrates how to use the audio_chunking module
"""

import numpy as np
import torch
from audio_chunking import (
    AudioChunker,
    ChunkConfig,
    EmbeddingAggregator,
    ChunkProcessor,
    create_default_chunker,
    create_default_processor
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_chunking():
    """
    Example 1: Basic audio chunking with default settings
    """
    print("\n=== Example 1: Basic Audio Chunking ===")
    
    # Create sample audio (10 seconds at 16kHz)
    sample_rate = 16000
    duration_seconds = 10
    audio = np.random.randn(sample_rate * duration_seconds).astype(np.float32)
    
    # Create chunker with default config
    chunker = create_default_chunker()
    
    # Chunk the audio
    chunks = chunker.chunk(audio)
    
    print(f"Original audio: {len(audio)} samples ({len(audio)/sample_rate:.2f} seconds)")
    print(f"Number of chunks: {len(chunks)}")
    print(f"Chunk sizes: {[len(c) for c in chunks[:3]]} (showing first 3)")
    
    return chunks


def example_custom_configuration():
    """
    Example 2: Custom chunking configuration
    """
    print("\n=== Example 2: Custom Configuration ===")
    
    # Create custom config
    config = ChunkConfig(
        chunk_size=32000,      # 2 seconds
        overlap_ratio=0.3,     # 30% overlap
        sample_rate=16000
    )
    
    chunker = AudioChunker(config)
    
    # Create sample audio (8 seconds)
    audio = np.random.randn(16000 * 8).astype(np.float32)
    
    chunks = chunker.chunk(audio)
    
    print(f"Custom chunk size: {config.chunk_size} samples ({config.chunk_size/16000:.2f}s)")
    print(f"Overlap ratio: {config.overlap_ratio * 100}%")
    print(f"Overlap samples: {config.overlap_samples}")
    print(f"Stride (hop) samples: {config.stride_samples}")
    print(f"Number of chunks created: {len(chunks)}")


def example_windowing():
    """
    Example 3: Apply windowing to reduce edge artifacts
    """
    print("\n=== Example 3: Audio Windowing ===")
    
    chunker = AudioChunker()
    
    # Create sample audio chunk
    chunk = np.random.randn(16000)
    
    # Try different windows
    windows = ['hann', 'hamming', 'blackman', 'bartlett']
    
    for window_type in windows:
        windowed = chunker.apply_windowing(chunk, window_type)
        print(f"{window_type:10} - Max value: {np.max(np.abs(windowed)):.4f}, "
              f"Energy before: {np.sum(chunk**2):.2e}, after: {np.sum(windowed**2):.2e}")


def example_chunk_statistics():
    """
    Example 4: Analyze chunk features
    """
    print("\n=== Example 4: Chunk Statistics ===")
    
    chunker = AudioChunker()
    audio = np.random.randn(16000 * 3)  # 3 seconds
    chunks = chunker.chunk(audio)
    
    print(f"Analyzing {len(chunks)} chunks:\n")
    
    for i, chunk in enumerate(chunks[:3]):  # Show first 3
        features = chunker.compute_chunk_features(chunk)
        print(f"Chunk {i}:")
        print(f"  Duration: {features['duration_ms']:.1f} ms")
        print(f"  RMS Energy: {features['rms']:.4f}")
        print(f"  Peak: {features['peak']:.4f}")
        print(f"  Std Dev: {features['std']:.4f}")


def example_embedding_aggregation():
    """
    Example 5: Aggregate embeddings from multiple chunks
    """
    print("\n=== Example 5: Embedding Aggregation ===")
    
    # Simulate embeddings from 3 chunks (192-dim speaker embeddings)
    embedding_dim = 192
    n_chunks = 3
    
    embeddings = [np.random.randn(embedding_dim) for _ in range(n_chunks)]
    chunks = [np.random.randn(16000) for _ in range(n_chunks)]
    
    aggregator = EmbeddingAggregator()
    
    # Try different aggregation methods
    print(f"Original embeddings: {n_chunks} x {embedding_dim}-dim\n")
    
    # Mean pooling
    mean_emb = aggregator.mean_pool(embeddings)
    print(f"Mean pooling: shape {mean_emb.shape}, mean value {np.mean(mean_emb):.6f}")
    
    # Max pooling
    max_emb = aggregator.max_pool(embeddings)
    print(f"Max pooling: shape {max_emb.shape}, mean value {np.mean(max_emb):.6f}")
    
    # Weighted average (linear)
    linear_emb = aggregator.weighted_average(embeddings, weight_type='linear')
    print(f"Weighted (linear): shape {linear_emb.shape}, mean value {np.mean(linear_emb):.6f}")
    
    # Energy-weighted
    energy_emb = aggregator.weighted_average_by_energy(embeddings, chunks)
    print(f"Energy-weighted: shape {energy_emb.shape}, mean value {np.mean(energy_emb):.6f}")
    
    # Variance-weighted
    var_emb = aggregator.variance_weighted_average(embeddings)
    print(f"Variance-weighted: shape {var_emb.shape}, mean value {np.mean(var_emb):.6f}")


def example_full_pipeline():
    """
    Example 6: Full pipeline - chunk, process, and aggregate
    """
    print("\n=== Example 6: Full Processing Pipeline ===")
    
    # Create sample audio (5 seconds)
    audio = np.random.randn(16000 * 5).astype(np.float32)
    
    # Create processor
    processor = ChunkProcessor()
    
    # Mock embedding function (normally this would be your model)
    def mock_embedding_func(audio_chunk):
        """Simulate embedding extraction"""
        # Return a 192-dim embedding
        return np.random.randn(192)
    
    # Process audio
    aggregated_embedding, metadata = processor.process_audio(
        audio=audio,
        embedding_func=mock_embedding_func,
        aggregation_method='mean',
        apply_window=True,
        window_type='hann',
        normalize=True
    )
    
    print(f"Aggregated embedding shape: {aggregated_embedding.shape}")
    print(f"Number of chunks processed: {metadata['n_chunks']}")
    print(f"Total duration: {metadata['total_duration_ms']:.1f} ms")
    print(f"Chunk size: {metadata['chunk_size_ms']:.1f} ms")
    print(f"Aggregation method: {metadata['aggregation_method']}")
    print(f"Window type: {metadata['window_type']}")
    print(f"Mean embedding value: {np.mean(aggregated_embedding):.6f}")


def example_torch_tensor_input():
    """
    Example 7: Using PyTorch tensors as input
    """
    print("\n=== Example 7: PyTorch Tensor Input ===")
    
    # Create audio as torch tensor
    audio_tensor = torch.randn(16000 * 3)  # 3 seconds
    
    chunker = create_default_chunker()
    chunks = chunker.chunk(audio_tensor)
    
    print(f"Input type: {type(audio_tensor)}")
    print(f"Number of chunks: {len(chunks)}")
    print(f"Output type: {type(chunks[0])}")
    print(f"All outputs are numpy: {all(isinstance(c, np.ndarray) for c in chunks)}")


def example_different_aggregations():
    """
    Example 8: Compare different aggregation strategies
    """
    print("\n=== Example 8: Aggregation Strategy Comparison ===")
    
    # Create processor and simulate several embeddings
    processor = ChunkProcessor()
    
    # Create embeddings with varying quality
    embeddings = [
        np.ones(192) * 0.9 + np.random.randn(192) * 0.01,  # High quality
        np.ones(192) * 0.5 + np.random.randn(192) * 0.1,   # Medium quality
        np.ones(192) * 0.9 + np.random.randn(192) * 0.01,  # High quality
    ]
    chunks = [
        np.ones(16000) * 0.8,  # High energy
        np.ones(16000) * 0.3,  # Low energy
        np.ones(16000) * 0.8,  # High energy
    ]
    
    aggregator = EmbeddingAggregator()
    
    methods = [
        ('mean', lambda: aggregator.mean_pool(embeddings)),
        ('max', lambda: aggregator.max_pool(embeddings)),
        ('weighted_linear', lambda: aggregator.weighted_average(embeddings, weight_type='linear')),
        ('weighted_inverse', lambda: aggregator.weighted_average(embeddings, weight_type='inverse')),
        ('energy_weighted', lambda: aggregator.weighted_average_by_energy(embeddings, chunks)),
    ]
    
    print("\nAggregation Results:")
    for name, func in methods:
        result = func()
        print(f"{name:20} - Mean: {np.mean(result):7.4f}, "
              f"Std: {np.std(result):7.4f}, Norm: {np.linalg.norm(result):7.4f}")


def example_large_audio_handling():
    """
    Example 9: Handling large audio files efficiently
    """
    print("\n=== Example 9: Large Audio File Handling ===")
    
    # Simulate 1-minute audio file (memory efficient)
    duration_minutes = 1
    sample_rate = 16000
    total_samples = duration_minutes * 60 * sample_rate
    
    print(f"Processing {duration_minutes}-minute audio file...")
    print(f"Total samples: {total_samples:,}")
    print(f"Memory size: {total_samples * 4 / (1024**2):.2f} MB (float32)")
    
    # Create chunker with 2-second chunks
    config = ChunkConfig(
        chunk_size=2 * sample_rate,
        overlap_ratio=0.1,
        sample_rate=sample_rate
    )
    
    chunker = AudioChunker(config)
    
    # In practice, you'd load and process file in streaming fashion
    # For demo, we'll just calculate expected chunks
    expected_stride = config.chunk_size - config.overlap_samples
    expected_n_chunks = (total_samples - config.chunk_size) // expected_stride + 1
    
    print(f"Expected chunk size: {config.chunk_size} samples ({config.chunk_size/sample_rate:.1f}s)")
    print(f"Expected number of chunks: {expected_n_chunks}")
    print(f"Memory per chunk: {config.chunk_size * 4 / (1024):.2f} KB")


if __name__ == "__main__":
    print("=" * 60)
    print("Audio Chunking Examples")
    print("=" * 60)
    
    # Run all examples
    example_basic_chunking()
    example_custom_configuration()
    example_windowing()
    example_chunk_statistics()
    example_embedding_aggregation()
    example_full_pipeline()
    example_torch_tensor_input()
    example_different_aggregations()
    example_large_audio_handling()
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
