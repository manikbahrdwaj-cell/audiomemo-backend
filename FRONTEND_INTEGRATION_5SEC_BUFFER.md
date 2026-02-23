# Frontend Integration Guide: 5-Second Buffer Voice Verification

## Overview

The backend verification system now accumulates audio for 5 seconds before processing. Frontend clients must handle a new **"buffering"** message type in addition to existing messages.

## Message Flow Diagram

```
Client                      Backend                   Frontend Display
  │                           │                            │
  ├─ audio (1s) ──────────→  Buffer [1.0s]  ──→ "buffering" ──→ Show 20% progress
  │                           │                            │
  ├─ audio (1s) ──────────→  Buffer [2.0s]  ──→ "buffering" ──→ Show 40% progress
  │                           │                            │
  ├─ audio (1s) ──────────→  Buffer [3.0s]  ──→ "buffering" ──→ Show 60% progress
  │                           │                            │
  ├─ audio (1s) ──────────→  Buffer [4.0s]  ──→ "buffering" ──→ Show 80% progress
  │                           │                            │
  ├─ audio (1s) ──────────→  Buffer [5.0s]  ──→ PROCESS     ──→ Process result
  │                           ├─ Merge                      │
  │                           ├─ Embed                      │
  │                           ├─ Compare                    │
  │                           └─ Clear buffer               │
  │                           │                            │
  │                           ├─ chunk_result        ──→ Show similarity score
  │                           │  (0.82, not match)         
  │                           │                            │
  │                           ├─ Clear buffer & start next  │
  │                           │                            │
  ├─ audio (1s) ──────────→  Buffer [1.0s]  ──→ "buffering" ──→ Show 20% progress
  │
  ... (repeat buffer accumulation for up to 4 chunks)
  │
  └─ final audio ──────────→  Process chunk 2      
                           ├─ Embed
                           ├─ Compare
                           └─ final_status="verified" ──→ Show verification result
```

## New Message Types

### 1. Buffering Message

**When:** Sent when audio buffer is accumulating (< 5 seconds)

**Format:**
```json
{
  "type": "buffering",
  "buffer_duration": 3.2,
  "target_duration": 5.0
}
```

**Fields:**
- `type`: String = "buffering"
- `buffer_duration`: Float = seconds accumulated so far
- `target_duration`: Float = target seconds (5.0)

**Frontend Action:**
- Display progress indicator
- Calculate percentage: `(buffer_duration / target_duration * 100)`
- Show visual feedback (progress bar, percentage text, etc.)
- **Do NOT** close connection
- **Do NOT** show result yet

**Example Implementation:**
```javascript
if (response.type === "buffering") {
  const percent = Math.round(
    (response.buffer_duration / response.target_duration) * 100
  );
  updateProgressBar(percent); // Show 0-100%
}
```

### 2. Chunk Result Message (Unchanged)

**When:** Sent after a 5-second chunk is processed

**Format:**
```json
{
  "type": "chunk_result",
  "chunk_number": 1,
  "max_chunks": 4,
  "similarity_score": 0.82,
  "threshold": 0.75,
  "is_match": false
}
```

**Fields:**
- `type`: String = "chunk_result"
- `chunk_number`: Integer = which chunk (1-4)
- `max_chunks`: Integer = total chunks possible (4)
- `similarity_score`: Float = cosine similarity (0.0-1.0)
- `threshold`: Float = comparison threshold (0.75)
- `is_match`: Boolean = score >= threshold
- `final_status`: String (optional) = "verified" or "unverified"
- `verified_at_chunk`: Integer (optional) = chunk number if verified

**Frontend Action:**
- If NO `final_status`: Continue listening for next chunk
- If `final_status` present: Processing complete
  - Show "verified" message
  - OR show "unverified" message
  - Close connection

## Complete Message Sequence Examples

### Example 1: Successful Verification on Chunk 2

