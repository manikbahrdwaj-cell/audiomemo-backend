# Embedding Operations API Documentation

## REST API Endpoints

### 1. Enroll Voice

Enroll a new voice identity and store its embedding.

**Endpoint:**
```
POST /enroll
```

**Parameters:**
- `phone_number` (form) - Unique identifier (string, required)
- `file` (file) - WAV audio file (required)

**Request Example (curl):**
```bash
curl -X POST http://localhost:8000/enroll \
  -F "phone_number=+1234567890" \
  -F "file=@enrollment_audio.wav"
```

**Request Example (Python):**
```python
import requests

with open("enrollment_audio.wav", "rb") as f:
    files = {"file": f}
    data = {"phone_number": "+1234567890"}
    
    response = requests.post(
        "http://localhost:8000/enroll",
        files=files,
        data=data
    )

print(response.json())
```

**Request Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append("phone_number", "+1234567890");
formData.append("file", audioBlob, "audio.wav");

const response = await fetch("http://localhost:8000/enroll", {
    method: "POST",
    body: formData
});

const result = await response.json();
console.log(result);
```

**Response:**
```json
{
    "success": true,
    "message": "Voice enrolled successfully",
    "phone_number": "+1234567890",
    "vector_id": "507f1f77bcf86cd799439011"
}
```

**Error Responses:**
```json
{
    "detail": "Invalid file type. Please upload a WAV file."
}
```

```json
{
    "detail": "Audio file too small. Please record a longer sample."
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Invalid input
- `500`: Server error

---

### 2. Verify Voice

Verify a voice against an enrolled identity.

**Endpoint:**
```
POST /verify
```

**Parameters:**
- `phone_number` (form) - Phone number to verify against (string, required)
- `file` (file) - WAV audio file (required)

**Request Example (curl):**
```bash
curl -X POST http://localhost:8000/verify \
  -F "phone_number=+1234567890" \
  -F "file=@verification_audio.wav"
```

**Request Example (Python):**
```python
import requests

with open("verification_audio.wav", "rb") as f:
    files = {"file": f}
    data = {"phone_number": "+1234567890"}
    
    response = requests.post(
        "http://localhost:8000/verify",
        files=files,
        data=data
    )

result = response.json()
print(f"Match: {result['is_match']}")
print(f"Similarity: {result['similarity_score']:.4f}")
print(f"Confidence: {1 - abs(result['similarity_score'] - result['threshold']) / (1 - result['threshold']):.1%}")
```

**Request Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append("phone_number", "+1234567890");
formData.append("file", audioBlob, "audio.wav");

const response = await fetch("http://localhost:8000/verify", {
    method: "POST",
    body: formData
});

const result = await response.json();
if (result.is_match) {
    console.log("✓ Voice verified!");
} else {
    console.log("✗ Voice verification failed");
    console.log(`Similarity: ${result.similarity_score.toFixed(4)}`);
}
```

**Response (Match):**
```json
{
    "success": true,
    "phone_number": "+1234567890",
    "similarity_score": 0.8234,
    "is_match": true,
    "threshold": 0.75
}
```

**Response (No Match):**
```json
{
    "success": true,
    "phone_number": "+1234567890",
    "similarity_score": 0.6891,
    "is_match": false,
    "threshold": 0.75
}
```

**Error Responses:**
```json
{
    "detail": "Phone number +1234567890 is not enrolled. Please enroll first."
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Invalid input
- `404`: Phone number not enrolled
- `500`: Server error

---

### 3. Check Enrollment Status

Check if a phone number is enrolled.

**Endpoint:**
```
GET /check/{phone_number}
```

**Parameters:**
- `phone_number` (path) - Phone number to check (string, required)

**Request Example (curl):**
```bash
curl -X GET http://localhost:8000/check/+1234567890
```

**Request Example (Python):**
```python
import requests

response = requests.get(
    "http://localhost:8000/check/+1234567890"
)

result = response.json()
if result['enrolled']:
    print("✓ Phone number is enrolled")
else:
    print("✗ Phone number is not enrolled")
```

**Request Example (JavaScript):**
```javascript
const response = await fetch("http://localhost:8000/check/+1234567890");
const result = await response.json();

if (result.enrolled) {
    console.log("✓ Phone number is enrolled");
} else {
    console.log("✗ Phone number is not enrolled - please enroll first");
}
```

**Response (Enrolled):**
```json
{
    "phone_number": "+1234567890",
    "enrolled": true
}
```

**Response (Not Enrolled):**
```json
{
    "phone_number": "+1234567890",
    "enrolled": false
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Invalid input
- `500`: Server error

---

## WebSocket API

### Connection

**Endpoint:**
```
WS /ws/voice
```

**JavaScript Example:**
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/voice");

ws.onopen = () => {
    console.log("Connected to voice WebSocket");
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log("Received:", message);
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    console.log("Disconnected from voice WebSocket");
};
```

---

### Audio Streaming

Send audio chunks for real-time processing.

**Message Format:**
```json
{
    "type": "audio",
    "data": "<base64_encoded_audio>"
}
```

**JavaScript Example:**
```javascript
// Collect audio from MediaRecorder
const mediaRecorder = new MediaRecorder(stream);
const chunks = [];

mediaRecorder.ondataavailable = (event) => {
    chunks.push(event.data);
};

mediaRecorder.onstop = () => {
    const blob = new Blob(chunks, { type: "audio/wav" });
    
    // Convert to base64
    const reader = new FileReader();
    reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        
        // Send over WebSocket
        ws.send(JSON.stringify({
            type: "audio",
            data: base64
        }));
    };
    reader.readAsDataURL(blob);
};
```

**Response:**
```json
{
    "type": "audio_processed",
    "status": "success",
    "bytes_received": 32000,
    "duration_ms": 1000
}
```

---

### Enrollment via WebSocket

Start enrollment process with accumulated audio.

**Message Format:**
```json
{
    "type": "enroll",
    "phone_number": "+1234567890"
}
```

**JavaScript Example:**
```javascript
ws.send(JSON.stringify({
    type: "enroll",
    phone_number: "+1234567890"
}));
```

**Response (Success):**
```json
{
    "type": "enroll_complete",
    "status": "success",
    "phone_number": "+1234567890",
    "vector_id": "507f1f77bcf86cd799439011",
    "quality_score": 0.78
}
```

**Response (Error):**
```json
{
    "type": "enroll_error",
    "status": "error",
    "error_type": "insufficient_audio",
    "message": "Insufficient audio. Please record more audio."
}
```

---

### Verification via WebSocket

Start verification process with accumulated audio.

**Message Format:**
```json
{
    "type": "verify",
    "phone_number": "+1234567890"
}
```

**JavaScript Example:**
```javascript
ws.send(JSON.stringify({
    type: "verify",
    phone_number": "+1234567890"
}));
```

**Response (Match):**
```json
{
    "type": "verify_complete",
    "status": "success",
    "phone_number": "+1234567890",
    "similarity_score": 0.8234,
    "is_match": true,
    "confidence": 0.82,
    "threshold": 0.75,
    "quality_score": 0.76
}
```

**Response (No Match):**
```json
{
    "type": "verify_complete",
    "status": "success",
    "phone_number": "+1234567890",
    "similarity_score": 0.6234,
    "is_match": false,
    "confidence": 0.62,
    "threshold": 0.75,
    "quality_score": 0.73
}
```

---

### Reset Audio Buffer

Clear the audio buffer for a new recording session.

**Message Format:**
```json
{
    "type": "reset"
}
```

**JavaScript Example:**
```javascript
ws.send(JSON.stringify({
    type: "reset"
}));
```

**Response:**
```json
{
    "type": "reset_acknowledged",
    "status": "ok",
    "message": "Audio buffer cleared"
}
```

---

### Ping (Keep-Alive)

Keep the WebSocket connection alive.

**Message Format:**
```json
{
    "type": "ping"
}
```

**JavaScript Example:**
```javascript
// Send ping every 30 seconds
setInterval(() => {
    ws.send(JSON.stringify({
        type: "ping"
    }));
}, 30000);
```

**Response:**
```json
{
    "type": "pong",
    "status": "ok",
    "timestamp": "2024-02-14T10:30:45.123Z"
}
```

---

### Get Status

Request current connection status.

**Message Format:**
```json
{
    "type": "status"
}
```

**Response:**
```json
{
    "type": "status",
    "status": "ok",
    "audio_buffered_ms": 5000,
    "client_id": "123e4567-e89b-12d3-a456-426614174000",
    "connected": true
}
```

---

## Complete Workflow Examples

### Example 1: REST API Enrollment → Verification

```python
import requests
import time

API_URL = "http://localhost:8000"
PHONE_NUMBER = "+1234567890"

# Step 1: Enroll
print("Enrolling...")
with open("user_enrollment.wav", "rb") as f:
    response = requests.post(
        f"{API_URL}/enroll",
        files={"file": f},
        data={"phone_number": PHONE_NUMBER}
    )

enroll_result = response.json()
if enroll_result["success"]:
    print(f"✓ Enrolled: {enroll_result['vector_id']}")
else:
    print(f"✗ Enrollment failed")
    exit(1)

# Wait a moment
time.sleep(1)

# Step 2: Check enrollment
print("\nChecking enrollment status...")
response = requests.get(f"{API_URL}/check/{PHONE_NUMBER}")
check_result = response.json()

if check_result["enrolled"]:
    print("✓ User is enrolled")
else:
    print("✗ User is not enrolled")
    exit(1)

# Step 3: Verify
print("\nVerifying...")
with open("user_verification.wav", "rb") as f:
    response = requests.post(
        f"{API_URL}/verify",
        files={"file": f},
        data={"phone_number": PHONE_NUMBER}
    )

verify_result = response.json()
print(f"Similarity: {verify_result['similarity_score']:.4f}")
print(f"Threshold: {verify_result['threshold']:.4f}")

if verify_result["is_match"]:
    print("✓ VERIFICATION SUCCESSFUL")
else:
    print("✗ VERIFICATION FAILED")
```

### Example 2: WebSocket Real-Time Verification

```javascript
const PHONE_NUMBER = "+1234567890";
const ws = new WebSocket("ws://localhost:8000/ws/voice");

let audioChunks = [];
let mediaRecorder;

ws.onopen = () => {
    console.log("Connected");
    startRecording();
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === "verify_complete") {
        console.log("Verification result:", message);
        
        if (message.is_match) {
            console.log(`✓ MATCH (confidence: ${(message.confidence * 100).toFixed(1)}%)`);
        } else {
            console.log(`✗ NO MATCH (similarity: ${message.similarity_score.toFixed(4)})`);
        }
    }
};

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
                sendAudioChunk(event.data);
            };
            
            mediaRecorder.start(1000); // Chunk every 1 second
        });
}

function sendAudioChunk(blob) {
    const reader = new FileReader();
    reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        ws.send(JSON.stringify({
            type: "audio",
            data: base64
        }));
    };
    reader.readAsDataURL(blob);
}

function stopRecordingAndVerify() {
    mediaRecorder.stop();
    
    // Give it a moment to finish
    setTimeout(() => {
        ws.send(JSON.stringify({
            type: "verify",
            phone_number: PHONE_NUMBER
        }));
    }, 500);
}
```

### Example 3: Batch Enrollment via REST

```python
import requests
import os
from glob import glob

API_URL = "http://localhost:8000"
AUDIO_DIR = "path/to/audio/files"

# Assume files are named like "+1111111111.wav", "+2222222222.wav", etc.
audio_files = glob(os.path.join(AUDIO_DIR, "+*.wav"))

enrolled = []
failed = []

for audio_file in audio_files:
    phone_number = os.path.basename(audio_file).replace(".wav", "")
    
    print(f"Enrolling {phone_number}...")
    
    try:
        with open(audio_file, "rb") as f:
            response = requests.post(
                f"{API_URL}/enroll",
                files={"file": f},
                data={"phone_number": phone_number}
            )
        
        if response.status_code == 200:
            enrolled.append(phone_number)
            print(f"✓ {phone_number}")
        else:
            failed.append(phone_number)
            print(f"✗ {phone_number}: {response.json()}")
    
    except Exception as e:
        failed.append(phone_number)
        print(f"✗ {phone_number}: {str(e)}")

print(f"\n✓ Enrolled: {len(enrolled)}")
print(f"✗ Failed: {len(failed)}")
```

---

## Error Handling

### Common Error Responses

**Invalid File Type:**
```json
{
    "detail": "Invalid file type. Please upload a WAV file."
}
```

**Audio Too Short:**
```json
{
    "detail": "Audio file too small. Please record a longer sample."
}
```

**Not Enrolled:**
```json
{
    "detail": "Phone number +1234567890 is not enrolled. Please enroll first."
}
```

**Server Error:**
```json
{
    "detail": "Failed to process voice enrollment: [error details]"
}
```

---

## Rate Limiting

WebSocket rate limits (per connection):
- `audio`: 100 messages/sec
- `verify`: 10 messages/sec
- `enroll`: 5 messages/sec
- `ping`: 1000 messages/sec

API rate limits are configured per endpoint.

---

## Performance Tips

1. **Batch Enrollment**: Process multiple users efficiently with batch REST calls
2. **WebSocket**: Use for interactive/real-time applications
3. **Audio Quality**: Use 16-bit, 16kHz mono WAV files
4. **Audio Length**: 2-5 seconds optimal for both enrollment and verification
5. **Caching**: Service automatically caches embeddings

---

## Integration Examples

### React Component

```javascript
import React, { useState } from 'react';

function VoiceAuth() {
    const [phoneNumber, setPhoneNumber] = useState('');
    const [isEnrolled, setIsEnrolled] = useState(null);
    const [verificationResult, setVerificationResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const checkEnrollment = async () => {
        setLoading(true);
        try {
            const response = await fetch(`http://localhost:8000/check/${phoneNumber}`);
            const result = await response.json();
            setIsEnrolled(result.enrolled);
        } finally {
            setLoading(false);
        }
    };

    const handleVerify = async (audioFile) => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('phone_number', phoneNumber);
            formData.append('file', audioFile);

            const response = await fetch('http://localhost:8000/verify', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            setVerificationResult(result);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <input
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="Enter phone number"
            />
            
            <button onClick={checkEnrollment} disabled={loading}>
                Check Enrollment
            </button>

            {isEnrolled !== null && (
                <p>
                    {isEnrolled ? '✓ Enrolled' : '✗ Not Enrolled'}
                </p>
            )}

            {verificationResult && (
                <div>
                    <p>Similarity: {verificationResult.similarity_score.toFixed(4)}</p>
                    <p>
                        Result: {verificationResult.is_match ? '✓ MATCH' : '✗ NO MATCH'}
                    </p>
                </div>
            )}
        </div>
    );
}

export default VoiceAuth;
```

---

## Deployment Checklist

- [ ] MongoDB running and accessible
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Model downloaded (`spkrec-ecapa-voxceleb`)
- [ ] CORS configured for frontend domain
- [ ] Port 8000 available (or configure alternate)
- [ ] GPU enabled if available (CUDA)
- [ ] Test with sample audio files
- [ ] Verify similarity threshold (default 0.75)
- [ ] Set up monitoring/logging
- [ ] Test REST API endpoints
- [ ] Test WebSocket connectivity
- [ ] Load test with concurrent users
