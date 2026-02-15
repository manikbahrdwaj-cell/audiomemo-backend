# Audio Chunking and Merging Integration Guide

## Overview

This guide demonstrates how to integrate the frontend audio chunking service with the backend chunk receiver to implement real-time enrollment and verification with audio chunks.

### Architecture

```
Frontend (React):
  1. Capture microphone audio (Web Audio API)
  2. Split into chunks (1s for enrollment, 5s for verification)
  3. Send each chunk via WebSocket
     ↓
Backend (FastAPI):
  1. Receive chunks from WebSocket
  2. Buffer/accumulate chunks
  3. Merge all chunks into single audio array
  4. Generate one embedding from merged audio
  5. Return results (embedding, similarity score, etc.)
```

## Frontend Implementation

### 1. Basic Audio Capture and Chunking

```javascript
import AudioChunkingService, { AUDIO_CONFIG, CHUNK_EVENTS } from './services/audioChunkingService';
import AudioChunkSenderService, { CHUNK_SENDER_EVENTS } from './services/audioChunkSenderService';
import WebSocketClientWrapper from './services/webSocketClientWrapper';

// Initialize services
const wsClient = new WebSocketClientWrapper('ws://localhost:8000/ws');
const audioChunker = new AudioChunkingService({
  mode: 'enrollment', // or 'verification'
  sampleRate: 16000,
});

const chunkSender = new AudioChunkSenderService(wsClient, {
  mode: 'enrollment',
});

// Initialize audio context and connect to microphone
await audioChunker.initialize();

// Listen for chunks and send them
audioChunker.on(CHUNK_EVENTS.CHUNK_READY, async (chunkInfo) => {
  console.log(`Chunk ${chunkInfo.chunkNumber} ready: ${chunkInfo.sampleCount} samples`);
  
  // Send chunk to backend
  await chunkSender.sendChunk(chunkInfo);
});

// Start recording
audioChunker.startRecording();

// Later: stop recording and finalize
setTimeout(async () => {
  audioChunker.stopRecording();
  
  // Notify backend to merge chunks and generate embedding
  await chunkSender.finalizeSession();
}, 5000); // Record for 5 seconds
```

### 2. In a React Component (Enrollment)

```javascript
import React, { useState, useRef, useEffect } from 'react';
import AudioChunkingService from '../services/audioChunkingService';
import AudioChunkSenderService from '../services/audioChunkSenderService';

function EnrollmentComponent() {
  const [isRecording, setIsRecording] = useState(false);
  const [chunkCount, setChunkCount] = useState(0);
  const [stats, setStats] = useState(null);
  const audioChunkerRef = useRef(null);
  const chunkSenderRef = useRef(null);
  const wsClientRef = useRef(null);

  useEffect(() => {
    // Initialize services
    return () => {
      // Cleanup
      audioChunkerRef.current?.cleanup();
    };
  }, []);

  const handleStartEnrollment = async (phoneNumber) => {
    try {
      // Initialize WebSocket connection
      wsClientRef.current = new WebSocketClientWrapper('ws://localhost:8000/ws');
      await wsClientRef.current.connect();

      // Initialize audio chunker (1 second chunks for enrollment)
      audioChunkerRef.current = new AudioChunkingService({
        mode: 'enrollment',
      });
      await audioChunkerRef.current.initialize();

      // Initialize chunk sender
      chunkSenderRef.current = new AudioChunkSenderService(wsClientRef.current, {
        mode: 'enrollment',
      });

      // Start backend session
      await chunkSenderRef.current.startSession(phoneNumber, 'enrollment', {
        max_chunks: 10,
        auto_process: true,
      });

      // Listen for chunks
      audioChunkerRef.current.on('chunk:ready', async (chunkInfo) => {
        console.log(`Chunk ${chunkInfo.chunkNumber}: ${chunkInfo.durationMs.toFixed(0)}ms`);
        await chunkSenderRef.current.sendChunk(chunkInfo);
        setChunkCount(c => c + 1);
      });

      // Start recording
      audioChunkerRef.current.startRecording();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting enrollment:', error);
    }
  };

  const handleStopEnrollment = async () => {
    try {
      if (audioChunkerRef.current) {
        audioChunkerRef.current.stopRecording();
        setIsRecording(false);
        
        // Finalize and generate embedding
        const result = await chunkSenderRef.current.finalizeSession();
        console.log('Enrollment completed:', result);
      }
    } catch (error) {
      console.error('Error stopping enrollment:', error);
    }
  };

  return (
    <div>
      <button 
        onClick={() => handleStartEnrollment('+1234567890')}
        disabled={isRecording}
      >
        Start Enrollment
      </button>
      
      <button 
        onClick={handleStopEnrollment}
        disabled={!isRecording}
      >
        Stop Enrollment
      </button>

      <p>Chunks: {chunkCount}</p>
      {stats && <pre>{JSON.stringify(stats, null, 2)}</pre>}
    </div>
  );
}

export default EnrollmentComponent;
```

