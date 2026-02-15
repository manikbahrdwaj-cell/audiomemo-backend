# WebSocket Infrastructure Setup Guide

## Quick Start

### 1. Installation
All dependencies are already in `requirements.txt`:
- `fastapi` - Web framework
- `websockets` - WebSocket support
- `uvicorn` - ASGI server

Run:
```bash
cd backend
pip install -r requirements.txt
```

### 2. File Structure
The WebSocket infrastructure consists of 4 main modules:

```
backend/
├── main.py                      # FastAPI app and WebSocket endpoint
├── websocket_handler.py         # Connection management
├── websocket_events.py          # Event processing and audio handling
├── websocket_config.py          # Configuration and registries
└── websocket_monitor.py         # Performance monitoring
```

### 3. Starting the Server
```bash
cd backend
python run.py
# or
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The WebSocket endpoint will be available at: `ws://localhost:8000/ws/voice`

### 4. WebSocket Endpoints

#### Main Endpoint
- **URL**: `ws://localhost:8000/ws/voice`
- **Purpose**: Real-time voice biometric operations
- **Description**: Accepts audio chunks, enrollment, and verification requests

#### Monitoring Endpoints
- **GET** `/ws/stats` - Get connection statistics
- **GET** `/ws/monitor` - Get detailed monitoring data
- **GET** `/ws/health` - Get infrastructure health status

### 5. Basic Frontend Integration

```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Voice Test</title>
</head>
<body>
    <h1>Voice Biometric WebSocket Test</h1>
    
    <button onclick="connectWebSocket()">Connect</button>
    <button onclick="sendPing()">Send Ping</button>
    <button onclick="enrollVoice()">Enroll Voice</button>
    <button onclick="verifyVoice()">Verify Voice</button>
    <button onclick="resetBuffer()">Reset Buffer</button>
    
    <div id="messages" style="border: 1px solid #ccc; padding: 10px; margin-top: 20px; height: 300px; overflow-y: auto;">
    </div>

    <script>
        let ws = null;

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws/voice');
            
            ws.onopen = () => {
                addMessage('Connected to WebSocket');
            };
            
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                addMessage('Received: ' + JSON.stringify(message, null, 2));
            };
            
            ws.onerror = (error) => {
                addMessage('Error: ' + error);
            };
            
            ws.onclose = () => {
                addMessage('Disconnected');
            };
        }

        function sendPing() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }

        function enrollVoice() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'enroll',
                    phone_number: '+1234567890'
                }));
            }
        }

        function verifyVoice() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'verify',
                    phone_number: '+1234567890'
                }));
            }
        }

        function resetBuffer() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'reset' }));
            }
        }

        function addMessage(msg) {
            const div = document.getElementById('messages');
            div.innerHTML += '<p>' + new Date().toLocaleTimeString() + ': ' + msg + '</p>';
            div.scrollTop = div.scrollHeight;
        }
    </script>
</body>
</html>
```

### 6. Configuration

#### Environment Variables
Create a `.env` file in the backend directory:

```bash
# Heartbeat settings (seconds)
WS_HEARTBEAT_INTERVAL=30
WS_HEARTBEAT_TIMEOUT=60

# Message and buffer limits (bytes)
WS_MAX_MESSAGE_SIZE=1048576    # 1MB
WS_MAX_BUFFER_SIZE=10000000    # 10MB
```

#### Config File
Edit `websocket_config.py` for advanced settings:
- Connection timeouts
- Similarity threshold
- Rate limiting
- Feature flags

### 7. Monitoring

#### Check Connection Statistics
```bash
curl http://localhost:8000/ws/stats
```

Response:
```json
{
  "active_connections": 2,
  "aggregate_stats": {
    "total_connections": 5,
    "total_messages": 150,
    "total_errors": 2,
    "active_connections": 2
  },
  "health_status": {
    "status": "healthy",
    "active_connections": 2
  }
}
```

#### Check Infrastructure Health
```bash
curl http://localhost:8000/ws/health
```