```javascript
// 1. User connects and clicks "Start Verification"
websocket.onmessage = (event) => {
  const response = JSON.parse(event.data);
  
  // Buffering phase (5-6 messages)
  if (response.type === "buffering") {
    console.log(`Buffering: ${response.buffer_duration}s / ${response.target_duration}s`);
    displayProgress(response.buffer_duration, response.target_duration);
  }
  
  // After 5 seconds of audio accumulated
  else if (response.type === "chunk_result") {
    console.log(`Chunk ${response.chunk_number}`);
    console.log(`Similarity: ${response.similarity_score.toFixed(3)}`);
    
    if (!response.final_status) {
      // Not done yet, buffer the next chunk
      displayMessage(`Chunk complete (${response.chunk_number}/4), starting next...`);
    } else if (response.final_status === "verified") {
      // SUCCESS!
      displayMessage("✓ Verification successful!");
      displayMessage(`Matched on chunk ${response.chunk_number}`);
      websocket.close();
    } else {
      // FAILED after all chunks
      displayMessage("✗ Verification failed");
      websocket.close();
    }
  }
};

// Message sequence:
// → buffering: 1.0s / 5.0s
// → buffering: 2.0s / 5.0s
// → buffering: 3.0s / 5.0s
// → buffering: 4.0s / 5.0s
// → buffering: 5.0s / 5.0s
// → chunk_result: chunk_number=1, similarity=0.82, is_match=false
// → buffering: 0.5s / 5.0s (next chunk starting)
// → buffering: 1.5s / 5.0s
// ... (continue buffering)
// → chunk_result: chunk_number=2, similarity=0.88, final_status="verified"
// (connection closes)
```

### Example 2: Failed Verification After 4 Chunks

```javascript
// Message sequence:
// → buffering: 1.0-5.0s progression (chunk 1)
// → chunk_result: chunk_number=1, similarity=0.68, is_match=false
// → buffering: 1.0-5.0s progression (chunk 2)
// → chunk_result: chunk_number=2, similarity=0.70, is_match=false
// → buffering: 1.0-5.0s progression (chunk 3)
// → chunk_result: chunk_number=3, similarity=0.72, is_match=false
// → buffering: 1.0-5.0s progression (chunk 4)
// → chunk_result: chunk_number=4, similarity=0.68, is_match=false, final_status="unverified"
// (connection closes)
```

## Frontend Implementation Patterns

### Pattern 1: React Component

```jsx
const VerificationComponent = () => {
  const [bufferProgress, setBufferProgress] = useState(0);
  const [currentChunk, setCurrentChunk] = useState(0);
  const [results, setResults] = useState([]);
  const [verificationStatus, setVerificationStatus] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    wsRef.current = new WebSocket(`ws://localhost:8000/ws/verify/${phoneNumber}`);
    
    wsRef.current.onmessage = (event) => {
      const response = JSON.parse(event.data);
      
      if (response.type === "buffering") {
        const percent = Math.round(
          (response.buffer_duration / response.target_duration) * 100
        );
        setBufferProgress(percent);
      } 
      else if (response.type === "chunk_result") {
        setResults(prev => [...prev, {
          chunk: response.chunk_number,
          similarity: response.similarity_score,
          isMatch: response.is_match
        }]);
        setCurrentChunk(response.chunk_number);
        
        if (response.final_status) {
          setVerificationStatus(response.final_status);
          wsRef.current.close();
        } else {
          setBufferProgress(0); // Reset for next chunk
        }
      }
    };
    
    return () => wsRef.current?.close();
  }, [phoneNumber]);

  return (
    <div>
      {verificationStatus === null && (
        <>
          <ProgressBar value={bufferProgress} />
          <p>Chunk {currentChunk} - {bufferProgress}% buffered</p>
          {results.map((r, i) => (
            <div key={i}>
              Chunk {r.chunk}: {r.similarity.toFixed(3)} 
              {r.isMatch ? "✓" : "✗"}
            </div>
          ))}
        </>
      )}
      {verificationStatus === "verified" && (
        <div className="success">✓ Verified!</div>
      )}
      {verificationStatus === "unverified" && (
        <div className="error">✗ Verification Failed</div>
      )}
    </div>
  );
};
```

### Pattern 2: Plain JavaScript

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/verify/${phoneNumber}`);

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  
  if (response.type === "buffering") {
    const percent = (response.buffer_duration / response.target_duration * 100).toFixed(0);
    document.getElementById("progress").textContent = `${percent}%`;
    document.getElementById("progress-bar").style.width = `${percent}%`;
  }
  
  else if (response.type === "chunk_result") {
    const resultDiv = document.createElement("div");
    resultDiv.textContent = `Chunk ${response.chunk_number}: ${response.similarity_score.toFixed(3)}`;
    document.getElementById("results").appendChild(resultDiv);
    
    if (response.final_status === "verified") {
      document.getElementById("final-result").textContent = "✓ VERIFIED";
      document.getElementById("final-result").className = "success";
      ws.close();
    } else if (response.final_status === "unverified") {
      document.getElementById("final-result").textContent = "✗ UNVERIFIED";
      document.getElementById("final-result").className = "error";
      ws.close();
    }
  }
};
```

## UI/UX Recommendations

### Progress Display
```
Buffering: [████████░░░░░░░░░░░░░░░░░░] 40% (2.0s / 5.0s)
```

### Chunk Results Display
```
Chunk 1: 0.820 ✗ (below 0.75 threshold)
Chunk 2: 0.880 ✓ (above 0.75 threshold) [VERIFIED]
```

### Timeline Display
```
Audio Length:    |-------|-------|-------|-------|
                 Chunk 1 Chunk 2 Chunk 3 Chunk 4
                  5s      5s      5s      5s
