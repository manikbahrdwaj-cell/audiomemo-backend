# Real-Time Feedback - Quick Reference

## Quick Start

### For Backend Developers

1. **Import the dispatcher:**
   ```python
   from chunk_progress_dispatcher import get_chunk_progress_dispatcher, ChunkProgressStatus
   ```

2. **Create a session:**
   ```python
   dispatcher = get_chunk_progress_dispatcher()
   dispatcher.create_session(session_id, total_chunks)
   dispatcher.start_processing(session_id)
   ```

3. **Send progress updates:**
   ```python
   async def send_progress(progress):
       await connection.send_json({
           "type": "chunk_progress",
           "payload": progress.to_dict()
       })
   
   await dispatcher.subscribe(send_progress)
   ```

4. **Update during processing:**
   ```python
   await dispatcher.update_chunk_progress(session_id, chunk_index)
   await dispatcher.mark_chunk_embedded(session_id, chunk_index)
   ```

5. **Finalize:**
   ```python
   await dispatcher.mark_completed(session_id)  # or
   await dispatcher.mark_failed(session_id, "error message")
   ```

### For Frontend Developers

1. **Import components:**
   ```jsx
   import ChunkProcessingIndicator from './components/ChunkProcessingIndicator';
   import { useChunkProgress } from './hooks/useChunkProgress';
   ```

2. **Use the hook:**
   ```jsx
   const { progress, startTracking, stopTracking } = useChunkProgress(wsConnection);
   
   // Start listening
   startTracking();
   
   // Stop listening
   stopTracking();
   ```

3. **Display progress:**
   ```jsx
   <ChunkProcessingIndicator
     isVisible={isProcessing}
     progress={progress}
     onComplete={() => handleComplete()}
     onError={(msg) => handleError(msg)}
   />
   ```

## API Reference

### ChunkProgressDispatcher Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `create_session` | `session_id`, `total_chunks` | `None` | Initialize tracking session |
| `start_processing` | `session_id` | `None` | Mark session as started |
| `update_chunk_progress` | `session_id`, `chunk_index`, `chunk_info?` | `None` | Report chunk processing |
| `mark_chunk_embedded` | `session_id`, `chunk_index`, `embedding_info?` | `None` | Report embedding generated |
| `mark_completed` | `session_id` | `None` | Mark session complete |
| `mark_failed` | `session_id`, `error_message` | `None` | Mark session failed |
| `subscribe` | `callback` | `str` | Add progress listener |
| `unsubscribe` | `callback` | `None` | Remove progress listener |
| `get_session_progress` | `session_id` | `dict` | Get current progress state |

### ChunkProgress Data Structure

```python
@dataclass
class ChunkProgress:
    session_id: str
    status: ChunkProcessingStatus
    current_chunk: int = 0
    total_chunks: int = 0
    percentage: float = 0.0
    duration_ms: float = 0.0
    chunks_processed: List[Dict] = []
    current_chunk_info: Optional[Dict] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
```

### Frontend Props

**ProgressBar:**
```typescript
percentage: number
status: 'processing' | 'completed' | 'failed'
label: string
showPercentage?: boolean
animated?: boolean
size?: 'small' | 'medium' | 'large'
variant?: string
```

**ChunkProcessingIndicator:**
```typescript
isVisible: boolean
progress: ChunkProgress | null
onComplete?: () => void
onError?: (message: string) => void
```

## WebSocket Message Examples

### Progress Update
```json
{
  "type": "chunk_progress",
  "payload": {
    "session_id": "abc-123",
    "status": "processing_chunk",
    "current_chunk": 3,
    "total_chunks": 10,
    "percentage": 30.0,
    "duration_ms": 1250.5,
    "chunks_processed": [...],
    "current_chunk_info": {
      "chunk_index": 2,
      "embedding_generated": true
    },
    "timestamp": "2024-02-14T12:00:00"
  }
}
```

### Enrollment with Progress
```json
{
  "type": "enroll",
  "phone_number": "+1-555-0000",
  "data": "SGVsbG8gV29ybGQh"
}
```

