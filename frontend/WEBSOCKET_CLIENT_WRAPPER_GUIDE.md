# Frontend WebSocket Client Wrapper

## Overview

The WebSocket Client Wrapper is a production-ready, feature-rich WebSocket client for the Voice Biometric Frontend. It provides:

- **Automatic Reconnection**: Exponential backoff reconnection strategy
- **Message Queuing**: Queue messages while disconnected
- **Heartbeat/Keep-Alive**: Automatic heartbeat mechanism
- **Event-Driven Architecture**: Comprehensive event system
- **Error Handling**: Robust error handling and recovery
- **Connection State Management**: Full lifecycle management
- **Request-Response Pattern**: Send requests and wait for responses
- **React Hooks**: Easy integration with React components

## Architecture

### Files

```
src/services/
├── webSocketClientWrapper.js      # Main WebSocket client class
├── webSocketConstants.js           # Constants and configuration
├── webSocketEventEmitter.js        # Event emitter utility
├── useWebSocket.js                # React hooks for WebSocket
└── websocketClient.js             # Legacy client (deprecated)

src/examples/
└── webSocketClientExamples.jsx    # Usage examples
```

### Components

#### 1. WebSocketClientWrapper (`webSocketClientWrapper.js`)
Main WebSocket client implementation with:
- Connection management
- Message queuing
- Heartbeat mechanism
- Error handling
- Event emitting

#### 2. EventEmitter (`webSocketEventEmitter.js`)
Simple event emitter for managing events:
- `on(event, handler)` - Register listener
- `once(event, handler)` - Register one-time listener
- `emit(event, ...args)` - Emit event
- `off(event, handler)` - Unregister listener
- `removeAllListeners()` - Clear all listeners

#### 3. React Hooks (`useWebSocket.js`)
Hooks for easy React integration:
- `useWebSocket()` - Main connection hook
- `useWebSocketMessage()` - Listen for message types
- `useWebSocketEvent()` - Listen for events
- `useSendWebSocketMessage()` - Send messages
- `useSendWebSocketRequest()` - Send requests
- `useSendAudioChunk()` - Send audio
- `useSendVerification()` - Send verification
- `useSendEnrollment()` - Send enrollment

## Installation & Setup

### 1. Install Dependencies
No additional dependencies required - uses native WebSocket API.

### 2. Configuration
Set environment variables in `.env`:

```env
# WebSocket URL (optional)
REACT_APP_WS_URL=ws://localhost:8000/ws
# Or specify just the host
REACT_APP_WS_HOST=localhost:8000
```

### 3. Enable Debug Mode
Set in environment or pass to client options:

```env
NODE_ENV=development  # Automatically enables debug logging
```

## Usage

### Basic Connection

```javascript
import { createWebSocketClient, getWebSocketUrl } from './services/webSocketClientWrapper';

// Create client with default URL
const client = createWebSocketClient(getWebSocketUrl());

// Connect
await client.connect();

// Send message
client.sendMessage({ type: 'ping', timestamp: Date.now() });

// Listen for messages
client.on('message_type', (message) => {
  console.log('Received:', message);
});

// Disconnect
client.disconnect();
```

### React Hook Usage

```javascript
import { useWebSocket } from './services/useWebSocket';

function MyComponent() {
  const { client, isConnected, state, error } = useWebSocket();

  return (
    <div>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      <p>State: {state}</p>
      {error && <p>Error: {error.message}</p>}
    </div>
  );
}
```

### Send Verification Request

```javascript
import { useSendVerification, useWebSocket } from './services/useWebSocket';

function VerificationComponent() {
  const { client, isConnected } = useWebSocket();
  const send = useSendVerification(client);

  const handleVerify = async () => {
    try {
      const result = await send('+1234567890');
      console.log('Verification result:', result);
    } catch (error) {
      console.error('Verification failed:', error);
    }
  };

  return <button onClick={handleVerify} disabled={!isConnected}>Verify</button>;
}
```

### Send Audio Stream

```javascript
import { useSendAudioChunk, useWebSocket } from './services/useWebSocket';

function AudioStreamComponent() {
  const { client, isConnected } = useWebSocket();
  const sendAudio = useSendAudioChunk(client);

  const sendAudioChunks = async () => {
    const audioData = new ArrayBuffer(4096);
    
    // Send chunk 1
    sendAudio(audioData, { chunk_number: 1 });
    
    // Send chunk 2
    sendAudio(audioData, { chunk_number: 2, final: true });
  };

  return <button onClick={sendAudioChunks} disabled={!isConnected}>Send Audio</button>;
}
```

### Listen to Events

```javascript
import { useWebSocketEvent, useWebSocket } from './services/useWebSocket';
import { EVENT_TYPES } from './services/webSocketConstants';

function EventComponent() {
  const { client } = useWebSocket();
  const [lastEvent, setLastEvent] = useState(null);

  useWebSocketEvent(client, EVENT_TYPES.CONNECTED, () => {
    setLastEvent('Connected to server');
  });

  useWebSocketEvent(client, EVENT_TYPES.ERROR, (error) => {
    setLastEvent(`Error: ${error.message}`);
  });

  return <p>{lastEvent}</p>;
}
```

