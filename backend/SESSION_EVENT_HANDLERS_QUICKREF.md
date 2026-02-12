# Session Event Handlers - Quick Reference Card

## 🚀 30-Second Start

```javascript
const { SessionManager } = require('./session-manager');
const SessionEventHandlers = require('./session-event-handlers');

// 1. Create manager
const sm = new SessionManager();

// 2. Create handlers
const handlers = new SessionEventHandlers(sm);

// 3. Register webhook
handlers.registerWebhook('session:created', (type, payload) => {
    console.log('New session:', payload.sessionId);
});

// 4. Use normally (events are automatic!)
const session = sm.createSession('user123', { action: 'enrollment' });
```

---

## 📚 Six Events You Need to Know

```javascript
'session:created'       // New session started
'session:updated'       // Session data changed
'session:destroyed'     // Session ended
'session:expired'       // Session timed out
'cleanup:completed'     // Expired sessions removed
'all-sessions:cleared'  // Force clear all sessions
```

---

## 📖 Main API

```javascript
// Create handlers
new SessionEventHandlers(sessionManager, options)

// Register webhook
handlers.registerWebhook(eventType, handler)
handlers.registerWebhook(['event1', 'event2'], handler)
handlers.registerWebhook('*', handler)  // All events

// Get stats
handlers.getEventStats()      // Basic stats
handlers.getDetailedReport()  // Full report

// Manage
handlers.resetEventCounters()
handlers.shutdown()
```

---

## 🔌 Quick Integrations

### WebSocket Integration
```javascript
handlers.registerWebhook('session:created', (type, payload) => {
    io.emit('session:created', payload);
});
```

### External API
```javascript
handlers.registerWebhook('session:destroyed', async (type, payload) => {
    await fetch('https://api.example.com/sessions/end', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
});
```

### Email Notification
```javascript
handlers.registerWebhook('session:expired', (type, payload) => {
    sendEmail(payload.userId, 'Your session expired');
});
```

### Slack Alert
```javascript
handlers.registerWebhook('all-sessions:cleared', (type, payload) => {
    slackBot.send(`⚠️ ${payload.clearedCount} sessions cleared`);
});
```

---

## 📊 Data Structures

### Session Created Event
```javascript
{
    sessionId: 'sess_...',
    userId: 'user123',
    timestamp: '2026-02-12T10:20:34Z',
    status: 'success'
}
```

### Session Updated Event
```javascript
{
    sessionId: 'sess_...',
    userId: 'user123',
    timestamp: '...',
    sessionData: {...},
    status: 'success'
}
```

### Session Expired Event
```javascript
{
    sessionId: 'sess_...',
    userId: 'user123',
    timestamp: '...',
    status: 'expired',
    reason: 'Timeout'
}
```

### Cleanup Completed Event
```javascript
{
    timestamp: '...',
    removedCount: 5,
    status: 'completed'
}
```

---

## ⚙️ Configuration Options

```javascript
new SessionEventHandlers(sessionManager, {
    enableAnalytics: true,      // Enable analytics
    enableAuditing: true,       // Enable audit logging
    analyticsStore: null,       // Custom store
    auditLog: null,             // Custom audit
    webhookHandlers: [],        // Initial webhooks
    logger: console             // Custom logger
});
```

---

## 📊 Statistics & Monitoring

```javascript
// Get event counters
const stats = handlers.getEventStats();
console.log(stats.eventCounters);
{
    'session:created': 5,
    'session:updated': 12,
    'session:destroyed': 2,
    'session:expired': 1,
    'cleanup:completed': 1,
    'all-sessions:cleared': 0
}

// Get comprehensive report
const report = handlers.getDetailedReport();
```

---

## ✅ Common Patterns

### Listen to All Session Lifecycle Events
```javascript
const events = ['session:created', 'session:updated', 
                'session:destroyed', 'session:expired'];
handlers.registerWebhook(events, (type, payload) => {
    console.log(`Session event: ${type}`, payload);
});
```

