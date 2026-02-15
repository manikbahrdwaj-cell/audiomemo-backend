# MongoDB Enrollment Service - API Reference

## Core Service Methods

### `MongoDBEnrollmentService` Class

#### `create_session(phone_number: str, config: Optional[EnrollmentSessionConfig]) → Tuple[str, Dict[str, Any]]`

Creates and persists a new enrollment session.

**Parameters:**
- `phone_number` (str): Phone number for enrollment (e.g., "+1234567890")
- `config` (Optional[EnrollmentSessionConfig]): Session configuration. If None, uses defaults.

**Returns:**
- Tuple of:
  - `session_id` (str): UUID of the created session
  - `session_data` (Dict): Session details dictionary

**Example:**
```python
from mongodb_enrollment_service import create_enrollment_session

session_id, session_data = create_enrollment_session("+1234567890")
print(f"Session created: {session_id}")
print(f"Status: {session_data['status']}")  # 'active'
```

**Exceptions:**
- Raises exception if phone_number is invalid format

---

#### `add_audio_chunk(session_id: str, audio_data: np.ndarray, duration_seconds: float, sample_rate: int = 16000, quality_score: float = 1.0) → Tuple[bool, str, Optional[str]]`

Adds an audio chunk to an enrollment session.

**Parameters:**
- `session_id` (str): UUID of the enrollment session
- `audio_data` (np.ndarray): Audio samples as numpy float32 array
- `duration_seconds` (float): Duration of audio in seconds
- `sample_rate` (int, default=16000): Sample rate in Hz
- `quality_score` (float, default=1.0): Quality confidence score (0.0-1.0)

**Returns:**
- Tuple of:
  - `success` (bool): True if chunk was added successfully
  - `message` (str): Status or error message
  - `chunk_id` (Optional[str]): UUID of the chunk if successful, None if failed

**Example:**
```python
import numpy as np
from mongodb_enrollment_service import add_audio_chunk

audio = np.random.randn(16000).astype(np.float32)
success, message, chunk_id = add_audio_chunk(
    session_id=session_id,
    audio_data=audio,
    duration_seconds=1.0,
    sample_rate=16000,
    quality_score=0.95
)

if success:
    print(f"Chunk {chunk_id} added")
else:
    print(f"Error: {message}")
```

**Exceptions:**
- Returns `(False, error_message, None)` if session not found
- Returns `(False, error_message, None)` if session is full
- Returns `(False, error_message, None)` if quality score below threshold

---

#### `finalize_enrollment(session_id: str, force_single: bool = False) → Tuple[bool, str, Optional[str]]`

Finalizes enrollment and stores the embedding.

**Parameters:**
- `session_id` (str): UUID of the enrollment session
- `force_single` (bool, default=False): If True, uses single best embedding if merge fails

**Returns:**
- Tuple of:
  - `success` (bool): True if enrollment completed successfully
  - `message` (str): Status or error message
  - `vector_id` (Optional[str]): ObjectId of stored embedding if successful

**Example:**
```python
from mongodb_enrollment_service import finalize_enrollment

success, message, vector_id = finalize_enrollment(session_id)

if success:
    print(f"Enrollment complete!")
    print(f"Vector stored with ID: {vector_id}")
else:
    print(f"Enrollment failed: {message}")
```

**Exceptions:**
- Returns `(False, error_message, None)` if session not found
- Returns `(False, error_message, None)` if insufficient chunks
- Returns `(False, error_message, None)` if no valid embeddings

---

#### `get_session_summary(session_id: str) → Optional[Dict[str, Any]]`

Retrieves comprehensive session summary with chunk details.

**Parameters:**
- `session_id` (str): UUID of the enrollment session

**Returns:**
- Dictionary with:
  - All session fields (session_id, phone_number, status, etc.)
  - `chunks` (List): Audio chunk metadata for session
  - `chunk_stats` (Dict): Aggregated chunk statistics
    - `total_saved` (int): Number of chunks in database
    - `total_samples` (int): Total audio samples
    - `total_duration_seconds` (float): Total audio duration