### Listen to Message Types

```javascript
import { useWebSocketMessage, useWebSocket } from './services/useWebSocket';
import { MESSAGE_TYPES } from './services/webSocketConstants';

function MessageComponent() {
  const { client } = useWebSocket();
  const [response, setResponse] = useState(null);

  useWebSocketMessage(client, MESSAGE_TYPES.RESPONSE, (message) => {
    setResponse(message);
  });

  return <pre>{JSON.stringify(response, null, 2)}</pre>;
}
```

## API Reference

### WebSocketClientWrapper

#### Constructor
```javascript
new WebSocketClientWrapper(url, options)
```

**Options:**
- `maxConnectionAttempts` (number): Max reconnection attempts (default: 5)
- `initialReconnectDelay` (number): Initial reconnect delay in ms (default: 1000)
- `maxReconnectDelay` (number): Max reconnect delay in ms (default: 30000)
- `reconnectDelayMultiplier` (number): Exponential backoff multiplier (default: 1.5)
- `heartbeatInterval` (number): Heartbeat interval in ms (default: 30000)
- `heartbeatTimeout` (number): Heartbeat timeout in ms (default: 60000)
- `messageQueueMaxSize` (number): Max queued messages (default: 100)
- `maxMessageSize` (number): Max message size in bytes (default: 1MB)
- `connectionTimeout` (number): Connection timeout in ms (default: 10000)
- `debug` (boolean): Enable debug logging (default: false)

#### Methods

**Connection Management**
```javascript
await client.connect()              // Connect to server
client.disconnect()                 // Disconnect
client.isConnected()               // Check if connected
client.getState()                  // Get current state
client.getConnectionInfo()         // Get detailed info
client.waitForConnection(timeout)  // Wait until connected
```

**Sending Messages**
```javascript
client.sendMessage(message, options)           // Send message
await client.sendRequest(message, timeout)     // Send & wait for response
client.sendAudioChunk(audioData, metadata)    // Send audio chunk
client.sendVerification(phoneNumber)          // Request verification
client.sendEnrollment(phoneNumber)            // Request enrollment
client.sendReset()                            // Send reset command
```

**Message Handlers**
```javascript
client.on(messageType, handler)               // Listen for message type
client.on(eventType, handler)                 // Listen for event
client.off(eventType, handler)                // Unregister listener
client.once(eventType, handler)               // One-time listener
```

**Message Queue**
```javascript
client.getMessageQueueSize()       // Get queue size
client.clearMessageQueue()         // Clear all queued messages
```

**Lifecycle**
```javascript
client.destroy()                   // Clean up and destroy
```

#### Events (EVENT_TYPES)
```javascript
// Connection events
EVENT_TYPES.CONNECTED            // Connected
EVENT_TYPES.DISCONNECTED         // Disconnected
EVENT_TYPES.RECONNECT_ATTEMPT    // Reconnecting

// Message events
EVENT_TYPES.MESSAGE              // Message received
EVENT_TYPES.MESSAGE_SENT         // Message sent
EVENT_TYPES.MESSAGE_QUEUED       // Message queued

// State & Error events
EVENT_TYPES.STATE_CHANGED        // State changed
EVENT_TYPES.ERROR                // Error occurred
EVENT_TYPES.HEARTBEAT            // Heartbeat
```

#### Message Types (MESSAGE_TYPES)
```javascript
MESSAGE_TYPES.AUDIO              // Audio data
MESSAGE_TYPES.VERIFY             // Verification request
MESSAGE_TYPES.VERIFY_CONFIRMED   // Verification confirmed
MESSAGE_TYPES.ENROLL             // Enrollment request
MESSAGE_TYPES.ENROLLMENT_STATUS  // Enrollment status
MESSAGE_TYPES.ENROLLMENT_CONFIRMED  // Enrollment confirmed
MESSAGE_TYPES.PING               // Heartbeat ping
MESSAGE_TYPES.PONG               // Heartbeat pong
MESSAGE_TYPES.RESET              // Reset command
MESSAGE_TYPES.STATUS             // Status request
MESSAGE_TYPES.CONFIG             // Configuration
MESSAGE_TYPES.ERROR              // Error message
MESSAGE_TYPES.RESPONSE           // Generic response
```

#### Connection States (CONNECTION_STATES)
```javascript
CONNECTION_STATES.NOT_INITIALIZED  // Not yet initialized
CONNECTION_STATES.CONNECTING       // Connecting
CONNECTION_STATES.CONNECTED        // Connected
CONNECTION_STATES.DISCONNECTING    // Disconnecting
CONNECTION_STATES.DISCONNECTED     // Disconnected
CONNECTION_STATES.ERROR            // Error state
CONNECTION_STATES.RECONNECTING     // Attempting reconnection
```

## Examples

