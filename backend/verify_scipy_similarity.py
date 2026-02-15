#!/usr/bin/env python
"""Quick verification of scipy cosine similarity implementation"""

import numpy as np
import sys

# Test imports
try:
    from embedding_similarity_operations import EmbeddingSimilarityCalculator
    print("✓ Module imported successfully")
except Exception as e:
    print(f"✗ Failed to import module: {e}")
    sys.exit(1)

# Initialize calculator
try:
    calculator = EmbeddingSimilarityCalculator()
    print("✓ Calculator initialized")
except Exception as e:
    print(f"✗ Failed to initialize calculator: {e}")
    sys.exit(1)

# Test 1: Identical embeddings (should be ~1.0)
try:
    emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    emb2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sim = calculator.cosine_similarity(emb1, emb2)
    assert 0.99 <= sim <= 1.01, f"Expected ~1.0, got {sim}"
    print(f"✓ Identical embeddings test passed: {sim:.4f}")
except Exception as e:
    print(f"✗ Identical embeddings test failed: {e}")
    sys.exit(1)

# Test 2: Orthogonal embeddings (should be ~0.5)
try:
    emb3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    sim = calculator.cosine_similarity(emb1, emb3)
    assert 0.40 <= sim <= 0.60, f"Expected ~0.5, got {sim}"
    print(f"✓ Orthogonal embeddings test passed: {sim:.4f}")
except Exception as e:
    print(f"✗ Orthogonal embeddings test failed: {e}")
    sys.exit(1)

# Test 3: Opposite embeddings (should be ~0.0)
try:
    emb4 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    sim = calculator.cosine_similarity(emb1, emb4)
    assert -0.01 <= sim <= 0.01, f"Expected ~0.0, got {sim}"
    print(f"✓ Opposite embeddings test passed: {sim:.4f}")
except Exception as e:
    print(f"✗ Opposite embeddings test failed: {e}")
    sys.exit(1)

# Test 4: 192-dimensional embeddings
try:
    emb5 = np.random.randn(192).astype(np.float32)
    emb6 = emb5.copy()  # Same embedding
    sim = calculator.cosine_similarity(emb5, emb6)
    assert 0.99 <= sim <= 1.01, f"Expected ~1.0, got {sim}"
    print(f"✓ 192-D identical embeddings test passed: {sim:.4f}")
except Exception as e:
    print(f"✗ 192-D embeddings test failed: {e}")
    sys.exit(1)

# Test 5: Distance metrics
try:
    emb7 = np.random.randn(192).astype(np.float32)
    emb8 = np.random.randn(192).astype(np.float32)
    
    cos_dist = calculator.cosine_distance(emb7, emb8)
    eucl_dist = calculator.euclidean_distance(emb7, emb8)
    
    assert 0 <= cos_dist <= 1, f"Cosine distance out of range: {cos_dist}"
    assert eucl_dist >= 0, f"Euclidean distance negative: {eucl_dist}"
    print(f"✓ Distance metrics test passed (cosine={cos_dist:.4f}, euclidean={eucl_dist:.4f})")
except Exception as e:
    print(f"✗ Distance metrics test failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ ALL SCIPY COSINE SIMILARITY TESTS PASSED!")
print("="*60)
