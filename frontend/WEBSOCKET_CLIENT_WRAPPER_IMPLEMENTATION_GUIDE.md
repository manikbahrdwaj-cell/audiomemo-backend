# WebSocket Client Wrapper - Implementation Guide

## Overview
This guide provides step-by-step instructions for integrating the WebSocket Client Wrapper into your React application.

## Files Created

1. **webSocketClientWrapper.js** - Main client class
2. **webSocketConstants.js** - Constants and configuration
3. **webSocketEventEmitter.js** - Event management utility
4. **useWebSocket.js** - React hooks
5. **webSocketClientExamples.jsx** - Usage examples
6. **webSocketClientWrapper.test.js** - Test suite

## Checklist for Integration

### Phase 1: Setup

- [ ] Review the files created in `/frontend/src/services/`
- [ ] Configure WebSocket URL in `.env`:
  ```env
  REACT_APP_WS_URL=ws://localhost:8000/ws
  # or
  REACT_APP_WS_HOST=localhost:8000
  ```
- [ ] Enable React StrictMode compatibility (double renders are expected)

### Phase 2: Basic Connection

- [ ] Test basic connection with a simple component:
  ```javascript
  import { useWebSocket } from './services/useWebSocket';

  function TestConnection() {
    const { client, isConnected, state } = useWebSocket();
    return <p>{isConnected ? 'Connected' : 'Not connected'}</p>;
  }
  ```
- [ ] Verify WebSocket connects successfully
- [ ] Test manual disconnect/reconnect
- [ ] Verify error handling and reconnection attempts

### Phase 3: Message Handling

- [ ] Implement message sending:
  ```javascript
  const sendMessage = useSendWebSocketMessage(client);
  sendMessage({ type: 'ping' });
  ```
- [ ] Implement message listening:
  ```javascript
  useWebSocketMessage(client, MESSAGE_TYPES.RESPONSE, handler);
  ```
- [ ] Implement event listening:
  ```javascript
  useWebSocketEvent(client, EVENT_TYPES.CONNECTED, handler);
  ```
- [ ] Test request-response pattern:
  ```javascript
  const response = await client.sendRequest(message);
  ```

### Phase 4: Audio Streaming

- [ ] Implement audio chunk sending:
  ```javascript
  const sendAudio = useSendAudioChunk(client);
  sendAudio(audioBuffer, { chunk_number: 1 });
  ```
- [ ] Verify audio chunks are being sent during recording
- [ ] Test streaming with various buffer sizes
- [ ] Monitor message queue during streaming

### Phase 5: Verification Flow

- [ ] Implement verification request:
  ```javascript
  const sendVerification = useSendVerification(client);
  const result = await sendVerification(phoneNumber);
  ```
- [ ] Handle verification responses
- [ ] Implement error handling for failed verifications
- [ ] Test with multiple phone numbers

### Phase 6: Enrollment Flow

- [ ] Implement enrollment request:
  ```javascript
  const sendEnrollment = useSendEnrollment(client);
  const result = await sendEnrollment(phoneNumber);
  ```
- [ ] Handle enrollment status updates
- [ ] Implement progress tracking
- [ ] Test with various audio inputs

### Phase 7: Error Handling

- [ ] Implement error event handler:
  ```javascript
  useWebSocketEvent(client, EVENT_TYPES.ERROR, handleError);
  ```
- [ ] Handle each error code appropriately
- [ ] Implement user-friendly error messages
- [ ] Test error recovery

### Phase 8: Connection Management

- [ ] Monitor connection state:
  ```javascript
  const info = client.getConnectionInfo();
  ```
- [ ] Implement connection status UI
- [ ] Display message queue size in debug mode
- [ ] Monitor reconnection attempts

### Phase 9: Testing

- [ ] Run unit tests:
  ```bash
  npm test -- webSocketClientWrapper.test.js
  ```
- [ ] Test with mock WebSocket
- [ ] Test with real backend
- [ ] Load test with rapid messages
- [ ] Test network disconnection scenarios

### Phase 10: Optimization

- [ ] Monitor memory usage
- [ ] Check for memory leaks
- [ ] Verify garbage collection
- [ ] Test with large audio files
- [ ] Profile event emitter performance

### Phase 11: Documentation

- [ ] Complete API documentation
- [ ] Add code comments for complex logic
- [ ] Update project README with WebSocket usage
- [ ] Create developer setup guide
- [ ] Document environment variables

### Phase 12: Deployment

- [ ] Configure production WebSocket URL
- [ ] Test with production backend
- [ ] Enable/disable debug logging
- [ ] Verify SSL/TLS for WSS
- [ ] Monitor production errors

## Common Tasks

### Task: Add New Message Type

1. Add to `MESSAGE_TYPES` in `webSocketConstants.js`
2. Create handler function in component
3. Listen with: `client.on(messageType, handler)`
4. Send with: `client.sendMessage({ type: messageType })`

**Example:**
```javascript
// In webSocketConstants.js
export const MESSAGE_TYPES = {
  // ... existing types
  CUSTOM: 'custom'
};

// In component
client.on(MESSAGE_TYPES.CUSTOM, (message) => {
  console.log('Custom message received:', message);
});
```

### Task: Add New Event Type

1. Add to `EVENT_TYPES` in `webSocketConstants.js`
2. Emit in appropriate location in WebSocketClientWrapper
3. Listen with: `client.on(eventType, handler)`

