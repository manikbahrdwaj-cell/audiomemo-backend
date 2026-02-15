# MongoDB Enrollment Service - Quick Reference

## Quick Start

### 1. Import Service
```python
from mongodb_enrollment_service import (
    create_enrollment_session,
    add_audio_chunk,
    finalize_enrollment,
    get_enrollment_history,
    get_enrollment_statistics
)
```

### 2. Start Enrollment
```python
phone_number = "+1234567890"
session_id, session_data = create_enrollment_session(phone_number)
# Returns: (session_id, session_data_dict)
```

### 3. Add Audio Chunks
```python
import numpy as np

# Load or generate audio
audio = np.random.randn(16000).astype(np.float32)  # 1 second

success, message, chunk_id = add_audio_chunk(
    session_id=session_id,
    audio_data=audio,
    duration_seconds=1.0,
    sample_rate=16000,
    quality_score=0.95
)

if success:
    print(f"✓ Chunk added: {chunk_id}")
else:
    print(f"✗ Error: {message}")
```

### 4. Finalize & Store
```python
success, message, vector_id = finalize_enrollment(session_id)

if success:
    print(f"✓ Enrolled! Vector: {vector_id}")
else:
    print(f"✗ Failed: {message}")
```

## Common Tasks

### Get Session Status
```python
from mongodb_enrollment_service import get_session_summary

summary = get_session_summary(session_id)
print(f"Status: {summary['status']}")
print(f"Chunks: {summary['chunks_collected']}/{summary['max_chunks']}")
print(f"Duration: {summary['chunk_stats']['total_duration_seconds']:.1f}s")
```

### View Enrollment History
```python
from mongodb_enrollment_service import get_enrollment_history, get_recent_completions

# For specific person
history = get_enrollment_history("+1234567890")
for rec in history:
    print(f"  {rec['completed_at']}: {rec['chunks_collected']} chunks → {rec['status']}")

# Recent enrollments (any number)
recent = get_recent_completions(limit=5)
for rec in recent[:3]:
    print(f"  {rec['phone_number']}: {rec['chunks_collected']} chunks")
```

### Check Enrollment Status
```python
from database import check_enrollment, get_voice_embedding

if check_enrollment("+1234567890"):
    print("✓ Person is enrolled")
    embedding_doc = get_voice_embedding("+1234567890")
    print(f"  Vector ID: {embedding_doc['_id']}")
else:
    print("✗ Not enrolled yet")
```

### View Statistics
```python
from mongodb_enrollment_service import get_enrollment_statistics

stats = get_enrollment_statistics()
print(f"Total sessions: {stats['total_sessions']}")
print(f"Total completions: {stats['total_completions']}")

for status, count in stats['by_status'].items():
    if count > 0:
        print(f"  {status}: {count}")
```

## Data Schema

### Enrollment Session
```
{
  session_id: "UUID",
  phone_number: "+1234567890",
  status: "initializing|active|collecting|processing|completed|error",
  chunks_collected: 3,
  max_chunks: 10,
  embeddings_generated: 3,
  created_at: "2026-02-14T12:30:45",
  completed_at: "2026-02-14T12:31:30",
  error_message: null or "error description"
}
```

### Audio Chunk
```
{
  chunk_id: "UUID",
  session_id: "UUID",
  phone_number: "+1234567890",
  duration_seconds: 2.5,
  sample_rate: 16000,
  audio_samples: 40000,
  quality_score: 0.92,
  timestamp: "2026-02-14T12:30:50"
}
```

### Enrollment History
```
{
  session_id: "UUID",
  phone_number: "+1234567890",
  status: "completed",
  chunks_collected: 3,
  vector_id: "ObjectId",
  merge_strategy: "embedding_merge",
  duration_seconds: 45.3,
  completed_at: "2026-02-14T12:31:30"
}
```

## Configuration Presets

### Minimal (1 chunk)
```python
from enrollment_service import EnrollmentSessionConfig

config = EnrollmentSessionConfig(
    max_chunks=1,
    min_chunks_required=1,
    merge_embeddings=False,
    merge_audio=False
)
session_id, _ = create_enrollment_session(phone, config)
```

### Optimal (3 chunks with merge)
```python
config = EnrollmentSessionConfig(
    max_chunks=3,
    min_chunks_required=2,
    merge_embeddings=True,
    merge_audio=False
)
session_id, _ = create_enrollment_session(phone, config)
```

