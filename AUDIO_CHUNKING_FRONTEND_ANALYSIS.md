# Audio Chunking Frontend Analysis Report

**Date:** February 15, 2026  
**Status:** ⚠️ **CRITICAL ISSUE - INCOMPLETE IMPLEMENTATION**

---

## Executive Summary

The React frontend has audio chunking logic defined in the codebase, but **it is NOT properly integrated** into the enrollment and verification components. The components are not actually chunking audio according to the required specifications:

- **Enrollment Mode:** Should split into 1-second chunks (16,000 samples @ 16kHz) ❌
- **Verification Mode:** Should split into 5-second chunks (80,000 samples @ 16kHz) ❌

---

## Current Implementation Status

### ✅ What EXISTS (Correctly Implemented)

#### 1. **Backend Audio Chunking** (WORKING)
- **Enrollment Service** (`backend/enrollment_service.py`):
  - Uses 1-second chunks (16,000 samples at 16kHz)
  - Properly generates embeddings with chunk_size_seconds=1.0

- **Verification Service** (`backend/verification_service.py`):
  - Uses 5-second chunks (80,000 samples at 16kHz)  
  - Properly generates embeddings with chunk_size_seconds=5.0

#### 2. **Frontend Audio Chunking Service** (DEFINED BUT NOT USED)
- **File:** `frontend/src/services/audioChunkingService.js`
- **Capabilities:**
  ```javascript
  AUDIO_CONFIG = {
    SAMPLE_RATE: 16000,
    ENROLLMENT_CHUNK_DURATION_MS: 1000,     // 1 second ✓
    VERIFICATION_CHUNK_DURATION_MS: 5000,   // 5 seconds ✓
    ENROLLMENT_CHUNK_SAMPLES: 16000,        // 1 second at 16kHz ✓
    VERIFICATION_CHUNK_SAMPLES: 80000,      // 5 seconds at 16kHz ✓
    BUFFER_SIZE: 4096,
  }
  ```
- **Features:**
  - Mode switching: `setMode('enrollment')` or `setMode('verification')`
  - Automatic chunk emission on reaching chunk size
  - Event emitter pattern with callbacks
  - Statistics tracking

---

### ❌ What's BROKEN (Integration Issues)

#### 1. **EnrollmentPageWebSocket.jsx** - MISUSING AUDIO RECORDER

**Current Code (Lines 1-100):**
```javascript
const SAMPLE_RATE = 16000;
const CHUNK_SIZE_SAMPLES = 16000; // 1 second ← DEFINED BUT NOT USED!
// ... other constants ...

// Uses createAudioRecorder() instead of audioChunkingService
const recorderRef = useRef(null);
// ...
recorderRef.current = createAudioRecorder();
```

**Problems:**
1. ✗ Defines `CHUNK_SIZE_SAMPLES` but never uses it
2. ✗ Uses `createAudioRecorder()` which records continuous audio as a single blob
3. ✗ The `calculateChunkCount()` function (lines 17-43) calculates chunks AFTER recording, not during recording
4. ✗ Sends entire recording as one blob via `enrollment.submitChunk(blob, audioChunks.length)`
5. ✗ Only the backend receives the full audio and chunks it (backend does the work, not frontend)

**Line 88 Analysis:**
```javascript
const blob = await recorderRef.current.stop();
if (blob) {
  setAudioChunks((prev) => [...prev, blob]);
  await enrollment.submitChunk(blob, audioChunks.length); // ← Sends ENTIRE blob!
}
```

---

#### 2. **VerificationPageWebSocket.jsx** - NO CHUNKING AT ALL

**Current Code (Lines 40-60):**
```javascript
const handleRecord = async () => {
  if (isRecording) {
    if (recorderRef.current) {
      const blob = await recorderRef.current.stop();
      if (blob) {
        const duration = await calculateDuration(blob);
        if (duration >= 2) {
          await verification.submitAudio(blob, false); // ← Sends ENTIRE blob!
        }
      }
    }
  }
  // ...
}
```

**Problems:**
1. ✗ No mode-specific chunking whatsoever
2. ✗ Doesn't use `audioChunkingService.js` at all
3. ✗ Sends entire recording as one blob with `submitAudio(blob, false)`
4. ✗ No 5-second chunk splitting for verification mode

---

#### 3. **audioRecorder.js** - DESIGNED FOR STREAMING, NOT CHUNKING

**Current Implementation:**
```javascript
const STREAM_CHUNK_SIZE = 4096;           // Small buffer for streaming
const STREAM_BUFFER_THRESHOLD = 16000;    // Stream ~1 second chunks

// Streams via WebSocket but final blob is continuous
const stop = async () => {
  // Merges ALL recorded chunks into single audio
  const totalLength = recordedChunks.reduce((acc, chunk) => acc + chunk.length, 0);
  const mergedAudio = new Float32Array(totalLength);
  // ...
  const wavBlob = encodeWAV(downsampledAudio, TARGET_SAMPLE_RATE);
  return wavBlob; // ← Returns SINGLE blob
}
```

