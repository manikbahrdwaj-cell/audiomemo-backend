# Session Manager - Documentation

## Overview

`session-manager.js` is a robust session management module for the Voice Biometric Authentication system. It handles user session lifecycle, including creation, validation, updates, expiration, and cleanup.

## Features

- **Session Creation**: Create unique sessions with user identification and custom metadata
- **Session Storage**: In-memory session storage with optional persistence
- **Activity Tracking**: Automatic tracking of last activity and session expiration
- **Timeout Management**: Automatic session timeout and cleanup
- **Audio Buffer Management**: Store and manage audio data per session
- **Event System**: Built-in event emitters for session lifecycle hooks
- **Statistics**: Real-time session statistics and monitoring
- **Multi-user Support**: Manage multiple sessions per user efficiently
- **Validation**: Comprehensive session validation and status checking
- **Persistence**: Optional persistence store for session data

## Installation

The Session Manager is already included in the backend. No additional dependencies required beyond Node.js built-ins.

### Dependencies

```json
{
  "dependencies": {}
}
```

No external dependencies - uses only Node.js built-in modules:
- `crypto` - Session ID generation
- `events` - EventEmitter for lifecycle hooks

## Quick Start

### Basic Usage

```javascript
const { SessionManager } = require('./session-manager');

// Initialize the Session Manager
const sessionManager = new SessionManager({
    sessionTimeout: 30 * 60 * 1000, // 30 minutes
    cleanupInterval: 5 * 60 * 1000,  // 5 minutes
    maxSessions: 1000
});

// Create a session
const session = sessionManager.createSession('user123', {
    action: 'enrollment',
    language: 'en',
    ipAddress: '192.168.1.1'
});

console.log('Session ID:', session.sessionId);
```

## API Reference

### Constructor

```javascript
new SessionManager(options)
```

**Options:**
- `sessionTimeout` (number): Session timeout in milliseconds (default: 30 minutes)
- `cleanupInterval` (number): Cleanup interval in milliseconds (default: 5 minutes)
- `maxSessions` (number): Maximum allowed sessions (default: 1000)
- `enablePersistence` (boolean): Enable session persistence (default: false)
- `persistenceStore` (object): Persistence store implementation (default: null)

### Session Creation

#### `createSession(userId, data)`

Creates a new user session.

**Parameters:**
- `userId` (string, required): Unique user identifier
- `data` (object, optional): Session metadata
  - `action` (string): Action type ('enrollment', 'verification', etc.)
  - `language` (string): Language preference (default: 'en')
  - `ipAddress` (string): Client IP address
  - `userAgent` (string): Client user agent
  - `connectionId` (string): WebSocket/connection identifier
  - Additional custom fields allowed

**Returns:** Session object
```javascript
{
    sessionId: 'sess_1707...abc',
    userId: 'user123',
    createdAt: 1707411234567,
    lastActivity: 1707411234567,
    expiresAt: 1707413034567,
    status: 'active',
    ipAddress: '192.168.1.1',
    userAgent: null,
    audioBuffer: Buffer.alloc(0),
    metadata: {
        action: 'enrollment',
        language: 'en',
        ...
    }
}
```

**Example:**
```javascript
const session = sessionManager.createSession('user123', {
    action: 'enrollment',
    language: 'es',
    ipAddress: '192.168.1.100'
});
```

### Session Retrieval

#### `getSession(sessionId)`

Retrieves an active session by ID.

**Parameters:**
- `sessionId` (string, required): Session identifier

**Returns:** Session object or null if not found/expired

**Example:**
```javascript
const session = sessionManager.getSession('sess_1707...abc');
if (session) {
    console.log('User:', session.userId);
}
```

#### `getUserSessions(userId)`

Retrieves all active sessions for a specific user.

**Parameters:**
- `userId` (string, required): User identifier

**Returns:** Array of session objects

**Example:**
```javascript
const userSessions = sessionManager.getUserSessions('user123');
console.log(`User has ${userSessions.length} active sessions`);
```

### Session Updates

#### `updateSession(sessionId, updates)`

Updates session data and extends expiration time.

**Parameters:**
- `sessionId` (string, required): Session identifier
- `updates` (object, optional): Fields to update
  - `metadata` (object): Merge with existing metadata
  - Other fields: Direct replacement

**Returns:** Updated session object or null if not found

**Example:**
```javascript
const updated = sessionManager.updateSession(sessionId, {
    metadata: {
        recordingDuration: 5000,
        step: 'processing'
    }
});
```

### Audio Buffer Management

#### `appendAudioData(sessionId, audioChunk)`

Appends audio data to session buffer.

**Parameters:**
- `sessionId` (string, required): Session identifier
- `audioChunk` (Buffer, required): Audio data chunk

**Returns:** Total buffer size in bytes

**Throws:** Error if session not found or invalid chunk

**Example:**
```javascript
const audioChunk = Buffer.from(audioData);
const totalSize = sessionManager.appendAudioData(sessionId, audioChunk);
console.log(`Total audio: ${totalSize} bytes`);
```

