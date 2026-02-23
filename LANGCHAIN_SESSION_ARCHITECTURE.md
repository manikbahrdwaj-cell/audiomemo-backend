# LangChain Session Management Architecture

## System Overview

This document provides a comprehensive overview of the LangChain session management system integrated with voice biometric authentication.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Voice Verification Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Voice Input → 2. Embedding Generation → 3. Similarity Match  │
│     (Audio)           (Voice Embedding)       (Score > Threshold)│
│                                                        │          │
│                                                        ↓          │
├─────────────────────────────────────────────────────────────────┤
│         On Successful Match → Create Verified Session             │
├─────────────────────────────────────────────────────────────────┤
│                             │                                      │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
                              ↓
              ┌───────────────────────────────────┐
              │  VerifiedSessionManager            │
              │  Create Verified Session          │
              │  - session_id (UUID)              │
              │  - phone_number                   │
              │  - verification_score            │
              │  - timestamp                      │
              └───────────────────────────────────┘
                              │
                              ↓
              ┌───────────────────────────────────┐
              │ LangChainSessionManager            │
              │ Create LangChain Session          │
              │ - UUID-based session_id           │
              │ - LangGraph thread_id             │
              │ - Metadata container              │
              │ - RunnableConfig for LangChain    │
              └───────────────────────────────────┘
                              │
              ┌───────┬───────┴────────┬─────────────┐
              ↓       ↓                 ↓             ↓
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Memory  │ │ MongoDB  │ │LangGraph │ │ Frontend │
        │ (Fast)   │ │(Persist) │ │ (Thread) │ │(Feedback)│
        └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Component Architecture

### 1. Voice Verification Module
**File**: `verification_service.py`, `websocket_events.py`

```python
Voice Input
    ↓
Generate Embeddings
    ↓
Match Against Enrolled Voice
    ↓
Calculate Similarity Score
    ↓
Match? (score > 0.75)
    ├─ YES → Create Verified Session
    └─ NO  → Return Failure
```

### 2. Session Management Layers

#### Layer 1: Verified Session
**File**: `session_service.py`
- Manages voice verification sessions
- Creates verified session on successful match
- Delegates to LangChain layer for multi-turn support

#### Layer 2: LangChain Session
**File**: `langchain_session_service.py`
- Manages LangChain/LangGraph sessions
- Handles conversation lifecycle
- Creates RunnableConfig for LangChain integration
- Generates LangGraph thread IDs

#### Layer 3: Integration Layer
**File**: `langchain_session_integration.py`
- Unified interface for all operations
- Bridges verification and LangChain sessions
- Synchronizes memory and MongoDB storage

#### Layer 4: Storage Layer
**File**: `database.py`
- MongoDB collection management
- Session persistence
- Query operations
- Cleanup/expiration

## Data Flow

### Create Session Flow
```
Voice Match Event
    ↓
VerifiedSessionManager.create_verified_session()
    ├─ Generate session_id (UUID)
    ├─ Store verification details
    └─ Return VerifiedSession object
    
    ↓
    
VerifiedSessionManager.create_langgraph_session()
    ├─ Get LangChainSessionManager
    └─ Delegate to LangChain layer
    
    ↓
    
LangChainSessionManager.create_session()
    ├─ Generate session_id
    ├─ Generate langgraph_thread_id
    ├─ Create RunnableConfig
    └─ Return LangChainSession object
    
    ↓
    
LangChainSessionIntegration.create_session_on_voice_match()
    ├─ Store session data in memory
    ├─ Save metadata to MongoDB
    └─ Return result with all IDs
    
    ↓
    
Return to WebSocket/API
    └─ Send session_id and thread_id to frontend
```

