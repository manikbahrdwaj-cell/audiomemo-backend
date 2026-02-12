# WebSocket Service Quick Reference

## Overview
Provided are three layers of WebSocket functionality:

1. **Service Layer** (`websocketService`) - Low-level connection management
2. **React Hooks** (`useWebSocket.js`) - High-level component integration  
3. **Context Provider** (`WebSocketProvider`) - Global state management

Choose the layer that fits your use case.

## Quick Usage

### Minimal Setup (3 steps)

**Step 1**: Wrap App with Provider
```javascript
// src/App.js
import { WebSocketProvider } from './services/WebSocketProvider';

export default function App() {
  return (
    <WebSocketProvider>
      {/* Your components */}
    </WebSocketProvider>
  );
}
```

**Step 2**: Use hook in component
```javascript
import { useEnrollment } from './services/useWebSocket';

function MyComponent() {
  const { recording, startRecording, stopRecording, result } = useEnrollment('user123');
  
  return (
    <button onClick={recording ? stopRecording : startRecording}>
      {recording ? 'Stop' : 'Start'}
    </button>
  );
}
```

**Step 3**: Check connection status
```javascript
import { useWebSocketContext } from './services/WebSocketProvider';

function Header() {
  const { connected, error } = useWebSocketContext();
  
  return (
    <div>
      {connected ? '🟢 Online' : '🔴 Offline'}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
```

## Available Hooks

### `useWebSocket()`
Connection management
```javascript
const { connected, error, isConnecting, disconnect } = useWebSocket();
```

### `useEnrollment(userId, language?)`
Complete enrollment workflow
```javascript
const {
  enrolling,        // bool
  recording,        // bool
  error,           // null | string
  result,          // null | { success, vectorId, message }
  status,          // 'idle' | 'ready-to-record' | 'recording' | 'processing' | 'completed'
  startEnrollment, // () => Promise
  startRecording,  // () => Promise
  stopRecording    // () => Promise
} = useEnrollment('user123', 'en');
```

### `useVerification(userId)`
Complete verification workflow
```javascript
const {
  verifying,        // bool
  recording,        // bool
  error,           // null | string
  result,          // null | { success, score, threshold, isMatch, message }
  status,          // current status string
  startVerification, // () => Promise
  startRecording,   // () => Promise
  stopRecording     // () => Promise
} = useVerification('user123');
```

### `useWebSocketEvent(event, callback)`
Listen to events
```javascript
useWebSocketEvent('message:enrollment-result', (data) => {
  console.log('Result:', data);
});
```

### `useWebSocketRequest(type, data?, immediate?)`
Send custom requests
```javascript
const { loading, response, error, send } = useWebSocketRequest('check-status', {});

// Send manually
const result = await send();

// Send different data
const result = await send({ userId: 'other' });

// Send immediately
const { response } = useWebSocketRequest('status', {}, true);
```

### `useConnectionQuality()`
Monitor connection quality
```javascript
const { latency, quality } = useConnectionQuality();
// quality: 'excellent' | 'good' | 'fair' | 'poor' | 'disconnected'
```

## WebSocket Context API

Access global state:
```javascript
import { useWebSocketContext } from './services/WebSocketProvider';

const {
  // State
  connected,              // bool
  connecting,             // bool
  error,                  // null | string
  status,                 // connection status
  clientId,               // unique identifier
  connectionQuality,      // quality level
  connectionAttempts,     // number of reconnect attempts
  sessionData,            // { userId, action, startTime, ... }
  recentErrors,           // array of { message, timestamp }

  // Methods
  connect,                // () => Promise
  disconnect,             // () => void
  clearError,             // () => void
  setSessionData,         // (data) => void
  getStatus,              // () => Object
  
  // Direct service access (advanced)
  service                 // WebSocketService instance
} = useWebSocketContext();
```

## Service Methods (Direct API)

```javascript
import webSocketService from './services/websocketService';

// Connection
await webSocketService.connect();
webSocketService.disconnect();
webSocketService.isConnected(); // bool

// Requests
const result = await webSocketService.initializeSession(userId, 'enroll');
const result = await webSocketService.startEnrollment(userId);
const result = await webSocketService.startVerification(userId);
await webSocketService.startAudioCapture();
await webSocketService.stopAudioCapture();

// Custom request
const result = await webSocketService.sendRequest(type, data, timeout);

// Messaging
webSocketService.send({ type: 'custom', data: '...' });

// Events
webSocketService.on(event, callback);         // returns unsubscribe function
webSocketService.once(event, callback);       // one-time listener
webSocketService.emit(event, data);           // fire event
webSocketService.removeAllListeners();        // clear all

// Status
webSocketService.getStatus(); // { connected, url, reconnectAttempts, clientId }
```

## Common Patterns

### Pattern 1: Check before action
```javascript
function Component() {
  const { connected } = useWebSocketContext();
  const { startRecording } = useEnrollment(userId);

  return (
    <button 
      onClick={startRecording} 
      disabled={!connected}
    >
      Record
    </button>
  );
}
```

