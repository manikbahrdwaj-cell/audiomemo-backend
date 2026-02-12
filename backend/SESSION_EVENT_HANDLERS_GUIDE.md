# Step 2.3: Create Event Handlers - Implementation Guide

## Overview

Event handlers for the Session Manager provide a robust system to manage all session lifecycle events. They enable automatic logging, analytics, auditing, and webhook triggers for monitoring and system integration.

**Status:** ✅ COMPLETE  
**Files:** 1 new file + this guide

---

## What Was Implemented

### 1. **session-event-handlers.js** (NEW)
A comprehensive event handler system with:

✅ **Six Event Handlers:**
- `session:created` - New session initialization
- `session:updated` - Session data changes
- `session:destroyed` - Session termination
- `session:expired` - Session timeout
- `cleanup:completed` - Cleanup operations
- `all-sessions:cleared` - Force clear all sessions

✅ **Features:**
- Audit logging for compliance
- Analytics recording for metrics
- Webhook integration for third-party systems
- Event counters for monitoring
- Resource lifecycle management
- User notifications
- Cleanup reports
- Error handling and recovery

---

## Architecture

```
SessionManager (Core)
    ↓ (emits events)
SessionEventHandlers (New)
    ├── Audit Log
    ├── Analytics Store
    ├── Webhook Handlers
    ├── Resource Manager
    └── Notification System
```

---

## Event Handlers Details

### 1. Session Created Handler

**Event:** `session:created`  
**Triggered:** When a new session is created  
**Data:** `{ sessionId, userId }`

**Actions:**
```javascript
✓ Log event with timestamp
✓ Record audit trail
✓ Record analytics metrics
✓ Trigger webhooks
✓ Initialize session resources
```

**Example Usage:**
```javascript
// Event data structure
{
    sessionId: 'sess_1707411234567_abc123def456',
    userId: 'user123',
    timestamp: '2026-02-12T10:20:34.567Z'
}
```

### 2. Session Updated Handler

**Event:** `session:updated`  
**Triggered:** When session data is modified  
**Data:** `{ sessionId, userId }`

**Actions:**
```javascript
✓ Log update event
✓ Record audit with metadata
✓ Capture audio buffer size
✓ Trigger webhooks with full session export
```

**Example Usage:**
```javascript
// Includes session metadata and audio size
{
    sessionId: 'sess_...',
    userId: 'user123',
    audioBufferSize: 2048,
    sessionMetadata: { action: 'enrollment', language: 'en' }
}
```

### 3. Session Destroyed Handler

**Event:** `session:destroyed`  
**Triggered:** When a session is destroyed  
**Data:** `{ sessionId, userId }`

**Actions:**
```javascript
✓ Log destruction event
✓ Record audit trail
✓ Record final analytics
✓ Trigger termination webhooks
✓ Cleanup allocated resources
```

### 4. Session Expired Handler

**Event:** `session:expired`  
**Triggered:** When a session times out  
**Data:** `{ sessionId, userId }`

**Actions:**
```javascript
✓ Log timeout event
✓ Record expiration audit
✓ Track analytics metrics
✓ Send user notification
✓ Trigger webhooks
```

### 5. Cleanup Completed Handler

**Event:** `cleanup:completed`  
**Triggered:** After periodic cleanup cycle  
**Data:** `{ removedCount }`

**Actions:**
```javascript
✓ Log cleanup completion
✓ Record audit event
✓ Generate cleanup report
✓ Trigger webhooks with statistics
```

### 6. All Sessions Cleared Handler

**Event:** `all-sessions:cleared`  
**Triggered:** When all sessions are force-cleared  
**Data:** `{ count }`

**Actions:**
```javascript
✓ Log with HIGH severity
✓ Record critical audit event
✓ Trigger emergency webhooks
```

---

## Implementation Guide

### Step 1: Initialize SessionEventHandlers

