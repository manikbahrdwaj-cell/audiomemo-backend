# MongoDB Enrollment Service - Implementation Guide

## Overview

The MongoDB Enrollment Service provides persistent, database-backed enrollment session management for voice biometric authentication. It extends the in-memory enrollment service with MongoDB storage, enabling session recovery, scalability, and comprehensive tracking of enrollment operations.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│         Voice Biometric Application                      │
│  (FastAPI Backend / WebSocket Server)                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├──── enrollment_service.py (In-memory sessions)
                 │
                 ├──► mongodb_enrollment_service.py (Persistent layer)
                 │
                 └──► database.py (MongoDB operations)
                      │
                      ├── enrollment_sessions (collection)
                      ├── audio_chunks (collection)
                      ├── enrollment_history (collection)
                      └── voice_embeddings (collection - existing)
```

### Collections

#### 1. `enrollment_sessions`
Stores active and completed enrollment sessions.

**Schema:**
```json
{
  "_id": ObjectId,
  "session_id": "uuid-string",
  "phone_number": "+1234567890",
  "status": "active|collecting|processing|completed|error",
  "created_at": "2026-02-14T...",
  "started_at": "2026-02-14T...",
  "completed_at": "2026-02-14T...",
  "chunks_collected": 3,
  "max_chunks": 10,
  "embeddings_generated": 3,
  "merge_embeddings": true,
  "merge_mode": "concatenate",
  "merge_audio": false,
  "audio_merge_mode": "overlap",
  "quality_threshold": 0.7,
  "has_merged_embedding": true,
  "vector_id": "embedding-vector-id",
  "error_message": null,
  "updated_at": "2026-02-14T..."
}
```

**Indexes:**
- `session_id` (unique)
- `phone_number`
- `status`
- `created_at`

#### 2. `audio_chunks`
Stores metadata for audio chunks (audio data itself kept in memory due to size).

**Schema:**
```json
{
  "_id": ObjectId,
  "chunk_id": "uuid-string",
  "session_id": "uuid-string",
  "phone_number": "+1234567890",
  "timestamp": "2026-02-14T...",
  "duration_seconds": 2.5,
  "sample_rate": 16000,
  "audio_samples": 40000,
  "audio_data_size": 160000,
  "quality_score": 0.92,
  "created_at": "2026-02-14T..."
}
```

**Indexes:**
- `session_id`
- `chunk_id` (unique)
- `phone_number`
- `created_at`

#### 3. `enrollment_history`
Audit trail of completed enrollments.

**Schema:**
```json
{
  "_id": ObjectId,
  "session_id": "uuid-string",
  "phone_number": "+1234567890",
  "status": "completed|failed",
  "chunks_collected": 3,
  "embeddings_generated": 3,
  "merge_strategy": "audio_merge|embedding_merge",
  "vector_id": "embedding-vector-id",
  "completed_at": "2026-02-14T...",
  "duration_seconds": 45.3,
  "error_message": null,
  "created_at": "2026-02-14T..."
}
```

**Indexes:**
- `phone_number`
- `session_id`
- `completed_at` (descending)

## Features

### 1. Session Persistence
- Create enrollment sessions that persist to MongoDB
- Automatic session serialization
- Session recovery from database

### 2. Audio Chunk Tracking
- Store chunk metadata (duration, quality, sample count)
- Audio samples kept in memory for performance
- Retrieve chunk history for any session

### 3. Enrollment History
- Complete audit trail of all enrollments
- Track merge strategies used
- Monitor success/failure rates

### 4. Session Queries
- Retrieve sessions by phone number
- Find active sessions
- List all sessions
- Get recent enrollments

### 5. Statistics & Analytics
- Count sessions by status
- Session duration tracking
- Enrollment success rates
- Per-phone-number statistics

## Usage Guide

### Installation & Setup

1. **Prerequisites:**
```bash
pip install pymongo>=4.6.0
```

2. **MongoDB Instance:**
```bash
# Using local MongoDB
mongod --dbpath /path/to/data

# Or use MongoDB Atlas (cloud)
```

3. **Configuration:**
```python
# In database.py
MONGODB_URL = "mongodb://localhost:27017"  # or MongoDB Atlas URL
DATABASE_NAME = "voice_biometric"
```

### API Usage

#### Create Enrollment Session

```python
from mongodb_enrollment_service import create_enrollment_session
from enrollment_service import EnrollmentSessionConfig

# Basic session
session_id, session_data = create_enrollment_session("+1234567890")

