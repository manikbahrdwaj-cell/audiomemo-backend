# Audio Chunking Architecture Diagrams

## Current Architecture (BROKEN)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENROLLMENT MODE                               │
│                     (BROKEN STATE)                               │
└─────────────────────────────────────────────────────────────────┘

Frontend UI Layer
┌────────────────────────────────────────────────────────────────┐
│ EnrollmentPageWebSocket.jsx                                    │
│                                                                │
│ const CHUNK_SIZE_SAMPLES = 16000  ← Defined but unused       │
│ const blob = recorderRef.current.stop()  ← Gets full blob     │
│ await enrollment.submitChunk(blob, index)  ← Sends full blob  │
└─────────────────┬──────────────────────────────────────────────┘
                  │
                  ↓ (WRONG: Full audio blob)
                  │
Service Layer
┌────────────────────────────────────────────────────────────────┐
│ createAudioRecorder():                                         │
│   • Records continuous audio                                  │
│   • Streams to WebSocket (~1s buffers)                        │
│   • Merges on stop()                                          │
│   • Returns SINGLE WAV blob                                   │
│                                                                │
│ enrollmentWebSocketService.submitChunk(blob):                 │
│   • Sends entire blob to backend                              │
│   • No chunk boundary control                                 │
└─────────────────┬──────────────────────────────────────────────┘
                  │
                  ↓ (Message: audio_data = full audio)
                  │
WebSocket / Network
┌────────────────────────────────────────────────────────────────┐
│ MESSAGE: {                                                     │
│   type: 'audio',                                              │
│   action: 'submit_chunk',                                     │
│   audio_data: <base64 encoded 10-second WAV>  ← ENTIRE FILE  │
│ }                                                              │
└─────────────────┬──────────────────────────────────────────────┘
                  │
                  ↓ (Receives: 1 file with all audio)
                  │
Backend Service Layer
┌────────────────────────────────────────────────────────────────┐
│ websocket_audio_chunk_handler.py:                              │
│   • Receives blob                                              │
│   • Extracts audio data                                        │
│   • Passes to backend service                                 │
│                                                                │
│ enrollment_service.py:                                        │
│   • Receives: full 10-second audio                            │
│   • CHUNKS it: into ~10 x (1-second) pieces  ← NOT FOUND!     │
│   • Generates embedding per chunk                             │
│                                                                │
│ audio_chunking.py:                                            │
│   • ChunkConfig: chunk_size=16000 ✓                           │
│   • AudioChunker: splits full audio into chunks               │
│   • Generates overlapping chunks (20% overlap)                │
└────────────────────────────────────────────────────────────────┘

PROBLEM: Frontend sends 1 blob → Backend chunks it
         Should be: Frontend chunks it → Backend uses chunks
