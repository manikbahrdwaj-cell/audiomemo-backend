# Session Manager Integration Guide

## Overview

This guide shows how to integrate the new `SessionManager` into your existing WebSocket server and API endpoints, replacing the current basic session tracking with a robust session management system.

## Current Architecture

Your current `websocket-handler.js` uses a basic session tracking approach:

```javascript
const connections = new Map();

wss.on('connection', (ws, req) => {
    const clientId = generateClientId();
    const clientConnection = {
        id: clientId,
        ws,
        audioBuffer: Buffer.alloc(0),
        sessionData: {
            userId: null,
            action: null,
            startTime: Date.now(),
        }
    };

    connections.set(clientId, clientConnection);
    // ... rest of code
});
```

## New Architecture with SessionManager

The SessionManager provides a more robust, scalable approach with built-in timeout management, persistence support, and event handling.

## Integration Steps

### Step 1: Import SessionManager

At the top of `websocket-handler.js`:

```javascript
const { SessionManager, MemoryPersistenceStore } = require('./session-manager');

// Create a global session manager instance
const sessionManager = new SessionManager({
    sessionTimeout: 30 * 60 * 1000,  // 30 minutes
    cleanupInterval: 5 * 60 * 1000,  // 5 minutes cleanup
    maxSessions: 1000                 // Maximum concurrent sessions
});

// Optional: Enable persistence
// const persistenceStore = new MemoryPersistenceStore();
// sessionManager.enablePersistence = true;
// sessionManager.persistenceStore = persistenceStore;
```

### Step 2: Update Connection Handler

Replace the connection handler to use SessionManager:

```javascript
// OLD CODE (Remove):
const connections = new Map();

wss.on('connection', (ws, req) => {
    const clientId = generateClientId();
    const clientConnection = {
        id: clientId,
        ws,
        audioBuffer: Buffer.alloc(0),
        sessionData: {
            userId: null,
            action: null,
            startTime: Date.now(),
        }
    };
    connections.set(clientId, clientConnection);
    // ...
});

// NEW CODE (Replace with):
wss.on('connection', (ws, req) => {
    const clientId = generateClientId();
    ws.clientId = clientId;
    ws.sessionId = null;  // Will be set on session init

    // Store minimal connection info
    const clientIp = req.socket.remoteAddress || 'unknown';
    ws.clientIp = clientIp;

    console.log(`[WS] Client connected: ${clientId} from ${clientIp}`);

    sendMessage(ws, {
        type: 'connection',
        clientId,
        message: 'Connected to WebSocket server'
    });

    // Message handler
    ws.on('message', async (data) => {
        try {
            if (typeof data === 'string') {
                handleTextMessage(ws, JSON.parse(data));
            } else if (Buffer.isBuffer(data)) {
                handleAudioData(ws, data);
            }
        } catch (error) {
            console.error(`[WS] Error handling message from ${clientId}:`, error.message);
            sendError(ws, 'Failed to process message', error.message);
        }
    });

    // Handle disconnection
    ws.on('close', () => {
        console.log(`[WS] Client disconnected: ${clientId}`);
        if (ws.sessionId) {
            sessionManager.destroySession(ws.sessionId);
        }
    });

    // Handle errors
    ws.on('error', (error) => {
        console.error(`[WS] Connection error for ${clientId}:`, error.message);
        if (ws.sessionId) {
            sessionManager.destroySession(ws.sessionId);
        }
    });
});
```

### Step 3: Update Text Message Handler

```javascript
// OLD CODE (Example):
function handleTextMessage(ws, clientConnection, message) {
    const { type, userId, action, language = 'en' } = message;

    switch (type) {
        case 'init':
            handleInitialization(ws, clientConnection, { userId, action, language });
            break;
        // ... other cases
    }
}

// NEW CODE (Replace with):
function handleTextMessage(ws, message) {
    const { type, userId, action, language = 'en' } = message;

    switch (type) {
        case 'init':
            handleInitialization(ws, { userId, action, language });
            break;

        case 'start-enrollment':
            handleStartEnrollment(ws);
            break;

        case 'start-verification':
            handleStartVerification(ws, { userId });
            break;

        case 'stop-audio':
            handleStopAudio(ws);
            break;

        case 'get-status':
            handleGetStatus(ws);
            break;

        case 'ping':
            sendMessage(ws, { type: 'pong', timestamp: Date.now() });
            break;

        default:
            sendError(ws, 'Unknown message type', `Type: ${type}`);
    }
}
```