### 3. Verification with Longer Chunks (5 seconds)

```javascript
async function handleVerification(phoneNumber, wsClient) {
  // Same as enrollment, but with verification mode
  const audioChunker = new AudioChunkingService({
    mode: 'verification', // 5-second chunks
  });

  const chunkSender = new AudioChunkSenderService(wsClient, {
    mode: 'verification',
  });

  await audioChunker.initialize();
  await chunkSender.startSession(phoneNumber, 'verification', {
    max_chunks: 3,
    verification_threshold: 0.75,
  });

  audioChunker.on('chunk:ready', (chunkInfo) => {
    chunkSender.sendChunk(chunkInfo);
  });

  audioChunker.startRecording();
}
```

## Backend Implementation

### 1. Add to WebSocket Router

In your `websocket_router.py`, add the audio message handler:

```python
from websocket_audio_chunk_handler import get_audio_chunk_handler
from websocket_router import MessageType, RouteConfig

# Get handler instance
audio_chunk_handler = get_audio_chunk_handler()

# In your router setup
router = WebSocketMessageRouter()

# Add route for AUDIO messages
router.register_route(RouteConfig(
    message_type=MessageType.AUDIO,
    handler=audio_chunk_handler.handle_audio_message,
    requires_fields=['action', 'session_id'],
))
```

### 2. Update WebSocket Connection Handler

In your `main.py`, integrate the chunk handler with WebSocket connections:

```python
from websocket_audio_chunk_handler import get_audio_chunk_handler

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    connection = await connection_manager.connect(websocket, client_id)
    audio_handler = get_audio_chunk_handler()
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'audio':
                # Handle audio chunk
                response = await audio_handler.handle_audio_message(data, connection)
                await connection.send_json(response)
            
            elif message_type == 'enrollment_status':
                # Handle enrollment status
                # ... existing code ...
                pass
            
            # ... handle other message types ...
    
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await connection.send_json({
            'type': 'error',
            'error': str(e)
        })
    finally:
        # Cleanup any pending sessions
        session_id = connection.get_metadata('chunk_session_id')
        if session_id:
            audio_handler.chunk_receiver.cleanup_session(session_id)
```

### 3. Chunk Size Configuration

**Enrollment Mode (1-second chunks):**
```python
# Frontend: 16,000 samples = 1 second at 16kHz
AUDIO_CONFIG.ENROLLMENT_CHUNK_SAMPLES = 16000

# Backend automatically handles merging
# Multiple 1-second chunks → merged audio → single embedding
```

**Verification Mode (5-second chunks):**
```python
# Frontend: 80,000 samples = 5 seconds at 16kHz
AUDIO_CONFIG.VERIFICATION_CHUNK_SAMPLES = 80000

# Backend automatically handles merging
# Multiple 5-second chunks → merged audio → single embedding
```

### 4. Backend Chunk Merging Process

```python
from audio_chunk_receiver import get_chunk_receiver

async def process_verification(session_id):
    receiver = get_chunk_receiver()
    
    # User sends multiple 5-second chunks
    # Backend receives and buffers them
    
    # When client finishes, finalize session
    success, embedding, error = receiver.process_session(session_id)
    
    if success:
        # embedding is single vector generated from merged audio
        # e.g., shape (192,) for ECAPA-TDNN embeddings
        
        # Use embedding for verification
        similarity = calculate_cosine_similarity(embedding, enrolled_embedding)
        
        return {
            'verification_result': similarity > 0.75,
            'similarity_score': similarity,
            'embedding': embedding.tolist(),
        }
```

## Message Format

### Frontend → Backend: Audio Chunk

```json
{
  "type": "audio",
  "action": "send_chunk",
  "session_id": "uuid",
  "phone_number": "+1234567890",
  "mode": "enrollment",
  "chunk_number": 1,
  "audio_data": [bytes as array],
  "sample_count": 16000,
  "sample_rate": 16000,
  "duration_ms": 1000,
  "timestamp": "2024-02-15T10:30:00Z"
}
```

