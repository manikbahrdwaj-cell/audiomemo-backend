# WebSocket Infrastructure Setup - Complete

## Overview
WebSocket support has been successfully added to the Voice Biometric API backend for real-time audio streaming and verification.

## Installation Summary

### Packages Installed
- **websockets** (v12.0) - WebSocket protocol support
- **FastAPI** (v0.104.1) - Already available, includes WebSocket support
- **Uvicorn** (v0.24.0) - Already available, handles WebSocket connections

### Files Modified
1. **requirements.txt** - Added `websockets==12.0`
2. **main.py** - Added WebSocket endpoint and infrastructure

## WebSocket Endpoint

### URL
```
ws://localhost:8000/ws/voice
```

## Connection Manager

The `ConnectionManager` class handles:
- Client connection registration
- Client disconnection cleanup
- Broadcasting messages to all connected clients
- Error handling and logging

## WebSocket Message Types

### Message Format
All WebSocket messages are JSON objects with required `type` field:
```json
{
  "type": "message_type",
  "data": "optional_field",
  "phone_number": "optional_field"
}
```

### Supported Message Types

#### 1. **audio** - Send audio chunk
Send base64-encoded audio data to accumulate in the buffer.

**Request:**
```json
{
  "type": "audio",
  "data": "base64_encoded_audio_bytes"
}
```

**Response:**
```json
{
  "type": "audio_received",
  "size": 2048,
  "status": "ok"
}
```

#### 2. **enroll** - Enroll a voice
Register a new voice identity for the specified phone number.

**Request:**
```json
{
  "type": "enroll",
  "phone_number": "+1234567890"
}
```

**Success Response:**
```json
{
  "type": "enrollment_success",
  "phone_number": "+1234567890",
  "vector_id": "64f8a3c5d2e1b9f4a7c3",
  "message": "Voice enrolled successfully"
}
```

#### 3. **verify** - Verify a voice
Compare accumulated audio against enrolled voice.

**Request:**
```json
{
  "type": "verify",
  "phone_number": "+1234567890"
}
```

**Success Response:**
```json
{
  "type": "verification_result",
  "phone_number": "+1234567890",
  "similarity_score": 0.87,
  "is_match": true,
  "threshold": 0.75
}
```

#### 4. **ping** - Keep-alive message
Maintain connection and check server status.

**Request:**
```json
{
  "type": "ping"
}
```

**Response:**
```json
{
  "type": "pong",
  "status": "alive"
}
```

#### 5. **reset** - Clear audio buffer
Reset the accumulated audio buffer without processing.

**Request:**
```json
{
  "type": "reset"
}
```

**Response:**
```json
{
  "type": "reset_acknowledged",
  "message": "Audio buffer cleared"
}
```

## Error Handling

All errors are returned as JSON:
```json
{
  "type": "error",
  "message": "Error description"
}
```

### Common Errors
- `"phone_number required for verification"`
- `"phone_number required for enrollment"`
- `"Insufficient audio data for enrollment"` (< 1000 bytes)
- `"Insufficient audio data for verification"` (< 1000 bytes)
- `"Phone number [X] not enrolled"`
- `"Unknown message type: [X]"`

## Connection Lifecycle

1. **Connect** - Client connects to `ws://localhost:8000/ws/voice`
2. **Send Audio** - Client sends `audio` messages with base64-encoded chunks
3. **Process** - Client sends either `verify` or `enroll` message
4. **Receive Result** - Server returns `verification_result` or `enrollment_success`
5. **Reset** - Client can reset with `reset` message to start over
6. **Disconnect** - Connection closes, server cleanup occurs

## Frontend Implementation Example (JavaScript)

