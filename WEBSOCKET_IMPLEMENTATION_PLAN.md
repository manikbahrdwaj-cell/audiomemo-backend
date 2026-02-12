# WebSocket Real-Time Voice Enrollment & Verification Implementation Plan

**Last Updated:** February 12, 2026  
**Status:** Planning Phase

---

## Table of Contents
1. [Overview & Requirements](#overview--requirements)
2. [Architecture](#architecture)
3. [Component Breakdown](#component-breakdown)
4. [Enrollment Flow (Detailed)](#enrollment-flow-detailed)
5. [Verification Flow (Detailed)](#verification-flow-detailed)
6. [Implementation Steps](#implementation-steps)
7. [File Structure](#file-structure)
8. [Core Utilities](#core-utilities)
9. [Frontend Integration](#frontend-integration)
10. [Testing & Validation](#testing--validation)
11. [Performance Considerations](#performance-considerations)

---

## Overview & Requirements

### Problem Statement
Currently, the voice enrollment/verification system processes audio files in batch mode. We need to implement real-time streaming capabilities using WebSocket for:
- **Live audio streaming** during enrollment and verification
- **Immediate feedback** to users
- **Flexible chunking strategies** for enrollment (1-second) and verification (5-second)

### Key Requirements

#### ENROLLMENT FLOW
- ✓ Real-time audio streaming via WebSocket
- ✓ Split audio into **1-second chunks**
- ✓ Generate embedding for each chunk using ECAPA-VoxCeleb model
- ✓ Merge/average all chunk embeddings into a single final embedding
- ✓ Store only the final merged embedding in MongoDB
- ✓ Prevent duplicate enrollments

#### VERIFICATION FLOW
- ✓ Real-time audio streaming via WebSocket
- ✓ Split audio into **5-second chunks**
- ✓ Generate embedding for each 5-second chunk
- ✓ Compare each chunk embedding with stored embedding using cosine similarity
- ✓ **Require minimum 4 chunk matches** above threshold (0.75)
- ✓ Provide success/failure response to user
- ✓ Log verification attempts

---

## Architecture

### System Overview
```
[React Frontend]
       ↓
   WebSocket
   (Socket.io)
       ↓
[Node.js + Express Backend]
   ├── Audio Chunking Service
   ├── Embedding Service (ECAPA-VoxCeleb)
   ├── Embedding Merge/Compare Service
   └── MongoDB Database
```

### Technology Stack
- **WebSocket Library:** Socket.io (recommended for features like auto-reconnect, fallbacks)
- **Backend:** Node.js + Express
- **Audio Processing:** 
  - `librosa` (Python subprocess) OR
  - `wav` + `fluent-ffmpeg` (Node.js native)
- **Embedding Model:** ECAPA-VoxCeleb (via existing Python backend)
- **Similarity:** Cosine similarity via `numpy` or Node.js `similarity` package
- **Database:** MongoDB (existing)

### Communication Flow
```
Frontend (WebSocket) → Backend (Socket.io Server)
                    ↓
              Audio Processor
                    ↓
              ECAPA Model (Python)
                    ↓
              Embedding Merger / Comparator
                    ↓
              MongoDB
                    ↓
Frontend (Response Message)
```

---

## Component Breakdown

### Backend Components to Implement

#### 1. **WebSocket Server** (`websocket-handler.js`)
- Listen for connection events
- Handle enrollment/verification room creation
- Manage binary audio data reception
- Emit progress updates and results

#### 2. **Audio Chunking Service** (`audio-chunker.js`)
- Decode base64/binary audio to PCM
- Split audio into configurable chunk sizes (1s or 5s)
- Handle variable frame rates and audio formats
- Detect silence/noise for quality checks

#### 3. **Embedding Service** (`embedding-service.js`)
- Interface with Python ECAPA model
- Cache embeddings during session
- Handle errors and retries
- Return normalized embedding vectors

#### 4. **Embedding Merger** (`embedding-merger.js`)
- Average embeddings from enrollment chunks
- Normalize final merged embedding
- Handle edge cases (single chunk, NaN values)

#### 5. **Similarity Checker** (`similarity-checker.js`)
- Calculate cosine similarity between embeddings
- Batch compare multiple chunk embeddings
- Track match count and confidence scores
- Return verification result with confidence

#### 6. **Session Manager** (`session-manager.js`)
- Track active enrollment/verification sessions
- Store temporary chunk embeddings
- Clean up resources on disconnect
- Implement timeout logic

#### 7. **Database Models** (MongoDB Updates)
- Create `VoiceProfile` schema with:
  - userId
  - finalEmbedding (single vector)
  - enrollmentDate
  - chunkCount (metadata)
  - isVerified (status)

#### 8. **Event Handlers**
- `enrollment:start` → Initialize session
- `audio:chunk` → Process incoming chunk
- `enrollment:complete` → Merge and save
- `verification:start` → Load stored embedding
- `audio:chunk` → Process & compare
- `verification:complete` → Return result

---

## Enrollment Flow (Detailed)

### High-Level Steps

```
User Starts Enrollment
        ↓
WebSocket Connection Established
        ↓
Audio Streamed in 1-Second Chunks
        ↓
[Repeat for each chunk]:
  - Receive chunk from frontend
  - Decode audio to PCM format
  - Generate embedding vector
  - Store embedding in memory (session)
  - Send ACK to frontend
        ↓
User Completes Recording
        ↓
Merge Phase:
  - Average all chunk embeddings
  - Create single final embedding
  - Normalize vector
        ↓
Save to MongoDB:
  - Create/Update VoiceProfile
  - Store final embedding
  - Record enrollment metadata
        ↓
Send Success Response to Frontend
```

### Enrollment Sequence Diagram
```
Frontend                Backend              Python Service        MongoDB
   |                       |                       |                  |
   |-- enrollment:start -->|                       |                  |
   |                    [Initialize Session]       |                  |
   |<-- ack:enrolled ------|                       |                  |
   |                       |                       |                  |
   |-- audio:chunk(t=0-1s)-|                       |                  |
   |                    [Buffer]                   |                  |
   |                       |-- generate:embedding->|                  |
   |                       |<-embedding vector----|                  |
   |<-- ack:chunk-1 ------|                       |                  |
   |                    [Store in memory]          |                  |
   |                       |                       |                  |
   |-- audio:chunk(t=1-2s)-|                       |                  |
   |                    [Repeat...]                |                  |
   |<-- ack:chunk-2 ------|                       |                  |
   |                       |                       |                  |
   |-- enrollment:done --->|                       |                  |
   |                    [Merge embeddings]        |                  |
   |                    [Normalize]               |                  |
   |                       |                       |                  |
   |                       |---- save:profile ----------> save ---->| 
   |                       |                       |                  |
   |<-- enrollment:success-|                       |                  |
   |   (finalEmbedding)    |                       |                  |
```

### Pseudo-Code

```python
ENROLLMENT_SESSION = {
    userId: string,
    embeddings: [],  # List of chunk embeddings
    startTime: timestamp,
    chunkCount: 0
}

async function handle_enrollment_start(userId):
    session = create_session(userId)
    emit "ack:enrolled" to frontend

async function handle_audio_chunk(chunk_audio_bytes):
    # 1. Decode and validate audio
    pcm_audio = decode_audio(chunk_audio_bytes)
    if is_silent(pcm_audio):
        emit "warning:silent_chunk"
        return
    
    # 2. Generate embedding
    embedding = await call_python_service(pcm_audio, model="ecapa-voxceleb")
    
    # 3. Store in session
    ENROLLMENT_SESSION.embeddings.append(embedding)
    ENROLLMENT_SESSION.chunkCount += 1
    
    # 4. Send ACK with metadata
    emit "ack:chunk-{ENROLLMENT_SESSION.chunkCount}" with {
        chunkIndex: ENROLLMENT_SESSION.chunkCount,
        confidence: calculate_embedding_quality(embedding)
    }

async function handle_enrollment_complete():
    # 1. Merge embeddings
    final_embedding = merge_embeddings(
        ENROLLMENT_SESSION.embeddings,
        method="average_with_normalization"
    )
    
    # 2. Validate embedding
    if not is_valid_embedding(final_embedding):
        emit "error:invalid_embedding"
        return
    
    # 3. Save to MongoDB
    profile = {
        userId: ENROLLMENT_SESSION.userId,
        finalEmbedding: final_embedding,
        enrollmentDate: now(),
        chunkCount: ENROLLMENT_SESSION.chunkCount,
        isVerified: true
    }
    
    saved_profile = await db.voiceProfiles.insertOne(profile)
    
    # 4. Clear session
    delete ENROLLMENT_SESSION
    
    # 5. Send success response
    emit "enrollment:success" with {
        profileId: saved_profile._id,
        embeddinDimensions: final_embedding.length,
        totalChunks: profile.chunkCount
    }
```

---

## Verification Flow (Detailed)

### High-Level Steps

```
User Starts Verification
        ↓
WebSocket Connection Established
        ↓
Load Stored Embedding from MongoDB
        ↓
Audio Streamed in 5-Second Chunks
        ↓
[Repeat for each chunk]:
  - Receive chunk from frontend
  - Decode audio to PCM format
  - Generate embedding vector
  - Calculate cosine similarity with stored embedding
  - Track match if similarity > 0.75
  - Send progress update to frontend
        ↓
Check Match Count
        ↓
IF (matchCount >= 4):
  - Verification SUCCESS ✓
  - Update user session (login/auth)
  - Record successful verification in logs
ELSE:
  - Verification FAILED ✗
  - Record failed verification attempt
  - Suggest re-recording
```

### Verification Sequence Diagram
```
Frontend                Backend              Python Service        MongoDB
   |                       |                       |                  |
   |-- verification:start->|                       |                  |
   |-- (userName/userId)  |---- load:profile ----------> query ---->|
   |                       |<-- storedEmbedding ---|                  |
   |<-- ack:ready---------|                       |                  |
   |                    [Initialize Session]      |                  |
   |                       |                       |                  |
   |--audio:chunk(t=0-5s)--| [Buffer]              |                  |
   |                       |-- generate:embedding->|                  |
   |                       |<-embedding vector----|                  |
   |                    [Compare similarities]     |                  |
   |<--progress:match(0.82)|  (0.82 > 0.75) ✓      |                  |
   |                    [matchCount = 1]          |                  |
   |                       |                       |                  |
   |--audio:chunk(t=5-10s)-|                       |                  |
   |                    [Repeat...]                |                  |
   |<--progress:match(0.81)|  (0.81 > 0.75) ✓      |                  |
   |                    [matchCount = 2]          |                  |
   |                       |                       |                  |
   |-- audio:chunk(t=10-15)|                       |                  |
   |<--progress:match(0.78)|  (0.78 > 0.75) ✓      |                  |
   |                    [matchCount = 3]          |                  |
   |                       |                       |                  |
   |-- audio:chunk(t=15-20)|                       |                  |
   |<--progress:match(0.79)|  (0.79 > 0.75) ✓      |                  |
   |                    [matchCount = 4]          |                  |
   |                    [THRESHOLD MET!]          |                  |
   |<--verification:success|                       |                  |
   |   (matchCount=4,      |                       |                  |
   |    avgScore=0.80)     |                       |                  |
```

### Pseudo-Code

```python
VERIFICATION_SESSION = {
    userId: string,
    storedEmbedding: vector,
    chunkEmbeddings: [],
    similarities: [],
    matchCount: 0,
    minChunkMatches: 4,
    matchThreshold: 0.75,
    startTime: timestamp
}

async function handle_verification_start(userId_or_userName):
    # 1. Load stored embedding from MongoDB
    profile = await db.voiceProfiles.findOne({ 
        userId: userId_or_userName 
    })
    
    if not profile:
        emit "error:user_not_enrolled"
        return
    
    # 2. Initialize session
    VERIFICATION_SESSION = {
        userId: userId_or_userName,
        storedEmbedding: profile.finalEmbedding,
        chunkEmbeddings: [],
        similarities: [],
        matchCount: 0,
        minChunkMatches: 4,
        matchThreshold: 0.75,
        startTime: now()
    }
    
    # 3. Send ready signal
    emit "ack:ready" with {
        user: profile.userName,
        profileId: profile._id
    }

async function handle_verification_chunk(chunk_audio_bytes):
    # 1. Decode and validate audio
    pcm_audio = decode_audio(chunk_audio_bytes)
    
    # 2. Generate embedding
    chunk_embedding = await call_python_service(
        pcm_audio,
        model="ecapa-voxceleb"
    )
    
    # 3. Calculate similarity
    similarity = cosine_similarity(
        VERIFICATION_SESSION.storedEmbedding,
        chunk_embedding
    )
    
    # 4. Check if match
    is_match = similarity >= VERIFICATION_SESSION.matchThreshold
    
    # 5. Update tracking
    VERIFICATION_SESSION.chunkEmbeddings.append(chunk_embedding)
    VERIFICATION_SESSION.similarities.append(similarity)
    
    if is_match:
        VERIFICATION_SESSION.matchCount += 1
    
    # 6. Send progress update
    emit "progress:chunk" with {
        chunkIndex: len(VERIFICATION_SESSION.similarities),
        similarity: similarity,
        isMatch: is_match,
        matchCount: VERIFICATION_SESSION.matchCount,
        threshold: VERIFICATION_SESSION.matchThreshold
    }
    
    # 7. Check if verification threshold reached early
    if VERIFICATION_SESSION.matchCount >= VERIFICATION_SESSION.minChunkMatches:
        handle_verification_complete(early=true)

async function handle_verification_complete():
    # 1. Calculate final score
    matchCount = VERIFICATION_SESSION.matchCount
    totalChunks = len(VERIFICATION_SESSION.similarities)
    avgSimilarity = mean(VERIFICATION_SESSION.similarities)
    
    # 2. Determine result
    isVerified = matchCount >= VERIFICATION_SESSION.minChunkMatches
    
    # 3. Log attempt
    verification_log = {
        userId: VERIFICATION_SESSION.userId,
        timestamp: now(),
        isSuccess: isVerified,
        chunkCount: totalChunks,
        matchCount: matchCount,
        avgSimilarity: avgSimilarity,
        similarities: VERIFICATION_SESSION.similarities
    }
    
    await db.verificationLogs.insertOne(verification_log)
    
    # 4. If successful, update auth session
    if isVerified:
        update_user_session(VERIFICATION_SESSION.userId, authenticated=true)
    
    # 5. Send result
    emit "verification:complete" with {
        isVerified: isVerified,
        matchCount: matchCount,
        requiredMatches: VERIFICATION_SESSION.minChunkMatches,
        totalChunks: totalChunks,
        avgSimilarity: avgSimilarity,
        similarities: VERIFICATION_SESSION.similarities
    }
    
    # 6. Clear session
    delete VERIFICATION_SESSION
```

---

## Implementation Steps

### Phase 1: Backend Setup (Weeks 1-2)

- [ ] **Step 1.1:** Install Socket.io and dependencies
  ```bash
  npm install socket.io express cors dotenv
  npm install node-wav audio-buffer wav-decoder
  ```

- [ ] **Step 1.2:** Create WebSocket server (`websocket-handler.js`)
  - Initialize Socket.io with Express
  - Create namespaces for `/enrollment` and `/verification`
  - Implement connection/disconnection handlers

- [ ] **Step 1.3:** Implement `audio-chunker.js`
  - Audio format detection and validation
  - PCM conversion utilities
  - 1-second and 5-second chunking logic
  - Silence detection

- [ ] **Step 1.4:** Create `embedding-service.js`
  - Interface with existing Python ECAPA model
  - Implement caching strategy
  - Error handling and retry logic

- [ ] **Step 1.5:** Implement `embedding-merger.js`
  - Average pooling function
  - L2 normalization
  - Quality validation

- [ ] **Step 1.6:** Create `similarity-checker.js`
  - Cosine similarity calculation
  - Batch comparison utilities
  - Confidence scoring

### Phase 2: Session Management (Week 2)

- [ ] **Step 2.1:** Implement `session-manager.js`
  - Session creation/deletion
  - Memory management
  - Timeout handling

- [ ] **Step 2.2:** Update MongoDB schemas
  - Add `VoiceProfile` collection
  - Add `VerificationLog` collection
  - Create indexes

- [ ] **Step 2.3:** Create event handlers
  - `enrollment:start`, `audio:chunk`, `enrollment:complete`
  - `verification:start`, `audio:chunk`, `verification:complete`
  - Error handlers

### Phase 3: Frontend Integration (Week 2-3)

- [ ] **Step 3.1:** Install Socket.io client
  ```bash
  npm install socket.io-client
  ```

- [ ] **Step 3.2:** Create WebSocket service (`websocket-service.js`)
  - Connection management
  - Event listeners
  - Reconnection logic

- [ ] **Step 3.3:** Update `audioRecorder.js`
  - Real-time audio streaming
  - Chunk buffering and transmission
  - Sample rate handling

- [ ] **Step 3.4:** Update enrollment component
  - WebSocket event handling
  - Progress display
  - Error handling

- [ ] **Step 3.5:** Update verification component
  - Real-time similarity display
  - Match counter
  - Success/failure UI

### Phase 4: Testing (Week 3)

- [ ] **Step 4.1:** Unit tests for utility functions
- [ ] **Step 4.2:** Integration tests for WebSocket handlers
- [ ] **Step 4.3:** End-to-end tests
- [ ] **Step 4.4:** Performance/load testing

### Phase 5: Deployment (Week 4)

- [ ] **Step 5.1:** Environment configuration
- [ ] **Step 5.2:** Docker containerization (optional)
- [ ] **Step 5.3:** Production deployment
- [ ] **Step 5.4:** Monitoring and logging setup

---

## File Structure

### Backend New Files

```
backend/
├── websocket/
│   ├── websocket-handler.js          # Main WebSocket server setup
│   ├── namespaces/
│   │   ├── enrollment-namespace.js   # Enrollment event handlers
│   │   └── verification-namespace.js # Verification event handlers
│   └── middleware/
│       └── auth-middleware.js        # WebSocket authentication
├── services/
│   ├── audio-chunker.js              # Audio chunking logic
│   ├── embedding-service.js          # ECAPA embedding generation
│   ├── embedding-merger.js           # Embedding averaging/merging
│   ├── similarity-checker.js         # Cosine similarity calculation
│   └── session-manager.js            # Session lifecycle management
├── models/
│   ├── voice-profile-model.js        # MongoDB VoiceProfile schema
│   └── verification-log-model.js     # VerificationLog schema
├── utils/
│   ├── audio-utils.js                # Audio processing helpers
│   ├── math-utils.js                 # Vector math utilities
│   └── logger.js                     # Logging utility
├── config/
│   └── websocket-config.js           # Configuration constants
└── websocket-main.js                 # Entry point
```

### Frontend New Files

```
frontend/src/
├── services/
│   └── websocket-service.js          # Socket.io client wrapper
├── hooks/
│   ├── useWebSocket.js               # Custom WebSocket hook
│   ├── useEnrollment.js              # Enrollment logic hook
│   └── useVerification.js            # Verification logic hook
├── components/
│   ├── EnrollmentPage.js (UPDATED)   # Real-time enrollment component
│   ├── VerificationPage.js (UPDATED) # Real-time verification component
│   ├── ProgressBar.js                # Chunk progress visualization
│   ├── SimilarityMeter.js            # Real-time similarity display
│   └── MatchCounter.js               # Match count indicator
├── utils/
│   └── audio-recorder.js (UPDATED)   # Real-time audio streaming
└── constants/
    └── websocket-events.js           # Event constants
```

---

## Core Utilities

### 1. Cosine Similarity Function

```python
# similarity-checker.js
function cosine_similarity(vector1, vector2) {
    """
    Calculate cosine similarity between two embedding vectors.
    
    Args:
        vector1: Array of numbers
        vector2: Array of numbers
    
    Returns:
        Float between -1 and 1 (typically 0 to 1 for normalized embeddings)
    """
    if (vector1.length !== vector2.length) {
        throw new Error("Vectors must have same dimension");
    }
    
    let dotProduct = 0;
    let magnitude1 = 0;
    let magnitude2 = 0;
    
    for (let i = 0; i < vector1.length; i++) {
        dotProduct += vector1[i] * vector2[i];
        magnitude1 += vector1[i] * vector1[i];
        magnitude2 += vector2[i] * vector2[i];
    }
    
    magnitude1 = Math.sqrt(magnitude1);
    magnitude2 = Math.sqrt(magnitude2);
    
    if (magnitude1 === 0 || magnitude2 === 0) {
        return 0;  // One or both vectors are zero
    }
    
    return dotProduct / (magnitude1 * magnitude2);
}
```

### 2. Embedding Merging Function

```python
# embedding-merger.js
function merge_embeddings(chunk_embeddings, method = "average") {
    """
    Merge multiple chunk embeddings into a single embedding vector.
    
    Args:
        chunk_embeddings: List of embedding vectors
        method: "average" (default), "weighted_average", or "median"
    
    Returns:
        Single normalized embedding vector
    """
    if (chunk_embeddings.length === 0) {
        throw new Error("No embeddings to merge");
    }
    
    const embedding_dim = chunk_embeddings[0].length;
    let merged = new Array(embedding_dim).fill(0);
    
    if (method === "average") {
        // Simple average
        for (let emb of chunk_embeddings) {
            for (let i = 0; i < embedding_dim; i++) {
                merged[i] += emb[i];
            }
        }
        for (let i = 0; i < embedding_dim; i++) {
            merged[i] /= chunk_embeddings.length;
        }
    } else if (method === "weighted_average") {
        // Weight recent chunks higher
        const weights = chunk_embeddings.map((_, i) => 
            (i + 1) / chunk_embeddings.length  // Linear weight increase
        );
        const total_weight = weights.reduce((a, b) => a + b, 0);
        
        for (let idx = 0; idx < chunk_embeddings.length; idx++) {
            const weight = weights[idx] / total_weight;
            for (let i = 0; i < embedding_dim; i++) {
                merged[i] += chunk_embeddings[idx][i] * weight;
            }
        }
    }
    
    // L2 Normalization
    let magnitude = Math.sqrt(
        merged.reduce((sum, val) => sum + val * val, 0)
    );
    
    if (magnitude !== 0) {
        merged = merged.map(val => val / magnitude);
    }
    
    return merged;
}
```

### 3. Audio Chunking Function

```python
# audio-chunker.js
async function chunk_audio(audio_buffer, chunk_duration_seconds, sample_rate) {
    """
    Split audio buffer into chunks of specified duration.
    
    Args:
        audio_buffer: PCM audio data (Float32Array or Buffer)
        chunk_duration_seconds: Duration of each chunk (1 or 5 seconds)
        sample_rate: Sample rate in Hz (typically 16000 Hz)
    
    Returns:
        List of audio chunks (each as Float32Array)
    """
    const samples_per_chunk = chunk_duration_seconds * sample_rate;
    const chunks = [];
    
    for (let i = 0; i < audio_buffer.length; i += samples_per_chunk) {
        const chunk = audio_buffer.slice(i, i + samples_per_chunk);
        if (chunk.length > 0) {
            chunks.push(chunk);
        }
    }
    
    return chunks;
}

function is_silent(audio_chunk, threshold = 0.01) {
    """
    Check if audio chunk is silent (too quiet to process).
    
    Args:
        audio_chunk: Audio samples
        threshold: RMS threshold for silence detection
    
    Returns:
        Boolean indicating if chunk is silent
    """
    let sum_of_squares = 0;
    for (let sample of audio_chunk) {
        sum_of_squares += sample * sample;
    }
    
    const rms = Math.sqrt(sum_of_squares / audio_chunk.length);
    return rms < threshold;
}
```

### 4. Verification Logic Function

```python
# verification-logic.js
async function verify_user(
    chunk_embeddings,
    stored_embedding,
    min_chunk_matches = 4,
    similarity_threshold = 0.75
) {
    """
    Verify user based on chunk embeddings.
    
    Args:
        chunk_embeddings: List of embeddings from verification chunks
        stored_embedding: User's enrolled embedding vector
        min_chunk_matches: Minimum number of chunks that must match (default 4)
        similarity_threshold: Cosine similarity threshold (default 0.75)
    
    Returns:
        {
            is_verified: Boolean,
            match_count: Integer,
            total_chunks: Integer,
            similarities: List of similarity scores,
            avg_similarity: Float,
            confidence: Float (0-1)
        }
    """
    const similarities = [];
    let match_count = 0;
    
    for (let embedding of chunk_embeddings) {
        const similarity = cosine_similarity(stored_embedding, embedding);
        similarities.push(similarity);
        
        if (similarity >= similarity_threshold) {
            match_count++;
        }
    }
    
    const total_chunks = chunk_embeddings.length;
    const avg_similarity = similarities.reduce((a, b) => a + b, 0) / total_chunks;
    const is_verified = match_count >= min_chunk_matches;
    
    // Confidence: How well did we exceed the threshold?
    const confidence = is_verified ? 
        (match_count / min_chunk_matches) * (avg_similarity / similarity_threshold)
        : 0;
    
    return {
        is_verified: is_verified,
        match_count: match_count,
        total_chunks: total_chunks,
        similarities: similarities,
        avg_similarity: avg_similarity,
        confidence: Math.min(confidence, 1.0)  // Clamp to [0, 1]
    };
}
```

### 5. Vector Math Utilities

```python
# math-utils.js
function vector_magnitude(vector) {
    return Math.sqrt(
        vector.reduce((sum, val) => sum + val * val, 0)
    );
}

function normalize_vector(vector) {
    const mag = vector_magnitude(vector);
    if (mag === 0) return vector;
    return vector.map(val => val / mag);
}

function vector_dot_product(v1, v2) {
    if (v1.length !== v2.length) {
        throw new Error("Vectors must have same dimension");
    }
    return v1.reduce((sum, val, i) => sum + val * v2[i], 0);
}

function vector_subtract(v1, v2) {
    return v1.map((val, i) => val - v2[i]);
}

function euclidean_distance(v1, v2) {
    const diff = vector_subtract(v1, v2);
    return Math.sqrt(
        diff.reduce((sum, val) => sum + val * val, 0)
    );
}
```

---

## Frontend Integration

### Sample WebSocket Service

```javascript
// frontend/src/services/websocket-service.js
import io from 'socket.io-client';

class WebSocketService {
    constructor() {
        this.socket = null;
        this.enrolled_users = new Map();
    }

    connect(url = 'http://localhost:5000') {
        this.socket = io(url, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5
        });

        this.socket.on('connect', () => {
            console.log('WebSocket connected');
        });

        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
        });

        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
        });

        return this;
    }

    // ENROLLMENT
    start_enrollment(user_id) {
        return new Promise((resolve) => {
            this.socket.emit('enrollment:start', { userId: user_id }, (ack) => {
                resolve(ack);
            });
        });
    }

    send_enrollment_chunk(audio_chunk) {
        this.socket.emit('audio:chunk', {
            type: 'enrollment',
            data: audio_chunk
        });
    }

    complete_enrollment() {
        return new Promise((resolve) => {
            this.socket.emit('enrollment:complete', (response) => {
                resolve(response);
            });
        });
    }

    on_enrollment_ack(callback) {
        this.socket.on('ack:enrolled', callback);
    }

    on_chunk_ack(callback) {
        this.socket.on('ack:chunk', callback);
    }

    on_enrollment_success(callback) {
        this.socket.on('enrollment:success', callback);
    }

    // VERIFICATION
    start_verification(user_id) {
        return new Promise((resolve) => {
            this.socket.emit('verification:start', { userId: user_id }, (ack) => {
                resolve(ack);
            });
        });
    }

    send_verification_chunk(audio_chunk) {
        this.socket.emit('audio:chunk', {
            type: 'verification',
            data: audio_chunk
        });
    }

    complete_verification() {
        return new Promise((resolve) => {
            this.socket.emit('verification:complete', (response) => {
                resolve(response);
            });
        });
    }

    on_verification_progress(callback) {
        this.socket.on('progress:chunk', callback);
    }

    on_verification_complete(callback) {
        this.socket.on('verification:complete', callback);
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}

export default new WebSocketService();
```

### Sample Enrollment Component

```javascript
// frontend/src/components/EnrollmentPage.js (Updated)
import React, { useState, useRef } from 'react';
import websocketService from '../services/websocket-service';
import audioRecorder from '../utils/audio-recorder';

const EnrollmentPage = () => {
    const [isRecording, setIsRecording] = useState(false);
    const [progress, setProgress] = useState(0);
    const [chunks, setChunks] = useState([]);
    const [feedback, setFeedback] = useState('');
    const recorderRef = useRef(null);

    const handleStartEnrollment = async () => {
        // 1. Request WebSocket enrollment
        const response = await websocketService.start_enrollment('user123');
        console.log('Enrollment started:', response);

        // 2. Initialize audio recorder
        recorderRef.current = audioRecorder;
        await recorderRef.current.start({
            onChunk: handleAudioChunk
        });

        setIsRecording(true);
        setFeedback('Recording... 🎤');
    };

    const handleAudioChunk = (audioData) => {
        // Send chunk via WebSocket
        websocketService.send_enrollment_chunk(audioData);
        
        setChunks(prev => [...prev, audioData]);
        setProgress(chunks.length + 1);
    };

    const handleCompleteEnrollment = async () => {
        // 1. Stop recording
        await recorderRef.current.stop();
        setIsRecording(false);

        // 2. Notify backend
        setFeedback('Processing embeddings... ⏳');
        const result = await websocketService.complete_enrollment();

        if (result.success) {
            setFeedback(`✅ Enrollment successful! (${result.totalChunks} chunks processed)`);
        } else {
            setFeedback('❌ Enrollment failed. Please try again.');
        }
    };

    // Listen for acknowledgments
    React.useEffect(() => {
        websocketService.on_chunk_ack((data) => {
            console.log(`Chunk ${data.chunkIndex} processed`);
        });

        websocketService.on_enrollment_success((data) => {
            console.log('Enrollment completed:', data);
        });

        return () => {
            websocketService.disconnect();
        };
    }, []);

    return (
        <div className="enrollment-container">
            <h2>Voice Enrollment</h2>
            <p>Progress: {progress} seconds recorded</p>
            <progress value={progress} max="30"></progress>
            
            {!isRecording ? (
                <button onClick={handleStartEnrollment}>
                    Start Recording
                </button>
            ) : (
                <button onClick={handleCompleteEnrollment}>
                    Complete Enrollment
                </button>
            )}
            
            <p>{feedback}</p>
        </div>
    );
};

export default EnrollmentPage;
```

### Sample Verification Component

```javascript
// frontend/src/components/VerificationPage.js (Updated)
import React, { useState, useRef } from 'react';
import websocketService from '../services/websocket-service';
import audioRecorder from '../utils/audio-recorder';

const VerificationPage = () => {
    const [isRecording, setIsRecording] = useState(false);
    const [username, setUsername] = useState('');
    const [matchCount, setMatchCount] = useState(0);
    const [chunksSimilarities, setChunksSimilarities] = useState([]);
    const [isVerified, setIsVerified] = useState(null);
    const recorderRef = useRef(null);

    const handleStartVerification = async () => {
        if (!username) {
            alert('Please enter username');
            return;
        }

        // 1. Request verification
        const response = await websocketService.start_verification(username);
        if (!response.success) {
            alert('User not found or not enrolled');
            return;
        }

        // 2. Start recording
        recorderRef.current = audioRecorder;
        await recorderRef.current.start({
            chunkDuration: 5000,  // 5-second chunks for verification
            onChunk: handleAudioChunk
        });

        setIsRecording(true);
        setMatchCount(0);
        setChunksSimilarities([]);
    };

    const handleAudioChunk = (audioData) => {
        websocketService.send_verification_chunk(audioData);
    };

    const handleCompleteVerification = async () => {
        await recorderRef.current.stop();
        setIsRecording(false);

        const result = await websocketService.complete_verification();
        setIsVerified(result.is_verified);
    };

    // Listen for progress updates
    React.useEffect(() => {
        websocketService.on_verification_progress((data) => {
            setMatchCount(data.matchCount);
            setChunksSimilarities(prev => [...prev, data.similarity]);
        });

        websocketService.on_verification_complete((data) => {
            setIsVerified(data.isVerified);
        });

        return () => {
            websocketService.disconnect();
        };
    }, []);

    return (
        <div className="verification-container">
            <h2>Voice Verification</h2>
            
            {!isRecording ? (
                <>
                    <input
                        type="text"
                        placeholder="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                    <button onClick={handleStartVerification}>
                        Start Verification
                    </button>
                </>
            ) : (
                <>
                    <p>Recording...</p>
                    <div className="match-counter">
                        Matches: {matchCount} / 4 ✓
                    </div>
                    <div className="similarities">
                        {chunksSimilarities.map((sim, idx) => (
                            <div key={idx} className="similarity-score">
                                Chunk {idx + 1}: {(sim * 100).toFixed(1)}%
                            </div>
                        ))}
                    </div>
                    <button onClick={handleCompleteVerification}>
                        Complete Verification
                    </button>
                </>
            )}

            {isVerified !== null && (
                <div className={`result ${isVerified ? 'success' : 'failure'}`}>
                    {isVerified ? '✅ Verification Successful!' : '❌ Verification Failed'}
                </div>
            )}
        </div>
    );
};

export default VerificationPage;
```

---

## Testing & Validation

### Unit Tests

```javascript
// backend/tests/embedding-merger.test.js
describe('Embedding Merger', () => {
    it('should average embeddings correctly', () => {
        const emb1 = [1, 2, 3];
        const emb2 = [2, 3, 4];
        const result = merge_embeddings([emb1, emb2], 'average');
        expect(result).toEqual([1.5, 2.5, 3.5]);
    });

    it('should normalize merged embeddings', () => {
        const merged = [3, 4];
        const result = normalize_vector(merged);
        expect(vector_magnitude(result)).toBeCloseTo(1.0);
    });
});

// backend/tests/similarity-checker.test.js
describe('Similarity Checker', () => {
    it('should calculate cosine similarity', () => {
        const v1 = [1, 0];
        const v2 = [1, 0];
        const similarity = cosine_similarity(v1, v2);
        expect(similarity).toBeCloseTo(1.0);
    });

    it('should verify user with 4 matches', () => {
        const stored = [0.5, 0.5];
        const chunks = [
            [0.5, 0.5],  // match
            [0.5, 0.4],  // match
            [0.5, 0.48], // match
            [0.5, 0.49], // match
            [0.2, 0.8]   // no match
        ];
        const result = verify_user(chunks, stored, 4, 0.75);
        expect(result.is_verified).toBe(true);
    });
});
```

### Integration Tests

```javascript
// backend/tests/websocket-integration.test.js
describe('WebSocket Integration', () => {
    let io, socket;

    beforeAll((done) => {
        const server = require('../websocket-main');
        io = require('socket.io-client');
        socket = io('http://localhost:5000');
        socket.on('connect', done);
    });

    it('should handle enrollment flow', (done) => {
        socket.emit('enrollment:start', { userId: 'test-user' });
        
        socket.on('ack:enrolled', () => {
            // Send sample audio chunk
            socket.emit('audio:chunk', {
                type: 'enrollment',
                data: new Float32Array(16000)  // 1 second @ 16kHz
            });
        });

        socket.on('ack:chunk', () => {
            socket.emit('enrollment:complete');
        });

        socket.on('enrollment:success', (data) => {
            expect(data.profileId).toBeDefined();
            done();
        });
    });

    afterAll(() => {
        socket.disconnect();
    });
});
```

### End-to-End Tests

```javascript
// frontend/tests/enrollment-verification.e2e.test.js
describe('E2E Enrollment & Verification', () => {
    it('should complete enrollment and verify user', async () => {
        // 1. Enrollment
        await page.click('[data-testid="enroll-button"]');
        await page.waitFor(10000);  // Record for 10 seconds
        await page.click('[data-testid="complete-button"]');
        
        const enrollResult = await page.textContent('[data-testid="result"]');
        expect(enrollResult).toContain('Enrollment successful');

        // 2. Verification
        await page.click('[data-testid="verify-tab"]');
        await page.type('[data-testid="username-input"]', 'test-user');
        await page.click('[data-testid="start-verify-button"]');
        await page.waitFor(10000);  // Record for 10 seconds
        await page.click('[data-testid="complete-verify-button"]');
        
        const verifyResult = await page.textContent('[data-testid="verify-result"]');
        expect(verifyResult).toContain('Verification Successful');
    });
});
```

---

## Performance Considerations

### Optimization Strategies

#### 1. **Embedding Caching**
- Cache embeddings during a session to avoid re-computing
- Use LRU cache with TTL (Time-To-Live) of 30 minutes
- Clear cache on logout

```javascript
class EmbeddingCache {
    constructor(maxSize = 100, ttlMs = 30 * 60 * 1000) {
        this.cache = new Map();
        this.maxSize = maxSize;
        this.ttlMs = ttlMs;
    }

    set(key, value) {
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        const expiry = Date.now() + this.ttlMs;
        this.cache.set(key, { value, expiry });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        if (Date.now() > item.expiry) {
            this.cache.delete(key);
            return null;
        }
        
        return item.value;
    }
}
```

#### 2. **Batch Processing**
- Process multiple verification chunks in parallel
- Use worker threads for CPU-intensive operations

```javascript
const { Worker } = require('worker_threads');

async function processChunksInParallel(chunks, stored_embedding) {
    const worker = new Worker('./embedding-worker.js');
    
    return new Promise((resolve, reject) => {
        worker.on('message', resolve);
        worker.on('error', reject);
        
        worker.postMessage({
            chunks: chunks,
            storedEmbedding: stored_embedding
        });
    });
}
```

#### 3. **Memory Management**
- Implement garbage collection for old sessions
- Monitor memory usage and set limits

```javascript
class SessionCleaner {
    constructor(maxAge = 60 * 60 * 1000) {  // 1 hour
        this.maxAge = maxAge;
        this.sessions = new Map();
        this.startCleaner();
    }

    startCleaner() {
        setInterval(() => {
            const now = Date.now();
            for (const [id, session] of this.sessions) {
                if (now - session.startTime > this.maxAge) {
                    this.sessions.delete(id);
                    console.log(`Cleaned up session: ${id}`);
                }
            }
        }, 5 * 60 * 1000);  // Check every 5 minutes
    }
}
```

#### 4. **Audio Compression**
- Compress audio before transmission (use Opus or AAC)
- Trade-off: Quality vs. bandwidth

#### 5. **Connection Pooling**
- Reuse database connections
- Implement connection pool for MongoDB

#### 6. **Rate Limiting**
- Limit verification attempts per user
- Prevent brute-force attacks

---

## Configuration Constants

```javascript
// backend/config/websocket-config.js
module.exports = {
    // Audio settings
    SAMPLE_RATE: 16000,           // Hz
    ENROLLMENT_CHUNK_DURATION: 1,  // seconds
    VERIFICATION_CHUNK_DURATION: 5, // seconds
    AUDIO_TIMEOUT: 30000,           // ms

    // Embedding settings
    EMBEDDING_DIM: 192,             // ECAPA-VoxCeleb dimension
    EMBEDDING_CACHE_TTL: 30 * 60 * 1000,  // 30 minutes

    // Verification settings
    SIMILARITY_THRESHOLD: 0.75,
    MIN_CHUNK_MATCHES: 4,
    MAX_CHUNK_ATTEMPTS: 8,  // Stop after 8 chunks max

    // Session settings
    SESSION_TIMEOUT: 60 * 60 * 1000,  // 1 hour
    MAX_CONCURRENT_SESSIONS: 100,

    // WebSocket settings
    SOCKET_IO_TRANSPORTS: ['websocket', 'polling'],
    RECONNECTION_ATTEMPTS: 5,

    // Database settings
    DB_COLLECTION: 'voice_profiles',
    LOGS_COLLECTION: 'verification_logs'
};
```

---

## Summary

This plan provides a **complete roadmap** for implementing WebSocket-based real-time voice enrollment and verification. The key components are:

1. **Backend:** WebSocket server, audio processing, embedding operations
2. **Frontend:** React components with real-time feedback
3. **Core Logic:** Embedding merging, similarity checking, verification rules
4. **Database:** MongoDB VoiceProfile and VerificationLog collections
5. **Testing:** Unit, integration, and E2E test strategies
6. **Performance:** Caching, parallel processing, memory management

**Total Estimated Timeline:** 4 weeks  
**Team Size:** 2-3 developers (backend, frontend)

---

## Next Steps

1. Review and approve architecture
2. Set up development environment
3. Begin Phase 1: Backend Setup
4. Implement components incrementally
5. Test thoroughly before production deployment

---

**Document Version:** 1.0  
**Last Reviewed:** February 12, 2026