### Pattern 2: Show errors
```javascript
function Component() {
  const { error, recentErrors, clearError } = useWebSocketContext();

  return (
    <>
      {error && (
        <div className="error">
          {error}
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}
      
      <details>
        <summary>Error History ({recentErrors.length})</summary>
        {recentErrors.map((e, i) => (
          <p key={i}>{e.message}</p>
        ))}
      </details>
    </>
  );
}
```

### Pattern 3: Results notification
```javascript
function Component() {
  const { result, error, status } = useEnrollment(userId);

  return (
    <div>
      {status === 'completed' && result && (
        <p className="success">✓ {result.message}</p>
      )}
      {error && <p className="error">✗ {error}</p>}
      {status === 'recording' && <p>🔴 Recording...</p>}
      {status === 'processing' && <p>⏳ Processing...</p>}
    </div>
  );
}
```

### Pattern 4: Custom workflow
```javascript
async function customWorkflow(userId) {
  try {
    // Initialize
    await webSocketService.initializeSession(userId, 'enroll');
    
    // Start enrollment
    await webSocketService.startEnrollment(userId);
    
    // Capture audio
    await webSocketService.startAudioCapture();
    await new Promise(r => setTimeout(r, 3000)); // 3 seconds
    await webSocketService.stopAudioCapture();
    
    // Listen for result
    webSocketService.once('message:enrollment-result', (data) => {
      console.log('Complete:', data);
    });
  } catch (err) {
    console.error('Failed:', err);
  }
}
```

## Environment Setup

`.env` in frontend root:
```bash
REACT_APP_WS_URL=ws://localhost:8001
REACT_APP_API_URL=http://localhost:8000
NODE_ENV=development
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| Can't connect | Check WS_PORT 8001 available, backend running |
| Audio not working | Grant microphone permission, check browser |
| Memory leak | Unsubscribe from events, cleanup on unmount |
| Frequent disconnects | Check network, review connection quality |
| Timeouts | Increase timeout in sendRequest(), check backend |

## Event Types

### Connection Events
- `connected` - Connected to server
- `disconnected` - Disconnected from server
- `reconnecting` - Attempting to reconnect
- `reconnected` - Successfully reconnected
- `reconnect-failed` - Max reconnect attempts reached

### Message Events
- `message:enrollment-result` - Enrollment complete
- `message:verification-result` - Verification complete
- `message:processing` - Processing status update
- `message` - Any message received
- `message:*` - Any message of type * (custom)

### Service Events
- `error` - Error occurred
- `processing` - Processing update
- `result` - Result received
- `send-failed` - Message send failed

## Types Reference

```typescript
// Enrollment Result
{
  success: boolean;
  vectorId: string;
  message: string;
}

// Verification Result
{
  success: boolean;
  score: number; // 0-1
  threshold: number; // 0-1
  isMatch: boolean;
  message: string;
}

// Connection Status
{
  connected: boolean;
  url: string;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  clientId: string;
}

// Session Data
{
  userId: string;
  action: 'enroll' | 'verify';
  language?: string;
  startTime: number;
}
```

## Performance Tips

1. Use WebSocketProvider at top level
2. Use hooks for automatic cleanup
3. Unsubscribe from custom events manually when done
4. Avoid nested WebSocket operations
5. Monitor with useConnectionQuality()
6. Use requestTimeout for long operations
7. Batch multiple operations in sequence, not parallel

## Complete Example

```javascript
import React from 'react';
import { WebSocketProvider, useWebSocketContext } from './services/WebSocketProvider';
import { useEnrollment } from './services/useWebSocket';

function EnrollmentApp() {
  const [userId, setUserId] = React.useState('');
  const { connected, error } = useWebSocketContext();
  const {
    enrolling,
    recording,
    error: enrollError,
    result,
    status,
    startEnrollment,
    startRecording,
    stopRecording
  } = useEnrollment(userId);

  return (
    <div>
      <h1>Voice Enrollment</h1>
      
      {/* Status */}
      {connected ? '✓ Ready' : '✗ Offline'}
      
      {/* Input */}
      <input
        type="text"
        placeholder="User ID"
        value={userId}
        onChange={(e) => setUserId(e.target.value)}
        disabled={enrolling || recording}
      />
      
      {/* Error display */}
      {(error || enrollError) && (
        <p className="error">{error || enrollError}</p>
      )}
      
      {/* Results */}
      {result && (
        <p className="success">
          ✓ {result.message} (ID: {result.vectorId})
        </p>
      )}
      
      {/* Status info */}
      <p>Status: {status}</p>
      {recording && <p>🔴 Recording...</p>}
      
      {/* Controls */}
      <button
        onClick={async () => {
          await startEnrollment();
          await startRecording();
        }}
        disabled={!connected || !userId || recording}
      >
        {enrolling ? 'Starting...' : recording ? 'Recording...' : 'Start'}
      </button>
      
      {recording && (
        <button onClick={stopRecording} className="danger">
          Stop
        </button>
      )}
    </div>
  );
}

export default function App() {
  return (
    <WebSocketProvider wsUrl="ws://localhost:8001">
      <EnrollmentApp />
    </WebSocketProvider>
  );
}
```

---

For detailed documentation, see [WEBSOCKET_INTEGRATION_GUIDE.md](./WEBSOCKET_INTEGRATION_GUIDE.md)
