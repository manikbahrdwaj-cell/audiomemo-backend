# WebSocket Client Quick Reference

## Quick Start

### 1. Basic Connection (Vanilla JavaScript)

```javascript
import WebSocketClientWrapper, { getWebSocketUrl } from './services/webSocketClientWrapper';

const client = new WebSocketClientWrapper(getWebSocketUrl());

// Connect
await client.connect();

// Send message
client.sendMessage({ type: 'ping' });

// Listen for messages
client.on('pong', (msg) => console.log('Pong:', msg));

// Disconnect
client.disconnect();
```

### 2. React Component

```javascript
import { useWebSocket } from './services/useWebSocket';

function MyComponent() {
  const { client, isConnected } = useWebSocket();

  return (
    <div>
      <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
      <button onClick={() => client?.sendMessage({ type: 'ping' })}>
        Send Ping
      </button>
    </div>
  );
}
```

## Common Use Cases

### Audio Streaming

```javascript
const { client } = useWebSocket();
const sendAudio = useSendAudioChunk(client);

// Send audio chunks
const audioBuffer = new ArrayBuffer(4096);
sendAudio(audioBuffer, { chunk_number: 1 });
```

### Voice Verification

```javascript
const sendVerification = useSendVerification(client);

try {
  const result = await sendVerification('+1234567890');
  console.log('Verification result:', result);
} catch (error) {
  console.error('Verification failed:', error);
}
```

### Voice Enrollment

```javascript
const sendEnrollment = useSendEnrollment(client);

try {
  const result = await sendEnrollment('+1234567890');
  console.log('Enrollment result:', result);
} catch (error) {
  console.error('Enrollment failed:', error);
}
```

### Listen to Events

```javascript
import { EVENT_TYPES } from './services/webSocketConstants';

// Connected
client.on(EVENT_TYPES.CONNECTED, () => {
  console.log('Connected');
});

// Disconnected
client.on(EVENT_TYPES.DISCONNECTED, () => {
  console.log('Disconnected');
});

// Error
client.on(EVENT_TYPES.ERROR, (error) => {
  console.error('Error:', error);
});

// Message received
client.on(EVENT_TYPES.MESSAGE, (message) => {
  console.log('Message:', message);
});
```

### Custom Message Handlers

```javascript
// Listen for specific message type
client.on('custom_response', (message) => {
  console.log('Custom response:', message);
});

// Send custom message
client.sendMessage({
  type: 'custom_request',
  data: 'some data'
});
```

## Connection Management

### Check Connection Status

```javascript
// Is connected
if (client.isConnected()) {
  console.log('Connected');
}

// Get state
const state = client.getState();
console.log('State:', state);

// Get detailed info
const info = client.getConnectionInfo();
console.log('Connection info:', info);
```

### Manual Connection Control

```javascript
// Connect
await client.connect();

// Disconnect
client.disconnect();

// Reconnect
await client.connect();

// Wait for connection
await client.waitForConnection(5000);
```

### Message Queue Management

```javascript
// Get queue size
const size = client.getMessageQueueSize();

// Clear queue
client.clearMessageQueue();

// Automatically handles queue when reconnecting
```

## Error Handling

### Error Types

```javascript
import { ERROR_CODES, ERROR_MESSAGES } from './services/webSocketConstants';

ERROR_CODES.CONNECTION_FAILED
ERROR_CODES.CONNECTION_TIMEOUT
ERROR_CODES.DISCONNECTED
ERROR_CODES.MESSAGE_SEND_FAILED
ERROR_CODES.MAX_ATTEMPTS_REACHED
ERROR_CODES.NOT_CONNECTED
ERROR_CODES.INVALID_MESSAGE
ERROR_CODES.MESSAGE_QUEUE_FULL
```

### Handle Errors

```javascript
client.on(EVENT_TYPES.ERROR, (error) => {
  console.error(`Error [${error.code}]: ${error.message}`);
  
  if (error.code === ERROR_CODES.MAX_ATTEMPTS_REACHED) {
    console.error('Max reconnection attempts reached');
  }
});
```

## Configuration

### Initialize with Options

```javascript
const client = new WebSocketClientWrapper(url, {
  maxConnectionAttempts: 5,
  initialReconnectDelay: 1000,
  maxReconnectDelay: 30000,
  heartbeatInterval: 30000,
  messageQueueMaxSize: 100,
  connectionTimeout: 10000,
  debug: true
});
```

### Environment Variables

```env
REACT_APP_WS_URL=ws://localhost:8000/ws
# or
REACT_APP_WS_HOST=localhost:8000
```

## Request-Response Pattern

### Send Request & Wait for Response

```javascript
try {
  const response = await client.sendRequest(
    {
      type: 'query',
      action: 'get_status'
    },
    5000  // timeout in ms
  );
  console.log('Response:', response);
} catch (error) {
  console.error('Request failed:', error);
}
```

## React Hooks Reference

### Main Connection Hook

```javascript
const { 
  client,           // WebSocket client instance
  isConnected,      // boolean
  state,            // CONNECTION_STATES value
  error,            // error object or null
  messageQueueSize  // number
} = useWebSocket(url, options, autoConnect);
```

