# Real-Time Chunk Processing Feedback

## Overview

This feature provides real-time visual feedback to users during audio chunk processing for both enrollment and verification operations. Users can see detailed progress information including:

- Overall processing progress percentage
- Current chunk being processed
- Total chunks being processed
- Processing duration
- Individual chunk embedding status
- Animations and status indicators

## Architecture

### Backend Components

#### Chunk Progress Dispatcher (`backend/chunk_progress_dispatcher.py`)

The `ChunkProgressDispatcher` class manages real-time progress tracking for audio chunk processing:

**Key Features:**
- Session-based progress tracking
- Throttled progress updates (configurable, default 100ms)
- Multiple subscriber support for progress events
- Automatic session cleanup after completion
- Detailed progress data with timestamps

**Main Classes:**
- `ChunkProgress`: Data class representing current processing state
- `ChunkProgressStatus`: Enum for processing status states
- `ChunkProgressDispatcher`: Main dispatcher for managing progress

**Status States:**
- `PENDING`: Session created, not started
- `STARTED`: Processing initiated
- `PROCESSING_CHUNK`: Currently processing a chunk
- `EMBEDDING_GENERATED`: Embedding created for a chunk
- `COMPLETED`: All chunks processed successfully
- `FAILED`: Processing failed

**Usage Example:**
```python
from chunk_progress_dispatcher import get_chunk_progress_dispatcher

dispatcher = get_chunk_progress_dispatcher()

# Create a new session
dispatcher.create_session(session_id="abc-123", total_chunks=5)
dispatcher.start_processing(session_id="abc-123")

# Subscribe to updates
async def on_progress(progress):
    print(f"Progress: {progress.percentage:.1f}%")

await dispatcher.subscribe(on_progress)

# Update progress as chunks are processed
await dispatcher.update_chunk_progress(
    session_id="abc-123",
    chunk_index=0,
    chunk_info={"duration_ms": 1000}
)

# Mark completion
await dispatcher.mark_completed(session_id="abc-123")
```

### WebSocket Integration

Both enrollment and verification endpoints now emit `chunk_progress` messages via WebSocket:

**Message Format:**
```json
{
  "type": "chunk_progress",
  "payload": {
    "session_id": "uuid",
    "status": "processing_chunk",
    "current_chunk": 1,
    "total_chunks": 5,
    "percentage": 20.0,
    "duration_ms": 250.5,
    "chunks_processed": [
      {
        "chunk_index": 0,
        "timestamp": "2024-02-14T12:00:00",
        "embedding_generated": true
      }
    ],
    "current_chunk_info": {
      "chunk_index": 0,
      "embedding_generated": true
    },
    "error_message": null,
    "timestamp": "2024-02-14T12:00:00"
  }
}
```

### Frontend Components

#### ProgressBar Component (`frontend/src/components/ProgressBar.jsx`)

A reusable progress bar component with visual feedback:

**Props:**
```typescript
interface ProgressBarProps {
  percentage: number;        // 0-100
  status: 'processing' | 'completed' | 'failed';
  label: string;            // Display label
  showPercentage: boolean;  // Show percentage number
  animated: boolean;        // Enable animation
  size: 'small' | 'medium' | 'large';
  variant: string;          // Theme variant
}
```

**Features:**
- Animated progress with shimmer effect
- Status-based color coding
- Responsive sizing
- Dark mode support
- Smooth transitions

**Usage:**
```jsx
<ProgressBar
  percentage={45}
  status="processing"
  label="Processing chunks"
  showPercentage={true}
  animated={true}
  size="medium"
/>
```

#### ChunkProcessingIndicator Component (`frontend/src/components/ChunkProcessingIndicator.jsx`)

Comprehensive status indicator for chunk processing:

**Props:**
```typescript
interface ChunkProcessingIndicatorProps {
  isVisible: boolean;
  progress: ChunkProgress | null;
  onComplete: () => void;
  onError: (message: string) => void;
}
```

