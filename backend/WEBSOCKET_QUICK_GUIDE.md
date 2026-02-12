# WebSocket Implementation - Quick Reference

**Updated**: February 12, 2026  
**Status**: ✅ Complete and Ready to Use

---

## 🚀 Start Here - 5 Minute Setup

### 1. Install Dependencies
```bash
cd reactapp/backend
npm install
pip install -r requirements.txt
```

### 2. Start Servers
```bash
python start_all_servers.py
```

### 3. Verify It Works
- FastAPI: http://localhost:8000/docs
- WebSocket: ws://localhost:8001
- Frontend: http://localhost:3000

---

## 📦 What You Get

### WebSocket Server (1200+ lines)
- ✅ Real-time audio streaming
- ✅ Session management
- ✅ Automatic reconnection
- ✅ Error handling
- ✅ Message routing
- ✅ Status monitoring

### Key Features
```javascript
// Handle all WebSocket operations
const handler = new WebSocketAudioHandler(8001);
await handler.start();

// Automatic features:
// ✓ Client connection tracking
// ✓ Session creation/expiration
// ✓ Audio buffer management
// ✓ FastAPI integration
// ✓ Error recovery
```

---

## 💬 Message Quick Reference

### Client Sends

| Type | Usage | Example |
|------|-------|---------|
| `init` | Start session | `{type: 'init', userId: 'user123', action: 'enroll'}` |
| `start-enrollment` | Begin enrollment | `{type: 'start-enrollment'}` |
| `start-verification` | Begin verification | `{type: 'start-verification'}` |
| `audio` | Send audio data | `<binary buffer>` |
| `stop-audio` | Process audio | `{type: 'stop-audio'}` |
| `get-status` | Check status | `{type: 'get-status'}` |
| `ping` | Test connection | `{type: 'ping'}` |

### Server Sends

| Type | Meaning | Contains |
|------|---------|----------|
| `connection` | Client connected | clientId, timestamp |
| `initialized` | Session created | userId, action |
| `enrollment-started` | Ready for audio | message, instructions |
| `verification-started` | Ready for audio | message, instructions |
| `audio-received` | Audio accepted | bytesReceived, chunkCount |
| `processing` | Processing started | message, audioSize |
| `result` | Process complete | success, data, message |
| `error` | Operation failed | error, details |
| `status` | Session info | sessionData, audioStats |
| `pong` | Connection alive | timestamp |

---

## 🔄 Complete Workflow Example

### Browser Console
```javascript
// 1. Connect
const ws = new WebSocket('ws://localhost:8001');

// 2. Handle connection
ws.onopen = () => {
    // Send init
    ws.send(JSON.stringify({
        type: 'init',
        userId: 'john@example.com',
        action: 'enroll'
    }));
};

// 3. Handle responses
ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data);
    
    // Wait for initialization
    if (msg.type === 'initialized') {
        ws.send(JSON.stringify({ type: 'start-enrollment' }));
    }
    
    // When ready, send audio
    if (msg.type === 'enrollment-started') {
        const audioBlob = await recordAudio(); // Your recording function
        const buffer = await audioBlob.arrayBuffer();
        ws.send(buffer);
    }
    
    // Get result
    if (msg.type === 'result') {
        console.log('Success:', msg.data);
        ws.close();
    }
    
    // Handle errors
    if (msg.type === 'error') {
        console.error('Error:', msg.error, msg.details);
    }
};

// 4. Send stop signal
function finishRecording() {
    ws.send(JSON.stringify({ type: 'stop-audio' }));
}
```

### React Component
```javascript
import { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useEnrollment } from '../hooks/useWebSocket';

export function VoiceEnrollment() {
    const { connected } = useWebSocket();
    const { 
        startRecording, 
        stopRecording, 
        result, 
        isLoading, 
        error 
    } = useEnrollment('user@example.com', 'en');

    return (
        <div>
            <h2>Voice Enrollment</h2>
            <p>Status: {connected ? '✓ Connected' : '✗ Disconnected'}</p>
            
            <button 
                onClick={startRecording} 
                disabled={!connected || isLoading}
            >
                🎤 Start Recording
            </button>
            
            <button 
                onClick={stopRecording} 
                disabled={isLoading}
            >
                ⏹ Stop Recording
            </button>
            
            {isLoading && <p>Processing...</p>}
            {error && <p style={{color: 'red'}}>Error: {error}</p>}
            {result && (
                <div>
                    <p>Success! Video ID: {result.vector_id}</p>
                </div>
            )}
        </div>
    );
}
```