#### Get Detailed Monitoring
```bash
curl http://localhost:8000/ws/monitor
```

### 8. Testing with Python

```python
import asyncio
import websockets
import json
import base64

async def test_websocket():
    uri = "ws://localhost:8000/ws/voice"
    
    async with websockets.connect(uri) as websocket:
        # Send ping
        await websocket.send(json.dumps({"type": "ping"}))
        response = await websocket.recv()
        print("Ping response:", response)
        
        # Send audio chunk
        audio_data = b"\x00" * 5000  # Dummy audio
        audio_b64 = base64.b64encode(audio_data).decode()
        await websocket.send(json.dumps({
            "type": "audio",
            "data": audio_b64
        }))
        response = await websocket.recv()
        print("Audio response:", response)

asyncio.run(test_websocket())
```

### 9. Message Flow Diagrams

#### Enrollment Flow
```
Client                          Server
  |                               |
  |------- Connect WS ----------->|
  |                               |
  |------- audio chunk ---------->|
  |<----- audio_received ---------|
  |                               |
  |------- audio chunk ---------->|
  |<----- audio_received ---------|
  |                               |
  |------- enroll -------->|
  |                  [Generate embedding]
  |                  [Store in DB]
  |<----- enrollment_success -----|
  |
```

#### Verification Flow
```
Client                          Server
  |                               |
  |------- Connect WS ----------->|
  |                               |
  |------- audio chunk ---------->|
  |<----- audio_received ---------|
  |                               |
  |------- audio chunk ---------->|
  |<----- audio_received ---------|
  |                               |
  |------- verify -------->|
  |                  [Generate embedding]
  |                  [Compare scores]
  |<----- verification_result -----|
  |
```

### 10. Troubleshooting

#### Connection Refused
- Make sure backend is running: `python run.py`
- Check if port 8000 is free
- Verify firewall settings

#### WebSocket Connection Fails
- Check browser console for errors
- Enable debug logging in logger
- Verify CORS is properly configured

#### Audio Processing Fails
- Ensure audio format is correct (WAV/PCM)
- Check audio size meets minimum requirement (1000 bytes)
- Verify embedding generation is working

#### Memory Issues
- Monitor buffer sizes
- Clean up old historical stats periodically
- Monitor active connection count

### 11. Production Considerations

1. **Enable WSS (WebSocket Secure)**
   ```python
   # In main.py, use HTTPS/WSS
   uvicorn.run(app, host="0.0.0.0", port=443, ssl_keyfile="...", ssl_certfile="...")
   ```

2. **Enable Compression**
   - Edit `websocket_config.py`
   - Set `enable_compression: True`

3. **Add Authentication**
   - Implement JWT token validation in connection handler
   - Add to `websocket_handler.py`

4. **Rate Limiting**
   - Set `enable_rate_limiting: True`
   - Define limits per client

5. **Load Balancing**
   - Use multiple server instances
   - Implement sticky sessions
   - Use Redis for shared state

6. **Monitoring**
   - Set up Prometheus metrics export
   - Create dashboard in Grafana
   - Alert on high error rates

### 12. Next Steps

1. ✅ WebSocket Infrastructure Created
2. ✅ Connection Management
3. ✅ Event Handling
4. ✅ Monitoring & Statistics
5. **TODO**: Add Authentication
6. **TODO**: Add Rate Limiting
7. **TODO**: Add Compression
8. **TODO**: Add Prometheus Metrics
9. **TODO**: Deploy to Production

### 13. Documentation Files

- `WEBSOCKET_INFRASTRUCTURE.md` - Complete documentation
- `WEBSOCKET_GUIDE.md` - Original guide (existing)
- This file - Quick setup guide

### 14. Support

For issues or questions:
1. Check the logs: `tail -f backend.log`
2. Review monitoring data: `curl http://localhost:8000/ws/stats`
3. Check health status: `curl http://localhost:8000/ws/health`

---
Created: 2024-02-14
Last Updated: 2024-02-14
Version: 1.0.0
