# Enrollment Service - Quick Reference

## What is the Enrollment Service?

The **Enrollment Service** is a multi-chunk voice enrollment system that allows users to provide multiple voice samples during enrollment. Each sample is processed into a voice embedding, and the embeddings are intelligently merged to create a robust final enrollment template.

## Key Components

### 1. **EnrollmentSession**
- Represents a single enrollment session for one user
- Tracks audio chunks, embeddings, and session state
- Manages chunk collection to finalization

### 2. **AudioChunkRecord**
- Stores a single audio sample with metadata
- Tracks quality scores and processing status
- Optional storage of raw audio data

### 3. **EnrollmentServiceManager**
- Manages multiple concurrent enrollment sessions
- Handles session lifecycle and cleanup
- Provides session listing and filtering

### 4. **Configuration**
- `EnrollmentSessionConfig`: Customizable session parameters
- Merge modes, quality thresholds, timeouts, etc.

## Quick Start

### 1. Create an Enrollment Session
```python
import requests

response = requests.post(
    "http://localhost:8000/enrollment/session",
    params={
        "phone_number": "1234567890",
        "max_chunks": 5
    }
)
session_id = response.json()["session_id"]
```

### 2. Add Audio Chunks
```python
with open("voice_sample.wav", "rb") as f:
    files = {"file": f}
    response = requests.post(
        f"http://localhost:8000/enrollment/session/{session_id}/chunk",
        files=files,
        params={"quality_score": 0.95}
    )
    print(response.json()["message"])
```

### 3. Finalize Enrollment
```python
response = requests.post(
    f"http://localhost:8000/enrollment/session/{session_id}/finalize"
)
result = response.json()
print(f"Enrollment: {result['success']}")
print(f"Vector ID: {result['vector_id']}")
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/enrollment/session` | POST | Create new session |
| `/enrollment/session/{id}/chunk` | POST | Add audio chunk |
| `/enrollment/session/{id}` | GET | Get session status |
| `/enrollment/session/{id}/finalize` | POST | Finalize enrollment |
| `/enrollment/session/{id}` | DELETE | Cancel session |
| `/enrollment/sessions` | GET | List all sessions |
| `/enrollment/cleanup` | POST | Cleanup expired sessions |

## Session States

```
INITIALIZING → ACTIVE → COLLECTING → PROCESSING → COMPLETED
                          ↓
                       ERROR
                          ↓
                      CANCELLED
```

## Configuration Options

```python
from enrollment_service import EnrollmentSessionConfig, MergeMode

config = EnrollmentSessionConfig(
    max_chunks=10,                           # Max chunks per session
    min_chunks_required=1,                   # Min chunks to finalize
    auto_process=True,                       # Auto generate embeddings
    merge_embeddings=True,                   # Merge multiple embeddings
    merge_mode=MergeMode.CONCATENATE,        # Averaging strategy
    quality_threshold=0.7,                   # Min quality score (0-1)
    store_chunks=True,                       # Keep raw audio data
    chunk_timeout_seconds=30,                # Max time per chunk
    session_timeout_seconds=300              # Max session time
)
```

## Merge Strategies

### CONCATENATE (Default)
- Simple arithmetic mean of embeddings
- Fair weighting of all samples
- **Best for**: Standard voice enrollment

### OVERLAP  
- Time-weighted averaging (recent samples weighted higher)
- Adaptive to enrollment progression
- **Best for**: Progressive enrollment

### MIX
- Weighted mixing of embeddings
- Reduces redundancy
- **Best for**: High-redundancy scenarios

## Code Examples

### Example 1: Pre-built Client
```python
from enrollment_service_examples import EnrollmentClient

client = EnrollmentClient()
client.create_session("1234567890", max_chunks=5)
client.upload_chunk("voice_sample.wav", quality_score=0.95)
client.get_status()
client.finalize()
```