**Features:**
- Real-time status updates
- Stats grid with processed chunks, duration, session ID
- Animated status  badge
- Current chunk information display
- Recent chunks visualization with badges
- Error details display
- Loading animation

**Visual Elements:**
- Header with status indicator
- Main progress bar
- Statistics grid
- Current chunk info panel
- Processed chunks list
- Error message display
- Loading dots animation

**Usage:**
```jsx
<ChunkProcessingIndicator
  isVisible={showProgress}
  progress={chunkProgress}
  onComplete={() => console.log('Done!')}
  onError={(msg) => setError(msg)}
/>
```

#### useChunkProgress Hook (`frontend/src/hooks/useChunkProgress.js`)

React hook for managing chunk progress via WebSocket:

**Returns:**
```typescript
interface UseChunkProgressReturn {
  progress: ChunkProgress | null;
  isTracking: boolean;
  startTracking: () => void;
  stopTracking: () => void;
  resetProgress: () => void;
}
```

**Advanced Version - useChunkProgressWithParser:**
```typescript
interface UseChunkProgressWithParserOptions {
  onChunkStart?: (chunkIndex: number) => void;
  onChunkComplete?: (chunkIndex: number, info: object) => void;
  onProcessingComplete?: (summary: object) => void;
  onProcessingError?: (message: string) => void;
}
```

**Usage:**
```jsx
const { progress, isTracking, startTracking } = useChunkProgress(wsConnection);

// Advanced usage
const { progress } = useChunkProgressWithParser(
  wsConnection,
  (idx) => console.log(`Chunk ${idx} started`),
  (idx, info) => console.log(`Chunk ${idx} embedded`),
  (summary) => console.log(`Complete: ${summary.totalChunks} chunks`),
  (error) => console.error(error)
);
```

### Updated Endpoints

#### Enrollment (`POST /enroll` via WebSocket)

Now supports real-time progress tracking:

**Sends:**
```json
{
  "type": "enroll",
  "phone_number": "+1-555-0000",
  "data": "base64-encoded-audio"
}
```

**Receives Progress Messages:**
- `chunk_progress` events during processing
- `enrollment_success` upon completion

#### Verification (`POST /verify` via WebSocket)

Now supports real-time progress tracking:

**Sends:**
```json
{
  "type": "verify",
  "phone_number": "+1-555-0000",
  "data": "base64-encoded-audio"
}
```

**Receives Progress Messages:**
- `chunk_progress` events during processing
- `verification_result` upon completion

## Integration with Enrollment & Verification Pages

### EnrollmentPage Updates

The `EnrollmentPage.js` component now:
1. Opens a WebSocket connection before submission
2. Sends audio chunks via WebSocket
3. Listens for `chunk_progress` messages
4. Displays progress with `ChunkProcessingIndicator`
5. Handles completion and errors gracefully

**Modified Methods:**
- `handleSubmit()`: Now uses WebSocket instead of HTTP POST

**New State:**
- `chunkProgress`: Current progress object
- `showChunkProgress`: Visibility flag for indicator
- `wsRef`: WebSocket reference

### VerificationPage Updates

The `VerificationPage.js` component now:
1. Opens a WebSocket connection before verification
2. Sends audio chunks via WebSocket
3. Listens for `chunk_progress` messages
4. Displays progress with `ChunkProcessingIndicator`
5. Shows results with real-time feedback

**Modified Methods:**
- `handleVerify()`: Now uses WebSocket instead of HTTP POST

**New State:**
- `chunkProgress`: Current progress object
- `showChunkProgress`: Visibility flag for indicator
- `wsRef`: WebSocket reference

## Styling

### Styles Files

- `frontend/src/styles/ProgressBar.css`: Progress bar styling
- `frontend/src/styles/ChunkProcessingIndicator.css`: Indicator styling

**Features:**
- Smooth animations and transitions
- Color-coded status indicators
- Responsive design
- Dark mode support
- Gradient backgrounds

## Configuration

### Backend Throttling

The chunk progress dispatcher throttles updates by default (100ms):