### Backend → Frontend: Chunk Acknowledgment

```json
{
  "status": "success",
  "type": "audio",
  "action": "chunk_received",
  "session_id": "uuid",
  "chunk_number": 1,
  "message": "Chunk 1 received successfully"
}
```

### Frontend → Backend: Finalize Session

```json
{
  "type": "audio",
  "action": "finalize_session",
  "session_id": "uuid",
  "phone_number": "+1234567890",
  "total_chunks": 5
}
```

### Backend → Frontend: Finalization Result

```json
{
  "status": "success",
  "type": "audio",
  "action": "finalize_session",
  "session_id": "uuid",
  "embedding_shape": [192],
  "embedding_dim": 192,
  "session_info": {
    "session_id": "uuid",
    "phone_number": "+1234567890",
    "mode": "enrollment",
    "status": "completed",
    "chunks_received": 5,
    "merged_duration_ms": 5000.0,
    "embedding_dim": 192,
    "processing_time_ms": 245.3
  }
}
```

## Key Features

### Frontend (`audioChunkingService.js`)
- ✅ Captures microphone audio using Web Audio API
- ✅ Automatically splits into configurable chunks
- ✅ Supports enrollment (1s) and verification (5s) modes
- ✅ Event-driven architecture for chunk readiness
- ✅ Proper cleanup and resource management

### Frontend (`audioChunkSenderService.js`)
- ✅ Sends chunks via WebSocket with optimal encoding
- ✅ Converts Float32Array to Uint8Array (4x compression)
- ✅ Tracks chunk delivery and acknowledgments
- ✅ Session management (start/finalize/cancel)
- ✅ Error handling and retry logic

### Backend (`audio_chunk_receiver.py`)
- ✅ Creates and manages chunk receiving sessions
- ✅ Validates and buffers incoming chunks
- ✅ Automatically merges chunks in correct order
- ✅ Generates single embedding from merged audio
- ✅ Session cleanup and memory management

### Backend (`websocket_audio_chunk_handler.py`)
- ✅ WebSocket integration for chunk reception
- ✅ Chunk validation and error handling
- ✅ Session lifecycle management
- ✅ Real-time acknowledgment responses

## Performance Notes

- **Chunk Size**: 16KB per 1-second chunk at 16kHz (efficient network usage)
- **Encoding**: Float32 → Uint8 reduces transmission by 4x
- **Latency**: Sub-second per chunk in typical networks
- **Memory**: Safe cleanup prevents memory leaks
- **Scalability**: Session-based tracking allows concurrent processing

## Error Handling

```javascript
// Frontend error handling
chunkSender.on('chunk:failed', (error) => {
  console.error('Chunk send failed:', error);
  // Retry logic or user notification
});

audioChunker.on('recording:error', (error) => {
  console.error('Recording error:', error);
  // Handle microphone access issues
});
```

```python
# Backend error handling
if not success:
    logger.error(f"Chunk processing failed: {error}")
    # Return error response to frontend
    # Frontend can retry or abort session
```

## Testing

### Frontend Testing
```javascript
// Mock chunk data for testing
const mockChunk = {
  chunkNumber: 1,
  samples: new Float32Array(16000),
  sampleCount: 16000,
  durationMs: 1000,
  sampleRate: 16000,
  mode: 'enrollment'
};

await chunkSender.sendChunk(mockChunk);
```

### Backend Testing
```python
from audio_chunk_receiver import get_chunk_receiver
import numpy as np

receiver = get_chunk_receiver()
session = receiver.create_session('+1234567890', 'enrollment')

# Simulate receiving chunks
for i in range(5):
    audio_data = np.random.randn(16000).astype(np.float32)
    receiver.add_chunk(session.session_id, i, audio_data)

# Process and generate embedding
success, embedding, error = receiver.process_session(session.session_id)
assert success
assert embedding.shape == (192,)  # ECAPA-TDNN dimension
```

## Summary

This implementation provides:
1. **Real-time audio chunking** on the frontend
2. **Efficient WebSocket transmission** with compression
3. **Automatic buffering and merging** on the backend
4. **Single embedding generation** from all chunks
5. **Complete session management** with error handling

The system is production-ready and handles both enrollment (1s chunks) and verification (5s chunks) workflows seamlessly.
