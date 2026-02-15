"""
VERIFICATION SERVICE - QUICK REFERENCE & EXAMPLES
Practical examples for voice verification with MongoDB embeddings
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from verification_service import (
    get_verification_manager,
    VerificationSessionConfig,
    VerificationResult,
)
from database import store_voice_embedding, get_voice_embedding
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# QUICK START: BASIC VERIFICATION
# ============================================================================

def example_basic_verification():
    """
    Most basic verification workflow
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Verification")
    print("="*60)
    
    # Get verification manager
    manager = get_verification_manager()
    
    # Create verification session for a phone number
    phone_number = "+1-234-567-8900"
    
    try:
        session = manager.create_session(phone_number)
        print(f"✓ Created verification session: {session.session_id}")
        print(f"  Status: {session.status.value}")
        print(f"  Threshold: {session.config.similarity_threshold}")
        
    except ValueError as e:
        print(f"✗ Error: {e}")


# ============================================================================
# EXAMPLE 2: CUSTOM THRESHOLD
# ============================================================================

def example_custom_threshold():
    """
    Use custom similarity threshold for stricter or looser matching
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Custom Similarity Threshold")
    print("="*60)
    
    # Create custom config with higher threshold (stricter)
    config = VerificationSessionConfig(
        similarity_threshold=0.90,  # Default is 0.85
        max_attempts=3
    )
    
    manager = get_verification_manager(config)
    print(f"✓ Manager configured with threshold: {config.similarity_threshold}")
    print("  Higher threshold = stricter matching")
    
    # For lower threshold (looser matching):
    config_loose = VerificationSessionConfig(
        similarity_threshold=0.75,
        max_attempts=5
    )
    print(f"\n✓ Alternative config with threshold: {config_loose.similarity_threshold}")
    print("  Lower threshold = more lenient matching")


# ============================================================================
# EXAMPLE 3: RETRIEVE STORED EMBEDDING
# ============================================================================

def example_retrieve_embedding():
    """
    Retrieve enrolled embedding from MongoDB for inspection
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Retrieve Stored Embedding from MongoDB")
    print("="*60)
    
    phone_number = "+1-234-567-8900"
    
    # Retrieve enrollment data
    enrollment = get_voice_embedding(phone_number)
    
    if enrollment:
        print(f"✓ Retrieved enrollment for {phone_number}:")
        print(f"  - Dimension: {enrollment.get('embedding_dimension')}")
        print(f"  - Created: {enrollment.get('created_at')}")
        print(f"  - Updated: {enrollment.get('updated_at')}")
        
        # Access embedding
        embedding = np.array(enrollment['embedding'])
        print(f"  - Embedding shape: {embedding.shape}")
        print(f"  - Embedding dtype: {embedding.dtype}")
        print(f"  - First 5 values: {embedding[:5]}")
    else:
        print(f"✗ No enrollment found for {phone_number}")


# ============================================================================
# EXAMPLE 4: SESSION SUMMARY & HISTORY
# ============================================================================

def example_session_summary():
    """
    Get detailed summary and history of verification attempts
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Session Summary & Verification History")
    print("="*60)
    
    manager = get_verification_manager()
    
    # Create test session
    try:
        session = manager.create_session("+1-234-567-8900")
        
        # Get session summary
        summary = manager.get_session_summary(session.session_id)
        
        print("✓ Session Summary:")
        print(f"  - Session ID: {summary['session_id']}")
        print(f"  - Phone: {summary['phone_number']}")
        print(f"  - Status: {summary['status']}")
        print(f"  - Verified: {summary['verified']}")
        print(f"  - Final score: {summary['final_similarity_score']:.4f}")
        print(f"  - Attempts: {summary['attempts']}/{summary['max_attempts']}")
        
        # Get verification history
        history = manager.get_verification_history("+1-234-567-8900", limit=5)
        print(f"\n✓ Verification History ({len(history)} records):")
        for record in history:
            print(f"  - {record['result']}: {record['similarity_score']:.4f}")
        
    except ValueError as e:
        print(f"✗ Error: {e}")


# ============================================================================
# EXAMPLE 5: MANAGER STATISTICS
# ============================================================================

def example_statistics():
    """
    Get overall statistics from verification manager
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Manager Statistics")
    print("="*60)
    
    manager = get_verification_manager()
    
    stats = manager.get_statistics()
    
    print("✓ Verification Statistics:")
    print(f"  - Total sessions: {stats['total_sessions']}")
    print(f"  - Completed: {stats['completed_sessions']}")
    print(f"  - Verified: {stats['verified_sessions']}")
    print(f"  - Success rate: {stats['success_rate']:.2%}")
    print(f"  - Total attempts: {stats['total_attempts']}")
    print(f"  - Avg similarity: {stats['avg_similarity_score']:.4f}")


