# MongoDB Enrollment Service - Getting Started

## 📋 What You Get

The MongoDB Enrollment Service provides:

✓ **Persistent session storage** - Enrollment sessions survive server restarts  
✓ **Audio chunk tracking** - Complete history of all audio submissions  
✓ **Enrollment history** - Audit trail for compliance  
✓ **Real-time statistics** - Monitor enrollment success rates  
✓ **Session recovery** - Resume interrupted enrollments  
✓ **Dual merge strategies** - Audio merge or embedding merge

## 🚀 Quick Start (5 Minutes)

### 1. Prerequisites

```bash
# Install MongoDB (if not already installed)
# Option A: Local
brew install mongodb-community  # macOS
apt-get install mongodb        # Ubuntu/Debian
choco install mongodb          # Windows

# Option B: Docker
docker run -d -p 27017:27017 mongo:latest

# Start MongoDB
mongod --dbpath /path/to/data
```

### 2. Start Enrollment

```python
from mongodb_enrollment_service import create_enrollment_session, add_audio_chunk, finalize_enrollment
import numpy as np

# Step 1: Create session
session_id, session_data = create_enrollment_session("+1234567890")
print(f"✓ Session: {session_id}")

# Step 2: Add audio chunks
for i in range(3):
    audio = np.random.randn(16000).astype(np.float32)  # 1 second of audio
    success, msg, chunk_id = add_audio_chunk(
        session_id, audio, 1.0, 16000, 0.95
    )
    print(f"✓ Chunk {i+1}: {chunk_id}")

# Step 3: Finalize
success, msg, vector_id = finalize_enrollment(session_id)
print(f"✓ Enrolled! Vector: {vector_id}")
```

## 📁 Files Overview

### Core Files

| File | Purpose |
|------|---------|
| `mongodb_enrollment_service.py` | Main service class & functions |
| `database.py` | MongoDB low-level operations |
| `enrollment_service.py` | Session management (in-memory base) |

### Documentation

| File | Purpose |
|------|---------|
| `GETTING_STARTED_MONGODB_ENROLLMENT.md` | **This file** - Quick intro |
| `MONGODB_ENROLLMENT_SERVICE_INDEX.md` | Complete feature index |
| `MONGODB_ENROLLMENT_SERVICE_QUICK_REFERENCE.md` | Common tasks & commands |
| `MONGODB_ENROLLMENT_SERVICE_IMPLEMENTATION.md` | Detailed guide |
| `MONGODB_ENROLLMENT_SERVICE_API_REFERENCE.md` | Complete API docs |

### Testing

| File | Purpose |
|------|---------|
| `test_mongodb_enrollment_service.py` | Full test suite |

## 🔧 Common Use Cases

### Use Case 1: Simple Enrollment (1 chunk)

```python
from mongodb_enrollment_service import create_enrollment_session, add_audio_chunk, finalize_enrollment
from enrollment_service import EnrollmentSessionConfig

# Create session (minimal config)
config = EnrollmentSessionConfig(max_chunks=1, min_chunks_required=1)
session_id, _ = create_enrollment_session("+1234567890", config)

# Add one chunk
audio = load_audio_file("user_voice.wav")
add_audio_chunk(session_id, audio, duration=2.0)

# Complete
success, msg, vector_id = finalize_enrollment(session_id)
```

### Use Case 2: Multi-Chunk Enrollment (Best Practice)

```python
from mongodb_enrollment_service import create_enrollment_session, add_audio_chunk, finalize_enrollment
from enrollment_service import EnrollmentSessionConfig

# Create session (optimal config)
config = EnrollmentSessionConfig(
    max_chunks=3,
    min_chunks_required=2,
    merge_embeddings=True  # Average the embeddings
)
session_id, _ = create_enrollment_session("+1234567890", config)

# Collect 3 samples
for i in range(3):
    print(f"Please say your phrase (sample {i+1})")
    audio = record_audio(duration=2.5)  # Your recording function
    add_audio_chunk(session_id, audio, 2.5)

# Finalize
success, msg, vector_id = finalize_enrollment(session_id)
```

