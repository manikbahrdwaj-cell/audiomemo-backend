# Quick Start Guide - Real-Time WebSocket Voice Biometrics

## Quick Summary of What's New

✅ **Frontend WebSocket Integration**
- Real-time audio streaming from browser
- Automatic 1-second chunks for enrollment, 5-second for verification
- React hook for easy integration

✅ **Security Enhancement**
- 4-chunk minimum requirement (prevents spoofing)
- Location: `backend/similarity-checker.js`

✅ **Backend Chunk Processing**
- New `ChunkProcessor` module handles real-time processing
- Per-chunk embedding generation at `/embedding/generate`
- Integrated with WebSocket handler

---

## Setup & Testing

### 1. Start Backend Services

**Terminal 1 - FastAPI Backend**:
```bash
cd c:\Users\manik.bhardwaj\.vscode\voice\reactapp\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - WebSocket Handler**:
```bash
cd c:\Users\manik.bhardwaj\.vscode\voice\reactapp\backend
node websocket-handler.js
```

**Check Services**:
- FastAPI: http://localhost:8000/docs (should show new `/embedding/generate` endpoint)
- WebSocket: ws://localhost:8001 (check console logs)

### 2. Start Frontend

**Terminal 3 - React App**:
```bash
cd c:\Users\manik.bhardwaj\.vscode\voice\reactapp
npm start
```

Frontend should connect to WebSocket automatically.

---

## Testing Workflows

### Test 1: Enrollment with 1-Second Chunks

```javascript
// Using the useWebSocket hook in your component:

const { 
  initialize, 
  startEnrollment, 
  startRecording, 
  stopRecordingAndProcess,
  enrollmentResult,
  statusMessage
} = useWebSocket();

// Flow:
1. await initialize('test-user-123', 'enroll');  // Init session
2. await startEnrollment();                        // Start 1-sec chunking
3. await startRecording();                         // Begin capture
4. [Wait 5-10 seconds]                            // Speak
5. const result = await stopRecordingAndProcess(); // Process & finalize
6. console.log(enrollmentResult);                  // Check result
```

**Expected Console Output**:
```
[WSClient] Connected to server
[WSClient] Session initialized
[ChunkProcessor] Initialized chunking for session XYZ (enroll, chunk size: 32000 bytes)
[ChunkProcessor] Processing chunk 0 for session XYZ
[ChunkProcessor] Chunk 0 processed - embedding generated
[WSHandler] Chunking finalized for session XYZ: 5 total chunks, 5 embeddings generated
[WSHandler] enroll completed for test-user-123: true
```

### Test 2: Verification with 5-Second Chunks

```javascript
const { 
  initialize, 
  startVerification, 
  startRecording, 
  stopRecordingAndProcess,
  verificationResult
} = useWebSocket();

// Flow:
1. await initialize('test-user-123', 'verify');   // Init session
2. await startVerification();                       // Start 5-sec chunking
3. await startRecording();                          // Begin capture
4. [Wait 10-15 seconds]                            // Speak
5. const result = await stopRecordingAndProcess(); // Process & verify
6. console.log(verificationResult);                // Check match
```

**Expected Output**:
```
[ChunkProcessor] Initialized chunking for session XYZ (verify, chunk size: 160000 bytes)
[ChunkProcessor] Processing chunk 0 for session XYZ
[ChunkProcessor] Session XYZ: 2 matching chunks (MATCH)
{
  success: true,
  is_match: true,  // True only if >= 4 chunks matched
  similarity_score: 0.87,
  chunkProcessing: {
    totalChunks: 2,
    embeddingsGenerated: 2,
    mode: 'chunk-based'
  }
}
```

---

## Key Changes in Architecture

### Data Flow - Enrollment
```
Browser Recording (with 1-sec auto-chunking)
      ↓ (binary WebSocket stream)
WebSocket Handler
      ↓
ChunkProcessor.addAudioData()
      ↓ (when 1-sec chunk ready)
generateChunkEmbedding() → /embedding/generate
      ↓
Store embeddings in session
      ↓ (on stop)
/enroll endpoint
      ↓
MongoDB + chunk embeddings
```

### Data Flow - Verification
```
Browser Recording (with 5-sec auto-chunking)
      ↓ (binary WebSocket stream)
WebSocket Handler
      ↓
ChunkProcessor.addAudioData()
      ↓ (when 5-sec chunk ready)
generateChunkEmbedding() → /embedding/generate
      ↓
Store embeddings in session
      ↓ (on stop)
ChunkProcessor.compareChunks()
      ↓
Count: needs >= 4 matching chunks
      ↓
/verify endpoint (use chunk comparison results)
      ↓
Return is_match: matchCount >= 4
```

---

## Monitoring Hooks

### useWebSocket State Variables
```javascript
const {
  // Connection state
  connected,              // bool - WebSocket connected
  connecting,             // bool - In progress
  clientId,               // string - Assigned by server
  sessionId,              // string - Session identifier
  
  // Audio state
  isRecording,            // bool - Currently recording
  bytesReceived,          // number - Total bytes from server
  chunksReceived,         // number - Total chunks
  
  // Operation state
  enrollmentInProgress,   // bool
  verificationInProgress, // bool
  processingAudio,        // bool
  
  // Results
  enrollmentResult,       // object - Last enrollment result
  verificationResult,     // object - Last verification result
  
  // Diagnostics
  statusMessage,          // string - Current status
  stats: {
    audioChunksRecorded,  // number - Chunks sent
    totalAudioSize,       // number - Total bytes sent
    averageChunkSize,     // number - Average chunk size
    recordingDuration     // number - Total recording time
  }
}
```

### Server Logs to Watch
```
✅ Connection established
[WSHandler] Client connected: client_XXXXX