---

## 🔧 Configuration

### Environment File (.env)
```env
WS_PORT=8001
BACKEND_API_URL=http://localhost:8000
NODE_ENV=development
LOG_LEVEL=info
```

### Session Timeout
Default: 30 minutes
Adjust in WebSocketAudioHandler constructor:
```javascript
const handler = new WebSocketAudioHandler(8001, {
    sessionTimeout: 60 * 60 * 1000  // 1 hour
});
```

---

## 🧪 Testing

### Quick Test
```bash
cd reactapp/backend
node test-websocket-integration.js
```

Expected output:
```
✓ Connection
✓ Initialization
✓ Start Enrollment
✓ Audio Reception
✓ Get Status
✓ Ping/Pong
✓ Stop Audio
```

---

## 📊 File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app.js` | 80 | WebSocket server entry point |
| `websocket-handler.js` | 1200+ | Main WebSocket server implementation |
| `session-manager.js` | 547 | Session lifecycle management |
| `start_all_servers.py` | 200+ | Unified server launcher |
| `test-websocket-integration.js` | 600+ | Integration test suite |
| `WEBSOCKET_IMPLEMENTATION_COMPLETE.md` | Full guide | Complete documentation |

---

## ✨ Key Classes

### WebSocketAudioHandler
Main server class managing all connections.

```javascript
const handler = new WebSocketAudioHandler(port);
await handler.start();
await handler.stop();
handler.getStats();  // Get live statistics
handler.broadcast(message);  // Send to all clients
```

### SessionManager
Manages user sessions and audio buffers.

```javascript
const mgr = new SessionManager();
const session = mgr.createSession(userId, data);
mgr.getSession(sessionId);
mgr.updateSession(sessionId, updates);
mgr.appendAudioData(sessionId, buffer);
mgr.getAudioBuffer(sessionId);
mgr.destroySession(sessionId);
```

---

## 🚨 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Cannot find module 'ws'" | Missing dependency | `npm install ws` |
| "Port 8001 already in use" | Port conflict | `netstat -an \| grep 8001` or change port |
| "Failed to connect to backend" | FastAPI not running | `python run.py` in separate terminal |
| "Session expired" | Timeout reached | Reduce audio recording time |
| "No audio received" | Empty audio buffer | Check microphone permission |

---

## 📈 Performance

### Recommended Settings
- **Chunk Size**: 16KB (default)
- **Session Timeout**: 30 minutes
- **Max Sessions**: 1000
- **Audio Format**: PCM 16-bit, 16kHz, mono
- **Max Recording**: ~5 minutes

### Monitoring
```bash
# Watch server stats
curl http://localhost:8000/stats
```

---

## 🔐 Security Notes

### Current Setup
- ✓ Basic connection validation
- ✓ Session timeout protection
- ✓ Buffer overflow prevention
- ⚠️ No authentication (add JWT for production)
- ⚠️ No encryption (use WSS for production)

### Production Checklist
- [ ] Enable JWT authentication
- [ ] Use WSS protocol
- [ ] Configure HTTPS
- [ ] Set up rate limiting
- [ ] Enable CORS properly
- [ ] Monitor error rates
- [ ] Backup database

---

## 📱 Frontend Integration

### Service URL
```javascript
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8001';
```

### React Hooks Available
```javascript
import {
    useWebSocket,           // Connection management
    useWebSocketEvent,      // Event listening
    useWebSocketRequest,    // Request handling
    useEnrollment,          // Enrollment workflow
    useVerification,        // Verification workflow
    useConnectionQuality    // Monitor connection
} from './hooks/useWebSocket';
```

---

## 🎯 Next Steps

1. **Test**: Run integration tests
2. **Monitor**: Check stats in production
3. **Optimize**: Tune session timeout and chunk size
4. **Secure**: Add authentication
5. **Scale**: Monitor resource usage

---

## 📞 Support

### Check Status
```bash
# FastAPI
curl http://localhost:8000/

# WebSocket (connection required)
# Check browser console WebSocket tab
```

### View Logs
```bash
# FastAPI logs
# Check server terminal output

# WebSocket logs
NODE_ENV=debug node app.js
```

### Get Server Stats
```javascript
// In Node REPL with server running
global.wsHandler.getStats()
```

---

**Implementation Complete** ✅  
**Version**: 1.0.0  
**Date**: February 12, 2026
