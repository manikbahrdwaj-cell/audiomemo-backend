# Multi-Sample Enrollment - System Architecture

## 🏗️ Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │           EnrollmentPage Component                │   │
│  │                                                    │   │
│  │  State: [5 Samples], Phone, Progress, Errors    │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────────────┐    │   │
│  │  │  Phone Input                             │    │   │
│  │  └──────────────────────────────────────────┘    │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────────────┐    │   │
│  │  │  Progress Bar (0/5 → 5/5)               │    │   │
│  │  └──────────────────────────────────────────┘    │   │
│  │                                                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │   │
│  │  │ Sample 1 │ │ Sample 2 │ │ ┌──────────────┐│  │   │
│  │  │ [RED]    │ │ [GREEN]  │ │ │ Sample 5     ││  │   │
│  │  │ Record   │ │ Record   │ │ │ [RED]        ││  │   │
│  │  └──────────┘ │ Play     │ │ │ Record       ││  │   │
│  │               │ Delete   │ │ └──────────────┘│  │   │
│  │               └──────────┘ └──────────────────┘  │   │
│  │                    [5 Sample Cards Grid]         │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────────────┐    │   │
│  │  │  Submit Button                           │    │   │
│  │  │  (Disabled until all 5 recorded)         │    │   │
│  │  └──────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  Component Uses:                                           │
│  - VoiceSampleCard.jsx (×5 instances)                     │
│  - audioRecorder.js (utility)                             │
│  - audioChunkSplitter.js (utility)                        │
│  - ChunkProcessingIndicator.jsx (progress)               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
                     (WebSocket)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Python)                         │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │  WebSocket Handler: /ws/voice                      │   │
│  │                                                    │   │
│  │  ┌─ Audio Chunk Messages (Sample 1-5) ──┐        │   │
│  │  │  {sample_number: 1, chunk_0: data}   │        │   │
│  │  │  {sample_number: 1, chunk_1: data}   │        │   │
│  │  │  {sample_number: 2, chunk_0: data}   │        │   │
│  │  │           ... (repeat for all 5)      │        │   │
│  │  └────────────────────────────────────────┘        │   │
│  │                                                    │   │
│  │  ┌─ Enrollment Message ──────┐                   │   │
│  │  │ {type: enroll,            │                   │   │
│  │  │  sample_count: 5}         │                   │   │
│  │  └───────────────────────────┘                   │   │
│  │                                                    │   │
│  │  Audio Reconstruction:                            │   │
│  │  ├─ Collect chunks for Sample 1 → PCM → WAV     │   │
│  │  ├─ Collect chunks for Sample 2 → PCM → WAV     │   │
│  │  ├─ Collect chunks for Sample 3 → PCM → WAV     │   │
│  │  ├─ Collect chunks for Sample 4 → PCM → WAV     │   │
│  │  └─ Collect chunks for Sample 5 → PCM → WAV     │   │
│  │                                                    │   │
│  │  Audio Processing:                                │   │
│  │  ├─ Merge 5 WAV samples → Single Audio          │   │
│  │  └─ Extract Embedding (ECAPA-TDNN)              │   │
│  │                                                    │   │
│  │  Database Storage:                                │   │
│  │  ├─ Store Enrollment Record                      │   │
│  │  ├─ phone_number: +1-555-0000                    │   │
│  │  ├─ embedding: [0.123, 0.456, ...]              │   │
│  │  ├─ sample_count: 5 ← NEW                        │   │
│  │  └─ metadata: {merged: true, platform: v2}       │   │
│  │                                                    │   │
│  │  Response: {type: enrollment_success,            │   │
│  │             vector_id: uuid,                      │   │
│  │             sample_count: 5}                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  Utilities:                                               │
│  - voice_embedding.py (embedding generation)             │
│  - audio_processor.py (merge & validate)                 │
│  - enrollment_model.py (database model)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
                       (Storage)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Database (MongoDB/SQL)                     │