# With custom config
config = EnrollmentSessionConfig(
    max_chunks=5,
    min_chunks_required=2,
    merge_audio=True,
    audio_merge_mode=MergeMode.OVERLAP
)
session_id, session_data = create_enrollment_session("+1234567890", config)
```

#### Add Audio Chunk

```python
from mongodb_enrollment_service import add_audio_chunk
import numpy as np

# Generate or load audio
audio_data = np.random.randn(16000).astype(np.float32)  # 1 second at 16kHz

success, message, chunk_id = add_audio_chunk(
    session_id=session_id,
    audio_data=audio_data,
    duration_seconds=1.0,
    sample_rate=16000,
    quality_score=0.95
)

if success:
    print(f"Chunk added: {chunk_id}")
```

#### Get Session Summary

```python
from mongodb_enrollment_service import get_session_summary

summary = get_session_summary(session_id)

print(f"Status: {summary['status']}")
print(f"Chunks: {summary['chunks_collected']}")
print(f"Embeddings: {summary['embeddings_generated']}")
print(f"Duration: {summary['chunk_stats']['total_duration_seconds']}s")
```

#### Finalize Enrollment

```python
from mongodb_enrollment_service import finalize_enrollment

success, message, vector_id = finalize_enrollment(session_id)

if success:
    print(f"Enrollment complete! Vector ID: {vector_id}")
else:
    print(f"Enrollment failed: {message}")
```

#### Get Enrollment History

```python
from mongodb_enrollment_service import get_enrollment_history

history = get_enrollment_history("+1234567890", limit=10)

for record in history:
    print(f"  Session: {record['session_id']}")
    print(f"  Status: {record['status']}")
    print(f"  Chunks: {record['chunks_collected']}")
    print(f"  Date: {record['completed_at']}")
```

#### Get Statistics

```python
from mongodb_enrollment_service import get_enrollment_statistics

# Overall stats
stats = get_enrollment_statistics()
print(f"Total sessions: {stats['total_sessions']}")
print(f"Total completions: {stats['total_completions']}")

# Phone-specific stats
phone_stats = get_enrollment_statistics("+1234567890")
print(f"Phone sessions: {phone_stats['total_sessions']}")
```

### FastAPI Integration Example

```python
from fastapi import FastAPI, HTTPException
from mongodb_enrollment_service import (
    create_enrollment_session,
    add_audio_chunk,
    finalize_enrollment,
    get_session_summary
)

app = FastAPI()

@app.post("/enrollment/start")
async def start_enrollment(phone_number: str):
    """Start a new enrollment session"""
    session_id, session_data = create_enrollment_session(phone_number)
    return {
        "session_id": session_id,
        "status": session_data["status"]
    }

@app.post("/enrollment/{session_id}/chunk")
async def add_chunk(session_id: str, file: UploadFile = File(...)):
    """Add audio chunk to session"""
    audio_data = await file.read()
    
    success, message, chunk_id = add_audio_chunk(
        session_id=session_id,
        audio_data=np.frombuffer(audio_data, dtype=np.float32),
        duration_seconds=2.0  # Calculate from file
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"chunk_id": chunk_id, "message": message}

@app.post("/enrollment/{session_id}/finalize")
async def finalize(session_id: str):
    """Finalize enrollment"""
    success, message, vector_id = finalize_enrollment(session_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "vector_id": vector_id,
        "message": message
    }

