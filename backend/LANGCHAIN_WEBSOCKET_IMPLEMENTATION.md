# LangChain WebSocket Integration Guide

## Overview
This guide demonstrates how to integrate LangChain session management with WebSocket events, including how to use RunnableConfig with your chains and graphs.

## 1. Architecture

```
Voice Verification → LangChain Session Created
                        ↓
                  WebSocket Handler
                        ↓
        Chat Message Handler → Integration → Database
                        ↓
            LangChain Chain/Graph
                        ↓
            RunnableConfig (Thread + Metadata)
```

## 2. WebSocket Integration Implementation

### 2.1 Before Integration
The websocket_events.py only handled:
- Voice audio chunks
- Enrollment
- Verification

### 2.2 After Integration
Now includes:
- Voice verification WITH LangChain session creation
- Chat message handling with session tracking
- Session information retrieval
- RunnableConfig support for chains

## 3. Using RunnableConfig in Your Chains

### 3.1 Basic Setup

```python
from langchain_core.runnables import RunnableConfig
from langchain_session_integration import get_langchain_session_integration

# Get session info
integration = get_langchain_session_integration()
session_info = integration.get_session_info(session_id)

# Create RunnableConfig with thread_id and metadata
config = RunnableConfig(
    run_name=f"voice_verified_{phone_number}",
    tags=["voice_verified", "websocket"],
    configurable={
        "session_id": session_id,
        "thread_id": session_info["thread_id"],
        "phone_number": phone_number,
        "verified": True
    },
    callbacks=[] # Add your callbacks here
)
```

### 3.2 Using Config with LangChain Chains

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

# Create a simple chain
llm = ChatOpenAI(model="gpt-4")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant for voice-verified users."),
    ("human", "{message}")
])

chain = prompt | llm

# Get session and create config
integration = get_langchain_session_integration()
session_info = integration.get_session_info(langchain_session_id)

config = RunnableConfig(
    configurable={
        "session_id": langchain_session_id,
        "thread_id": session_info["thread_id"],
        "phone_number": phone_number
    }
)

# Invoke chain with config
response = chain.invoke(
    {"message": "Hello, how can you help?"},
    config=config
)

# Add response to session
integration.add_message_to_session(
    session_id=langchain_session_id,
    role="assistant",
    content=response.content,
    metadata={"config": config}
)
```

### 3.3 Using Config with LangGraph

```python
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableConfig

# Create a graph
graph_builder = StateGraph(AgentState)
# ... build your graph ...

# Compile graph
graph = graph_builder.compile()

# Get session
integration = get_langchain_session_integration()
session_info = integration.get_session_info(langchain_session_id)

config = RunnableConfig(
    configurable={
        "thread_id": session_info["thread_id"],
        "session_id": langchain_session_id,
        "phone_number": phone_number
    }
)

# Invoke graph with thread_id from config
result = graph.invoke(
    {"messages": [("user", user_message)]},
    config=config,
    thread_id=config.configurable.get("thread_id")
)

# Store in session
integration.add_message_to_session(
    session_id=langchain_session_id,
    role="assistant",
    content=result["messages"][-1].content
)
```

## 4. WebSocket Event Flow

### 4.1 Verification → LangChain Session

**Current Flow in websocket_events.py (handle_verify method):**

```python
# After successful voice match:
is_match = similarity_score >= SIMILARITY_THRESHOLD

if is_match:
    # 1. Create verified session
    verified_session = session_manager.create_verified_session(...)
    
    # 2. CREATE LANGCHAIN SESSION (NEW)
    integration = get_langchain_session_integration()
    session_result = integration.create_session_on_voice_match(
        phone_number=matched_phone_number,
        verification_score=similarity_score,
        similarity_metrics=comprehensive_metrics
    )
    
    # 3. Store in MongoDB
    session_doc["langchain_session_id"] = session_result['session_id']
    save_verified_session(session_doc)
    
    # 4. Update connection metadata
    connection.set_metadata("langchain_session_id", langchain_session_id)
