# Enrollment Service - Audio Chunk Collection

## Overview

The Enrollment Service is a comprehensive system for collecting multiple voice samples during user enrollment. It provides session-based management of audio chunks, automatic embedding generation, and intelligent merging of embeddings from multiple utterances.

## Key Features

### 1. **Multi-Chunk Collection**
- Collect multiple audio samples from a single user
- Configurable maximum number of chunks (default: 5)
- Each chunk is processed independently into a voice embedding

### 2. **Session Management**
- Create enrollment sessions with unique session IDs
- Track session state (initializing, active, collecting, processing, completed)
- Automatic session cleanup and timeout management

### 3. **Audio Processing**
- Automatic WAV file validation
- Format conversion and resampling
- Mono/stereo audio handling
- Quality scoring for each chunk

### 4. **Embedding Aggregation**
- Generate embeddings for each audio chunk
- Multiple merge strategies:
  - **CONCATENATE**: Simple averaging (default)
  - **OVERLAP**: Time-weighted averaging (recent chunks weighted higher)
  - **MIX**: Simple averaging (same as concatenate for embeddings)

### 5. **Quality Management**
- Quality scoring for each chunk (0-1 scale)
- Minimum quality threshold validation
- Error tracking and reporting

## API Endpoints

### 1. Create Enrollment Session
```
POST /enrollment/session
```

**Parameters:**
- `phone_number` (string): Unique identifier for the user
- `max_chunks` (integer, optional): Maximum number of chunks per session (default: 5)
- `merge_embeddings` (boolean, optional): Whether to merge embeddings (default: true)

**Response:**
```json
{
  "session_id": "uuid-string",
  "phone_number": "1234567890",
  "status": "active",
  "created_at": "2026-02-14T10:30:00",
  "started_at": "2026-02-14T10:30:00",
  "chunks_collected": 0,
  "max_chunks": 5,
  "embeddings_generated": 0,
  "error_message": null
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/enrollment/session?phone_number=1234567890&max_chunks=5"
```

---

### 2. Add Audio Chunk
```
POST /enrollment/session/{session_id}/chunk
```

**Parameters:**
- `session_id` (path): Session ID from create_enrollment_session
- `file` (file): WAV audio file
- `quality_score` (float, optional): Quality confidence score 0-1 (default: 1.0)

**Response:**
```json
{
  "success": true,
  "message": "Chunk added (1/5)",
  "chunk": {
    "chunk_id": "uuid-string",
    "chunk_number": 1,
    "total_chunks": 5,
    "duration_seconds": 3.5,
    "timestamp": "2026-02-14T10:30:15",
    "has_embedding": true,
    "quality_score": 0.95
  },
  "session_status": "collecting"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/enrollment/session/{session_id}/chunk" \
  -F "file=@voice_sample.wav" \
  -F "quality_score=0.95"
```

---

### 3. Get Session Status
```
GET /enrollment/session/{session_id}
```

**Parameters:**
- `session_id` (path): Session ID

**Response:**
```json
{
  "session_id": "uuid-string",
  "phone_number": "1234567890",
  "status": "collecting",
  "created_at": "2026-02-14T10:30:00",
  "started_at": "2026-02-14T10:30:00",
  "chunks_collected": 2,
  "max_chunks": 5,
  "embeddings_generated": 2,
  "error_message": null
}
```

---

### 4. Finalize Enrollment
```
POST /enrollment/session/{session_id}/finalize
```

**Parameters:**
- `session_id` (path): Session ID
- `force_single` (boolean, optional): Use single best embedding if merge fails (default: false)

**Response:**
```json
{
  "success": true,
  "message": "Enrollment completed with 5 chunk(s)",
  "phone_number": "1234567890",
  "vector_id": "mongodb-id",
  "chunks_processed": 5,
  "enrollment_status": "completed"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/enrollment/session/{session_id}/finalize"
```

---

### 5. Cancel Session
```
DELETE /enrollment/session/{session_id}
```

**Parameters:**
- `session_id` (path): Session ID

**Response:**
```json
{
  "success": true,
  "message": "Session xxx cancelled and removed"
}
```

---

### 6. List All Sessions
```
GET /enrollment/sessions
```

