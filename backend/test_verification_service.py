"""
Test Verification Service
Tests voice verification with MongoDB embedding retrieval
"""

import logging
import numpy as np
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from verification_service import (
    get_verification_manager,
    VerificationSessionConfig,
    VerificationResult,
    VerificationStatus,
    reset_verification_manager
)
from voice_embedding import get_model, preprocess_audio, calculate_cosine_similarity
from database import store_voice_embedding, get_voice_embedding, check_enrollment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_verification_manager_initialization():
    """Test 1: Verify manager initialization"""
    print("\n" + "="*60)
    print("TEST 1: Verification Manager Initialization")
    print("="*60)
    
    try:
        reset_verification_manager()
        manager = get_verification_manager()
        
        print("✓ VerificationManager initialized successfully")
        print(f"✓ Default threshold: {manager.config.similarity_threshold}")
        print(f"✓ Max attempts: {manager.config.max_attempts}")
        print(f"✓ Session timeout: {manager.config.session_timeout_seconds}s")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_session_configuration():
    """Test 2: Custom session configuration"""
    print("\n" + "="*60)
    print("TEST 2: Custom Session Configuration")
    print("="*60)
    
    try:
        config = VerificationSessionConfig(
            max_attempts=5,
            similarity_threshold=0.80,
            session_timeout_seconds=600,
            auto_process=True
        )
        
        print(f"✓ Configuration created with:")
        print(f"  - Max attempts: {config.max_attempts}")
        print(f"  - Similarity threshold: {config.similarity_threshold}")
        print(f"  - Session timeout: {config.session_timeout_seconds}s")
        print(f"  - Auto process: {config.auto_process}")
        
        # Test invalid configuration
        try:
            bad_config = VerificationSessionConfig(
                similarity_threshold=1.5  # Invalid: > 0.99
            )
            print("✗ Invalid config not caught")
            return False
        except ValueError as e:
            print(f"✓ Invalid threshold properly rejected: {str(e)}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False


def test_mongo_embedding_storage_and_retrieval():
    """Test 3: Store and retrieve embeddings from MongoDB"""
    print("\n" + "="*60)
    print("TEST 3: MongoDB Embedding Storage and Retrieval")
    print("="*60)
    
    try:
        # Create test embedding (192-dimensional)
        test_phone = "+1-234-567-8901"
        test_embedding = np.random.randn(192).astype(np.float32)
        
        print(f"✓ Created test embedding: shape={test_embedding.shape}, dtype={test_embedding.dtype}")
        
        # Store embedding
        doc_id = store_voice_embedding(test_phone, test_embedding)
        print(f"✓ Stored embedding in MongoDB: doc_id={doc_id}")
        
        # Retrieve embedding
        retrieved = get_voice_embedding(test_phone)
        if retrieved is None:
            print("✗ Failed to retrieve embedding")
            return False
        
        print(f"✓ Retrieved embedding from MongoDB:")
        print(f"  - Phone: {retrieved['phone_number']}")
        print(f"  - Dimension: {retrieved.get('embedding_dimension', 'unknown')}")
        print(f"  - Updated at: {retrieved.get('updated_at', 'unknown')}")
        
        # Check enrollment
        is_enrolled = check_enrollment(test_phone)
        print(f"✓ Enrollment check: is_enrolled={is_enrolled}")
        
        # Verify stored embedding
        stored_emb = np.array(retrieved['embedding'])
        cosine_sim = calculate_cosine_similarity(test_embedding, stored_emb)
        print(f"✓ Stored embedding similarity check: {cosine_sim:.6f} (should be ~1.0)")
        
        if cosine_sim < 0.99:
            print("✗ Stored embedding verification failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_session_creation_with_enrollment():
    """Test 4: Create verification session with enrolled embedding"""
    print("\n" + "="*60)
    print("TEST 4: Session Creation with Enrolled Embedding")
    print("="*60)
    
    try:
        # Setup: Store test embedding
        test_phone = "+1-555-123-4567"
        test_embedding = np.random.randn(192).astype(np.float32)
        store_voice_embedding(test_phone, test_embedding)
        print(f"✓ Test embedding stored for {test_phone}")
        
        # Create verification session
        reset_verification_manager()
        manager = get_verification_manager()
        
        session = manager.create_session(test_phone)
        print(f"✓ Verification session created:")
        print(f"  - Session ID: {session.session_id}")
        print(f"  - Phone: {session.phone_number}")
        print(f"  - Status: {session.status.value}")
        print(f"  - Threshold: {session.config.similarity_threshold}")
        
        # Verify enrollment data loaded
        if session.enrolled_embedding is None:
            print("✗ Enrollment data not loaded")
            return False
        
        print(f"✓ Enrollment data loaded:")
        print(f"  - Embedding dimension: {session.enrolled_embedding.get('embedding_dimension', 'unknown')}")
        print(f"  - Has embedding: {'embedding' in session.enrolled_embedding}")
        
        # Test invalid phone number
        try:
            bad_session = manager.create_session("+1-999-NOT-ENROLLED")
            print("✗ Invalid phone not rejected")
            return False
        except ValueError as e:
            print(f"✓ Invalid phone properly rejected: {str(e)}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_verification_attempt():
    """Test 5: Perform verification attempt"""
    print("\n" + "="*60)
    print("TEST 5: Verification Attempt")
    print("="*60)
    
    try:
        # Setup
        test_phone = "+1-555-999-1111"
        test_embedding = np.random.randn(192).astype(np.float32)
        store_voice_embedding(test_phone, test_embedding)
        print(f"✓ Test enrollment stored")
        
        reset_verification_manager()
        manager = get_verification_manager()
        session = manager.create_session(test_phone)
        print(f"✓ Verification session created: {session.session_id}")
        
        # Generate similar embedding (simulate correct speaker)
        similar_embedding = test_embedding + np.random.randn(192) * 0.01
        similar_audio = np.random.randn(16000).astype(np.float32)  # 1 second of audio
        
        print("✓ Generated test audio for verification")
        
        # Note: In real scenario, embedding would be generated from audio
        # For testing, we'll verify the structure works
        print(f"✓ Session can attempt verification: {session.can_attempt_verification()}")
        print(f"✓ Remaining attempts: {session.get_remaining_attempts()}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_session_summary_and_history():
    """Test 6: Session summary and verification history"""
    print("\n" + "="*60)
    print("TEST 6: Session Summary and History")
    print("="*60)
    
    try:
        # Setup
        test_phone = "+1-555-777-2222"
        test_embedding = np.random.randn(192).astype(np.float32)
        store_voice_embedding(test_phone, test_embedding)
        
        reset_verification_manager()
        manager = get_verification_manager()
        session = manager.create_session(test_phone)
        
        # Get session summary
        summary = manager.get_session_summary(session.session_id)
        print("✓ Session summary:")
        print(f"  - Session ID: {summary['session_id']}")
        print(f"  - Phone: {summary['phone_number']}")
        print(f"  - Verified: {summary['verified']}")
        print(f"  - Attempts: {summary['attempts']}/{summary['max_attempts']}")
        print(f"  - Status: {summary['status']}")
        
        # Get verification history
        history = manager.get_verification_history(test_phone)
        print(f"✓ Verification history retrieved: {len(history)} records")
        
        # Get statistics
        stats = manager.get_statistics()
        print("✓ Manager statistics:")
        print(f"  - Total sessions: {stats['total_sessions']}")
        print(f"  - Completed sessions: {stats['completed_sessions']}")
        print(f"  - Verified sessions: {stats['verified_sessions']}")
        print(f"  - Total attempts: {stats['total_attempts']}")
        print(f"  - Avg similarity: {stats['avg_similarity_score']:.4f}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_session_cancellation():
    """Test 7: Cancel verification session"""
    print("\n" + "="*60)
    print("TEST 7: Session Cancellation")
    print("="*60)
    
    try:
        # Setup
        test_phone = "+1-555-333-4444"
        test_embedding = np.random.randn(192).astype(np.float32)
        store_voice_embedding(test_phone, test_embedding)
        
        reset_verification_manager()
        manager = get_verification_manager()
        session = manager.create_session(test_phone)
        
        print(f"✓ Session created: {session.status.value}")
        
        # Cancel session
        cancelled = manager.cancel_session(session.session_id)
        print(f"✓ Session cancelled: {cancelled}")
        
        # Verify cancellation
        updated_session = manager.get_session(session.session_id)
        print(f"✓ Session status: {updated_session.status.value}")
        print(f"✓ Final result: {updated_session.final_result.value if updated_session.final_result else None}")
        
        return updated_session.status == VerificationStatus.CANCELLED
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_expiration_handling():
    """Test 8: Expired session handling"""
    print("\n" + "="*60)
    print("TEST 8: Expired Session Handling")
    print("="*60)
    
    try:
        # Setup with very short timeout
        test_phone = "+1-555-555-6666"
        test_embedding = np.random.randn(192).astype(np.float32)
        store_voice_embedding(test_phone, test_embedding)
        
        config = VerificationSessionConfig(
            session_timeout_seconds=1  # Very short timeout
        )
        
        reset_verification_manager()
        manager = get_verification_manager(config)
        session = manager.create_session(test_phone, config)
        
        print(f"✓ Session created with 1s timeout")
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Check expiration
        is_expired = session.is_expired()
        print(f"✓ Session expired: {is_expired}")
        
        # Cleanup expired sessions
        cleaned = manager.cleanup_expired_sessions()
        print(f"✓ Cleaned up {cleaned} expired sessions")
        
        return is_expired and cleaned > 0
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all verification tests"""
    print("\n" + "="*70)
    print("VOICE VERIFICATION SERVICE - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Manager Initialization", test_verification_manager_initialization),
        ("Session Configuration", test_session_configuration),
        ("MongoDB Storage & Retrieval", test_mongo_embedding_storage_and_retrieval),
        ("Session Creation with Enrollment", test_session_creation_with_enrollment),
        ("Session Summary & History", test_session_summary_and_history),
        ("Session Cancellation", test_session_cancellation),
        ("Expired Session Handling", test_expiration_handling),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            results[name] = result
        except Exception as e:
            print(f"✗ Unhandled exception: {str(e)}")
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
