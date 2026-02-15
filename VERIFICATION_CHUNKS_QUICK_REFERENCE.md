"""
Quick reference for Multi-Chunk Verification Endpoints
"""

# ====== VERIFICATION ENDPOINTS ======

# 1. CREATE VERIFICATION SESSION
POST /verification/session
Content-Type: application/x-www-form-urlencoded

phone_number=+1234567890

Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "status": "initializing",
  "created_at": "2026-02-15T00:28:57.123456",
  "chunks_collected": 0,
  "max_chunks": 10,
  "error_message": null
}


# 2. ADD AUDIO CHUNK TO SESSION (repeat with different audio)
POST /verification/session/{session_id}/chunk
Content-Type: multipart/form-data

- file: <audio.wav>
- quality_score: 1.0 (optional, 0-1)

Response:
{
  "success": true,
  "message": "Chunk added (1/10)",
  "chunk": {
    "chunk_id": "550e8400-e29b-41d4-a716-446655440001",
    "chunk_number": 1,
    "total_chunks": 10,
    "duration_seconds": 3.45,
    "timestamp": "2026-02-15T00:28:58.123456",
    "has_embedding": true,
    "quality_score": 1.0
  },
  "session_status": "collecting"
}


# 3. GET SESSION STATUS
GET /verification/session/{session_id}/status

Response:
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "status": "collecting",
  "created_at": "2026-02-15T00:28:57.123456",
  "started_at": null,
  "completed_at": null,
  "chunks_collected": 1,
  "max_chunks": 10,
  "min_chunks_required": 1,
  "error_message": null,
  "verification_result": null
}


# 4. FINALIZE VERIFICATION
POST /verification/session/{session_id}/finalize

Response:
{
  "success": true,
  "message": "Verification completed",
  "phone_number": "+1234567890",
  "chunks_processed": 1,
  "average_similarity": 0.8765,
  "min_similarity": 0.8765,
  "max_similarity": 0.8765,
  "threshold": 0.75,
  "is_match": true,
  "verification_status": "completed"
}


# 5. CANCEL SESSION (optional)
POST /verification/session/{session_id}/cancel

Response:
{
  "success": true,
  "message": "Verification session cancelled",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}


# ====== EXAMPLE FLOW ======

# Step 1: Create session for a phone number
curl -X POST http://localhost:8000/verification/session \
  -F "phone_number=+1234567890"

# Response includes: session_id = "abc123..."

# Step 2: Add first chunk
curl -X POST http://localhost:8000/verification/session/abc123.../chunk \
  -F "file=@chunk1.wav" \
  -F "quality_score=1.0"

# Response: Chunk 1 added with embedding generated

# Step 3: Add second chunk
curl -X POST http://localhost:8000/verification/session/abc123.../chunk \
  -F "file=@chunk2.wav" \
  -F "quality_score=0.95"

# Response: Chunk 2 added with embedding generated

# Step 4: Check status
curl -X GET http://localhost:8000/verification/session/abc123.../status

# Response: Shows 2 chunks collected

# Step 5: Finalize verification
curl -X POST http://localhost:8000/verification/session/abc123.../finalize

# Response: 
# - Processes both chunk embeddings
# - Averages them into merged embedding
# - Compares against enrolled embedding
# - Returns:
#   - average_similarity: 0.8765
#   - min/max similarity from chunks
#   - is_match: true/false
#   - Individual chunk similarities


# ====== CONFIGURATION DEFAULTS ======

VerificationSessionConfig {
    max_chunks: 10                # Maximum number of chunks per session
    min_chunks_required: 1        # Minimum chunks needed
    max_attempts: 3               # Maximum verification attempts
    session_timeout_seconds: 300  # Session expires after 5 minutes
    similarity_threshold: 0.85    # Threshold for matching
    auto_process: True            # Auto-generate embeddings on upload
}


# ====== KEY DIFFERENCES: VERIFICATION vs ENROLLMENT ======

Enrollment Chunks:
  + Stores multiple embeddings
  + Merges to create final enrollment
  + Stored in MongoDB

Verification Chunks:
  + Collects verification samples
  + Each generates embedding
  + All compared against SINGLE enrolled embedding
  + Average similarity determines match


# ====== PYTHON CLIENT EXAMPLE ======

import requests

# 1. Create session
session_resp = requests.post(
    "http://localhost:8000/verification/session",
    data={"phone_number": "+1234567890"}
)
session_id = session_resp.json()["session_id"]

# 2. Add chunks
for audio_file in ["chunk1.wav", "chunk2.wav"]:
    with open(audio_file, "rb") as f:
        files = {"file": ("audio.wav", f, "audio/wav")}
        data = {"quality_score": "1.0"}
        response = requests.post(
            f"http://localhost:8000/verification/session/{session_id}/chunk",
            files=files,
            data=data
        )
        print(f"Chunk added: {response.json()['message']}")

# 3. Get status
status = requests.get(
    f"http://localhost:8000/verification/session/{session_id}/status"
).json()
print(f"Chunks: {status['chunks_collected']}/{status['max_chunks']}")

# 4. Finalize
result = requests.post(
    f"http://localhost:8000/verification/session/{session_id}/finalize"
).json()

print(f"Verification Result:")
print(f"  Is Match: {result['is_match']}")
print(f"  Average Similarity: {result['average_similarity']:.4f}")
print(f"  Threshold: {result['threshold']}")
