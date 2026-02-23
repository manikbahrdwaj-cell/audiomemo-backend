# LangChain Session Management - Quick Reference

## Quick Start

### 1. Create Session After Voice Match
```python
from langchain_session_integration import get_langchain_session_integration

integration = get_langchain_session_integration()

session = integration.create_session_on_voice_match(
    phone_number="+1-555-0123",
    verification_score=0.92,
    similarity_metrics={"cosine_similarity": 0.92, "confidence": 92.0}
)

if session['success']:
    session_id = session['session_id']
    thread_id = session['thread_id']
```

### 2. Add Message to Session
```python
integration.add_message_to_session(
    session_id=session_id,
    role="user",
    content="Hello"
)
```

### 3. Get Session Info
```python
info = integration.get_session_info(session_id)
print(info['status'])  # "active", "paused", "completed", etc
print(info['messages'])  # Number of messages
```

### 4. Pause/Resume/Terminate
```python
integration.pause_session(session_id)
integration.resume_session(session_id)
integration.terminate_session(session_id)
```

## Module Reference

### langchain_session_service.py

```python
from langchain_session_service import (
    get_langchain_session_manager,
    LangChainSessionManager,
    LangChainSession,
    LangChainSessionMetadata,
    LangChainSessionStatus
)

manager = get_langchain_session_manager()

# Create session
session = manager.create_session(
    phone_number="+1-555-0123",
    verification_score=0.95,
    session_status="active",
    custom_metadata={...}
)

# Session operations
manager.get_session(session_id)
manager.is_session_valid(session_id)
manager.add_conversation_turn(session_id, "user", "message")
manager.get_session_summary(session_id)
manager.pause_session(session_id)
manager.resume_session(session_id)
manager.terminate_session(session_id)
manager.clear_expired_sessions()
manager.get_all_active_sessions()
manager.get_session_config(session_id)  # For LangChain
```

### database.py

```python
from database import (
    get_langchain_sessions_collection,
    save_langchain_session,
    get_langchain_session,
    update_langchain_session_status,
    add_conversation_turn,
    get_langchain_sessions_by_phone,
    get_active_langchain_sessions,
    get_langchain_session_summary,
    delete_expired_langchain_sessions
)

# Save/retrieve
doc_id = save_langchain_session(session_data)
session = get_langchain_session(session_id)
summary = get_langchain_session_summary(session_id)

# Query
sessions = get_langchain_sessions_by_phone("+1-555-0123")
active = get_active_langchain_sessions("active", limit=100)

# Update
add_conversation_turn(session_id, "user", "content")
update_langchain_session_status(session_id, "paused")

# Cleanup
deleted = delete_expired_langchain_sessions(ttl_seconds=3600)
```

### langchain_session_integration.py

```python
from langchain_session_integration import get_langchain_session_integration

integration = get_langchain_session_integration()

# High-level operations
integration.create_session_on_voice_match(phone, score, metrics)
integration.add_message_to_session(session_id, "user", "content")
integration.get_session_info(session_id)
integration.pause_session(session_id)
integration.resume_session(session_id)
integration.terminate_session(session_id)
integration.get_user_sessions(phone_number, limit=10)
integration.cleanup_expired_sessions(ttl_seconds=86400)
```

## Data Structures

### LangChainSessionMetadata
```python
{
    "session_id": "lg_session_...",
    "phone_number": "+1-555-0123",
    "verification_score": 0.95,
    "timestamp": datetime,
    "session_status": "active|paused|completed|expired|terminated",
    "langgraph_thread_id": "thread_...",
    "ttl_seconds": 3600,
    "voice_verified": true,
    "verification_timestamp": datetime,
    "conversation_history": [
        {"role": "user", "content": "...", "timestamp": ...},
        {"role": "assistant", "content": "...", "timestamp": ...}
    ],
    "current_turn": 2,
    "custom_metadata": {...}
}
```

### Session Info (from get_session_info)
```python
{
    "session_id": "lg_session_...",
    "phone_number": "+1-555-0123",
    "status": "active",
    "is_valid": true,
    "thread_id": "thread_...",
    "verification_score": 0.95,
    "duration_seconds": 120.5,
    "conversation_turns": 5,
    "messages": 10,
    "started_at": "2024-01-15T10:30:00",
    "last_activity": "2024-01-15T10:32:00",
    "verified": true
}
```

