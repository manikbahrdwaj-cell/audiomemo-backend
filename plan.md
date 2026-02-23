# WebSocket Real-Time Voice Enrollment & Verification Implementation Plan

## Overview
Implement WebSocket-based real-time audio streaming for voice enrollment and verification in the React app with Python (FastAPI) backend. Audio will be chunked, embedding vectors will be generated, and similarity comparison will determine user authenticity.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      REACT FRONTEND                             │
│  (Real-time audio capture, WebSocket client, UI updates)        │
└──────────────────────┬──────────────────────────────────────────┘
                       │ WebSocket Connection (ws://)
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                   WEBSOCKET SERVER (FastAPI)                     │
│  (websockets dependency, connection handling, message routing)   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ↓             ↓             ↓
    ┌─────────┐ ┌──────────────┐ ┌──────────────────┐
    │ AUDIO   │ │ EMBEDDING    │ │ VERIFICATION &   │
    │CHUNKING │ │GENERATION    │ │ STORAGE LOGIC    │
    │(1s/5s)  │ │(SpeechBrain) │ │(MongoDB, cosine) │
    └─────────┘ └──────────────┘ └──────────────────┘
         │             │                  │
         └─────────────┼──────────────────┘
                       ↓
                  ┌─────────────┐
                  │   MongoDB   │
                  │ (User Data) │
                  └─────────────┘
```

---

## Core Components to Implement

### 1. **WebSocket Server Setup**
- Install `fastapi` and `websockets` packages for WebSocket server
- Set up WebSocket connection handling in FastAPI
- Handle client connections, disconnections, and message routing
- Implement event-based message handling (enrollment, verification, audio chunks)

### 2. **Audio Chunking Logic**
- **Enrollment Mode**: Split audio into 1-second chunks (16kHz sampling = 16,000 samples)
- **Verification Mode**: Split audio into 5-second chunks (16kHz sampling = 80,000 samples)
- Implement buffer management to accumulate audio data until chunk size is reached
- Return chunks with metadata (timestamp, chunk_id)

### 3. **Embedding Generation**
- Use existing SpeechBrain model (`spkrec-ecapa-voxceleb`)
- **Enrollment**: Merge all 1-second audio chunks into a single audio buffer
- Generate a single embedding vector from the merged audio
- **Verification**: Generate embedding vector for each 5-second audio chunk separately
- Return embeddings with shape [1, 192] (SpeechBrain ECAPA-TDNN output size)

### 4. **Audio Merging Function**
- Collect all 1-second audio chunks from enrollment session
- Concatenate/merge all audio chunks into a single continuous audio buffer
- **Strategy**: Linear concatenation - combine chunks in order with no gaps
  - Formula: `merged_audio = concatenate([chunk_1, chunk_2, ..., chunk_n])`
- Generate single embedding from merged audio using SpeechBrain
- Normalize embedding using L2 normalization for consistent similarity scores
- Store only the merged audio's embedding in MongoDB

### 5. **Cosine Similarity Function**
- Implement cosine similarity calculation between two embedding vectors
- Formula: `similarity = (A · B) / (||A|| × ||B||)`
- Return similarity score in range [0, 1]
- Use threshold of **0.75** for verification decision

### 6. **Verification Logic**
- Accept 4 chunks during verification (or configurable number)
- Generate embedding for each chunk
- Compare each chunk embedding against stored user embedding
- **Decision Rule**: If **1 or more chunks** have similarity ≥ 0.75, verify user successfully
- Return verification result with confidence score (best match score)

---

## Detailed Flow Diagrams

### ENROLLMENT FLOW

```
User clicks "Enroll" 
        │
        ↓
WebSocket Connection Established
(POST: {action: 'enroll', userId: 'user123'})
        │
        ↓
Frontend - Start Recording & Streaming
        │
        ├─→ Accumulate audio for 1 second
        │
        ├─→ Send 1-second chunk via WebSocket
        │   {type: 'audio_chunk', data: ArrayBuffer}
        │
        ├─→ Backend receives chunk
        │   ├─→ Convert to audio format
        │   ├─→ Generate embedding via SpeechBrain
        │   └─→ Store in memory (enrollmentEmbeddings[])
        │
        ├─→ Repeat until user stops recording (minimum 5 chunks = 5 seconds)
        │
        ↓
Frontend sends completion signal
{type: 'enrollment_complete'}
        │
        ↓
Backend - Merge All Audio Chunks
├─→ audio_chunks = [chunk_1, chunk_2, chunk_3, ...]
├─→ merged_audio = concatenate(audio_chunks)
        │
        ↓
Generate Embedding from Merged Audio
├─→ final_embedding = generateEmbedding(merged_audio)
├─→ final_embedding = L2Normalize(final_embedding)
        │
        ↓
Save to MongoDB
├─→ db.users.updateOne(
│   {userId: 'user123'},
│   {$set: {voiceEmbedding: final_embedding, enrolledAt: Date}}
│ )
        │
        ↓
Send confirmation to Frontend
{status: 'enrolled_successfully', message: 'Voice profile created'}
```

### VERIFICATION FLOW

```
User clicks "Verify" 
        │
        ↓
WebSocket Connection Established
(POST: {action: 'verify', userId: 'user123'})
        │
        ↓
Retrieve Stored Embedding from MongoDB
├─→ storedEmbedding = db.users.findOne({userId: 'user123'}).voiceEmbedding
        │
        ↓
Frontend - Start Recording & Streaming
        │
        ├─→ Accumulate audio for 5 seconds
        │
        ├─→ Send 5-second chunk via WebSocket
        │   {type: 'audio_chunk', data: ArrayBuffer}
        │
        ├─→ Backend receives chunk
        │   ├─→ Convert to audio format
        │   ├─→ Generate embedding via SpeechBrain
        │   ├─→ Calculate cosine_similarity(chunk_embedding, storedEmbedding)
        │   └─→ Track similarity score
        │
        ├─→ Repeat for 4 chunks total (20 seconds of audio)
        │
        ↓
Collect Results: [similarity_1, similarity_2, similarity_3, similarity_4]
        │
        ↓
Apply Verification Logic (UPDATED: All Chunks Must Pass)
├─→ For each chunk, check: similarity_score >= 0.75
├─→ IF any chunk fails → verify_success = False, STOP
├─→ IF all 4 chunks pass → verify_success = True
        │
        ↓
Send Result to Frontend
{
  status: 'verified' | 'failed',
  confidence: min_or_avg(similarity_scores),
  details: {
    chunk_scores: [0.82, 0.81, 0.78, 0.83],
    all_chunks_passed: true,
    threshold: 0.75
  }
}
```

---

## Implementation Checklist

### Backend Setup
- [ ] Install required packages: `pip install fastapi websockets uvicorn numpy scipy`
- [ ] Create WebSocket server wrapper/handler
- [ ] Set up WebSocket endpoint in FastAPI

### Core Functions (Python)

#### Audio Processing
- [ ] `chunk_audio(buffer, sample_rate, chunk_duration_ms)` - Split audio into chunks
- [ ] `buffered_audio_receiver(websocket_message)` - Accumulate incoming audio data

#### Embedding Operations
- [ ] `generate_embedding(audio_buffer)` - Generate embedding from audio buffer using SpeechBrain
- [ ] `merge_audio_chunks(chunk_array)` - Concatenate audio chunks into single buffer
  - Input: Array of audio chunks [chunk_1, chunk_2, ..., chunk_n]
  - Output: Single merged audio buffer
- [ ] `cosine_similarity(vec1, vec2)` - Calculate similarity between two vectors

#### Verification Logic
- [ ] `verify_user(user_id, chunk_embeddings, threshold)` - Apply matching rule logic
  - Inputs: user_id, array of chunk embeddings, similarity threshold
  - Outputs: verification result with confidence score

#### MongoDB Integration
- [ ] `save_user_embedding(user_id, final_embedding, metadata)` - Store in MongoDB
- [ ] `get_user_embedding(user_id)` - Retrieve stored embedding from MongoDB
- [ ] `validate_enrollment_duration(chunk_count)` - Enforce minimum 5-second enrollment
- [ ] Schema: `{user_id, voice_embedding, enrolled_at, enrollment_duration_seconds, enrollment_chunks_count}`

### WebSocket Message Handlers
- [ ] `on_enrollment_start(message)` - Initialize enrollment session
- [ ] `on_audio_chunk(message)` - Receive and process audio chunk
- [ ] `on_enrollment_complete(message)` - Finalize enrollment
- [ ] `on_verification_start(message)` - Initialize verification
- [ ] `on_verification_complete(message)` - Finalize and verify

### Frontend Updates (React)
- [ ] Update `audioRecorder.js` to support WebSocket streaming
- [ ] Modify enrollment component to use WebSocket
- [ ] Modify verification component to use WebSocket
- [ ] Add UI feedback for real-time chunk processing
- [ ] Display confidence scores and chunk results

### Testing & Validation
- [ ] Unit tests for chunking logic
- [ ] Unit tests for embedding merging
- [ ] Unit tests for cosine similarity calculation
- [ ] Integration test for enrollment flow
- [ ] Integration test for verification flow
- [ ] Test edge cases (silent audio, background noise, different speakers)

---

## Technical Specifications

### Audio Format & Parameters
```
Sample Rate: 16,000 Hz (16 kHz)
Channels: 1 (mono)
Bit Depth: 16-bit
Chunk Duration (Enrollment): 1 second = 16,000 samples
Chunk Duration (Verification): 5 seconds = 80,000 samples
```

### Embedding Specifications
```
Model: SpeechBrain ECAPA-TDNN (spkrec-ecapa-voxceleb)
Embedding Dimension: 192
Output Shape per chunk: [1, 192]
Final merged embedding shape: [192]
Similarity Range: [0.0, 1.0]
Verification Threshold: 0.75 (adjustable)
```

### Enrollment Parameters
```
Chunk Duration: 1 second
Min Total Duration: 5 seconds (5 chunks minimum)
Audio Merge Strategy: Concatenation (linear)
Embedding: Single embedding from merged audio
```

### Verification Parameters
```
Chunks per Verification: 4
Chunk Duration: 5 seconds each
Min Chunks for Match: 1
Similarity Threshold: 0.75
Decision: IF matched_chunks >= 1 THEN verified ELSE rejected
```

---

## Python Dependencies

```
fastapi==0.104.0
websockets==12.0
uvicorn==0.24.0
numpy==1.24.0
scipy==1.11.0
pydantic==2.5.0
pymongo==4.5.0
python-multipart==0.0.6
librosa==0.10.0
torch==2.1.0
speechbrain==0.5.14
```

---

## File Structure (Post-Implementation)

```
backend/
  ├── websocket_server.py     [NEW] WebSocket server setup
  ├── audio_chunking.py       [NEW] Chunking logic
  ├── embedding_service.py    [NEW] Embedding/merging/similarity operations
  ├── verification_service.py [NEW] Verification logic
  ├── enrollment_service.py   [NEW] Enrollment flow handler
  ├── database.py             [UPDATED] Save/retrieve embeddings
  ├── models/
  │   └── user.py             [NEW/UPDATED] User schema with embedding field
  ├── routes/
  │   └── ws_routes.py        [NEW] WebSocket routes
  ├── main.py                 [UPDATED] FastAPI app setup

frontend/src/
  ├── utils/
  │   └── audioRecorder.js   [UPDATED] Add WebSocket streaming
  ├── services/
  │   └── wsClient.js        [NEW] WebSocket client wrapper
  ├── components/
  │   ├── EnrollmentPage.js  [UPDATED] WebSocket integration
  │   └── VerificationPage.js[UPDATED] WebSocket + results display
```

---

## Implementation Order (Recommended)

1. **Setup WebSocket Infrastructure** (Backend)
   - Install FastAPI and websockets packages
   - Create WebSocket server handler
   - Set up message routing endpoints

2. **Implement Audio Chunking** (Backend)
   - Implement chunking logic with numpy
   - Test with sample audio

3. **Implement Embedding Operations** (Backend)
   - Embedding generation using SpeechBrain
   - Audio merging (concatenation) function
   - Cosine similarity function using scipy

4. **Implement Enrollment Service** (Backend)
   - Collect audio chunks
   - Merge audio, generate embedding
   - Store in MongoDB
   - Send confirmation

5. **Implement Verification Service** (Backend)
   - Retrieve stored embedding from MongoDB
   - Compare chunk embeddings
   - Apply matching logic

6. **Frontend WebSocket Client** (Frontend)
   - Update audioRecorder.js for streaming
   - Create WebSocket client wrapper
   - Integrate with enrollment/verification components

7. **UI/UX Updates** (Frontend)
   - Real-time feedback on chunk processing
   - Display similarity scores
   - Show verification results

8. **Testing & Validation**
   - Unit tests for all functions (pytest)
   - Integration tests for full flows
   - Edge case testing

---

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| **Audio Merging** (concatenate chunks) for enrollment | Preserves continuous speech context, captures natural speaker patterns across extended audio |
| **Single embedding from merged audio** | More robust than averaging individual embeddings; captures prosody and speech dynamics |
| **L2 Normalization** | Ensures consistent cosine similarity scores in [0, 1] range |
| **Cosine Similarity** | Industry-standard for voice embeddings, efficient computation |
| **Min 1 chunk match rule** | Balances security (at least 1 match) with usability (doesn't require all chunks to match) |
| **0.75 threshold** | Typical threshold for ECAPA-TDNN embeddings; can be tuned based on false accept/reject rates |
| **WebSocket over HTTP** | Enables real-time streaming without request-response overhead |

---

## Performance Considerations

- **Latency**: WebSocket eliminates HTTP overhead; embedding generation (~50-100ms per chunk)
- **Memory**: Store embeddings in MongoDB, not in memory (except during active session)
- **Scalability**: Each WebSocket connection is independent; scale backend horizontally
- **Bandwidth**: Audio streaming ~2KB per second (16kHz, 16-bit mono)

---

## Security Considerations

- Validate user IDs and prevent enrollment/verification mismatches
- Use HTTPS + WSS (WebSocket Secure) in production
- Rate limit enrollment/verification attempts
- Store embeddings securely in MongoDB (no plain text)
- Validate audio data format and size before processing

---

## Error Handling

- Handle WebSocket disconnections gracefully
- Validate audio chunk size and format
- Handle embedding generation failures
- Manage MongoDB connection errors
- Return meaningful error messages to frontend

---

## Next Steps

1. Review and finalize this plan
2. Begin implementation starting with WebSocket infrastructure
3. Test each component independently
4. Perform integration testing
5. Deploy and monitor performance