### Step 4: Update Session Initialization

```javascript
// OLD CODE:
function handleInitialization(ws, clientConnection, { userId, action, language }) {
    clientConnection.sessionData.userId = userId;
    clientConnection.sessionData.action = action;
    clientConnection.sessionData.language = language;
    clientConnection.sessionData.startTime = Date.now();
    clientConnection.audioBuffer = Buffer.alloc(0);

    sendMessage(ws, {
        type: 'initialized',
        userId,
        action,
        message: `Session initialized for ${action}`
    });
}

// NEW CODE:
function handleInitialization(ws, { userId, action, language }) {
    try {
        // Create session in SessionManager
        const session = sessionManager.createSession(userId, {
            action,
            language,
            ipAddress: ws.clientIp,
            connectionId: ws.clientId
        });

        // Store session ID on WebSocket
        ws.sessionId = session.sessionId;

        sendMessage(ws, {
            type: 'initialized',
            sessionId: session.sessionId,
            userId,
            action,
            message: `Session initialized for ${action}`
        });

        console.log(`[WS] Session initialized - User: ${userId}, Action: ${action}, SessionId: ${session.sessionId}`);
    } catch (error) {
        sendError(ws, 'Session initialization failed', error.message);
    }
}
```

### Step 5: Update Enrollment Handler

```javascript
// OLD CODE:
function handleStartEnrollment(ws, clientConnection) {
    const { userId } = clientConnection.sessionData;

    if (!userId) {
        sendError(ws, 'User ID not set', 'Call init first with userId');
        return;
    }

    clientConnection.sessionData.enrollmentStart = Date.now();

    sendMessage(ws, {
        type: 'enrollment-started',
        message: 'Start speaking for enrollment'
    });
}

// NEW CODE:
function handleStartEnrollment(ws) {
    // Validate session
    const validation = sessionManager.validateSession(ws.sessionId);
    if (!validation.valid) {
        sendError(ws, validation.message, 'Please initialize session first');
        return;
    }

    const session = validation.session;

    // Verify session is for enrollment
    if (session.metadata.action !== 'enrollment') {
        sendError(ws, 'Invalid action', 'Session is not configured for enrollment');
        return;
    }

    // Update session metadata
    sessionManager.updateSession(ws.sessionId, {
        metadata: {
            enrollmentStart: Date.now(),
            audioChunkCount: 0
        }
    });

    sendMessage(ws, {
        type: 'enrollment-started',
        sessionId: ws.sessionId,
        userId: session.userId,
        message: 'Start speaking for enrollment'
    });

    console.log(`[WS] Enrollment started for user: ${session.userId}`);
}
```

### Step 6: Update Verification Handler

```javascript
// OLD CODE:
async function handleStartVerification(ws, clientConnection, { userId }) {
    const { userId: sessionUserId } = clientConnection.sessionData;
    // ... verification logic
}

// NEW CODE:
async function handleStartVerification(ws, { userId }) {
    // Validate session
    const validation = sessionManager.validateSession(ws.sessionId);
    if (!validation.valid) {
        sendError(ws, validation.message, 'Please initialize session first');
        return;
    }

    const session = validation.session;

    // Verify session is for verification
    if (session.metadata.action !== 'verification') {
        sendError(ws, 'Invalid action', 'Session is not configured for verification');
        return;
    }

    // Update session metadata
    sessionManager.updateSession(ws.sessionId, {
        metadata: {
            enrollmentStart: Date.now(),
            targetUserId: userId,
            audioChunkCount: 0
        }
    });

    // Check if user is enrolled (your existing logic)
    try {
        const isEnrolled = await checkUserEnrollment(userId);
        if (!isEnrolled) {
            sendError(ws, 'User not enrolled', `${userId} is not enrolled in the system`);
            return;
        }

        sendMessage(ws, {
            type: 'verification-started',
            sessionId: ws.sessionId,
            userId,
            message: 'Start speaking for verification'
        });

        console.log(`[WS] Verification started for user: ${userId}`);
    } catch (error) {
        sendError(ws, 'Verification failed', error.message);
    }
}
```

### Step 7: Update Audio Data Handler

