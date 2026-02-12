# MongoDB Schema Guide - Phase 2.2

## Overview

This document defines the MongoDB schemas for the Voice Biometric Authentication system's session management, audio storage, and analytics functionality.

**Database:** `voice_biometric`

**Collections:**
- `voice_embeddings` - User voice embeddings (existing)
- `sessions` - Active and completed user sessions (NEW)
- `audio_chunks` - Segmented audio data for sessions (NEW)
- `session_analytics` - Session events and analytics (NEW)

---

## Collection Schemas

### 1. Sessions Collection (`sessions`)

Stores session metadata and tracking information. Sessions represent user authentication workflows (enrollment, verification, etc.).

#### Schema Definition

```javascript
{
    // Identifiers (Required)
    "_id": ObjectId,                    // MongoDB document ID
    "session_id": String,               // Unique session identifier (unique index)
    "user_id": String,                  // User identifier

    // Status & Timing
    "status": String,                   // 'active', 'paused', 'completed', 'expired'
    "created_at": Date,                 // Session creation timestamp
    "last_activity": Date,              // Last activity timestamp
    "expires_at": Date,                 // Session expiration timestamp (12 hours)
    "updated_at": Date,                 // Last update timestamp

    // Client Information
    "ip_address": String,               // Client IP address (nullable)
    "user_agent": String,               // Client user agent (nullable)

    // Session Metadata
    "metadata": {
        "action": String,               // 'enrollment', 'verification', 're-enrollment'
        "language": String,             // Language preference (default: 'en')
        "connection_id": String,        // WebSocket connection ID (nullable)
        // Custom fields allowed
        ...
    },

    // Audio Tracking
    "audio_chunks_count": Number,       // Total number of audio chunks
    "total_audio_size": Number          // Total audio size in bytes
}
```

#### Example Document

```json
{
    "_id": ObjectId("507f1f77bcf86cd799439011"),
    "session_id": "sess_1707411234567_abc123",
    "user_id": "user_12345",
    "status": "active",
    "created_at": ISODate("2026-02-12T10:20:34.000Z"),
    "last_activity": ISODate("2026-02-12T10:25:45.000Z"),
    "expires_at": ISODate("2026-02-12T22:20:34.000Z"),
    "updated_at": ISODate("2026-02-12T10:25:45.000Z"),
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "metadata": {
        "action": "enrollment",
        "language": "en",
        "connection_id": "ws_conn_123"
    },
    "audio_chunks_count": 5,
    "total_audio_size": 125000
}
```

#### Indexes

| Field(s) | Type | Purpose |
|----------|------|---------|
| `session_id` | Unique | Fast session lookup |
| `user_id`, `status` | Compound | List user's sessions by status |
| `expires_at` | Ascending | Identify expired sessions |
| `created_at` | Descending | Sort sessions by creation time |
| `last_activity` | Descending | Sort sessions by recent activity |
| `user_id` | Ascending | List all user sessions |
| `expires_at` (TTL) | Ascending + TTL | Auto-delete expired sessions after 24h |

#### Query Patterns

```javascript
// Get active sessions for a user
db.sessions.find({
    user_id: "user_123",
    status: "active",
    expires_at: { $gt: new Date() }
})

// Get expired sessions (for cleanup)
db.sessions.find({
    expires_at: { $lt: new Date() }
})

// Get user's session history
db.sessions.find({
    user_id: "user_123"
}).sort({ created_at: -1 }).limit(10)

// Get single session
db.sessions.findOne({
    session_id: "sess_1707411234567_abc123"
})

// Update session status
db.sessions.updateOne(
    { session_id: "sess_..." },
    { 
        $set: { 
            status: "completed",
            updated_at: new Date()
        }
    }
)
```

---

### 2. Audio Chunks Collection (`audio_chunks`)

Stores segmented audio data for sessions. Audio is split into chunks for efficient storage and streaming.

#### Schema Definition

```javascript
{
    // Identifiers
    "_id": ObjectId,                    // MongoDB document ID
    "session_id": String,               // Reference to session
    "chunk_index": Number,              // Sequential chunk index (0-based)

    // Audio Data
    "audio_data": BinData,              // Binary audio data
    "size_bytes": Number,               // Size of this chunk in bytes

    // Metadata
    "created_at": Date                  // Chunk upload timestamp
}
```