### Message Type Listener

```javascript
import { MESSAGE_TYPES } from './services/webSocketConstants';

useWebSocketMessage(client, MESSAGE_TYPES.RESPONSE, (message) => {
  console.log('Response received:', message);
});
```

### Event Listener

```javascript
import { EVENT_TYPES } from './services/webSocketConstants';

useWebSocketEvent(client, EVENT_TYPES.CONNECTED, () => {
  console.log('Connected');
});
```

### Send Message

```javascript
const sendMessage = useSendWebSocketMessage(client);
sendMessage({ type: 'ping' });
```

### Send Request

```javascript
const sendRequest = useSendWebSocketRequest(client);

const response = await sendRequest({ type: 'query' });
```

### Send Audio

```javascript
const sendAudio = useSendAudioChunk(client);
sendAudio(audioBuffer, { chunk_number: 1 });
```

### Send Verification

```javascript
const sendVerification = useSendVerification(client);
const result = await sendVerification('+1234567890');
```

### Send Enrollment

```javascript
const sendEnrollment = useSendEnrollment(client);
const result = await sendEnrollment('+1234567890');
```

## Message Types

```javascript
import { MESSAGE_TYPES } from './services/webSocketConstants';

MESSAGE_TYPES.AUDIO                    // Audio data
MESSAGE_TYPES.VERIFY                  // Verification request
MESSAGE_TYPES.ENROLL                  // Enrollment request
MESSAGE_TYPES.PING                    // Keep-alive ping
MESSAGE_TYPES.PONG                    // Keep-alive pong
MESSAGE_TYPES.RESET                   // Reset command
MESSAGE_TYPES.STATUS                  // Status request
MESSAGE_TYPES.CONFIG                  // Configuration
MESSAGE_TYPES.ERROR                   // Error message
MESSAGE_TYPES.RESPONSE                // Generic response
```

## Connection States

```javascript
import { CONNECTION_STATES } from './services/webSocketConstants';

CONNECTION_STATES.NOT_INITIALIZED
CONNECTION_STATES.CONNECTING
CONNECTION_STATES.CONNECTED
CONNECTION_STATES.DISCONNECTING
CONNECTION_STATES.DISCONNECTED
CONNECTION_STATES.ERROR
CONNECTION_STATES.RECONNECTING
```

## Event Types

```javascript
import { EVENT_TYPES } from './services/webSocketConstants';

EVENT_TYPES.CONNECTED              // Connected
EVENT_TYPES.DISCONNECTED           // Disconnected
EVENT_TYPES.ERROR                  // Error occurred
EVENT_TYPES.MESSAGE                // Message received
EVENT_TYPES.MESSAGE_SENT           // Message sent
EVENT_TYPES.MESSAGE_QUEUED         // Message queued
EVENT_TYPES.STATE_CHANGED          // State changed
EVENT_TYPES.HEARTBEAT              // Heartbeat
EVENT_TYPES.RECONNECT_ATTEMPT      // Reconnecting
```

## Debugging

### Enable Debug Mode

```javascript
const client = new WebSocketClientWrapper(url, {
  debug: true  // or NODE_ENV=development
});
```

### Monitor Connection Info

```javascript
setInterval(() => {
  console.log(client.getConnectionInfo());
}, 5000);
```

## Complete Example

```javascript
import React, { useState } from 'react';
import { useWebSocket, useWebSocketEvent, useSendVerification } from './services/useWebSocket';
import { EVENT_TYPES } from './services/webSocketConstants';

export function CompleteExample() {
  const { client, isConnected, state, error } = useWebSocket();
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const sendVerification = useSendVerification(client);

  // Monitor connection
  useWebSocketEvent(client, EVENT_TYPES.CONNECTED, () => {
    console.log('Connected');
  });

  useWebSocketEvent(client, EVENT_TYPES.ERROR, (error) => {
    console.error('Error:', error);
    setResult({ error: error.message });
  });

  const handleVerify = async () => {
    setIsLoading(true);
    try {
      const res = await sendVerification('+1234567890');
      setResult(res);
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <p>Status: {isConnected ? '✓' : '✗'} {state}</p>
      {error && <p style={{ color: 'red' }}>Error: {error.message}</p>}
      <button onClick={handleVerify} disabled={!isConnected || isLoading}>
        {isLoading ? 'Loading...' : 'Verify'}
      </button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}
```

## File Structure

```
frontend/
├── src/
│   └── services/
│       ├── webSocketClientWrapper.js      # Main client (NEW)
│       ├── webSocketConstants.js          # Constants (NEW)
│       ├── webSocketEventEmitter.js       # Event emitter (NEW)
│       ├── useWebSocket.js                # React hooks (NEW)
│       └── websocketClient.js             # Legacy client (OLD)
│
├── src/examples/
│   └── webSocketClientExamples.jsx        # Usage examples (NEW)
│
└── WEBSOCKET_CLIENT_WRAPPER_GUIDE.md      # Full documentation (NEW)
```