# ============================================================================
# EXAMPLE 6: ERROR HANDLING
# ============================================================================

def example_error_handling():
    """
    Proper error handling for verification operations
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: Error Handling")
    print("="*60)
    
    manager = get_verification_manager()
    
    # Handle non-enrolled phone
    try:
        session = manager.create_session("+1-999-INVALID-XXX")
    except ValueError as e:
        print(f"✓ Caught error for invalid phone: {e}")
    
    # Handle invalid session ID
    summary = manager.get_session_summary("invalid-session-id")
    if summary is None:
        print("✓ Properly handled invalid session ID")
    
    # Handle unenrolled number
    is_enrolled = "+1-234-567-8900"  # Assuming not enrolled
    try:
        session = manager.create_session(is_enrolled)
        print(f"✓ Session created for {is_enrolled}")
    except ValueError as e:
        print(f"✓ Properly handled unenrolled user: {e}")


# ============================================================================
# EXAMPLE 7: CUSTOM CONFIG FOR SESSION
# ============================================================================

def example_custom_session_config():
    """
    Create session with custom configuration
    """
    print("\n" + "="*60)
    print("EXAMPLE 7: Custom Session Configuration")
    print("="*60)
    
    manager = get_verification_manager()
    
    # Custom config for this specific session
    custom_config = VerificationSessionConfig(
        max_attempts=2,  # Only 2 attempts
        similarity_threshold=0.88,  # Stricter threshold
        session_timeout_seconds=120,  # 2 minute timeout
        auto_process=True,
        use_auto_chunking=False
    )
    
    print("✓ Custom config created:")
    print(f"  - Max attempts: {custom_config.max_attempts}")
    print(f"  - Threshold: {custom_config.similarity_threshold}")
    print(f"  - Timeout: {custom_config.session_timeout_seconds}s")
    print(f"  - Auto process: {custom_config.auto_process}")


# ============================================================================
# EXAMPLE 8: SESSION LIFECYCLE
# ============================================================================

def example_session_lifecycle():
    """
    Complete session lifecycle from creation to completion
    """
    print("\n" + "="*60)
    print("EXAMPLE 8: Session Lifecycle")
    print("="*60)
    
    manager = get_verification_manager()
    phone = "+1-234-567-8900"
    
    try:
        # Step 1: Create session
        print("\n1. CREATE SESSION")
        session = manager.create_session(phone)
        print(f"   - Session created: {session.session_id}")
        print(f"   - Status: {session.status.value}")
        print(f"   - Can verify: {session.can_attempt_verification()}")
        
        # Step 2: Check session details
        print("\n2. RETRIEVE SESSION")
        retrieved = manager.get_session(session.session_id)
        print(f"   - Retrieved: {retrieved is not None}")
        print(f"   - Remaining attempts: {retrieved.get_remaining_attempts()}")
        
        # Step 3: Get summary before any attempts
        print("\n3. GET INITIAL SUMMARY")
        summary_before = manager.get_session_summary(session.session_id)
        print(f"   - Attempts: {summary_before['attempts']}")
        print(f"   - Status: {summary_before['status']}")
        
        # Note: Actual verification would happen here
        # result, score, error = await manager.verify(session_id, audio_data, sample_rate)
        
        # Step 4: Cancel if needed
        print("\n4. CANCEL SESSION")
        manager.cancel_session(session.session_id)
        summary_after = manager.get_session_summary(session.session_id)
        print(f"   - Status: {summary_after['status']}")
        print(f"   - Result: {summary_after['final_result']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


# ============================================================================
# EXAMPLE 9: CLEANUP EXPIRED SESSIONS
# ============================================================================

def example_cleanup():
    """
    Clean up expired sessions from memory
    """
    print("\n" + "="*60)
    print("EXAMPLE 9: Cleanup Expired Sessions")
    print("="*60)
    
    manager = get_verification_manager()
    
    # Cleanup expired sessions
    cleaned = manager.cleanup_expired_sessions()
    
    print(f"✓ Cleanup performed")
    print(f"  - Expired sessions removed: {cleaned}")
    
    # Get current stats
    stats = manager.get_statistics()
    print(f"  - Active sessions remaining: {stats['total_sessions']}")


# ============================================================================
# EXAMPLE 10: INTEGRATION WITH API
# ============================================================================

def example_api_integration():
    """
    Example of how to integrate verification service in FastAPI
    """
    print("\n" + "="*60)
    print("EXAMPLE 10: API Integration Pattern")
    print("="*60)
    
    print("""
