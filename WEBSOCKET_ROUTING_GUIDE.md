# WebSocket Message Routing Infrastructure

## Overview

The WebSocket message routing infrastructure provides a centralized, extensible system for handling real-time voice communication. It implements message validation, routing, rate limiting, and monitoring with a clean separation of concerns.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Client                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                  JSON Message
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI WebSocket Endpoint                      │
│              (/ws/voice)                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                  Message Received
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            WebSocketMessageRouter                           │
│  ┌────────────────┬─────────────┬──────────────────────┐   │
│  │ Route Lookup   │ Validation  │ Rate Limiting        │   │
│  └────────────────┴─────────────┴──────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                    Route Handler
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Event Handlers                                   │
│  - Audio Chunk Handler                                      │
│  - Verification Handler                                     │
│  - Enrollment Handler                                       │
│  - Status Handler                                           │
│  - Control Handlers                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                  Process & Response
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Monitoring & Statistics                             │
│         (WebSocketMonitor)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Message Types

### 1. Audio Messages
**Type**: `"audio"`

Send audio chunks for processing (enrollment/verification).

```json
{
  "type": "audio",
  "data": "<base64-encoded-audio-data>"
}
```

**Properties**:
- Required Fields: `data`
- Max Message Size: 1 MB
- Rate Limit: 100 messages/sec
- Response: Audio chunk acknowledgment with buffer stats

---

### 2. Verification Messages
**Type**: `"verify"`

Initiate voice verification against enrolled identity.

```json
{
  "type": "verify",
  "phone_number": "+1234567890"
}
```

**Properties**:
- Required Fields: `phone_number`
- Rate Limit: 10 messages/sec
- Prerequisites: Audio chunks must be sent first
- Response: Similarity score and match result

---

### 3. Enrollment Messages
**Type**: `"enroll"`

Enroll a new voice identity.

```json
{
  "type": "enroll",
  "phone_number": "+1234567890"
}
```

**Properties**:
- Required Fields: `phone_number`
- Rate Limit: 5 messages/sec
- Prerequisites: Audio chunks must be sent first
- Response: Enrollment confirmation with vector ID

---

### 4. Ping Messages
**Type**: `"ping"`

Keep-alive message to maintain connection.

```json
{
  "type": "ping"
}
```

**Properties**:
- Required Fields: None
- Rate Limit: 1000 messages/sec
- Response: Pong with connection stats

---

### 5. Reset Messages
**Type**: `"reset"`

Clear the audio buffer and reset state.

```json
{
  "type": "reset"
}
```

**Properties**:
- Required Fields: None
- Rate Limit: 10 messages/sec
- Response: Reset acknowledgment

---

### 6. Status Messages
**Type**: `"status"`

Get current connection and buffer status.

```json
{
  "type": "status"
}
```

**Properties**:
- Required Fields: None
- Rate Limit: 10 messages/sec
- Response: Detailed connection status

---

## Response Format

All responses follow a standard format:

```json
{
  "type": "message-type",
  "status": "ok|error",
  "timestamp": "2026-02-14T12:00:00.000Z",
  "data": {},
  "error_type": "error-code",
  "message": "error-description"
}
```

### Success Response Example
```json
{
  "type": "audio_received",
  "status": "ok",
  "timestamp": "2026-02-14T12:00:00.000Z",
  "data": {
    "size": 8192,
    "chunks": 2
  }
}
```

### Error Response Example
```json
{
  "type": "error",
  "status": "error",
  "timestamp": "2026-02-14T12:00:00.000Z",
  "error_type": "rate_limit",
  "message": "Rate limit exceeded: 5 messages per second"
}
```

## Routing System Components

### WebSocketMessageRouter

Core routing engine that manages message dispatch.

```python
from websocket_router import WebSocketMessageRouter

# Get routes info
routes = message_router.get_routes_info()

# Get specific route
route = message_router.get_route("audio")

# Route a message
response = await message_router.route_message(client_id, message)
```

### MessageValidator

Validates messages against route requirements.

```python
from websocket_router import MessageValidator, RouteConfig

validator = MessageValidator()
is_valid, error_msg = validator.validate_message(
    message={"phone_number": "+1234567890"},
    route=route_config
)
```

### RateLimit

Enforces per-client rate limits per message type.

```python
from websocket_router import RateLimit

limiter = RateLimit()
is_allowed, msg = limiter.check_limit(
    client_id="client-123",
    message_type="audio",
    limit=100
)
```

## REST API Endpoints

### 1. Get WebSocket Routes
**Endpoint**: `GET /ws/routes`

Returns information about all registered message routes.

**Response**:
```json
{
  "routes": {
    "audio": {
      "message_type": "audio",
      "requires_auth": false,
      "requires_fields": ["data"],
      "optional_fields": [],
      "max_message_size": 1000000,
      "rate_limit": 100
    },
    "verify": { ... },
    "enroll": { ... }
  },
  "total_routes": 6
}
```

### 2. Get WebSocket Statistics
**Endpoint**: `GET /ws/stats`

Returns real-time WebSocket connection statistics.

**Response**:
```json
{
  "active_connections": 5,
  "connections": [...],
  "aggregate_stats": {
    "total_connections": 50,
    "total_messages": 5000,
    "total_audio_bytes": 10485760,
    "total_verifications": 25,
    "total_enrollments": 10,
    "total_errors": 2
  },
  "health_status": {
    "status": "healthy",
    "active_connections": 5,
    "total_errors": 2
  }
}
```