- None if session not found

**Example:**
```python
from mongodb_enrollment_service import get_session_summary

summary = get_session_summary(session_id)

if summary:
    print(f"Session: {summary['session_id'][:8]}")
    print(f"Phone: {summary['phone_number']}")
    print(f"Status: {summary['status']}")
    print(f"Chunks: {summary['chunks_collected']}/{summary['max_chunks']}")
    print(f"Duration: {summary['chunk_stats']['total_duration_seconds']:.1f}s")
    
    for chunk in summary['chunks']:
        print(f"  Chunk: {chunk['chunk_id'][:8]} - {chunk['duration_seconds']:.1f}s")
else:
    print("Session not found")
```

---

#### `get_sessions_for_phone(phone_number: str, limit: int = 10, include_chunks: bool = False) → List[Dict[str, Any]]`

Retrieves all sessions for a phone number.

**Parameters:**
- `phone_number` (str): Phone number to search
- `limit` (int, default=10): Maximum sessions to return
- `include_chunks` (bool, default=False): Whether to include chunk details

**Returns:**
- List of session dictionaries, sorted by creation date (newest first)

**Example:**
```python
from mongodb_enrollment_service import get_sessions_for_phone

sessions = get_sessions_for_phone("+1234567890", limit=5, include_chunks=True)

for session in sessions:
    print(f"Session: {session['session_id'][:8]}")
    print(f"  Status: {session['status']}")
    print(f"  Chunks: {session['chunks_collected']}")
    
    if 'chunks' in session:
        for chunk in session['chunks']:
            print(f"    - {chunk['duration_seconds']:.1f}s @ {chunk['quality_score']:.2f}")
```

---

#### `get_active_sessions(phone_number: Optional[str] = None) → List[Dict[str, Any]]`

Retrieves active (in-progress) enrollment sessions.

**Parameters:**
- `phone_number` (Optional[str]): Filter by phone number. If None, returns all active sessions.

**Returns:**
- List of active session dictionaries

**Example:**
```python
from mongodb_enrollment_service import get_active_sessions

# All active sessions
all_active = get_active_sessions()
print(f"Active sessions: {len(all_active)}")

# Active for specific person
phone_active = get_active_sessions("+1234567890")
if phone_active:
    print(f"Person has {len(phone_active)} active sessions")
```

---

#### `get_enrollment_history(phone_number: str, limit: int = 10) → List[Dict[str, Any]]`

Retrieves enrollment history for a phone number.

**Parameters:**
- `phone_number` (str): Phone number to search
- `limit` (int, default=10): Maximum records to return

**Returns:**
- List of enrollment history records, sorted by completion date (newest first)

**Record structure:**
```python
{
    "session_id": "uuid-string",
    "phone_number": "+1234567890",
    "status": "completed",
    "chunks_collected": 3,
    "embeddings_generated": 3,
    "merge_strategy": "embedding_merge",
    "vector_id": "embedding-object-id",
    "completed_at": "2026-02-14T12:31:30",
    "duration_seconds": 45.3,
    "error_message": None,
    "_id": "history-object-id"
}
```

**Example:**
```python
from mongodb_enrollment_service import get_enrollment_history

history = get_enrollment_history("+1234567890", limit=10)

print(f"Enrollment history ({len(history)} records):")
for record in history:
    status_symbol = "✓" if record["status"] == "completed" else "✗"
    print(f"  {status_symbol} {record['completed_at'][:10]}: {record['chunks_collected']} chunks")
    if record["error_message"]:
        print(f"     Error: {record['error_message']}")
```

---

#### `get_recent_enrollments(limit: int = 20) → List[Dict[str, Any]]`

Retrieves recent enrollment completions across all users.

**Parameters:**
- `limit` (int, default=20): Maximum records to return

**Returns:**
- List of enrollment history records for completed enrollments

