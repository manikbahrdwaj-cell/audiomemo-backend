# LangChain Session Management Integration Guide

## Overview

This guide explains how to implement and use LangChain session management with MongoDB storage for voice-authenticated users in the voice biometric application.

## Architecture

### Components

1. **langchain_session_service.py** - Core LangChain session management
   - `LangChainSessionManager` - In-memory session management
   - `LangChainSessionMetadata` - Session metadata container
   - `LangChainSession` - Complete session representation

2. **database.py** - MongoDB storage layer
   - `get_langchain_sessions_collection()` - Collection management
   - `save_langchain_session()` - Save/update sessions
   - `get_langchain_session()` - Retrieve sessions
   - Session querying and management functions

3. **session_service.py** - Voice verification session integration
   - `VerifiedSessionManager` - Manages verified sessions
   - Integration with `LangChainSessionManager`

4. **langchain_session_integration.py** - High-level integration
   - `LangChainSessionIntegration` - Unified interface
   - Complete lifecycle management

## Installation

### 1. Verify Dependencies

Ensure these packages are in `requirements.txt`:

```
langchain>=0.2.0
langchain-core>=0.2.0
langchain-openai>=0.2.0
langchain-google-genai>=1.1.0
langgraph>=0.2.0
langchain-community>=0.2.0
pymongo==4.6.0
```

Install if needed:
```bash
pip install -r requirements.txt
```

### 2. Database Setup

MongoDB collections are automatically created with proper indexes:

```
Collections:
- verified_sessions     (voice verification records)
- langchain_sessions    (LangChain session metadata)
```

## Usage

### 1. Basic Flow: Voice Verification → LangChain Session

```python
from voice_verification_flow import verify_voice_sample
from langchain_session_integration import get_langchain_session_integration

# 1. Verify voice
verification_result = verify_voice_sample(
    phone_number="+1-555-0123",
    audio_data=audio_bytes
)

if verification_result['is_match']:
    # 2. Create LangChain session
    integration = get_langchain_session_integration()
    
    session = integration.create_session_on_voice_match(
        phone_number=verification_result['phone_number'],
        verification_score=verification_result['similarity_score'],
        similarity_metrics=verification_result['metrics']
    )
    
    if session['success']:
        session_id = session['session_id']
        # Session is now active and stored in MongoDB
```

### 2. Creating a Session Directly

```python
from langchain_session_service import get_langchain_session_manager

manager = get_langchain_session_manager()

session = manager.create_session(
    phone_number="+1-555-0123",
    verification_score=0.95,
    session_status="active",
    custom_metadata={
        "device": "mobile",
        "region": "US"
    }
)

print(f"Session ID: {session.metadata.session_id}")
print(f"Thread ID: {session.metadata.langgraph_thread_id}")
```

### 3. Storing Session in MongoDB

```python
from database import save_langchain_session

session_data = {
    "metadata": session.metadata.to_dict(),
    "phone_number": "+1-555-0123",
    "session_status": "active"
}

doc_id = save_langchain_session(session_data)
print(f"Stored in MongoDB with ID: {doc_id}")
```

### 4. Managing Conversation History

```python
from langchain_session_integration import get_langchain_session_integration

integration = get_langchain_session_integration()

# Add user message
integration.add_message_to_session(
    session_id=session_id,
    role="user",
    content="I need to verify my account"
)

# Add assistant response
integration.add_message_to_session(
    session_id=session_id,
    role="assistant",
    content="Your voice has been verified. How can I help?"
)

# Get session info with conversation
info = integration.get_session_info(session_id)
print(f"Messages: {info['messages']}")
print(f"Conversation turns: {info['conversation_turns']}")
```

### 5. Session Lifecycle Management

```python
# Pause session
integration.pause_session(session_id)

# Resume session
integration.resume_session(session_id)

# Terminate session
integration.terminate_session(session_id)

# Get all user sessions
sessions = integration.get_user_sessions("+1-555-0123")
for sess in sessions:
    print(f"Session: {sess['session_id']} - Status: {sess['status']}")
```

## MongoDB Schema

### langchain_sessions Collection

```json
{
  "_id": ObjectId,
  "session_id": "lg_session_uuid",
  "phone_number": "+1-555-0123",
  "session_status": "active|paused|completed|expired|terminated",
  "langgraph_thread_id": "thread_uuid",
  "conversation_history": [
    {
      "role": "user|assistant",
      "content": "message text",
      "timestamp": ISODate,
      "turn_number": 1,
      "metadata": {}
    }
  ],
  "metadata": {
    "verification_score": 0.95,
    "voice_verified": true,
    "verification_timestamp": ISODate,
    "current_turn": 2,
    "custom_metadata": {},
    "ttl_seconds": 3600
  },
  "created_at": ISODate,
  "updated_at": ISODate,
  "last_activity": ISODate,
  "start_time": ISODate,
  "end_time": ISODate (optional)
}
```

### Indexes

```javascript
// session_id - unique
db.langchain_sessions.createIndex({ "session_id": 1 }, { unique: true })

// phone_number - for user queries
db.langchain_sessions.createIndex({ "phone_number": 1 })

// thread_id - for LangGraph queries
db.langchain_sessions.createIndex({ "langgraph_thread_id": 1 })

// Status filtering
db.langchain_sessions.createIndex({ "session_status": 1 })

// Time-based queries
db.langchain_sessions.createIndex({ "start_time": 1 })

// TTL index - auto-delete after 24 hours
db.langchain_sessions.createIndex(
  { "start_time": 1 },
  { expireAfterSeconds: 86400 }
)
```

