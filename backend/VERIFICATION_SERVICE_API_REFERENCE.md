# VERIFICATION SERVICE API REFERENCE
Voice Verification with MongoDB Embeddings Retrieval

## Overview

The Verification Service provides a complete voice verification system that:
- Retrieves stored speaker embeddings from MongoDB
- Performs real-time similarity comparison
- Manages verification sessions with attempt tracking
- Handles multiple verification attempts with configurable thresholds
- Provides comprehensive session tracking and statistics

## Installation

```python
# The verification service is part of the backend
from verification_service import (
    get_verification_manager,
    VerificationSessionConfig,
    VerificationResult,
    VerificationStatus
)
from database import get_voice_embedding
```

## Core Classes

### VerificationSessionConfig

Configuration for verification sessions.

**Parameters:**
- `max_attempts` (int, default=3): Maximum verification attempts (range: >= 1)
- `attempt_timeout_seconds` (int, default=60): Timeout for single attempt
- `session_timeout_seconds` (int, default=300): Total session timeout
- `similarity_threshold` (float, default=0.85): Acceptance threshold (range: 0.70-0.99)
- `auto_process` (bool, default=True): Auto-generate embeddings
- `use_auto_chunking` (bool, default=False): Use automatic audio chunking

**Example:**
```python
from verification_service import VerificationSessionConfig

config = VerificationSessionConfig(
    max_attempts=5,
    similarity_threshold=0.90,
    session_timeout_seconds=600
)
```

### VerificationSession

Active verification session with enrollment data and attempt tracking.

**Attributes:**
- `session_id` (str): Unique session identifier
- `phone_number` (str): Phone number being verified
- `status` (VerificationStatus): Current session status
- `attempts` (List[VerificationAttempt]): List of verification attempts
- `verified` (bool): Whether verification succeeded
- `final_similarity_score` (float): Similarity score from verification
- `enrolled_embedding` (Dict): Retrieved enrollment data from MongoDB

**Methods:**
```python
# Check if session is valid
session.can_attempt_verification() -> bool

# Get remaining attempts
session.get_remaining_attempts() -> int

# Check expiration
session.is_expired() -> bool

# Convert to dictionary
session.to_dict() -> Dict[str, Any]
```

### VerificationAttempt

Record of a single verification attempt.

**Attributes:**
- `attempt_id` (str): Unique attempt identifier
- `timestamp` (datetime): When attempt was made
- `audio_duration_seconds` (float): Duration of audio verified
- `similarity_score` (float): Computed similarity score
- `result` (VerificationResult): Result of attempt
- `threshold_used` (float): Threshold used for this attempt

### VerificationResult

Enum for verification outcomes.

**Values:**
- `MATCH`: Verification successful
- `MISMATCH`: Voice does not match stored enrollment
- `NOT_ENROLLED`: Phone number has no enrollment
- `ERROR`: Error during verification process
- `TIMEOUT`: Verification session timed out
- `CANCELLED`: Verification was cancelled

### VerificationStatus

Enum for session status.

**Values:**
- `INITIALIZING`: Session being initialized
- `ACTIVE`: Session ready for verification
- `PROCESSING`: Generating embedding
- `COMPARING`: Comparing with stored embedding
- `VERIFIED`: Verification successful
- `REJECTED`: Verification failed after attempts
- `FAILED`: Error occurred
- `EXPIRED`: Session timed out
- `CANCELLED`: Session was cancelled

## VerificationManager

Main class for managing verification operations.

### Initialization

```python
from verification_service import get_verification_manager

# Get global manager instance (singleton)
manager = get_verification_manager()

# Or create with custom config
from verification_service import VerificationSessionConfig, VerificationManager

config = VerificationSessionConfig(
    similarity_threshold=0.90,
    max_attempts=5
)
manager = VerificationManager(config)
```

### Methods

#### create_session(phone_number, config=None) → VerificationSession

Create a new verification session.

**Parameters:**
- `phone_number` (str): Phone number to verify (must be enrolled)
- `config` (VerificationSessionConfig, optional): Session-specific config

**Returns:** VerificationSession object

**Raises:** ValueError if phone not enrolled or invalid

**Example:**
```python
manager = get_verification_manager()

try:
    session = manager.create_session("+1-234-567-8900")
    print(f"Session created: {session.session_id}")
except ValueError as e:
    print(f"Error: {e}")
```

**MongoDB Integration:**
```python
# Retrieves enrollment from MongoDB automatically
# Looks up phone_number in voice_embeddings collection
# Requires prior enrollment via enrollment_service
```

#### get_session(session_id) → Optional[VerificationSession]

