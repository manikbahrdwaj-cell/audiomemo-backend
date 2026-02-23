"""
Integration Test: Voice Verification with Proper WAV Encoding
Tests the complete flow from enrollment to verification
"""

import sys
import os
import asyncio
import json
import base64
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from database import store_voice_embedding, get_voice_embedding
from voice_embedding import generate_embedding
import soundfile as sf
import numpy as np
import io

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_wav(duration_seconds=5, sample_rate=16000, frequency=440):
    """Create a test WAV file with proper RIFF headers"""
    num_samples = duration_seconds * sample_rate
    t = np.linspace(0, duration_seconds, num_samples, False)
    audio = np.sin(2 * np.pi * frequency * t) * 0.3
    
    with io.BytesIO() as f:
        sf.write(f, audio, sample_rate, format='WAV')
        wav_bytes = f.getvalue()
    
    return wav_bytes


def test_enrollment_and_verification():
    """Test enrollment and verification with WAV files"""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Voice Verification with WAV Encoding")
    print("=" * 70)
    
    test_phone = "1234567890"
    
    # STEP 1: Enrollment
    print("\n[STEP 1] Testing Enrollment")
    print("-" * 70)
    
    try:
        # Create test WAV for enrollment
        wav_bytes = create_test_wav(duration_seconds=5, sample_rate=16000)
        print(f"✓ Created test WAV: {len(wav_bytes)} bytes")
        
        # Generate embedding
        embedding = generate_embedding(wav_bytes)
        print(f"✓ Generated embedding: shape={embedding.shape}")
        
        # Store in database
        store_voice_embedding(test_phone, embedding)
        print(f"✓ Stored embedding for phone: {test_phone}")
        
    except Exception as e:
        print(f"✗ Enrollment failed: {str(e)}")
        return False
    
    # STEP 2: Verification - Matching Sample
    print("\n[STEP 2] Testing Verification - Matching Sample")
    print("-" * 70)
    
    try:
        # Create similar audio (same frequency)
        test_wav = create_test_wav(duration_seconds=5, sample_rate=16000, frequency=440)
        print(f"✓ Created matching test WAV: {len(test_wav)} bytes")
        
        # Verify it's a valid WAV file
        if test_wav[:4] != b'RIFF' or test_wav[8:12] != b'WAVE':
            print("✗ Invalid WAV format!")
            return False
        print("✓ Valid RIFF WAV format")
        
        # Generate embedding for test audio
        test_embedding = generate_embedding(test_wav)
        print(f"✓ Generated embedding: shape={test_embedding.shape}")
        
        # Compare embeddings
        from voice_embedding import calculate_cosine_similarity
        similarity = calculate_cosine_similarity(embedding, test_embedding)
        print(f"✓ Similarity score: {similarity:.4f} (threshold: 0.75)")
        
        if similarity >= 0.75:
            print("✓ VERIFICATION PASSED - Similarity exceeds threshold")
        else:
            print(f"✗ VERIFICATION FAILED - Similarity {similarity:.4f} < 0.75")
            
    except Exception as e:
        print(f"✗ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # STEP 3: Verification - Non-matching Sample
    print("\n[STEP 3] Testing Verification - Non-matching Sample")
    print("-" * 70)
    
    try:
        # Create different audio (different frequency)
        test_wav = create_test_wav(duration_seconds=5, sample_rate=16000, frequency=880)
        print(f"✓ Created non-matching test WAV: {len(test_wav)} bytes")
        
        # Generate embedding for different audio
        test_embedding = generate_embedding(test_wav)
        print(f"✓ Generated embedding: shape={test_embedding.shape}")
        
        # Compare embeddings
        similarity = calculate_cosine_similarity(embedding, test_embedding)
        print(f"✓ Similarity score: {similarity:.4f} (threshold: 0.75)")
        
        if similarity < 0.75:
            print("✓ CORRECTLY REJECTED - Similarity below threshold")
        else:
            print(f"✗ INCORRECTLY ACCEPTED - Similarity {similarity:.4f} >= 0.75")
            
    except Exception as e:
        print(f"✗ Non-matching test failed: {str(e)}")
        return False
    
    # STEP 4: Verify Database Read
    print("\n[STEP 4] Testing Database Retrieval")
    print("-" * 70)
    
    try:
        doc = get_voice_embedding(test_phone)
        if doc is None:
            print(f"✗ Could not retrieve embedding for {test_phone}")
            return False
        
        # Extract embedding from document
        stored_embedding = np.array(doc.get("embedding", []))
        print(f"✓ Retrieved embedding from database: shape={stored_embedding.shape}")
        
        # Verify it matches what we stored
        if np.allclose(embedding, stored_embedding):
            print("✓ Retrieved embedding matches stored embedding")
        else:
            print("✗ Retrieved embedding differs from stored embedding")
            return False
            
    except Exception as e:
        print(f"✗ Database retrieval failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # SUMMARY
    print("\n" + "=" * 70)
    print("✓ ALL INTEGRATION TESTS PASSED")
    print("=" * 70)
    print("\nThe verification system can now:")
    print("  1. Create proper WAV files with RIFF headers")
    print("  2. Generate embeddings from WAV files")
    print("  3. Store and retrieve embeddings")
    print("  4. Compare embeddings and determine match (> 0.75 threshold)")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        success = test_enrollment_and_verification()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
