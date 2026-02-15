# Frontend WebSocket Client - Quick Reference

## Quick Start

### 1. Setup (App.js)
```jsx
import { WebSocketProvider } from './context/WebSocketContext';

<WebSocketProvider wsUrl="ws://localhost:8000/ws">
  <YourApp />
</WebSocketProvider>
```

### 2. Use Components
```jsx
import EnrollmentPageWebSocket from './components/EnrollmentPageWebSocket';
import VerificationPageWebSocket from './components/VerificationPageWebSocket';

// Components automatically use WebSocket
<EnrollmentPageWebSocket />
<VerificationPageWebSocket />
```

### 3. Or Use Hooks in Custom Components
```jsx
import { useEnrollmentService, useVerificationService } from './context/WebSocketContext';
import { useEnrollment } from './hooks/useEnrollment';
import { useVerification } from './hooks/useVerification';

function MyComponent() {
  const enrollmentService = useEnrollmentService();
  const { startEnrollment, submitChunk, completeEnrollment } = useEnrollment(enrollmentService);
  
  // Use enrollment...
}
```

## Enrollment Flow

```
startEnrollment()
    ↓
submitChunk(audioData)  [x N chunks]
    ↓
completeEnrollment()
    ↓
COMPLETED event with vectorId
```

### Code Example
```javascript
// Start
const sessionId = await startEnrollment('+1-555-0000', {
  max_chunks: 5,
  auto_process: true,
});

// Submit chunks
for (let i = 0; i < 3; i++) {
  const audioBlob = await recordAudio();
  await submitChunk(audioBlob, i);
}

// Complete
await completeEnrollment();
```

## Verification Flow

```
startVerification()
    ↓
submitAudio(audioData)
    ↓
Similarity Score → Match/Mismatch
    ↓
VERIFIED/REJECTED event
```

### Code Example
```javascript
// Start
await startVerification('+1-555-0000', {
  similarity_threshold: 0.85,
  max_attempts: 3,
});

// Submit audio
const audioBlob = await recordAudio();
await submitAudio(audioBlob);

// Listen for result
verificationService.on('verification:verified', (data) => {
  console.log('Matched!', data.similarity);
});
```

## Hook State

### useEnrollment
```javascript
{
  sessionId, status, progress, error, successMessage,
  audioChunksCollected, isActive, isProcessing,
  stats: { vectorId, chunksProcessed },
  startEnrollment, submitChunk, completeEnrollment,
  canSubmitChunk, isEnrollmentComplete
}
```

### useVerification
```javascript
{
  sessionId, status, attemptNumber, remainingAttempts,
  similarity, threshold, progress, error,
  verificationResult, isActive, isProcessing,
  startVerification, submitAudio, cancelVerification,
  canSubmitAudio, isVerified, isRejected, isVerificationComplete
}
```

## Events

### Enrollment Events
- `enrollment:session_created` - Session started
- `enrollment:chunk_received` - Chunk submitted
- `enrollment:chunk_processed` - Chunk processed
- `enrollment:status_changed` - Status update
- `enrollment:completed` - Enrollment done
- `enrollment:error` - Error occurred
- `enrollment:cancelled` - Cancelled by user

### Verification Events
- `verification:session_created` - Session started
- `verification:processing` - Processing audio
- `verification:comparing` - Comparing with stored
- `verification:verified` - Match found
- `verification:rejected` - No match
- `verification:completed` - Session complete
- `verification:error` - Error occurred
- `verification:cancelled` - Cancelled by user

## API Integration

### WebSocketContext Hooks
```javascript
const { wsClient, enrollmentService, verificationService, isConnected } = useWebSocket();
const enrollmentService = useEnrollmentService();
const verificationService = useVerificationService();
```

### WebSocket Connection Status
```javascript
const { isConnected, connectionError, reconnect } = useWebSocket();

if (connectionError) {
  <button onClick={reconnect}>Reconnect</button>
}
```

## Configuration

### Environment Variables (.env)
```
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_DEBUG_WEBSOCKET=false
```

### Enrollment Config
```javascript
{
  max_chunks: 10,              // Max audio chunks
  auto_process: true,          // Auto-generate embeddings
  merge_embeddings: true,      // Merge multiple embeddings
  min_chunks_required: 1,      // Minimum chunks required
  quality_threshold: 0.7,      // Min quality score
}
```