```javascript
class VoiceBiometricWSClient {
  constructor(url = 'ws://localhost:8000/ws/voice') {
    this.ws = null;
    this.url = url;
    this.audioBuffer = [];
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('Connected to voice WebSocket');
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);
        this.handleMessage(message);
      };
      
      this.ws.onclose = () => {
        console.log('Disconnected from voice WebSocket');
      };
    });
  }

  sendAudioChunk(audioBytes) {
    const base64Audio = btoa(String.fromCharCode(...audioBytes));
    this.ws.send(JSON.stringify({
      type: 'audio',
      data: base64Audio
    }));
  }

  verify(phoneNumber) {
    this.ws.send(JSON.stringify({
      type: 'verify',
      phone_number: phoneNumber
    }));
  }

  enroll(phoneNumber) {
    this.ws.send(JSON.stringify({
      type: 'enroll',
      phone_number: phoneNumber
    }));
  }

  ping() {
    this.ws.send(JSON.stringify({
      type: 'ping'
    }));
  }

  reset() {
    this.ws.send(JSON.stringify({
      type: 'reset'
    }));
  }

  disconnect() {
    this.ws.close();
  }

  handleMessage(message) {
    // Handle based on message type
    switch(message.type) {
      case 'audio_received':
        console.log(`Audio received: ${message.size} bytes`);
        break;
      case 'verification_result':
        console.log(`Match: ${message.is_match}, Score: ${message.similarity_score}`);
        break;
      case 'enrollment_success':
        console.log(`Enrolled with ID: ${message.vector_id}`);
        break;
      case 'error':
        console.error(`Error: ${message.message}`);
        break;
    }
  }
}

// Usage
const client = new VoiceBiometricWSClient();
await client.connect();

// Send audio chunks
const audioBytes = new Uint8Array([...]);
client.sendAudioChunk(audioBytes);

// Verify voice
client.verify('+1234567890');

// Clean up
client.disconnect();
```

## Performance Considerations

1. **Audio Buffer** - Each connection maintains its own audio buffer in memory
2. **Processing** - Embedding generation happens on-demand (verify/enroll)
3. **Concurrency** - Each WebSocket connection is independent
4. **Keep-Alive** - Use `ping` messages if connection is idle for extended periods

## CORS Configuration

WebSocket connections respect the existing CORS configuration:
- Allowed origins: `http://localhost:3000`, `http://127.0.0.1:3000`
- Credentials: Enabled
- Methods/Headers: All allowed

## Security Notes

1. Authentication should be added via headers before production
2. Phone numbers should be validated/sanitized
3. Consider rate limiting for enrollment/verification
4. Audio data should be encrypted in transit (use `wss://` in production)

## Integration with Existing REST Endpoints

The WebSocket endpoint works alongside existing REST endpoints:
- **POST /enroll** - Traditional file upload enrollment
- **POST /verify** - Traditional file upload verification
- **GET /check/{phone_number}** - Check enrollment status

Both REST and WebSocket can be used interchangeably.

## Running the Backend

```bash
# From backend directory
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will support both HTTP and WebSocket connections concurrently.

## Testing WebSocket

### Using wscat (Node.js CLI tool)
```bash
npm install -g wscat
wscat -c ws://localhost:8000/ws/voice
# Then type JSON messages
{"type":"ping"}
```

### Using Python WebSocket client
```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/ws/voice"
    async with websockets.connect(uri) as websocket:
        # Send ping
        await websocket.send(json.dumps({"type": "ping"}))
        
        # Receive response
        response = await websocket.recv()
        print(response)

asyncio.run(test())
```

## Architecture Diagram

```
┌─────────────────┐
│  Frontend App   │
│   (React)       │
└────────┬────────┘
         │
         │ HTTP/WebSocket
         │
         ▼
┌─────────────────────────┐
│   FastAPI Backend       │
├─────────────────────────┤
│  WebSocket Endpoint     │
│  /ws/voice              │
├─────────────────────────┤
│  ConnectionManager      │
├─────────────────────────┤
│  Voice Embedding        │
│  generate_embedding()   │
├─────────────────────────┤
│  MongoDB Database       │
│  Voice vectors storage  │
└─────────────────────────┘
```

## Troubleshooting

### Connection timeout
- Check if backend is running: `http://localhost:8000/`
- Verify CORS origins match frontend URL
- Check firewall rules allowing port 8000

### Audio not being processed
- Ensure audio chunk size > 1000 bytes before verify/enroll
- Verify phone_number field is included in request
- Check server logs for error messages

### High latency
- Reduce audio chunk size for streaming
- Consider message batching
- Monitor server CPU/memory usage

## Next Steps

1. **Frontend Integration** - Update React components to use WebSocket
2. **Real-time UI Updates** - Implement progress indicators
3. **Audio Streaming** - Add incremental audio processing
4. **Error Recovery** - Implement reconnection logic
5. **Performance Testing** - Load test with multiple concurrent connections
