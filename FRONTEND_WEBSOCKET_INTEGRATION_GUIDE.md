# Frontend WebSocket Client Integration Guide

## Overview

This guide demonstrates how to integrate the Frontend WebSocket Client with enrollment and verification components. The system provides real-time, bidirectional communication for:

- **Multi-chunk voice enrollment** - Submit audio in chunks with progress tracking
- **Real-time voice verification** - Verify audio with immediate similarity feedback
- **Session management** - Create, track, and manage enrollment/verification sessions
- **Error handling** - Comprehensive error recovery and retry logic
- **State management** - React hooks for easy state integration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   React Components                           │
│  ┌──────────────────┐  ┌────────────────────┐              │
│  │ Enrollment       │  │ Verification       │              │
│  │ Component        │  │ Component          │              │
│  └────────┬─────────┘  └─────────┬──────────┘              │
└───────────┼───────────────────────┼──────────────────────────┘
            │                       │
            └───────────┬───────────┘
                        │
              ┌─────────▼──────────┐
              │  React Hooks       │
              │ - useEnrollment    │
              │ - useVerification  │
              └────────┬───────────┘
                       │
         ┌─────────────▼────────────────┐
         │  Services                    │
         │ ┌──────────────────────────┐ │
         │ │ Enrollment WebSocket Svc │ │
         │ │ Verification WebSocket   │ │
         │ │ Svc                      │ │
         │ └──────────┬───────────────┘ │
         └────────────┼─────────────────┘
                      │
              ┌───────▼────────┐
              │  WebSocket     │
              │  Client        │
              │  Wrapper       │
              └────────┬───────┘
                       │
              ┌────────▼───────┐
              │  Backend       │
              │  WebSocket     │
              │  Server        │
              └────────────────┘
```

## Setup Instructions

### 1. Wrap Application with WebSocketProvider

In your main App component:

```jsx
import { WebSocketProvider } from './context/WebSocketContext';
import EnrollmentPageWebSocket from './components/EnrollmentPageWebSocket';
import VerificationPageWebSocket from './components/VerificationPageWebSocket';

function App() {
  const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

  return (
    <WebSocketProvider wsUrl={WS_URL}>
      <div className="App">
        {/* Your routes and components */}
        <EnrollmentPageWebSocket />
        <VerificationPageWebSocket />
      </div>
    </WebSocketProvider>
  );
}

export default App;
```

### 2. Environment Configuration

Add to your `.env` file:

```env
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_DEBUG_WEBSOCKET=false
```

### 3. Update package.json

Ensure dependencies are installed:

```bash
npm install react@18.2.0 react-dom@18.2.0 axios@1.6.0
```

## Usage Examples

### Basic Enrollment Flow

```jsx
import { useEnrollmentService } from '../context/WebSocketContext';
import { useEnrollment } from '../hooks/useEnrollment';

function MyEnrollmentComponent() {
  const enrollmentService = useEnrollmentService();
  const {
    sessionId,
    status,
    progress,
    error,
    startEnrollment,
    submitChunk,
    completeEnrollment,
  } = useEnrollment(enrollmentService);

  const handleEnroll = async () => {
    // Start enrollment
    const sid = await startEnrollment('+1-555-0000', {
      max_chunks: 5,
      auto_process: true,
    });

    // Submit audio chunks
    for (let i = 0; i < 5; i++) {
      const audioBlob = await recordAudio();
      await submitChunk(audioBlob, i);
    }

    // Complete enrollment
    await completeEnrollment();
  };

  return (
    <div>
      <p>Status: {status}</p>
      <p>Progress: {progress.toFixed(0)}%</p>
      {error && <p>Error: {error}</p>}
      <button onClick={handleEnroll}>Start Enrollment</button>
    </div>
  );
}
```

### Basic Verification Flow

```jsx
import { useVerificationService } from '../context/WebSocketContext';
import { useVerification } from '../hooks/useVerification';

