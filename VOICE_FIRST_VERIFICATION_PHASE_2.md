# Voice-First Verification Flow - Phase 2 Implementation

## Overview

Phase 2 implements the **NEW VOICE-FIRST VERIFICATION FLOW** as requested. This is a fundamental shift from the old enrollment-first model to a voice-first biometric authentication system.

---

## Old Flow (Before Phase 2)
```
User enters phone number → Voice recording → Verification against specific phone number
```

## New Flow (After Phase 2)
```
User records voice → Backend searches ALL enrollments → Auto-detect phone number → Create verified session
```

---

## Architecture

### 1. Session Service (`session_service.py`)

A new service module that manages verified sessions after successful voice biometric authentication.

**Key Classes:**
- `VerifiedSession`: Dataclass representing a verified session with:
  - `session_id`: Unique UUID for this verification
  - `phone_number`: Auto-detected matched phone number
  - `verification_score`: Similarity score (0-1)
  - `langgraph_session_id`: Reference to LangChain/LangGraph session
  - Comprehensive similarity metrics

- `VerifiedSessionManager`: Manager for creating and managing verified sessions
  - `create_verified_session()`: Creates a new verified session
  - `create_langgraph_session()`: Creates LangChain session for verified user
  - `get_session()`, `revoke_session()`, `is_session_valid()`

**Global Instance:**
```python
session_manager = get_verified_session_manager()
```

---

### 2. Database Schema (`database.py`)

Added **`verified_sessions`** collection with the following structure:

```json
{
    "session_id": "uuid",
    "phone_number": "matched-phone-number",
    "verification_score": 0.85,
    "session_status": "verified|active|expired|revoked",
    "created_at": "timestamp",
    "verified_at": "timestamp",
    "expires_at": "timestamp",
    "langgraph_session_id": "lg_xxx",
    "similarity_score": 0.85,
    "cosine_similarity": 0.85,
    "cosine_distance": 0.15,
    "euclidean_distance": 1.2,
    "correlation_distance": 0.1,
    "confidence": 85.0,
    "metadata": {}
}
```

**Database Operations:**
- `save_verified_session()` - Store verified session
- `get_verified_session()` - Retrieve by session ID
- `update_verified_session()` - Update session status
- `get_verified_sessions_for_phone()` - Get sessions by phone number
- `get_active_verified_sessions()` - Get active sessions
- `get_recent_verifications()` - Get recent verified sessions

---

### 3. WebSocket Verification Handler (`websocket_events.py`)

**Updated `handle_verify()` method** - Now implements voice-first verification:

#### Key Changes:

1. **No Phone Number Required**
   - Frontend sends only audio, no phone_number field
   - Router updated: `requires_fields=[]` (was `["phone_number"]`)

2. **Voice-First Search**
   ```python
   results = find_nearest_embedding(
       query_embedding=query_embedding,
       phone_number=None,  # Search ALL enrollments
       limit=1
   )
   ```

3. **Auto-Detection & Matching**
   - Gets best match from all enrolled embeddings
   - Compares against threshold (0.75 by default)

4. **Session Creation on Match**
   ```python
   if is_match:
       verified_session = session_manager.create_verified_session(
           phone_number=matched_phone_number,
           verification_score=similarity_score,
           similarity_metrics=comprehensive_metrics
       )
       
       langgraph_session_id = session_manager.create_langgraph_session(
           verified_session
       )
       
       save_verified_session(verified_session.to_dict())
   ```

---

## Response Format

### Success Response (Match Found)
```json
{
    "type": "verification_success",
    "status": "success",
    "data": {
        "status": "success",
        "message": "Your voice is matched with this mobile number: +1234567890",
        "phone_number": "+1234567890",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "langgraph_session_id": "lg_550e8400_1234567890",
        "similarity_score": 0.85,
        "threshold": 0.75,
        "confidence": 85.0,
        "metrics": {
            "cosine_similarity": 0.85,
            "cosine_distance": 0.15,
            "euclidean_distance": 1.2,
            "correlation_distance": 0.1,
            "confidence": 85.0
        },
        "timestamp": "2026-02-19T10:30:45.123Z"
    }
}
```

### Failure Response (No Match)
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

## Frontend Implementation

### Old Way
```javascript
const response = await sendVerifyMessage({
    type: 'verify',
    phone_number: '+1234567890'  // User enters this
});
```

### New Way (Phase 2)
```javascript
const response = await sendVerifyMessage({
    type: 'verify'
    // NO phone_number needed!
});

// Response contains auto-detected phone_number
if (response.status === 'success') {
    console.log(`Matched: ${response.phone_number}`);
    console.log(`Session ID: ${response.session_id}`);
}
```

---

## Workflow

### Step 1: Frontend - Record Voice
```javascript
// User clicks "Record Voice"
const audioBlob = await recordAudio();
// Send audio via WebSocket (no phone number)
ws.send(JSON.stringify({
    type: 'audio',
    data: base64EncodedAudio
}));
```

### Step 2: Frontend - Initiate Verification
```javascript
// User clicks "Verify"
ws.send(JSON.stringify({
    type: 'verify'
    // No phone_number field!
}));
```

