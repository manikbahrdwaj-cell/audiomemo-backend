# WebSocket Developer Quick Reference

## Quick Command Reference

### Start Backend
```bash
cd backend
python run.py
# or
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests
```bash
python test_websocket.py
```

### Check Health
```bash
curl http://localhost:8000/ws/health
```

### Check Statistics
```bash
curl http://localhost:8000/ws/stats
```

## Message Format Quick Reference

### Audio Chunk
```json
{
  "type": "audio",
  "data": "base64_encoded_audio"
}
```

### Enroll
```json
{
  "type": "enroll",
  "phone_number": "+1234567890"
}
```

### Verify
```json
{
  "type": "verify",
  "phone_number": "+1234567890"
}
```

### Keep-Alive
```json
{
  "type": "ping"
}
```

### Reset
```json
{
  "type": "reset"
}
```

### Status
```json
{
  "type": "status"
}
```

## JavaScript Client Quick Reference

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws/voice');

// Send audio
ws.send(JSON.stringify({
  type: 'audio',
  data: base64AudioData
}));

// Send enrollment
ws.send(JSON.stringify({
  type: 'enroll',
  phone_number: '+1234567890'
}));

// Send verification
ws.send(JSON.stringify({
  type: 'verify',
  phone_number: '+1234567890'
}));

// Send ping
ws.send(JSON.stringify({ type: 'ping' }));

// Listen for responses
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Type:', message.type);
  console.log('Data:', message.data);
};
```

## Python Client Quick Reference

```python
import asyncio
import websockets
import json
import base64

async def test():
    async with websockets.connect('ws://localhost:8000/ws/voice') as ws:
        # Send ping
        await ws.send(json.dumps({'type': 'ping'}))
        response = await ws.recv()
        print(response)

asyncio.run(test())
```

## Configuration Quick Reference

### Environment Variables
```bash
WS_HEARTBEAT_INTERVAL=30        # Seconds
WS_HEARTBEAT_TIMEOUT=60         # Seconds
WS_MAX_MESSAGE_SIZE=1048576     # Bytes (1MB)
WS_MAX_BUFFER_SIZE=10000000     # Bytes (10MB)
```

### Default Values
- Min audio size: 1000 bytes
- Similarity threshold: 0.75
- Max connections: 100
- Connection timeout: 300s
- Idle timeout: 600s

## Common Error Codes

| Error Type | Description | Solution |
|-----------|-------------|----------|
| `validation_error` | Invalid message format | Check JSON structure |
| `insufficient_audio` | Audio too small | Record longer audio |
| `not_enrolled` | Phone not enrolled | Enroll first |
| `no_audio` | No audio available | Send audio chunks first |
| `buffer_overflow` | Buffer too large | Reset buffer |
| `decode_error` | Can't decode data | Verify base64 encoding |

## Connection States

- `IDLE` - Ready for input
- `PROCESSING` - Processing operation
- `CONNECTED` - Active connection
- `DISCONNECTED` - Disconnected
- `ERROR` - Error state

## Module Structure

```
websocket_handler.py
├── ConnectionState (enum)
├── ClientConnection (class)
├── ConnectionManager (class)
├── WebSocketMessageBuilder (class)
└── WebSocketMessageValidator (class)

websocket_events.py
├── AudioBuffer (class)
└── WebSocketEventHandler (class)

websocket_config.py
├── WebSocketConfig (dataclass)
├── MessageTypeRegistry (class)
└── ResponseTypeRegistry (class)

websocket_monitor.py
├── ConnectionStats (dataclass)
└── WebSocketMonitor (class)
```

## Monitoring Endpoints

```
GET /ws/health           # Health status
GET /ws/stats            # Connection statistics
GET /ws/monitor          # Detailed monitoring data
GET /                    # API health check
```

## Response Format

### Success Response
```json
{
  "type": "verification_result",
  "status": "ok",
  "timestamp": "2024-02-14T10:30:00",
  "data": {
    "phone_number": "+1234567890",
    "similarity_score": 0.87,
    "is_match": true,
    "threshold": 0.75,
    "confidence": 87.0
  }
}
```

### Error Response
```json
{
  "type": "error",
  "status": "error",
  "timestamp": "2024-02-14T10:30:00",
  "error_type": "insufficient_audio",
  "message": "Audio data too small (min: 1000 bytes)"
}
```

## Debugging Tips

### Enable Detailed Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Connection Health
```bash
curl http://localhost:8000/ws/health
```

### Monitor Active Connections
```bash
curl http://localhost:8000/ws/stats
```

### View Detailed Metrics
```bash
curl http://localhost:8000/ws/monitor
```

### Test WebSocket Connection
```bash
python test_websocket.py
```

## Performance Optimization Tips

1. **Optimal audio chunk size**: 50KB
2. **Heartbeat interval**: 30 seconds
3. **Max buffer size**: 10MB
4. **Keep connections alive**: Send pings every 30s

## Testing Checklist

- [ ] Backend starts without errors
- [ ] WebSocket endpoint accessible
- [ ] Connection established
- [ ] Ping-pong working
- [ ] Audio chunks received
- [ ] Enrollment successful
- [ ] Verification working
- [ ] Error handling working
- [ ] Monitor endpoints accessible
- [ ] Health status good

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Connection refused | Start backend with `python run.py` |
| Timeout error | Check network, increase timeout in config |
| Audio processing fails | Verify audio format and size |
| High error rate | Check logs, monitor connection count |
| Memory issues | Reduce buffer size, cleanup old connections |

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| WS | `/ws/voice` | Main WebSocket endpoint |
| GET | `/` | Health check |
| GET | `/ws/health` | WebSocket health status |
| GET | `/ws/stats` | Connection statistics |
| GET | `/ws/monitor` | Detailed monitoring |
| POST | `/enroll` | REST enrollment (file upload) |
| POST | `/verify` | REST verification (file upload) |
| GET | `/check/{phone}` | Check enrollment status |

## External Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **WebSocket Spec**: https://tools.ietf.org/html/rfc6455
- **Python Async**: https://docs.python.org/3/library/asyncio.html
- **MongoDB**: https://www.mongodb.com/

## Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `websocket_handler.py` | Connection management | 218 |
| `websocket_events.py` | Event processing | 332 |
| `websocket_config.py` | Configuration | 145 |
| `websocket_monitor.py` | Monitoring | 265 |
| `main.py` | FastAPI app (updated) | 479 |
| `test_websocket.py` | Test suite | 260 |

## Support

For detailed information:
- See `WEBSOCKET_INFRASTRUCTURE.md` for complete documentation
- See `WEBSOCKET_SETUP_GUIDE.md` for setup instructions
- See `WEBSOCKET_IMPLEMENTATION_SUMMARY.md` for overview
- Check logs: enable with `logging.basicConfig(level=logging.DEBUG)`

---
**Quick Reference Version**: 1.0
**Last Updated**: 2024-02-14