Retrieve a verification session by ID.

**Parameters:**
- `session_id` (str): Session identifier

**Returns:** VerificationSession or None if not found

**Example:**
```python
session = manager.get_session(session_id)
if session:
    print(f"Status: {session.status.value}")
else:
    print("Session not found")
```

#### verify(session_id, audio_data, sample_rate=16000) → Tuple

Perform voice verification.

**Parameters:**
- `session_id` (str): Session identifier
- `audio_data` (np.ndarray): Audio samples as float32 array
- `sample_rate` (int, default=16000): Sample rate in Hz

**Returns:** Tuple of (VerificationResult, similarity_score: float, error_message: str)

**Example:**
```python
import numpy as np

# Load audio
audio = np.random.randn(16000).astype(np.float32)  # 1 second at 16kHz

# Verify
result, score, error = await manager.verify(
    session_id,
    audio,
    sample_rate=16000
)

if result == VerificationResult.MATCH:
    print(f"✓ Verified! Score: {score:.4f}")
else:
    print(f"✗ Failed: {error}")
```

**Process:**
1. Validates session is active and not expired
2. Generates embedding from audio using ECAPA-TDNN
3. Retrieves stored embedding from session
4. Calculates cosine similarity
5. Compares against threshold
6. Records attempt with results

#### get_session_summary(session_id) → Optional[Dict]

Get detailed summary of a session.

**Parameters:**
- `session_id` (str): Session identifier

**Returns:** Dictionary with session details or None

**Example:**
```python
summary = manager.get_session_summary(session_id)

if summary:
    print(f"Status: {summary['status']}")
    print(f"Verified: {summary['verified']}")
    print(f"Score: {summary['final_similarity_score']:.4f}")
    print(f"Attempts: {summary['attempts']}/{summary['max_attempts']}")
```

**Response Structure:**
```python
{
    "session_id": "uuid",
    "phone_number": "+1-xxx-xxx-xxxx",
    "status": "verified|rejected|active|expired",
    "verified": True/False,
    "final_similarity_score": 0.85,
    "final_result": "match|mismatch|error",
    "attempts": 2,
    "max_attempts": 3,
    "remaining_attempts": 1,
    "created_at": "2024-01-15T10:30:00",
    "completed_at": "2024-01-15T10:35:00",
    "attempt_details": [
        {
            "attempt_id": "uuid",
            "timestamp": "2024-01-15T10:30:05",
            "similarity_score": 0.82,
            "result": "mismatch",
            "threshold_used": 0.85
        }
    ],
    "error": null
}
```

#### get_verification_history(phone_number, limit=10) → List[Dict]

Get verification history for a phone number.

**Parameters:**
- `phone_number` (str): Phone number to get history for
- `limit` (int, default=10): Maximum records to return

**Returns:** List of verification attempt records

**Example:**
```python
history = manager.get_verification_history("+1-234-567-8900", limit=5)

for record in history:
    print(f"{record['timestamp']}: {record['result']} (score: {record['similarity_score']:.4f})")
```

#### cancel_session(session_id) → bool

Cancel a verification session.

**Parameters:**
- `session_id` (str): Session to cancel

**Returns:** True if cancelled, False if not found

**Example:**
```python
if manager.cancel_session(session_id):
    print("Session cancelled")
else:
    print("Session not found")
```

#### cleanup_expired_sessions() → int

Remove expired sessions from memory.

**Returns:** Number of sessions cleaned up

**Example:**
```python
cleaned = manager.cleanup_expired_sessions()
print(f"Cleaned up {cleaned} expired sessions")
```

#### get_statistics() → Dict

Get verification statistics.

**Returns:** Statistics dictionary

**Example:**
```python
stats = manager.get_statistics()

print(f"Total sessions: {stats['total_sessions']}")
print(f"Verified: {stats['verified_sessions']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Avg similarity: {stats['avg_similarity_score']:.4f}")
```

**Response Structure:**
```python
{
    "total_sessions": 42,
    "completed_sessions": 35,
    "verified_sessions": 32,
    "total_attempts": 58,
    "avg_similarity_score": 0.87,
    "success_rate": 0.914  # 91.4%
}
```

## Database Integration

### MongoDB Collections

The verification service uses the following MongoDB collections:

**1. voice_embeddings**
```json
{
  "_id": ObjectId,
  "phone_number": "+1-234-567-8900",
  "embedding": [0.123, 0.456, ...],  // 192-dimensional array
  "embedding_dimension": 192,
  "created_at": ISODate("2024-01-15T10:00:00Z"),
  "updated_at": ISODate("2024-01-15T10:00:00Z")
}
```

