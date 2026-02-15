# Audio Chunking Implementation - Current vs Required

## 1. ENROLLMENT MODE ANALYSIS

### Current Implementation (BROKEN)

**File:** `EnrollmentPageWebSocket.jsx`

```javascript
// DEFINED BUT NOT USED
const SAMPLE_RATE = 16000;
const CHUNK_SIZE_SAMPLES = 16000; // 1 second
const OVERLAP_RATIO = 0.2;
const OVERLAP_SAMPLES = Math.floor(CHUNK_SIZE_SAMPLES * OVERLAP_RATIO); // 3200

// NEVER USED - Just for display calculation
function calculateChunkCount(durationSeconds) {
  // ... calculates expected chunks from duration
  // But audio is NOT actually chunked during recording!
}

// PROBLEM: Uses continuous audio recorder
const handleRecord = async () => {
  if (isRecording) {
    const blob = await recorderRef.current.stop();
    if (blob) {
      setAudioChunks((prev) => [...prev, blob]);  // ❌ Full blob, not 1-second chunks!
      await enrollment.submitChunk(blob, audioChunks.length);
    }
  }
}
```

### Result When User Records 3 Seconds
```
INPUT:   3 seconds of continuous audio
CHUNKS SENT TO BACKEND: 1 blob (all 3 seconds)
BACKEND RECEIVES: { session_id, audio_data: <all 3 seconds> }
BACKEND DOES: Chunks it into 3 pieces (1s each)
FRONTEND DOES: Nothing, just sends one blob!
STATUS: ❌ BROKEN - Frontend not chunking
```

---

### What SHOULD Happen (Using audioChunkingService.js)

```javascript
import AudioChunkingService, { AUDIO_CONFIG } from '../services/audioChunkingService';

const handleRecord = async () => {
  if (isRecording) {
    // ✅ CORRECT: Create service with enrollment mode
    const chunker = new AudioChunkingService({
      mode: 'enrollment',  // Sets chunk size to 16000 samples (1 second)
      sampleRate: AUDIO_CONFIG.SAMPLE_RATE,
      onChunkReady: async (chunkInfo) => {
        // ✅ This fires every 1 second with 16,000 samples
        console.log(`Chunk ${chunkInfo.chunkNumber}: ${chunkInfo.sampleCount} samples`);
        await enrollment.submitAudioChunk(chunkInfo.samples, chunkInfo.chunkNumber);
      }
    });

    // Start chunking...
    await chunker.initialize();
    chunker.startRecording();
    
    // When user stops:
    chunker.stopRecording(); // Emits final partial chunk if needed
  }
}
```

### Result When User Records 3 Seconds (CORRECT)
```
INPUT:   3 seconds of continuous audio
CHUNKS SENT TO BACKEND:
  - Chunk 1: 1-second audio (16,000 samples) at t=0s
  - Chunk 2: 1-second audio (16,000 samples) at t=0.8s  (20% overlap)
  - Chunk 3: 1-second audio (16,000 samples) at t=1.6s  (20% overlap)
  - Chunk 4: 1-second audio (16,000 samples) at t=2.4s  (20% overlap)
FRONTEND SENDS: 4 messages, each with 16,000 samples
BACKEND RECEIVES: 4 separate chunks
BACKEND DOES: Generate embedding for each chunk
FRONTEND DOES: Proper chunking ✅
STATUS: ✅ CORRECT
```

---

## 2. VERIFICATION MODE ANALYSIS

### Current Implementation (BROKEN)

**File:** `VerificationPageWebSocket.jsx`

```javascript
// PROBLEM: No mode-specific chunking at all!
const handleRecord = async () => {
  if (isRecording) {
    if (recorderRef.current) {
      const blob = await recorderRef.current.stop();
      if (blob) {
        const duration = await calculateDuration(blob);
        if (duration >= 2) {
          // ❌ Sends ENTIRE recording, doesn't chunk for 5-second segments
          await verification.submitAudio(blob, false);
        }
      }
    }
  }
}
```

