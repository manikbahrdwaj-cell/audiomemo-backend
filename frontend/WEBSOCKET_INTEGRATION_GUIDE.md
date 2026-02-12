# WebSocket Service Integration Guide - Phase 3, Step 3.2

## Overview

This guide covers the complete WebSocket service implementation for real-time frontend-backend communication in the Voice Biometric Authentication system.

## Architecture

```
Frontend Components
    ↓
React Hooks (useWebSocket, useEnrollment, useVerification)
    ↓
WebSocket Context (WebSocketProvider, useWebSocketContext)
    ↓
WebSocket Service (websocketService)
    ↓
WebSocket Client (VoiceWebSocketClient)
    ↓
WebSocket Server (ws://localhost:8001)
```

## Files Created

### 1. Core Services

#### `services/websocketService.js`
- **Purpose**: Centralized WebSocket service with connection management, event handling, and request/response handling
- **Features**:
  - Automatic reconnection with exponential backoff
  - Request/response pattern with timeouts
  - Event listener system
  - Connection status tracking
  - Error handling and recovery

**Usage**:
```javascript
import webSocketService from '@/services/websocketService';

// Connect
await webSocketService.connect();

// Send request and wait for response
const result = await webSocketService.initializeSession(userId, 'enroll');

// Listen to events
const unsubscribe = webSocketService.on('message:enrollment-result', (data) => {
  console.log('Enrollment complete:', data);
});

// Cleanup
unsubscribe();
```

#### `services/WebSocketProvider.js`
- **Purpose**: React Context Provider for global WebSocket state management
- **Features**:
  - Global connection state
  - Connection quality tracking
  - Error history
  - Session data management
  - Automatic connection initialization

**Usage**:
```javascript
// In App.js
import { WebSocketProvider } from '@/services/WebSocketProvider';

function App() {
  return (
    <WebSocketProvider wsUrl="ws://localhost:8001">
      <YourComponents />
    </WebSocketProvider>
  );
}

// In components
import { useWebSocketContext } from '@/services/WebSocketProvider';

function MyComponent() {
  const { connected, error, status, disconnect } = useWebSocketContext();
  
  return (
    <div>
      Status: {status}
      {error && <p>Error: {error}</p>}
    </div>
  );
}
```

### 2. React Hooks

#### `services/useWebSocket.js`

**`useWebSocket()`** - Basic connection management
```javascript
const { connected, error, isConnecting, disconnect } = useWebSocket();
```

**`useWebSocketEvent(event, callback)`** - Listen to events
```javascript
useWebSocketEvent('message:enrollment-result', (data) => {
  console.log('Result:', data);
});
```

**`useWebSocketRequest(type, data, immediate)`** - Send requests
```javascript
const { loading, response, error, send } = useWebSocketRequest('ping', {});
// Send manually
const result = await send();
// Or send immediately on mount
const { loading, response, error } = useWebSocketRequest('getStatus', {}, true);
```

**`useEnrollment(userId, language)`** - Voice enrollment workflow
```javascript
const {
  enrolling,      // Boolean: enrollment in progress
  recording,      // Boolean: audio recording active
  error,          // Error message or null
  result,         // Enrollment result { success, vectorId, message }
  status,         // Current status: idle, ready-to-record, recording, processing, completed, failed
  startEnrollment,  // Function to initiate enrollment
  startRecording,   // Function to start recording
  stopRecording     // Function to stop recording
} = useEnrollment('user123', 'en');
```

**`useVerification(userId)`** - Voice verification workflow
```javascript
const {
  verifying,        // Boolean: verification in progress
  recording,        // Boolean: audio recording active
  error,           // Error message or null
  result,          // Result { success, score, threshold, isMatch, message }
  status,          // Current status
  startVerification, // Function to initiate verification
  startRecording,    // Function to start recording
  stopRecording      // Function to stop recording
} = useVerification('user123');
```

**`useConnectionQuality()`** - Monitor connection quality
```javascript
const { latency, quality } = useConnectionQuality();
// quality: 'excellent', 'good', 'fair', 'poor', 'disconnected', 'unknown'
```

## Integration Steps

### Step 1: Setup WebSocket Provider

Update `frontend/src/App.js`:
```javascript
import { WebSocketProvider } from './services/WebSocketProvider';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import EnrollmentPage from './components/EnrollmentPage';
import VerificationPage from './components/VerificationPage';

function App() {
  return (
    <WebSocketProvider wsUrl="ws://localhost:8001">
      <Router>
        <Routes>
          <Route path="/" element={<EnrollmentPage />} />
          <Route path="/verify" element={<VerificationPage />} />
        </Routes>
      </Router>
    </WebSocketProvider>
  );
}

export default App;
```

