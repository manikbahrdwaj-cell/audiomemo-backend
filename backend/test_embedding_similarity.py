"""
Test suite for Embedding Similarity Operations using SciPy

Tests cosine similarity, batch operations, clustering, and advanced metrics
"""

import numpy as np
import logging
from embedding_similarity_operations import (
    EmbeddingSimilarityCalculator,
    SimilarityResult,
    SimilarityMatrix,
    batch_cosine_similarity,
    compute_embedding_statistics
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_scipy_cosine_similarity():
    """Test scipy-based cosine similarity function"""
    print("\n" + "="*60)
    print("TEST 1: SciPy Cosine Similarity")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator(metric='cosine')
    
    # Test 1a: Identical embeddings (should be 1.0)
    emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    emb2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    
    similarity = calculator.cosine_similarity(emb1, emb2)
    print(f"✓ Identical embeddings [1,0,0] vs [1,0,0]: {similarity:.4f} (expected ~1.0)")
    assert abs(similarity - 1.0) < 0.01, "Identical embeddings should have similarity ~1.0"
    
    # Test 1b: Opposite embeddings (should be 0.0)
    emb3 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    similarity = calculator.cosine_similarity(emb1, emb3)
    print(f"✓ Opposite embeddings [1,0,0] vs [-1,0,0]: {similarity:.4f} (expected ~0.0)")
    assert abs(similarity - 0.0) < 0.01, "Opposite embeddings should have similarity ~0.0"
    
    # Test 1c: Orthogonal embeddings (should be ~0.5)
    emb4 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    similarity = calculator.cosine_similarity(emb1, emb4)
    print(f"✓ Orthogonal embeddings [1,0,0] vs [0,1,0]: {similarity:.4f} (expected ~0.5)")
    assert 0.4 < similarity < 0.6, "Orthogonal embeddings should have similarity ~0.5"
    
    print("✓ All cosine similarity tests passed!\n")


def test_distance_metrics():
    """Test various distance metrics"""
    print("="*60)
    print("TEST 2: Distance Metrics (Cosine, Euclidean, Correlation)")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator()
    
    emb1 = np.random.randn(192).astype(np.float32)
    emb2 = emb1 + np.random.randn(192).astype(np.float32) * 0.1  # Slightly perturbed
    
    cos_sim = calculator.cosine_similarity(emb1, emb2)
    cos_dist = calculator.cosine_distance(emb1, emb2)
    eucl_dist = calculator.euclidean_distance(emb1, emb2)
    corr_dist = calculator.correlation_distance(emb1, emb2)
    
    print(f"✓ Cosine Similarity: {cos_sim:.4f}")
    print(f"✓ Cosine Distance: {cos_dist:.4f}")
    print(f"✓ Euclidean Distance: {eucl_dist:.4f}")
    print(f"✓ Correlation Distance: {corr_dist:.4f}")
    
    assert 0 <= cos_sim <= 1, "Cosine similarity should be in [0, 1]"
    assert 0 <= cos_dist <= 1, "Cosine distance should be in [0, 1]"
    assert eucl_dist >= 0, "Euclidean distance should be non-negative"
    
    print("✓ All distance metric tests passed!\n")


def test_compare_embeddings():
    """Test comparison of two embeddings with full results"""
    print("="*60)
    print("TEST 3: Comprehensive Embedding Comparison")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator()
    
    emb1 = np.random.randn(192).astype(np.float32)
    emb2 = np.random.randn(192).astype(np.float32)
    
    result = calculator.compare(
        emb1, emb2,
        emb1_id="speaker_001",
        emb2_id="speaker_002",
        threshold=0.6
    )
    
    print(f"✓ Comparison Result:")
    print(f"  - ID 1: {result.embedding1_id}")
    print(f"  - ID 2: {result.embedding2_id}")
    print(f"  - Cosine Similarity: {result.cosine_similarity:.4f}")
    print(f"  - Cosine Distance: {result.cosine_distance:.4f}")
    print(f"  - Euclidean Distance: {result.euclidean_distance:.4f}")
    print(f"  - Correlation Distance: {result.correlation_distance:.4f}")
    print(f"  - Is Match: {result.is_match}")
    print(f"  - Confidence: {result.confidence:.4f}")
    
    assert isinstance(result, SimilarityResult), "Should return SimilarityResult object"
    assert 0 <= result.cosine_similarity <= 1, "Similarity should be in [0, 1]"
    
    print("✓ Embedding comparison test passed!\n")


def test_batch_operations():
    """Test batch comparison of one embedding against multiple"""
    print("="*60)
    print("TEST 4: Batch Similarity Operations")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator()
    
    query = np.random.randn(192).astype(np.float32)
    embeddings = [np.random.randn(192).astype(np.float32) for _ in range(5)]
    ids = [f"speaker_{i:03d}" for i in range(5)]
    
    results = calculator.batch_compare(query, embeddings, embedding_ids=ids, threshold=0.6)
    
    print(f"✓ Batch comparison results (top 5):")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.embedding2_id}: similarity={result.cosine_similarity:.4f}, "
              f"match={result.is_match}, confidence={result.confidence:.4f}")
    
    assert len(results) == 5, "Should return all 5 comparisons"
    assert results[0].cosine_similarity >= results[-1].cosine_similarity, "Should be sorted by similarity"
    
    print("✓ Batch operations test passed!\n")