### Message Processing Flow
```
User Message from Frontend
    ↓
WebSocket Handler
    ↓
LangChainSessionIntegration.add_message_to_session()
    ├─ Update in-memory session (fast access)
    ├─ Add to MongoDB (persistence)
    ├─ Increment conversation counter
    └─ Update last_activity timestamp
    
    ↓
    
Process with LangChain/LLM
    ├─ Retrieve session config
    ├─ Pass to chain/graph
    └─ Get response
    
    ↓
    
LangChainSessionIntegration.add_message_to_session() [Assistant]
    ├─ Add assistant response
    └─ Update session in both stores
    
    ↓
    
Send to Frontend with Session Context
```

## MongoDB Collections Schema

### Collection: langchain_sessions

**Purpose**: Store complete LangChain session data

**Document Structure**:
```javascript
{
  _id: ObjectId,
  
  // Session Identifiers
  session_id: String,              // "lg_session_<uuid>"
  phone_number: String,            // "+1-555-0123"
  langgraph_thread_id: String,     // "thread_<uuid>"
  
  // Status Management
  session_status: String,          // "active" | "paused" | "completed" | ...
  created_at: ISODate,
  updated_at: ISODate,
  start_time: ISODate,
  end_time: ISODate,               // Optional, set on completion/termination
  last_activity: ISODate,          // Updated on each interaction
  
  // Verification Details (from voice auth)
  phone_number: String,
  verification_score: Number,      // 0.0 - 1.0
  voice_verified: Boolean,
  verification_timestamp: ISODate,
  
  // Conversation Data
  conversation_history: [
    {
      role: String,                // "user" | "assistant"
      content: String,
      timestamp: ISODate,
      turn_number: Number,
      metadata: {
        source: String,            // "voice_app", "llm", etc
        confidence: Number,
        processing_time_ms: Number,
        ...
      }
    }
  ],
  
  // Session Metadata
  metadata: {
    current_turn: Number,
    max_turns: Number,
    ttl_seconds: Number,
    custom_metadata: Object        // App-specific data
  },
  
  // Configuration
  config: {
    configurable: {
      session_id: String,
      thread_id: String,
      user_id: String,
      ...
    }
  }
}
```

**Indexes**:
```javascript
{ "session_id": 1 }                  // Unique
{ "phone_number": 1 }                // Query by user
{ "langgraph_thread_id": 1 }         // LangGraph lookup
{ "session_status": 1 }              // Filter by status
{ "start_time": 1 }                  // Time-based queries
{ "last_activity": 1 }               // Activity tracking
{ "start_time": 1 }, expireAfterSeconds: 86400  // TTL index
```

## Class Hierarchy

```
LangChainSessionMetadata (dataclass)
├─ session_id: str
├─ phone_number: str
├─ verification_score: float
├─ session_status: str
├─ langgraph_thread_id: str
├─ conversation_history: List[Dict]
└─ to_dict(), from_dict()

LangChainSession
├─ metadata: LangChainSessionMetadata
├─ config: RunnableConfig (from LangChain)
└─ to_dict()

LangChainSessionManager
├─ sessions: Dict[session_id → LangChainSession]
├─ create_session()
├─ get_session()
├─ add_conversation_turn()
├─ pause_session()
├─ resume_session()
├─ terminate_session()
├─ is_session_valid()
├─ get_session_summary()
└─ clear_expired_sessions()

LangChainSessionIntegration
├─ session_manager: LangChainSessionManager
├─ create_session_on_voice_match()
├─ add_message_to_session()
├─ get_session_info()
├─ pause_session()
├─ resume_session()
├─ terminate_session()
├─ get_user_sessions()
└─ cleanup_expired_sessions()

VerifiedSessionManager
├─ sessions: Dict[session_id → VerifiedSession]
├─ create_verified_session()
├─ create_langgraph_session()  // → Creates LangChainSession
└─ ...other methods
```

## Session Lifecycle

```
┌─────────────┐
│   CREATED   │ (Initial state when created)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   ACTIVE    │ ← Main state, can send/receive messages
├─────┬───────┤
│     │       │
│     ↓       ↓
│  PAUSED  (can resume)
│     │       │
│     └───┬───┘
│         │
│         ↓
│      ACTIVE (resumed)
│
├─────────────────────┐
│ (at any time)       │
├─────────────────────┤
│                     │
↓                     ↓
COMPLETED         TERMINATED
(finished)        (forced end)
```