# In your FastAPI endpoint:

from fastapi import FastAPI, HTTPException
from verification_service import get_verification_manager

app = FastAPI()
verification_manager = get_verification_manager()

@app.post("/verify/start")
async def start_verification(phone_number: str):
    \"\"\"Start verification session\"\"\"
    try:
        session = verification_manager.create_session(phone_number)
        return {
            "session_id": session.session_id,
            "phone_number": session.phone_number,
            "max_attempts": session.config.max_attempts
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/verify/{session_id}")
async def verify(session_id: str, audio: UploadFile):
    \"\"\"Perform verification\"\"\"
    session = verification_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Read audio and generate embedding
    audio_data = await audio.read()
    
    # Verify
    result, score, error = await verification_manager.verify(
        session_id,
        audio_data,
        sample_rate=16000
    )
    
    return {
        "result": result.value,
        "similarity_score": score,
        "verified": result == VerificationResult.MATCH
    }

@app.get("/verify/{session_id}/summary")
async def verify_summary(session_id: str):
    \"\"\"Get verification summary\"\"\"
    summary = verification_manager.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary
    """)


# ============================================================================
# CONFIGURATION REFERENCE
# ============================================================================

def print_configuration_reference():
    """
    Print configuration reference
    """
    print("\n" + "="*60)
    print("CONFIGURATION REFERENCE")
    print("="*60)
    
    print("""
VerificationSessionConfig Parameters:
────────────────────────────────────────

1. max_attempts (int)
   Default: 3
   Range: >= 1
   Description: Maximum number of verification attempts per session

2. attempt_timeout_seconds (int)
   Default: 60
   Range: > 0
   Description: Timeout for a single verification attempt

3. session_timeout_seconds (int)
   Default: 300
   Range: > 0
   Description: Total timeout for entire verification session

4. similarity_threshold (float)
   Default: 0.85
   Range: [0.70, 0.99]
   Description: Similarity score threshold for acceptance

5. auto_process (bool)
   Default: True
   Description: Automatically generate embeddings for each attempt

6. use_auto_chunking (bool)
   Default: False
   Description: Use automatic audio chunking for long audio


Similarity Thresholds:
────────────────────────────────────────

Strict (0.90 - 0.99)
  - Use for high-security applications
  - More false negatives (reject valid speakers)
  - Fewer false positives (accept invalid speakers)

Moderate (0.80 - 0.90)
  - Balanced security and convenience
  - Recommended for most applications
  - Default: 0.85

Lenient (0.70 - 0.80)
  - Use for low-security applications
  - Fewer false negatives (accept valid speakers)
  - More false positives (accept invalid speakers)
    """)


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

def print_troubleshooting():
    """
    Print troubleshooting guide
    """
    print("\n" + "="*60)
    print("TROUBLESHOOTING GUIDE")
    print("="*60)
    
    print("""
Issue: "Phone number is not enrolled"
Solution:
  - Ensure the phone number was enrolled using the enrollment service
  - Check MongoDB connection: verify_phone = check_enrollment("+1-xxx-xxx-xxxx")
  - Check for exact phone number format match

Issue: "Verification attempts exhausted"
Solution:
  - Increase max_attempts in VerificationSessionConfig
  - Reduce similarity_threshold if threshold is too strict
  - Check audio quality for verification

Issue: "Session expired"
Solution:
  - Increase session_timeout_seconds in VerificationSessionConfig
  - Perform verification faster
  - Create new session if needed

Issue: High false rejection rate
Solution:
  - Lower similarity_threshold (try 0.80 instead of 0.85)
  - Check audio quality and duration
  - Ensure consistent microphone/acoustic environment

Issue: High false acceptance rate
Solution:
  - Increase similarity_threshold (try 0.90 instead of 0.85)
  - Increase max_attempts to allow retries
  - Verify enrollment embedding quality
    """)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("VERIFICATION SERVICE - QUICK REFERENCE & EXAMPLES")
    print("="*70)
    print("\nThis guide covers common verification scenarios and configurations")
    
    try:
        # Basic examples (no MongoDB required)
        example_basic_verification()
        example_custom_threshold()
        example_session_lifecycle()
        example_error_handling()
        
        # Configuration
        example_custom_session_config()
        print_configuration_reference()
        
        # API integration
        example_api_integration()
        
        # Troubleshooting
        print_troubleshooting()
        
        print("\n" + "="*70)
        print("✓ All examples completed successfully!")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
