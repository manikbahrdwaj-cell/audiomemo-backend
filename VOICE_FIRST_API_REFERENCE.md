# Voice-First Verification - API Reference

## WebSocket Messages

### Audio Chunk Message
**Send audio data to the backend**

```json
{
    "type": "audio",
    "data": "base64-encoded-audio-bytes"
}
```

**Response:**
```json
{
    "type": "success",
    "message": "audio_received",
    "data": {
        "size": 32000,
        "chunks": 2
    }
}
```

---

### Verify Message (NEW - Phase 2)
**Initiate voice-first verification**

**Request:**
```json
{
    "type": "verify"
}
```

**Note:** No `phone_number` field required! Backend auto-detects it.

**Response - Success:**
```json
{
    "type": "verification_success",
    "status": "success",
    "data": {
        "status": "success",
        "message": "Your voice is matched with this mobile number: +1234567890",
        "phone_number": "+1234567890",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "langgraph_session_id": "lg_550e8400_1234567890_1645234245",
        "similarity_score": 0.8534,
        "threshold": 0.75,
        "confidence": 85.34,
        "metrics": {
            "cosine_similarity": 0.8534,
            "cosine_distance": 0.1466,
            "euclidean_distance": 1.245,
            "correlation_distance": 0.089,
            "confidence": 85.34
        },
        "timestamp": "2026-02-19T10:30:45.123Z"
    }
}
```

**Response - No Match:**
```json
{
    "type": "error",
    "status": "error",
    "error_type": "no_match",
    "message": "No record found for this voice in the system.",
    "data": {
        "status": "failed",
        "message": "No record found for this voice in the system.",
        "best_match_phone": "+1234567890",
        "best_match_score": 0.65,
        "threshold": 0.75,
        "similarity_metrics": {
            "cosine_similarity": 0.65,
            "cosine_distance": 0.35
        }
    }
}
```

---

### Enroll Message (Unchanged)
**Enroll a new voice**

```json
{
    "type": "enroll",
    "phone_number": "+1234567890"
}
```

---

### Reset Message
**Clear audio buffer**

```json
{
    "type": "reset"
}
```

**Response:**
```json
{
    "type": "success",
    "message": "reset_acknowledged"
}
```

---

### Ping Message
**Keep-alive signal**

```json
{
    "type": "ping"
}
```

**Response:**
```json
{
    "type": "success",
    "message": "pong",
    "data": {
        "connection_id": "client-uuid",
        "uptime": 123.456
    }
}
```

---

## HTTP REST Endpoints (Optional)

### Get Verified Session
```
GET /verified-sessions/{session_id}
```

**Response:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "phone_number": "+1234567890",
    "verification_score": 0.85,
    "session_status": "verified",
    "created_at": "2026-02-19T10:30:45Z",
    "verified_at": "2026-02-19T10:30:46Z",
    "langgraph_session_id": "lg_550e8400_1234567890_1645234245",
    "metrics": {
        "cosine_similarity": 0.85,
        "confidence": 85.0
    }
}
```

---

## Database Schema

### Verified Session Document
```json
{
    "_id": "ObjectId",
    "session_id": "uuid",
    "phone_number": "+1234567890",
    "verification_score": 0.85,
    "session_status": "verified|active|expired|revoked",
    "created_at": "2026-02-19T10:30:45.123Z",
    "verified_at": "2026-02-19T10:30:46.123Z",
    "expires_at": "2026-02-19T11:30:45.123Z",
    "updated_at": "2026-02-19T10:30:46.123Z",
    "langgraph_session_id": "lg_550e8400_1234567890_1645234245",
    "embedded_phone_number": "+1234567890",
    "similarity_score": 0.8534,
    "cosine_similarity": 0.8534,
    "cosine_distance": 0.1466,
    "euclidean_distance": 1.245,
    "correlation_distance": 0.089,
    "confidence": 85.34,
    "metadata": {
        "client_id": "...",
        "ip_address": "...",
        "user_agent": "..."
    }
}
```

---

## Session Service API

### Python
```python
from session_service import get_verified_session_manager

manager = get_verified_session_manager()

# Create a verified session
session = manager.create_verified_session(
    phone_number="+1234567890",
    verification_score=0.85,
    similarity_metrics={
        "cosine_similarity": 0.85,
        "cosine_distance": 0.15,
        "euclidean_distance": 1.2,
        "correlation_distance": 0.1,
        "confidence": 85.0
    }
)

# Create LangChain session
langgraph_id = manager.create_langgraph_session(session)

# Retrieve session
retrieved = manager.get_session(session.session_id)

# Check validity
is_valid = manager.is_session_valid(session.session_id)