function MyVerificationComponent() {
  const verificationService = useVerificationService();
  const {
    sessionId,
    status,
    similarity,
    isVerified,
    startVerification,
    submitAudio,
  } = useVerification(verificationService);

  const handleVerify = async () => {
    // Start verification session
    await startVerification('+1-555-0000', {
      similarity_threshold: 0.85,
      max_attempts: 3,
    });

    // Record and submit audio
    const audioBlob = await recordAudio();
    await submitAudio(audioBlob);
  };

  return (
    <div>
      <p>Status: {status}</p>
      <p>Similarity: {(similarity * 100).toFixed(2)}%</p>
      {isVerified && <p>✓ Verified!</p>}
      <button onClick={handleVerify}>Start Verification</button>
    </div>
  );
}
```

## WebSocket Message Protocol

### Enrollment Messages

#### Start Enrollment Session
```json
{
  "type": "enroll",
  "action": "start_session",
  "session_id": "enroll_1702234560000_abc123",
  "phone_number": "+1-555-0000",
  "config": {
    "max_chunks": 10,
    "auto_process": true,
    "merge_embeddings": true
  }
}
```

#### Submit Audio Chunk
```json
{
  "type": "audio",
  "action": "submit_chunk",
  "session_id": "enroll_1702234560000_abc123",
  "chunk_index": 0,
  "audio_data": "base64_encoded_audio_data",
  "timestamp": "2024-02-14T10:30:00Z"
}
```

#### Complete Enrollment
```json
{
  "type": "enroll",
  "action": "complete",
  "session_id": "enroll_1702234560000_abc123"
}
```

### Verification Messages

#### Start Verification Session
```json
{
  "type": "verify",
  "action": "start_session",
  "session_id": "verify_1702234560000_xyz789",
  "phone_number": "+1-555-0000",
  "config": {
    "similarity_threshold": 0.85,
    "max_attempts": 3
  }
}
```

#### Submit Verification Audio
```json
{
  "type": "audio",
  "action": "verify_audio",
  "session_id": "verify_1702234560000_xyz789",
  "attempt_number": 1,
  "audio_data": "base64_encoded_audio_data",
  "timestamp": "2024-02-14T10:30:00Z"
}
```

## Event System

### Enrollment Events

```javascript
import { ENROLLMENT_EVENTS } from '../services/enrollmentWebSocketService';

enrollmentService.on(ENROLLMENT_EVENTS.SESSION_CREATED, (data) => {
  console.log('Session created:', data.sessionId);
});

enrollmentService.on(ENROLLMENT_EVENTS.CHUNK_RECEIVED, (data) => {
  console.log('Chunk submitted:', data.chunkIndex);
});

enrollmentService.on(ENROLLMENT_EVENTS.CHUNK_PROCESSED, (data) => {
  console.log('Chunk processed:', data.embedding);
});

enrollmentService.on(ENROLLMENT_EVENTS.STATUS_CHANGED, (data) => {
  console.log('Status:', data.status);
});

enrollmentService.on(ENROLLMENT_EVENTS.COMPLETED, (data) => {
  console.log('Enrollment complete:', data.vectorId);
});

enrollmentService.on(ENROLLMENT_EVENTS.ERROR, (data) => {
  console.error('Enrollment error:', data.error);
});
```

### Verification Events

```javascript
import { VERIFICATION_EVENTS } from '../services/verificationWebSocketService';

verificationService.on(VERIFICATION_EVENTS.SESSION_CREATED, (data) => {
  console.log('Session created:', data.sessionId);
});

verificationService.on(VERIFICATION_EVENTS.PROCESSING, (data) => {
  console.log('Processing audio...');
});

verificationService.on(VERIFICATION_EVENTS.COMPARING, (data) => {
  console.log('Similarity:', data.similarity);
});

verificationService.on(VERIFICATION_EVENTS.VERIFIED, (data) => {
  console.log('Verified!', data.similarity);
});

verificationService.on(VERIFICATION_EVENTS.REJECTED, (data) => {
  console.log('Not verified. Attempts remaining:', data.remainingAttempts);
});

verificationService.on(VERIFICATION_EVENTS.ERROR, (data) => {
  console.error('Verification error:', data.error);
});
```

## State Management

### useEnrollment Hook

```javascript
const {
  // State
  sessionId,           // Current enrollment session ID
  phoneNumber,         // Enrolled phone number
  status,              // Current enrollment status
  audioChunksCollected,// Number of chunks submitted
  progress,            // Progress percentage (0-100)
  isProcessing,        // Whether currently processing
  error,               // Error message if any
  successMessage,      // Success message after completion
  stats,               // Enrollment statistics
  isActive,            // Whether enrollment is active

  // Methods
  startEnrollment,     // (phoneNumber, config) => Promise<sessionId>
  submitChunk,         // (audioData, chunkIndex) => Promise<boolean>
  completeEnrollment,  // () => Promise<boolean>
  cancelEnrollment,    // () => Promise<boolean>
} = useEnrollment(enrollmentService);
```

### useVerification Hook

```javascript
const {
  // State
  sessionId,           // Current verification session ID
  phoneNumber,         // Phone number being verified
  status,              // Current verification status
  attemptNumber,       // Current attempt number
  maxAttempts,         // Maximum allowed attempts
  remainingAttempts,   // Remaining verification attempts
  isProcessing,        // Whether currently processing
  error,               // Error message if any
  verificationResult,  // Result object after completion
  similarity,          // Similarity score (0-1)
  threshold,           // Similarity threshold
  progress,            // Progress percentage (0-100)
  isActive,            // Whether verification is active

  // Methods
  startVerification,   // (phoneNumber, config) => Promise<sessionId>
  submitAudio,         // (audioData, isChunk) => Promise<boolean>
  cancelVerification,  // () => Promise<boolean>

  // Computed
  canSubmitAudio,      // Whether audio can be submitted
  isVerified,          // Whether verification succeeded
  isRejected,          // Whether verification failed
  isVerificationComplete, // Whether verification is done
} = useVerification(verificationService);
```

## Error Handling

### Connection Errors

```javascript
import { useWebSocket } from '../context/WebSocketContext';

