"""
WebSocket Infrastructure Documentation
Complete guide for WebSocket implementation and usage
"""

# WEBSOCKET INFRASTRUCTURE SETUP DOCUMENTATION

## Overview
The WebSocket infrastructure provides real-time, bidirectional communication between the frontend and backend for voice biometric operations (enrollment and verification).

## Architecture

### Components

1. **websocket_handler.py**
   - `ConnectionManager`: Manages active WebSocket connections
   - `ClientConnection`: Represents individual client connections
   - `WebSocketMessageBuilder`: Helper for creating formatted messages
   - `WebSocketMessageValidator`: Validates incoming messages

2. **websocket_events.py**
   - `AudioBuffer`: Accumulates audio chunks per connection
   - `WebSocketEventHandler`: Processes and routes WebSocket events
   - `event_handler`: Global event handler instance

3. **websocket_config.py**
   - `WebSocketConfig`: Centralized configuration
   - `MessageTypeRegistry`: Registry of supported message types
   - `ResponseTypeRegistry`: Registry of response types

4. **websocket_monitor.py**
   - `WebSocketMonitor`: Tracks performance metrics
   - `ConnectionStats`: Per-connection statistics
   - `monitor`: Global monitor instance


## Supported Message Types

### 1. Audio Chunk Message
**Type**: `audio`
**Purpose**: Send audio data to the server

```json
{
  "type": "audio",
  "data": "base64_encoded_audio_bytes"
}
```

### 2. Enrollment Request
**Type**: `enroll`
**Purpose**: Enroll a new voice identity

```json
{
  "type": "enroll",
  "phone_number": "+1234567890"
}
```

**Response** (on success):
```json
{
  "type": "enrollment_success",
  "status": "ok",
  "timestamp": "2024-02-14T10:30:00",
  "data": {
    "phone_number": "+1234567890",
    "vector_id": "uuid-string",
    "message": "Voice enrolled successfully"
  }
}
```

### 3. Verification Request
**Type**: `verify`
**Purpose**: Verify voice against enrolled identity

```json
{
  "type": "verify",
  "phone_number": "+1234567890"
}
```

**Response** (on success):
```json
{
  "type": "verification_result",
  "status": "ok",
  "timestamp": "2024-02-14T10:30:00",
  "data": {
    "phone_number": "+1234567890",
    "similarity_score": 0.87,
    "is_match": true,
    "threshold": 0.75,
    "confidence": 87.0
  }
}
```

### 4. Keep-Alive (Ping)
**Type**: `ping`
**Purpose**: Keep connection alive

```json
{
  "type": "ping"
}
```

**Response**:
```json
{
  "type": "pong",
  "status": "ok",
  "timestamp": "2024-02-14T10:30:00",
  "data": {
    "connection_id": "uuid-string",
    "uptime": 125.5
  }
}
```

### 5. Reset Buffer
**Type**: `reset`
**Purpose**: Clear accumulated audio buffer

```json
{
  "type": "reset"
}
```

### 6. Connection Status
**Type**: `status`
**Purpose**: Get current connection status

```json
{
  "type": "status"
}
```

**Response**:
```json
{
  "type": "status",
  "status": "ok",
  "timestamp": "2024-02-14T10:30:00",
  "data": {
    "connection_id": "uuid-string",
    "state": "idle",
    "connected_at": "2024-02-14T10:25:00",
    "uptime_seconds": 300,
    "last_heartbeat": "2024-02-14T10:30:00",
    "buffer": {
      "size_bytes": 0,
      "chunks_received": 0,
      "is_valid": false,
      "created_at": "2024-02-14T10:25:00"
    }
  }
}
```

## Error Response Format

```json
{
  "type": "error",
  "status": "error",
  "timestamp": "2024-02-14T10:30:00",
  "error_type": "insufficient_audio",
  "message": "Audio data too small (min: 1000 bytes)"
}
```

### Common Error Types
- `validation_error`: Message structure is invalid
- `insufficient_audio`: Audio buffer too small
- `not_enrolled`: Phone number not enrolled
- `no_audio`: No audio available
- `decode_error`: Failed to decode data
- `buffer_overflow`: Audio buffer exceeded
- `enrollment_error`: Enrollment failed
- `verification_error`: Verification failed


## Frontend Integration Example

### JavaScript/React
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/voice');

// Connection established
ws.onopen = () => {
  console.log('Connected to WebSocket');
  // Send keep-alive ping every 30 seconds
  setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }));
  }, 30000);
};

// Send audio chunk
function sendAudioChunk(audioBytes) {
  const base64Data = btoa(String.fromCharCode(...new Uint8Array(audioBytes)));
  ws.send(JSON.stringify({
    type: 'audio',
    data: base64Data
  }));
}

// Verify voice
function verifyVoice(phoneNumber) {
  ws.send(JSON.stringify({
    type: 'verify',
    phone_number: phoneNumber
  }));
}

// Enroll voice
function enrollVoice(phoneNumber) {
  ws.send(JSON.stringify({
    type: 'enroll',
    phone_number: phoneNumber
  }));
}