### Custom Analytics Setup
```javascript
class MyAnalytics {
    record(event) {
        // Send to MongoDB, Kafka, etc
    }
}

const handlers = new SessionEventHandlers(sm, {
    analyticsStore: new MyAnalytics(),
    enableAnalytics: true
});
```

### Monitoring Loop
```javascript
setInterval(() => {
    const stats = handlers.getEventStats();
    console.log('Active sessions:', stats.sessionStats.activeSessions);
    console.log('Total events:', stats.totalEvents);
}, 60000);
```

### Graceful Shutdown
```javascript
process.on('SIGTERM', () => {
    handlers.shutdown();
    sessionManager.shutdown();
    process.exit(0);
});
```

---

## 🎯 30 Second Integration Examples

### Example 1: Log All Sessions
```javascript
handlers.registerWebhook('*', (type, payload) => {
    console.log(`[${type}]`, payload);
});
```

### Example 2: Track Created Sessions
```javascript
handlers.registerWebhook('session:created', (type, payload) => {
    database.log({type: 'session_created', userId: payload.userId});
});
```

### Example 3: Notify on Expiration
```javascript
handlers.registerWebhook('session:expired', (type, payload) => {
    notificationService.send(payload.userId, 'Session ended');
});
```

### Example 4: Monitor Activity
```javascript
handlers.registerWebhook('session:updated', (type, payload) => {
    metrics.increment('session.update');
});
```

---

## 🔍 Debug Mode

```javascript
const handlers = new SessionEventHandlers(sm, {
    logger: {
        log: (msg) => console.log(`[LOG] ${msg}`),
        warn: (msg) => console.warn(`[WARN] ${msg}`),
        error: (msg) => console.error(`[ERROR] ${msg}`)
    }
});

// Now all handler actions are logged
```

---

## ❌ Common Mistakes

### ❌ Wrong: Initialize handlers after sessions
```javascript
sessionManager.createSession(...);
const handlers = new SessionEventHandlers(sessionManager); // Too late!
```

### ✅ Right: Initialize handlers first
```javascript
const handlers = new SessionEventHandlers(sessionManager);
sessionManager.createSession(...);
```

### ❌ Wrong: Event type mismatch
```javascript
handlers.registerWebhook('sessionCreated', ...);   // Wrong!
```

### ✅ Right: Exact event type
```javascript
handlers.registerWebhook('session:created', ...);  // Correct!
```

### ❌ Wrong: No shutdown
```javascript
// App exits without cleanup
process.exit(0);
```

### ✅ Right: Clean shutdown
```javascript
handlers.shutdown();
sessionManager.shutdown();
process.exit(0);
```

---

## 📈 Performance Tips

1. **Register webhooks early** - Before creating sessions
2. **Use specific events** - Not wildcard '*'
3. **Async webhooks** - For slow operations
4. **Batch operations** - Process multiple events together
5. **Monitor regularly** - Check statistics

---

## 🔗 File References

- **Source:** `session-event-handlers.js`
- **Examples:** `test-event-handlers.js`
- **Full Guide:** `SESSION_EVENT_HANDLERS_GUIDE.md`
- **Summary:** `PHASE_2_3_COMPLETION.md`
- **Index:** `PHASE_2_3_INDEX.md`

---

## 📞 Help

### Isn't working?
Check: `SESSION_EVENT_HANDLERS_GUIDE.md#troubleshooting`

### Need examples?
Run: `node test-event-handlers.js`

### Want details?
Read: `SESSION_EVENT_HANDLERS_GUIDE.md`

### Need to understand?
See: `PHASE_2_3_COMPLETION.md`

---

## ✨ The Bottom Line

**3 steps to working event handlers:**
1. `const handlers = new SessionEventHandlers(sm);`
2. `handlers.registerWebhook('session:created', callback);`
3. Done! All events automatically captured.

---

**Last Updated:** February 12, 2026  
**Status:** ✅ Production Ready  
**Version:** 1.0
