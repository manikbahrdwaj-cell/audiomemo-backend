"""
Test Suite for MongoDB Enrollment Service
Tests all enrollment operations with MongoDB persistence
"""

import numpy as np
import logging
from datetime import datetime
from typing import Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_test_audio(duration_seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """
    Generate test audio data
    
    Args:
        duration_seconds: Duration of audio to generate
        sample_rate: Sample rate in Hz
        
    Returns:
        Audio data as numpy array
    """
    num_samples = int(duration_seconds * sample_rate)
    # Generate sine wave at 440 Hz (A4 note)
    t = np.linspace(0, duration_seconds, num_samples)
    frequency = 440.0
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    return audio


def test_create_session():
    """Test creating an enrollment session"""
    print("\n" + "="*60)
    print("TEST: Create Enrollment Session")
    print("="*60)
    
    from mongodb_enrollment_service import create_enrollment_session
    from enrollment_service import EnrollmentSessionConfig
    
    config = EnrollmentSessionConfig(
        max_chunks=5,
        min_chunks_required=2,
        merge_audio=False
    )
    
    session_id, session_data = create_enrollment_session("+1234567890", config)
    
    assert session_id is not None
    assert session_data["phone_number"] == "+1234567890"
    assert session_data["status"] == "active"
    assert session_data["chunks_collected"] == 0
    
    print(f"✓ Session created: {session_id[:8]}")
    print(f"✓ Phone: {session_data['phone_number']}")
    print(f"✓ Status: {session_data['status']}")
    
    return session_id


def test_add_audio_chunks(session_id: str):
    """Test adding audio chunks to session"""
    print("\n" + "="*60)
    print("TEST: Add Audio Chunks")
    print("="*60)
    
    from mongodb_enrollment_service import add_audio_chunk
    
    # Add 3 chunks
    chunk_ids = []
    for i in range(3):
        audio = generate_test_audio(duration_seconds=2.0)
        success, message, chunk_id = add_audio_chunk(
            session_id,
            audio,
            duration_seconds=2.0,
            sample_rate=16000,
            quality_score=0.9 + (i * 0.03)  # Slightly varying quality
        )
        
        assert success, f"Failed to add chunk {i+1}: {message}"
        assert chunk_id is not None
        chunk_ids.append(chunk_id)
        
        print(f"✓ Chunk {i+1} added: {chunk_id[:8]}")
        print(f"  Message: {message}")
    
    return chunk_ids


def test_get_session_summary(session_id: str):
    """Test getting session summary"""
    print("\n" + "="*60)
    print("TEST: Get Session Summary")
    print("="*60)
    
    from mongodb_enrollment_service import get_session_summary
    
    summary = get_session_summary(session_id)
    
    assert summary is not None
    assert summary["session_id"] == session_id
    assert summary["chunks_collected"] == 3
    
    print(f"✓ Session ID: {summary['session_id'][:8]}")
    print(f"✓ Phone: {summary['phone_number']}")
    print(f"✓ Status: {summary['status']}")
    print(f"✓ Chunks: {summary['chunks_collected']}")
    print(f"✓ Audio chunks saved: {summary['chunk_stats']['total_saved']}")
    print(f"✓ Total duration: {summary['chunk_stats']['total_duration_seconds']:.2f}s")
    print(f"✓ Total samples: {summary['chunk_stats']['total_samples']}")


def test_finalize_enrollment(session_id: str):
    """Test finalizing enrollment"""
    print("\n" + "="*60)
    print("TEST: Finalize Enrollment")
    print("="*60)
    
    from mongodb_enrollment_service import finalize_enrollment
    
    success, message, vector_id = finalize_enrollment(session_id)
    
    assert success, f"Finalization failed: {message}"
    assert vector_id is not None
    
    print(f"✓ Enrollment finalized successfully")
    print(f"✓ Vector ID: {vector_id[:8]}")
    print(f"✓ Message: {message}")


def test_get_enrollment_history():
    """Test getting enrollment history"""
    print("\n" + "="*60)
    print("TEST: Get Enrollment History")
    print("="*60)
    
    from mongodb_enrollment_service import get_enrollment_history
    
    history = get_enrollment_history("+1234567890", limit=10)
    
    assert isinstance(history, list)
    
    print(f"✓ Retrieved {len(history)} enrollment records")
    
    if history:
        latest = history[0]
        print(f"  Latest enrollment: {latest['session_id'][:8]}")
        print(f"  Status: {latest['status']}")
        print(f"  Chunks: {latest['chunks_collected']}")
        print(f"  Duration: {latest.get('duration_seconds', 'N/A')}")


def test_get_recent_completions():
    """Test getting recent enrollments"""
    print("\n" + "="*60)
    print("TEST: Get Recent Completions")
    print("="*60)
    
    from mongodb_enrollment_service import get_recent_completions
    
    recent = get_recent_completions(limit=10)
    
    assert isinstance(recent, list)
    
    print(f"✓ Retrieved {len(recent)} recent enrollment completions")
    
    if recent:
        for i, enrollment in enumerate(recent[:3]):
            print(f"  {i+1}. {enrollment['session_id'][:8]} - {enrollment['phone_number']} ({enrollment['chunks_collected']} chunks)")


def test_get_statistics():
    """Test getting enrollment statistics"""
    print("\n" + "="*60)
    print("TEST: Get Enrollment Statistics")
    print("="*60)
    
    from mongodb_enrollment_service import get_enrollment_statistics
    
    # Overall stats
    overall_stats = get_enrollment_statistics()
    
    print(f"✓ Overall Statistics:")
    print(f"  Total sessions: {overall_stats['total_sessions']}")
    print(f"  Total completions: {overall_stats['total_completions']}")
    print(f"  By status:")
    for status, count in overall_stats['by_status'].items():
        if count > 0:
            print(f"    - {status}: {count}")
    
    # Phone-specific stats
    phone_stats = get_enrollment_statistics("+1234567890")
    
    print(f"\n✓ Phone-Specific Statistics (+1234567890):")
    print(f"  Total sessions: {phone_stats['total_sessions']}")
    print(f"  Total completions: {phone_stats['total_completions']}")


def test_multiple_phone_numbers():
    """Test enrollment for multiple phone numbers"""
    print("\n" + "="*60)
    print("TEST: Multiple Phone Numbers")
    print("="*60)
    
    from mongodb_enrollment_service import create_enrollment_session, add_audio_chunk
    from enrollment_service import EnrollmentSessionConfig
    
    config = EnrollmentSessionConfig(max_chunks=3, min_chunks_required=1)
    
    phones = ["+1111111111", "+2222222222", "+3333333333"]
    
    for phone in phones:
        session_id, _ = create_enrollment_session(phone, config)
        
        # Add one chunk
        audio = generate_test_audio(1.5)
        add_audio_chunk(session_id, audio, 1.5)
        
        print(f"✓ Session created for {phone}: {session_id[:8]}")


def test_audio_merge_mode():
    """Test enrollment with audio merge enabled"""
    print("\n" + "="*60)
    print("TEST: Audio Merge Mode")
    print("="*60)
    
    from mongodb_enrollment_service import create_enrollment_session, add_audio_chunk, finalize_enrollment
    from enrollment_service import EnrollmentSessionConfig, MergeMode
    
    config = EnrollmentSessionConfig(
        max_chunks=3,
        min_chunks_required=2,
        merge_audio=True,
        audio_merge_mode=MergeMode.OVERLAP,
        audio_merge_crossfade_ms=100.0
    )
    
    session_id, session_data = create_enrollment_session("+1987654321", config)
    
    print(f"✓ Session created: {session_id[:8]}")
    print(f"  Merge audio: {session_data['merge_audio']}")
    print(f"  Merge mode: {session_data['audio_merge_mode']}")
    
    # Add chunks
    for i in range(2):
        audio = generate_test_audio(1.0)
        success, msg, _ = add_audio_chunk(session_id, audio, 1.0)
        print(f"✓ Chunk {i+1} added: {msg}")
    
    # Finalize
    success, message, vector_id = finalize_enrollment(session_id)
    print(f"✓ Finalization: {message}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print(" "*15 + "MONGODB ENROLLMENT SERVICE TEST SUITE")
    print("="*80)
    
    try:
        # Test 1: Create session
        session_id = test_create_session()
        
        # Test 2: Add chunks
        test_add_audio_chunks(session_id)
        
        # Test 3: Get summary
        test_get_session_summary(session_id)
        
        # Test 4: Finalize
        test_finalize_enrollment(session_id)
        
        # Test 5: Get history
        test_get_enrollment_history()
        
        # Test 6: Get recent
        test_get_recent_completions()
        
        # Test 7: Statistics
        test_get_statistics()
        
        # Test 8: Multiple phones
        test_multiple_phone_numbers()
        
        # Test 9: Audio merge
        test_audio_merge_mode()
        
        # Summary
        print("\n" + "="*80)
        print(" "*25 + "ALL TESTS PASSED ✓")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
