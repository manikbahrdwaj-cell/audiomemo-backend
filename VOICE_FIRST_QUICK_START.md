# Voice-First Verification - Quick Start Guide

## What Changed?

**Before (Phase 1):**
```
User Input: Phone Number → Voice Recording → Backend Verifies Against That Number
```

**Now (Phase 2):**
```
Voice Recording → Backend Automatically Finds Matching Phone Number → Creates Session
```

---

## Frontend Implementation

### Step 1: Create WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/voice');

ws.onopen = () => console.log('Connected');
ws.onerror = (error) => console.error('Connection error:', error);
```

### Step 2: Record Voice
```javascript
async function recordVoice() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    const chunks = [];
    
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
    mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        sendAudioToBackend(audioBlob);
    };
    
    mediaRecorder.start();
    
    // Stop after 5 seconds (adjust as needed)
    setTimeout(() => mediaRecorder.stop(), 5000);
}

function sendAudioToBackend(audioBlob) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64Audio = btoa(new Uint8Array(e.target.result)
            .reduce((data, byte) => data + String.fromCharCode(byte), ''));
        
        ws.send(JSON.stringify({
            type: 'audio',
            data: base64Audio
        }));
    };
    reader.readAsArrayBuffer(audioBlob);
}
```

### Step 3: Initiate Verification
```javascript
function startVerification() {
    // SIMPLE! No phone number needed
    ws.send(JSON.stringify({
        type: 'verify'
    }));
}
```

### Step 4: Handle Response
```javascript
ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    
    if (response.type === 'verification_success') {
        // SUCCESS - Show matched phone number
        const matchedPhone = response.data.phone_number;
        const sessionId = response.data.session_id;
        
        showSuccessMessage(
            `Your voice is matched with this mobile number: ${matchedPhone}`
        );
        
        // Store session for future use
        localStorage.setItem('sessionId', sessionId);
        localStorage.setItem('phoneNumber', matchedPhone);
        
    } else if (response.error_type === 'no_match') {
        // FAILURE - No matching voice found
        showErrorMessage(response.message);
    } else if (response.type === 'chunk_progress') {
        // Update progress bar
        updateProgress(response.payload);
    }
};
```

---

## HTML UI Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Voice Authentication</title>
    <style>
        .container { max-width: 500px; margin: 50px auto; }
        button { padding: 10px 20px; margin: 10px 5px; }
        .message { margin-top: 20px; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Voice Authentication</h1>
        
        <button onclick="recordVoice()">🎤 Record Voice</button>
        <button onclick="startVerification()">✓ Verify</button>
        
        <div id="progress" style="display:none;">
            <progress id="progressBar" value="0" max="100"></progress>
        </div>
        
        <div id="message" class="message" style="display:none;"></div>
    </div>

    <script>
        const ws = new WebSocket('ws://localhost:8000/ws/voice');
        
        ws.onopen = () => {
            console.log('✓ Connected to voice server');
        };
        
        ws.onmessage = handleResponse;
        
        async function recordVoice() {
            // Implementation from above
        }
        
        function startVerification() {
            ws.send(JSON.stringify({ type: 'verify' }));
        }
        
        function handleResponse(event) {
            const response = JSON.parse(event.data);
            const messageDiv = document.getElementById('message');
            
            if (response.type === 'verification_success') {
                messageDiv.className = 'message success';
                messageDiv.innerHTML = response.data.message;
                messageDiv.style.display = 'block';
                
            } else if (response.error_type === 'no_match') {
                messageDiv.className = 'message error';
                messageDiv.innerHTML = response.message;
                messageDiv.style.display = 'block';
            }
        }
    </script>
</body>
</html>
```

---

## Backend Integration

### Check if User is Verified
```python
from database import get_verified_session

def is_user_verified(session_id: str) -> bool:
    session = get_verified_session(session_id)
    return session and session['session_status'] == 'verified'

def get_verified_phone(session_id: str) -> Optional[str]:
    session = get_verified_session(session_id)
    return session['phone_number'] if session else None
```