@app.get("/enrollment/{session_id}/summary")
async def get_summary(session_id: str):
    """Get session summary"""
    summary = get_session_summary(session_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return summary
```

## Configuration Options

### EnrollmentSessionConfig

```python
class EnrollmentSessionConfig:
    max_chunks: int = 10                          # Maximum chunks per session
    chunk_timeout_seconds: int = 30              # Max time per chunk
    session_timeout_seconds: int = 300           # Max session duration
    min_chunks_required: int = 1                 # Minimum for completion
    auto_process: bool = True                    # Auto-generate embeddings
    merge_embeddings: bool = True                # Merge embeddings
    merge_mode: MergeMode = CONCATENATE          # Embedding merge strategy
    store_chunks: bool = True                    # Store raw chunks
    quality_threshold: float = 0.7               # Min quality score
    merge_audio: bool = False                    # Merge audio chunks first
    audio_merge_mode: MergeMode = OVERLAP        # Audio merge strategy
    audio_merge_crossfade_ms: float = 100.0      # Crossfade duration
    auto_merge_threshold: int = 2                # Min chunks for auto-merge
```

## Merge Strategies

### Embedding Merge (Default)
1. Generate embedding for each audio chunk
2. Average embeddings
3. Normalize result

**When to use:** Fast processing, lower memory usage

### Audio Merge
1. Merge audio chunks into single audio file
2. Generate single embedding from merged audio
3. More natural audio representation

**When to use:** Higher quality requirements, longer audio context needed

## Performance Considerations

### Memory Management
- Audio data kept in Python memory during session
- Only metadata stored in MongoDB
- Automatic cleanup of expired sessions

### Database Optimization
- Indexes on frequently queried fields
- Time-based indexes for cleanup operations
- Compound indexes for multi-field queries

### Scalability
- Session IDs are UUIDs (no server state dependency)
- Stateless operations (can run multiple instances)
- MongoDB Atlas Vector Search compatible

## Testing

### Run Test Suite
```bash
cd backend
python test_mongodb_enrollment_service.py
```

### Test Coverage
- Session creation and persistence
- Audio chunk operations
- Enrollment finalization
- History tracking
- Statistics generation
- Multiple phone numbers
- Merge strategies

## Troubleshooting

### MongoDB Connection Issues
```python
from database import get_database

# Test connection
try:
    db = get_database()
    print("✓ MongoDB connected")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Session Not Found
```python
# Verify session exists
from database import get_enrollment_session

session = get_enrollment_session(session_id)
if not session:
    print(f"Session {session_id} not found in database")
```

### Cleanup Expired Sessions
```python
from database import cleanup_expired_enrollment_sessions

count = cleanup_expired_enrollment_sessions(max_age_seconds=3600)
print(f"Cleaned up {count} sessions")
```

## Migration from In-Memory

To migrate existing in-memory sessions to MongoDB:

```python
from enrollment_service import get_enrollment_manager
from mongodb_enrollment_service import get_mongodb_enrollment_service

# Get existing in-memory manager
memory_manager = get_enrollment_manager()

# Get MongoDB service
mongo_service = get_mongodb_enrollment_service()

# Migrate sessions
for session_id, session in memory_manager.sessions.items():
    session_data = mongo_service._serialize_session(session)
    save_enrollment_session(session_data)
    print(f"✓ Migrated session {session_id[:8]}")
```

## Best Practices

1. **Session Cleanup:** Regularly clean up expired sessions
   ```python
   cleanup_expired_enrollment_sessions(max_age_seconds=3600)
   ```

2. **Monitor Statistics:** Track enrollment success rates
   ```python
   stats = get_enrollment_statistics()
   print(f"Success rate: {stats['total_completions'] / stats['total_sessions']}")
   ```

3. **Error Handling:** Always check operation results
   ```python
   success, message, result = add_audio_chunk(...)
   if not success:
       logger.error(f"Chunk addition failed: {message}")
   ```

4. **Backup MongoDB:** Regularly backup enrollment data
   ```bash
   mongodump --uri "mongodb://localhost:27017" --out /backup/path
   ```

5. **Load Testing:** Monitor performance with multiple concurrent sessions
   ```bash
   python test_mongodb_enrollment_service.py
   ```

## API Reference

### Collection: enrollment_sessions

| Method | Description |
|--------|-------------|
| `save_enrollment_session(data)` | Create/update session |
| `get_enrollment_session(session_id)` | Retrieve session |
| `update_enrollment_session(session_id, updates)` | Update specific fields |
| `delete_enrollment_session(session_id)` | Remove session |
| `get_enrollment_sessions_for_phone(phone)` | Get all for phone number |
| `get_active_enrollment_sessions(phone)` | Get active sessions |
| `cleanup_expired_enrollment_sessions(max_age)` | Remove old sessions |

### Collection: audio_chunks

| Method | Description |
|--------|-------------|
| `save_audio_chunk(data)` | Store chunk metadata |
| `get_audio_chunks_for_session(session_id)` | Retrieve all chunks |

### Collection: enrollment_history

| Method | Description |
|--------|-------------|
| `save_enrollment_history(data)` | Record enrollment completion |
| `get_enrollment_history_for_phone(phone)` | Get completion history |
| `get_recent_enrollments(limit)` | Recent completions |
| `get_enrollment_stats(phone)` | Statistics |

## Support & Documentation

- See `MONGODB_ENROLLMENT_SERVICE_REFERENCE.md` for complete API reference
- See `README.md` for general project setup
- See individual test files for usage examples
