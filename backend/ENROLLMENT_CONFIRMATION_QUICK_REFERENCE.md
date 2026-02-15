# Enrollment Service with Confirmation - Quick Reference

## 🚀 Quick Start

### 1. See Confirmation Feature in Action (5 minutes)

**Terminal 1 - Start Server:**
```bash
cd backend
python main.py
```

**Terminal 2 - Run Test:**
```bash
cd backend
python test_enrollment_confirmation.py
```

Watch the console as confirmations are sent and received!

---

## 📋 Common Use Cases

### Use Case 1: Complete Enrollment with Auto-Confirmation

**Scenario**: Frontend wants to enroll with automatic confirmation when done

**Steps**:
```
1. Generate UUID client_id on frontend
2. Connect to WebSocket: ws://localhost:8000/ws/voice
3. Create enrollment session via REST
4. Register client with session
5. Upload audio chunks
6. Finalize enrollment (automatic confirmation sent)
7. Receive confirmation on WebSocket
```

**Code Example:**
```python
import requests
import asyncio
import websockets
import json
import uuid

client_id = str(uuid.uuid4())

async def run():
    # Connect WebSocket
    async with websockets.connect('ws://localhost:8000/ws/voice') as ws:
        # Create session
        r = requests.post('http://localhost:8000/enrollment/session',
                         params={'phone_number': '1234567890', 'max_chunks': 1})
        session_id = r.json()['session_id']
        
        # Register client
        requests.post(
            f'http://localhost:8000/enrollment/session/{session_id}/register-client',
            params={'client_id': client_id})
        
        # Upload chunk (simplified - read real audio file)
        # POST /enrollment/session/{session_id}/chunk with file
        
        # Finalize (triggers confirmation)
        r = requests.post(
            f'http://localhost:8000/enrollment/session/{session_id}/finalize')
        
        # Wait for confirmation
        msg = json.loads(await ws.recv())
        if msg['type'] == 'enrollment_confirmed':
            print('✓ Confirmation received!')
            print(msg['data'])

asyncio.run(run())
```

---

### Use Case 2: Manual Confirmation Sending

**Scenario**: You want to send confirmation manually after custom processing

**Steps**:
```
1. Create and finalize enrollment session
2. Get vector_id from database
3. Call confirmation endpoint with session details
4. Confirmation sent to registered client (if any)
```

**API Call:**
```bash
curl -X POST "http://localhost:8000/enrollment/confirmation/send" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-...",
    "phone_number": "1234567890",
    "vector_id": "vector-uuid-...",
    "chunks_processed": 5,
    "success": true,
    "message": "Custom enrollment complete!"
  }'
```

---

### Use Case 3: Multiple Clients Enrolling

**Scenario**: Multiple frontend clients enrolling different users

**Code:**
```python
import requests
import uuid

def enroll_user(phone, samples_count):
    # Each client sends unique client_id
    client_id = str(uuid.uuid4())
    
    # Create session
    r = requests.post('http://localhost:8000/enrollment/session',
                     params={'phone_number': phone})
    session_id = r.json()['session_id']
    
    # Register THIS client with THIS session
    requests.post(
        f'http://localhost:8000/enrollment/session/{session_id}/register-client',
        params={'client_id': client_id})
    
    # Upload samples...
    # Then finalize
    requests.post(
        f'http://localhost:8000/enrollment/session/{session_id}/finalize')
    
    return session_id, client_id

# Multiple enrollments
enroll_user('1111111111', 3)
enroll_user('2222222222', 3)
enroll_user('3333333333', 3)

# Each gets their own confirmation to their client_id!
```

---

## 🔌 API Quick Reference

### Create Enrollment Session
```
POST /enrollment/session

Parameters:
  phone_number: "1234567890"
  max_chunks: 5
  merge_embeddings: true

Response:
{
  "session_id": "uuid",
  "phone_number": "1234567890",
  "status": "active",
  "created_at": "2026-02-14T...",
  "chunks_collected": 0,
  "max_chunks": 5,
  "embeddings_generated": 0,
  "error_message": null
}
```

### Register Client with Session
```
POST /enrollment/session/{session_id}/register-client

Parameters:
  client_id: "client-uuid"

Response:
{
  "success": true,
  "message": "Client ... registered for session ...",
  "session_id": "uuid",
  "client_id": "client-uuid"
}
```

### Add Audio Chunk
```
POST /enrollment/session/{session_id}/chunk

Form Data:
  file: <wav file>
  quality_score: 1.0 (optional)

Response:
{
  "success": true,
  "message": "Chunk added (1/5)",
  "chunk": {
    "chunk_id": "uuid",
    "chunk_number": 1,
    "total_chunks": 5,
    "duration_seconds": 2.5,
    "timestamp": "2026-02-14T...",
    "has_embedding": true,
    "quality_score": 1.0
  },
  "session_status": "collecting"
}
```

### Finalize Enrollment
```
POST /enrollment/session/{session_id}/finalize

Parameters:
  force_single: false

Response:
{
  "success": true,
  "message": "Enrollment finalized successfully",
  "phone_number": "1234567890",
  "vector_id": "vector-uuid",
  "chunks_processed": 5,
  "enrollment_status": "completed"
}

Side Effect:
  → Sends confirmation to registered client via WebSocket
```

