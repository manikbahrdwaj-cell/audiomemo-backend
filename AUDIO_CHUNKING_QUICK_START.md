# Audio Chunking Quick Start

## Quick Overview

**Enrollment**: Split microphone audio into **1-second chunks** (16,000 samples)
**Verification**: Split microphone audio into **5-second chunks** (80,000 samples)

Each chunk is sent via WebSocket to the backend, which merges them all into a single audio array and generates one embedding.

---

## Frontend Quick Start (React)

### Step 1: Import Services

```javascript
import AudioChunkingService from './services/audioChunkingService';
import AudioChunkSenderService from './services/audioChunkSenderService';
import WebSocketClientWrapper from './services/webSocketClientWrapper';
```

### Step 2: Complete Enrollment Example

```javascript
async function enrollUser(phoneNumber) {
  // 1. Setup WebSocket
  const ws = new WebSocketClientWrapper('ws://localhost:8000/ws');
  await ws.connect();

  // 2. Setup audio chunker (1 second chunks for enrollment)
  const chunker = new AudioChunkingService({ mode: 'enrollment' });
  await chunker.initialize();

  // 3. Setup chunk sender
  const sender = new AudioChunkSenderService(ws, { mode: 'enrollment' });
  
  // 4. Start backend session
  await sender.startSession(phoneNumber, 'enrollment');

  // 5. Send chunks as they're captured
  chunker.on('chunk:ready', async (chunk) => {
    console.log(`Sending chunk ${chunk.chunkNumber}`);
    await sender.sendChunk(chunk);
  });

  // 6. Start recording
  chunker.startRecording();

  // ... recording happens ...

  // 7. After 10-15 seconds, stop and finalize
  chunker.stopRecording();
  await sender.finalizeSession(); // Merges chunks and generates embedding
}
```

### Step 3: Complete Verification Example

```javascript
async function verifyUser(phoneNumber) {
  // Same as enrollment, but with 'verification' mode
  const ws = new WebSocketClientWrapper('ws://localhost:8000/ws');
  await ws.connect();

  // 5-second chunks for verification
  const chunker = new AudioChunkingService({ mode: 'verification' });
  await chunker.initialize();

  const sender = new AudioChunkSenderService(ws, { mode: 'verification' });
  await sender.startSession(phoneNumber, 'verification');

  chunker.on('chunk:ready', (chunk) => {
    sender.sendChunk(chunk);
  });

  chunker.startRecording();
  // ... after ~10-15 seconds ...
  chunker.stopRecording();
  const result = await sender.finalizeSession();
  
  console.log('Verification result:', result);
}
```

### Step 4: React Component

```javascript
import React, { useState } from 'react';

function VoiceAuth() {
  const [isRecording, setIsRecording] = useState(false);

  const handleEnroll = async () => {
    setIsRecording(true);
    await enrollUser('+1234567890');
    setIsRecording(false);
  };

  const handleVerify = async () => {
    setIsRecording(true);
    const result = await verifyUser('+1234567890');
    setIsRecording(false);
    alert(`Verification: ${result.verification_result ? 'PASSED' : 'FAILED'}`);
  };

  return (
    <div>
      <button onClick={handleEnroll} disabled={isRecording}>
        {isRecording ? 'Recording...' : 'Enroll'}
      </button>
      <button onClick={handleVerify} disabled={isRecording}>
        {isRecording ? 'Recording...' : 'Verify'}
      </button>
    </div>
  );
}

export default VoiceAuth;
```

---

## Backend Quick Start (Python)

### Step 1: Import Handler

```python
from websocket_audio_chunk_handler import get_audio_chunk_handler
from audio_chunk_receiver import get_chunk_receiver
```

### Step 2: Add to WebSocket Endpoint

In your `main.py`:

```python
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    connection = await connection_manager.connect(websocket, client_id)
    audio_handler = get_audio_chunk_handler()
    
    try:
        while True:
            message_text = await websocket.receive_text()
            message = json.loads(message_text)
            
            # Handle audio chunks
            if message.get('type') == 'audio':
                response = await audio_handler.handle_audio_message(message, connection)
                await connection.send_json(response)
            
            # ... handle other message types ...
    
    except WebSocketDisconnect:
        # Cleanup
        session_id = connection.get_metadata('chunk_session_id')
        if session_id:
            audio_handler.chunk_receiver.cleanup_session(session_id)
        connection_manager.disconnect(client_id)
```

### Step 3: Manual Testing