### Result When User Records 12 Seconds
```
INPUT:   12 seconds of continuous audio
CHUNKS SENT TO BACKEND: 1 blob (all 12 seconds)
BACKEND RECEIVES: { session_id, audio_data: <all 12 seconds> }
BACKEND DOES: Chunks it into 5-second pieces
FRONTEND DOES: Nothing, just sends one blob!
STATUS: ❌ BROKEN - No 5-second chunking
```

---

### What SHOULD Happen (With Proper Implementation)

```javascript
import AudioChunkingService, { AUDIO_CONFIG } from '../services/audioChunkingService';

const handleRecord = async () => {
  if (isRecording) {
    // ✅ CORRECT: Create service with verification mode
    const chunker = new AudioChunkingService({
      mode: 'verification',  // Sets chunk size to 80000 samples (5 seconds)
      sampleRate: AUDIO_CONFIG.SAMPLE_RATE,
      onChunkReady: async (chunkInfo) => {
        // ✅ This fires every 5 seconds with 80,000 samples
        console.log(`Chunk ${chunkInfo.chunkNumber}: ${chunkInfo.sampleCount} samples (5s)`);
        await verification.submitAudioChunk(chunkInfo.samples, chunkInfo.chunkNumber);
      }
    });

    await chunker.initialize();
    chunker.startRecording();
    
    // When user stops after 12 seconds:
    chunker.stopRecording(); // Emits remaining ~2 seconds as partial chunk
  }
}
```

### Result When User Records 12 Seconds (CORRECT)
```
INPUT:   12 seconds of continuous audio
CHUNKS SENT TO BACKEND:
  - Chunk 1: 5-second audio (80,000 samples) at t=0s
  - Chunk 2: 5-second audio (80,000 samples) at t=4s   (20% overlap)
  - Chunk 3: 5-second audio (80,000 samples) at t=8s   (20% overlap)
  - Chunk 4: ~2-second audio (32,000 samples)         (remaining)
FRONTEND SENDS: 4 messages, with proper chunk sizes
BACKEND RECEIVES: 4 separate chunks
BACKEND DOES: Generate embedding for each chunk
FRONTEND DOES: Proper chunking ✅
STATUS: ✅ CORRECT
```

---

## 3. CODE COMPARISON TABLE

| Aspect | Current (Broken) | Should Be (Correct) |
|--------|-----------------|-------------------|
| **Enrollment Chunking** | None (sends full blob) | 1-second chunks (16,000 samples) |
| **Verification Chunking** | None (sends full blob) | 5-second chunks (80,000 samples) |
| **Mode Awareness** | ❌ No | ✅ Yes (EnrollmentPageWebSocket uses 'enrollment', VerificationPageWebSocket uses 'verification') |
| **Service Used** | `createAudioRecorder()` (streaming utility) | `AudioChunkingService` (chunking utility) |
| **Chunk Events** | ❌ Not emitted | ✅ Should emit on reaching chunk size |
| **Backend Integration** | Backend chunks (inefficient) | Frontend chunks (correct) |
| **Overlap Support** | ❌ No | ✅ Yes (20% overlap = 3,200 samples for enrollment) |

---

## 4. SERVICE COMPARISON

### audioRecorder.js (Current Usage)
```
PURPOSE: WebSocket streaming of continuous audio
BEHAVIOR: 
  - Records in 4096-sample buffers
  - Streams to WS when reaching ~1 second
  - Returns SINGLE merged WAV blob on stop()

USE CASE: Real-time audio transmission
PROBLEM: Returns merged blob, defeating chunking!
```

### audioChunkingService.js (Should Be Used)
```
PURPOSE: Chunk audio into discrete time windows
BEHAVIOR:
  - Records in 4096-sample buffers
  - EMITS chunks when reaching required size
  - Supports enrollment (1s) and verification (5s) modes
  - Includes overlap calculation

USE CASE: Discrete chunk-based processing
BENEFIT: Sends chunks incrementally, not full blob!
```

