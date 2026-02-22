# Backend Implementation Guide: Multi-Sample Enrollment Support

## Overview
This guide provides the backend implementation details needed to support the new 5-sample voice enrollment from the upgraded frontend.

## 🔄 WebSocket Message Flow

### Receiving Audio Chunks (per sample)
```
Frontend sends multiple audio messages with sample_number:

Sample 1:
  - Message 1: {type: "audio", sample_number: 1, chunk_number: 0, total_chunks: 8, ...}
  - Message 2: {type: "audio", sample_number: 1, chunk_number: 1, total_chunks: 8, ...}
  - ... (up to 8 chunks)

Sample 2:
  - Message 1: {type: "audio", sample_number: 2, chunk_number: 0, total_chunks: 7, ...}
  - ... (up to 7 chunks)

... (repeat for samples 3, 4, 5)

Then final message:
  {type: "enroll", phone_number: "+1-555-0000", sample_count: 5}
```

## 📁 Storage Structure

### Option 1: Individual Sample Files (Recommended for flexibility)
```
enrollment_samples/
├── phone_number_hash/
│   ├── sample_1.wav
│   ├── sample_2.wav
│   ├── sample_3.wav
│   ├── sample_4.wav
│   └── sample_5.wav
```

### Option 2: In-Memory During Processing
```python
samples_buffer = {
    1: b'',  # Sample 1 bytes
    2: b'',  # Sample 2 bytes
    3: b'',  # Sample 3 bytes
    4: b'',  # Sample 4 bytes
    5: b'',  # Sample 5 bytes
}
```

## 🛠️ Implementation Steps

### Step 1: Update WebSocket Handler State

```python
# In your WebSocket connection handler
class VoiceEnrollmentHandler:
    def __init__(self):
        self.audio_chunks = {}  # {sample_number: [chunk_data, ...]}
        self.current_phone = None
        self.expected_samples = 0
        
    async def handle_message(self, data):
        message = json.loads(data)
        
        if message['type'] == 'audio':
            self.store_audio_chunk(message)
        elif message['type'] == 'enroll':
            await self.process_enrollment(message)
```

### Step 2: Store Audio Chunks

```python
async def store_audio_chunk(self, message):
    """
    Store audio chunk from specific sample
    
    Args:
        message: WebSocket message with audio chunk
    """
    sample_num = message.get('sample_number', 1)
    chunk_number = message.get('chunk_number', 0)
    is_last = message.get('is_last', False)
    data = message.get('data', '')
    
    # Initialize sample buffer if needed
    if sample_num not in self.audio_chunks:
        self.audio_chunks[sample_num] = b''
    
    # Append chunk data (already in base64, need to decode if binary)
    try:
        chunk_bytes = base64.b64decode(data)
        self.audio_chunks[sample_num] += chunk_bytes
        
        logger.debug(f"Stored chunk {chunk_number} for sample {sample_num} "
                    f"({len(chunk_bytes)} bytes). Last: {is_last}")
    except Exception as e:
        logger.error(f"Error storing audio chunk: {e}")
        await self.send_error(f"Failed to store audio chunk: {str(e)}")
```

### Step 3: Reconstruct Audio and Process