**Example:**
```javascript
// In webSocketConstants.js
export const EVENT_TYPES = {
  // ... existing types
  CUSTOM_EVENT: 'custom_event'
};

// In WebSocketClientWrapper
this.emit(EVENT_TYPES.CUSTOM_EVENT, data);

// In component
useWebSocketEvent(client, EVENT_TYPES.CUSTOM_EVENT, handler);
```

### Task: Modify Connection Behavior

1. Update options in `WebSocketClientWrapper` constructor
2. Pass options when creating client:
   ```javascript
   const { client } = useWebSocket(url, {
     maxConnectionAttempts: 10,
     heartbeatInterval: 60000
   });
   ```

### Task: Debug Connection Issues

1. Enable debug mode:
   ```env
   NODE_ENV=development
   ```
2. Check console for detailed logs
3. Monitor events:
   ```javascript
   client.on(EVENT_TYPES.ERROR, console.error);
   ```
4. Check connection info:
   ```javascript
   console.log(client.getConnectionInfo());
   ```

### Task: Handle Offline Scenarios

1. Listen for disconnect:
   ```javascript
   useWebSocketEvent(client, EVENT_TYPES.DISCONNECTED, handleOffline);
   ```
2. Queue messages automatically:
   ```javascript
   client.sendMessage(message, { queue: true });
   ```
3. Process queue on reconnect (automatic)
4. Notify user of offline state

## API Reference Summary

### Client Methods

- `await client.connect()` - Connect
- `client.disconnect()` - Disconnect
- `client.sendMessage(msg, opts)` - Send message
- `await client.sendRequest(msg, timeout)` - Send request
- `client.sendAudioChunk(data, meta)` - Send audio
- `client.sendVerification(phone)` - Request verification
- `client.sendEnrollment(phone)` - Request enrollment
- `client.on(type, handler)` - Register listener
- `client.isConnected()` - Check connection
- `client.getState()` - Get state
- `client.getConnectionInfo()` - Get info
- `client.destroy()` - Clean up

### React Hooks

- `useWebSocket()` - Main connection hook
- `useWebSocketMessage()` - Listen for messages
- `useWebSocketEvent()` - Listen for events
- `useSendWebSocketMessage()` - Send message
- `useSendWebSocketRequest()` - Send request
- `useSendAudioChunk()` - Send audio
- `useSendVerification()` - Verify
- `useSendEnrollment()` - Enroll

### Constants

- `MESSAGE_TYPES` - Message type values
- `EVENT_TYPES` - Event type values
- `CONNECTION_STATES` - Connection state values
- `ERROR_CODES` - Error code values
- `CONFIG_DEFAULTS` - Default configuration

## Troubleshooting

### Symptom: "WebSocket not connected" errors

**Solution:**
1. Check WebSocket URL configuration
2. Verify backend is running
3. Check firewall/proxy settings
4. Enable debug mode to see detailed logs

### Symptom: Messages not being sent

**Solution:**
1. Verify `client.isConnected()` is true
2. Check error events
3. Monitor message queue size
4. Check message size limits

### Symptom: Connection keeps disconnecting

**Solution:**
1. Verify heartbeat timeout is reasonable
2. Check backend for timeout settings
3. Look for pong response issues
4. Check for exception in message handlers

### Symptom: Memory leaks

**Solution:**
1. Ensure components unmount properly
2. Call cleanup in useEffect
3. Check for circular references in listeners
4. Monitor listener count

### Symptom: Messages arriving out of order

**Solution:**
1. Normal for async messaging - add sequence numbers
2. Use request-response for order-critical operations
3. Implement message queuing on client side

## Performance Tips

1. **Batch Audio Chunks**: Group small audio chunks into larger messages
2. **Use Request-Response**: For critical operations that need ordering
3. **Monitor Queue Size**: Alert if queue exceeds 50 messages
4. **Clean Up Listeners**: Remove listeners when no longer needed
5. **Use React Keys**: Ensure proper component rendering

## Security Considerations

1. **Use WSS**: Always use secure WebSocket (wss://) in production
2. **Validate Messages**: Always validate received messages
3. **Sanitize Data**: Sanitize user input before sending
4. **No Credentials in Logs**: Avoid logging sensitive data
5. **Error Handling**: Don't expose sensitive error details to users

## Next Steps

1. Integrate into main application components
2. Replace old WebSocket client (`websocketClient.js`)
3. Update components that use old client
4. Test thoroughly with backend
5. Deploy to production with monitoring
6. Gather metrics on connection stability
7. Optimize based on real-world usage

## Support

Refer to:
- `WEBSOCKET_CLIENT_WRAPPER_GUIDE.md` - Full documentation
- `WEBSOCKET_CLIENT_WRAPPER_QUICK_REFERENCE.md` - Quick reference
- `webSocketClientExamples.jsx` - Code examples
- `webSocketClientWrapper.test.js` - Test examples

## Migration from Old Client

If migrating from the old `WebSocketClient`:

1. **Old API:**
   ```javascript
   const client = new WebSocketClient(url);
   await client.connect();
   client.sendMessage(msg);
   client.on('message_type', handler);
   ```

2. **New API (backward compatible):**
   ```javascript
   const client = createWebSocketClient(url);
   await client.connect();
   client.sendMessage(msg);
   client.on('message_type', handler);  // Same!
   ```

3. **New Features to Use:**
   - React hooks instead of manual connection management
   - Event system for better control
   - Request-response pattern for critical operations
   - Better error handling

4. **Gradual Migration:**
   - Start new components with hooks
   - Migrate existing components gradually
   - Keep both clients during transition
   - Use feature flags if needed

---

**Last Updated:** 2024-02-14
**Status:** Ready for Integration