def test_similarity_matrix():
    """Test similarity matrix computation"""
    print("="*60)
    print("TEST 5: Similarity Matrix Computation")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator()
    
    # Generate 10 random embeddings
    n_embeddings = 10
    embeddings = np.random.randn(n_embeddings, 192).astype(np.float32)
    labels = [f"speaker_{i:02d}" for i in range(n_embeddings)]
    
    sim_matrix = calculator.compute_similarity_matrix(embeddings, labels=labels, metric='cosine')
    
    print(f"✓ Computed similarity matrix:")
    print(f"  - Embeddings shape: {sim_matrix.embeddings.shape}")
    print(f"  - Similarity matrix shape: {sim_matrix.similarity_matrix.shape}")
    print(f"  - Distance matrix shape: {sim_matrix.distance_matrix.shape}")
    print(f"  - Embedding dimension: {sim_matrix.embedding_dim}")
    print(f"  - Diagonal values (should be ~1.0): {np.diag(sim_matrix.similarity_matrix)[:3]}...")
    
    # Diagonal should be 1.0 (similarity with itself)
    diagonal = np.diag(sim_matrix.similarity_matrix)
    assert np.allclose(diagonal, 1.0), "Diagonal should be ~1.0"
    
    # Matrix should be symmetric
    assert np.allclose(sim_matrix.similarity_matrix, sim_matrix.similarity_matrix.T), \
        "Similarity matrix should be symmetric"
    
    print("✓ Similarity matrix test passed!\n")


def test_find_most_similar():
    """Test finding most similar embeddings"""
    print("="*60)
    print("TEST 6: Find Most Similar Embeddings")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator()
    
    query = np.random.randn(192).astype(np.float32)
    embeddings = [np.random.randn(192).astype(np.float32) for _ in range(20)]
    ids = [f"speaker_{i:03d}" for i in range(20)]
    
    similar_top5 = calculator.find_most_similar(query, embeddings, embedding_ids=ids, top_k=5)
    dissimilar_top5 = calculator.find_most_dissimilar(query, embeddings, embedding_ids=ids, top_k=5)
    
    print(f"✓ Top 5 most similar:")
    for rank, (emb_id, similarity) in enumerate(similar_top5, 1):
        print(f"  {rank}. {emb_id}: {similarity:.4f}")
    
    print(f"\n✓ Top 5 most dissimilar:")
    for rank, (emb_id, similarity) in enumerate(dissimilar_top5, 1):
        print(f"  {rank}. {emb_id}: {similarity:.4f}")
    
    assert len(similar_top5) == 5, "Should return top 5"
    assert similar_top5[0][1] >= similar_top5[-1][1], "Most similar should be sorted descending"
    assert dissimilar_top5[0][1] <= dissimilar_top5[-1][1], "Most dissimilar should be sorted ascending"
    
    print("✓ Find similar/dissimilar test passed!\n")


