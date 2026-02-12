# WebSocket Handler Implementation - Step 1.2

## Overview

The WebSocket Handler provides real-time, bidirectional communication between the frontend and backend for voice biometric authentication. It handles audio streaming, enrollment, and verification in real-time.

## Architecture

```
Frontend (React)
    ↓
WebSocket Client (websocketClient.js)
    ↓
WebSocket Server (websocket-handler.js - Node.js)
    ↓
FastAPI Backend (main.py)
    ↓
Voice Embedding & Database
```

## Files Created

### 1. **websocket-handler.js**
   - Node.js WebSocket server using `ws` library
   - Handles real-time audio streaming
   - Manages enrollment and verification processes
   - Location: `reactapp/backend/websocket-handler.js`

### 2. **websocketClient.js**
   - Frontend WebSocket client utility
   - Manages microphone access and audio capture
   - Handles message sending/receiving
   - Location: `reactapp/frontend/src/services/websocketClient.js`

### 3. **package.json**
   - Node.js dependencies configuration
   - Location: `reactapp/backend/package.json`

### 4. **.env.example**
   - Environment configuration template
   - Location: `reactapp/backend/.env.example`

## Installation

### 1. Install Node.js Dependencies

```bash
cd reactapp/backend
npm install
```

### 2. Create Environment File

```bash
copy .env.example .env
```

Configure as needed:
```
WS_PORT=8001
BACKEND_API_URL=http://localhost:8000
NODE_ENV=development
```

## Running the WebSocket Server

### Development Mode (with auto-reload)
```bash
cd reactapp/backend
npm run dev
```

### Production Mode
```bash
cd reactapp/backend
npm start
```

The server will start on `ws://localhost:8001`

## API Protocol

### Server → Client Messages

#### Connection Acknowledgment
```json
{
  "type": "connection",
  "clientId": "client_1234567890_abc123def",
  "message": "Connected to WebSocket server",
  "timestamp": 1676543210000
}
```

#### Initialization Response
```json
{
  "type": "initialized",
  "userId": "user123",
  "action": "enroll",
  "message": "Session initialized for enroll",
  "timestamp": 1676543210000
}
```

#### Enrollment Started
```json
{
  "type": "enrollment-started",
  "message": "Ready to receive audio for enrollment",
  "instructions": "Please speak your enrollment phrase",
  "timestamp": 1676543210000
}
```

#### Verification Started
```json
{
  "type": "verification-started",
  "message": "Ready to receive audio for verification",
  "instructions": "Please speak to verify your identity",
  "timestamp": 1676543210000
}
```

#### Audio Received
```json
{
  "type": "audio-received",
  "bytesReceived": 32768,
  "chunkCount": 8,
  "timestamp": 1676543210000
}
```

#### Processing
```json
{
  "type": "processing",
  "message": "Processing audio...",
  "timestamp": 1676543210000
}
```

#### Result
```json
{
  "type": "result",
  "action": "verify",
  "success": true,
  "data": {
    "verified": true,
    "confidence": 0.95,
    "user_id": "user123"
  },
  "message": "Voice verified successfully",
  "timestamp": 1676543210000
}
```

#### Error
```json
{
  "type": "error",
  "error": "No audio received",
  "details": "Audio buffer is empty",
  "timestamp": 1676543210000
}
```

#### Status
```json
{
  "type": "status",
  "sessionData": {
    "userId": "user123",
    "action": "verify",
    "language": "en",
    "durationMs": 5000
  },
  "audioStats": {
    "bufferSize": 32768,
    "chunkCount": 8
  },
  "timestamp": 1676543210000
}
```

### Client → Server Messages

#### Initialize Session
```json
{
  "type": "init",
  "userId": "user123",
  "action": "enroll",
  "language": "en"
}
```

#### Start Enrollment
```json
{
  "type": "start-enrollment"
}
```

#### Start Verification
```json
{
  "type": "start-verification",
  "userId": "user123"
}
```

#### Audio Data
Binary audio data (PCM 16-bit) sent directly as binary frames

#### Stop Audio Processing
```json
{
  "type": "stop-audio"
}
```

#### Get Status
```json
{
  "type": "get-status"
}
```

#### Ping
```json
{
  "type": "ping"
}
```

## Frontend Usage

### Basic Setup in React Component