## Common Patterns

### Pattern 1: WebSocket Handler
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # After voice verification
    integration = get_langchain_session_integration()
    session = integration.create_session_on_voice_match(
        phone_number="+1-555-0123",
        verification_score=0.92,
        similarity_metrics={...}
    )
    
    if session['success']:
        # Send to frontend
        await websocket.send_json({
            "type": "session_created",
            "session_id": session['session_id'],
            "thread_id": session['thread_id']
        })
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            integration.add_message_to_session(
                session_id=session['session_id'],
                role="user",
                content=data['content']
            )
```

### Pattern 2: REST Endpoint
```python
@app.post("/api/voice/verify")
async def verify_voice(request: VerifyRequest):
    # Verify voice
    result = verify_voice_sample(request.audio)
    
    if result['is_match']:
        # Create session
        integration = get_langchain_session_integration()
        session = integration.create_session_on_voice_match(
            phone_number=result['phone_number'],
            verification_score=result['similarity_score'],
            similarity_metrics=result['metrics']
        )
        
        return {
            "status": "verified",
            "session_id": session['session_id'],
            "thread_id": session['thread_id']
        }
```

### Pattern 3: Background Cleanup
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def cleanup_sessions():
    integration = get_langchain_session_integration()
    count = integration.cleanup_expired_sessions(ttl_seconds=3600)
    logger.info(f"Cleaned up {count} sessions")

scheduler.add_job(cleanup_sessions, "interval", hours=1)
scheduler.start()
```

### Pattern 4: Conversation Loop
```python
session = integration.create_session_on_voice_match(...)

for turn in range(5):
    # Add user input
    integration.add_message_to_session(
        session_id,
        "user",
        f"Input {turn + 1}"
    )
    
    # Add assistant response
    integration.add_message_to_session(
        session_id,
        "assistant",
        f"Response {turn + 1}"
    )

# Get final summary
summary = integration.get_session_info(session_id)
print(f"Session ended with {summary['conversation_turns']} turns")
```

## Session States Explained

```
CREATED    → Initial state when session is created
ACTIVE     → Session is running, can accept messages
PAUSED     → Session is paused, no messages accepted
COMPLETED  → Session finished normally
EXPIRED    → Session TTL exceeded
TERMINATED → Session was forcefully terminated
```

## MongoDB Queries

### Find Active Sessions
```javascript
db.langchain_sessions.find({
    "session_status": "active",
    "last_activity": { $gt: new Date(Date.now() - 3600000) }
})
```

### Find Sessions by User
```javascript
db.langchain_sessions.find({
    "phone_number": "+1-555-0123"
}).sort({ "created_at": -1 })
```

### Count Sessions by Status
```javascript
db.langchain_sessions.aggregate([
    { $group: { _id: "$session_status", count: { $sum: 1 } } }
])
```

### Get Session Statistics
```javascript
db.langchain_sessions.aggregate([
    {
        $group: {
            _id: "$phone_number",
            session_count: { $sum: 1 },
            avg_messages: { $avg: { $size: "$conversation_history" } }
        }
    }
])
```

## Error Handling

```python
try:
    session = integration.create_session_on_voice_match(...)
    if not session['success']:
        logger.error(f"Failed: {session['error']}")
except Exception as e:
    logger.error(f"Exception: {str(e)}")
```

## Environment Setup

```python
# .env or config
LANGCHAIN_SESSION_TTL=3600
LANGCHAIN_SESSION_MAX_TURNS=100
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=voice_biometric
```

## Testing

```python
def test_session_creation():
    integration = get_langchain_session_integration()
    
    session = integration.create_session_on_voice_match(
        phone_number="+1-555-0123",
        verification_score=0.95,
        similarity_metrics={"cosine_similarity": 0.95}
    )
    
    assert session['success']
    assert session['session_id'].startswith('lg_session_')
    assert session['thread_id'].startswith('thread_')
```

## Useful Links

- [LangChain Docs](https://python.langchain.com/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [MongoDB PyDriver](https://pymongo.readthedocs.io/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