### Verification with Progress
```json
{
  "type": "verify",
  "phone_number": "+1-555-0000",
  "data": "SGVsbG8gV29ybGQh"
}
```

## Common Patterns

### Monitoring Progress in Python
```python
session_id = str(uuid.uuid4())
dispatcher = get_chunk_progress_dispatcher()

# Setup
dispatcher.create_session(session_id, 5)
dispatcher.start_processing(session_id)

# Subscribe
async def handle_progress(progress):
    if progress.percentage >= 100:
        print("✓ Complete!")
    else:
        print(f"█ {progress.percentage:.0f}% - Chunk {progress.current_chunk}")

await dispatcher.subscribe(handle_progress)

# Process...
for i in range(5):
    await dispatcher.update_chunk_progress(session_id, i)
    # ... actual processing ...

await dispatcher.mark_completed(session_id)
```

### Real-time Progress in React
```jsx
function ProcessingComponent() {
  const [progress, setProgress] = useState(null);
  const ws = useRef(null);
  
  useEffect(() => {
    ws.current = new WebSocket('ws://...');
    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'chunk_progress') {
        setProgress(msg.payload);
      }
    };
  }, []);
  
  return (
    <ChunkProcessingIndicator
      isVisible={progress !== null}
      progress={progress}
    />
  );
}
```

## Configuration Examples

### Faster Updates
```python
# Every 50ms instead of 100ms
dispatcher = ChunkProgressDispatcher(update_throttle_ms=50)
```

### Slower Updates
```python
# Every 200ms for low-bandwidth networks
dispatcher = ChunkProgressDispatcher(update_throttle_ms=200)
```

### Session Cleanup
```python
# Sessions automatically cleaned up after 5 seconds
# Can modify in mark_completed/mark_failed calls
await dispatcher._cleanup_session_delayed(session_id, delay_seconds=10)
```

## Status States Flow

```
PENDING → STARTED → PROCESSING_CHUNK ⟷ EMBEDDING_GENERATED → COMPLETED
                                  ↑
                                  └─ FAILED
```

## Styling Customization

### Override Progress Bar Color
```css
.progress-bar-fill {
  background: linear-gradient(90deg, #ff6b6b, #ff8e72);
}
```

### Customize Status Badge
```css
.indicator-status--processing {
  background-color: #your-color;
  color: #your-text-color;
}
```

### Adjust Component Size
```css
.chunk-processing-indicator {
  padding: 2rem;  /* Increase from 1.5rem */
}
```

## Debugging

### Enable Verbose Logging
```python
import logging
logging.getLogger('chunk_progress_dispatcher').setLevel(logging.DEBUG)
```

### Monitor Progress State
```python
dispatcher = get_chunk_progress_dispatcher()
progress = dispatcher.get_session_progress(session_id)
print(progress)
# {
#   'session_id': 'abc-123',
#   'status': 'processing_chunk',
#   'current_chunk': 2,
#   'percentage': 40.0,
#   ...
# }
```

### Check Browser Console
```javascript
// Check WebSocket messages
ws.onmessage = (event) => {
  console.log('Received:', event.data);
};
```

## Performance Tips

1. **Throttle updates** on slow networks (increase update_throttle_ms)
2. **Close WebSocket** when not needed to free resources
3. **Unsubscribe** from progress callbacks to prevent memory leaks
4. **Cleanup sessions** for very long operations
5. **Batch updates** if processing many chunks

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Progress not updating | Check WebSocket connection, verify message format |
| Too many UI re-renders | Increase throttle_ms, use memo() for components |
| Memory issues | Cleanup old sessions, limit subscriber count |
| Slow performance | Reduce animation complexity, increase throttle_ms |
| WebSocket timeout | Increase timeout duration, check network |

## Links

- Full Documentation: `REALTIME_FEEDBACK_DOCUMENTATION.md`
- Backend Module: `backend/chunk_progress_dispatcher.py`
- Components: `frontend/src/components/ChunkProcessingIndicator.jsx`
- Hook: `frontend/src/hooks/useChunkProgress.js`
- Updated Pages: `frontend/src/components/EnrollmentPage.js`, `VerificationPage.js`
