# LangChain Session Implementation - Integration Checklist

## Pre-Integration Checklist

### Infrastructure
- [ ] MongoDB running and accessible (default: localhost:27017)
- [ ] MongoDB voice_biometric database exists
- [ ] Python 3.8+ installed
- [ ] FastAPI/uvicorn running

### Python Dependencies
- [ ] langchain >= 0.2.0
- [ ] langchain-core >= 0.2.0
- [ ] langchain-openai >= 0.2.0 (if using OpenAI)
- [ ] langgraph >= 0.2.0
- [ ] pymongo >= 4.6.0
- [ ] python-dotenv (for environment variables)
- [ ] pytest (for running tests)

Check with:
```bash
pip list | grep -E "langchain|pymongo"
```

## MongoDB Setup

- [ ] MongoDB connection verified
  ```bash
  mongosh "mongodb://localhost:27017"
  ```

- [ ] Voice biometric database exists
  ```bash
  use voice_biometric
  show collections
  ```

- [ ] Collections will be auto-created:
  - [ ] verified_sessions
  - [ ] langchain_sessions (NEW)

- [ ] Indexes will be auto-created on first use

## Code Integration Steps

### Step 1: Update Imports
In files that handle voice verification, add:
```python
from langchain_session_integration import get_langchain_session_integration
from langchain_session_service import get_langchain_session_manager
```

### Step 2: Integrate with Voice Verification Handler
Locate: `backend/websocket_events.py` or your verification handler

Find the section: "if is_match:" (around line 310)

Add after successful voice match:
```python
if is_match:
    # ... existing code ...
    
    # CREATE LANGCHAIN SESSION
    integration = get_langchain_session_integration()
    session = integration.create_session_on_voice_match(
        phone_number=matched_phone_number,
        verification_score=similarity_score,
        similarity_metrics=comprehensive_metrics
    )
    
    if session['success']:
        langgraph_session_id = session['session_id']
        thread_id = session['thread_id']
        
        # Send to frontend
        # ... update response_message with session details ...
```

### Step 3: Integrate with Message Handling
For handling incoming messages from verified users:

```python
integration = get_langchain_session_integration()

# Add user message
success = integration.add_message_to_session(
    session_id=session_id,
    role="user",
    content=user_message,
    metadata={"source": "websocket"}
)

if success:
    # Process with LLM/Chain
    response = await process_with_llm(user_message, thread_id)
    
    # Add assistant response
    integration.add_message_to_session(
        session_id=session_id,
        role="assistant",
        content=response,
        metadata={"source": "llm"}
    )
```

### Step 4: Update Frontend Communication
Frontend should now handle session_id and thread_id:

```javascript
// After verification success
const { session_id, thread_id } = response;

// Store for subsequent messages
localStorage.setItem('session_id', session_id);
localStorage.setItem('thread_id', thread_id);

// Send messages with session context
ws.send(JSON.stringify({
    type: 'message',
    session_id: session_id,
    thread_id: thread_id,
    content: userMessage
}));
```

## Testing Integration

### Test 1: Basic Module Import
```bash
cd backend
python -c "from langchain_session_service import get_langchain_session_manager; print('✓ Import successful')"
```

### Test 2: Create Sample Session
```bash
python -c "
from langchain_session_integration import get_langchain_session_integration
i = get_langchain_session_integration()
s = i.create_session_on_voice_match('+1-555-0123', 0.95, {'cosine_similarity': 0.95})
print(f'Session created: {s[\"session_id\"][:16]}')
"
```

### Test 3: Run Test Suite
```bash
pytest backend/test_langchain_sessions.py -v
```

Expected output: All tests passing

### Test 4: Verify MongoDB Storage
```bash
mongosh
use voice_biometric
db.langchain_sessions.count()     # Should have test documents
db.langchain_sessions.findOne()   # View structure
```

### Test 5: Integration Test
```bash
cd backend
python langchain_session_integration.py
```

Expected output: Example walkthrough with session lifecycle

## Voice Verification Integration Points

### Point 1: After Successful Voice Match
**File**: `websocket_events.py` (line ~310)

**Current Code**:
```python
if is_match:
    session_manager = get_verified_session_manager()
    verified_session = session_manager.create_verified_session(...)
    langgraph_session_id = session_manager.create_langgraph_session(verified_session)
```

**Now Integrated**: `create_langgraph_session()` now uses `LangChainSessionManager`

### Point 2: Session Retrieval
**File**: `websocket_handler.py` or `api/` routes

**Add**:
```python
integration = get_langchain_session_integration()
session_info = integration.get_session_info(session_id)
if session_info:
    status = session_info['status']
    is_valid = session_info['is_valid']
```

### Point 3: Message Processing
**File**: `websocket_events.py` or message handler

**Add**:
```python
# On receiving user message
integration.add_message_to_session(
    session_id,
    "user",
    message_content,
    metadata={"timestamp": datetime.now().isoformat()}
)

# Process...

# On sending assistant response
integration.add_message_to_session(
    session_id,
    "assistant",
    response_content
)
```

## Environment Configuration

Add to `.env` or `config.py`:
```env
# LangChain Session Configuration
LANGCHAIN_SESSION_TTL=3600              # 1 hour
LANGCHAIN_SESSION_MAX_TURNS=100         # Max conversation turns
LANGCHAIN_CLEANUP_INTERVAL=3600         # Cleanup every hour

# MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=voice_biometric
```

In code:
```python
import os
from dotenv import load_dotenv

load_dotenv()

SESSION_TTL = int(os.getenv("LANGCHAIN_SESSION_TTL", 3600))
MAX_TURNS = int(os.getenv("LANGCHAIN_SESSION_MAX_TURNS", 100))
```

