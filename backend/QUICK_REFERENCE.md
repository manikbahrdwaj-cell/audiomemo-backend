# Session Manager - Quick Reference

## Installation & Setup

```javascript
const { SessionManager } = require('./session-manager');

const sessionManager = new SessionManager({
    sessionTimeout: 30 * 60 * 1000,  // 30 minutes
    cleanupInterval: 5 * 60 * 1000,  // 5 minutes
    maxSessions: 1000
});
```

## Core Methods

### Create Session
```javascript
const session = sessionManager.createSession('user123', {
    action: 'enrollment',
    language: 'en'
});
```

### Get Session
```javascript
const session = sessionManager.getSession(sessionId);
```

### Validate Session
```javascript
const { valid, message, session } = sessionManager.validateSession(sessionId);
if (valid) {
    // Use session
}
```

### Update Session
```javascript
sessionManager.updateSession(sessionId, {
    metadata: { step: 'processing' }
});
```

### Handle Audio
```javascript
// Append audio
const size = sessionManager.appendAudioData(sessionId, audioBuffer);

// Get audio
const audio = sessionManager.getAudioBuffer(sessionId);

// Clear audio
sessionManager.clearAudioBuffer(sessionId);
```

### Destroy Session
```javascript
sessionManager.destroySession(sessionId);

// Destroy all user sessions
sessionManager.destroyUserSessions(userId);
```

### Get Statistics
```javascript
const stats = sessionManager.getStatistics();
console.log(stats.activeSessions);
console.log(stats.totalUsers);
```

## WebSocket Integration Pattern

```javascript
wss.on('connection', (ws) => {
    ws.sessionId = null;

    ws.on('message', (data) => {
        const msg = JSON.parse(data);

        if (msg.type === 'init') {
            const session = sessionManager.createSession(msg.userId, {
                action: msg.action
            });
            ws.sessionId = session.sessionId;
        }

        if (msg.type === 'audio') {
            const validation = sessionManager.validateSession(ws.sessionId);
            if (validation.valid) {
                sessionManager.appendAudioData(ws.sessionId, msg.chunk);
            }
        }
    });

    ws.on('close', () => {
        sessionManager.destroySession(ws.sessionId);
    });
});
```

## Event Listeners

```javascript
// Session created
sessionManager.on('session:created', (data) => {
    console.log('Created:', data.sessionId);
});

// Session expired
sessionManager.on('session:expired', (data) => {
    console.log('Expired:', data.sessionId);
});

// Session destroyed
sessionManager.on('session:destroyed', (data) => {
    console.log('Destroyed:', data.sessionId);
});

// Cleanup completed
sessionManager.on('cleanup:completed', (data) => {
    console.log('Removed:', data.removedCount);
});
```

## Common Use Cases

### Express Middleware
```javascript
app.use((req, res, next) => {
    const sessionId = req.headers['x-session-id'];
    const validation = sessionManager.validateSession(sessionId);
    
    if (!validation.valid) {
        return res.status(401).json({ error: validation.message });
    }
    
    req.session = validation.session;
    next();
});
```

### Audio Processing
```javascript
async function processAudio(sessionId) {
    const audioBuffer = sessionManager.getAudioBuffer(sessionId);
    const embedding = await generateEmbedding(audioBuffer);
    sessionManager.clearAudioBuffer(sessionId);
    return embedding;
}
```

### Multi-User Management
```javascript
// Get all user sessions
const userSessions = sessionManager.getUserSessions(userId);

// Destroy all user sessions
sessionManager.destroyUserSessions(userId);

// Export session data
const exported = sessionManager.exportSession(sessionId);
```

## Configuration Presets

### Development
```javascript
new SessionManager({
    sessionTimeout: 10 * 60 * 1000,
    cleanupInterval: 2 * 60 * 1000
});
```

### Production
```javascript
new SessionManager({
    sessionTimeout: 30 * 60 * 1000,
    cleanupInterval: 5 * 60 * 1000,
    maxSessions: 5000
});
```

### High Load
```javascript
new SessionManager({
    sessionTimeout: 15 * 60 * 1000,
    cleanupInterval: 2 * 60 * 1000,
    maxSessions: 10000
});
```

## Error Handling

```javascript
// Pattern 1: Validation (recommended)
const validation = sessionManager.validateSession(sessionId);
if (!validation.valid) {
    console.error(validation.message);
    return;
}

// Pattern 2: Try-Catch
try {
    sessionManager.appendAudioData(sessionId, chunk);
} catch (error) {
    console.error('Error:', error.message);
}
```

## Performance Tips

1. **Always validate before operations**
   ```javascript
   if (sessionManager.validateSession(id).valid) { ... }
   ```

2. **Listen to events for cleanup**
   ```javascript
   sessionManager.on('session:expired', cleanup);
   ```

3. **Monitor statistics**
   ```javascript
   setInterval(() => {
       console.log(sessionManager.getStatistics());
   }, 60000);
   ```

4. **Graceful shutdown**
   ```javascript
   process.on('SIGTERM', () => sessionManager.shutdown());
   ```

## Session Object Properties

```javascript
{
    sessionId: 'sess_1707...',
    userId: 'user123',
    createdAt: 1707411234567,
    lastActivity: 1707411234567,
    expiresAt: 1707413034567,
    status: 'active',              // 'active', 'expired', 'destroyed'
    ipAddress: '192.168.1.1',
    userAgent: 'Mozilla/5.0',
    audioBuffer: Buffer,           // Audio data
    metadata: {
        action: 'enrollment',
        language: 'en',
        connectionId: 'ws_001',
        // Custom fields...
    }
}
```

## Files Included

- **session-manager.js** - Core SessionManager class
- **session-manager-examples.js** - 10 detailed usage examples
- **test-session-manager.js** - 30 comprehensive tests
- **SESSION_MANAGER_README.md** - Full documentation
- **INTEGRATION_GUIDE.md** - Step-by-step integration instructions
- **QUICK_REFERENCE.md** - This file

## Running Tests & Examples

```bash
# Run tests
node test-session-manager.js

# Run examples (uncomment in file to run)
node session-manager-examples.js

# In your code
const { exampleBasicInitialization } = require('./session-manager-examples');
exampleBasicInitialization();
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Session not found | Check sessionId is correct, may have expired |
| Sessions expire too fast | Increase `sessionTimeout` value |
| Memory grows | Verify `destroySession()` called on disconnect |
| No cleanup events | Check `cleanupInterval` config and setup |
| Audio buffer too large | Implement size limits in application |

## Next Steps

1. Review `SESSION_MANAGER_README.md` for full API
2. Follow `INTEGRATION_GUIDE.md` for integration steps
3. Run `test-session-manager.js` to verify setup
4. Review `session-manager-examples.js` for patterns
5. Integrate into your WebSocket handler

## Support

- Full documentation: `SESSION_MANAGER_README.md`
- Integration guide: `INTEGRATION_GUIDE.md`
- Code examples: `session-manager-examples.js`
- Test suite: `test-session-manager.js`

## Version

Session Manager v1.0.0

## License

MIT