#### `getAudioBuffer(sessionId)`

Retrieves the complete audio buffer from a session.

**Parameters:**
- `sessionId` (string, required): Session identifier

**Returns:** Buffer object or null if not found

**Example:**
```javascript
const audioBuffer = sessionManager.getAudioBuffer(sessionId);
if (audioBuffer) {
    // Process audio...
}
```

#### `clearAudioBuffer(sessionId)`

Clears the audio buffer for a session.

**Parameters:**
- `sessionId` (string, required): Session identifier

**Returns:** Boolean success status

**Example:**
```javascript
const cleared = sessionManager.clearAudioBuffer(sessionId);
console.log('Buffer cleared:', cleared);
```

### Session Validation

#### `validateSession(sessionId)`

Validates session status and expiration.

**Parameters:**
- `sessionId` (string, required): Session identifier

**Returns:** Validation object
```javascript
{
    valid: boolean,
    message: string,
    session: Session|null
}
```

**Example:**
```javascript
const validation = sessionManager.validateSession(sessionId);
if (validation.valid) {
    console.log('Session is valid:', validation.session.userId);
} else {
    console.log('Validation failed:', validation.message);
}
```

### Session Destruction

#### `destroySession(sessionId)`

Immediately destroys a session and releases resources.

**Parameters:**
- `sessionId` (string, required): Session identifier

**Returns:** Boolean success status

**Example:**
```javascript
const destroyed = sessionManager.destroySession(sessionId);
if (destroyed) {
    console.log('Session destroyed');
}
```

#### `destroyUserSessions(userId)`

Destroys all sessions for a specific user.

**Parameters:**
- `userId` (string, required): User identifier

**Returns:** Number of destroyed sessions

**Example:**
```javascript
const count = sessionManager.destroyUserSessions('user123');
console.log(`Destroyed ${count} sessions`);
```

### Statistics & Monitoring

#### `getStatistics()`

Returns current session statistics.

**Returns:** Statistics object
```javascript
{
    totalSessions: number,
    activeSessions: number,
    expiredSessions: number,
    destroyedSessions: number,
    totalUsers: number,
    sessionsByStatus: {...}
}
```

**Example:**
```javascript
const stats = sessionManager.getStatistics();
console.log('Active sessions:', stats.activeSessions);
console.log('Total users:', stats.totalUsers);
```

#### `exportSession(sessionId)`

Exports session data in a serializable format (excludes raw buffers).

**Parameters:**
- `sessionId` (string, required): Session identifier

**Returns:** Sanitized session object or null

**Example:**
```javascript
const exported = sessionManager.exportSession(sessionId);
console.log(JSON.stringify(exported)); // Safe to serialize
```

### Lifecycle Management

#### `clearAllSessions()`

Clears all sessions (useful for testing or shutdown).

**Returns:** void

**Example:**
```javascript
sessionManager.clearAllSessions();
```

#### `shutdown()`

Gracefully shuts down the session manager.

**Returns:** void

**Example:**
```javascript
sessionManager.shutdown();
```

## Events

The SessionManager extends Node.js EventEmitter and emits lifecycle events.

### Supported Events

#### `session:created`
Emitted when a new session is created.
```javascript
sessionManager.on('session:created', (data) => {
    console.log('Session created:', data.sessionId, 'for user:', data.userId);
});
```

#### `session:updated`
Emitted when a session is updated.
```javascript
sessionManager.on('session:updated', (data) => {
    console.log('Session updated:', data.sessionId);
});
```

#### `session:expired`
Emitted when a session expires.
```javascript
sessionManager.on('session:expired', (data) => {
    console.log('Session expired:', data.sessionId);
});
```

#### `session:destroyed`
Emitted when a session is destroyed.
```javascript
sessionManager.on('session:destroyed', (data) => {
    console.log('Session destroyed:', data.sessionId);
});
```

#### `cleanup:completed`
Emitted when automatic cleanup removes expired sessions.
```javascript
sessionManager.on('cleanup:completed', (data) => {
    console.log('Cleanup removed', data.removedCount, 'sessions');
});
```

#### `all-sessions:cleared`
Emitted when all sessions are cleared.
```javascript
sessionManager.on('all-sessions:cleared', (data) => {
    console.log('All', data.count, 'sessions cleared');
});
```

## Integration Examples

### WebSocket Handler Integration

```javascript
const { SessionManager } = require('./session-manager');
const sessionManager = new SessionManager();

// In WebSocket connection handler
wss.on('connection', (ws) => {
    // Client sends initialization
    ws.on('message', (data) => {
        const message = JSON.parse(data);
        
        if (message.type === 'init') {
            const session = sessionManager.createSession(message.userId, {
                action: message.action,
                connectionId: ws.id,
                userAgent: message.userAgent
            });
            
            ws.sessionId = session.sessionId;
            ws.send(JSON.stringify({
                type: 'session-ready',
                sessionId: session.sessionId
            }));
        }
        
        if (message.type === 'audio-chunk') {
            const validation = sessionManager.validateSession(ws.sessionId);
            if (validation.valid) {
                sessionManager.appendAudioData(ws.sessionId, message.chunk);
            }
        }
    });
    
    ws.on('close', () => {
        sessionManager.destroySession(ws.sessionId);
    });
});
```