**Example:**
```python
from mongodb_enrollment_service import get_recent_enrollments

recent = get_recent_enrollments(limit=10)

print("Recent enrollments:")
for enrollment in recent:
    print(f"  {enrollment['phone_number']}: {enrollment['chunks_collected']} chunks")
    print(f"    Duration: {enrollment['duration_seconds']:.1f}s")
    print(f"    Vector: {enrollment['vector_id'][:8]}")
```

---

#### `get_stats(phone_number: Optional[str] = None) → Dict[str, Any]`

Retrieves enrollment statistics.

**Parameters:**
- `phone_number` (Optional[str]): If provided, returns stats for that phone number only

**Returns:**
```python
{
    "total_sessions": 5,           # Total enrollment sessions
    "by_status": {                 # Sessions by status
        "initializing": 0,
        "active": 0,
        "collecting": 1,
        "processing": 0,
        "completed": 4,
        "error": 0,
        "cancelled": 0
    },
    "total_completions": 4,        # Successfully completed enrollments
    "filtered_by_phone": False     # Whether filtered by phone_number
}
```

**Example:**
```python
from mongodb_enrollment_service import get_enrollment_statistics

# Overall stats
overall = get_enrollment_statistics()
print(f"Total sessions: {overall['total_sessions']}")
print(f"Total completions: {overall['total_completions']}")
if overall['total_sessions'] > 0:
    success_rate = overall['total_completions'] / overall['total_sessions']
    print(f"Success rate: {success_rate * 100:.1f}%")

# Phone-specific stats
phone_stats = get_enrollment_statistics("+1234567890")
print(f"\nPhone {'+1234567890'}:")
print(f"  Sessions: {phone_stats['total_sessions']}")
print(f"  Completions: {phone_stats['total_completions']}")
```

---

#### `cleanup_expired_sessions(max_age_seconds: int = 3600) → int`

Removes expired enrollment sessions from database.

**Parameters:**
- `max_age_seconds` (int, default=3600): Sessions older than this are deleted

**Returns:**
- Number of sessions deleted

**Example:**
```python
from mongodb_enrollment_service import get_mongodb_enrollment_service

service = get_mongodb_enrollment_service()

# Clean sessions older than 1 hour
count = service.cleanup_expired_sessions(max_age_seconds=3600)
print(f"Cleaned up {count} expired sessions")

# Clean sessions older than 24 hours
count = service.cleanup_expired_sessions(max_age_seconds=86400)
print(f"Cleaned up {count} old sessions")
```

---

#### `delete_session(session_id: str) → bool`

Deletes an enrollment session.

**Parameters:**
- `session_id` (str): UUID of session to delete

**Returns:**
- True if deleted, False if not found

**Example:**
```python
from mongodb_enrollment_service import get_mongodb_enrollment_service

service = get_mongodb_enrollment_service()

if service.delete_session(session_id):
    print("Session deleted")
else:
    print("Session not found")
```

---

## Module-Level Functions

These are convenience functions that use the global service instance.

```python
# All return same as above

create_enrollment_session(phone_number, config)
get_session_summary(session_id)
add_audio_chunk(session_id, audio_data, duration_seconds, sample_rate, quality_score)
finalize_enrollment(session_id, force_single)
get_enrollment_history(phone_number, limit)
get_recent_completions(limit)
get_enrollment_statistics(phone_number)
```

---

## Database Functions

Located in `database.py`, these provide lower-level access.

### Enrollment Sessions

```python
from database import (
    save_enrollment_session,
    get_enrollment_session,
    update_enrollment_session,
    delete_enrollment_session,
    get_enrollment_sessions_for_phone,
    get_active_enrollment_sessions,
    cleanup_expired_enrollment_sessions
)

# Save session data
doc_id = save_enrollment_session(session_data_dict)

# Retrieve
session = get_enrollment_session(session_id)

# Update fields
success = update_enrollment_session(session_id, {"status": "completed"})

# Delete
success = delete_enrollment_session(session_id)

# Query
sessions = get_enrollment_sessions_for_phone(phone_number)
active = get_active_enrollment_sessions(phone_number)
count = cleanup_expired_enrollment_sessions(max_age_seconds=3600)
```

### Audio Chunks