See `webSocketClientExamples.jsx` for complete examples:
1. **BasicWebSocketExample** - Connection status display
2. **SendMessagesExample** - Sending messages
3. **AudioStreamingExample** - Audio streaming
4. **VoiceVerificationExample** - Voice verification flow
5. **VoiceEnrollmentExample** - Voice enrollment flow
6. **EventMonitoringExample** - Event monitoring
7. **CompleteWebSocketApplication** - Full application

## Features

### 1. Automatic Reconnection
- Exponential backoff strategy
- Configurable max attempts
- Automatic message queue processing after reconnect

### 2. Message Queuing
- Queue messages while disconnected
- Automatic processing when connected
- Configurable queue size limit
- Event notification for queued messages

### 3. Heartbeat Mechanism
- Automatic keep-alive pings
- Configurable interval and timeout
- Automatic disconnect on timeout

### 4. Error Handling
- Connection errors
- Message send failures
- Invalid message format errors
- Request timeouts
- Queue full errors

### 5. Event System
- Connection events
- Message events
- State change events
- Error events
- Heartbeat events
- Reconnection events

### 6. Request-Response Pattern
- Send requests with unique IDs
- Wait for corresponding responses
- Automatic timeout handling
- Promise-based API

## Configuration

### Default Configuration

```javascript
{
  // Connection settings
  maxConnectionAttempts: 5,
  initialReconnectDelay: 1000,        // ms
  maxReconnectDelay: 30000,           // ms
  reconnectDelayMultiplier: 1.5,

  // Heartbeat/keep-alive
  heartbeatInterval: 30000,           // ms
  heartbeatTimeout: 60000,            // ms

  // Message settings
  maxMessageSize: 1024 * 1024,        // 1MB
  messageQueueMaxSize: 100,
  messageTimeout: 30000,              // ms

  // Connection timeout
  connectionTimeout: 10000,           // ms

  // Audio settings
  audioChunkSize: 4096,               // bytes
  audioSampleRate: 16000              // Hz
}
```

### Environment Variables

```.env
# WebSocket URL (optional)
REACT_APP_WS_URL=ws://localhost:8000/ws
# Or custom host
REACT_APP_WS_HOST=localhost:8000

# Debug mode
NODE_ENV=development  # Enables debug logging
```

## Backward Compatibility

The wrapper provides backward compatibility callbacks:
- `onOpen()` - Called when connected
- `onClose()` - Called when disconnected
- `onError(error)` - Called on error
- `onMessage(message)` - Called on message receive
- `onConnectionFailure()` - Called when max reconnect attempts reached

## Best Practices

1. **Always handle errors**
   ```javascript
   useWebSocketEvent(client, EVENT_TYPES.ERROR, (error) => {
     console.error('WebSocket error:', error);
   });
   ```

2. **Listen for disconnections**
   ```javascript
   useWebSocketEvent(client, EVENT_TYPES.DISCONNECTED, () => {
     console.log('Connection lost');
   });
   ```

3. **Check connection before sending critical messages**
   ```javascript
   if (client.isConnected()) {
     client.sendMessage(importantMessage);
   }
   ```

4. **Use request-response for critical operations**
   ```javascript
   try {
     const result = await client.sendRequest(message, 5000);
   } catch (error) {
     console.error('Request failed:', error);
   }
   ```

5. **Clean up on unmount**
   The `useWebSocket` hook handles this automatically.

6. **Monitor queue size**
   ```javascript
   if (client.getMessageQueueSize() > 50) {
     console.warn('High message queue - connection may be unstable');
   }
   ```

## Troubleshooting

### Connection Issues
- Check WebSocket URL configuration
- Verify backend server is running
- Check firewall/proxy settings
- Enable debug logging to see detailed logs

### Message Not Sending
- Verify client is connected: `client.isConnected()`
- Check message queue size: `client.getMessageQueueSize()`
- Monitor events for errors: `EVENT_TYPES.ERROR`

### Reconnection Loop
- Verify backend is accessible
- Check max connection attempts: `maxConnectionAttempts`
- Monitor reconnect events: `EVENT_TYPES.RECONNECT_ATTEMPT`

### High Memory Usage
- Clear old event listeners when done
- Monitor message queue size
- Call `client.destroy()` on component unmount

## Performance

- Lightweight: ~20KB minified
- No external dependencies (native WebSocket)
- Efficient event emitter
- Automatic cleanup and garbage collection
- Message queue prevents memory issues

## Security

- Supports WSS (secure WebSocket)
- Message validation
- Error boundary isolation
- No credentials in logs

## Testing

To test the client:

```javascript
// In test file
import WebSocketClientWrapper from './services/webSocketClientWrapper';

// Mock WebSocket
global.WebSocket = jest.fn();

// Create client and test
const client = new WebSocketClientWrapper('ws://localhost:8000/ws', {
  debug: true
});
```

## Migration from Old Client

Old API:
```javascript
const client = new WebSocketClient(url);
await client.connect();
client.sendMessage(message);
client.on('message_type', handler);
client.disconnect();
```

New API (forward compatible):
```javascript
const client = createWebSocketClient(url);
await client.connect();
client.sendMessage(message);
client.on('message_type', handler);  // Same
client.disconnect();
```

The new client is fully backward compatible with the old API while adding new features.