│                                                             │
│  Collection: voice_enrollments                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ _id: ObjectId()                                    │   │
│  │ phone_number: "+1-555-0000"                        │   │
│  │ embedding: [0.123, 0.456, ...]  ← 512-dim        │   │
│  │ sample_count: 5                   ← NEW (multi)   │   │
│  │ enrollment_date: 2024-02-20                        │   │
│  │ audio_hash: "sha256_hash"                          │   │
│  │ status: "active"                                   │   │
│  │ metadata: {                                        │   │
│  │   multi_sample: true,                             │   │
│  │   samples_used: 5,                                │   │
│  │   merged: true,                                   │   │
│  │   platform: "frontend-v2"                         │   │
│  │ }                                                  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  [Optional] Collection: enrollment_samples               │
│  ┌────────────────────────────────────────────────────┐   │
│  │ phone_number, sample_number, duration, hash       │   │
│  │ (For tracking & quality metrics)                   │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow: Audio Recording to Database

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Recording (User Side)                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User clicks Record → Web Audio API captures at 16kHz      │
│                                                             │
│  Browser Memory:                                           │
│  ╔═════════════════════════════════════════════════════╗   │
│  ║  AudioContext {sampleRate: 16000, channels: 1}     ║   │
│  ║    ↓                                                ║   │
│  ║  ScriptProcessorNode                              ║   │
│  ║    ↓                                                ║   │
│  ║  Float32Array chunks                              ║   │
│  ║    ↓                                                ║   │
│  ║  [Sample 1 blob, Sample 2 blob, ...]              ║   │
│  ╚═════════════════════════════════════════════════════╝   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Encoding (Frontend)                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  For each sample (1-5):                                    │
│    1. Extract blob from state                              │
│    2. Read as DataURL                                      │
│    3. Convert to base64                                    │
│    4. Split into transmission chunks                       │
│                                                             │
│  Encoding Example:                                         │
│  Sample 1 (10 seconds):                                    │
│    ├─ 160,000 PCM samples (16kHz × 10s)                   │
│    ├─ Read as data URL                                    │
│    └─ Split into 8 chunks (base64)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: WebSocket Transmission (Network)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Message Stream:                                           │
│  ┌─ Sample 1 ─┐  ┌─ Sample 2 ─┐  ┌─ Sample 3 ─┐...     │
│  │ Chunk 0    │  │ Chunk 0    │  │ Chunk 0    │        │
│  │ Chunk 1    │  │ Chunk 1    │  │ Chunk 1    │        │
│  │ ... (8)    │  │ ... (7)    │  │ ... (9)    │        │
│  └────────────┘  └────────────┘  └────────────┘        │
│           ↓                                              │
│  ws.send({                                               │
│    type: "audio",                                        │
│    sample_number: 1,    ← Which sample                   │
│    chunk_number: 0,     ← Which chunk                    │
│    total_chunks: 8,     ← Total for this sample          │
│    is_last: false,                                       │
│    data: "A1B2C3..."    ← base64 data                    │
│  })                                                      │
│                                                          │
│  After all samples:                                     │
│  ws.send({                                              │
│    type: "enroll",                                      │
│    phone_number: "+1-555-0000",                        │
│    sample_count: 5      ← NEW                           │
│  })                                                     │
│                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Backend Reception (Server Side)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  WebSocket Handler:                                        │
│  ┌──────────────────────────────────────┐                │
│  │ audio_chunks = {                     │                │
│  │   1: b'' ← accumulate chunks 0-7    │                │
│  │   2: b'' ← accumulate chunks 0-6    │                │
│  │   3: b'' ← accumulate chunks 0-8    │                │
│  │   4: b'' ← accumulate chunks 0-7    │                │
│  │   5: b'' ← accumulate chunks 0-9    │                │
│  │ }                                    │                │
│  └──────────────────────────────────────┘                │
│                                                            │
│  Each WebSocket message appends to correct sample        │
│                                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: PCM to WAV Conversion                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  For each sample (1-5):                                    │
│                                                             │
│  Raw PCM bytes                                             │
│       ↓                                                     │
│  Add WAV header                                            │
│  (RIFF metadata: sample rate, channels, etc.)             │
│       ↓                                                     │
│  Valid WAV file                                            │
│       ↓                                                     │
│  Output: [sample_1.wav, sample_2.wav, ..., sample_5.wav]  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Audio Processing                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Option A: Merge Approach                                 │
│  ──────────────────────────                               │
│  sample_1.wav (5s)                                        │
│  sample_2.wav (4s)     ──→  Concatenate  ──→  processed_audio.wav
│  sample_3.wav (4.5s)                        (17.5s total)│
│  sample_4.wav (3s)                                        │
│  sample_5.wav (4s)                                        │
│                                                             │
│  Option B: Average Approach                              │
│  ────────────────────────                                │
│  sample_1.wav  ──→  Extract Embedding 1  ──→             │
│  sample_2.wav  ──→  Extract Embedding 2  ──→  Average  →│
│  sample_3.wav  ──→  Extract Embedding 3  ──→             │
│  sample_4.wav  ──→  Extract Embedding 4  ──→             │
│  sample_5.wav  ──→  Extract Embedding 5  ──→  Final Emb │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Embedding Generation (ECAPA-TDNN)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: processed_audio.wav (merged or chosen method)      │
│                                                             │
│  ECAPA-TDNN Model:                                         │
│  ┌─ Frame-level features ─┐                              │
│  │ (mel-spectrogram)       │                              │
│  │        ↓                │                              │
│  │ SE-Res2Block×3          │                              │
│  │        ↓                │                              │
│  │ Attention Module        │                              │
│  │        ↓                │                              │
│  │ Pooling                 │                              │
│  │        ↓                │                              │
│  │ FC → Embedding (512-dim)│                              │
│  └─────────────────────────┘                              │
│                                                             │
│  Output: embedding = [0.123, 0.456, ..., 0.789] (512 dim) │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Database Storage                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Insert into voice_enrollments:                            │
│  {                                                          │
│    _id: ObjectId("..."),                                  │
│    phone_number: "+1-555-0000",                           │
│    embedding: [0.123, 0.456, ..., 0.789],                 │
│    sample_count: 5,          ← NEW / UPDATED             │
│    enrollment_date: "2024-02-20T10:30:00Z",              │
│    audio_hash: "abc123def456...",                         │
│    status: "active",                                       │
│    metadata: {                                             │
│      multi_sample: true,                                  │
│      samples_used: 5,                                     │
│      merged: true,                                        │
│      platform: "frontend-v2"                              │
│    }                                                       │
│  }                                                         │
│                                                             │
│  Return to Frontend:                                      │
│  {                                                         │
│    type: "enrollment_success",                            │
│    payload: {                                             │
│      message: "All 5 voice samples enrolled...",         │
│      vector_id: ObjectId(...),                           │
│      sample_count: 5                                      │
│    }                                                       │
│  }                                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 9: Frontend Success Response                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Display Success Message:                                  │
│  ✓ "All 5 voice samples enrolled successfully!"           │
│  ✓ Vector ID: abc123...                                   │
│  ✓ Sample Count: 5                                         │
│                                                             │
│  Reset Form:                                               │
│  - Clear phone number                                      │
│  - Reset all samples to null                               │
│  - Reset progress to 0/5                                   │
│  - Ready for next enrollment                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Component Hierarchy

