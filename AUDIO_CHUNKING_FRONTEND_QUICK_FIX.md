# Audio Chunking - Quick Fix Guide

## The Problem (In One Sentence)
**The frontend UI components record audio as continuous blobs instead of chunking them into 1-second (enrollment) or 5-second (verification) pieces like they should.**

---

## Evidence

### ❌ What's Happening Now (WRONG)

**EnrollmentPageWebSocket.jsx - Line 88:**
```javascript
const blob = await recorderRef.current.stop();
// User records 10 seconds → Gets 1 blob containing ALL 10 seconds
// Sends to backend: { audio_data: <10-second WAV file> }
```

**VerificationPageWebSocket.jsx - Line 53:**
```javascript
await verification.submitAudio(blob, false);
// User records 15 seconds → Gets 1 blob containing ALL 15 seconds
// Sends to backend: { audio_data: <15-second WAV file> }
```

---

## Expected Behavior

### ✅ What SHOULD Happen (CORRECT)

**Enrollment Mode (1-second chunks):**
```
Record 10 seconds → Frontend generates events for:
  - Chunk 1 after ~1 second
  - Chunk 2 after ~1.8 seconds (with overlap)
  - Chunk 3 after ~2.6 seconds
  - ... continues for all 10 seconds
  
Each chunk sent separately to backend with message:
{
  session_id: "...",
  chunk_number: 1,
  audio_data: <16,000 samples (1 second)>,
  ...
}
```

**Verification Mode (5-second chunks):**
```
Record 20 seconds → Frontend generates events for:
  - Chunk 1 after ~5 seconds
  - Chunk 2 after ~9 seconds (with overlap)
  - Chunk 3 after ~13 seconds
  - Chunk 4 after ~17 seconds
  
Each chunk sent separately to backend with message:
{
  session_id: "...",
  chunk_number: 1,
  audio_data: <80,000 samples (5 seconds)>,
  ...
}
```

---

## The Solution

### Step 1: Understand the Service

**File:** `frontend/src/services/audioChunkingService.js`

This service ALREADY EXISTS and does exactly what you need:
- ✅ Creates proper chunk events
- ✅ Supports enrollment mode (1-second chunks)
- ✅ Supports verification mode (5-second chunks)
- ✅ Has overlap and stride calculations built in

### Step 2: What Needs to Change

#### IN `EnrollmentPageWebSocket.jsx`:

**REMOVE:**
- Import of `createAudioRecorder`
- Usage of `createAudioRecorder()` in recording

**ADD:**
- Import `AudioChunkingService` and `AUDIO_CONFIG`
- Create service instance with mode='enrollment'
- Listen to chunk ready events
- Send each chunk to backend

#### IN `VerificationPageWebSocket.jsx`:

**REMOVE:**
- Usage of `createAudioRecorder()` directly
- Full blob sending

**ADD:**
- Import `AudioChunkingService` and `AUDIO_CONFIG`
- Create service instance with mode='verification'
- Listen to chunk ready events (5-second chunks)
- Send each chunk to backend

### Step 3: Backend Impact

**NO CHANGES NEEDED:** Backend already supports both modes!
- `enrollment_service.py` - Handles 1-second chunks ✅
- `verification_service.py` - Handles 5-second chunks ✅

---

## Technical Details

### Constants That Are Correct

**In audioChunkingService.js:**
```javascript
AUDIO_CONFIG = {
  SAMPLE_RATE: 16000,
  ENROLLMENT_CHUNK_DURATION_MS: 1000,       // ✅ Correct
  VERIFICATION_CHUNK_DURATION_MS: 5000,     // ✅ Correct
  ENROLLMENT_CHUNK_SAMPLES: 16000,          // ✅ Correct (1s × 16kHz)
  VERIFICATION_CHUNK_SAMPLES: 80000,        // ✅ Correct (5s × 16kHz)
}
```

### Chunk Size Math

**Enrollment:**
- 1 second × 16,000 Hz = 16,000 samples ✅

**Verification:**
- 5 seconds × 16,000 Hz = 80,000 samples ✅

### Overlap Calculation

For both modes (20% overlap):
- **Enrollment:** 
  - Chunk size: 16,000 samples
  - Overlap: 3,200 samples (20%)
  - Stride: 12,800 samples (80%)

- **Verification:**
  - Chunk size: 80,000 samples
  - Overlap: 16,000 samples (20%)
  - Stride: 64,000 samples (80%)

---

## Quick Reference: Code Changes

### Option A: Use Existing audioChunkingService

**Benefits:**
- No new dependencies
- Service already built
- Tested code path

**What to do:**
1. Import `AudioChunkingService` in components
2. Instantiate with correct mode
3. Listen to `CHUNK_READY` events
4. Send chunks to backend

### Option B: Modify UI Component (NOT RECOMMENDED)

This would mean:
- Duplicating chunking logic in components
- Not using the created service
- More error-prone

---

## Verification Steps

After implementing the fix:

### For Enrollment:
1. ✅ Record 3 seconds of audio
2. ✅ Count chunks: Should be ~3-4 chunks (with overlap)
3. ✅ Each chunk: ~16,000 samples
4. ✅ Backend receives separate messages for each chunk
5. ✅ No single 3-second audio message

### For Verification:
1. ✅ Record 12 seconds of audio
2. ✅ Count chunks: Should be 2-3 chunks
3. ✅ Each chunk: ~80,000 samples (except last)
4. ✅ Backend receives separate messages for each chunk
5. ✅ No single 12-second audio message

---

## Files Involved

### Currently Using (WRONG):
- `frontend/src/utils/audioRecorder.js` - Continuous blob recording
- `createAudioRecorder()` function

### Should Be Using (RIGHT):
- `frontend/src/services/audioChunkingService.js` - Proper chunking
- `AudioChunkingService` class

### Backend (NO CHANGES):
- `backend/enrollment_service.py` ✅
- `backend/verification_service.py` ✅
- `backend/websocket_audio_chunk_handler.py` ✅

---

## Why This Matters

### Current Issue:
- Frontend sends ONE 30-second audio file
- Backend chunks it internally
- Inefficient, no real-time feedback

### With Fix:
- Frontend sends chunks as generated (1s after user starts in enrollment, 5s in verification)
- Backend processes chunks immediately
- Better user feedback, cleaner architecture
- Matches designed data flow

---

## Status Summary

| Component | Status | Issue |
|-----------|--------|-------|
| **audioChunkingService.js** | ✅ Ready | None - use this! |
| **EnrollmentPageWebSocket.jsx** | ❌ Broken | Not using audioChunkingService |
| **VerificationPageWebSocket.jsx** | ❌ Broken | Not using audioChunkingService |
| **enrollmentWebSocketService.js** | ⚠️ Verify | May need small changes |
| **verificationWebSocketService.js** | ⚠️ Verify | May need small changes |
| **Backend services** | ✅ Ready | No changes needed |

---

## Conclusion

✅ **The chunking infrastructure exists.**
❌ **The UI components don't use it.**
🔧 **Fix: Connect components to service.**