```javascript
const { SessionManager } = require('./session-manager');
const SessionEventHandlers = require('./session-event-handlers');

// Create SessionManager
const sessionManager = new SessionManager({
    sessionTimeout: 30 * 60 * 1000,
    cleanupInterval: 5 * 60 * 1000
});

// Create and attach event handlers
const eventHandlers = new SessionEventHandlers(sessionManager, {
    enableAnalytics: true,
    enableAuditing: true,
    logger: console // or custom logger
});
```

### Step 2: Register Webhooks

```javascript
// Register for specific events
eventHandlers.registerWebhook('session:created', (eventType, payload) => {
    console.log(`New session created:`, payload);
    // Send to external system
});

// Register for multiple events
eventHandlers.registerWebhook(
    ['session:expired', 'session:destroyed'],
    (eventType, payload) => {
        console.log(`Session ended:`, eventType, payload);
    }
);

// Register for all events
eventHandlers.registerWebhook('*', (eventType, payload) => {
    console.log(`[ANY EVENT] ${eventType}:`, payload);
});
```

### Step 3: Integrate Analytics Store

```javascript
class CustomAnalyticsStore {
    record(event) {
        // Send to MongoDB, Kafka, etc.
        console.log('Recording analytics:', event);
    }
}

const analyticsStore = new CustomAnalyticsStore();

const eventHandlers = new SessionEventHandlers(sessionManager, {
    analyticsStore,
    enableAnalytics: true
});
```

### Step 4: Integrate Audit Log

```javascript
class CustomAuditLog {
    log(entry) {
        // Store in audit database
        console.log('Audit entry:', entry);
    }
}

const auditLog = new CustomAuditLog();

const eventHandlers = new SessionEventHandlers(sessionManager, {
    auditLog,
    enableAuditing: true
});
```

---

## Usage Examples

### Complete Integration Example

```javascript
const { SessionManager, MemoryPersistenceStore } = require('./session-manager');
const SessionEventHandlers = require('./session-event-handlers');

// Setup
const sessionManager = new SessionManager({
    sessionTimeout: 30 * 60 * 1000,
    cleanupInterval: 5 * 60 * 1000,
    maxSessions: 1000,
    enablePersistence: true,
    persistenceStore: new MemoryPersistenceStore()
});

// Create event handlers with all options
const eventHandlers = new SessionEventHandlers(sessionManager, {
    enableAnalytics: true,
    enableAuditing: true
});

// Register webhooks
eventHandlers.registerWebhook('session:created', (eventType, payload) => {
    console.log('New session:', payload.sessionId);
    // Notify dashboard
    // Send notification to user
});

eventHandlers.registerWebhook('session:expired', (eventType, payload) => {
    console.log('Session expired:', payload.sessionId);
    // Contact user
    // Clean external resources
});

// Use SessionManager normally
const session = sessionManager.createSession('user123', {
    action: 'enrollment',
    language: 'en'
});

console.log('Session created:', session.sessionId);

// Later...
sessionManager.updateSession(session.sessionId, {
    metadata: { audioProcessed: true }
});

// Get event statistics
const stats = eventHandlers.getEventStats();
console.log('Event Stats:', stats);

// Get detailed report
const report = eventHandlers.getDetailedReport();
console.log('Detailed Report:', report);

// Shutdown
eventHandlers.shutdown();
sessionManager.shutdown();
```

### Async Webhook Example

```javascript
// Async webhook handler
eventHandlers.registerWebhook('session:destroyed', async (eventType, payload) => {
    try {
        // Send to external API
        const response = await fetch('https://api.example.com/sessions/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        console.log('Webhook sent successfully');
    } catch (error) {
        console.error('Webhook failed:', error);
    }
});
```

### Monitoring Example

```javascript
// Setup event monitoring
setInterval(() => {
    const stats = eventHandlers.getEventStats();
    console.log('=== Event Statistics ===');
    console.table(stats.eventCounters);
    console.log('Total Events:', stats.totalEvents);
    console.log('Active Sessions:', stats.sessionStats.activeSessions);
}, 60000); // Every minute
```