**Response:**
```json
{
  "total_sessions": 2,
  "sessions": [
    {
      "session_id": "uuid-1",
      "phone_number": "1234567890",
      "status": "collecting",
      "created_at": "2026-02-14T10:30:00",
      "chunks_collected": 3,
      "max_chunks": 5,
      "embeddings_generated": 3,
      "error_message": null,
      "chunks": [...]
    }
  ]
}
```

---

### 7. Cleanup Expired Sessions
```
POST /enrollment/cleanup
```

**Parameters:**
- `max_age_hours` (integer, optional): Maximum age for a session in hours (default: 1)

**Response:**
```json
{
  "success": true,
  "sessions_cleaned": 2,
  "message": "Cleaned up 2 expired enrollment session(s)"
}
```

---

## Usage Workflow

### Example: Complete Enrollment Flow

#### Step 1: Create Session
```python
import requests

# Create a new enrollment session
response = requests.post(
    "http://localhost:8000/enrollment/session",
    params={
        "phone_number": "1234567890",
        "max_chunks": 5
    }
)

session_data = response.json()
session_id = session_data["session_id"]
print(f"Session created: {session_id}")
```

#### Step 2: Add Audio Chunks
```python
import os

# Add multiple audio samples
audio_files = [
    "sample1.wav",
    "sample2.wav",
    "sample3.wav",
    "sample4.wav",
    "sample5.wav"
]

for i, audio_file in enumerate(audio_files):
    with open(audio_file, 'rb') as f:
        files = {'file': f}
        params = {'quality_score': 0.9 + (i * 0.01)}  # Slightly varied scores
        
        response = requests.post(
            f"http://localhost:8000/enrollment/session/{session_id}/chunk",
            files=files,
            params=params
        )
        
        chunk_data = response.json()
        print(f"Chunk {i+1} added: {chunk_data['message']}")
        
        # Optional: Check session status
        if (i + 1) % 2 == 0:  # Check every 2 chunks
            status_response = requests.get(
                f"http://localhost:8000/enrollment/session/{session_id}"
            )
            status = status_response.json()
            print(f"Session status: {status['embeddings_generated']} embeddings generated")
```

#### Step 3: Finalize Enrollment
```python
# Finalize the enrollment
response = requests.post(
    f"http://localhost:8000/enrollment/session/{session_id}/finalize"
)

final_data = response.json()
print(f"Enrollment result: {final_data['success']}")
print(f"Vector ID: {final_data['vector_id']}")
print(f"Chunks processed: {final_data['chunks_processed']}")
```

---

## Configuration

### EnrollmentSessionConfig

```python
from enrollment_service import EnrollmentSessionConfig, MergeMode

config = EnrollmentSessionConfig(
    max_chunks=10,                      # Max chunks per session
    chunk_timeout_seconds=30,           # Timeout for single chunk
    session_timeout_seconds=300,        # Timeout for entire session
    min_chunks_required=1,              # Minimum chunks needed
    auto_process=True,                  # Auto-generate embeddings
    merge_embeddings=True,              # Merge multiple embeddings
    merge_mode=MergeMode.CONCATENATE,   # Merge strategy
    store_chunks=True,                  # Store raw chunks
    quality_threshold=0.7               # Min quality score
)

session = create_enrollment_session("1234567890", config)
```

---

## Session States

```
INITIALIZING → ACTIVE → COLLECTING → PROCESSING → COMPLETED
                           ↓
                        ERROR
                           ↓
                       CANCELLED
```

### State Descriptions

| State | Description |
|-------|-------------|
| `initializing` | Session created, not yet active |
| `active` | Session active, ready for chunks |
| `collecting` | Actively collecting audio chunks |
| `processing` | Processing chunks into embeddings |
| `finalizing` | Merging embeddings and storing |
| `completed` | Enrollment successfully completed |
| `error` | Error occurred during enrollment |
| `cancelled` | Session was cancelled by user |

---

## Audio Format Requirements

- **Format**: WAV (RIFF)
- **Sample Rate**: 16000 Hz (will be auto-corrected if different)
- **Channels**: Mono or Stereo (auto-converted to mono)
- **Min Duration**: 0.5 seconds
- **Max Duration**: 5 seconds
- **Quality Score**: 0-1 (floating point)

