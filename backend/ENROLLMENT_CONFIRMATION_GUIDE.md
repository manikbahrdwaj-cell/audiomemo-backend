# Enrollment Service with Confirmation

## Overview

The **Enrollment Service with Confirmation** provides a complete implementation for multi-chunk voice enrollment with real-time WebSocket confirmation messages. When an enrollment session is finalized, the system automatically sends a confirmation message to the registered WebSocket client.

## Key Features

- ✅ **Multi-Chunk Enrollment**: Collect multiple voice samples during enrollment
- ✅ **Session Management**: Track enrollment sessions with full lifecycle management
- ✅ **Real-Time Confirmations**: Send WebSocket messages when enrollment completes
- ✅ **Client Registration**: Register WebSocket clients with enrollment sessions
- ✅ **Confirmation History**: Track all sent confirmations
- ✅ **Automatic Sending**: Confirmations are automatically sent when enrollment finalizes
- ✅ **Manual Confirmation**: Support for manually sending confirmations if needed

## Components

### 1. **EnrollmentConfirmationService**
Located in `enrollment_service.py`, this service manages:
- Client-to-session mapping
- Confirmation message transmission via WebSocket
- Confirmation history tracking

### 2. **WebSocket Message Types**
Added to `websocket_router.py`:
- `ENROLLMENT_CONFIRMED`: Status message when enrollment completes
- `ENROLLMENT_STATUS`: Updates about enrollment progress
- `VERIFY_CONFIRMED`: Status message when verification completes

### 3. **API Endpoints**
New REST endpoints for confirmation management:
- `POST /enrollment/session/{session_id}/register-client`: Register a WebSocket client
- `POST /enrollment/confirmation/send`: Send confirmation manually
- `GET /enrollment/confirmation/history`: Get confirmation history

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                           │
│                  (Sends WebSocket client_id)                │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    WebSocket    REST API    Database
         │           │           │
┌────────┴────────────┴───────────┴────────────────────────┐
│                    FastAPI Backend                        │
│  ┌──────────────────────────────────────────────────┐    │
│  │        Enrollment Service with Confirmation      │    │
│  │  ┌────────────────────────────────────────────┐  │    │
│  │  │ EnrollmentConfirmationService              │  │    │
│  │  │ - Session to Client Mapping                │  │    │
│  │  │ - Confirmation Sending                     │  │    │
│  │  │ - History Tracking                         │  │    │
│  │  └────────────────────────────────────────────┘  │    │
│  │  ┌────────────────────────────────────────────┐  │    │
│  │  │ WebSocket Handler                          │  │    │
│  │  │ - Connection Management                    │  │    │
│  │  │ - Message Routing                          │  │    │
│  │  └────────────────────────────────────────────┘  │    │
│  │  ┌────────────────────────────────────────────┐  │    │
│  │  │ Enrollment Session Manager                 │  │    │
│  │  │ - Session Lifecycle                        │  │    │
│  │  │ - Chunk Collection                         │  │    │
│  │  │ - Embedding Generation                     │  │    │
│  │  └────────────────────────────────────────────┘  │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

### 1. Start WebSocket Connection (Frontend)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/voice');
const clientId = generateUUID();
```

### 2. Create Enrollment Session (REST)
```bash
POST /enrollment/session?phone_number=1234567890&max_chunks=5
Response: { "session_id": "uuid-..." }
```

### 3. Register Client with Session (REST)
```bash
POST /enrollment/session/{session_id}/register-client?client_id={clientId}
Response: { "success": true, "message": "Client registered..." }
```

### 4. Upload Audio Chunks (REST)
```bash
POST /enrollment/session/{session_id}/chunk
File: audio.wav
```

### 5. Finalize Enrollment (REST)
```bash
POST /enrollment/session/{session_id}/finalize
Effect: Automatically sends confirmation to registered client
Response: { "success": true, "vector_id": "..." }
```

### 6. Receive Confirmation (WebSocket)
```json
{
  "type": "enrollment_confirmed",
  "status": "success",
  "confirmation_id": "uuid-...",
  "timestamp": "2026-02-14T12:00:00...",
  "data": {
    "session_id": "uuid-...",
    "phone_number": "1234567890",
    "vector_id": "....",
    "chunks_processed": 5,
    "message": "Enrollment completed successfully"
  }
}
```

## API Reference

### Register Client with Session

**Endpoint:** `POST /enrollment/session/{session_id}/register-client`

**Parameters:**
- `session_id` (path): Enrollment session ID
- `client_id` (query): WebSocket client ID

**Response:**
```json
{
  "success": true,
  "message": "Client ... registered for session ...",
  "session_id": "uuid-...",
  "client_id": "uuid-..."
}
```

### Send Enrollment Confirmation

**Endpoint:** `POST /enrollment/confirmation/send`

**Parameters:**
- `session_id` (query): Enrollment session ID
- `phone_number` (query): Phone number enrolled
- `vector_id` (query): Vector ID from database
- `chunks_processed` (query): Number of chunks
- `success` (query, optional): Success status (default: true)
- `message` (query, optional): Custom message

**Response:**
```json
{
  "success": true,
  "message": "Confirmation sent successfully",
  "confirmation_id": "uuid-...",
  "session_id": "uuid-...",
  "phone_number": "1234567890"
}
```

### Get Confirmation History

**Endpoint:** `GET /enrollment/confirmation/history`

**Parameters:**
- `limit` (query, optional): Max records to return (default: 100)

**Response:**
```json
{
  "total": 5,
  "confirmations": [
    {
      "confirmation_id": "uuid-...",
      "session_id": "uuid-...",
      "client_id": "uuid-...",
      "phone_number": "1234567890",
      "timestamp": "2026-02-14T12:00:00...",
      "chunks_processed": 5
    },
    ...
  ]
}
```

## Usage Examples

### Complete Enrollment with Confirmation (Python)

```python
import requests
import asyncio
import websockets
import json
import uuid

