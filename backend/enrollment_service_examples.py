"""
Enrollment Service - Practical Usage Examples
Demonstrates various use cases for the enrollment service
"""

import requests
import json
import time
from pathlib import Path
from typing import Optional, List
import numpy as np


# Configuration
API_BASE_URL = "http://localhost:8000"
ENROLLMENT_SESSION_ENDPOINT = f"{API_BASE_URL}/enrollment/session"
CHUNK_UPLOAD_ENDPOINT_TEMPLATE = "{base}/enrollment/session/{session_id}/chunk"
FINALIZE_ENDPOINT_TEMPLATE = "{base}/enrollment/session/{session_id}/finalize"
GET_STATUS_ENDPOINT_TEMPLATE = "{base}/enrollment/session/{session_id}"
CLEANUP_ENDPOINT = f"{API_BASE_URL}/enrollment/cleanup"


class EnrollmentClient:
    """Client for interacting with enrollment service"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session_id = None
        self.phone_number = None
        
    def create_session(self, phone_number: str, max_chunks: int = 5) -> Optional[dict]:
        """Create a new enrollment session"""
        print(f"\n📋 Creating enrollment session for {phone_number}...")
        
        try:
            response = requests.post(
                ENROLLMENT_SESSION_ENDPOINT,
                params={
                    "phone_number": phone_number,
                    "max_chunks": max_chunks
                }
            )
            response.raise_for_status()
            
            data = response.json()
            self.session_id = data["session_id"]
            self.phone_number = phone_number
            
            print(f"✅ Session created successfully!")
            print(f"   Session ID: {self.session_id[:16]}...")
            print(f"   Status: {data['status']}")
            print(f"   Max chunks: {data['max_chunks']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating session: {e}")
            return None
            
    def upload_chunk(self, audio_file: str, quality_score: float = 1.0) -> Optional[dict]:
        """Upload an audio chunk"""
        if not self.session_id:
            print("❌ No active session. Create a session first.")
            return None
            
        print(f"\n📤 Uploading audio chunk: {audio_file}...")
        
        try:
            # Check file exists
            if not Path(audio_file).exists():
                print(f"❌ File not found: {audio_file}")
                return None
                
            # Upload file
            with open(audio_file, 'rb') as f:
                files = {'file': f}
                params = {'quality_score': quality_score}
                
                response = requests.post(
                    CHUNK_UPLOAD_ENDPOINT_TEMPLATE.format(
                        base=self.base_url,
                        session_id=self.session_id
                    ),
                    files=files,
                    params=params
                )
                response.raise_for_status()
                
            data = response.json()
            
            if data.get('success'):
                chunk_info = data.get('chunk', {})
                print(f"✅ Chunk uploaded successfully!")
                print(f"   Chunk ID: {chunk_info.get('chunk_id', 'N/A')[:16]}...")
                print(f"   Progress: {chunk_info.get('chunk_number')}/{chunk_info.get('total_chunks')}")
                print(f"   Duration: {chunk_info.get('duration_seconds', 0):.2f}s")
                print(f"   Quality: {chunk_info.get('quality_score', 0):.2%}")
                print(f"   Has embedding: {chunk_info.get('has_embedding')}")
            else:
                print(f"❌ Upload failed: {data.get('message')}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error uploading chunk: {e}")
            return None
            
    def get_status(self) -> Optional[dict]:
        """Get current session status"""
        if not self.session_id:
            print("❌ No active session.")
            return None
            
        try:
            response = requests.get(
                GET_STATUS_ENDPOINT_TEMPLATE.format(
                    base=self.base_url,
                    session_id=self.session_id
                )
            )
            response.raise_for_status()
            
            data = response.json()
            
            print(f"\n📊 Session Status:")
            print(f"   Phone: {data['phone_number']}")
            print(f"   Status: {data['status']}")
            print(f"   Chunks collected: {data['chunks_collected']}/{data['max_chunks']}")
            print(f"   Embeddings generated: {data['embeddings_generated']}")
            print(f"   Created at: {data['created_at']}")
            
            if data.get('error_message'):
                print(f"   Error: {data['error_message']}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting status: {e}")
            return None
            
    def finalize(self, force_single: bool = False) -> Optional[dict]:
        """Finalize enrollment"""
        if not self.session_id:
            print("❌ No active session.")
            return None
            
        print(f"\n🔐 Finalizing enrollment...")
        
        try:
            response = requests.post(
                FINALIZE_ENDPOINT_TEMPLATE.format(
                    base=self.base_url,
                    session_id=self.session_id
                ),
                params={"force_single": force_single}
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                print(f"✅ Enrollment completed successfully!")
                print(f"   Phone: {data['phone_number']}")
                print(f"   Vector ID: {data.get('vector_id', 'N/A')[:16]}...")
                print(f"   Chunks processed: {data['chunks_processed']}")
                print(f"   Status: {data['enrollment_status']}")
            else:
                print(f"❌ Finalization failed: {data.get('message')}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error finalizing enrollment: {e}")
            return None
            
    def reset(self):
        """Reset client state"""
        self.session_id = None
        self.phone_number = None


# ============================================================================
# Example Usage Scenarios
# ============================================================================

def example_1_basic_enrollment():
    """
    Example 1: Basic enrollment with 3 audio chunks
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Enrollment (3 chunks)")
    print("="*60)
    
    client = EnrollmentClient()
    
    # Create session
    client.create_session("1234567890", max_chunks=3)
    
    # Simulate chunk uploads with dummy files
    # In real scenario, these would be actual audio files from user
    audio_files = [
        "voice_sample_1.wav",
        "voice_sample_2.wav",
        "voice_sample_3.wav"
    ]
    
    print("\n📝 Note: This example assumes audio files exist in current directory")
    print("   In production, you would use actual recorded audio files")
    
    # Check status before finalization
    client.get_status()
    
    # Finalize enrollment
    # client.finalize()
    
    client.reset()