```javascript
// OLD CODE:
function handleAudioData(ws, clientConnection, data) {
    const { audioBuffer } = clientConnection;
    const newBuffer = Buffer.concat([audioBuffer, data]);

    if (newBuffer.length > MAX_AUDIO_SIZE) {
        sendError(ws, 'Audio size exceeded', `Max size: ${MAX_AUDIO_SIZE}`);
        return;
    }

    clientConnection.audioBuffer = newBuffer;
    clientConnection.sessionData.audioChunkCount = (clientConnection.sessionData.audioChunkCount || 0) + 1;

    // Send progress
    sendMessage(ws, {
        type: 'audio-progress',
        size: newBuffer.length,
        chunks: clientConnection.sessionData.audioChunkCount
    });
}

// NEW CODE:
function handleAudioData(ws, data) {
    // Validate session
    const validation = sessionManager.validateSession(ws.sessionId);
    if (!validation.valid) {
        sendError(ws, validation.message, 'Session expired or invalid');
        return;
    }

    try {
        // Append audio to session (SessionManager handles buffer concatenation)
        const totalSize = sessionManager.appendAudioData(ws.sessionId, data);

        if (totalSize > MAX_AUDIO_SIZE) {
            sendError(ws, 'Audio size exceeded', `Max size: ${MAX_AUDIO_SIZE}`);
            // Clear audio on size violation
            sessionManager.clearAudioBuffer(ws.sessionId);
            return;
        }

        // Update chunk count
        const session = sessionManager.getSession(ws.sessionId);
        const chunkCount = (session.metadata.audioChunkCount || 0) + 1;
        sessionManager.updateSession(ws.sessionId, {
            metadata: { audioChunkCount: chunkCount }
        });

        // Send progress
        sendMessage(ws, {
            type: 'audio-progress',
            sessionId: ws.sessionId,
            size: totalSize,
            chunks: chunkCount
        });
    } catch (error) {
        sendError(ws, 'Audio processing failed', error.message);
    }
}
```

### Step 8: Update Stop Audio Handler

```javascript
// OLD CODE:
async function handleStopAudio(ws, clientConnection) {
    const { userId, action } = clientConnection.sessionData;
    const audioBuffer = clientConnection.audioBuffer;
    // ... processing logic
}

// NEW CODE:
async function handleStopAudio(ws) {
    // Validate session
    const validation = sessionManager.validateSession(ws.sessionId);
    if (!validation.valid) {
        sendError(ws, validation.message, 'Session expired or invalid');
        return;
    }

    const session = validation.session;
    const audioBuffer = sessionManager.getAudioBuffer(ws.sessionId);

    if (!audioBuffer || audioBuffer.length === 0) {
        sendError(ws, 'No audio data', 'No audio was recorded in this session');
        return;
    }

    try {
        sendMessage(ws, {
            type: 'audio-processing',
            message: 'Processing voice data...'
        });

        // Your existing audio processing logic
        const embedding = await generateEmbedding(audioBuffer);

        if (session.metadata.action === 'enrollment') {
            await storeVoiceEmbedding(session.userId, embedding);

            sendMessage(ws, {
                type: 'enrollment-complete',
                sessionId: ws.sessionId,
                message: `Enrollment successful for ${session.userId}`
            });
        } else if (session.metadata.action === 'verification') {
            const { targetUserId } = session.metadata;
            const enrolledEmbedding = await getVoiceEmbedding(targetUserId);
            const similarity = calculateSimilarity(embedding, enrolledEmbedding);

            const isMatch = similarity > SIMILARITY_THRESHOLD;

            sendMessage(ws, {
                type: 'verification-complete',
                sessionId: ws.sessionId,
                isMatch,
                similarity,
                message: isMatch ? 'Voice match verified!' : 'Voice does not match'
            });
        }

        // Clear audio buffer after processing
        sessionManager.clearAudioBuffer(ws.sessionId);
    } catch (error) {
        sendError(ws, 'Audio processing error', error.message);
    }
}
```

### Step 9: Add Status Handler

```javascript
function handleGetStatus(ws) {
    // Validate session
    const validation = sessionManager.validateSession(ws.sessionId);

    if (!validation.valid) {
        sendMessage(ws, {
            type: 'status',
            sessionId: ws.sessionId,
            status: 'inactive',
            message: validation.message
        });
        return;
    }

    const session = validation.session;
    const stats = sessionManager.getStatistics();
    const audioBuffer = sessionManager.getAudioBuffer(ws.sessionId);

    sendMessage(ws, {
        type: 'status',
        sessionId: ws.sessionId,
        status: 'active',
        userId: session.userId,
        action: session.metadata.action,
        audioSize: audioBuffer.length,
        createdAt: session.createdAt,
        expiresAt: session.expiresAt,
        serverStats: {
            activeSessions: stats.activeSessions,
            totalUsers: stats.totalUsers
        }
    });
}
```