```

### Status Indicators
- 🔵 Recording / Buffering
- 🟡 Processing (after 5s buffered)
- 🟢 Verified (threshold met)
- 🔴 Unverified (no threshold after 4 chunks)

## Migration Guide

### If Using Old Protocol

**Old:**
```javascript
websocket.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.chunk_number) {
    // Process chunk
    displayResult(data.similarity_score);
  }
};
```

**New:**
```javascript
websocket.onmessage = (e) => {
  const data = JSON.parse(e.data);
  
  if (data.type === "buffering") {
    // NEW: Handle buffering
    displayProgress(data.buffer_duration);
  }
  else if (data.type === "chunk_result") {
    // Same logic as before
    displayResult(data.similarity_score);
  }
};
```

## Testing Considerations

1. **Short Audio:** Send 1-second chunks repeatedly
   - Expect 5 buffering messages before chunk result

2. **Variable Chunks:** Send 0.8s, 1.2s, 1.5s chunks
   - Expect buffering until sum ≥ 5.0s

3. **Continuous Stream:** Send audio stream at 16kHz
   - Expect buffering progress increasing
   - Expect chunk result after 80,000 samples

4. **Early Disconnection:** Close connection during buffering
   - Should not cause server errors

## Performance Impact on Frontend

- **Bandwidth:** Same (same audio sent)
- **Messages:** More messages (buffering + chunk results)
- **UI Responsiveness:** Show progress during buffering phase
- **User Perception:** 5-second delay before first result

## Error Handling

```javascript
websocket.onerror = (error) => {
  console.error("WebSocket error:", error);
  displayError("Connection error during verification");
};

websocket.onclose = (event) => {
  if (event.code !== 1000) {
    // Unexpected close
    displayError("Verification interrupted");
  } else {
    // Normal close after verification
    displayFinalResult(verificationStatus);
  }
};
```

## Summary

| Aspect | Before | After | Action Required |
|--------|--------|-------|-----------------|
| Message Types | 1 type | 2 types | Handle "buffering" |
| Messages per Chunk | 1 | 5-10 | Process multiple |
| First Result | 1 second | 5 seconds | Set expectations |
| Buffer Progress | None | Available | Show to user |
| Connection Timing | Shorter | Longer | Adjust timeouts |
| Total Data Volume | 4-20s audio | 4-20s audio | None |