def example_2_progressive_collection():
    """
    Example 2: Progressive audio collection with status checks
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Progressive Audio Collection")
    print("="*60)
    
    client = EnrollmentClient()
    
    # Create session with high max chunks
    client.create_session("9876543210", max_chunks=5)
    
    # Collect chunks progressively
    for i in range(1, 4):
        print(f"\n📦 Collecting chunk {i}...")
        
        # In real scenario, this would be actual recorded audio
        audio_file = f"sample_{i}.wav"
        
        # Simulate upload delay
        print(f"   (Simulating upload...)")
        time.sleep(0.5)
        
        # Check status after each chunk
        client.get_status()
    
    # Finalize when done
    # client.finalize()
    
    client.reset()


def example_3_quality_scoring():
    """
    Example 3: Upload chunks with quality scores
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Quality-Based Audio Collection")
    print("="*60)
    
    client = EnrollmentClient()
    
    client.create_session("5555555555", max_chunks=4)
    
    # Upload chunks with varying quality scores
    quality_scores = [0.85, 0.92, 0.88, 0.95]
    
    for idx, quality in enumerate(quality_scores, 1):
        print(f"\n🎤 Uploading sample {idx} with quality {quality:.0%}...")
        time.sleep(0.3)
        # client.upload_chunk(f"audio_{idx}.wav", quality_score=quality)
    
    client.reset()


def example_4_error_handling():
    """
    Example 4: Error handling and recovery
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Error Handling")
    print("="*60)
    
    client = EnrollmentClient()
    
    # Attempt to upload without session
    print("\n1️⃣ Attempting upload without session:")
    client.upload_chunk("dummy.wav")  # Should fail
    
    # Attempt to get status without session
    print("\n2️⃣ Attempting to get status without session:")
    client.get_status()  # Should fail
    
    # Create session and check nonexistent session
    print("\n3️⃣ Creating session:")
    client.create_session("1111111111")
    
    # Try to finalize with no chunks
    print("\n4️⃣ Attempting to finalize with no chunks:")
    client.finalize()
    
    client.reset()


def example_5_multi_user_enrollment():
    """
    Example 5: Multiple users enrolling simultaneously
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Multi-User Enrollment")
    print("="*60)
    
    # Simulate multiple users
    users = [
        "1111111111",
        "2222222222",
        "3333333333"
    ]
    
    clients = []
    
    # Create sessions for all users
    print("\n📋 Creating sessions for multiple users...")
    for phone in users:
        client = EnrollmentClient()
        client.create_session(phone, max_chunks=2)
        clients.append(client)
    
    # Check status for all
    print("\n📊 Checking status for all users...")
    for client in clients:
        client.get_status()
    
    # Cleanup
    for client in clients:
        client.reset()