### 3. Get WebSocket Monitor Data
**Endpoint**: `GET /ws/monitor`

Returns detailed monitoring and historical data.

**Response**:
```json
{
  "active_stats": [...],
  "historical_stats": [...],
  "recent_events": [...],
  "health": { ... }
}
```

### 4. Get WebSocket Health
**Endpoint**: `GET /ws/health`

Returns infrastructure health status.

**Response**:
```json
{
  "status": "healthy|degraded",
  "active_connections": 5,
  "total_errors": 2,
  "health_checks": {
    "active_connections_ok": true,
    "error_rate_ok": true,
    "recent_activity": true
  },
  "timestamp": "2026-02-14T12:00:00.000Z"
}
```

## Configuration

### Route Configuration

Routes are configured in `main.py`:

```python
RouteConfig(
    message_type=MessageType.AUDIO,
    handler=handle_audio,
    requires_fields=["data"],
    optional_fields=[],
    max_message_size=1_000_000,  # 1MB
    rate_limit=100  # 100 messages/sec
)
```

### Environment Variables

WebSocket settings can be configured via environment variables:

```bash
# Connection timeouts
WS_HEARTBEAT_INTERVAL=30        # seconds
WS_HEARTBEAT_TIMEOUT=60         # seconds

# Message sizes
WS_MAX_MESSAGE_SIZE=1048576     # 1MB
WS_MAX_BUFFER_SIZE=10000000     # 10MB
```

## Error Codes

| Error Code | Meaning |
|-----------|---------|
| `validation_error` | Message validation failed |
| `unknown_type` | Unknown message type |
| `rate_limit` | Rate limit exceeded |
| `missing_field` | Required field missing |
| `decode_error` | Failed to decode message data |
| `handler_error` | Error during message handling |
| `no_audio` | No audio in buffer |
| `buffer_overflow` | Audio buffer exceeds size limit |
| `insufficient_audio` | Audio too small for processing |
| `enrollment_error` | Enrollment failed |
| `verification_error` | Verification failed |
| `not_enrolled` | Phone number not enrolled |

## Usage Examples

### Example 1: Complete Enrollment Flow

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/voice');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('Response:', response);
};

// Send audio chunk
ws.send(JSON.stringify({
  type: "audio",
  data: "base64-encoded-audio"
}));

// Wait for acknowledgment, then enroll
setTimeout(() => {
  ws.send(JSON.stringify({
    type: "enroll",
    phone_number: "+1234567890"
  }));
}, 1000);
```

### Example 2: Verification with Keep-Alive

```python
import asyncio
import websockets
import json
import base64

async def verify_voice(phone_number):
    uri = "ws://localhost:8000/ws/voice"
    
    async with websockets.connect(uri) as websocket:
        # Send audio chunk
        with open('sample.wav', 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode()
        
        await websocket.send(json.dumps({
            "type": "audio",
            "data": audio_data
        }))
        
        response = await websocket.recv()
        print("Audio received:", json.loads(response))
        
        # Keep connection alive
        await websocket.send(json.dumps({"type": "ping"}))
        response = await websocket.recv()
        print("Pong:", json.loads(response))
        
        # Verify
        await websocket.send(json.dumps({
            "type": "verify",
            "phone_number": phone_number
        }))
        response = await websocket.recv()
        print("Verification result:", json.loads(response))

# Run
asyncio.run(verify_voice("+1234567890"))
```

## Monitoring & Debugging

### Check Active Connections
```bash
curl http://localhost:8000/ws/stats
```

### Monitor Message Routing
```bash
curl http://localhost:8000/ws/monitor
```

### Check Infrastructure Health
```bash
curl http://localhost:8000/ws/health
```

### Get Route Configuration
```bash
curl http://localhost:8000/ws/routes
```

## Adding New Message Types

To add a new message type:

1. Add to `MessageType` enum in `websocket_router.py`:
```python
class MessageType(Enum):
    NEW_TYPE = "new_type"
```

2. Create handler in `websocket_events.py`:
```python
async def handle_new_type(self, connection: ClientConnection, message: Dict[str, Any]):
    # Implementation
    return WebSocketMessageBuilder.create_success_message("new_type_response", data)
```

3. Register route in `main.py`:
```python
RouteConfig(
    message_type=MessageType.NEW_TYPE,
    handler=handle_new_type,
    requires_fields=["field1", "field2"],
    optional_fields=[],
    rate_limit=10
)
```

4. Update WebSocket endpoint message routing switch statement

## Performance Considerations

1. **Rate Limiting**: Configure limits based on expected load
2. **Message Size**: Keep messages under size limits
3. **Audio Buffer**: Monitor buffer usage in `/ws/monitor`
4. **Connections**: Monitor active connections in `/ws/stats`
5. **Cleanup**: Historical stats automatically cleaned up (7-day retention)

## Troubleshooting

### Connection Drops
- Check `/ws/health` endpoint
- Review recent events in `/ws/monitor`
- Verify rate limits aren't being exceeded

### Message Validation Errors
- Ensure required fields are included
- Check message type spelling (case-sensitive)
- Verify field data types

### Rate Limit Issues
- Check configured limits in route config
- Space out messages to stay under limits
- Use ping messages strategically to maintain connection

### Audio Processing Issues
- Ensure minimum audio size (1000 bytes)
- Verify phone number is enrolled before verify
- Check buffer size in status endpoint