#### Example Document

```json
{
    "_id": ObjectId("507f1f77bcf86cd799439012"),
    "session_id": "sess_1707411234567_abc123",
    "chunk_index": 0,
    "audio_data": BinData(0, "...binary audio data..."),
    "size_bytes": 25000,
    "created_at": ISODate("2026-02-12T10:20:45.000Z")
}
```

#### Indexes

| Field(s) | Type | Purpose |
|----------|------|---------|
| `session_id` | Ascending | List all chunks for a session |
| `session_id`, `chunk_index` | Compound | Get specific chunk in order |
| `created_at` | Descending | Sort chunks by upload time |

#### Constraints

- **Maximum Chunk Size:** 16 MB (MongoDB document limit)
- **Typical Chunk Size:** 25-50 KB
- **Maximum Chunks per Session:** ~1000 (depends on total audio size)

#### Query Patterns

```javascript
// Get all chunks for a session (in order)
db.audio_chunks.find({
    session_id: "sess_..."
}).sort({ chunk_index: 1 })

// Get specific chunk
db.audio_chunks.findOne({
    session_id: "sess_...",
    chunk_index: 2
})

// Count chunks
db.audio_chunks.countDocuments({
    session_id: "sess_..."
})

// Delete all chunks (when session cleanup)
db.audio_chunks.deleteMany({
    session_id: "sess_..."
})
```

---

### 3. Session Analytics Collection (`session_analytics`)

Records events and analytics data throughout a session's lifecycle for monitoring and reporting.

#### Schema Definition

```javascript
{
    // Identifiers
    "_id": ObjectId,                    // MongoDB document ID
    "session_id": String,               // Session reference
    "user_id": String,                  // User identifier

    // Event Information
    "event_type": String,               // 'created', 'audio_added', 'verification_complete', etc.
    "details": Object,                  // Event-specific data (flexible)

    // Timestamps
    "created_at": Date,                 // Event timestamp
    "date": String                      // Date in YYYY-MM-DD format (for daily aggregation)
}
```

#### Example Documents

```json
{
    "_id": ObjectId("507f1f77bcf86cd799439013"),
    "session_id": "sess_1707411234567_abc123",
    "user_id": "user_12345",
    "event_type": "session_created",
    "details": {
        "action": "enrollment",
        "ip_address": "192.168.1.100"
    },
    "created_at": ISODate("2026-02-12T10:20:34.000Z"),
    "date": "2026-02-12"
}
```

```json
{
    "_id": ObjectId("507f1f77bcf86cd799439014"),
    "session_id": "sess_1707411234567_abc123",
    "user_id": "user_12345",
    "event_type": "audio_chunk_received",
    "details": {
        "chunk_index": 0,
        "chunk_size": 25000,
        "total_audio_size": 25000
    },
    "created_at": ISODate("2026-02-12T10:20:45.000Z"),
    "date": "2026-02-12"
}
```

```json
{
    "_id": ObjectId("507f1f77bcf86cd799439015"),
    "session_id": "sess_1707411234567_abc123",
    "user_id": "user_12345",
    "event_type": "verification_completed",
    "details": {
        "status": "success",
        "similarity_score": 0.92,
        "duration_ms": 2500
    },
    "created_at": ISODate("2026-02-12T10:25:30.000Z"),
    "date": "2026-02-12"
}
```

#### Event Types

| Event Type | Context | Details |
|-----------|---------|---------|
| `session_created` | Session initialization | action, ip_address, user_agent |
| `audio_chunk_received` | Audio upload | chunk_index, chunk_size, total_audio_size |
| `verification_started` | Auth process begins | N/A |
| `verification_completed` | Auth process ends | status, similarity_score, duration_ms |
| `verification_failed` | Auth errors | error_reason, similarity_score |
| `session_extended` | Timeout extension | new_expiration_time |
| `session_completed` | Session ends | final_status, total_duration_ms |
| `session_expired` | Session timeout | expired_at |

#### Indexes

| Field(s) | Type | Purpose |
|----------|------|---------|
| `user_id`, `date` | Compound | User's events for a specific date |
| `session_id` | Ascending | Get all events for a session |

#### Query Patterns