### Retrieval Functions

```python
from database import (
    get_voice_embedding,
    check_enrollment,
    find_nearest_embedding
)

# Get stored embedding for phone number
enrollment = get_voice_embedding("+1-234-567-8900")
if enrollment:
    embedding = np.array(enrollment['embedding'])
    print(f"Embedding shape: {embedding.shape}")

# Check if phone is enrolled
is_enrolled = check_enrollment("+1-234-567-8900")

# Find nearest embedding (for speaker identification)
nearest = find_nearest_embedding(query_embedding, limit=1)
```

## API Integration Examples

### FastAPI Routes

```python
from fastapi import FastAPI, HTTPException, UploadFile, File
from verification_service import get_verification_manager, VerificationResult
import soundfile as sf
import numpy as np

app = FastAPI()
verification_manager = get_verification_manager()

@app.post("/verify/start/{phone_number}")
async def start_verification(phone_number: str):
    """Start a verification session"""
    try:
        session = verification_manager.create_session(phone_number)
        return {
            "session_id": session.session_id,
            "max_attempts": session.config.max_attempts,
            "threshold": session.config.similarity_threshold
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/verify/{session_id}/attempt")
async def verify_attempt(session_id: str, audio: UploadFile = File(...)):
    """Submit verification attempt"""
    session = verification_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Read audio
    audio_bytes = await audio.read()
    audio_data, sr = sf.read(audio_bytes)
    audio_data = audio_data.astype(np.float32)
    
    # Verify
    result, score, error = await verification_manager.verify(
        session_id,
        audio_data,
        sr
    )
    
    return {
        "result": result.value,
        "similarity_score": score,
        "verified": result == VerificationResult.MATCH,
        "remaining_attempts": session.get_remaining_attempts(),
        "error": error
    }

@app.get("/verify/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    summary = verification_manager.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary

@app.get("/verify/{phone_number}/history")
async def get_history(phone_number: str, limit: int = 10):
    """Get verification history"""
    history = verification_manager.get_verification_history(phone_number, limit)
    return {"history": history}

@app.get("/verify/stats")
async def get_stats():
    """Get verification statistics"""
    return verification_manager.get_statistics()
```

## Configuration Guide

### Thresholds by Use Case

**High Security (0.90-0.99)**
```python
config = VerificationSessionConfig(
    similarity_threshold=0.95,
    max_attempts=2
)
# Best for: Banking, government, high-value transactions
```

**Moderate Security (0.80-0.90)**
```python
config = VerificationSessionConfig(
    similarity_threshold=0.85,
    max_attempts=3
)
# Best for: General applications, most use cases
```

**Low Security (0.70-0.80)**
```python
config = VerificationSessionConfig(
    similarity_threshold=0.75,
    max_attempts=5
)
# Best for: Entertainment, non-critical applications
```

## Error Handling

```python
from verification_service import VerificationResult

result, score, error = await manager.verify(session_id, audio_data)

if result == VerificationResult.MATCH:
    print("✓ Verified")
elif result == VerificationResult.MISMATCH:
    print("✗ Voice does not match")
elif result == VerificationResult.NOT_ENROLLED:
    print("✗ Phone number not enrolled")
elif result == VerificationResult.TIMEOUT:
    print("✗ Session timed out")
elif result == VerificationResult.ERROR:
    print(f"✗ Error: {error}")
```

## Performance Considerations

1. **Embedding Generation**: ~200-500ms per verification attempt
2. **Similarity Calculation**: <1ms (cosine similarity)
3. **MongoDB Retrieval**: ~10-50ms (indexed lookup)
4. **Memory Usage**: ~1-2MB per session (includes embeddings)

## Best Practices

1. **Session Management**
   - Create new session per verification attempt
   - Clean up expired sessions regularly
   - Store session ID on client side

2. **Threshold Tuning**
   - Start with 0.85 (default)
   - Adjust based on false positive/negative rates
   - Document threshold choice

3. **Error Handling**
   - Handle all VerificationResult types
   - Log incorrect verifications for analysis
   - Provide user-friendly error messages

4. **Database**
   - Ensure MongoDB indexes on phone_number
   - Backup embeddings collection regularly
   - Monitor collection size growth

## See Also

- [Enrollment Service](./ENROLLMENT_SERVICE_IMPLEMENTATION_SUMMARY.md)
- [Embedding Operations](./EMBEDDING_OPERATIONS_IMPLEMENTATION_SUMMARY.md)
- [Database Guide](./database.py)
- [Voice Embedding](./voice_embedding.py)