function MyComponent() {
  const { isConnected, connectionError, reconnect } = useWebSocket();

  if (connectionError) {
    return (
      <div>
        <p>Connection error: {connectionError}</p>
        <button onClick={reconnect}>Reconnect</button>
      </div>
    );
  }

  return <div>Connected: {isConnected ? 'Yes' : 'No'}</div>;
}
```

### Handling Service Errors

```javascript
const handleEnrollment = async () => {
  try {
    const sessionId = await enrollment.startEnrollment(phone);
    // Process enrollment
  } catch (error) {
    console.error('Enrollment failed:', error.message);
    // Show user-friendly error message
  }
};
```

## Performance Optimization

### Audio Chunk Size

```javascript
// Recommended chunk durations
const CHUNK_CONFIGS = {
  NETWORK_OPTIMIZED: {
    maxChunks: 5,
    targetChunkDuration: 2,  // seconds
  },
  QUALITY_OPTIMIZED: {
    maxChunks: 10,
    targetChunkDuration: 1,  // seconds
  },
  BALANCED: {
    maxChunks: 8,
    targetChunkDuration: 1.5,  // seconds
  },
};

// Use in your component
await enrollment.startEnrollment(phone, {
  max_chunks: CHUNK_CONFIGS.BALANCED.maxChunks,
  auto_process: true,
});
```

### Memory Management

```javascript
// Cleanup audio data after submission
const handleSubmitChunk = async (audioBlob) => {
  try {
    await submitChunk(audioBlob);
    // Audio is processed, can be garbage collected
  } catch (error) {
    console.error('Failed to submit:', error);
  }
};
```

## Testing

### Unit Tests

```javascript
import { renderHook, act } from '@testing-library/react';
import { useEnrollment } from '../hooks/useEnrollment';

describe('useEnrollment', () => {
  it('should initialize enrollment session', async () => {
    const mockService = {
      startEnrollment: jest.fn().mockResolvedValue('session_123'),
      on: jest.fn(),
      off: jest.fn(),
    };

    const { result } = renderHook(() => useEnrollment(mockService));

    await act(async () => {
      await result.current.startEnrollment('+1-555-0000');
    });

    expect(result.current.sessionId).toBe('session_123');
  });
});
```

## Deployment Checklist

- [ ] Configure WebSocket URL for production environment
- [ ] Enable HTTPS/WSS for secure connections
- [ ] Set appropriate CORS headers
- [ ] Configure message queue limits
- [ ] Set up error monitoring and logging
- [ ] Test reconnection behavior
- [ ] Verify session timeout handling
- [ ] Test error scenarios
- [ ] Load test with multiple concurrent sessions
- [ ] Document API changes

## File Structure

```
frontend/src/
├── components/
│   ├── EnrollmentPageWebSocket.jsx    # Enhanced enrollment component
│   ├── VerificationPageWebSocket.jsx  # Enhanced verification component
│   ├── EnrollmentPage.js              # Original enrollment component
│   └── VerificationPage.js            # Original verification component
├── hooks/
│   ├── useEnrollment.js               # Enrollment hook
│   └── useVerification.js             # Verification hook
├── services/
│   ├── enrollmentWebSocketService.js  # Enrollment WebSocket service
│   ├── verificationWebSocketService.js # Verification WebSocket service
│   ├── webSocketClientWrapper.js      # Main WebSocket client
│   ├── websocketClient.js             # Basic WebSocket client
│   ├── webSocketConstants.js          # Constants
│   └── webSocketEventEmitter.js       # Event emitter
├── context/
│   └── WebSocketContext.js            # WebSocket context provider
└── utils/
    └── webSocketUtils.js              # Utility functions
```

## Troubleshooting

### WebSocket Connection Issues

1. **Check WebSocket URL**: Verify `ws://` protocol (or `wss://` for secure)
2. **Check CORS**: Ensure backend allows WebSocket connections
3. **Check Firewall**: Ensure WebSocket port is not blocked
4. **Check Logs**: Enable debug mode to see detailed logs

### Message Not Received

1. Check connection status: `useWebSocket().isConnected`
2. Verify message format matches backend requirements
3. Check backend logs for processing errors
4. Verify session ID matches active session

### Performance Issues

1. Reduce message frequency if rate-limited
2. Increase chunk duration to reduce overhead
3. Check browser DevTools for memory leaks
4. Monitor WebSocket message queue size

## Support and Documentation

- **Backend WebSocket Guide**: See `../backend/WEBSOCKET_GUIDE.md`
- **API Reference**: See `../backend/WEBSOCKET_IMPLEMENTATION_SUMMARY.md`
- **Examples**: See `../examples/` directory