### Express Middleware Integration

```javascript
const sessionManager = new SessionManager();

// Middleware to validate session
app.use('/api/', (req, res, next) => {
    const sessionId = req.headers['x-session-id'];
    const validation = sessionManager.validateSession(sessionId);
    
    if (!validation.valid) {
        return res.status(401).json({ error: validation.message });
    }
    
    req.session = validation.session;
    next();
});

app.post('/api/submit-audio', (req, res) => {
    const audioBuffer = Buffer.from(req.body.audio, 'base64');
    
    try {
        sessionManager.appendAudioData(req.session.sessionId, audioBuffer);
        res.json({ success: true, size: req.session.audioBuffer.length });
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});
```

## Persistence

### Using Custom Persistence Store

```javascript
// Implement your own persistence store
class DatabasePersistenceStore {
    async save(sessionId, session) {
        await db.sessions.insert({ _id: sessionId, ...session });
    }
    
    async update(sessionId, session) {
        await db.sessions.updateOne({ _id: sessionId }, { $set: session });
    }
    
    async get(sessionId) {
        return db.sessions.findOne({ _id: sessionId });
    }
    
    async delete(sessionId) {
        await db.sessions.deleteOne({ _id: sessionId });
    }
    
    async getAll() {
        return db.sessions.find({}).toArray();
    }
    
    clear() {
        return db.sessions.deleteMany({});
    }
}

// Use with SessionManager
const store = new DatabasePersistenceStore();
const sessionManager = new SessionManager({
    enablePersistence: true,
    persistenceStore: store
});
```

## Error Handling

```javascript
try {
    // Session creation
    const session = sessionManager.createSession(userId, data);
} catch (error) {
    console.error('Session creation failed:', error.message);
    // Likely cause: maxSessions limit reached
}

try {
    // Audio append
    sessionManager.appendAudioData(sessionId, chunk);
} catch (error) {
    console.error('Audio append failed:', error.message);
    // Likely causes: Session expired, invalid chunk
}

// Validation pattern (preferred for non-critical errors)
const validation = sessionManager.validateSession(sessionId);
if (!validation.valid) {
    console.warn('Session validation failed:', validation.message);
}
```

## Best Practices

1. **Always validate sessions before operations:**
   ```javascript
   const validation = sessionManager.validateSession(sessionId);
   if (validation.valid) {
       // Proceed with operation
   }
   ```

2. **Listen to expiration events:**
   ```javascript
   sessionManager.on('session:expired', (data) => {
       // Notify client, cleanup resources
   });
   ```

3. **Use appropriate timeout values:**
   ```javascript
   // Short timeout for mobile/unstable connections
   const sessionManager = new SessionManager({
       sessionTimeout: 10 * 60 * 1000 // 10 minutes
   });
   ```

4. **Monitor statistics in production:**
   ```javascript
   setInterval(() => {
       const stats = sessionManager.getStatistics();
       console.log('Current sessions:', stats.activeSessions);
   }, 60000); // Every minute
   ```

5. **Gracefully shutdown:**
   ```javascript
   process.on('SIGTERM', () => {
       sessionManager.shutdown();
       server.close();
   });
   ```

## Testing

Run the comprehensive test suite:

```bash
node test-session-manager.js
```

Run example demonstrations:

```bash
node session-manager-examples.js
```

## Performance Considerations

- **Memory**: Each session stores metadata, audio buffer, and timeout handles
- **CPU**: Cleanup interval uses configurable interval (default 5 minutes)
- **Scalability**: Designed to handle 1000+ concurrent sessions
- **Audio Buffer**: No automatic size limits; implement application-level limits

## Troubleshooting

### Session expires unexpectedly
- Check `sessionTimeout` configuration
- Verify `updateSession()` is called on activity
- Check system clock accuracy

### Memory usage grows
- Ensure `destroySession()` is called on disconnect
- Verify cleanup interval is running
- Check for audio buffer accumulation

### Session not found
- Verify session ID is correct
- Check if session has already expired
- Use `validateSession()` for debugging

## Migration from Current Code

To migrate from the existing websocket-handler.js session management:

```javascript
// OLD: Direct session storage in connections map
const connections = new Map();
connections.set(clientId, {
    id: clientId,
    sessionData: { userId, action, ... }
});

// NEW: Use SessionManager
const sessionManager = new SessionManager();
const session = sessionManager.createSession(userId, {
    action,
    connectionId: clientId
});
```

## License

MIT

## Support

For issues or questions, refer to the examples and test files:
- `session-manager-examples.js` - 10 detailed usage examples
- `test-session-manager.js` - 30 comprehensive tests