### Step 2: Update Enrollment Component

```javascript
import React from 'react';
import { useEnrollment } from '../services/useWebSocket';
import { useWebSocketContext } from '../services/WebSocketProvider';

function EnrollmentPage() {
  const [phoneNumber, setPhoneNumber] = React.useState('');
  const { connected, error: connectionError } = useWebSocketContext();
  const {
    enrolling,
    recording,
    error,
    result,
    status,
    startEnrollment,
    startRecording,
    stopRecording
  } = useEnrollment(phoneNumber, 'en');

  const handleStartEnrollment = async () => {
    if (!phoneNumber.trim()) {
      alert('Please enter a phone number');
      return;
    }
    try {
      await startEnrollment();
      await startRecording();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  const handleStopRecording = async () => {
    try {
      await stopRecording();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  return (
    <div>
      <h1>Voice Enrollment</h1>
      
      {connectionError && (
        <div className="error-banner">
          Connection Error: {connectionError}
        </div>
      )}
      
      <input
        type="tel"
        placeholder="Phone Number"
        value={phoneNumber}
        onChange={(e) => setPhoneNumber(e.target.value)}
        disabled={!connected || recording}
      />

      {result && (
        <div className="success-message">
          {result.message}
          {result.vectorId && <p>Vector ID: {result.vectorId}</p>}
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="status-info">
        <p>Status: {status}</p>
        {recording && <p className="recording-indicator">🔴 Recording...</p>}
      </div>

      <button
        onClick={handleStartEnrollment}
        disabled={!connected || enrolling || recording}
      >
        {enrolling ? 'Starting...' : 'Start Enrollment'}
      </button>

      {recording && (
        <button
          onClick={handleStopRecording}
          className="stop-button"
        >
          Stop Recording
        </button>
      )}
    </div>
  );
}

export default EnrollmentPage;
```

### Step 3: Update Verification Component

```javascript
import React from 'react';
import { useVerification } from '../services/useWebSocket';
import { useWebSocketContext } from '../services/WebSocketProvider';

function VerificationPage() {
  const [phoneNumber, setPhoneNumber] = React.useState('');
  const { connected, error: connectionError } = useWebSocketContext();
  const {
    verifying,
    recording,
    error,
    result,
    status,
    startVerification,
    startRecording,
    stopRecording
  } = useVerification(phoneNumber);

  const handleStartVerification = async () => {
    if (!phoneNumber.trim()) {
      alert('Please enter a phone number');
      return;
    }
    try {
      await startVerification();
      await startRecording();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  const handleStopRecording = async () => {
    try {
      await stopRecording();
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  return (
    <div>
      <h1>Voice Verification</h1>
      
      {connectionError && (
        <div className="error-banner">
          Connection Error: {connectionError}
        </div>
      )}
      
      <input
        type="tel"
        placeholder="Phone Number"
        value={phoneNumber}
        onChange={(e) => setPhoneNumber(e.target.value)}
        disabled={!connected || recording}
      />

      {result && (
        <div className={result.isMatch ? 'success-message' : 'error-message'}>
          <p>{result.message}</p>
          <p>Score: {(result.score * 100).toFixed(2)}%</p>
          <p>Threshold: {(result.threshold * 100).toFixed(2)}%</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="status-info">
        <p>Status: {status}</p>
        {recording && <p className="recording-indicator">🔴 Recording...</p>}
      </div>

      <button
        onClick={handleStartVerification}
        disabled={!connected || verifying || recording}
      >
        {verifying ? 'Starting...' : 'Start Verification'}
      </button>

      {recording && (
        <button
          onClick={handleStopRecording}
          className="stop-button"
        >
          Stop Recording
        </button>
      )}
    </div>
  );
}

export default VerificationPage;
```

## Advanced Usage

### Custom Event Handling

```javascript
import webSocketService from '@/services/websocketService';

// Listen to specific message type
const unsubscribe = webSocketService.on('message:enrollment-result', (data) => {
  console.log('Enrollment result:', data);
});

// Listen to all messages
webSocketService.on('message', (msg) => {
  console.log('Message received:', msg);
});

// Emit custom events
webSocketService.emit('custom-event', { data: 'value' });

// Remove specific listener
unsubscribe();

// Remove all listeners
webSocketService.removeAllListeners();
```