## Monitoring Setup

### Enable Logging
```python
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sessions.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Monitor Session Operations
```python
# Log all session creations
logger.info(f"Created LangChain session {session_id} for user {phone}")

# Log message additions
logger.debug(f"Added {role} message to session {session_id}")

# Monitor errors
logger.error(f"Failed to create session: {error}")
```

## Periodic Maintenance Tasks

### Task 1: Clean Up Expired Sessions
Add to background task scheduler:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def cleanup_expired_sessions():
    integration = get_langchain_session_integration()
    count = integration.cleanup_expired_sessions(ttl_seconds=86400)
    if count > 0:
        logger.info(f"Cleaned up {count} expired sessions")

# Run every hour
scheduler.add_job(cleanup_expired_sessions, "interval", hours=1)
scheduler.start()
```

### Task 2: Monitor Active Sessions
```python
def monitor_active_sessions():
    manager = get_langchain_session_manager()
    active = manager.get_all_active_sessions()
    logger.info(f"Active sessions: {len(active)}")
    
    for session_id, session in active.items():
        summary = manager.get_session_summary(session_id)
        logger.debug(f"  - {session_id[:16]}: {summary['conversation_turns']} turns")

scheduler.add_job(monitor_active_sessions, "interval", minutes=15)
```

### Task 3: Database Maintenance
```python
from database import delete_expired_langchain_sessions

def cleanup_mongodb():
    # Delete sessions older than 30 days
    count = delete_expired_langchain_sessions(ttl_seconds=2592000)
    logger.info(f"Deleted {count} old sessions from MongoDB")

scheduler.add_job(cleanup_mongodb, "interval", days=7)
```

## Deployment Verification

### Before Deploying to Production

- [ ] All tests passing: `pytest backend/test_langchain_sessions.py -v`
- [ ] Import tests passing: Verify all imports work
- [ ] MongoDB accessible from production environment
- [ ] Environment variables configured
- [ ] Logging configured and working
- [ ] Cleanup tasks scheduled
- [ ] Error handling in place
- [ ] Rate limiting configured (if needed)
- [ ] Session timeout values appropriate
- [ ] Monitoring/alerting set up

### Post-Deployment Verification

- [ ] Verify MongoDB connection from production
- [ ] Check session creation on first voice verification
- [ ] Monitor logs for any errors
- [ ] Verify session persistence (disconnect/reconnect)
- [ ] Check MongoDB storage size
- [ ] Verify cleanup tasks running
- [ ] Monitor memory usage
- [ ] Test error scenarios

## Rollback Plan

If issues found:

1. **Revert Code**:
   ```bash
   git revert HEAD
   ```

2. **Keep MongoDB Data**:
   - Sessions are stored, no loss
   - Can restart and restore sessions

3. **Verify Revert**:
   ```bash
   pytest backend/test_langchain_sessions.py -v
   ```

## Performance Baseline

Expected performance metrics:

| Operation | Time | Notes |
|-----------|------|-------|
| Create Session | < 10ms | Memory: < 1ms, MongoDB roundtrip |
| Add Message | 1-2ms | Memory: < 1ms |
| Get Session Info | < 1ms | Memory lookup (O(1)) |
| Cleanup 1000 sessions | < 100ms | Linear in count |
| Memory per session | ~ 1KB | + conversation history |

## Troubleshooting Common Issues

### Issue: MongoDB Connection Error
```
Solution: 
1. Verify MongoDB running: mongosh
2. Check connection string in code
3. Verify credentials if using auth
```

### Issue: Collections not found
```
Solution:
1. Collections auto-create on first use
2. Verify database name matches
3. Check MongoDB logs
```

### Issue: Session not persisting
```
Solution:
1. Verify save_langchain_session() called
2. Check MongoDB write permissions
3. Monitor Mongo logs
```

### Issue: Memory growing too large
```
Solution:
1. Run cleanup_expired_sessions() more frequently
2. Reduce SESSION_TTL
3. Set up MongoDB TTL index properly
```

## Success Criteria

After integration, verify:

- ✅ Sessions created successfully after voice match
- ✅ Session data persisted in MongoDB
- ✅ Messages added to conversation history
- ✅ Session config available for LangChain
- ✅ Thread ID working with LangGraph
- ✅ Session info retrievable
- ✅ Pause/resume working
- ✅ Expiration working
- ✅ Cleanup removing expired sessions
- ✅ No performance degradation
- ✅ Logs showing all operations
- ✅ Tests all passing

## Support Documentation

For detailed information, see:

1. **LANGCHAIN_SESSION_INTEGRATION_GUIDE.md** - Full integration guide
2. **LANGCHAIN_SESSION_QUICK_REFERENCE.md** - API quick reference
3. **LANGCHAIN_SESSION_ARCHITECTURE.md** - System architecture
4. **LANGCHAIN_SESSION_IMPLEMENTATION_SUMMARY.md** - What was created
5. **test_langchain_sessions.py** - Example usage tests
6. **langchain_session_integration.py** - Code examples in `__main__`

## Next Steps After Integration

1. Connect LangChain chains to use session context
2. Implement LangGraph with thread persistence
3. Add conversation analytics
4. Build session monitoring dashboard
5. Implement session export/import
6. Add conversation summarization
7. Create admin session management UI

---

**Integration Status**: Ready for Implementation
**Documentation**: Complete
**Tests**: Comprehensive Suite Available
**Examples**: Included in Code

For questions or issues, refer to documentation or check test cases for usage examples.