### Send Confirmation Manually
```
POST /enrollment/confirmation/send

Parameters:
  session_id: "uuid"
  phone_number: "1234567890"
  vector_id: "vector-uuid"
  chunks_processed: 5
  success: true
  message: "Optional custom message"

Response:
{
  "success": true,
  "message": "Confirmation sent successfully",
  "confirmation_id": "uuid",
  "session_id": "uuid",
  "phone_number": "1234567890"
}
```

### Get Confirmation History
```
GET /enrollment/confirmation/history

Parameters:
  limit: 100

Response:
{
  "total": 5,
  "confirmations": [
    {
      "confirmation_id": "uuid",
      "session_id": "uuid",
      "client_id": "client-uuid",
      "phone_number": "1234567890",
      "timestamp": "2026-02-14T...",
      "chunks_processed": 5
    },
    ...
  ]
}
```

---

## 💬 WebSocket Message Format

### Confirmation Message (Received)
```json
{
  "type": "enrollment_confirmed",
  "status": "success",
  "confirmation_id": "uuid-...",
  "timestamp": "2026-02-14T12:30:45.123456",
  "data": {
    "session_id": "uuid-...",
    "phone_number": "1234567890",
    "vector_id": "vector-uuid-...",
    "chunks_processed": 5,
    "message": "Enrollment completed successfully"
  }
}
```

### Error Response (if any)
```json
{
  "type": "error",
  "status": "error",
  "error_type": "error_code",
  "message": "Error description"
}
```

---

## 🎯 JavaScript/Frontend Example

```javascript
const clientId = generateUUID();
const ws = new WebSocket('ws://localhost:8000/ws/voice');

ws.onopen = async () => {
  console.log('Connected to server');
  
  // Create session
  const sessionResp = await fetch('http://localhost:8000/enrollment/session', {
    method: 'POST',
    body: new URLSearchParams({
      phone_number: '1234567890',
      max_chunks: 3
    })
  });
  
  const { session_id } = await sessionResp.json();
  console.log('Session:', session_id);
  
  // Register client
  await fetch(
    `http://localhost:8000/enrollment/session/${session_id}/register-client`,
    {
      method: 'POST',
      body: new URLSearchParams({ client_id: clientId })
    }
  );
  console.log('Client registered');
  
  // Upload audio chunks...
  // ...
  
  // Finalize
  await fetch(
    `http://localhost:8000/enrollment/session/${session_id}/finalize`,
    { method: 'POST' }
  );
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'enrollment_confirmed') {
    console.log('✓ Enrollment confirmed!');
    console.log('Vector ID:', message.data.vector_id);
    console.log('Chunks processed:', message.data.chunks_processed);
    // Update UI to show success
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

---

## 🐛 Common Issues & Solutions

### Issue: "No client registered for session"
**Cause**: Client not registered before finalization
**Solution**: Call register-client endpoint first
```bash
POST /enrollment/session/{session_id}/register-client?client_id={id}
```

### Issue: Confirmation not received on WebSocket
**Possible Causes**:
1. Client ID mismatch
2. WebSocket disconnected
3. Registration happened after finalization

**Solution**:
```javascript
// Correct order:
1. Connect WebSocket (get connections)
2. Create session
3. Register client with session
4. Upload chunks
5. Finalize → confirmation sent
```

### Issue: "Client not in active connections"
**Cause**: WebSocket client disconnected
**Solution**:
1. Reconnect WebSocket
2. Re-register client with session
3. Retry finalization

### Issue: "Session not found"
**Cause**: Session ID is invalid or incorrect
**Solution**: Verify session_id from create session response

---

## ✅ Verification Checklist

After implementing, verify:

- [ ] Server starts without errors
- [ ] WebSocket endpoint responds: `ws://localhost:8000/ws/voice`
- [ ] Can create enrollment session: `POST /enrollment/session`
- [ ] Can register client: `POST /enrollment/session/{id}/register-client`
- [ ] Can add chunks: `POST /enrollment/session/{id}/chunk`
- [ ] Can finalize: `POST /enrollment/session/{id}/finalize`
- [ ] Automatic confirmation sent when finalized
- [ ] Can query history: `GET /enrollment/confirmation/history`
- [ ] Test script runs without errors: `python test_enrollment_confirmation.py`

---

## 📚 Full Documentation

For complete details, see:
- `ENROLLMENT_CONFIRMATION_GUIDE.md` - Full guide
- `ENROLLMENT_CONFIRMATION_IMPLEMENTATION.md` - Implementation details
- `test_enrollment_confirmation.py` - Test examples
- `ENROLLMENT_SERVICE_GUIDE.md` - Enrollment service details

---

## 🎓 Learning Path

**Beginner:**
1. Read this quick reference
2. Run test script
3. Try manual confirmation sending

**Intermediate:**
1. Implement client registration
2. Set up WebSocket listener
3. Integrate into your frontend

**Advanced:**
1. Custom confirmation messages
2. Batch confirmations
3. Retry mechanisms
4. Database persistence

---

**Status**: ✅ Ready to use
**Last Updated**: 2026-02-14