```javascript
// Get all events for a session
db.session_analytics.find({
    session_id: "sess_..."
}).sort({ created_at: -1 })

// Get user's events for today
const today = new Date().toISOString().split('T')[0];
db.session_analytics.find({
    user_id: "user_...",
    date: today
}).sort({ created_at: -1 })

// Get user's events for past 7 days
db.session_analytics.find({
    user_id: "user_...",
    date: { $gte: "2026-02-05", $lte: "2026-02-12" }
})

// Count verification failures
db.session_analytics.countDocuments({
    user_id: "user_...",
    event_type: "verification_failed"
})

// Aggregate events by type
db.session_analytics.aggregate([
    { $match: { user_id: "user_...", date: "2026-02-12" } },
    { $group: { _id: "$event_type", count: { $sum: 1 } } }
])
```

---

### 4. Voice Embeddings Collection (`voice_embeddings`)

Stores user voice embeddings for authentication (existing collection, included for reference).

#### Schema Definition

```javascript
{
    "_id": ObjectId,
    "phone_number": String,             // Unique user identifier
    "embedding": [Number],              // 192-dimensional embedding vector
    "embedding_dimension": Number,      // Always 192
    "created_at": Date,                 // First enrollment timestamp
    "updated_at": Date                  // Last update timestamp
}
```

#### Indexes

| Field(s) | Type | Purpose |
|----------|------|---------|
| `phone_number` | Unique | Fast lookup by phone number |
| `created_at` | Descending | Sort by enrollment time |
| `updated_at` | Descending | Sort by update time |

---

## Database Initialization

### Python Initialization (database.py)

The database module automatically creates all collections and indexes on first connection:

```python
from database import get_database

# Call once to initialize
get_database()

# Creates all collections with proper indexes:
# - voice_embeddings
# - sessions
# - audio_chunks
# - session_analytics
```

### JavaScript/Node.js Initialization

Using the MongoDB Persistence Store:

```javascript
const { MongoDBPersistenceStore } = require('./mongodb-persistence-store');

const store = new MongoDBPersistenceStore({
    url: 'mongodb://localhost:27017',
    database: 'voice_biometric'
});

// Indexes are automatically created on connect
await store.connect();
```

---

## Storage and Performance Considerations

### Storage Requirements

| Item | Space per Record |
|------|-----------------|
| Session metadata | ~1-3 KB |
| Audio chunk (50 KB) | 50 KB |
| Analytics event | ~0.5-1 KB |

### Typical Session

- **Recording Duration:** 30 seconds
- **Audio Chunks:** ~20-30 chunks (25 KB each)
- **Total Storage:** 500-750 KB per session
- **Including Metadata & Analytics:** ~1 MB per session

### Estimated Growth (100,000 users)

**Monthly:**
- Active sessions/month: ~3,000,000
- Storage needed: ~3-5 GB
- Analytics events: ~30,000,000 events (~30 GB with full event details)

**Annual:**
- Storage needed: ~40-60 GB
- Analytics: ~350 GB (can be archived monthly)

### Optimization Strategies

1. **Archive Old Sessions:** Move completed sessions >90 days old to archive collection
2. **Compress Audio:** Consider audio compression before storing chunks
3. **Cleanup Expired:** Automatic TTL indexes handle expired session cleanup
4. **Partition Analytics:** Move analytics to separate database after 30 days

---

## Usage Examples

### Creating a Session

**Python (Backend)**

```python
from database import create_session

session = create_session({
    "session_id": "sess_1707411234567_abc123",
    "user_id": "user_12345",
    "action": "enrollment",
    "ip_address": "192.168.1.100",
    "expires_at": datetime.utcnow() + timedelta(hours=12)
})

print(f"Session created: {session['session_id']}")
```

**JavaScript (Node.js)**

```javascript
const sessionManager = new SessionManager();
const session = sessionManager.createSession('user_12345', {
    action: 'enrollment',
    ipAddress: '192.168.1.100'
});

// With MongoDB persistence
const store = new MongoDBPersistenceStore();
await store.connect();
await store.save(session.sessionId, session);
```

### Saving Audio

**Python**

```python
from database import save_audio_chunk

chunk_id = save_audio_chunk(
    session_id="sess_1707411234567_abc123",
    chunk_index=0,
    audio_data=audio_bytes
)
```