### Premium (5 chunks with audio merge)
```python
from enrollment_service import MergeMode

config = EnrollmentSessionConfig(
    max_chunks=5,
    min_chunks_required=3,
    merge_audio=True,
    audio_merge_mode=MergeMode.OVERLAP,
    audio_merge_crossfade_ms=100.0
)
session_id, _ = create_enrollment_session(phone, config)
```

## Error Handling

```python
try:
    success, message, chunk_id = add_audio_chunk(
        session_id, audio, 1.0, 16000, 0.9
    )
    
    if not success:
        # Handle specific error
        if "not found" in message.lower():
            print("Session expired")
        elif "max chunks" in message.lower():
            print("Session full - finalize to complete")
        else:
            print(f"Error: {message}")
            
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Monitoring Queries

### Get Active Sessions
```python
from database import get_active_enrollment_sessions

active = get_active_enrollment_sessions()
print(f"Active sessions: {len(active)}")

# For specific person
phone_active = get_active_enrollment_sessions(phone_number)
print(f"Active for {phone_number}: {len(phone_active)}")
```

### Get Session Details with Chunks
```python
from database import get_enrollment_sessions_for_phone, get_audio_chunks_for_session

sessions = get_enrollment_sessions_for_phone(phone_number)
for sess in sessions:
    chunks = get_audio_chunks_for_session(sess['session_id'])
    print(f"Session {sess['session_id'][:8]}: {len(chunks)} chunks, status={sess['status']}")
    total_dur = sum(c['duration_seconds'] for c in chunks)
    print(f"  Total duration: {total_dur:.1f}s")
```

### Cleanup Expired
```python
from database import cleanup_expired_enrollment_sessions

# Delete sessions older than 1 hour
count = cleanup_expired_enrollment_sessions(max_age_seconds=3600)
print(f"Cleaned up {count} expired sessions")
```

## FastAPI Endpoints (Example)

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from mongodb_enrollment_service import *

app = FastAPI()

@app.post("/enroll/start/{phone}")
def start(phone: str):
    session_id, data = create_enrollment_session(phone)
    return {"session_id": session_id, "status": data["status"]}

@app.post("/enroll/{session_id}/chunk")
async def add_chunk(session_id: str, file: UploadFile):
    audio = await file.read()
    audio_np = np.frombuffer(audio, dtype=np.float32)
    success, msg, chunk_id = add_audio_chunk(
        session_id, audio_np, len(audio_np)/16000
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"chunk_id": chunk_id}

@app.post("/enroll/{session_id}/complete")
def complete(session_id: str):
    success, msg, vector_id = finalize_enrollment(session_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"vector_id": vector_id}

@app.get("/enroll/{phone}/history")
def history(phone: str):
    return get_enrollment_history(phone)

@app.get("/stats")
def stats():
    return get_enrollment_statistics()
```

## Testing

```bash
# Run full test suite
python test_mongodb_enrollment_service.py

# Test specific functionality
python -c "
from mongodb_enrollment_service import create_enrollment_session
session_id, _ = create_enrollment_session('+1234567890')
print(f'✓ Session created: {session_id[:8]}')
"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Session not found" | Session expired or incorrect session_id |
| "Max chunks reached" | Finalize enrollment or create new session |
| MongoDB connection error | Check MONGODB_URL in database.py |
| Audio chunk too large | Reduce sample rate or duration |
| Embedding generation failed | Check audio quality, format, content |

## Database Commands (MongoDB CLI)

```javascript
// View sessions
db.enrollment_sessions.find()

// View chunks for session
db.audio_chunks.find({"session_id": "session-uuid"})

// Get completion rate
db.enrollment_history.countDocuments({status: "completed"})

// Get recent completions
db.enrollment_history.find().sort({"completed_at": -1}).limit(10)

// Delete old sessions (older than 24 hours)
db.enrollment_sessions.deleteMany({
  "created_at": {$lt: new Date(Date.now() - 24*60*60*1000)}
})

// Get stats by status
db.enrollment_sessions.aggregate([
  {$group: {_id: "$status", count: {$sum: 1}}}
])
```

## Performance Tips

1. **Batch Operations:** Process multiple chunks before finalizing
2. **Cleanup:** Regularly remove expired sessions
3. **Indexing:** All important fields already indexed
4. **Concurrency:** Service handles multiple sessions safely
5. **Memory:** Audio kept in memory during session lifetime

## Next Steps

- See `MONGODB_ENROLLMENT_SERVICE_IMPLEMENTATION.md` for complete guide
- See `test_mongodb_enrollment_service.py` for code examples
- Check `database.py` for lower-level operations
- Review `enrollment_service.py` for session configuration
