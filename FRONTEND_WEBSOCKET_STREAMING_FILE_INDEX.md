# Frontend WebSocket Audio Streaming - File Index

## Quick Navigation

### 🎯 Start Here
- **[FRONTEND_WEBSOCKET_STREAMING_IMPLEMENTATION_SUMMARY.md](FRONTEND_WEBSOCKET_STREAMING_IMPLEMENTATION_SUMMARY.md)** - Overview of all changes
- **[FRONTEND_STREAMING_QUICK_REFERENCE.md](FRONTEND_STREAMING_QUICK_REFERENCE.md)** - Quick lookup guide

### 📚 Full Documentation
- **[FRONTEND_WEBSOCKET_STREAMING.md](FRONTEND_WEBSOCKET_STREAMING.md)** - Comprehensive guide

## File Locations

### Core Implementation Files

#### 1. Updated: Audio Recorder
**File**: `frontend/src/utils/audioRecorder.js`  
**Size**: 402 lines  
**Status**: ✅ Updated  
**Changes**: Added WebSocket streaming, PCM16 conversion, Base64 encoding

```javascript
import { createAudioRecorder } from '@/utils/audioRecorder';

const recorder = createAudioRecorder({
  websocket: wsConnection,
  onChunkSent: (info) => console.log(info),
  onError: (error) => console.error(error)
});
```

#### 2. New: WebSocket Client Service
**File**: `frontend/src/services/websocketClient.js`  
**Size**: 290 lines  
**Status**: ✨ New  
**Purpose**: WebSocket connection management

```javascript
import { createWebSocketClient } from '@/services/websocketClient';

const ws = createWebSocketClient(url, {
  onOpen: () => console.log('Connected'),
  onMessage: (msg) => console.log(msg)
});

await ws.connect();
ws.sendVerification(phoneNumber);
```

#### 3. New: Streaming Recorder Integration
**File**: `frontend/src/utils/streamingRecorder.js`  
**Size**: 185 lines  
**Status**: ✨ New  
**Purpose**: High-level unified API (RECOMMENDED)

```javascript
import { createStreamingRecorder } from '@/utils/streamingRecorder';

const recorder = createStreamingRecorder({
  onVerificationResult: (result) => console.log(result)
});

await recorder.initialize();
await recorder.startRecording();
```

### Example Component Files

#### 4. New: React Component Example
**File**: `frontend/src/components/StreamingVerificationExample.jsx`  
**Size**: 350 lines  
**Status**: ✨ New  
**Purpose**: Full working React example

**Features**:
- Phone number input
- Record/Stop controls
- Verification buttons
- Live statistics display
- Result display
- Error handling

#### 5. New: Component Styling
**File**: `frontend/src/styles/StreamingVerification.css`  
**Size**: 400 lines  
**Status**: ✨ New  
**Purpose**: Professional component styling

### Documentation Files

#### 6. New: Full Documentation
**File**: `FRONTEND_WEBSOCKET_STREAMING.md`  
**Size**: 600+ lines  
**Type**: Comprehensive Guide  

**Sections**:
- Architecture overview
- Component descriptions
- Full API reference
- Usage examples
- React hooks
- Performance tips
- Configuration guide
- Troubleshooting
- Browser compatibility

#### 7. New: Quick Reference
**File**: `FRONTEND_STREAMING_QUICK_REFERENCE.md`  
**Size**: 400+ lines  
**Type**: Quick Lookup Guide

**Sections**:
- Quick start examples
- API cheat sheet
- Message formats
- Common patterns
- Configuration
- Debugging tips
- FAQ/Troubleshooting

#### 8. New: Implementation Summary
**File**: `FRONTEND_WEBSOCKET_STREAMING_IMPLEMENTATION_SUMMARY.md`  
**Size**: 600+ lines  
**Type**: Technical Summary

**Sections**:
- Overview
- Files created/updated
- Architecture diagrams
- Performance metrics
- Usage examples
- Testing recommendations
- Next steps

#### 9. New: File Index (This File)
**File**: `FRONTEND_WEBSOCKET_STREAMING_FILE_INDEX.md`  
**Type**: Navigation guide

## Recommended Reading Order

1. **New to the project?**
   - Start: FRONTEND_WEBSOCKET_STREAMING_IMPLEMENTATION_SUMMARY.md
   - Then: FRONTEND_STREAMING_QUICK_REFERENCE.md
   - Deep dive: FRONTEND_WEBSOCKET_STREAMING.md

2. **Want to implement streaming?**
   - Read: FRONTEND_STREAMING_QUICK_REFERENCE.md ("Quick Start" section)
   - Copy: StreamingVerificationExample.jsx code
   - Reference: FRONTEND_WEBSOCKET_STREAMING.md for detailed API

3. **Need to debug?**
   - Check: FRONTEND_STREAMING_QUICK_REFERENCE.md ("Troubleshooting" section)
   - See: FRONTEND_WEBSOCKET_STREAMING.md ("Debugging" section)
   - Review: Component example for error handling patterns

4. **Need performance tuning?**
   - Read: FRONTEND_WEBSOCKET_STREAMING.md ("Performance Considerations" section)
   - Adjust: audioRecorder.js constants
   - Monitor: streamingRecorder.getStats()

## API Quick Reference

### Simple API (Recommended)
```javascript
const recorder = createStreamingRecorder();
await recorder.initialize();
await recorder.startRecording();
await recorder.stopRecording();
recorder.verifyVoice(phoneNumber);
```

### WebSocket API (Direct Control)
```javascript
const ws = createWebSocketClient(url);
await ws.connect();
ws.sendVerification(phoneNumber);
ws.on('verification_result', handler);
```

### Audio Recorder API (Low-Level)
```javascript
const recorder = createAudioRecorder({ websocket: ws });
await recorder.start();
const blob = await recorder.stop();
```