### Step 3: Backend - Process Verification
```python
# In websocket_events.py handle_verify():
1. Get audio from buffer
2. Generate embedding: query_embedding = generate_embedding(audio_data)
3. Search ALL enrollments: find_nearest_embedding(query_embedding, phone_number=None, limit=1)
4. Get best match
5. Compare score against threshold
6. If match >= threshold:
   - Create verified session
   - Create LangChain session
   - Store in verified_sessions collection
   - Return success with phone_number and session_id
7. Else:
   - Return failure with "No record found" message
```

### Step 4: Frontend - Display Result
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'verification_success') {
        // SUCCESS: Show matched phone number
        showMessage(`Your voice is matched with this mobile number: ${data.phone_number}`);
        storeSessionId(data.session_id);
    } else if (data.error_type === 'no_match') {
        // FAILURE: Show error message
        showMessage('No record found for this voice in the system.');
    }
};
```

---

## Key Features

✅ **Voice-First Authentication**
- No phone number input required from user
- Backend intelligently identifies the user from voice

✅ **LangChain Integration**
- `langgraph_session_id` created for each successful verification
- Ready for conversational AI integration

✅ **Session Persistence**
- Verified sessions stored in MongoDB
- Session history available for audit

✅ **Comprehensive Metrics**
- Cosine similarity
- Euclidean distance
- Correlation distance
- Confidence score

✅ **Clear Error Messages**
- "Your voice is matched with this mobile number: XXX" (Success)
- "No record found for this voice in the system." (Failure)

✅ **Production-Grade Architecture**
- Thin router in main.py
- Business logic in websocket_events.py
- Session management in session_service.py
- DB operations in database.py
- Proper logging at every step
- Async-compatible implementation

---

## Configuration

### Similarity Threshold
```python
# In websocket_events.py
SIMILARITY_THRESHOLD = 0.75  # Adjust based on your requirements
```

### Session Timeout
```python
# In session_service.py
session_manager = VerifiedSessionManager(
    session_timeout_seconds=3600  # 1 hour
)
```

---

## Testing

### Manual WebSocket Test
```python
import websocket
import json
import base64

def test_voice_first_verification():
    ws = websocket.create_connection("ws://localhost:8000/ws/voice")
    
    # Load enrolled voice audio
    with open('enrolled_voice.wav', 'rb') as f:
        audio_data = f.read()
    
    # Send audio chunks
    ws.send(json.dumps({
        "type": "audio",
        "data": base64.b64encode(audio_data).decode()
    }))
    
    # Initiate verification (NO phone_number)
    ws.send(json.dumps({
        "type": "verify"
    }))
    
    # Receive response
    response = ws.recv()
    data = json.loads(response)
    
    print(f"Status: {data.get('type')}")
    print(f"Message: {data.get('message')}")
    if data.get('phone_number'):
        print(f"Matched Phone: {data.get('phone_number')}")
        print(f"Session ID: {data.get('session_id')}")
```

---

## Database Indexes

```python
# verified_sessions collection
- session_id (unique)
- phone_number
- session_status
- created_at
- verified_at
```

---

## Logging

The implementation includes detailed logging:
```
[INFO] Generating embedding for voice-first verification...
[INFO] Searching across all enrolled embeddings...
[INFO] Best match: +1234567890 with similarity score 0.8500
[INFO] ✓ Voice verification successful for +1234567890 (score: 0.8500)
[INFO] Created LangGraph session: lg_550e8400_1234567890
[INFO] Stored verified session in MongoDB: 550e8400
```

---

## Summary of Changes

| File | Changes |
|------|---------|
| `session_service.py` | Created new file for verified session management |
| `database.py` | Added verified_sessions collection operations |
| `websocket_events.py` | Rewrote handle_verify() for voice-first flow, added imports |
| `main.py` | Updated VERIFY route: removed phone_number requirement |

---

## Migration Guide

### For Existing Enrollment Users
- Users enrolled in Phase 1 are automatically supported in Phase 2
- No re-enrollment needed
- Voice biometrics are already in the system

### Frontend Update
```javascript
// OLD
ws.send(JSON.stringify({
    type: 'verify',
    phone_number: '+1234567890'
}));

// NEW - Much simpler!
ws.send(JSON.stringify({
    type: 'verify'
}));
```

---

## Next Steps

1. **Test voice-first verification** with existing enrollments
2. **Implement LangChain session usage** in your conversation flow
3. **Add session validation** in subsequent requests
4. **Implement session expiry** mechanism
5. **Add analytics** for verification success rates

---

## Support & Troubleshooting

### "No record found for this voice in the system"
- Check if any voices are enrolled in the system
- Verify similarity_score is below threshold
- Check logs for embedding generation errors

### No LangGraph session created
- Ensure session_service.py is properly imported
- Check for exceptions in create_langgraph_session()
- Verify MongoDB is accessible

### Verification always fails
- Increase SIMILARITY_THRESHOLD (check if threshold is too high)
- Verify voice quality
- Check embedding generation
- Review logs for error messages