**Issues:**
1. ✗ Designed for WebSocket streaming, not for discrete chunk generation
2. ✗ Returns merged audio as single WAV blob, defeating chunking purpose
3. ✗ Frontend has no control over chunk boundaries

---

## Data Flow Comparison

### ❌ CURRENT FLOW (Broken)
```
Frontend Recording → Full Audio Blob → Backend → Backend Chunks Audio → Generate Embeddings
```

### ✅ CORRECT FLOW (Should Be)
```
Frontend Recording → Frontend Chunks Audio (1s or 5s) → Multiple Chunk Messages → Backend Processes Each Chunk → Generate Embeddings Per Chunk
```

---

## Verification of Requirements

| Requirement | Enrollment | Verification | Status |
|-------------|-----------|--------------|--------|
| **1-second chunks in enrollment** | 16,000 samples @ 16kHz | N/A | ❌ NOT IMPLEMENTED |
| **5-second chunks in verification** | N/A | 80,000 samples @ 16kHz | ❌ NOT IMPLEMENTED |
| **Backend supports chunks** | ✅ Yes | ✅ Yes | ✅ WORKING |
| **Frontend service exists** | ✅ Yes | ✅ Yes | ✅ EXISTS |
| **Frontend components use service** | ❌ No | ❌ No | ❌ BROKEN |

---

## Code Files Needing Fixes

### Priority 1: Critical (Must Fix)
1. **`frontend/src/components/EnrollmentPageWebSocket.jsx`**
   - Replace `createAudioRecorder()` with `AudioChunkingService`
   - Set mode to 'enrollment'
   - Listen to chunk events and send each chunk separately

2. **`frontend/src/components/VerificationPageWebSocket.jsx`**
   - Add `AudioChunkingService` integration
   - Set mode to 'verification'
   - Handle 5-second chunk events

### Priority 2: Important (Should Check)
3. **`frontend/src/services/enrollmentWebSocketService.js`**
   - Verify it can handle multiple chunks or if it's designed for single chunk

4. **`frontend/src/services/verificationWebSocketService.js`**
   - Check if it supports chunk-based audio or expects single audio blob

---

## Specific Implementation Issues Found

### Issue 1: EnrollmentPageWebSocket Chunk Calculation Misuse
**Location:** Lines 17-43
```javascript
function calculateChunkCount(durationSeconds) {
  // ... calculates expected chunks from FULL recording duration
  // But this is just for DISPLAY, not actual chunking!
}
```
**Impact:** This function misleads developers into thinking chunks are created, but they're not.

### Issue 2: Records Full Audio Instead of Chunking
**Location:** Lines 87-96
```javascript
const blob = await recorderRef.current.stop();
if (blob) {
  setAudioChunks((prev) => [...prev, blob]); // Full blob, not 1s chunks!
  await enrollment.submitChunk(blob, audioChunks.length);
}
```
**Impact:** Entire recording sent as one blob, defeating chunking purpose.

### Issue 3: No Mode-Specific Chunking in Verification
**Location:** `VerificationPageWebSocket.jsx` Lines 40-65
```javascript
const blob = await recorderRef.current.stop();
if (blob) {
  const duration = await calculateDuration(blob);
  if (duration >= 2) {
    await verification.submitAudio(blob, false); // No 5-second chunking!
  }
}
```
**Impact:** Verification mode never chunks 5-second audio segments.

---

## Recommendations

### Immediate Action Required
1. **Integrate AudioChunkingService into EnrollmentPageWebSocket.jsx**
   - Remove `createAudioRecorder()` usage
   - Use `AudioChunkingService` with mode='enrollment'
   - Listen to `CHUNK_READY` events
   - Send each chunk via `enrollment.submitAudioChunk()`

2. **Integrate AudioChunkingService into VerificationPageWebSocket.jsx**
   - Add `AudioChunkingService` with mode='verification'
   - Handle 5-second chunk events
   - Modify verification service to accept chunks

3. **Test the Integration**
   - Record 10 seconds of audio in enrollment mode
   - Verify exactly 10-11 chunks are generated (with overlap calculation)
   - Record 10 seconds in verification mode
   - Verify 2-3 chunks are generated

### API Changes Needed
- **EnrollmentWebSocketService:** May need new method `submitAudioChunk()` that handles proper chunk messages
- **VerificationWebSocketService:** May need to support chunk-based submission

---

## Testing Checklist

- [ ] Enrollment: Record 3 seconds → Should emit 3 chunks (1s each)
- [ ] Enrollment: Record 1.5 seconds → Should emit 2 chunks (with overlap)
- [ ] Verification: Record 12 seconds → Should emit 2-3 chunks (5s each)
- [ ] Backend receives correct chunk messages with chunk indices
- [ ] Embeddings generated per chunk (not for full audio)
- [ ] Chunk metadata (timestamps, sample counts) correct

---

## Conclusion

**The audio chunking infrastructure exists in the frontend but is completely disconnected from the UI components.** The enrollment and verification pages are recording audio but NOT chunking it according to specifications before sending to the backend. This defeats the purpose of the chunking design and forces the backend to do all the work.

**Action Required:** Connect the components to use `AudioChunkingService` properly.