```python
from database import save_audio_chunk, get_audio_chunks_for_session

# Save chunk metadata
doc_id = save_audio_chunk(chunk_data_dict)

# Retrieve all chunks for session
chunks = get_audio_chunks_for_session(session_id)
```

### Enrollment History

```python
from database import (
    save_enrollment_history,
    get_enrollment_history_for_phone,
    get_recent_enrollments,
    get_enrollment_stats
)

# Save completion record
doc_id = save_enrollment_history(history_data_dict)

# Query
history = get_enrollment_history_for_phone(phone_number)
recent = get_recent_enrollments(limit)
stats = get_enrollment_stats(phone_number)
```

---

## Data Models

### EnrollmentSessionConfig

```python
from enrollment_service import EnrollmentSessionConfig, MergeMode

config = EnrollmentSessionConfig(
    max_chunks: int = 10,                      # Maximum chunks per session
    chunk_timeout_seconds: int = 30,          # Max wait per chunk
    session_timeout_seconds: int = 300,       # Max total session time
    min_chunks_required: int = 1,             # Minimum to finalize
    auto_process: bool = True,                # Generate embeddings
    merge_embeddings: bool = True,            # Merge embeddings
    merge_mode: MergeMode = CONCATENATE,      # Embedding merge strategy
    store_chunks: bool = True,                # Store raw audio
    quality_threshold: float = 0.7,           # Min quality
    merge_audio: bool = False,                # Merge audio first
    audio_merge_mode: MergeMode = OVERLAP,    # Audio merge strategy
    audio_merge_crossfade_ms: float = 100.0,  # Crossfade duration
    auto_merge_threshold: int = 2             # Min chunks for auto-merge
)
```

### MergeMode Enum

```python
from embedding_operations import MergeMode

class MergeMode(Enum):
    CONCATENATE = "concatenate"  # Average embeddings
    OVERLAP = "overlap"          # Weighted average (time-weighted)
    MIX = "mix"                  # Simple mix
```

---

## Error Codes & Messages

| Situation | Return Value |
|-----------|--------------|
| Session not found | `(False, "Session {id} not found", None)` |
| Max chunks reached | `(False, "Session has reached max chunks limit ({n})", None)` |
| Insufficient chunks | `(False, "Insufficient chunks. Need {n}, got {m}", None)` |
| Quality too low | `(False, "Audio quality score {x} below threshold {y}", None)` |
| No embeddings | `(False, "No valid embeddings generated", None)` |
| Merge failed | `(False, "Failed to merge embeddings", None)` |
| Database error | `(False, "Failed to store embedding: {error}", None)` |

---

## Best Practices

### Input Validation
```python
# Always check audio format
assert isinstance(audio, np.ndarray), "Audio must be numpy array"
assert audio.dtype == np.float32, "Audio must be float32"
assert 0 < duration <= 60, "Duration must be 0-60 seconds"
assert 0 <= quality_score <= 1, "Quality score 0-1"
```

### Error Handling
```python
success, message, result = operation(session_id)
if not success:
    logger.error(f"Operation failed: {message}")
    # Handle error appropriately
    if "not found" in message:
        # Session expired
    elif "max chunks" in message:
        # Session full
    else:
        # Generic error
```

### Resource Cleanup
```python
# Always cleanup expired sessions periodically
from scheduling_library import schedule

schedule.every(1).hours.do(service.cleanup_expired_sessions)
```

### Monitoring
```python
# Track statistics regularly
stats = get_enrollment_statistics()
if stats['total_sessions'] > 0:
    success_rate = stats['total_completions'] / stats['total_sessions']
    # Alert if success_rate < threshold
```

---

## See Also

- `MONGODB_ENROLLMENT_SERVICE_IMPLEMENTATION.md` - Full implementation guide
- `MONGODB_ENROLLMENT_SERVICE_QUICK_REFERENCE.md` - Quick start guide
- `test_mongodb_enrollment_service.py` - Code examples and tests
- `database.py` - Low-level MongoDB operations
- `enrollment_service.py` - Core session management