### Verification Config
```javascript
{
  similarity_threshold: 0.85,  // Match threshold
  max_attempts: 3,             // Max verification attempts
  attempt_timeout_seconds: 60, // Timeout per attempt
}
```

## Utility Functions

```javascript
import {
  encodeAudioData,            // Base64 encode audio
  decodeAudioData,            // Base64 decode audio
  isValidPhoneNumber,         // Validate phone format
  formatPhoneNumber,          // Format for display
  validateAudioDuration,      // Check duration
  formatDuration,             // Format seconds to readable
  calculateQualityScore,      // Calculate audio quality
  retryOperation,             // Retry with backoff
  WebSocketConnectionMonitor, // Monitor connection
  SessionPersistenceManager,  // Persist sessions
} from './utils/webSocketUtils';
```

## Error Handling

```javascript
try {
  await startEnrollment(phone);
} catch (error) {
  console.error('Enrollment failed:', error.message);
  // Handle error
}

// Or listen to error events
enrollmentService.on('enrollment:error', (data) => {
  console.error('Error:', data.error);
});
```

## Files Created

```
frontend/src/
├── services/
│   ├── enrollmentWebSocketService.js   (NEW)
│   └── verificationWebSocketService.js (NEW)
├── hooks/
│   ├── useEnrollment.js               (NEW)
│   └── useVerification.js             (NEW)
├── context/
│   └── WebSocketContext.js            (NEW)
├── components/
│   ├── EnrollmentPageWebSocket.jsx    (NEW)
│   └── VerificationPageWebSocket.jsx  (NEW)
└── utils/
    └── webSocketUtils.js              (NEW)

Root:
└── FRONTEND_WEBSOCKET_INTEGRATION_GUIDE.md (NEW)
```

## Status Codes

### Enrollment Status
- `initializing` - Session initializing
- `active` - Session active, ready for chunks
- `collecting` - Collecting audio chunks
- `processing` - Processing chunks
- `finalizing` - Finalizing enrollment
- `completed` - Enrollment successful
- `error` - Error occurred
- `cancelled` - User cancelled

### Verification Status
- `initializing` - Session initializing
- `active` - Session active
- `processing` - Processing audio
- `comparing` - Comparing embeddings
- `verified` - Match found
- `rejected` - No match, try again
- `completed` - Session complete
- `failed` - Verification failed
- `expired` - Session expired
- `cancelled` - User cancelled

## Common Tasks

### Record and Submit Audio
```javascript
const recordAudio = async (duration = 5) => {
  const recorder = createAudioRecorder();
  await recorder.start();
  await new Promise(r => setTimeout(r, duration * 1000));
  return await recorder.stop();
};

const blob = await recordAudio(5);
await submitChunk(blob);
```

### Monitor Progress
```javascript
enrollmentService.on('enrollment:chunk_received', (data) => {
  setProgress((data.totalChunks / 10) * 100);
});
```

### Handle Real-Time Updates
```javascript
verificationService.on('verification:comparing', (data) => {
  console.log('Similarity:', data.similarity);
  const match = data.similarity >= data.threshold;
});
```

### Persist Session Data
```javascript
import { SessionPersistenceManager } from './utils/webSocketUtils';

const manager = new SessionPersistenceManager();
manager.saveSession(sessionId, { /* data */ });
const session = manager.loadSession(sessionId);
```

## Performance Tips

1. **Chunk Duration**: Use 1-2 seconds per chunk
2. **Batch Processing**: Submit multiple chunks at once if possible
3. **Compression**: Compress audio before transmission
4. **Caching**: Cache enrollment results when possible
5. **Rate Limiting**: Handle rate limits gracefully

## Browser Compatibility

- Chrome 55+ ✓
- Firefox 50+ ✓
- Safari 12+ ✓
- Edge 15+ ✓

## Debugging

Enable debug logs:
```javascript
<WebSocketProvider 
  wsUrl="ws://localhost:8000/ws"
  debug={true}
>
  {children}
</WebSocketProvider>
```

Check connection status:
```javascript
const { isConnected, connectionError } = useWebSocket();
console.log('Connected:', isConnected);
console.log('Error:', connectionError);
```