```

---

## Correct Architecture (SHOULD BE)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENROLLMENT MODE                               │
│                   (CORRECT STATE)                                │
└─────────────────────────────────────────────────────────────────┘

Frontend UI Layer
┌────────────────────────────────────────────────────────────────┐
│ EnrollmentPageWebSocket.jsx                                    │
│                                                                │
│ const chunker = new AudioChunkingService({                     │
│   mode: 'enrollment',                                          │
│   onChunkReady: (chunk) => {                                   │
│     sendChunkToBackend(chunk)  ← Send each chunk               │
│   }                                                            │
│ })                                                             │
│                                                                │
│ await chunker.startRecording()                                 │
│ // Emits CHUNK_READY every 1 second                           │
└─────────────────┬──────────────────────────────────────────────┘
                  │
                  ├─ Chunk 1 (1s): 16,000 samples
                  ├─ Chunk 2 (1s): 16,000 samples (overlapped)
                  ├─ Chunk 3 (1s): 16,000 samples (overlapped)
                  ├─ Chunk 4 (1s): 16,000 samples (overlapped)
                  ├─ ... (continues)
                  │
Service Layer
┌────────────────────────────────────────────────────────────────┐
│ AudioChunkingService:                                          │
│   • Mode: 'enrollment'                                         │
│   • Chunk size: ENROLLMENT_CHUNK_SAMPLES (16,000)            │
│   • Emits: CHUNK_READY event (every 1 second)                │
│   • Provides: onChunkReady callback per chunk                 │
│                                                                │
│ enrollmentWebSocketService.submitAudioChunk(chunk):            │
│   • Called for EACH chunk separately                           │
│   • Sends chunk message to backend                             │
└─────────────────┬──────────────────────────────────────────────┘
                  │
                  ├─ (Message 1: Chunk 1)
                  ├─ (Message 2: Chunk 2)  
                  ├─ (Message 3: Chunk 3)
                  ├─ (Message 4: Chunk 4)
                  ├─ ... (continues)
                  │
WebSocket / Network (STREAMING)
┌────────────────────────────────────────────────────────────────┐
│ MESSAGE 1: {                                                   │
│   action: 'submit_chunk',                                      │
│   chunk_number: 1,                                             │
│   audio_data: <base64 encoded 1-second chunk>  ← 16k samples  │
│ }                                                              │
│                                                                │
│ MESSAGE 2: {                                                   │
│   action: 'submit_chunk',                                      │
│   chunk_number: 2,                                             │
│   audio_data: <base64 encoded 1-second chunk>  ← 16k samples  │
│ } ... (more messages)                                          │
└─────────────────┬──────────────────────────────────────────────┘
                  │
                  ├─ (Receives: Chunk 1)
                  ├─ (Receives: Chunk 2)
                  ├─ (Receives: Chunk 3)
                  ├─ ... (continues)
                  │
Backend Service Layer (STREAMING PROCESSING)
┌────────────────────────────────────────────────────────────────┐
│ websocket_audio_chunk_handler.py:                              │
│   • Receives chunk 1 → Process immediately                     │
│   • Receives chunk 2 → Process immediately                     │
│   • Received chunk 3 → Process immediately                     │
│                                                                │
│ enrollment_service.py (per chunk):                             │
│   • Receives: 1-second chunk (16,000 samples)                 │
│   • Generates embedding immediately                           │
│   • No re-chunking needed                                      │
│                                                                │
│ BENEFITS:                                                      │
│   • Real-time feedback                                         │
│   • No late processing                                         │
│   • Cleaner architecture                                       │
└────────────────────────────────────────────────────────────────┘

BENEFIT: Frontend chunks it → Backend uses chunks immediately
         Real-time streaming, not batch processing
```

---

## Verification Mode Comparison

### Current (BROKEN)
```
User Records 15s
         ↓
VerificationPageWebSocket
         ↓
createAudioRecorder()
         ↓
Returns: 1 x (15-second blob)
         ↓
verification.submitAudio(blob, false)
         ↓
Backend: Chunks into 3 x (5-second)  ← inefficient
```

### Correct (SHOULD BE)
```
User Records 15s
         ↓
VerificationPageWebSocket
         ↓
AudioChunkingService (mode='verification')
         ↓
Emits after 5s:  Chunk 1 (80,000 samples)
         ↓
Emits after 10s: Chunk 2 (80,000 samples)
         ↓
Emits after 15s: Chunk 3 (partial, ~80,000 samples)
         ↓
Backend: Uses 3 chunks immediately  ← efficient
```

---

## Service Component Diagram

### Current (Not Using audioChunkingService)

```
┌──────────────────────────────┐
│  EnrollmentPageWebSocket.jsx │
└──────────────┬───────────────┘
               │
               ├─→ createAudioRecorder()  ← Uses streaming service
               │
               ├─→ calculateDuration()
               │
               └─→ enrollment.submitChunk()

┌──────────────────────────────────────┐
│ audioChunkingService.js              │
│ (Completely Unused)                  │
│                                      │
│ ✓ ENROLLMENT_CHUNK_SAMPLES: 16000    │
│ ✓ VERIFICATION_CHUNK_SAMPLES: 80000  │
│ ✓ CHUNK_READY event                  │
│ ✓ Mode switching                     │
│                                      │
│ STATUS: NOT IMPORTED ANYWHERE        │
└──────────────────────────────────────┘
```

### Correct (Should Use audioChunkingService)

```
┌──────────────────────────────┐
│  EnrollmentPageWebSocket.jsx │
└──────────────┬───────────────┘
               │
               ├─→ AudioChunkingService  ← Uses chunking service
               │   (mode: 'enrollment')
               │
               ├─→ CHUNK_READY event
               │   (every 1 second)
               │
               └─→ enrollment.submitAudioChunk()
                   (called per chunk)

┌──────────────────────────────────────┐
│ audioChunkingService.js              │
│ (Should Be Used)                     │
│                                      │
│ ✓ ENROLLMENT_CHUNK_SAMPLES: 16000    │
│ ✓ VERIFICATION_CHUNK_SAMPLES: 80000  │
│ ✓ CHUNK_READY event                  │
│ ✓ Mode switching                     │
│                                      │
│ STATUS: PROPERLY INTEGRATED          │
└──────────────────────────────────────┘
```