```javascript
import { useState, useEffect } from 'react';
import VoiceWebSocketClient from '../services/websocketClient';

export function EnrollmentPage() {
  const [wsClient, setWsClient] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const client = new VoiceWebSocketClient('ws://localhost:8001');
    
    // Set up event handlers
    client.onConnect = () => {
      console.log('Connected to WebSocket server');
    };

    client.onError = (error) => {
      console.error('WebSocket error:', error);
    };

    client.onResult = (message) => {
      console.log('Result:', message);
      setResult(message);
      setIsRecording(false);
    };

    // Connect to server
    client.connect().catch(console.error);

    setWsClient(client);

    return () => {
      client.disconnect();
    };
  }, []);

  const handleEnroll = async () => {
    if (!wsClient) return;

    // Initialize session
    wsClient.initialize('user123', 'enroll', 'en');

    // Start enrollment
    wsClient.startEnrollment();

    // Request microphone and start recording
    await wsClient.startAudioCapture();
    setIsRecording(true);
  };

  const handleStopRecording = async () => {
    if (wsClient) {
      await wsClient.stopAudioCapture();
      setIsRecording(false);
    }
  };

  return (
    <div>
      <button 
        onClick={handleEnroll}
        disabled={isRecording}
      >
        Start Enrollment
      </button>

      <button 
        onClick={handleStopRecording}
        disabled={!isRecording}
      >
        Stop Recording
      </button>

      {result && (
        <div>
          <h3>Result:</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
```

## Health Check

```bash
# Check server health
curl http://localhost:8001/health

# Response:
# {
#   "status": "healthy",
#   "server": "WebSocket Handler",
#   "timestamp": "2024-02-12T10:30:45.123Z",
#   "activeConnections": 2
# }
```

## Statistics Endpoint

```bash
# Get active connections and stats
curl http://localhost:8001/stats

# Response:
# {
#   "activeConnections": 2,
#   "totalConnected": 2,
#   "connections": [
#     {
#       "clientId": "client_1234567890_abc123def",
#       "userId": "user123",
#       "action": "enroll",
#       "audioBufferSize": 32768,
#       "connectedSince": 1676543210000
#     }
#   ]
# }
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_PORT` | 8001 | WebSocket server port |
| `BACKEND_API_URL` | http://localhost:8000 | FastAPI backend URL |
| `NODE_ENV` | development | Environment mode |

## Error Handling

The WebSocket handler includes comprehensive error handling:

- **Invalid messages**: Returns error with details
- **Audio size exceeded**: Returns error if audio exceeds 5MB
- **Processing failures**: Returns detailed error messages
- **Connection issues**: Automatically handles disconnections

## Performance Considerations

- **Chunk size**: 4096 bytes (configurable in code)
- **Max audio size**: 5MB (configurable)
- **Timeout**: 30 seconds for backend API calls
- **Connection limit**: Handled by Node.js and system

## Logging

The server logs:
- Connection/disconnection events
- Session initialization
- Audio processing
- Errors and exceptions

Enable detailed logging by setting `LOG_LEVEL=debug` in `.env`

## Troubleshooting

### Connection Refused
```
Error: Connection refused on ws://localhost:8001
```
**Solution**: Ensure WebSocket server is running with `npm start`

### No Audio Received
```
Error: Audio buffer is empty
```
**Solution**: 
- Allow microphone access
- Check browser microphone permissions
- Verify audio capture is running

### Backend API Not Responding
```
Error during enrollment/verification
```
**Solution**:
- Verify FastAPI server is running on `http://localhost:8000`
- Check `BACKEND_API_URL` in `.env`
- Check FastAPI logs for errors

### CORS Issues
The WebSocket protocol doesn't use CORS, but if frontend is on different origin, ensure proper WebSocket URL configuration.

## Next Steps

- **Step 1.3**: Update frontend components to use WebSocket client
- **Step 1.4**: Implement real-time audio visualization
- **Step 1.5**: Add error recovery and automatic reconnection

## Security Considerations

- Add authentication/authorization in production
- Implement rate limiting on enrollment/verification
- Use WSS (WebSocket Secure) with TLS certificates
- Validate audio data and MIME types
- Implement CORS/CSP policies
- Add user session validation

## Dependencies

- `express`: 4.18.2 - HTTP server framework
- `ws`: 8.14.2 - WebSocket implementation
- `axios`: 1.6.2 - HTTP client for backend API
- `dotenv`: 16.3.1 - Environment variable management
- `nodemon`: 3.0.2 (dev) - Auto-reload during development