**JavaScript**

```javascript
const store = new MongoDBPersistenceStore();
await store.saveAudioChunk(
    'sess_1707411234567_abc123',
    0,
    audioBuffer
);
```

### Recording Events

**Python**

```python
from database import record_session_event

record_session_event(
    session_id="sess_1707411234567_abc123",
    user_id="user_12345",
    event_type="verification_completed",
    event_data={
        "status": "success",
        "similarity_score": 0.92,
        "duration_ms": 2500
    }
)
```

**JavaScript**

```javascript
await store.recordEvent(
    'sess_1707411234567_abc123',
    'user_12345',
    'verification_completed',
    {
        status: 'success',
        similarity_score: 0.92,
        duration_ms: 2500
    }
);
```

### Querying Sessions

**Python - Get Active Sessions**

```python
from database import get_active_sessions

active = get_active_sessions()
print(f"Active sessions: {len(active)}")
```

**Python - Get User Sessions**

```python
from database import get_user_sessions

sessions = get_user_sessions("user_12345", status="completed")
```

**JavaScript - Using MongoDB directly**

```javascript
const userSessions = await sessionsCol.find({
    user_id: "user_12345",
    expires_at: { $gt: new Date() }
}).toArray();
```

### Analytics

**Get User Statistics**

```python
from database import get_user_analytics

stats = get_user_analytics("user_12345", days=7)
print(f"Total events: {stats['total_events']}")
print(f"Event breakdown: {stats['event_types']}")
```

**Get Session Statistics**

```python
from database import get_session_statistics

stats = get_session_statistics()
print(f"Total sessions: {stats['total_sessions']}")
print(f"Active: {stats['active_sessions']}")
print(f"Audio size: {stats['audio']['total_size_bytes']} bytes")
```

---

## Migration from In-Memory Storage

If migrating from in-memory session storage:

1. **Enable Persistence in SessionManager:**
   ```javascript
   const store = new MongoDBPersistenceStore();
   await store.connect();
   
   sessionManager.enablePersistence = true;
   sessionManager.persistenceStore = store;
   ```

2. **Sessions are automatically persisted on create/update**

3. **Load sessions on server restart:**
   ```javascript
   const savedSession = await store.load(sessionId);
   if (savedSession) {
       sessionManager.sessions.set(sessionId, savedSession);
   }
   ```

---

## Maintenance and Monitoring

### Monitoring Queries

```javascript
// Session statistics
db.sessions.stats()

// Collection sizes
db.audio_chunks.stats()

// Index usage
db.sessions.aggregate([{ $indexStats: {} }])

// Count active sessions
db.sessions.countDocuments({ 
    status: "active",
    expires_at: { $gt: new Date() }
})
```

### Regular Maintenance

```javascript
// Remove old analytics (keep last 30 days)
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

db.session_analytics.deleteMany({
    created_at: { $lt: thirtyDaysAgo }
})

// Rebuild indexes
db.sessions.reIndex()
db.audio_chunks.reIndex()
```

---

## Security Considerations

1. **Authentication:** Use MongoDB authentication in production
2. **Encryption:** Enable MongoDB encryption at rest
3. **Audio Data:** Consider storing audio in separate encrypted storage
4. **Access Control:** Implement role-based access control (RBAC)
5. **Audit Logging:** Enable MongoDB audit logs for compliance

---

## Related Documentation

- [SESSION_MANAGER_README.md](SESSION_MANAGER_README.md) - Session manager API
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - WebSocket integration
- [mongodb-persistence-store.js](mongodb-persistence-store.js) - MongoDB persistence implementation
- [database.py](database.py) - Python database functions

---

## Summary

| Collection | Purpose | Documents | Indexes | TTL |
|-----------|---------|-----------|---------|-----|
| `sessions` | Session tracking | 1 per session | 7 | 24h after expiry |
| `audio_chunks` | Audio storage | 20-30 per session | 3 | None |
| `session_analytics` | Event logging | 10-20 per session | 2 | None |
| `voice_embeddings` | User embeddings | 1 per user | 3 | None |

**Total Implementation:**
- 4 Collections
- 15+ Indexes
- Automatic cleanup via TTL
- Full CRUD operations
- Analytics and monitoring
- Python + JavaScript support