### Example 2: Custom Config
```python
from enrollment_service import (
    create_enrollment_session,
    EnrollmentSessionConfig,
    MergeMode
)

config = EnrollmentSessionConfig(
    max_chunks=3,
    merge_mode=MergeMode.OVERLAP,
    quality_threshold=0.85
)

session = create_enrollment_session("1234567890", config)
```

### Example 3: Direct API
```python
import requests

# Create session
r1 = requests.post("http://localhost:8000/enrollment/session",
                   params={"phone_number": "1234567890"})
sid = r1.json()["session_id"]

# Add chunk
with open("audio.wav", "rb") as f:
    r2 = requests.post(
        f"http://localhost:8000/enrollment/session/{sid}/chunk",
        files={"file": f}
    )

# Finalize
r3 = requests.post(
    f"http://localhost:8000/enrollment/session/{sid}/finalize"
)
print(r3.json()["vector_id"])
```

## File Structure

```
backend/
├── enrollment_service.py              # Core service
├── ENROLLMENT_SERVICE_GUIDE.md         # Full documentation
├── enrollment_service_examples.py      # Usage examples
├── test_enrollment_service.py          # Test suite
├── main.py                             # API endpoints (updated)
└── [other_files...]
```

## Testing

Run the test suite:
```bash
cd backend
pytest test_enrollment_service.py -v
```

Run specific test:
```bash
pytest test_enrollment_service.py::TestEnrollmentSession::test_add_chunk_success -v
```

Run examples:
```bash
python enrollment_service_examples.py
```

## Performance Tips

1. **Memory Optimization**
   ```python
   config.store_chunks = False  # Don't store raw audio
   ```

2. **Faster Processing**
   ```python
   config.auto_process = True  # Generate embeddings immediately
   ```

3. **Session Cleanup**
   ```python
   requests.post("http://localhost:8000/enrollment/cleanup?max_age_hours=1")
   ```

4. **Batch Operations**
   - Create multiple sessions in parallel
   - Process uploads concurrently
   - Use connection pooling

## Troubleshooting

### Audio Not Accepted
- ✓ Check WAV format
- ✓ Verify min duration (0.5s)
- ✓ Check file size (> 1KB)

### Session Not Found
- ✓ Verify session_id is correct
- ✓ Check session hasn't expired
- ✓ Ensure session was created

### Low Quality Embeddings
- ✓ Increase number of chunks
- ✓ Increase quality_threshold
- ✓ Use better audio samples

### Memory Issues
- ✓ Set store_chunks=False
- ✓ Run cleanup more frequently
- ✓ Reduce max_chunks

## Integration Checklist

- [ ] Install `soundfile` package
- [ ] Import `enrollment_service` in main.py
- [ ] Add API endpoints to FastAPI app
- [ ] Configure MongoDB for storage
- [ ] Test with sample audio files
- [ ] Implement frontend UI
- [ ] Set up monitoring/logging
- [ ] Deploy to production

## Best Practices

1. **Always validate phone numbers** before session creation
2. **Set appropriate quality thresholds** for your use case
3. **Collect 3-5 chunks** for robust enrollment
4. **Implement proper error handling** in frontend
5. **Monitor session lifecycle** and cleanup expired sessions
6. **Log all enrollment events** for auditing
7. **Use appropriate merge strategy** for your use case
8. **Implement anti-spoofing** checks (future enhancement)

## Related Files

- 📖 [Full Guide](ENROLLMENT_SERVICE_GUIDE.md)
- 🧪 [Test Suite](test_enrollment_service.py)
- 💻 [Examples](enrollment_service_examples.py)
- 🔌 [Main API](main.py)

## Next Steps

1. Review [ENROLLMENT_SERVICE_GUIDE.md](ENROLLMENT_SERVICE_GUIDE.md) for detailed documentation
2. Run [enrollment_service_examples.py](enrollment_service_examples.py) for live examples
3. Execute [test_enrollment_service.py](test_enrollment_service.py) to verify functionality
4. Update frontend to use new enrollment endpoints
5. Deploy and monitor in production

---

**Last Updated**: February 14, 2026
**Status**: Ready for Integration