```
App
└── EnrollmentPage
    ├── Header
    │   ├── Logo
    │   └── Status Indicator
    │
    ├── Main Content
    │   ├── Intro Section
    │   │   ├── Title
    │   │   └── Description
    │   │
    │   └── Enrollment Card
    │       ├── Phone Input
    │       │   ├── Label
    │       │   └── Input Field
    │       │
    │       ├── ChunkProcessingIndicator
    │       │   └── Progress Display
    │       │
    │       ├── Progress Section
    │       │   ├── Title & Counter
    │       │   └── Progress Bar
    │       │
    │       ├── Sample Cards Container
    │       │   ├── VoiceSampleCard #1
    │       │   │   ├── Header (Sample #, Status)
    │       │   │   ├── Recording Info Display
    │       │   │   ├── Audio Element (hidden)
    │       │   │   └── Action Buttons (Record/Stop/Play/Delete)
    │       │   ├── VoiceSampleCard #2
    │       │   ├── VoiceSampleCard #3
    │       │   ├── VoiceSampleCard #4
    │       │   └── VoiceSampleCard #5
    │       │
    │       ├── Messages Section
    │       │   ├── Error Message (if applicable)
    │       │   ├── Success Message (if applicable)
    │       │   └── Warning Message (if incomplete)
    │       │
    │       ├── Submit Button
    │       │   └── Loading State (during submission)
    │       │
    │       └── Footer Bar
    │           ├── Samples Ready Counter
    │           └── Security Badge
    │
    ├── Steps Indicator
    │   ├── Step 1: Identity
    │   ├── Step 2: 5 Voice Samples (current)
    │   └── Step 3: Verification
    │
    └── Footer
        └── Copyright
```

---

## 🔐 State Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     Initial State                            │
├──────────────────────────────────────────────────────────────┤
│ samples = [{blob: null, duration: 0}, ...]  (×5)            │
│ recordingBlackout = -1                                       │
│ phoneNumber = ""                                             │
│ isSubmitting = false                                         │
│ error = null                                                 │
│ result = null                                                │
└──────────────────────────────────────────────────────────────┘
         ↓
    User Actions:
    • Enter phone
    • Record samples
    • Stop recording
    • Play audio
    • Delete sample
    • Submit enrollment
         ↓