```python
async def process_enrollment(self, message):
    """
    Process enrollment with all 5 samples
    
    Args:
        message: Enroll message with phone_number and sample_count
    """
    phone_number = message.get('phone_number')
    expected_sample_count = message.get('sample_count', 5)
    
    self.current_phone = phone_number
    self.expected_samples = expected_sample_count
    
    try:
        # Validate all samples received
        received_samples = len(self.audio_chunks)
        if received_samples != expected_sample_count:
            raise ValueError(
                f"Expected {expected_sample_count} samples, "
                f"received {received_samples}"
            )
        
        # Convert raw audio bytes to WAV format for each sample
        samples_wav = []
        for sample_num in range(1, expected_sample_count + 1):
            if sample_num not in self.audio_chunks:
                raise ValueError(f"Sample {sample_num} not received")
            
            # Reconstruct WAV file
            wav_data = convert_pcm_to_wav(
                self.audio_chunks[sample_num],
                sample_rate=16000,
                channels=1
            )
            samples_wav.append(wav_data)
        
        # Send progress
        await self.send_progress(f"Processing {expected_sample_count} samples")
        
        # Option A: Merge all samples
        merged_audio = merge_audio_samples(samples_wav)
        enrollment_result = await enroll_voice_samples(
            phone_number=phone_number,
            audio_blob=merged_audio,
            sample_count=expected_sample_count,
            individual_samples=samples_wav  # Keep originals for reference
        )
        
        # Option B: Or process individually and average embeddings
        # embeddings = [extract_embedding(s) for s in samples_wav]
        # avg_embedding = np.mean(embeddings, axis=0)
        # enrollment_result = store_enrollment(phone_number, avg_embedding, samples_wav)
        
        # Send success
        await self.send_enrollment_success(enrollment_result)
        
    except Exception as e:
        logger.error(f"Enrollment failed: {e}")
        await self.send_error(f"Enrollment failed: {str(e)}")
    finally:
        self.cleanup()
```

### Step 4: Audio Merging (Option A)

```python
def merge_audio_samples(audio_list):
    """
    Merge multiple WAV audio files into one
    
    Args:
        audio_list: List of WAV file bytes
    
    Returns:
        Merged WAV file bytes
    """
    import wave
    import io
    
    frames_list = []
    
    for audio_data in audio_list:
        # Read each WAV file
        with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            frames_list.append(frames)
    
    # Concatenate all frames
    merged_frames = b''.join(frames_list)
    
    # Write to new WAV file
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav_out:
        # Match first sample's parameters
        with wave.open(io.BytesIO(audio_list[0]), 'rb') as template:
            params = template.getparams()
        
        wav_out.setparams(params)
        wav_out.writeframes(merged_frames)
    
    return output.getvalue()
```

### Step 5: Store Enrollment with Metadata

```python
async def enroll_voice_samples(
    phone_number,
    audio_blob,
    sample_count,
    individual_samples=None
):
    """
    Enroll voice with multiple samples
    
    Args:
        phone_number: User identifier
        audio_blob: Merged or processed audio
        sample_count: Number of samples (typically 5)
        individual_samples: Optional raw samples for backup
    
    Returns:
        Enrollment result with vector_id
    """
    try:
        # Extract embedding
        embedding = extract_embedding(audio_blob)
        
        # Create enrollment record
        enrollment = {
            'phone_number': phone_number,
            'embedding': embedding.tolist(),  # Store as list for JSON
            'sample_count': sample_count,
            'enrollment_date': datetime.now().isoformat(),
            'audio_hash': hashlib.sha256(audio_blob).hexdigest(),
            'status': 'active',
            'metadata': {
                'multi_sample': True,
                'samples_used': sample_count,
                'merged': True,  # Indicate merged audio
            }
        }
        
        # Store in database
        vector_id = await db.store_enrollment(phone_number, enrollment)
        
        # Optionally store individual samples for quality analysis
        if individual_samples:
            await db.store_backup_samples(phone_number, individual_samples)
        
        return {
            'message': f'All {sample_count} voice samples enrolled successfully!',
            'vector_id': vector_id,
            'sample_count': sample_count
        }
        
    except Exception as e:
        logger.error(f"Failed to enroll voice samples: {e}")
        raise
```

### Step 6: Send Progress Updates

```python
async def send_progress(self, message, sample_num=None):
    """Send progress update to frontend"""
    progress_msg = {
        'type': 'chunk_progress',
        'payload': {
            'status': message,
            'sample_number': sample_num,
            'timestamp': datetime.now().isoformat()
        }
    }
    await self.send(json.dumps(progress_msg))
```

### Step 7: Send Success Response

```python
async def send_enrollment_success(self, result):
    """Send enrollment success message"""
    response = {
        'type': 'enrollment_success',
        'payload': {
            'message': result.get('message'),
            'vector_id': result.get('vector_id'),
            'sample_count': result.get('sample_count')
        }
    }
    await self.send(json.dumps(response))
```

