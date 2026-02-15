"""
Test script for multi-chunk verification endpoints
"""

import requests
import json
import time
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Test audio files
TEST_AUDIO_DIR = Path("test_audio_files")
SPEAKER1_FILES = [
    "test_voice_speaker1.wav",
    "test_voice_speaker1_variant.wav"
]

def test_verification_chunk_endpoints():
    """Test the new chunk-based verification endpoints"""
    
    print("\n" + "="*80)
    print("Testing Multi-Chunk Verification Endpoints")
    print("="*80)
    
    # Step 1: Enroll a speaker first
    print("\n[Step 1] Enrolling speaker...")
    audio_file = TEST_AUDIO_DIR / SPEAKER1_FILES[0]
    
    if not audio_file.exists():
        print(f"ERROR: Test audio file not found: {audio_file}")
        return False
    
    with open(audio_file, "rb") as f:
        files = {"file": ("test_voice.wav", f, "audio/wav")}
        data = {"phone_number": "+1234567890"}
        response = requests.post(f"{API_BASE_URL}/enroll", files=files, data=data)
        
        if response.status_code != 200:
            print(f"ERROR: Enrollment failed: {response.status_code}")
            print(response.text)
            return False
        
        print(f"✓ Enrollment successful: {response.json()}")
    
    # Step 2: Create verification session
    print("\n[Step 2] Creating verification session...")
    response = requests.post(
        f"{API_BASE_URL}/verification/session",
        data={"phone_number": "+1234567890"}
    )
    
    if response.status_code != 200:
        print(f"ERROR: Session creation failed: {response.status_code}")
        print(response.text)
        return False
    
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"✓ Session created: {session_id}")
    print(f"  Status: {session_data['status']}")
    print(f"  Chunks: {session_data['chunks_collected']}/{session_data['max_chunks']}")
    
    # Step 3: Add audio chunks to session
    print("\n[Step 3] Adding audio chunks...")
    chunk_count = 0
    
    for file_name in SPEAKER1_FILES:
        audio_file = TEST_AUDIO_DIR / file_name
        
        if not audio_file.exists():
            print(f"WARNING: Audio file not found: {audio_file}")
            continue
        
        with open(audio_file, "rb") as f:
            files = {"file": ("chunk.wav", f, "audio/wav")}
            data = {"quality_score": "1.0"}
            response = requests.post(
                f"{API_BASE_URL}/verification/session/{session_id}/chunk",
                files=files,
                data=data
            )
            
            if response.status_code != 200:
                print(f"ERROR: Chunk upload failed: {response.status_code}")
                print(response.text)
                return False
            
            chunk_data = response.json()
            chunk_count += 1
            print(f"✓ Chunk {chunk_count} added:")
            print(f"  Chunk ID: {chunk_data['chunk']['chunk_id']}")
            print(f"  Duration: {chunk_data['chunk']['duration_seconds']:.2f}s")
            print(f"  Session status: {chunk_data['session_status']}")
    
    if chunk_count == 0:
        print("ERROR: No chunks were added")
        return False
    
    # Step 4: Get verification session status
    print("\n[Step 4] Checking verification session status...")
    response = requests.get(f"{API_BASE_URL}/verification/session/{session_id}/status")
    
    if response.status_code != 200:
        print(f"ERROR: Status check failed: {response.status_code}")
        print(response.text)
        return False
    
    status_data = response.json()
    print(f"✓ Session status:")
    print(f"  Status: {status_data['status']}")
    print(f"  Chunks collected: {status_data['chunks_collected']}/{status_data['max_chunks']}")
    print(f"  Error: {status_data['error_message']}")
    
    # Step 5: Finalize verification
    print("\n[Step 5] Finalizing verification...")
    response = requests.post(f"{API_BASE_URL}/verification/session/{session_id}/finalize")
    
    if response.status_code != 200:
        print(f"ERROR: Verification finalization failed: {response.status_code}")
        print(response.text)
        return False
    
    result_data = response.json()
    print(f"✓ Verification result:")
    print(f"  Phone: {result_data['phone_number']}")
    print(f"  Chunks processed: {result_data['chunks_processed']}")
    print(f"  Average similarity: {result_data['average_similarity']:.4f}")
    print(f"  Min similarity: {result_data['min_similarity']:.4f}")
    print(f"  Max similarity: {result_data['max_similarity']:.4f}")
    print(f"  Threshold: {result_data['threshold']:.4f}")
    print(f"  Is Match: {result_data['is_match']}")
    print(f"  Status: {result_data['verification_status']}")
    
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED!")
    print("="*80)
    
    return True


if __name__ == "__main__":
    print("\nStarting verification chunk endpoint tests...")
    print(f"API Base URL: {API_BASE_URL}")
    
    try:
        success = test_verification_chunk_endpoints()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