## Session States

```
CREATED → ACTIVE → (PAUSED ↔ ACTIVE) → COMPLETED
                                    → TERMINATED
                                    → EXPIRED
```

## LangChain Integration

### Using Session Config with LangChain

```python
from langchain_session_service import get_langchain_session_manager
from langchain_core.runnables import RunnableLambda

manager = get_langchain_session_manager()
session = manager.create_session(
    phone_number="+1-555-0123",
    verification_score=0.95
)

# Get RunnableConfig for LangChain invoke
config = manager.get_session_config(session.metadata.session_id)

# Use with LangChain
chain = RunnableLambda(lambda x: x.upper())
result = chain.invoke(
    "hello",
    config=config  # Pass session config
)
```

### Thread ID for LangGraph

The `langgraph_thread_id` can be used with LangGraph checkpointer:

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

session = manager.create_session("+1-555-0123", 0.95)
thread_id = session.metadata.langgraph_thread_id

# Use in LangGraph
builder = StateGraph(MyState)
# ... build graph ...

graph = builder.compile(checkpointer=MemorySaver())

# Invoke with thread_id
result = graph.invoke(
    input_data,
    {"configurable": {"thread_id": thread_id}}
)
```

## WebSocket Integration (Example)

### In websocket_events.py

```python
from langchain_session_integration import get_langchain_session_integration

# After voice verification success
if is_match:
    integration = get_langchain_session_integration()
    
    session = integration.create_session_on_voice_match(
        phone_number=matched_phone_number,
        verification_score=similarity_score,
        similarity_metrics=comprehensive_metrics
    )
    
    if session['success']:
        # Send session info to frontend
        result_message = {
            "event": "verification_result",
            "status": "success",
            "data": {
                "session_id": session['session_id'],
                "thread_id": session['thread_id'],
                "status": "active",
                # ... other data
            }
        }
        await connection.send_json(result_message)
```

## Best Practices

1. **Session Cleanup**
   ```python
   # Periodic cleanup (e.g., every hour)
   integration.cleanup_expired_sessions(ttl_seconds=3600)
   ```

2. **Session Monitoring**
   ```python
   # Get active sessions
   sessions = manager.get_all_active_sessions()
   for session_id, session in sessions.items():
       if not manager.is_session_valid(session_id):
           manager.terminate_session(session_id)
   ```

3. **Error Handling**
   ```python
   try:
       session = integration.create_session_on_voice_match(...)
       if not session['success']:
           logger.error(f"Session creation failed: {session['error']}")
   except Exception as e:
       logger.error(f"Unexpected error: {str(e)}")
   ```

4. **Metadata Organization**
   ```python
   session = manager.create_session(
       phone_number="+1-555-0123",
       verification_score=0.95,
       custom_metadata={
           "app_version": "1.0.0",
           "device_type": "ios",
           "region": "US",
           "language": "en"
       }
   )
   ```

## Configuration

### Session TTL (Time-To-Live)

```python
# Default 1 hour
manager = LangChainSessionManager(default_ttl_seconds=3600)

# Custom TTL per session
metadata = LangChainSessionMetadata(
    ttl_seconds=7200  # 2 hours
)
```

### Max Conversation Turns

```python
metadata = LangChainSessionMetadata(
    max_turns=500  # Allow up to 500 turns
)
```

## Monitoring and Debugging

### Get Session Summary
```python
summary = integration.get_session_info(session_id)
print(f"""
Session: {summary['session_id']}
Status: {summary['status']}
User: {summary['phone_number']}
Messages: {summary['messages']}
Duration: {summary['duration_seconds']}s
Last Activity: {summary['last_activity']}
""")
```

### Query MongoDB Directly

```python
from database import get_langchain_sessions_collection

col = get_langchain_sessions_collection()

# Recent sessions
recent = col.find().sort("created_at", -1).limit(10)

# Active sessions for user
user_sessions = col.find({
    "phone_number": "+1-555-0123",
    "session_status": "active"
})

# Session count
count = col.count_documents({"session_status": "active"})
```

## Troubleshooting

### Session Not Found
1. Check if session was created successfully
2. Verify session_id is correct
3. Check MongoDB for expired sessions
4. Ensure TTL hasn't expired

### Connection Issues
```python
from database import get_database

# Test MongoDB connection
try:
    db = get_database()
    info = db.info()
    print(f"MongoDB connection OK: {info}")
except Exception as e:
    print(f"MongoDB error: {str(e)}")
```

### Session State Issues
```python
# Verify session validity
is_valid = manager.is_session_valid(session_id)
session = manager.get_session(session_id)
print(f"Status: {session.metadata.session_status}")
print(f"Valid: {is_valid}")
```

## Performance Considerations

1. **Memory vs MongoDB**
   - Fast access: in-memory sessions
   - Persistence: MongoDB storage
   - Sync both for reliability

2. **Indexing**
   - Session queries use indexes
   - Lookups by phone_number optimized
   - Time-based cleanup uses indexes

3. **Cleanup Strategy**
   - Automatic cleanup after TTL
   - Manual cleanup for old sessions
   - MongoDB TTL index auto-deletion

## Next Steps

1. Test the integration with your voice verification flow
2. Configure session TTL based on requirements
3. Set up monitoring and cleanup tasks
4. Integrate with LangGraph for multi-turn conversations
5. Add custom metadata specific to your use case