### Use Case 3: High-Quality Enrollment (Audio Merge)

```python
from mongodb_enrollment_service import create_enrollment_session, add_audio_chunk, finalize_enrollment
from enrollment_service import EnrollmentSessionConfig, MergeMode

# Create session (premium config)
config = EnrollmentSessionConfig(
    max_chunks=5,
    min_chunks_required=3,
    merge_audio=True,  # Merge audio first, then embed
    audio_merge_mode=MergeMode.OVERLAP,
    audio_merge_crossfade_ms=100.0
)
session_id, _ = create_enrollment_session("+1234567890", config)

# Collect samples
for i in range(3):
    audio = record_audio(2.0)
    add_audio_chunk(session_id, audio, 2.0)

# Finalize (will merge audio, generate single embedding)
success, msg, vector_id = finalize_enrollment(session_id)
```

### Use Case 4: Check Enrollment Status

```python
from mongodb_enrollment_service import get_session_summary, get_enrollment_history
from database import check_enrollment, get_voice_embedding

# Check if enrolled
if check_enrollment("+1234567890"):
    print("✓ Person is enrolled")
    
    # Get their embedding
    doc = get_voice_embedding("+1234567890")
    print(f"  Vector ID: {doc['_id']}")
    print(f"  Created: {doc['created_at']}")
    
    # Get history
    history = get_enrollment_history("+1234567890")
    print(f"  Enrollments: {len(history)}")
    for record in history:
        print(f"    - {record['completed_at']}: {record['chunks_collected']} chunks")
else:
    print("✗ Not enrolled yet")
```

### Use Case 5: Monitor Enrollment Progress

```python
from mongodb_enrollment_service import get_session_summary, get_enrollment_statistics

# During enrollment
session_id = "your-session-id"
summary = get_session_summary(session_id)

if summary['status'] == 'collecting':
    progress = summary['chunks_collected'] / summary['max_chunks'] * 100
    print(f"Progress: {progress:.0f}% ({summary['chunks_collected']}/{summary['max_chunks']} chunks)")
    print(f"Duration so far: {summary['chunk_stats']['total_duration_seconds']:.1f}s")

# Overall statistics
stats = get_enrollment_statistics()
print(f"\nOverall Stats:")
print(f"  Total sessions: {stats['total_sessions']}")
print(f"  Completed: {stats['total_completions']}")
print(f"  Success: {stats['total_completions']/stats['total_sessions']*100:.1f}%")
```

## 🔌 FastAPI Integration

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from mongodb_enrollment_service import (
    create_enrollment_session,
    add_audio_chunk,
    finalize_enrollment,
    get_session_summary
)
import numpy as np

app = FastAPI()

@app.post("/enrollment/start")
async def start_enrollment(phone: str):
    """Start new enrollment session"""
    session_id, data = create_enrollment_session(phone)
    return {"session_id": session_id, "status": data["status"]}