## Configuration Files

### Environment Variables
```bash
# Add to .env
REACT_APP_WS_URL=ws://localhost:8000/ws
```

### Audio Settings
Edit constants in `audioRecorder.js`:
- `TARGET_SAMPLE_RATE`: 16000 (ECAPA-TDNN standard)
- `STREAM_BUFFER_THRESHOLD`: 16000 (samples, ~1 second)
- `STREAM_CHUNK_SIZE`: 4096 (bytes)

## Common Tasks

### Task: Add streaming verification to existing component
```javascript
// 1. Import
import { createStreamingRecorder } from '@/utils/streamingRecorder';

// 2. Initialize in useEffect
useEffect(() => {
  const recorder = createStreamingRecorder({
    onVerificationResult: handleResult
  });
  recorder.initialize();
}, []);

// 3. Use in buttons
<button onClick={() => recorder.startRecording()}>Record</button>
<button onClick={() => recorder.verifyVoice(phone)}>Verify</button>
```

### Task: Monitor streaming quality
```javascript
const stats = recorder.getStreamStats();
console.table({
  chunksStreamed: stats.chunksStreamed,
  bufferSize: stats.bufferSize,
  wsConnected: stats.websocketConnected
});
```

### Task: Handle connection failures
```javascript
const recorder = createStreamingRecorder({
  onWSError: (error) => {
    console.error('Connection failed:', error);
    // Retry logic
  }
});
```

### Task: Implement fallback to HTTP API
```javascript
// If WebSocket fails, fall back to HTTP upload
import { verifyVoice } from '@/services/api';

const result = await verifyVoice(phoneNumber, audioBlob);
```

## File Relationships

```
audioRecorder.js (Core)
  ├─ Used by: streamingRecorder.js
  ├─ Used by: StreamingVerificationExample.jsx
  └─ Exports: createAudioRecorder()

websocketClient.js (Transport)
  ├─ Used by: streamingRecorder.js
  ├─ Used by: audioRecorder.js (indirectly)
  └─ Exports: createWebSocketClient()

streamingRecorder.js (Integration)
  ├─ Uses: audioRecorder.js
  ├─ Uses: websocketClient.js
  ├─ Used by: StreamingVerificationExample.jsx
  └─ Exports: createStreamingRecorder()

StreamingVerificationExample.jsx (UI)
  ├─ Uses: streamingRecorder.js
  ├─ Imports: StreamingVerification.css
  └─ Purpose: Full working example

api.js (Fallback)
  ├─ Provides: HTTP-based endpoints
  ├─ Alternative to: WebSocket streaming
  └─ Functions: enrollVoice(), verifyVoice()
```

## Testing Checklist

- [ ] WebSocket connection test
- [ ] Audio streaming test
- [ ] Verification result handling
- [ ] Error recovery test
- [ ] Mobile responsiveness test
- [ ] Performance monitoring
- [ ] Fallback to HTTP API
- [ ] Graceful disconnect
- [ ] Multiple consecutive recordings
- [ ] Browser compatibility

## Deployment Checklist

- [ ] WebSocket server running on backend
- [ ] Correct WebSocket URL configured
- [ ] HTTPS/WSS in production
- [ ] Error logging enabled
- [ ] Performance monitoring active
- [ ] Rollback plan ready
- [ ] User documentation updated
- [ ] Support team trained

## Rollback Instructions

If issues occur, revert to HTTP-only mode:

```javascript
// Use original api.js functions
import { verifyVoice, enrollVoice } from '@/services/api';

// Or revert audioRecorder.js changes:
// - Remove websocket parameter
// - Use only stop() method to get blob
// - Upload blob via HTTP POST
```

## Support Resources

### Documentation
- [FRONTEND_WEBSOCKET_STREAMING.md](FRONTEND_WEBSOCKET_STREAMING.md) - Full guide
- [FRONTEND_STREAMING_QUICK_REFERENCE.md](FRONTEND_STREAMING_QUICK_REFERENCE.md) - API reference

### Examples
- [StreamingVerificationExample.jsx](frontend/src/components/StreamingVerificationExample.jsx) - React component
- Quick start examples in QUICK_REFERENCE.md

### Backend Integration
- [WEBSOCKET_GUIDE.md](WEBSOCKET_GUIDE.md) - Backend setup
- Backend files: websocket_handler.py, websocket_events.py

### Related Files
- [api.js](frontend/src/services/api.js) - HTTP API (fallback)
- [audioRecorder.js](frontend/src/utils/audioRecorder.js) - Core recorder

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-14 | WebSocket streaming added |
| 1.0.0 | Before | HTTP-only API |

## FAQ

**Q: Should I use createStreamingRecorder or createAudioRecorder?**  
A: Use createStreamingRecorder for most cases. It's simpler and handles everything.

**Q: Does streaming work without WebSocket?**  
A: No, streaming requires WebSocket. Use HTTP API as fallback.

**Q: Can I use both HTTP and WebSocket?**  
A: Yes, you can implement fallback logic (try WebSocket, fall back to HTTP).

**Q: What's the minimum audio length?**  
A: Backend requires 1000 bytes minimum (configurable).

**Q: Can I stop streaming mid-recording?**  
A: Yes, call stop() to end recording and streaming.

**Q: How is privacy handled?**  
A: Audio is streamed real-time, not stored on client if not needed.

## Next Steps

1. Run the example component to see it in action
2. Integrate into your existing UI
3. Test with various network conditions
4. Monitor performance metrics
5. Provide feedback for improvements

---

**Need help?** Check the troubleshooting section in [FRONTEND_STREAMING_QUICK_REFERENCE.md](FRONTEND_STREAMING_QUICK_REFERENCE.md)