# Revoke session
manager.revoke_session(session.session_id)
```

---

## Database API

### Python
```python
from database import (
    save_verified_session,
    get_verified_session,
    update_verified_session,
    get_verified_sessions_for_phone,
    get_active_verified_sessions,
    get_recent_verifications
)

# Save a verified session
doc_id = save_verified_session({
    "session_id": session_id,
    "phone_number": phone_number,
    "verification_score": score,
    "session_status": "verified",
    "metrics": {...}
})

# Retrieved session
session = get_verified_session(session_id)

# Update session
update_verified_session(session_id, {
    "session_status": "active",
    "metadata": {...}
})

# Get all verified sessions for a phone
sessions = get_verified_sessions_for_phone("+1234567890")

# Get active sessions
active = get_active_verified_sessions()

# Get recent verifications
recent = get_recent_verifications(limit=20)
```

---

## Error Responses

### No Audio Data
```json
{
    "type": "error",
    "error_type": "no_audio",
    "message": "No audio data available"
}
```

### Insufficient Audio
```json
{
    "type": "error",
    "error_type": "insufficient_audio",
    "message": "Audio data too small (min: 1000 bytes)"
}
```

### Verification Error
```json
{
    "type": "error",
    "error_type": "verification_error",
    "message": "Verification failed: [error details]"
}
```

### No Match Found
```json
{
    "type": "error",
    "error_type": "no_match",
    "message": "No record found for this voice in the system."
}
```

---

## Configuration Parameters

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| `SIMILARITY_THRESHOLD` | websocket_events.py | 0.75 | Voice match threshold (0-1) |
| `MIN_AUDIO_SIZE` | websocket_events.py | 1000 | Minimum audio bytes required |
| `session_timeout_seconds` | session_service.py | 3600 | Session validity duration |
| `max_chunks` | enrollment_service.py | 10 | Max audio chunks per session |

---

## Request/Response Statistics

### Success Flow
1. **Send Audio** → `audio_received` (instant)
2. **Send Verify** → `chunk_progress` (multiple) → `verification_success` (~2-3 sec)

### Failure Flow
1. **Send Audio** → `audio_received` (instant)
2. **Send Verify** → `chunk_progress` (multiple) → `error: no_match` (~2-3 sec)

---

## Example: Complete Flow

### JavaScript
```javascript
// 1. Connect
const ws = new WebSocket('ws://localhost:8000/ws/voice');

// 2. Send audio
ws.send(JSON.stringify({
    type: 'audio',
    data: base64_audio
}));

// Wait for: {"type": "success", "message": "audio_received"}

// 3. Verify
ws.send(JSON.stringify({
    type: 'verify'
}));

// Wait for progress updates if enabled
// {"type": "chunk_progress", "payload": {...}}

// 4. Get result
ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    
    if (response.type === 'verification_success') {
        const phone = response.data.phone_number;
        const sessionId = response.data.session_id;
        console.log(`✓ Matched: ${phone}`);
        console.log(`Session: ${sessionId}`);
        
    } else if (response.error_type === 'no_match') {
        console.log('✗ No match found');
    }
};
```

### Python
```python
import websocket
import json
import base64

# 1. Connect
ws = websocket.create_connection('ws://localhost:8000/ws/voice')

# 2. Send audio
with open('voice.wav', 'rb') as f:
    audio = base64.b64encode(f.read()).decode()
    
ws.send(json.dumps({
    'type': 'audio',
    'data': audio
}))

resp = ws.recv()
print(f"Audio: {resp}")

# 3. Verify
ws.send(json.dumps({
    'type': 'verify'
}))

# 4. Get result
result = ws.recv()
data = json.loads(result)

if data['type'] == 'verification_success':
    print(f"✓ Matched: {data['data']['phone_number']}")
    print(f"Session: {data['data']['session_id']}")
else:
    print(f"✗ {data['message']}")
```

---

## Metrics Explanation

| Metric | Range | Interpretation |
|--------|-------|-----------------|
| `cosine_similarity` | 0-1 | Voice similarity (higher = more similar) |
| `cosine_distance` | 0-1 | Voice distance (lower = more similar) |
| `euclidean_distance` | 0-∞ | Vector distance |
| `correlation_distance` | 0-2 | Correlation coefficient distance |
| `confidence` | 0-100 | Confidence percentage |

---

## Next Steps

1. Store `session_id` and `phone_number` on client
2. Use `session_id` for future API calls
3. Use `phone_number` to display in UI
4. Use `langgraph_session_id` for LangChain conversations

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review error messages in response
3. Monitor WebSocket connection state
4. Verify MongoDB is running
5. Check threshold settings