@app.post("/enrollment/{session_id}/chunk")
async def add_chunk(session_id: str, file: UploadFile = File(...)):
    """Add audio chunk"""
    audio_bytes = await file.read()
    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
    
    success, msg, chunk_id = add_audio_chunk(
        session_id=session_id,
        audio_data=audio_np,
        duration_seconds=len(audio_np) / 16000
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    return {"chunk_id": chunk_id}

@app.post("/enrollment/{session_id}/complete")
async def complete_enrollment(session_id: str):
    """Finalize enrollment"""
    success, msg, vector_id = finalize_enrollment(session_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    return {"vector_id": vector_id}

@app.get("/enrollment/{session_id}")
async def get_status(session_id: str):
    """Get enrollment status"""
    summary = get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return summary
```

## 🧪 Run Tests

```bash
# Run all tests
cd backend
python test_mongodb_enrollment_service.py

# Expected output:
# ================================================================================
#                 MONGODB ENROLLMENT SERVICE TEST SUITE
# ================================================================================
# ============================================================
# TEST: Create Enrollment Session
# ============================================================
# ✓ Session created: 12345678
# ✓ Phone: +1234567890
# ✓ Status: active
# ... (more tests)
# ================================================================================
#                         ALL TESTS PASSED ✓
# ================================================================================
```

## 📊 Database Schema

The service creates 3 collections in MongoDB:

### enrollment_sessions
- Stores active and completed enrollment sessions
- Tracks all metadata about each session
- Used for session state management

### audio_chunks
- Records metadata for each audio chunk submitted
- Includes quality scores, duration, sample count
- Enables retrieval of submission history

### enrollment_history
- Audit trail of completed enrollments
- Tracks success/failure and merge strategy
- Used for compliance and analytics

See MongoDB directly:
```bash
# Connect to MongoDB
mongosh

# Show databases
show dbs

# Use voice_biometric database
use voice_biometric

# Show collections
show collections

# View sessions
db.enrollment_sessions.find()

# View session details
db.enrollment_sessions.findOne()

# View statistics
db.enrollment_sessions.aggregate([
  {$group: {_id: "$status", count: {$sum: 1}}}
])
```

## 🚨 Troubleshooting

### MongoDB Not Running

**Error:** `Connection refused` or `Failed to connect`

**Solution:**
```bash
# Start MongoDB
mongod --dbpath /path/to/data

# Or with Docker
docker run -d -p 27017:27017 mongo:latest
```

### Session Not Found

**Error:** `Session {id} not found`

**Solution:**
- Session may have expired (default timeout 1 hour)
- Verify session_id is correct
- Check database has data: `db.enrollment_sessions.countDocuments()`

### Audio Quality Issues

**Error:** `Audio quality score below threshold`

**Solution:**
- Provide higher quality audio (less noise)
- Adjust `quality_threshold` in config, or
- Increase `quality_score` parameter when adding chunk

### Too Many Chunks Required

**Error:** `Insufficient chunks. Need X, got Y`

**Solution:**
- Add more chunks before finalizing
- Or reduce `min_chunks_required` in config

## 📚 Next Steps

1. **Run tests** to verify everything works:
   ```bash
   python test_mongodb_enrollment_service.py
   ```

2. **Read the Quick Reference** for common tasks:
   - See `MONGODB_ENROLLMENT_SERVICE_QUICK_REFERENCE.md`

3. **Review the Full API** for all methods:
   - See `MONGODB_ENROLLMENT_SERVICE_API_REFERENCE.md`

4. **Explore the Implementation** guide for deep dive:
   - See `MONGODB_ENROLLMENT_SERVICE_IMPLEMENTATION.md`

5. **Integrate into your app**:
   - See FastAPI examples above
   - Use `mongodb_enrollment_service` functions directly

## 💡 Key Concepts

### Session
A sequence of audio chunks submitted by one person for enrollment.
- Can have 1-N chunks
- Stateful (tracking progress)
- Persistent (stored in MongoDB)

### Embedding
A 192-dimensional vector representing a person's voice.
- Generated from audio
- Stored in `voice_embeddings` collection
- Used for verification/matching

### Merge Strategy
How to combine multiple chunks into single embedding:
- **Embedding merge**: Generate embedding per chunk, average embeddings
- **Audio merge**: Merge audio chunks, generate single embedding

### Quality Score
Confidence that audio is good (0.0-1.0):
- 1.0 = perfect audio
- 0.7 = acceptable
- < threshold = rejected

## 📞 Support Resources

- **Quick Start:** `GETTING_STARTED_MONGODB_ENROLLMENT.md` ← You are here
- **Feature Index:** `MONGODB_ENROLLMENT_SERVICE_INDEX.md`
- **Quick Reference:** `MONGODB_ENROLLMENT_SERVICE_QUICK_REFERENCE.md`
- **Full Implementation:** `MONGODB_ENROLLMENT_SERVICE_IMPLEMENTATION.md`
- **API Reference:** `MONGODB_ENROLLMENT_SERVICE_API_REFERENCE.md`
- **Tests:** `test_mongodb_enrollment_service.py`

---

**Ready to get started?** Pick a use case above and try it! 🎉