---

## Event Data Structures

### Session Created Event
```javascript
{
    sessionId: 'sess_1707411234567_abc123',
    userId: 'user123',
    timestamp: '2026-02-12T10:20:34.567Z',
    status: 'success'
}
```

### Session Updated Event
```javascript
{
    sessionId: 'sess_...',
    userId: 'user123',
    timestamp: '2026-02-12T10:21:00.123Z',
    sessionData: {
        sessionId: 'sess_...',
        userId: 'user123',
        createdAt: 1707411234567,
        lastActivity: 1707411260123,
        audioBufferSize: 2048,
        metadata: { action: 'enrollment' }
    },
    status: 'success'
}
```

### Session Destroyed Event
```javascript
{
    sessionId: 'sess_...',
    userId: 'user123',
    timestamp: '2026-02-12T10:25:00.456Z',
    status: 'destroyed'
}
```

### Session Expired Event
```javascript
{
    sessionId: 'sess_...',
    userId: 'user123',
    timestamp: '2026-02-12T10:50:00.789Z',
    status: 'expired',
    reason: 'Timeout'
}
```

### Cleanup Completed Event
```javascript
{
    timestamp: '2026-02-12T10:55:00.123Z',
    removedCount: 5,
    status: 'completed'
}
```

---

## API Reference

### Constructor

```javascript
new SessionEventHandlers(sessionManager, options)
```

**Options:**
- `enableAnalytics` (boolean): Enable analytics recording (default: true)
- `enableAuditing` (boolean): Enable audit logging (default: true)
- `analyticsStore` (object): Custom analytics store implementation
- `auditLog` (object): Custom audit log implementation
- `webhookHandlers` (array): Initial webhook handlers
- `logger` (object): Custom logger (default: console)

### Methods

#### `registerWebhook(eventTypes, handler)`
Register a webhook handler for events.

**Parameters:**
- `eventTypes` (string|array): Event type(s) to listen to or '*' for all
- `handler` (function): Handler function(eventType, payload)

**Example:**
```javascript
eventHandlers.registerWebhook('session:created', (type, payload) => {
    console.log('Session created:', payload.sessionId);
});
```

#### `getEventStats()`
Get current event statistics.

**Returns:**
```javascript
{
    timestamp: '...',
    eventCounters: {
        'session:created': 5,
        'session:updated': 12,
        'session:destroyed': 2,
        'session:expired': 1,
        'cleanup:completed': 1,
        'all-sessions:cleared': 0
    },
    totalEvents: 21,
    sessionStats: { ... }
}
```

#### `getDetailedReport()`
Get comprehensive event and session report.

**Returns:**
```javascript
{
    timestamp: '2026-02-12T10:30:00.000Z',
    events: { ... },
    sessions: { ... },
    enabledFeatures: { ... }
}
```

#### `resetEventCounters()`
Reset all event counters to zero.

#### `shutdown()`
Cleanup and remove all event listeners.

---

## Integration Points

### With MongoDB Persistence
```javascript
const MongoDBPersistenceStore = require('./mongodb-persistence-store');
const store = new MongoDBPersistenceStore();

eventHandlers.registerWebhook('*', async (eventType, payload) => {
    if (eventType === 'session:destroyed') {
        // Persist final state to MongoDB
        await store.recordEvent(payload.sessionId, payload.userId, 
                               eventType, payload);
    }
});
```

### With WebSocket Server
```javascript
const io = require('socket.io')(server);

eventHandlers.registerWebhook('session:created', (type, payload) => {
    io.emit('session:created', payload);
});

eventHandlers.registerWebhook('session:expired', (type, payload) => {
    io.to(payload.userId).emit('session:expired', payload);
});
```

