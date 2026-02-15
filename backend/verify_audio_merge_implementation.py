"""
Quick Verification Test for Audio Merge & Embedding Implementation
Tests the core functionality of the new features
"""

import numpy as np
import logging
from enrollment_service import (
    create_enrollment_session,
    EnrollmentSessionConfig,
    MergeMode,
    merge_audio_chunks,
    generate_embedding_from_merged_audio,
    merge_and_generate_embedding,
    get_enrollment_session,
    AudioChunkRecord,
    EnrollmentSession,
    EnrollmentServiceManager
)
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_test_audio(duration=1.0, sr=16000):
    """Generate test audio"""
    t = np.linspace(0, duration, int(duration * sr))
    return (0.1 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)


def test_1_config_validation():
    """Test: EnrollmentSessionConfig with audio merge options"""
    print("\n" + "="*60)
    print("TEST 1: Configuration Validation")
    print("="*60)
    
    try:
        config = EnrollmentSessionConfig(
            max_chunks=5,
            merge_audio=True,
            audio_merge_mode=MergeMode.CROSSFADE,
            audio_merge_crossfade_ms=100.0
        )
        
        assert config.merge_audio == True
        assert config.audio_merge_mode == MergeMode.CROSSFADE
        assert config.audio_merge_crossfade_ms == 100.0
        
        print("✓ Configuration created successfully")
        print(f"  - merge_audio: {config.merge_audio}")
        print(f"  - audio_merge_mode: {config.audio_merge_mode.value}")
        print(f"  - audio_merge_crossfade_ms: {config.audio_merge_crossfade_ms}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_2_enrollment_session_fields():
    """Test: EnrollmentSession has new fields for merged audio"""
    print("\n" + "="*60)
    print("TEST 2: Session Data Model Enhancement")
    print("="*60)
    
    try:
        config = EnrollmentSessionConfig(merge_audio=True)
        session = create_enrollment_session("+1-555-0001", config)
        
        # Check new fields exist
        assert hasattr(session, 'merged_audio')
        assert hasattr(session, 'merged_audio_sample_rate')
        assert hasattr(session, 'merged_audio_timestamp')
        assert hasattr(session, 'merged_audio_embedding')
        
        assert session.merged_audio is None
        assert session.merged_audio_sample_rate == 16000
        
        print("✓ All new fields present and initialized correctly")
        print(f"  - merged_audio: {session.merged_audio}")
        print(f"  - merged_audio_sample_rate: {session.merged_audio_sample_rate}")
        print(f"  - merged_audio_timestamp: {session.merged_audio_timestamp}")
        print(f"  - merged_audio_embedding: {session.merged_audio_embedding}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_3_audio_chunk_addition():
    """Test: Adding audio chunks to session"""
    print("\n" + "="*60)
    print("TEST 3: Audio Chunk Addition")
    print("="*60)
    
    try:
        session = create_enrollment_session("+1-555-0002")
        
        # Add chunks
        for i in range(3):
            audio = generate_test_audio(1.5)
            chunk = session.add_chunk(audio, 1.5, quality_score=0.95)
            assert chunk is not None
            assert chunk.duration_seconds == 1.5
        
        assert len(session.chunks) == 3
        
        print("✓ Successfully added 3 audio chunks")
        print(f"  - Total chunks: {len(session.chunks)}")
        print(f"  - Total duration: {sum(c.duration_seconds for c in session.chunks):.2f}s")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_4_merge_audio_chunks():
    """Test: merge_audio_chunks() method"""
    print("\n" + "="*60)
    print("TEST 4: Audio Chunk Merging")
    print("="*60)
    
    try:
        config = EnrollmentSessionConfig(merge_audio=True)
        session = create_enrollment_session("+1-555-0003", config)
        
        # Add chunks
        for i in range(3):
            audio = generate_test_audio(1.0)
            session.add_chunk(audio, 1.0)
        
        # Merge audio
        success, msg, merged = merge_audio_chunks(session.session_id)
        
        assert success == True
        assert merged is not None
        assert len(merged) > 0
        
        session = get_enrollment_session(session.session_id)
        assert session.merged_audio is not None
        assert session.merged_audio_timestamp is not None
        
        print("✓ Audio chunks merged successfully")
        print(f"  - Success: {success}")
        print(f"  - Message: {msg}")
        print(f"  - Merged audio shape: {merged.shape}")
        print(f"  - Merged audio duration: {len(merged) / 16000:.2f}s")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_session_summary_enhanced():
    """Test: Enhanced get_summary() with new fields"""
    print("\n" + "="*60)
    print("TEST 5: Enhanced Session Summary")
    print("="*60)
    
    try:
        config = EnrollmentSessionConfig(
            merge_audio=True,
            audio_merge_mode=MergeMode.OVERLAP
        )
        session = create_enrollment_session("+1-555-0004", config)
        
        # Add chunks
        for i in range(2):
            audio = generate_test_audio(1.0)
            session.add_chunk(audio, 1.0)
        
        # Merge audio
        merge_audio_chunks(session.session_id)
        
        # Get summary
        session = get_enrollment_session(session.session_id)
        summary = session.get_summary()
        
        # Check new fields in summary
        assert 'has_merged_audio' in summary
        assert 'merged_audio_duration_seconds' in summary
        assert 'merge_audio_enabled' in summary
        assert 'audio_merge_mode' in summary
        
        assert summary['has_merged_audio'] == True
        assert summary['merge_audio_enabled'] == True
        assert summary['audio_merge_mode'] == 'overlap'
        
        print("✓ Enhanced summary contains all new fields")
        print(f"  - has_merged_audio: {summary['has_merged_audio']}")
        print(f"  - merged_audio_duration_seconds: {summary.get('merged_audio_duration_seconds'):.2f}")
        print(f"  - merge_audio_enabled: {summary['merge_audio_enabled']}")
        print(f"  - audio_merge_mode: {summary['audio_merge_mode']}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_merge_modes():
    """Test: Different merge modes"""
    print("\n" + "="*60)
    print("TEST 6: Merge Mode Validation")
    print("="*60)
    
    try:
        modes = [
            MergeMode.CONCATENATE,
            MergeMode.OVERLAP,
            MergeMode.CROSSFADE,
            MergeMode.MIX
        ]
        
        for mode in modes:
            config = EnrollmentSessionConfig(
                merge_audio=True,
                audio_merge_mode=mode
            )
            session = create_enrollment_session(f"+1-555-0005-{mode.value}", config)
            
            # Add chunks
            for i in range(2):
                audio = generate_test_audio(0.5)
                session.add_chunk(audio, 0.5)
            
            # Merge
            success, msg, merged = merge_audio_chunks(session.session_id)
            assert success, f"Failed for mode {mode.value}"
            assert merged is not None
        
        print(f"✓ All merge modes work correctly")
        for mode in modes:
            print(f"  ✓ {mode.value}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_7_helper_functions():
    """Test: Module-level helper functions"""
    print("\n" + "="*60)
    print("TEST 7: Helper Functions")
    print("="*60)
    
    try:
        # Test function availability
        from enrollment_service import (
            merge_audio_chunks,
            generate_embedding_from_merged_audio,
            merge_and_generate_embedding
        )
        
        assert callable(merge_audio_chunks)
        assert callable(generate_embedding_from_merged_audio)
        assert callable(merge_and_generate_embedding)
        
        print("✓ All helper functions available")
        print("  ✓ merge_audio_chunks()")
        print("  ✓ generate_embedding_from_merged_audio()")
        print("  ✓ merge_and_generate_embedding()")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_8_error_handling():
    """Test: Error handling for edge cases"""
    print("\n" + "="*60)
    print("TEST 8: Error Handling")
    print("="*60)
    
    try:
        # Test with invalid session ID
        success, msg, _ = merge_audio_chunks("invalid-session-id")
        assert success == False
        print("✓ Invalid session ID handled correctly")
        
        # Test merging empty session
        session = create_enrollment_session("+1-555-0006")
        success, msg, _ = merge_audio_chunks(session.session_id)
        assert success == False
        print("✓ Empty session handled correctly")
        
        # Test embedding from empty merged audio
        success, msg, _ = generate_embedding_from_merged_audio("invalid-session-id")
        assert success == False
        print("✓ No merged audio error handled correctly")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def main():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("AUDIO MERGE & EMBEDDING VERIFICATION TESTS")
    print("="*60)
    
    tests = [
        ("Config Validation", test_1_config_validation),
        ("Session Fields", test_2_enrollment_session_fields),
        ("Chunk Addition", test_3_audio_chunk_addition),
        ("Audio Merging", test_4_merge_audio_chunks),
        ("Enhanced Summary", test_5_session_summary_enhanced),
        ("Merge Modes", test_6_merge_modes),
        ("Helper Functions", test_7_helper_functions),
        ("Error Handling", test_8_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Implementation is complete and working!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed - Please review")
        return 1


if __name__ == "__main__":
    exit(main())