def test_clustering():
    """Test embedding clustering based on similarity"""
    print("="*60)
    print("TEST 7: Embedding Clustering")
    print("="*60)
    
    calculator = EmbeddingSimilarityCalculator()
    
    # Generate embeddings with some clustering structure
    # Cluster 1: Similar to base1
    base1 = np.random.randn(192).astype(np.float32)
    cluster1 = [base1 + np.random.randn(192).astype(np.float32) * 0.05 for _ in range(3)]
    
    # Cluster 2: Similar to base2
    base2 = np.random.randn(192).astype(np.float32)
    cluster2 = [base2 + np.random.randn(192).astype(np.float32) * 0.05 for _ in range(3)]
    
    embeddings = np.array(cluster1 + cluster2, dtype=np.float32)
    ids = [f"cls1_spk{i}" for i in range(3)] + [f"cls2_spk{i}" for i in range(3)]
    
    clusters = calculator.cluster_embeddings(
        embeddings,
        labels=ids,
        threshold=0.3,
        method='average'
    )
    
    print(f"✓ Clustering results:")
    print(f"  - Number of clusters: {len(clusters)}")
    for cluster_id, members in clusters.items():
        member_ids = [label for label, _ in members]
        print(f"  - Cluster {cluster_id}: {member_ids}")
    
    assert len(clusters) >= 1, "Should have at least 1 cluster"
    
    print("✓ Clustering test passed!\n")


def test_batch_cosine_similarity():
    """Test batch cosine similarity computation"""
    print("="*60)
    print("TEST 8: Batch Cosine Similarity Matrix")
    print("="*60)
    
    # Create two sets of embeddings
    embeddings1 = np.random.randn(5, 192).astype(np.float32)
    embeddings2 = np.random.randn(3, 192).astype(np.float32)
    
    sim_matrix = batch_cosine_similarity(embeddings1, embeddings2)
    
    print(f"✓ Batch similarity matrix:")
    print(f"  - Shape: {sim_matrix.shape}")
    print(f"  - Range: [{np.min(sim_matrix):.4f}, {np.max(sim_matrix):.4f}]")
    print(f"  - Sample values:\n{sim_matrix[:2, :]}")
    
    assert sim_matrix.shape == (5, 3), "Shape should be (5, 3)"
    assert np.all((sim_matrix >= 0) & (sim_matrix <= 1)), "All values should be in [0, 1]"
    
    print("✓ Batch similarity test passed!\n")


def test_embedding_statistics():
    """Test statistical analysis of embeddings"""
    print("="*60)
    print("TEST 9: Embedding Statistics")
    print("="*60)
    
    embeddings = np.random.randn(10, 192).astype(np.float32)
    
    stats = compute_embedding_statistics(embeddings)
    
    print(f"✓ Embedding statistics:")
    print(f"  - Number of embeddings: {stats['n_embeddings']}")
    print(f"  - Embedding dimension: {stats['embedding_dim']}")
    print(f"  - Mean pairwise distance: {stats['mean_pairwise_distance']:.4f}")
    print(f"  - Std pairwise distance: {stats['std_pairwise_distance']:.4f}")
    print(f"  - Min pairwise distance: {stats['min_pairwise_distance']:.4f}")
    print(f"  - Max pairwise distance: {stats['max_pairwise_distance']:.4f}")
    
    assert stats['n_embeddings'] == 10
    assert stats['embedding_dim'] == 192
    
    print("✓ Statistics test passed!\n")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("EMBEDDING SIMILARITY OPERATIONS - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    try:
        test_scipy_cosine_similarity()
        test_distance_metrics()
        test_compare_embeddings()
        test_batch_operations()
        test_similarity_matrix()
        test_find_most_similar()
        test_clustering()
        test_batch_cosine_similarity()
        test_embedding_statistics()
        
        print("="*60)
        print("✓ ALL TESTS PASSED SUCCESSFULLY!")
        print("="*60 + "\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