### With Logging Service
```javascript
const winston = require('winston');

const logger = winston.createLogger({
    transports: [
        new winston.transports.File({ filename: 'audit.log' })
    ]
});

eventHandlers.registerWebhook('*', (eventType, payload) => {
    logger.info(`Session Event: ${eventType}`, payload);
});
```

---

## Monitoring & Debugging

### Enable Debug Mode

```javascript
const eventHandlers = new SessionEventHandlers(sessionManager, {
    logger: {
        log: console.log,
        warn: console.warn,
        error: console.error
    }
});
```

### View Statistics

```javascript
// Every 30 seconds
setInterval(() => {
    const report = eventHandlers.getDetailedReport();
    console.log(JSON.stringify(report, null, 2));
}, 30000);
```

### Real-time Monitoring

```javascript
eventHandlers.registerWebhook('*', (eventType, payload) => {
    const stats = eventHandlers.getEventStats();
    console.log(`[${eventType}] Total Events: ${stats.totalEvents}`);
});
```

---

## Best Practices

1. **Always Register Webhooks Early**
   - Register all webhooks before creating sessions

2. **Use Specific Event Types**
   - Better to listen to specific events than use '*'
   - Improves performance and clarity

3. **Handle Async Operations**
   - Webhooks can be async - they won't block
   - Errors in webhooks won't crash the system

4. **Monitor Event Counts**
   - Check event statistics periodically
   - Watch for unusual patterns

5. **Implement Audit Logging**
   - Use audit logging for compliance
   - Store in secure, immutable location

6. **Test Event Handlers**
   - Test with various event types
   - Verify async operations complete

7. **Clean Shutdown**
   - Always call `shutdown()` before process exit
   - Ensures listeners are properly removed

---

## Troubleshooting

### Events Not Being Triggered

**Issue:** Event handlers not receiving events  
**Solution:** Ensure SessionEventHandlers is initialized before creating sessions

```javascript
// ✓ Correct
const sessionManager = new SessionManager();
const eventHandlers = new SessionEventHandlers(sessionManager);
const session = sessionManager.createSession(...);

// ✗ Wrong
const sessionManager = new SessionManager();
const session = sessionManager.createSession(...);
const eventHandlers = new SessionEventHandlers(sessionManager); // Too late!
```

### Webhooks Not Firing

**Issue:** Registered webhooks not being called  
**Solution:** Check event type spelling and registration

```javascript
// Verify event type
eventHandlers.registerWebhook('session:created', ...); // Correct
// NOT 'sessionCreated', 'SessionCreated', etc.
```

### Memory Leaks

**Issue:** Event handlers consuming memory  
**Solution:** Call shutdown() when done

```javascript
process.on('SIGTERM', () => {
    eventHandlers.shutdown();
    sessionManager.shutdown();
    process.exit(0);
});
```

---

## What's Next (Phase 2.4+)

Future enhancements could include:
- [ ] Distributed event tracking
- [ ] Event replay/audit trail retrieval
- [ ] Custom event types
- [ ] Event filtering and transformation
- [ ] Rate limiting for webhooks
- [ ] Dead letter queues for failed webhooks
- [ ] Event versioning

---

## Files Summary

**New Files:**
- `session-event-handlers.js` - Event handler implementation

**Related Files:**
- `session-manager.js` - Event emitter (unchanged)
- `mongodb-persistence-store.js` - Can integrate with webhooks
- `database.py` - Can integrate with analytics

**This Document:** `SESSION_EVENT_HANDLERS_GUIDE.md`

---

## Quick Reference

```javascript
// Initialize
const eventHandlers = new SessionEventHandlers(sessionManager);

// Register webhook
eventHandlers.registerWebhook(eventType, handler);

// Get stats
eventHandlers.getEventStats();

// Get report
eventHandlers.getDetailedReport();

// Reset counters
eventHandlers.resetEventCounters();

// Shutdown
eventHandlers.shutdown();
```

---

**Status:** ✅ Ready for production  
**Last Updated:** February 12, 2026