### Create LangChain Conversation
```python
from session_service import get_verified_session_manager

def create_conversation(session_id: str):
    session_manager = get_verified_session_manager()
    session = session_manager.get_session(session_id)
    
    if session and session.is_session_valid(session_id):
        phone_number = session.phone_number
        langgraph_session_id = session.langgraph_session_id
        
        # Use these in your LangChain conversation
        return {
            'phone': phone_number,
            'langgraph_session': langgraph_session_id
        }
```

---

## Expected Responses

### Success
```json
{
    "type": "verification_success",
    "status": "success",
    "data": {
        "message": "Your voice is matched with this mobile number: +1234567890",
        "phone_number": "+1234567890",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "similarity_score": 0.85,
        "confidence": 85.0
    }
}
```

### Failure
```json
{
    "type": "error",
    "error_type": "no_match",
    "message": "No record found for this voice in the system."
}
```

---

## Testing Checklist

- [ ] User can record voice without entering phone number
- [ ] Backend successfully identifies matching voice
- [ ] Success message shows correct phone number
- [ ] Session ID is returned and stored
- [ ] Failed verification shows "No record found" message
- [ ] Multiple users can be verified in same session
- [ ] Progress updates are sent during processing
- [ ] Connection recovers after temporary errors

---

## Configuration

### Adjust Sensitivity
```python
# In websocket_events.py
SIMILARITY_THRESHOLD = 0.75  # Range: 0.0 to 1.0
# Lower = more lenient (more false positives)
# Higher = stricter (more false negatives)
```

### Recommended Settings
- **High Security**: 0.85+
- **Standard**: 0.75-0.84
- **Lenient**: 0.65-0.74

---

## Common Issues

### Issue: "No record found" with correct user
**Solution:** Lower SIMILARITY_THRESHOLD slightly (try 0.70)

### Issue: Verification accepts wrong users
**Solution:** Increase SIMILARITY_THRESHOLD (try 0.85)

### Issue: Too slow
**Solution:** Check audio quality, ensure embeddings are cached

---

## Performance Tips

1. **Keep audio chunks reasonable** (3-5 seconds)
2. **Test with multiple users** to find optimal threshold
3. **Cache embeddings** for better performance
4. **Use HTTPS/WSS** in production
5. **Monitor logs** for bottlenecks

---

## Next Steps

1. ✅ Record voice (no phone number)
2. ✅ Get matched phone number automatically
3. ✅ Create verified session
4. → Use session for LangChain conversation
5. → Track user preferences per session
6. → Build personalized experiences

---

## Full Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Voice-First Authentication</title>
</head>
<body>
    <h1>Voice Authentication</h1>
    <button id="recordBtn">Record Voice</button>
    <button id="verifyBtn" disabled>Verify</button>
    <div id="result"></div>

    <script>
        const ws = new WebSocket('ws://localhost:8000/ws/voice');
        let hasAudio = false;
        
        document.getElementById('recordBtn').onclick = async () => {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream);
            const chunks = [];
            
            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = () => {
                const blob = new Blob(chunks);
                const reader = new FileReader();
                reader.onload = e => {
                    const data = btoa(new Uint8Array(e.target.result)
                        .reduce((d, b) => d + String.fromCharCode(b), ''));
                    ws.send(JSON.stringify({
                        type: 'audio',
                        data: data
                    }));
                    hasAudio = true;
                    document.getElementById('verifyBtn').disabled = false;
                };
                reader.readAsArrayBuffer(blob);
                stream.getTracks().forEach(t => t.stop());
            };
            
            recorder.start();
            setTimeout(() => recorder.stop(), 5000);
        };
        
        document.getElementById('verifyBtn').onclick = () => {
            ws.send(JSON.stringify({ type: 'verify' }));
        };
        
        ws.onmessage = event => {
            const data = JSON.parse(event.data);
            const resultDiv = document.getElementById('result');
            
            if (data.type === 'verification_success') {
                resultDiv.innerHTML = `<h2 style="color:green">${data.data.message}</h2>`;
            } else {
                resultDiv.innerHTML = `<h2 style="color:red">${data.message}</h2>`;
            }
        };
    </script>
</body>
</html>
```

This is all you need to get started with voice-first verification! 🎉