### Connection Status Monitoring

```javascript
import { useWebSocketContext } from '@/services/WebSocketProvider';

function ConnectionStatus() {
  const {
    connected,
    connecting,
    status,
    connectionQuality,
    connectionAttempts,
    recentErrors
  } = useWebSocketContext();

  return (
    <div>
      <p>Connected: {connected ? '✓' : '✗'}</p>
      <p>Status: {status}</p>
      <p>Quality: {connectionQuality}</p>
      <p>Attempts: {connectionAttempts}</p>
      {recentErrors.map((err, i) => (
        <p key={i}>{new Date(err.timestamp).toLocaleTimeString()}: {err.message}</p>
      ))}
    </div>
  );
}
```

### Session Management

```javascript
import { useWebSocketContext } from '@/services/WebSocketProvider';

function SessionManager() {
  const { setSessionData, sessionData } = useWebSocketContext();

  const initSession = async () => {
    setSessionData({
      userId: 'user123',
      action: 'enroll',
      startTime: Date.now()
    });
  };

  return (
    <div>
      <button onClick={initSession}>Initialize Session</button>
      <pre>{JSON.stringify(sessionData, null, 2)}</pre>
    </div>
  );
}
```

## Configuration

### Environment Variables

Create `.env` in the frontend root:
```
REACT_APP_WS_URL=ws://localhost:8001
REACT_APP_API_URL=http://localhost:8000
```

Use in code:
```javascript
const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8001';
```

## Error Handling

The WebSocket service provides comprehensive error handling:

```javascript
import { useWebSocketContext } from '@/services/WebSocketProvider';

function ErrorHandler() {
  const { error, recentErrors, clearError } = useWebSocketContext();

  return (
    <div>
      {error && (
        <div className="error-alert">
          <p>{error}</p>
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}
      
      <details>
        <summary>Recent Errors ({recentErrors.length})</summary>
        <ul>
          {recentErrors.map((err, i) => (
            <li key={i}>
              {new Date(err.timestamp).toLocaleTimeString()}: {err.message}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
```

## Performance Considerations

1. **Connection Pooling**: Single global connection is maintained
2. **Event Debouncing**: Audio capture uses ScriptProcessor at 4096 samples
3. **Memory Management**: Old listeners are cleaned up automatically
4. **Timeouts**: Requests timeout after 30 seconds by default
5. **Reconnection**: Exponential backoff prevents server overload

## Testing

### Test WebSocket Connection

```javascript
import webSocketService from '@/services/websocketService';

async function testConnection() {
  try {
    await webSocketService.connect();
    console.log('Connected:', webSocketService.isConnected());
    
    const result = await webSocketService.sendRequest('ping', {});
    console.log('Ping result:', result);
    
    webSocketService.disconnect();
  } catch (err) {
    console.error('Test failed:', err);
  }
}
```

### Test Enrollment Flow

```javascript
async function testEnrollment(userId) {
  try {
    // Initialize
    const initResult = await webSocketService.initializeSession(userId, 'enroll');
    console.log('Initialized:', initResult);
    
    // Start enrollment
    const enrollResult = await webSocketService.startEnrollment(userId);
    console.log('Enrollment started:', enrollResult);
    
    // Start audio
    await webSocketService.startAudioCapture();
    console.log('Audio capture started');
    
    // Stop after 5 seconds
    await new Promise(r => setTimeout(r, 5000));
    await webSocketService.stopAudioCapture();
    console.log('Audio capture stopped');
  } catch (err) {
    console.error('Test failed:', err);
  }
}
```

## Troubleshooting

### Connection Refused
- Ensure backend WebSocket server is running on port 8001
- Check `REACT_APP_WS_URL` environment variable

### Audio Capture Not Working
- Grant microphone permissions to browser
- Check browser console for permission errors
- Verify audio constraints in `startAudioCapture()`

### Timeouts
- Increase `requestTimeout` in WebSocketService constructor
- Check backend processing time
- Monitor network latency with `useConnectionQuality()`

### Memory Leaks
- Always unsubscribe from events using returned function
- Disconnect on component unmount
- Clear listeners when switching routes

## Next Steps

1. ✅ WebSocket Service Implementation
2. ✅ React Hooks & Context
3. ⬜ Component Integration (see examples above)
4. ⬜ Testing & Validation
5. ⬜ Performance Monitoring