def example_6_api_direct_usage():
    """
    Example 6: Direct API usage with raw requests
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: Direct API Usage")
    print("="*60)
    
    # 1. Create session
    print("\n1️⃣ Create Session")
    response = requests.post(
        ENROLLMENT_SESSION_ENDPOINT,
        params={
            "phone_number": "3333333333",
            "max_chunks": 3
        }
    )
    print(f"Status: {response.status_code}")
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"Session ID: {session_id[:16]}...\n")
    
    # 2. Get status
    print("2️⃣ Get Session Status")
    response = requests.get(
        GET_STATUS_ENDPOINT_TEMPLATE.format(
            base=API_BASE_URL,
            session_id=session_id
        )
    )
    print(f"Status: {response.status_code}")
    print(f"Chunks: {response.json()['chunks_collected']}/{response.json()['max_chunks']}\n")
    
    # 3. List all sessions
    print("3️⃣ List All Sessions")
    response = requests.get(f"{API_BASE_URL}/enrollment/sessions")
    print(f"Status: {response.status_code}")
    print(f"Total sessions: {response.json()['total_sessions']}\n")


def example_7_session_management():
    """
    Example 7: Session lifecycle management
    """
    print("\n" + "="*60)
    print("EXAMPLE 7: Session Lifecycle Management")
    print("="*60)
    
    client = EnrollmentClient()
    
    # Create session
    print("\n1️⃣ Creating session...")
    client.create_session("7777777777", max_chunks=5)
    session_id = client.session_id
    
    # Simulate some activity
    print("\n2️⃣ Getting status...")
    client.get_status()
    
    # List all sessions
    print("\n3️⃣ Listing all sessions...")
    response = requests.get(f"{API_BASE_URL}/enrollment/sessions")
    print(f"   Total active sessions: {response.json()['total_sessions']}")
    
    # Cancel session
    print("\n4️⃣ Cancelling session...")
    response = requests.delete(
        f"{API_BASE_URL}/enrollment/session/{session_id}"
    )
    print(f"   Result: {response.json().get('message')}")
    
    # Verify deletion
    print("\n5️⃣ Verifying deletion...")
    response = requests.get(
        GET_STATUS_ENDPOINT_TEMPLATE.format(
            base=API_BASE_URL,
            session_id=session_id
        )
    )
    print(f"   Status code: {response.status_code} (should be 404)")
    
    client.reset()


def example_8_cleanup_expired_sessions():
    """
    Example 8: Cleanup expired sessions
    """
    print("\n" + "="*60)
    print("EXAMPLE 8: Cleanup Expired Sessions")
    print("="*60)
    
    print("\n🧹 Cleaning up expired sessions...")
    response = requests.post(
        CLEANUP_ENDPOINT,
        params={"max_age_hours": 1}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Cleanup complete!")
        print(f"   Sessions cleaned: {data['sessions_cleaned']}")
        print(f"   Message: {data['message']}")
    else:
        print(f"❌ Cleanup failed: {response.status_code}")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run examples"""
    print("\n🎤 Enrollment Service - Usage Examples")
    print("=====================================\n")
    
    examples = {
        "1": ("Basic Enrollment", example_1_basic_enrollment),
        "2": ("Progressive Collection", example_2_progressive_collection),
        "3": ("Quality Scoring", example_3_quality_scoring),
        "4": ("Error Handling", example_4_error_handling),
        "5": ("Multi-User Enrollment", example_5_multi_user_enrollment),
        "6": ("Direct API Usage", example_6_api_direct_usage),
        "7": ("Session Management", example_7_session_management),
        "8": ("Cleanup Sessions", example_8_cleanup_expired_sessions),
    }
    
    print("Available Examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  0. Run All")
    print("  q. Quit\n")
    
    choice = input("Select example (0-8, or q): ").strip().lower()
    
    if choice == 'q':
        print("Goodbye!")
        return
    elif choice == '0':
        for name, func in examples.values():
            try:
                func()
            except Exception as e:
                print(f"\n❌ Error: {e}")
            time.sleep(1)
    elif choice in examples:
        name, func = examples[choice]
        try:
            func()
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