// Handle responses
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch(message.type) {
    case 'audio_received':
      console.log('Audio chunk received:', message.data);
      break;
    case 'verification_result':
      console.log('Verification result:', message.data);
      break;
    case 'enrollment_success':
      console.log('Enrollment complete:', message.data);
      break;
    case 'error':
      console.error('Error:', message.message);
      break;
    case 'pong':
      console.log('Connection alive');
      break;
  }
};

// Error handling
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket connection closed');
};
```


## Configuration

### Environment Variables
```bash
# Heartbeat settings (in seconds)
WS_HEARTBEAT_INTERVAL=30
WS_HEARTBEAT_TIMEOUT=60

# Message and buffer limits (in bytes)
WS_MAX_MESSAGE_SIZE=1048576  # 1MB
WS_MAX_BUFFER_SIZE=10000000  # 10MB
```

### Configuration File
Edit `websocket_config.py` to customize:
- Connection timeouts
- Heartbeat intervals
- Buffer sizes
- Similarity threshold
- Rate limiting


## Monitoring and Statistics

### Get Connection Stats
```python
from websocket_monitor import monitor

# Get stats for specific connection
stats = monitor.get_connection_stats(connection_id)

# Get all active connections
all_stats = monitor.get_all_active_stats()

# Get aggregate statistics
aggregate = monitor.get_aggregate_stats()

# Get health status
health = monitor.get_health_status()
```

### MonitoringEndpoint
Add to `main.py`:
```python
@app.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket statistics"""
    return {
        "connections": manager.get_connection_count(),
        "stats": event_handler.event_handler.get_all_active_stats(),
        "health": monitor.get_health_status()
    }
```


## Connection States

- `IDLE`: Waiting for input
- `PROCESSING`: Processing audio/verification/enrollment
- `CONNECTED`: Initially connected
- `DISCONNECTED`: Disconnected
- `ERROR`: Error state


## Audio Processing Workflow

### Enrollment Flow
1. Client connects to WebSocket
2. Client sends audio chunks (type: `audio`)
3. Server accumulates chunks in AudioBuffer
4. Client sends enrollment request (type: `enroll`, phone_number)
5. Server generates embedding from accumulated audio
6. Server stores embedding in MongoDB
7. Server responds with success message and vector_id

### Verification Flow
1. Client connects to WebSocket
2. Client sends audio chunks (type: `audio`)
3. Server accumulates chunks in AudioBuffer
4. Client sends verification request (type: `verify`, phone_number)
5. Server generates embedding from accumulated audio
6. Server compares against stored embedding
7. Server returns similarity score and match result


## Best Practices

### Client Side
1. Implement reconnection logic with exponential backoff
2. Send heartbeat pings to keep connection alive
3. Handle all error responses appropriately
4. Clear audio buffer between operations
5. Set reasonable timeout for verification/enrollment

### Server Side
1. Monitor connection health metrics
2. Clean up stale connections
3. Implement rate limiting if needed
4. Log all significant events
5. Track performance metrics

### Network
1. Use WSS (WebSocket Secure) in production
2. Implement compression for large audio chunks
3. Optimize chunk size (50KB recommended)
4. Handle network failures gracefully
5. Implement connection pooling


## Performance Metrics

### Key Metrics Tracked
- Messages sent/received
- Audio chunks received
- Total audio bytes
- Verification/enrollment operations
- Error counts and types
- Connection duration
- Messages per second

### Accessing Metrics
```python
from websocket_monitor import monitor

# Get specific connection stats
stats = monitor.get_connection_stats(connection_id)
print(f"Duration: {stats['duration_seconds']}s")
print(f"Messages/sec: {stats['messages_per_second']}")
print(f"Audio: {stats['audio_mb']}MB")

# Get aggregate stats
aggregate = monitor.get_aggregate_stats()
print(f"Active: {aggregate['active_connections']}")
print(f"Total errors: {aggregate['total_errors']}")
```

## Troubleshooting

### Connection Times Out
- Check heartbeat settings
- Ensure network connectivity
- Check firewall rules

### Audio Processing Fails
- Verify audio format and size
- Check audio buffer size limits
- Enable debug logging

### High Error Rate
- Monitor network conditions
- Check server resources
- Review error logs

### Memory Leaks
- Ensure disconnect cleanup
- Monitor buffer sizes
- Use monitor.cleanup_old_historical()

## Future Enhancements

1. Compression support (gzip)
2. Authentication/authorization
3. Rate limiting per connection
4. Streaming video alongside audio
5. Audio quality detection
6. Real-time progress indicators
7. Message queuing
8. Connection pooling
9. Multi-room support
10. Client-side caching


## References

- WebSocket RFC: https://tools.ietf.org/html/rfc6455
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
- Message Format: JSON (RFC 7159)
- Audio Format: Base64-encoded WAV/PCM


---
Created: 2024-02-14
Last Updated: 2024-02-14
Version: 1.0.0
