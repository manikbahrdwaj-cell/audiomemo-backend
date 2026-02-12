# WebSocket Implementation Guide - Complete System

**Status**: ✅ COMPLETE  
**Date**: February 12, 2026  
**Version**: 1.0.0

---

## 📋 Overview

This guide documents the complete WebSocket-based system for the Voice Biometric Authentication application. The system enables real-time audio streaming between the React frontend and the backend processing engines.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     React Frontend                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  WebSocket Service (websocketService.js)                │ │
│  │  - Connection management                                │ │
│  │  - Message handling                                     │ │
│  │  - Automatic reconnection                              │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │ WebSocket Connection
                       │ (ws://localhost:8001)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│          Node.js WebSocket Server (app.js)                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  WebSocketAudioHandler                                  │ │
│  │  - Client connection management                         │ │
│  │  - Session management                                   │ │
│  │  - Audio buffer accumulation                            │ │
│  │  - Message routing                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                       │                                       │
│  ┌──────────────────┴──────────────────────────────────────┐ │
│  │  Session Manager (session-manager.js)                   │ │
│  │  - Session creation/deletion                            │ │
│  │  - Audio buffer management                              │ │
│  │  - Session persistence (optional)                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP POST (multipart/form-data)
                       │ (http://localhost:8000)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (main.py)                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Endpoints:                                             │ │
│  │  - POST /enroll  - Register voice                       │ │
│  │  - POST /verify  - Authenticate voice                   │ │
│  │  - GET /check    - Check enrollment                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                       │                                       │
│  ┌──────────────────┴──────────────────────────────────────┐ │
│  │  Voice Processing Pipeline                              │ │
│  │  1. Generate embedding (ECAPA-TDNN)                     │ │
│  │  2. Store/retrieve from MongoDB                         │ │
│  │  3. Calculate similarity scores                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Node.js dependencies
cd reactapp/backend
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start All Servers

**Option A: Unified Launcher (Recommended)**
```bash
cd reactapp/backend
python start_all_servers.py
```

**Option B: Manual Start (Separate Terminals)**

Terminal 1 - FastAPI Backend:
```bash
cd reactapp/backend
python run.py
# Listens on http://localhost:8000
```

Terminal 2 - WebSocket Server:
```bash
cd reactapp/backend
npm start
# Listens on ws://localhost:8001
```

Terminal 3 - React Frontend:
```bash
cd reactapp/frontend
npm start
# Listens on http://localhost:3000
```

### 3. Verify Installation

- **FastAPI Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/
- **WebSocket Test**: Use the testing console in the app

---

## 📁 File Structure

### Backend Files

```
reactapp/backend/
├── app.js                           # WebSocket server entry point
├── websocket-handler.js             # WebSocket server implementation (1200+ lines)
├── session-manager.js               # Session management (547 lines)
├── start_all_servers.py             # Unified server launcher
├── test-websocket-integration.js    # Integration test suite
├── main.py                          # FastAPI backend
├── voice_embedding.py               # ECAPA-TDNN embedding
├── database.py                      # MongoDB operations
├── .env.example                     # Configuration template
└── package.json                     # Node.js dependencies
```

### Frontend Files (WebSocket Client)

```
reactapp/frontend/src/
├── services/
│   ├── websocketService.js          # WebSocket client service
│   └── api.js                       # HTTP API client
├── hooks/
│   └── useWebSocket.js              # React hooks
├── context/
│   └── WebSocketProvider.js         # React context provider
└── components/
    ├── EnrollmentPage.js            # Enrollment UI
    └── VerificationPage.js          # Verification UI
```

---

## 🔌 WebSocket Protocol

### Message Types

#### Server → Client Messages

**1. Connection Acknowledgment**
```json
{
  "type": "connection",
  "clientId": "client_1234567890_123",
  "message": "Connected to WebSocket server",
  "timestamp": 1707734400000
}
```

**2. Session Initialized**
```json
{
  "type": "initialized",
  "userId": "user123",
  "action": "enroll",
  "message": "Session initialized for enroll",
  "timestamp": 1707734400000
}
```

**3. Enrollment Started**
```json
{
  "type": "enrollment-started",
  "message": "Ready to receive audio for enrollment",
  "instructions": "Please speak your enrollment phrase",
  "timestamp": 1707734400000
}
```

**4. Verification Started**
```json
{
  "type": "verification-started",
  "message": "Ready to receive audio for verification",
  "instructions": "Please speak to verify your identity",
  "timestamp": 1707734400000
}
```

**5. Audio Received**
```json
{
  "type": "audio-received",
  "bytesReceived": 16384,
  "totalBytes": 32768,
  "chunkCount": 2,
  "timestamp": 1707734400000
}
```

**6. Processing**
```json
{
  "type": "processing",
  "message": "Processing audio...",
  "audioSize": 32768,
  "timestamp": 1707734400000
}
```

**7. Result - Success**
```json
{
  "type": "result",
  "action": "verify",
  "success": true,
  "data": {
    "success": true,
    "phone_number": "user123",
    "similarity_score": 0.92,
    "is_match": true,
    "threshold": 0.75
  },
  "message": "Voice verified successfully",
  "timestamp": 1707734400000
}
```

**8. Result - Enrollment**
```json
{
  "type": "result",
  "action": "enroll",
  "success": true,
  "data": {
    "success": true,
    "message": "Voice enrolled successfully",
    "phone_number": "user123",
    "vector_id": "507f1f77bcf86cd799439011"
  },
  "message": "Voice enrolled successfully",
  "timestamp": 1707734400000
}
```

**9. Error**
```json
{
  "type": "error",
  "error": "Processing failed",
  "details": "Phone number not enrolled",
  "timestamp": 1707734400000
}
```

**10. Status**
```json
{
  "type": "status",
  "connected": true,
  "sessionActive": true,
  "sessionData": {
    "userId": "user123",
    "action": "verify",
    "language": "en",
    "createdAt": 1707734400000,
    "expiresAt": 1707735200000
  },
  "audioStats": {
    "bufferSize": 32768,
    "chunkCount": 2
  },
  "timestamp": 1707734400000
}
```

**11. Pong**
```json
{
  "type": "pong",
  "timestamp": 1707734400000
}
```

#### Client → Server Messages

**1. Initialize Session**
```json
{
  "type": "init",
  "userId": "user123",
  "action": "enroll",
  "language": "en"
}
```

**2. Start Enrollment**
```json
{
  "type": "start-enrollment"
}
```

**3. Start Verification**
```json
{
  "type": "start-verification",
  "userId": "user123"
}
```

**4. Audio Data**
Binary PCM 16-bit audio data sent as buffer

**5. Stop Audio Processing**
```json
{
  "type": "stop-audio"
}
```

**6. Get Status**
```json
{
  "type": "get-status"
}
```

**7. Ping**
```json
{
  "type": "ping"
}
```

---

## 💻 Usage Examples

### JavaScript/Node.js

```javascript
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8001');

ws.on('open', () => {
    console.log('Connected');
    
    // Initialize session
    ws.send(JSON.stringify({
        type: 'init',
        userId: 'user123',
        action: 'enroll',
        language: 'en'
    }));
});

ws.on('message', (data) => {
    const message = JSON.parse(data);
    
    if (message.type === 'initialized') {
        console.log('Session initialized');
        
        // Start enrollment
        ws.send(JSON.stringify({
            type: 'start-enrollment'
        }));
    }
    
    if (message.type === 'enrollment-started') {
        console.log('Ready for audio');
        
        // Send audio data (binary)
        const audioBuffer = Buffer.from([...]);
        ws.send(audioBuffer);
    }
    
    if (message.type === 'result') {
        console.log('Result:', message.data);
    }
});

ws.on('error', (error) => {
    console.error('WebSocket error:', error);
});
```

### React Component

```javascript
import { useWebSocket } from '../hooks/useWebSocket';
import { useEnrollment } from '../hooks/useWebSocket';

function EnrollmentComponent() {
    const { connected } = useWebSocket();
    const { startRecording, stopRecording, result, isLoading } = useEnrollment('user123', 'en');
    
    return (
        <div>
            <p>Connected: {connected ? '✓' : '✗'}</p>
            <button onClick={startRecording} disabled={!connected || isLoading}>
                Start Recording
            </button>
            <button onClick={stopRecording} disabled={!connected || isLoading}>
                Stop Recording
            </button>
            {result && <p>Result: {result.message}</p>}
        </div>
    );
}
```

---

## 🔧 Configuration

### Environment Variables (.env)

```env
# WebSocket Server
WS_PORT=8001                                    # WebSocket server port
BACKEND_API_URL=http://localhost:8000         # FastAPI backend URL
NODE_ENV=development                          # development|production

# Optional
LOG_LEVEL=info                                # Logging level
SESSION_TIMEOUT=1800000                       # Session timeout (30 min)
MAX_SESSIONS=1000                             # Max concurrent sessions
```

### Python Requirements

The Python backend requires these packages (all in requirements.txt):
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `torch` - Deep learning framework
- `torchaudio` - Audio processing
- `speechbrain` - ECAPA-TDNN model
- `pymongo` - MongoDB driver
- `numpy` - Numerical computing
- `scipy` - Scientific computing

---

## 📊 Session Management

### Session Lifecycle

```
1. Client connects to WebSocket
2. Client sends 'init' message
3. Server creates session
4. Client sends 'start-enrollment' or 'start-verification'
5. Client sends audio data (binary chunks)
6. Client sends 'stop-audio'
7. Server processes with FastAPI backend
8. Server sends 'result' message
9. Session expires after timeout (default: 30 minutes)
```

### Session Data

Each session stores:
- `sessionId` - Unique identifier
- `userId` - User identifier
- `action` - 'enroll' or 'verify'
- `language` - Language code
- `createdAt` - Creation timestamp
- `lastActivity` - Last activity timestamp
- `expiresAt` - Expiration timestamp
- `audioBuffer` - Accumulated audio data

---

## 🧪 Testing

### Run Integration Tests

```bash
cd reactapp/backend
npm install
node test-websocket-integration.js
```

**Test Coverage:**
1. ✓ Basic connection
2. ✓ Session initialization
3. ✓ Start enrollment
4. ✓ Audio data reception
5. ✓ Get status
6. ✓ Ping/pong
7. ✓ Audio processing

### Manual Testing

Using WebSocket client in browser console:

```javascript
const ws = new WebSocket('ws://localhost:8001');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'init',
        userId: 'test_user',
        action: 'enroll'
    }));
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    console.log('Received:', msg);
};
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "Cannot find module 'ws'"**
```bash
npm install ws
```

**2. "WebSocket server not responding"**
- Check if server is running: `curl http://localhost:8001`
- Check port 8001 is not in use: `netstat -an | grep 8001`
- Check firewall settings

**3. "Failed to connect to backend API"**
- Ensure FastAPI backend is running: `http://localhost:8000/`
- Check `BACKEND_API_URL` in .env
- Verify no CORS issues

**4. "Session expired"**
- Increase `SESSION_TIMEOUT` in config
- Ensure audio is sent within timeout window

**5. "Audio processing failed"**
- Check audio format is PCM 16-bit
- Verify sample rate is 16kHz
- Ensure phone number is valid
- Check MongoDB connection

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=debug node app.js
```

Check server stats:
```javascript
global.wsHandler.getStats()
```

---

## 📈 Performance Considerations

### Optimization Tips

1. **Buffer Size**: Default 16KB chunks, adjust based on network
2. **Timeout**: Default 30 minutes, adjust for your use case
3. **Session Limit**: Default 1000, monitor memory on high load
4. **Audio Format**: PCM 16-bit 16kHz optimal size/quality tradeoff

### Monitoring

```javascript
// Get real-time stats
setInterval(() => {
    const stats = handler.getStats();
    console.log(`Clients: ${stats.connectedClients}, Sessions: ${stats.activeSessions}`);
}, 30000);
```

---

## 🔒 Security Considerations

### Current Implementation

1. ✓ Connection validation
2. ✓ Session timeout and cleanup
3. ✓ Audio buffer limits
4. ✓ Error rate limiting (implicit)

### Recommended Enhancements

1. Add authentication (JWT tokens)
2. Rate limiting per user
3. Encryption for audio in transit
4. HTTPS/WSS for production
5. Audio validation (silence detection, etc.)

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `NODE_ENV=production`
- [ ] Use `wss://` (secure WebSocket) instead of `ws://`
- [ ] Configure firewall rules
- [ ] Monitor memory usage
- [ ] Set up log aggregation
- [ ] Configure error alerts
- [ ] Backup MongoDB regularly
- [ ] Test failover procedures

### Docker Example

```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

ENV NODE_ENV=production
ENV WS_PORT=8001
ENV BACKEND_API_URL=http://fastapi:8000

CMD ["npm", "start"]
```

---

## 📚 References

### Related Documentation
- [WEBSOCKET_SETUP.md](WEBSOCKET_SETUP.md) - Detailed setup guide
- [SESSION_MANAGER_README.md](SESSION_MANAGER_README.md) - Session management details
- [PHASE_3_2_COMPLETION_REPORT.md](../PHASE_3_2_COMPLETION_REPORT.md) - Frontend WebSocket service
- [APP_ARCHITECTURE.md](../APP_ARCHITECTURE.md) - Complete system architecture

### External Resources
- [ws npm package](https://github.com/websockets/ws)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-12 | Initial implementation complete |

---

## ✅ Checklist

- [x] WebSocket server implementation (websocket-handler.js)
- [x] Session manager integration
- [x] Message protocol definition
- [x] Frontend integration
- [x] Error handling
- [x] Integration tests
- [x] Documentation
- [x] Deployment guide

---

**Status**: Ready for Production  
**Last Updated**: February 12, 2026  
**Maintainer**: Voice Biometric Team