```python
from audio_chunk_receiver import get_chunk_receiver
import numpy as np

# Create receiver instance
receiver = get_chunk_receiver()

# Create session
session = receiver.create_session(
    phone_number='+1234567890',
    mode='enrollment'
)

# Simulate receiving 5 chunks of 1 second each
for chunk_num in range(5):
    # Create mock audio (random data)
    audio_data = np.random.randn(16000).astype(np.float32)
    
    # Add chunk
    success, error = receiver.add_chunk(
        session_id=session.session_id,
        chunk_number=chunk_num,
        audio_data=audio_data,
        sample_rate=16000,
        duration_ms=1000
    )
    print(f"Chunk {chunk_num}: {success}")

# Merge and generate embedding
success, embedding, error = receiver.process_session(session.session_id)

if success:
    print(f"✅ Success! Embedding shape: {embedding.shape}")
    print(f"Embedding: {embedding[:5]}...")  # First 5 values
else:
    print(f"❌ Error: {error}")
```

---

## Data Flow

### What Happens on Frontend

```
1. User clicks "Start Enrollment"
   ↓
2. Browser requests microphone permission
   ↓
3. Audio is captured continuously
   ↓
4. Chunker waits for 16,000 samples (1 second)
   ↓
5. Chunk is ready → sent to backend via WebSocket
   ↓
6. Process repeats for each chunk
   ↓
7. User clicks "Stop"
   ↓
8. Last partial chunk is sent
   ↓
9. Message sent: "finalize_session"
```

### What Happens on Backend

```
1. Receive chunk #1 (16,000 samples)
   ↓
2. Create session and buffer chunk
   ↓
3. Receive chunk #2 (16,000 samples)
   ↓
   ... (repeat for all chunks) ...
   ↓
N. Receive finalize_session message
   ↓
N+1. Merge all chunks:
     [chunk1] + [chunk2] + ... = [merged_audio]
   ↓
N+2. Generate embedding from merged audio:
     embedding = model(merged_audio)
   ↓
N+3. Send embedding back to frontend
```

---

## Chunk Sizes Reference

| Mode | Chunk Duration | Samples | Bytes | Purpose |
|------|----------------|---------|-------|---------|
| Enrollment | 1 second | 16,000 | ~64KB | Frequent enrollment chunks |
| Verification | 5 seconds | 80,000 | ~320KB | Longer verification samples |

---

## Common Issues & Solutions

### Issue: No audio chunks being sent

**Solution**: Check browser console for permission errors. Ensure microphone is allowed.

```javascript
try {
  await chunker.initialize();
} catch (error) {
  if (error.name === 'NotAllowedError') {
    console.error('Microphone permission denied');
  }
}
```

### Issue: Chunks not received by backend

**Solution**: Verify WebSocket is connected and audio_data is properly encoded.

```python
# Backend debug
if not message.get('audio_data'):
    return {'status': 'error', 'error': 'Missing audio_data'}
```

### Issue: Embedding generation fails

**Solution**: Ensure audio data is valid float32 and sample count matches.

```python
# Validate audio
if not isinstance(audio_data, np.ndarray):
    audio_data = np.array(audio_data, dtype=np.float32)

if audio_data.dtype != np.float32:
    audio_data = audio_data.astype(np.float32)
```

---

## Testing the Complete Flow

### Test 1: Frontend Only (No Backend)

```javascript
// Just test that chunks are created
const chunker = new AudioChunkingService({ mode: 'enrollment' });
await chunker.initialize();

let chunkCount = 0;
chunker.on('chunk:ready', (chunk) => {
  chunkCount++;
  console.log(`Got chunk ${chunk.chunkNumber}: ${chunk.sampleCount} samples`);
});

chunker.startRecording();
setTimeout(() => {
  chunker.stopRecording();
  console.log(`Total chunks: ${chunkCount}`);
}, 5000);
```

### Test 2: Backend Only (Batch Processing)

```python
# Simulate 3 chunks of enrollment
receiver = get_chunk_receiver()
session = receiver.create_session('+1234567890', 'enrollment')

chunks = []
for i in range(3):
    # Create audio chunk
    audio = np.random.randn(16000).astype(np.float32)
    chunks.append(audio)
    receiver.add_chunk(session.session_id, i, audio)

# Process
success, embedding, error = receiver.process_session(session.session_id)
print(f"Success: {success}, Embedding shape: {embedding.shape if success else 'N/A'}")
```

### Test 3: Complete End-to-End

1. Start Python backend: `python main.py`
2. Start React frontend: `npm start`
3. Open http://localhost:3000
4. Click "Enroll" and speak for 5 seconds
5. Check response has embedding and status ✅

---

## Next Steps

1. **Add persistence**: Store embeddings in database (MongoDB)
2. **Add matching**: Compare embeddings for verification
3. **Add UI feedback**: Show progress, errors, and results
4. **Add error recovery**: Retry failed chunks
5. **Add batch processing**: Handle multiple concurrent sessions

See `AUDIO_CHUNKING_WEBSOCKET_INTEGRATION_GUIDE.md` for full details.