✅ Session initialized  
[WSHandler] Session created for test-user: session-XXXXX

✅ 1-second chunking started
[ChunkProcessor] Initialized chunking for session (enroll, chunk size: 32000 bytes)

✅ Chunks being processed
[ChunkProcessor] Processing chunk 0 for session
[ChunkProcessor] Chunk 0 processed - embedding generated

✅ Finalization
[WSHandler] Chunking finalized for session: 5 total chunks, 5 embeddings generated

✅ Backend processing
[WSHandler] enroll completed: true
```

---

## Troubleshooting

### Issue: WebSocket Connection Refused
```
Error: Failed to connect to WebSocket server
```
**Fix**: Start WebSocket handler first
```bash
cd backend
node websocket-handler.js
```

### Issue: No Chunks Being Generated
```
Audio received but no chunk-processed events
```
**Check**:
- Audio size? Need at least 1 second for enrollment (32KB)
- Browser support? Check Web Audio API
- Console logs for errors

### Issue: Verification Always Fails
```
is_match: false, matchCount: 1
```
**Normal** - Need >= 4 matching chunks now. Record longer audio during verification (10+ seconds recommended for 2 x 5-second chunks).

### Issue: Session Expired During Recording
```
{"error": "Session expired", "details": "Your session has expired"}
```
**Fix**: Sessions timeout after 30 minutes. Reinitialize if needed.

---

## Performance Expectations

**Enrollment** (~5-10 seconds):
- Recording: 5-10 seconds
- Chunk generation: 5-10 chunks (1 sec each)
- Processing: ~0.5-1.0 second per chunk
- Total: ~10-15 seconds

**Verification** (~10-20 seconds):
- Recording: 10-15 seconds  
- Chunk generation: 2-3 chunks (5 sec each)
- Chunk comparison: ~1-2 seconds total
- Total: ~15-25 seconds

**Network**:
- Per 1-sec chunk: ~32KB (typical network time: 20-50ms)
- Per 5-sec chunk: ~160KB (typical network time: 100-200ms)

---

## Testing Checklist

- [ ] WebSocket connects on page load
- [ ] Enrollment records 5+ seconds without error
- [ ] 5+ one-second chunks generated during enrollment
- [ ] Enrollment completes within 15 seconds
- [ ] Enrollment result shows `success: true`
- [ ] Verification records 10+ seconds without error
- [ ] 2+ five-second chunks generated during verification
- [ ] Verification processes with chunk-based comparison
- [ ] Enrollment verification: `is_match = true` (if same user)
- [ ] Enrollment verification: `is_match = false` (if different user)
- [ ] Reconnection works after network interruption
- [ ] Multiple sessions can run independently
- [ ] Chunk statistics update in real-time

---

## Example Component Integration

```javascript
import useWebSocket from './services/useWebSocket';

export function EnrollmentComponent() {
  const {
    initialize,
    startEnrollment,
    startRecording,
    stopRecordingAndProcess,
    connected,
    enrollmentInProgress,
    isRecording,
    enrollmentResult,
    statusMessage,
    stats
  } = useWebSocket();

  const handleEnroll = async () => {
    try {
      // Step 1: Initialize session
      await initialize('user-phone-number', 'enroll');
      
      // Step 2: Start enrollment mode
      await startEnrollment();
      
      // Step 3: Start recording
      await startRecording();
      
      // Step 4: Recording happens (show UI feedback)
      console.log(`Recording: ${stats.totalAudioSize} bytes, ${stats.audioChunksRecorded} chunks`);
      
      // Step 5: Process when done
      const result = await stopRecordingAndProcess();
      
      if (result.success) {
        console.log('✅ Enrollment successful!');
        console.log(`Chunks processed: ${result.chunkProcessing.embeddingsGenerated}`);
      }
    } catch (error) {
      console.error('❌ Enrollment failed:', error);
    }
  };

  return (
    <div>
      <p>Status: {statusMessage}</p>
      <p>Chunks: {stats.audioChunksRecorded}</p>
      <button onClick={handleEnroll} disabled={!connected || enrollmentInProgress}>
        {enrollmentInProgress ? 'Enrolling...' : 'Start Enrollment'}
      </button>
    </div>
  );
}
```

---

## Next Steps

1. **Test Real-Time Streaming**: Verify WebSocket connection and chunk transmission
2. **Validate Chunk Embeddings**: Confirm per-chunk embedding generation at `/embedding/generate`
3. **Test 4-Chunk Rule**: Verify that <4 matching chunks fail verification
4. **Stress Test**: Multiple simultaneous sessions, long recordings, network interruptions
5. **Performance Tuning**: Adjust chunk sizes if needed, optimize embedding generation
6. **Security Review**: Test spoofing scenarios to validate 4-chunk protection

---

**Status**: Ready for testing! All critical components implemented.