---

## Embedding Merge Strategies

### 1. **CONCATENATE (Default)**
Simple arithmetic mean of all embeddings:
```
merged = (embedding_1 + embedding_2 + ... + embedding_n) / n
```

**Pros:**
- Simple and fast
- Fair weighting of all samples

**Cons:**
- Doesn't account for quality differences

### 2. **OVERLAP**
Time-weighted average (newer samples have higher weight):
```
weights = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # For 6 samples
merged = weighted_average(embeddings, weights)
```

**Pros:**
- Recent samples have higher confidence
- Adaptive to user behavior changes

**Cons:**
- Slightly more complex
- May bias towards last sample

### 3. **MIX**
Same as CONCATENATE for embeddings:
```
merged = mean(embeddings)
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Session not found | Invalid session_id | Create a new session |
| Max chunks reached | Too many chunks added | Finalize current session or create new one |
| File too small | Audio too short | Record longer audio sample (>0.5s) |
| Invalid file type | Not a WAV file | Convert to WAV format |
| Low quality score | Poor audio quality | Re-record with better conditions |
| Embedding merge failed | Quality issues | Use `force_single=true` in finalize |

---

## Performance Considerations

### Memory Usage
- **Per Chunk**: ~400KB for 5-second audio
- **Per Embedding**: ~800 bytes (192-dim float32)
- **Per Session** (5 chunks): ~2-3 MB

### Processing Time
- **Chunk Upload**: <100ms
- **Embedding Generation**: 500-2000ms per chunk (GPU dependent)
- **Merge**: <100ms
- **Total for 5 chunks**: ~3-12 seconds

### Optimization Tips
1. Use `store_chunks=False` to save memory after processing
2. Implement client-side audio validation
3. Use quality scores to filter low-quality samples
4. Set reasonable `max_chunks` (5-10 is typical)

---

## Security Considerations

1. **Phone Number Validation**: Always validate phone number format
2. **File Size Limits**: Max 10MB per audio file
3. **Session Timeout**: Implement proper cleanup timers
4. **Rate Limiting**: Use WebSocket rate limits for rapid uploads
5. **Audio Privacy**: Consider storing only embeddings, not raw audio

---

## Integration with Voice Biometrics

### Enrollment Flow
1. User initiates enrollment → Create Session
2. User provides voice samples → Add Chunks
3. Service generates embeddings → Auto-process enabled
4. User confirms completion → Finalize Enrollment
5. System stores merged embedding

### Verification Flow
1. Collect single verification audio
2. Generate embedding
3. Calculate similarity with stored enrollment embedding
4. Compare against threshold (typically 0.6-0.7)

---

## Troubleshooting

### Session Expires Before Completion
**Issue**: Session gets cleaned up before finalization

**Solution**:
```python
# Increase session timeout
config = EnrollmentSessionConfig(
    session_timeout_seconds=600  # 10 minutes
)
```

### Low Quality Embeddings
**Issue**: Merged embedding has poor quality

**Solution**:
```python
# Require more chunks or higher quality
config = EnrollmentSessionConfig(
    min_chunks_required=3,
    quality_threshold=0.8
)
```

### Memory Issues
**Issue**: Too much memory usage with many sessions

**Solution**:
```python
# Don't store raw audio chunks
config = EnrollmentSessionConfig(
    store_chunks=False  # Only store embeddings
)

# Periodic cleanup
requests.post("http://localhost:8000/enrollment/cleanup?max_age_hours=1")
```

---

## API Testing

See [enrollment_service_test.py](enrollment_service_test.py) for comprehensive tests.

---

## Files

- **enrollment_service.py**: Core service implementation
- **API Endpoints**: Integrated into main.py
- **Documentation**: This file

---

## Future Enhancements

1. **Progressive Learning**: Update enrollment embeddings over time
2. **Anti-Spoofing**: Detect and reject spoofed audio
3. **Liveness Detection**: Voice challenge-response
4. **Multi-Language Support**: Support multiple languages
5. **Batch Processing**: Process multiple users in parallel
6. **Analytics Dashboard**: Track enrollment metrics
7. **A/B Testing**: Compare different merge strategies
8. **Adaptive Thresholds**: Dynamic quality thresholds

---