## Memory vs MongoDB Strategy

### In-Memory (session_manager.sessions)
- **Pros**: Fast access, real-time updates
- **Cons**: Lost on restart, limited to available memory
- **Use**: Current sessions being actively used

### MongoDB
- **Pros**: Persistent, queryable, shareable
- **Cons**: Slightly slower access
- **Use**: Session history, analytics, backups

### Sync Strategy
```
┌────────────┐         ┌──────────────┐
│   Memory   │◄────────►│   MongoDB    │
│  (Faster)  │  Sync    │(Persistent) │
└────────────┘         └──────────────┘
    ↑                         ↑
    │                         │
    └──────── All ops ────────┘
     (create, update, query)
```

## Integration with LangChain Ecosystem

### LangChain Chain
```
Session Config + Input
    ↓
chain.invoke(input, config=session_config)
    ├─ Uses session_id, thread_id, user_id from config
    └─ Maintains context across turns
    
    ↓
    
Output → Add to Session History
    └─ Stored in conversation_history
```

### LangGraph Graph
```
Session created with langgraph_thread_id
    ↓
graph.invoke(
    input_state,
    config={"configurable": {"thread_id": thread_id}}
)
    ├─ Checkpointer stores state at thread_id
    ├─ Can resume from checkpoint
    └─ Full conversation context preserved
```

## WebSocket Integration Example

```
WebSocket Connection
    ↓
User Sends Voice
    ↓
Voice Verification
    ↓
Match? 
    ├─ YES
    │   ├─ Create VerifiedSession
    │   ├─ Create LangChainSession
    │   └─ Send to frontend: {session_id, thread_id}
    │
    └─ NO
        └─ Send error

Client receives session_id
    ↓
Client sends: {session_id, message}
    ↓
Server processes:
    ├─ Validate session
    ├─ Add to conversation
    ├─ Process with LLM/Chain
    ├─ Add response
    └─ Send back to client

...repeat for each turn...

Client closes connection
    ↓
Server:
    ├─ Mark session as COMPLETED
    ├─ Keep in MongoDB for history
    └─ Clean from memory (if expired)
```

## Performance Considerations

1. **Session Lookup**: O(1) from memory dict, indexed MongoDB query
2. **Message Addition**: O(1) append to list
3. **Session Expiration**: O(n) periodic cleanup
4. **MongoDB TTL**: Automatic background cleanup

## Security Considerations

1. **Session ID**: UUID format makes guessing impossible
2. **Thread ID**: LangGraph-specific, separate from session_id
3. **Phone Number**: Indexed for per-user queries
4. **Voice Verified**: Flag ensures only authenticated sessions
5. **Timestamps**: Allows audit trail

## Troubleshooting Guide

### Issue: Session not found in memory
**Solution**: Check MongoDB, session might have expired or restarted

### Issue: Conversation history missing
**Solution**: Verify MongoDB update was successful

### Issue: LangGraph thread not found
**Solution**: Ensure langgraph_thread_id is passed correctly to graph

### Issue: Performance degradation with many sessions
**Solution**: Run cleanup_expired_sessions() more frequently

## Deployment Checklist

- [ ] MongoDB running and accessible
- [ ] Indexes created on langchain_sessions collection
- [ ] TTL index configured for auto-cleanup
- [ ] Session manager initialized before first use
- [ ] Error handling in WebSocket handler
- [ ] Monitoring for expired sessions
- [ ] Cleanup tasks scheduled
- [ ] Logging configured
- [ ] Tests passing

## Next Features

- [ ] User analytics from conversation history
- [ ] Session replay functionality
- [ ] Multi-session support per user
- [ ] Advanced session filtering
- [ ] Real-time session monitoring dashboard
- [ ] Session export/import
- [ ] Conversation summarization