---

## 5. ACTUAL DATA FLOW

### Current (Broken) Flow

```
Recording Started
       ↓
[Accumulate 48kHz audio samples in ScriptProcessor]
       ↓
[Merge to single audio blob on stop]
       ↓
[Downsample to 16kHz]
       ↓
[Convert to WAV]
       ↓
[Send to Backend: { data: <full 48-second WAV> }]
       ↓
Backend Chunks → Extracts 1s or 5s chunks
       ↓
Backend Generates Embeddings
```

**Issue:** Frontend has opportunity to chunk at ~10ms intervals but doesn't!

---

### Correct Flow

```
Recording Started (Mode: enrollment)
       ↓
[Accumulate samples in buffer]
       ↓
[Every 16,000 samples (~1 second)] → EMIT EVENT
       ↓
[Frontend handles CHUNK_READY event]
       ↓
[Convert chunk to PCM16, send to Backend]
       ↓
Backend Receives Chunk → Generates Embedding
       ↓
[Repeat for next chunk]
```

**Benefit:** Frontend sends chunks as they're ready, backend processes immediately!

---

## 6. Key Numbers

### Enrollment Mode
- **Chunk Duration:** 1 second
- **Samples per Chunk:** 16,000 samples
- **Sample Rate:** 16,000 Hz (16 kHz)
- **Calculation:** 1 second × 16,000 samples/second = 16,000 samples
- **Buffer Size:** 4,096 bytes (16-bit PCM) × 16,000 = 32,000 bytes per chunk
- **Expected Chunks:** 1 second of audio → 1 chunk
  - 3 seconds of audio → 3 chunks (with 20% overlap, ~4 chunks)
  - 10 seconds of audio → ~10 chunks

### Verification Mode
- **Chunk Duration:** 5 seconds
- **Samples per Chunk:** 80,000 samples
- **Sample Rate:** 16,000 Hz (16 kHz)
- **Calculation:** 5 seconds × 16,000 samples/second = 80,000 samples
- **Buffer Size:** 4,096 bytes (16-bit PCM) × 80,000 = 160,000 bytes per chunk
- **Expected Chunks:** 
  - 10 seconds of audio → 2 chunks
  - 15 seconds of audio → 3 chunks
  - 20 seconds of audio → 4 chunks

---

## 7. Files That Need Modification

### Immediate Fixes Required

1. **`EnrollmentPageWebSocket.jsx`** ⚠️ HIGH PRIORITY
   - Lines 8: Remove `createAudioRecorder` import
   - Add `AudioChunkingService` import
   - Replace `handleRecord()` logic (lines 84-116)
   - Replace recording mechanism entirely

2. **`VerificationPageWebSocket.jsx`** ⚠️ HIGH PRIORITY
   - Add `AudioChunkingService` import
   - Add mode='verification' initialization
   - Modify `handleRecord()` to use chunking (lines 40-65)

3. **`enrollmentWebSocketService.js`** ⚠️ MEDIUM PRIORITY
   - Check if `submitChunk()` can handle multiple calls
   - May need to support `submitAudioChunk()` method

4. **`verificationWebSocketService.js`** ⚠️ MEDIUM PRIORITY
   - Check if `submitAudio()` needs modification for chunks
   - May need to add chunk handling

---

## Summary

| Status | Component | Issue |
|--------|-----------|-------|
| ❌ CRITICAL | EnrollmentPageWebSocket | Not using audioChunkingService, sends full blob |
| ❌ CRITICAL | VerificationPageWebSocket | Not using audioChunkingService, no 5s chunking |
| ✅ WORKING | Backend enrollment_service.py | Properly chunks 1-second audio |
| ✅ WORKING | Backend verification_service.py | Properly chunks 5-second audio |
| ⚠️ UNUSED | audioChunkingService.js | Service exists but never instantiated |
| ⚠️ PARTIAL | audioRecorder.js | Designed for streaming, not chunking |