# Configuration
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/voice"
PHONE = "1234567890"

async def main():
    # Generate client ID
    client_id = str(uuid.uuid4())
    
    # Connect to WebSocket
    async with websockets.connect(WS_URL) as ws:
        print(f"Connected with client_id: {client_id}")
        
        # Create enrollment session
        session_response = requests.post(
            f"{API_URL}/enrollment/session",
            params={"phone_number": PHONE, "max_chunks": 3}
        )
        session_id = session_response.json()["session_id"]
        print(f"Created session: {session_id}")
        
        # Register client with session
        requests.post(
            f"{API_URL}/enrollment/session/{session_id}/register-client",
            params={"client_id": client_id}
        )
        print(f"Registered client with session")
        
        # Upload audio chunks (simplified)
        for i in range(3):
            with open(f"audio_{i}.wav", "rb") as f:
                files = {"file": f}
                requests.post(
                    f"{API_URL}/enrollment/session/{session_id}/chunk",
                    files=files
                )
            print(f"Uploaded chunk {i+1}")
        
        # Finalize enrollment (will trigger confirmation)
        finalize_response = requests.post(
            f"{API_URL}/enrollment/session/{session_id}/finalize"
        )
        vector_id = finalize_response.json()["vector_id"]
        print(f"Enrollment finalized - Vector ID: {vector_id}")
        
        # Wait for confirmation on WebSocket
        async for message in ws:
            data = json.loads(message)
            if data.get("type") == "enrollment_confirmed":
                print(f"✓ Confirmation received!")
                print(f"  Phone: {data['data']['phone_number']}")
                print(f"  Chunks: {data['data']['chunks_processed']}")
                break

asyncio.run(main())
```

### Manual Confirmation Sending (Python)

```python
import requests

# Send confirmation manually
response = requests.post(
    "http://localhost:8000/enrollment/confirmation/send",
    params={
        "session_id": "uuid-...",
        "phone_number": "1234567890",
        "vector_id": "vector-uuid-...",
        "chunks_processed": 5,
        "success": True,
        "message": "Enrollment completed successfully!"
    }
)

result = response.json()
print(f"Confirmation ID: {result['confirmation_id']}")
```

### Get Confirmation History

```python
import requests

response = requests.get(
    "http://localhost:8000/enrollment/confirmation/history",
    params={"limit": 50}
)

history = response.json()
print(f"Total confirmations: {history['total']}")

for conf in history["confirmations"]:
    print(f"  {conf['confirmation_id']}: {conf['phone_number']}")
```

## Testing

Run the included test suite:

```bash
python test_enrollment_confirmation.py
```

This will test:
1. WebSocket connection
2. Session creation
3. Client registration
4. Confirmation sending
5. Message delivery
6. Confirmation history

## Error Handling

### Common Errors

**"No client registered for session"**
- Ensure client has been registered before finalizing
- Use: `POST /enrollment/session/{session_id}/register-client`

**"Client not in active connections"**
- Client WebSocket connection may have closed
- Re-establish WebSocket connection
- Re-register client with session

**"Failed to send confirmation"**
- Check that connection manager is properly initialized
- Verify WebSocket client is still connected
- Check logs for detailed error messages

## Configuration

The confirmation service is initialized in `main.py`:

```python
# Initialize confirmation service
confirmation_service = get_confirmation_service()
confirmation_service.set_connection_manager(manager)
```

## Security Considerations

1. **Client Validation**: Ensure client_id is from trusted source
2. **Session Validation**: Verify session exists before registering
3. **Phone Number**: Validate phone format before registration
4. **Rate Limiting**: Implement rate limiting on confirmation endpoints
5. **Timeout Management**: Clean up old registrations periodically

## Performance Notes

- Confirmations are sent asynchronously
- No blocking of enrollment finalization
- History stored in memory (consider DB for production)
- Supports concurrent sessions and clients

## Future Enhancements

- [ ] Database storage for confirmation history
- [ ] Confirmation retry mechanism
- [ ] WebSocket session lifecycle events
- [ ] Bulk confirmation sending
- [ ] Confirmation ACK from client
- [ ] Persistence of pending confirmations

## Troubleshooting

### WebSocket Not Receiving Confirmations

1. Check client_id is correct
2. Verify client is still connected
3. Check browser console for connection errors
4. Ensure registration happened before finalization
5. Check server logs for errors

### Missing Confirmation History

1. Confirmations stored only in memory during session
2. Restart clears history (normal)
3. For persistence, enable database storage
4. Use `/enrollment/confirmation/history` endpoint

### Performance Issues

1. Check number of concurrent sessions
2. Monitor WebSocket connection count
3. Clear old sessions: `POST /enrollment/cleanup`
4. Review logs for bottlenecks

## Related Documentation

- [Enrollment Service Guide](ENROLLMENT_SERVICE_GUIDE.md)
- [WebSocket Architecture](WEBSOCKET_ARCHITECTURE_DIAGRAMS.md)
- [API Reference](EMBEDDING_OPERATIONS_API.md)