## 🔄 Example Integration (FastAPI + WebSockets)

```python
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class EnrollmentWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.enrollment_handlers = {}
    
    async def handle_enrollment_ws(self, websocket: WebSocket):
        """Handle new WebSocket connection for enrollment"""
        await websocket.accept()
        connection_id = f"{websocket.client.host}:{websocket.client.port}"
        
        handler = VoiceEnrollmentHandler()
        handler.websocket = websocket
        self.enrollment_handlers[connection_id] = handler
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message['type'] == 'audio':
                    await handler.store_audio_chunk(message)
                
                elif message['type'] == 'enroll':
                    await handler.process_enrollment(message)
                    # Connection complete
                    break
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.send_json({
                'type': 'error',
                'payload': {'error_message': str(e)}
            })
        
        finally:
            del self.enrollment_handlers[connection_id]
            await websocket.close()

# Route handler
@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    manager = EnrollmentWebSocketManager()
    await manager.handle_enrollment_ws(websocket)
```

## 📊 Database Schema Updates

### MongoDB Example
```javascript
// Collection: voice_enrollments
{
  _id: ObjectId(),
  phone_number: "+1-555-0000",
  embedding: [0.123, 0.456, ...],  // 512-dim ECAPA-TDNN
  sample_count: 5,
  enrollment_date: ISODate("2024-02-20T10:30:00Z"),
  audio_hash: "sha256_hash",
  status: "active",
  metadata: {
    multi_sample: true,
    samples_used: 5,
    merged: true,
    platform: "frontend-v2"
  },
  updated_at: ISODate("2024-02-20T10:30:00Z")
}

// Optional: Store sample metadata
// Collection: enrollment_samples
{
  _id: ObjectId(),
  phone_number: "+1-555-0000",
  sample_number: 1,
  duration: 4.5,  // seconds
  audio_hash: "sha256_hash",
  stored_at: ISODate("2024-02-20T10:30:00Z")
}
```

### PostgreSQL Example
```sql
-- Update enrollment table
ALTER TABLE voice_enrollments 
ADD COLUMN sample_count INTEGER DEFAULT 1,
ADD COLUMN is_multi_sample BOOLEAN DEFAULT false,
ADD COLUMN audio_hash VARCHAR(255);

-- New table for sample tracking
CREATE TABLE enrollment_samples (
  id SERIAL PRIMARY KEY,
  phone_number VARCHAR(255),
  sample_number INTEGER,
  duration FLOAT,
  audio_hash VARCHAR(255),
  stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (phone_number) REFERENCES voice_enrollments(phone_number)
);
```

## ✅ Validation Checklist

- [ ] WebSocket handler accepts `sample_number` in audio messages
- [ ] All 5 samples are collected before processing
- [ ] Audio chunks are properly reassembled per sample
- [ ] Audio is converted from PCM to WAV format correctly
- [ ] Embedding extraction handles 5-sample merged audio
- [ ] Enrollment stored with `sample_count: 5` metadata
- [ ] Progress messages sent to frontend
- [ ] Error handling for incomplete samples
- [ ] Database supports multi-sample enrollment
- [ ] Backward compatibility maintained (if needed)

## 🐛 Common Issues & Solutions

### Issue: "Expected 5 samples, received 4"
**Cause**: One sample didn't send its audio chunks
**Solution**: Validate frontend recording completed; check network

### Issue: "Failed to reconstruct WAV"
**Cause**: PCM to WAV conversion failed
**Solution**: Verify sample rate (16000) and channel count (1) match

### Issue: "Embedding extraction failed"
**Cause**: Audio quality or format issue
**Solution**: Log raw audio size; verify WAV validity

### Issue: WebSocket timeout
**Cause**: Processing taking too long
**Solution**: Increase timeout; implement streaming validation

---

**Version**: 1.0  
**Status**: Ready for Implementation  
**Last Updated**: February 2026