```python
dispatcher = ChunkProgressDispatcher(update_throttle_ms=100)
```

Lower values = more frequent updates (more bandwidth)
Higher values = fewer updates (smoother UI)

### Progress Updates

Estimate chunks based on audio size:
```python
# At 16kHz, 16000 samples = 1 second
# Each sample = 2 bytes
estimated_chunks = len(audio_data) // (16000 * 2)
```

## Error Handling

### Backend Errors

Failed processing is tracked and reported:
```python
await dispatcher.mark_failed(session_id, "Error message")
```

Progress message with `status: "failed"`:
```json
{
  "status": "failed",
  "error_message": "Embedding generation timeout",
  "percentage": 0.0
}
```

### Frontend Error Handling

Components handle errors gracefully:
- Display error messages in indicator
- Close WebSocket on error
- Call `onError` callback
- Return to idle state

## Performance Considerations

1. **Throttling**: Update frequency controlled to avoid UI lag
2. **Memory**: Old sessions cleaned up after 5 seconds
3. **WebSocket**: Binary data conversion uses base64 for simplicity
4. **Animation**: CSS animations are GPU-accelerated

## Browser Compatibility

- Modern browsers supporting WebSocket
- CSS Grid and Flexbox layouts
- CSS Animations and Transitions
- FileReader API for audio processing

## Testing

### Backend Test

```python
import asyncio
from chunk_progress_dispatcher import get_chunk_progress_dispatcher

async def test_progress():
    dispatcher = get_chunk_progress_dispatcher()
    
    session_id = "test-123"
    dispatcher.create_session(session_id, 5)
    dispatcher.start_processing(session_id)
    
    async def on_progress(progress):
        print(f"Progress: {progress.percentage:.1f}%")
    
    await dispatcher.subscribe(on_progress)
    
    for i in range(5):
        await dispatcher.update_chunk_progress(session_id, i)
        await asyncio.sleep(0.5)
    
    await dispatcher.mark_completed(session_id)

asyncio.run(test_progress())
```

### Frontend Test

```jsx
import ChunkProcessingIndicator from './ChunkProcessingIndicator';

// Mock progress data
const mockProgress = {
  session_id: "test-123",
  status: "processing_chunk",
  current_chunk: 2,
  total_chunks: 5,
  percentage: 40.0,
  duration_ms: 1500,
  chunks_processed: [
    { chunk_index: 0, embedding_generated: true },
    { chunk_index: 1, embedding_generated: true }
  ],
  timestamp: new Date().toISOString()
};

// Test render
<ChunkProcessingIndicator
  isVisible={true}
  progress={mockProgress}
  onComplete={() => {}}
  onError={() => {}}
/>
```

## Future Enhancements

1. **Detailed Analytics**: Per-chunk timing and metrics
2. **Custom Visualizations**: Audio waveforms, spectrograms
3. **Pause/Resume**: Allow pausing long operations
4. **Retry Logic**: Automatic chunk retry on failure
5. **Progress Persistence**: Save progress to localStorage
6. **Mobile Optimization**: Responsive progress indicators
7. **Accessibility**: ARIA labels, keyboard navigation

## Troubleshooting

### Progress Not Showing

1. Verify WebSocket connection is established
2. Check browser console for connection errors
3. Ensure backend is sending chunk_progress messages
4. Verify `showChunkProgress` state is true

### Updates Not Received

1. Check WebSocket message format
2. Verify JSON parsing in frontend
3. Check throttle settings (may be too high)
4. Monitor network tab for message delivery

### UI Lag During Processing

1. Increase `update_throttle_ms` on backend
2. Reduce animation complexity
3. Check browser performance in DevTools
4. Verify renderer not blocked by other tasks

## Contributing

When adding new progress-related features:
1. Update `ChunkProgressStatus` enum if adding new states
2. Ensure WebSocket messages include all required fields
3. Add TypeScript types if using TypeScript
4. Test with various audio durations
5. Verify dark mode compatibility
6. Check mobile responsiveness