┌──────────────────────────────────────────────────────────────┐
│              Updated State (After Actions)                   │
├──────────────────────────────────────────────────────────────┤
│ samples = [                                                  │
│   {blob: Blob(...), duration: 4.5},  ← GREEN              │
│   {blob: Blob(...), duration: 5.2},  ← GREEN              │
│   {blob: Blob(...), duration: 3.8},  ← GREEN              │
│   {blob: Blob(...), duration: 4.1},  ← GREEN              │
│   {blob: Blob(...), duration: 4.9}   ← GREEN              │
│ ]                                                            │
│ recordingBlackout = -1  (no recording in progress)          │
│ phoneNumber = "+1-555-0000"                                 │
│ isSubmitting = false                                        │
│ error = null                                                │
│ result = null                                               │
│                                                              │
│ UI Changes:                                                 │
│ • All 5 cards turn GREEN                                   │
│ • Progress bar = 100%                                      │
│ • Submit button ENABLED                                    │
│ • Counter shows 5/5                                        │
└──────────────────────────────────────────────────────────────┘
         ↓
    User clicks Submit
         ↓
┌──────────────────────────────────────────────────────────────┐
│           Submitting State                                   │
├──────────────────────────────────────────────────────────────┤
│ isSubmitting = true                                          │
│ showChunkProgress = true                                     │
│ chunkProgress = {current: 0, total: 40, status: "..."}     │
│                                                              │
│ UI: Spinner on submit button, progress indicator visible   │
└──────────────────────────────────────────────────────────────┘
         ↓
    Backend processes samples
         ↓
┌──────────────────────────────────────────────────────────────┐
│           Success State                                      │
├──────────────────────────────────────────────────────────────┤
│ isSubmitting = false                                         │
│ result = {                                                   │
│   success: true,                                             │
│   message: "All 5 voice samples enrolled...",               │
│   vectorId: "abc123...",                                    │
│   sampleCount: 5                                             │
│ }                                                            │
│ samples = [{blob: null, duration: 0}, ...] ← RESET         │
│ phoneNumber = "" ← RESET                                    │
│                                                              │
│ UI: Show success message, form reset                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 🌐 WebSocket Message Sequence

```
Frontend                              WebSocket                Backend
   │                                    │                        │
   ├──── Connect ─────────────────────→ │                        │
   │                                    ├─→ Accept Connection    │
   │                                    │ ← Initialize Handler   │
   │
   ├─ Audio Sample 1, Chunk 0 ────────→ │
   │  {sample_number: 1, chunk_number: 0, total_chunks: 8}     │
   │                                    ├─→ Store in [1]        │
   │
   ├─ Audio Sample 1, Chunk 1 ────────→ │
   │  {sample_number: 1, chunk_number: 1, total_chunks: 8}     │
   │                                    ├─→ Append to [1]       │
   │
   │                   ... (7 more chunks for sample 1)
   │
   ├─ Audio Sample 2, Chunk 0 ────────→ │
   │  {sample_number: 2, chunk_number: 0, total_chunks: 7}     │
   │                                    ├─→ Store in [2]        │
   │
   │                   ... (6 more chunks for sample 2)
   │
   │                   ... (samples 3, 4, 5 follow same pattern)
   │
   ├─ Enroll Request ──────────────────→ │
   │  {type: "enroll", phone_number, sample_count: 5}          │
   │                                    ├─→ Validate all 5      │
   │                                    ├─→ Reconstruct WAVs    │
   │                                    ├─→ Merge audio         │
   │                                    ├─→ Extract embedding   │
   │                                    ├─→ Store MongoDB       │
   │
   │ ← Progress Update ─────────────── │
   │  {type: "chunk_progress", status: "..."}                  │
   │
   │ ← Enrollment Success ──────────── │
   │  {type: "enrollment_success",     │
   │   payload: {vector_id, sample_count: 5}}                  │
   │
   └──── Disconnect ───────────────────→ │
        (automated after success)         └─→ Cleanup Handler
```

---

## 📊 Statistics & Performance

```
Recording Phase:
├─ Sample Duration: 2-10 seconds each
├─ Total Recording Time: 10-50 seconds
├─ Browser Memory: ~24MB - 120MB (depending on duration)
└─ File Size per Sample: ~32KB - 160KB

Transmission Phase:
├─ Chunk Size: ~4KB average
├─ Samples 1: 8 chunks
├─ Sample 2: 7 chunks
├─ Total Chunks: ~35-40 chunks
├─ Network Payload: ~150-200KB
├─ Transmission Time: 10-30 seconds
└─ WebSocket Messages: 40-45 total

Backend Processing:
├─ Audio Reconstruction: 1-2 seconds
├─ PCM to WAV Conversion: 0.5-1 second
├─ Audio Merging: 1-2 seconds
├─ Embedding Generation: 5-10 seconds
├─ Database Storage: 0.5-1 second
└─ Total Processing: 8-16 seconds

Total Enrollment Time:
├─ Recording: 10-50 seconds
├─ Transmission: 10-30 seconds
├─ Backend Processing: 8-16 seconds
└─ Total: 28-96 seconds (~1-2 minutes)
```

---

**Architecture Version**: 1.0  
**Last Updated**: February 2026
