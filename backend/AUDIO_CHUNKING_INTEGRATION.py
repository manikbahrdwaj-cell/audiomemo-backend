"""
Audio Chunking Integration Guide
How to use audio chunking in the Voice Biometric API
"""

import numpy as np
from voice_embedding import (
    generate_embedding,
    generate_embedding_with_chunking,
    get_embedding_with_auto_chunking,
    compare_embeddings_with_chunks,
    calculate_cosine_similarity
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkingIntegrationGuide:
    """
    Complete guide for integrating audio chunking into the API
    """
    
    @staticmethod
    def integration_example_1_simple_chunking():
        """
        Integration Example 1: Simple chunking for longer audio
        
        Use case: User enrolls with a 15-second long recording
        """
        print("\n" + "="*60)
        print("INTEGRATION EXAMPLE 1: Simple Chunking")
        print("="*60)
        
        code = '''
# In your Flask/FastAPI endpoint:

from voice_embedding import generate_embedding_with_chunking

@app.post("/enroll-chunked")
async def enroll_with_chunking(
    phone_number: str = Form(...),
    audio: UploadFile = File(...)
):
    """Enrollment with chunking support for longer audio files"""
    
    audio_bytes = await audio.read()
    
    # Generate embedding with chunking
    embedding = generate_embedding_with_chunking(
        audio_bytes,
        chunk_size_seconds=2.0,        # 2-second chunks
        overlap_ratio=0.2,              # 20% overlap
        aggregation_method='energy_weighted',  # Better for variable quality
        apply_windowing=True,
        normalize_chunks=True
    )
    
    # Store embedding as usual
    store_voice_embedding(phone_number, embedding)
    
    return {
        "success": True,
        "message": "Voice enrolled successfully with chunking",
        "phone_number": phone_number
    }
        '''
        print(code)
    
    @staticmethod
    def integration_example_2_auto_chunking():
        """
        Integration Example 2: Automatic chunking based on audio length
        
        Use case: Use standard embedding for short audio, chunked for long
        """
        print("\n" + "="*60)
        print("INTEGRATION EXAMPLE 2: Auto Chunking")
        print("="*60)
        
        code = '''
# In your endpoint:

from voice_embedding import get_embedding_with_auto_chunking

@app.post("/verify-auto")
async def verify_with_auto_chunking(
    phone_number: str = Form(...),
    audio: UploadFile = File(...)
):
    """Verification with automatic chunking decision"""
    
    audio_bytes = await audio.read()
    
    # Automatically chunks if audio > 10 seconds
    embedding = get_embedding_with_auto_chunking(
        audio_bytes,
        auto_chunk_threshold_seconds=10.0,
        chunk_size_seconds=2.0,
        aggregation_method='mean'
    )
    
    # Verify as usual
    stored_embedding = get_voice_embedding(phone_number)
    similarity = calculate_cosine_similarity(embedding, stored_embedding)
    
    return {
        "success": True,
        "phone_number": phone_number,
        "similarity_score": similarity,
        "is_match": similarity > 0.65,
        "threshold": 0.65
    }
        '''
        print(code)
    
    @staticmethod
    def integration_example_3_endpoint_variants():
        """
        Integration Example 3: Multiple endpoints with different strategies
        
        Use case: Offer different endpoints for different use cases
        """
        print("\n" + "="*60)
        print("INTEGRATION EXAMPLE 3: Multiple Endpoints")
        print("="*60)
        
        code = '''
# Different endpoints for different use cases:

# 1. Fast enrollment (short audio, no chunking)
@app.post("/enroll-fast")
async def enroll_fast(phone_number: str, audio: UploadFile):
    embedding = generate_embedding(await audio.read())
    store_voice_embedding(phone_number, embedding)
    return {"success": True}

# 2. Robust enrollment (chunked, energy-weighted)
@app.post("/enroll-robust")
async def enroll_robust(phone_number: str, audio: UploadFile):
    embedding = generate_embedding_with_chunking(
        await audio.read(),
        chunk_size_seconds=2.0,
        aggregation_method='energy_weighted'
    )
    store_voice_embedding(phone_number, embedding)
    return {"success": True}

# 3. Auto-deciding endpoint (intelligent selection)
@app.post("/enroll")
async def enroll(phone_number: str, audio: UploadFile):
    embedding = get_embedding_with_auto_chunking(
        await audio.read(),
        auto_chunk_threshold_seconds=5.0  # Chunk if > 5 seconds
    )
    store_voice_embedding(phone_number, embedding)
    return {"success": True}

# Similarly for verification endpoints
        '''
        print(code)
    
    @staticmethod
    def audio_quality_handling():
        """
        Best practices for handling variable audio quality with chunking
        """
        print("\n" + "="*60)
        print("BEST PRACTICES: Audio Quality Handling")
        print("="*60)
        
        guide = '''
1. ENERGY-WEIGHTED AGGREGATION (Recommended)
   - Method: generate_embedding_with_chunking(..., aggregation_method='energy_weighted')
   - Best for: Variable quality recordings with silent/loud sections
   - Benefit: Automatically emphasizes high-quality (high-energy) sections

2. WEIGHTED_NORMALIZED AGGREGATION
   - Method: generate_embedding_with_chunking(..., aggregation_method='weighted_normalized')
   - Best for: Longer recordings where middle sections are typically more stable
   - Benefit: Middle chunks weighted higher, reducing impact of start/end artifacts

3. MEAN POOLING (Simple & Robust)
   - Method: generate_embedding_with_chunking(..., aggregation_method='mean')
   - Best for: Already good quality, consistent audio
   - Benefit: Simple, fast, handles noise well with averaging

4. WINDOWING FUNCTION
   - Hann window reduces edge artifacts in chunks
   - Applied automatically with apply_windowing=True
   - Recommended for most use cases

5. CHUNK SIZE SELECTION
   - 1 second (16000 samples): Good balance for variety
   - 2 seconds: Recommended default, good temporal context
   - 3+ seconds: Better for music/environmental sounds, may miss variations

6. OVERLAP SETTINGS
   - 20% (0.2): Good balance, standard recommendation
   - 10% (0.1): Fewer chunks, faster processing
   - 30% (0.3): More overlap, better continuity, slower processing
        '''
        print(guide)
    
    @staticmethod
    def performance_considerations():
        """
        Performance and optimization tips
        """
        print("\n" + "="*60)
        print("PERFORMANCE CONSIDERATIONS")
        print("="*60)
        
        guide = '''
PROCESSING TIME:
- Non-chunked: ~0.5-1 second for typical audio
- Chunked (3 chunks): ~2 seconds (3x embedding generation + aggregation)
- Chunked (5 chunks): ~3+ seconds

MEMORY USAGE:
- Single embedding: ~1.5 MB
- With chunking: Memory remains constant (process one chunk at a time)
- Good for embedded/mobile deployment

OPTIMIZATION STRATEGIES:

1. Use suitable chunk size
   - Smaller chunks = more processing time
   - Recommended: 2 seconds = good trade-off

2. Reduce overlap for speed
   - 10% overlap: Fastest
   - 20% overlap: Recommended default
   - 30% overlap: More accurate but slower

3. Batch processing
   - For multiple enrollments, pre-load model with get_model()
   - Subsequent calls reuse cached model

4. Caching
   - Cache embeddings to avoid re-processing
   - Useful for repeated verification attempts

5. Streaming processing
   - Process audio in real-time chunks
   - Not waiting for full file upload
        '''
        print(guide)
    
    @staticmethod
    def comparison_recommendations():
        """
        Recommendations for comparing different strategies
        """
        print("\n" + "="*60)
        print("STRATEGY COMPARISON & SELECTION")
        print("="*60)
        
        guide = '''
CHOOSE STANDARD (NON-CHUNKED) FOR:
✓ Short audio files (< 5 seconds)
✓ High-quality, clean recordings
✓ Known good recording conditions
✓ Mobile/low-latency requirements
✓ Real-time streaming with buffer

CHOOSE CHUNKING FOR:
✓ Longer audio (> 10 seconds)
✓ Variable quality recordings
✓ Background noise present
✓ Multiple speaking segments
✓ Unknown recording conditions
✓ Robustness is priority over speed

RECOMMENDED SETUPS:

Setup 1: Fast Path (mobile app)
- Use auto_chunking with threshold=3.0 seconds
- chunk_size=1.5 seconds
- aggregation='mean'
- Processing: <2 seconds

Setup 2: Robust Path (security-critical)
- Always use chunking
- chunk_size=2.0 seconds
- overlap=0.3
- aggregation='energy_weighted'
- Processing: 2-3 seconds

Setup 3: Balanced Path (default recommendation)
- Use auto_chunking with threshold=10.0 seconds
- chunk_size=2.0 seconds
- overlap=0.2
- aggregation='weighted_normalized'
- Processing: 0.5-3 seconds based on audio length
        '''
        print(guide)
    
    @staticmethod
    def testing_chunking():
        """
        Code for testing and validating chunking implementation
        """
        print("\n" + "="*60)
        print("TESTING & VALIDATION CODE")
        print("="*60)
        
        code = '''
import numpy as np
from voice_embedding import (
    generate_embedding,
    generate_embedding_with_chunking,
    calculate_cosine_similarity
)

def test_chunking_stability(audio_bytes):
    """Test that chunking produces stable embeddings"""
    
    # Generate embedding multiple times with chunking
    embeddings = [
        generate_embedding_with_chunking(
            audio_bytes,
            aggregation_method='energy_weighted'
        )
        for _ in range(3)
    ]
    
    # Check similarity between runs
    sim_1_2 = calculate_cosine_similarity(embeddings[0], embeddings[1])
    sim_2_3 = calculate_cosine_similarity(embeddings[1], embeddings[2])
    sim_1_3 = calculate_cosine_similarity(embeddings[0], embeddings[2])
    
    print(f"Embedding stability test:")
    print(f"  Run 1 vs 2: {sim_1_2:.4f}")
    print(f"  Run 2 vs 3: {sim_2_3:.4f}")
    print(f"  Run 1 vs 3: {sim_1_3:.4f}")
    
    assert sim_1_2 > 0.99, "Low stability between runs"
    assert sim_2_3 > 0.99, "Low stability between runs"
    assert sim_1_3 > 0.99, "Low stability between runs"
    print("✓ Stability test PASSED")

def test_chunking_vs_standard(audio_bytes):
    """Compare chunked vs standard embedding"""
    
    standard_emb = generate_embedding(audio_bytes)
    chunked_emb = generate_embedding_with_chunking(
        audio_bytes,
        aggregation_method='mean'
    )
    
    similarity = calculate_cosine_similarity(standard_emb, chunked_emb)
    print(f"\\nChunked vs Standard similarity: {similarity:.4f}")
    
    # They should be reasonably similar
    assert similarity > 0.85, "Chunked embedding too different from standard"
    print("✓ Consistency test PASSED")

def test_all_aggregation_methods(audio_bytes):
    """Test all aggregation methods"""
    
    methods = [
        'mean', 'max', 'weighted_linear', 'weighted_inverse',
        'weighted_normalized', 'energy_weighted'
    ]
    
    embeddings = {}
    for method in methods:
        try:
            embeddings[method] = generate_embedding_with_chunking(
                audio_bytes,
                aggregation_method=method
            )
            print(f"✓ {method:20} generated successfully")
        except Exception as e:
            print(f"✗ {method:20} failed: {e}")
    
    # Check that methods produce different results
    if len(embeddings) > 1:
        methods_list = list(embeddings.keys())
        sim = calculate_cosine_similarity(
            embeddings[methods_list[0]],
            embeddings[methods_list[1]]
        )
        print(f"\\nMethods produce different results: {sim < 0.99}")
        '''
        print(code)


def main():
    """Run all integration examples"""
    
    print("\n" * 2)
    print("╔" + "═" * 58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "Audio Chunking Integration Guide".center(58) + "║")
    print("║" + "Voice Biometric API".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "═" * 58 + "╝")
    
    guide = ChunkingIntegrationGuide()
    
    # Run all examples
    guide.integration_example_1_simple_chunking()
    guide.integration_example_2_auto_chunking()
    guide.integration_example_3_endpoint_variants()
    guide.audio_quality_handling()
    guide.performance_considerations()
    guide.comparison_recommendations()
    guide.testing_chunking()
    
    print("\n" + "="*60)
    print("QUICK START RECOMMENDATION:")
    print("="*60)
    print("""
For most use cases, use the auto-chunking endpoint:

    embedding = get_embedding_with_auto_chunking(
        audio_bytes,
        auto_chunk_threshold_seconds=10.0  # Chunk if > 10s
    )

This provides:
✓ Automatic handling of short and long audio
✓ Good balance between speed and accuracy
✓ No manual tuning required
✓ Seamless integration into existing code
    """)
    
    print("\n" + "="*60)
    print("Integration guide complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