---

## Data Flow: Complete Picture

### CURRENT (WRONG)

```
                        FRONTEND
                           
                    Record 10 seconds
                           |
                           v
                   createAudioRecorder()
                           |
          Streams ~1s chunks to WS
          (For streaming purposes)
                           |
                           v
                    Merge to 1 blob
                           |
                    10-second WAV file
                           |
                    ─ ─ ─ ─ ─ ─ ─ ─ ─
                           |
                        NETWORK
                           |
                    ─ ─ ─ ─ ─ ─ ─ ─ ─
                           |
                           v
                        BACKEND
                           |
                   AudioChunker receives
                   one 10-second file
                           |
                   Chunks into 10 x (1s)
                           |
        {Does chunking that frontend should have!}
                           |
                Generates 10 embeddings
                (After receiving full file)
                           
RESULT: Inefficient, late processing, waste of bandwidth
```

### CORRECT (SHOULD BE)

```
                        FRONTEND
                           
                    Record 10 seconds
                           |
                           v
                   AudioChunkingService
                     (mode: enrollment)
                           |
    ┌──────────────────────┼──────────────────────┐
    |                      |                      |
  1sec              +0.8sec stride            +0.8sec
    v                      v                      v
Chunk 1         Chunk 2 (overlap)         Chunk 3 (overlap)
16k samples     16k samples               16k samples
    |                      |                      |
    └──────────────┬───────┴──────────────┬──────┘
                   |                      |
                   +─ 10 CHUNK_READY events (streaming)
                   |
              ─ ─ ─ ─ ─ ─ ─ ─ ─
              |
           NETWORK (Real-time)
              |
    ┌─────────┼─────────┬─────────┐
    |         |         |         |
    v         v         v         v
  Chunk1    Chunk2    Chunk3    Chunk4...
    |         |         |         |
    └─────────┼─────────┼─────────┘
              |
           ─ ─ ─ ─ ─ ─ ─ ─ ─
              |
              v
           BACKEND

     {Processes chunks as they arrive!}

   Embedding1  Embedding2  Embedding3...
   (after 1s)  (after 1.8s) (after 2.6s)
   
RESULT: Efficient, real-time processing, streaming feel
```

---

## Mode Selection Flow

### Current (No Mode Logic)

```
EnrollmentPageWebSocket.jsx
    └─ Uses createAudioRecorder()
       └─ No mode parameter
          └─ No awareness of chunking mode
             └─ Sends full blob

VerificationPageWebSocket.jsx
    └─ Uses createAudioRecorder()
       └─ No mode parameter
          └─ No awareness of chunking mode
             └─ Sends full blob
```

### Correct (Mode-Aware)

```
EnrollmentPageWebSocket.jsx
    └─ Uses AudioChunkingService
       └─ mode: 'enrollment'
          └─ chunk size: 16,000 samples (1s)
             └─ Emits every 1 second
                └─ Sends 1-second chunks

VerificationPageWebSocket.jsx
    └─ Uses AudioChunkingService
       └─ mode: 'verification'
          └─ chunk size: 80,000 samples (5s)
             └─ Emits every 5 seconds
                └─ Sends 5-second chunks
```

---

## Summary Table

| Aspect | Current | Correct |
|--------|---------|---------|
| **Frontend Chunks Audio** | ❌ No | ✅ Yes |
| **Service Used** | createAudioRecorder() | AudioChunkingService |
| **Mode Awareness** | ❌ None | ✅ enrollment/verify |
| **Chunk Size Control** | ❌ None (full blob) | ✅ 1s or 5s |
| **Chunk Emission** | ❌ No events | ✅ CHUNK_READY events |
| **Backend Workload** | Too much (chunks full) | Appropriate (uses chunks) |
| **Real-time Feel** | ❌ No (waits for full) | ✅ Yes (streaming) |
| **Architecture** | Inefficient | Efficient |

---

## Conclusion

The frontend has all the tools needed (audioChunkingService.js) but is using the wrong tool (createAudioRecorder). 

**Fix:** Switch tools and enable proper audio chunking at the frontend level.