### Step 10: Add Graceful Shutdown

```javascript
// Handle server shutdown
process.on('SIGTERM', () => {
    console.log('[Server] SIGTERM signal received: closing HTTP server');
    server.close(() => {
        console.log('[Server] HTTP server closed');
        sessionManager.shutdown();
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('[Server] SIGINT signal received: closing HTTP server');
    server.close(() => {
        console.log('[Server] HTTP server closed');
        sessionManager.shutdown();
        process.exit(0);
    });
});
```

## Monitoring Session Manager

Add session monitoring endpoints:

```javascript
// GET /admin/sessions/stats - Session statistics
app.get('/admin/sessions/stats', (req, res) => {
    const stats = sessionManager.getStatistics();
    res.json(stats);
});

// GET /admin/sessions/:sessionId - Get session info
app.get('/admin/sessions/:sessionId', (req, res) => {
    const exported = sessionManager.exportSession(req.params.sessionId);
    if (exported) {
        res.json(exported);
    } else {
        res.status(404).json({ error: 'Session not found' });
    }
});

// GET /admin/sessions/user/:userId - Get user sessions
app.get('/admin/sessions/user/:userId', (req, res) => {
    const userSessions = sessionManager.getUserSessions(req.params.userId);
    res.json(userSessions.map(s => sessionManager.exportSession(s.sessionId)));
});

// DELETE /admin/sessions/:sessionId - Destroy session
app.delete('/admin/sessions/:sessionId', (req, res) => {
    const result = sessionManager.destroySession(req.params.sessionId);
    res.json({ success: result });
});
```

## Event Monitoring

```javascript
// Log all session events
sessionManager.on('session:created', (data) => {
    console.log(`[Event] Session created: ${data.sessionId}`);
});

sessionManager.on('session:expired', (data) => {
    console.log(`[Event] Session expired: ${data.sessionId}`);
});

sessionManager.on('cleanup:completed', (data) => {
    console.log(`[Event] Cleanup removed ${data.removedCount} sessions`);
});
```

## Configuration Recommendations

### Development
```javascript
const sessionManager = new SessionManager({
    sessionTimeout: 10 * 60 * 1000,   // 10 minutes
    cleanupInterval: 2 * 60 * 1000     // 2 minutes
});
```

### Production
```javascript
const sessionManager = new SessionManager({
    sessionTimeout: 30 * 60 * 1000,   // 30 minutes
    cleanupInterval: 5 * 60 * 1000,   // 5 minutes
    maxSessions: 5000                  // Adjust based on expected load
});
```

### High-Load Scenarios
```javascript
const sessionManager = new SessionManager({
    sessionTimeout: 15 * 60 * 1000,   // 15 minutes (shorter to free resources)
    cleanupInterval: 2 * 60 * 1000,   // 2 minutes (more frequent cleanup)
    maxSessions: 10000                 // Higher limit
});
```

## Migration Checklist

- [ ] Import SessionManager in websocket-handler.js
- [ ] Create SessionManager instance with appropriate config
- [ ] Update connection handler to use SessionManager
- [ ] Update message handler to pass only ws object
- [ ] Update initialization handler to create sessions
- [ ] Update enrollment handler
- [ ] Update verification handler
- [ ] Update audio data handler
- [ ] Update stop audio handler
- [ ] Add status handler
- [ ] Add graceful shutdown
- [ ] Test all functionality
- [ ] Add monitoring endpoints
- [ ] Add event listeners for debugging
- [ ] Deploy and monitor

## Testing the Integration

```bash
# Start the server
npm start

# Run tests in another terminal
node test-session-manager.js

# Run examples
node session-manager-examples.js
```

## Troubleshooting Integration

### Sessions expire too quickly
- Increase `sessionTimeout` value
- Verify `updateSession()` is called on activity

### Memory usage increases
- Check `cleanupInterval` is running
- Verify `destroySession()` is called on disconnect
- Monitor audio buffer sizes

### Session validation fails
- Ensure `ws.sessionId` is set during init
- Verify session timeout settings
- Check network connectivity

## Next Steps

1. Implement the integration steps above
2. Run the test suite to verify functionality
3. Update API endpoints to use sessions
4. Monitor session statistics in production
5. Adjust timeout values based on user behavior
6. Consider persistent session storage for recovery