```

### 4.2 Chat Message → LangChain Session

**New Handler: handle_chat_message**

```python
async def handle_chat_message(
    self, 
    connection: ClientConnection,
    message: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handles incoming chat messages from verified users
    """
    # 1. Get session from connection metadata
    langchain_session_id = connection.metadata.get("langchain_session_id")
    
    # 2. Add user message to session
    integration = get_langchain_session_integration()
    integration.add_message_to_session(
        session_id=langchain_session_id,
        role="user",
        content=message["content"],
        metadata={"source": "websocket"}
    )
    
    # 3. Return acknowledgment
    return {
        "status": "message_received",
        "session_id": langchain_session_id
    }
```

### 4.3 Session Information Retrieval

**New Handler: handle_get_session**

```python
async def handle_get_session(
    self,
    connection: ClientConnection
) -> Dict[str, Any]:
    """
    Get current session information
    """
    langchain_session_id = connection.metadata.get("langchain_session_id")
    integration = get_langchain_session_integration()
    session_info = integration.get_session_info(langchain_session_id)
    
    return {
        "status": "success",
        "session_info": session_info
    }
```

## 5. Complete Workflow Example

### 5.1 Frontend Sends Voice for Verification

```javascript
// Frontend
websocket.send({
    event: "verify",
    phone_number: "+1-555-0123",
    audio_data: base64_encoded_audio
});
```

### 5.2 Backend Processes Verification & Creates Session

```python
# Backend (websocket_events.handle_verify)

# Voice matches → Create LangChain session
if is_match:
    integration = get_langchain_session_integration()
    session_result = integration.create_session_on_voice_match(...)
    
    # Send to frontend
    result_message = {
        "event": "verification_result",
        "status": "success",
        "langchain_session_id": session_result['session_id'],
        "thread_id": session_result['thread_id']
    }
```

### 5.3 Frontend Stores Session IDs

```javascript
// Frontend
websocket.on("verification_result", (data) => {
    if (data.status === "success") {
        // Store session IDs for future use
        userSession = {
            langchain_session_id: data.langchain_session_id,
            thread_id: data.thread_id,
            verified: true
        };
    }
});
```

### 5.4 Frontend Sends Chat Message

```javascript
// Frontend
websocket.send({
    event: "chat_message",
    content: "I need help with my account",
    session_id: userSession.langchain_session_id
});
```

### 5.5 Backend Processes Chat with LangChain

```python
# Backend (NEW: websocket_events.handle_chat_message)

# Add to session
integration.add_message_to_session(
    session_id=langchain_session_id,
    role="user",
    content=user_message
)

# Get session config for chain
session_info = integration.get_session_info(langchain_session_id)
config = RunnableConfig(
    configurable={
        "session_id": langchain_session_id,
        "thread_id": session_info["thread_id"],
        "phone_number": phone_number
    }
)

# Process with LangChain chain/graph
response = await llm_chain.ainvoke(
    {"message": user_message},
    config=config
)

# Store response
integration.add_message_to_session(
    session_id=langchain_session_id,
    role="assistant",
    content=response.content
)
```

## 6. Event Router Integration

To use these new handlers, update your WebSocket router:

```python
# In your websocket connection router
message_type = message.get("event") or message.get("type")

if message_type == "chat_message":
    response = await event_handler.handle_chat_message(connection, message)
elif message_type == "get_session":
    response = await event_handler.handle_get_session(connection)
elif message_type == "verify":
    response = await event_handler.handle_verify(connection, message)
# ... other handlers ...

# Send response
await connection.send_json(response)
```

## 7. RunnableConfig Best Practices

### 7.1 Configurable Parameters

```python
config = RunnableConfig(
    configurable={
        # Required
        "session_id": langchain_session_id,
        "thread_id": langgraph_thread_id,
        
        # User Context
        "phone_number": phone_number,
        "verification_score": 0.92,
        
        # Session Context
        "source": "websocket",
        "client_id": connection.client_id,
        
        # Chain-specific
        "model": "gpt-4",
        "temperature": 0.7
    }
)
```

### 7.2 Using in Chain Definition

```python
from langchain_core.runnables import RunnableConfig

def create_chain(config: RunnableConfig):
    """Create chain with session context"""
    
    system_prompt = f"""
    You are assisting a voice-verified user.
    Phone: {config.configurable['phone_number']}
    Verification: {config.configurable['verification_score']:.2%}
    Session: {config.configurable['session_id']}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{message}")
    ])
    
    return prompt | ChatOpenAI(temperature=config.configurable.get("temperature", 0.7))

# Usage
config = create_config(...)
chain = create_chain(config)
response = chain.invoke({"message": "Hello"})
```

## 8. Testing the Integration

### 8.1 Run Tests

```bash
cd backend
pytest test_langchain_sessions.py -v
```

### 8.2 Test Coverage

- ✅ Session metadata creation
- ✅ Session manager operations
- ✅ Conversation history tracking
- ✅ Session pause/resume
- ✅ Session termination
- ⚠️ Integration with MongoDB (requires DB connection)
- ⚠️ RunnableConfig edge cases

### 8.3 Manual Testing

```python
# In Python interactive shell
from langchain_session_integration import get_langchain_session_integration

integration = get_langchain_session_integration()

# Create session
result = integration.create_session_on_voice_match(
    phone_number="+1-555-0123",
    verification_score=0.92,
    similarity_metrics={"cosine_similarity": 0.92}
)

# Add messages
integration.add_message_to_session(
    session_id=result['session_id'],
    role="user",
    content="Hello"
)

# Get info
info = integration.get_session_info(result['session_id'])
print(info)
```

## 9. Integration Checklist

- [x] LangChain session service implemented
- [x] Session managers and metadata classes created
- [x] MongoDB integration for persistence
- [x] WebSocket events updated with LangChain creation
- [x] Chat message handler added
- [x] Session info handler added
- [x] RunnableConfig support enabled
- [ ] LLM chain integration (implement in your use case)
- [ ] LangGraph integration (implement in your use case)
- [ ] Frontend WebSocket event handlers (see FRONTEND_WEBSOCKET_STREAMING.md)
- [ ] Production deployment (see FINAL_DEPLOYMENT_CHECKLIST.md)

## 10. Next Steps

1. **Implement LLM Processing**: Create handlers that process chat messages with LangChain chains
   ```python
   from langchain_openai import ChatOpenAI
   # Implement message processing with RunnableConfig
   ```

2. **Add LangGraph**: Implement multi-step agentic flows
   ```python
   from langgraph.graph import StateGraph
   # Build agent graphs with session context
   ```

3. **Update Frontend**: Handle new WebSocket events in frontend
   - Listen for `chat_response` events
   - Display session information
   - Handle errors gracefully

4. **Add Monitoring**: Track session metrics
   - Session duration
   - Message counts
   - Error rates

5. **Deploy**: Follow FINAL_DEPLOYMENT_CHECKLIST.md

## References

- [langchain_session_service.py](langchain_session_service.py)
- [langchain_session_integration.py](langchain_session_integration.py)
- [websocket_events.py](websocket_events.py) - Updated handlers
- [test_langchain_sessions.py](test_langchain_sessions.py)
