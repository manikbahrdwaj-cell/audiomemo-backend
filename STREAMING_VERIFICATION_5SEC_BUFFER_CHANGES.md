# Streaming Verification 5-Second Buffer Implementation

## Overview

Modified the real-time streaming verification system to accumulate incoming audio until **5 seconds** is collected before processing, replacing the previous **1-second chunk processing** approach.

## Changes Made

### 1. StreamingVerificationSession Data Structure

**File:** `backend/verification_streaming_service.py`

#### Added Fields:
```python
# Audio buffer for accumulating chunks (5-second accumulation)
audio_buffer: List[bytes] = field(default_factory=list)
buffer_duration_seconds: float = 0.0
target_duration_seconds: float = 5.0
sample_rate: int = 16000

# Chunk tracking (now tracks processed 5-second chunks)
chunks_processed: int = 0  # Changed from chunks_received
```

**Rationale:** These fields track the accumulated audio data and know when to process.

### 2. Modified process_chunk() Method

**File:** `backend/verification_streaming_service.py`

#### New Logic Flow:

1. **Receive incoming audio chunk** (any duration)
2. **Calculate chunk duration** from audio data
3. **Add to buffer** (`audio_buffer` list)
4. **Accumulate duration** (`buffer_duration_seconds += chunk_duration`)
5. **Check buffer status:**
   - If `buffer_duration_seconds < 5.0`: Return `buffering` response, continue accumulating
   - If `buffer_duration_seconds >= 5.0`: Process the accumulated audio
6. **On processing:**
   - Merge all buffered audio chunks using `_merge_audio_chunks()`
   - Generate single embedding from merged 5-second audio
   - Calculate similarity against stored embedding
   - Clear buffer for next 5-second accumulation
   - Increment `chunks_processed` counter
7. **Check completion:**
   - If `similarity_score >= threshold`: Mark as `verified`
   - If `chunks_processed >= max_chunks` (4): Mark as `unverified`
   - Otherwise: Continue to buffer next 5 seconds

#### Key Changes:
- **Old:** Process each chunk immediately, increment counter per chunk
- **New:** Accumulate chunks, only process when buffer reaches 5 seconds

### 3. New _merge_audio_chunks() Helper Method

**File:** `backend/verification_streaming_service.py`

Merges multiple WAV audio chunks into a single continuous audio buffer:

```python
def _merge_audio_chunks(self, audio_chunks: List[bytes], sample_rate: int) -> bytes:
    """
    Merge multiple audio chunks into a single audio buffer.
    - Reads each chunk with soundfile
    - Converts to numpy arrays
    - Handles mono/stereo conversion
    - Concatenates all audio
    - Writes merged audio back to WAV bytes
    """
```

**Purpose:** Combines incoming small audio packets into one coherent 5-second audio sample for embedding generation.

### 4. WebSocket Handler Updates

**File:** `backend/main.py` - `websocket_verify_endpoint()`

#### New Response Handling:

Added buffering status responses before chunk results:

```python
# Handle buffering status (accumulating audio, not yet processing)
if result.get("type") == "buffering" or result.get("buffering"):
    buffering_response = {
        "type": "buffering",
        "buffer_duration": result.get("buffer_duration"),
        "target_duration": result.get("target_duration", 5.0)
    }
    await websocket.send_json(buffering_response)
    continue  # Don't close connection, keep accumulating
```

#### Response Flow:

1. **During buffering (< 5 seconds):**
   ```json
   {
     "type": "buffering",
     "buffer_duration": 3.2,
     "target_duration": 5.0
   }
   ```

2. **After processing (>= 5 seconds):**
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

3. **On completion:**
   ```json
   {
     "type": "chunk_result",
     "chunk_number": 2,
     "max_chunks": 4,
     "similarity_score": 0.88,
     "threshold": 0.75,
     "is_match": true,
     "final_status": "verified",
     "verified_at_chunk": 2
   }
   ```

### 5. Updated Documentation

**File:** `backend/main.py` - WebSocket endpoint docstring

Updated to reflect:
- 5-second buffer accumulation behavior
- New "buffering" message type
- Merge process before embedding generation
- Maximum 4 chunks = 20 seconds total

## Behavior Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Processing Trigger** | Every 1-second chunk | Every 5-second accumulation |
| **Embedding Generation** | Per 1-second chunk | Per merged 5-second buffer |
| **Maximum Duration** | 4 seconds | 20 seconds (4 × 5-second chunks) |
| **Buffer State** | None | Accumulates up to 5 seconds |
| **Frontend Response** | Immediate per chunk | Buffering status + chunk result |
| **Total Comparisons** | Up to 4 | Up to 4 (of 5-second chunks) |

## Implementation Details

### Audio Accumulation Algorithm:

```
1. Receive small chunk (e.g., 1-second)
   └─ Add to buffer list
   └─ Add duration to counter
   
2. Check if buffer >= 5 seconds
   ├─ NO: Send "buffering" response, continue
   └─ YES: Proceed to step 3
   
3. Merge all buffered chunks
   └─ Read each chunk's audio data
   └─ Convert to numpy arrays (handle mono/stereo)
   └─ Concatenate all arrays
   └─ Write back to WAV bytes
   
4. Generate embedding from merged audio
   └─ Single embedding for ~5 seconds of audio
   
5. Compare with stored embedding
   └─ Calculate cosine similarity
   └─ Check against threshold (0.75)
   
6. Clear buffer for next round
   └─ Empty audio_buffer list
   └─ Reset buffer_duration_seconds to 0
   
7. Check completion criteria
   ├─ If match: Return "verified"
   ├─ If max chunks reached: Return "unverified"
   └─ Otherwise: Continue to next buffer
```

## Verification Flow Example

**Timeline (assuming chunks arrive every 1 second):**

```
Time  Buffer Duration  Action                              Response
----  ---------------  ------                              --------
1s    1.0s            Add chunk 1 to buffer              Buffering (1.0/5.0)
2s    2.0s            Add chunk 2 to buffer              Buffering (2.0/5.0)
3s    3.0s            Add chunk 3 to buffer              Buffering (3.0/5.0)
4s    4.0s            Add chunk 4 to buffer              Buffering (4.0/5.0)
5s    5.0s            Add chunk 5 to buffer              → Process chunk 1
                      Merge, embed, compare               Chunk 1/4, similarity: 0.82
                      Clear buffer                       
6s    1.0s            Add chunk 6 to buffer              Buffering (1.0/5.0)
7s    2.0s            Add chunk 7 to buffer              Buffering (2.0/5.0)
8s    3.0s            Add chunk 8 to buffer              Buffering (3.0/5.0)
9s    4.0s            Add chunk 9 to buffer              Buffering (4.0/5.0)
10s   5.0s            Add chunk 10 to buffer             → Process chunk 2
                      Merge, embed, compare               Chunk 2/4, similarity: 0.88
                      Clear buffer, final_status=verified ✓ VERIFIED
```

## Threshold Logic (Unchanged)

- **Threshold:** 0.75 (default)
- **Match Condition:** `similarity_score >= threshold`
- **Verification Complete:** On first chunk match OR after 4 chunks
- **Result:** "verified" (threshold met) or "unverified" (4 chunks exhausted)

## Frontend Impact

Frontend clients need to handle the new "buffering" message type:

```javascript
websocket.onmessage = (event) => {
  const response = JSON.parse(event.data);
  
  if (response.type === "buffering") {
    // Show buffer progress
    console.log(`Buffering: ${response.buffer_duration}/${response.target_duration}s`);
    // Update UI with progress bar
  } 
  else if (response.type === "chunk_result") {
    // Show verification result for this 5-second chunk
    console.log(`Chunk ${response.chunk_number}: ${response.similarity_score}`);
    
    if (response.final_status) {
      // Verification complete
      console.log(`Result: ${response.final_status}`);
    }
  }
};
```

## Testing Recommendations

1. **Buffering Accumulation Test:**
   - Send audio in 1-second chunks
   - Verify "buffering" responses count up to 5 seconds
   - Verify chunk processing occurs at 5-second mark

2. **5-Second Chunk Processing:**
   - Send 5 seconds of audio continuously
   - Verify single chunk result is returned
   - Check embedding generation occurs once

3. **Multiple Chunks:**
   - Send 20+ seconds total
   - Verify 4 chunks are processed maximum
   - Verify final_status is set after 4 chunks

4. **Early Verification:**
   - Send audio that matches threshold at chunk 2
   - Verify verification completes immediately
   - Verify connection closes after "verified" result

5. **No Match:**
   - Send audio that never matches threshold
   - Verify exactly 4 chunks are processed
   - Verify "unverified" status after chunk 4

## Files Modified

1. `backend/verification_streaming_service.py`
   - Updated `StreamingVerificationSession` dataclass with buffer fields
   - Modified `process_chunk()` method with buffering logic
   - Added `_merge_audio_chunks()` helper method

2. `backend/main.py`
   - Updated WebSocket audio chunk handling to process buffering responses
   - Modified docstring for `websocket_verify_endpoint()`
   - Added buffering response in the message loop

## Backward Compatibility

- **No external API changes:** Client sends same "audio" messages
- **Response format change:** Clients now receive "buffering" messages in addition to "chunk_result"
- **Threshold logic unchanged:** Same 0.75 default threshold
- **Max chunks unchanged:** Still processes maximum 4 chunks

## Performance Implications

- **Reduced embedding generations:** 1 per 5 seconds (vs. 1 per 1 second)
- **5x fewer model calls:** Significant GPU/CPU improvement if using ECAPA-TDNN
- **Increased latency:** First result delayed until 5 seconds of audio
- **Improved accuracy:** More audio context per embedding comparison
