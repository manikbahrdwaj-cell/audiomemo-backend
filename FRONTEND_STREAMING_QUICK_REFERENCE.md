# Frontend WebSocket Audio Streaming - Quick Reference

## Files Created/Updated

### Core Files
1. **audioRecorder.js** (Updated)
   - Real-time WebSocket streaming
   - Audio chunk buffering and downsampling
   - Local recording buffer
   - Returns: `{ start, stop, getIsRecording, flushStreamData, notifyStreamComplete, getStreamStats, sendStreamChunk }`

2. **websocketClient.js** (New)
   - WebSocket connection management
   - Message handling registry
   - Automatic reconnection
   - Returns: `{ connect, disconnect, sendAudioChunk, sendVerification, sendEnrollment, sendMessage, on, isConnected, getState }`

3. **streamingRecorder.js** (New)
   - High-level integration wrapper
   - Combines audio + WebSocket
   - Simple unified API
   - Returns: `{ initialize, startRecording, stopRecording, verifyVoice, enrollVoice, resetBuffer, getStats, disconnect }`

### Example Components
4. **StreamingVerificationExample.jsx** (New)
   - Full React component example
   - UI with recording, verification controls
   - Real-time statistics display

5. **StreamingVerification.css** (New)
   - Component styling

## Quick Start

### 1. Basic Setup (Recommended)

```javascript
import { createStreamingRecorder } from '@/utils/streamingRecorder';

async function startVerification() {
  const recorder = createStreamingRecorder({
    onVerificationResult: (result) => {
      console.log('Verified:', result.is_match ? 'YES' : 'NO');
    }
  });

  await recorder.initialize();
  await recorder.startRecording();
  
  // After 5 seconds or manual stop
  const blob = await recorder.stopRecording();
  
  recorder.verifyVoice('+1234567890');
  recorder.disconnect();
}
```

### 2. Advanced Usage (Direct Control)

```javascript
import { createAudioRecorder } from '@/utils/audioRecorder';
import { createWebSocketClient } from '@/services/websocketClient';

const wsClient = createWebSocketClient('ws://localhost:8000/ws');
await wsClient.connect();

const recorder = createAudioRecorder({
  websocket: wsClient.websocket,
  onChunkSent: (info) => console.log(`Sent: ${info.size}B`)
});

await recorder.start();
await new Promise(r => setTimeout(r, 5000));
const blob = await recorder.stop();
```

## API Cheat Sheet

### createStreamingRecorder(options)
```javascript
const recorder = createStreamingRecorder({
  websocketUrl: 'wss://api.example.com/ws',  // optional
  onWSOpen: () => {},                         // WebSocket connected
  onWSClose: () => {},                        // WebSocket disconnected
  onWSError: (err) => {},                     // WebSocket error
  onChunkStreamed: (info) => {},              // Chunk sent
  onVerificationResult: (result) => {},       // Verification done
  onEnrollmentResult: (result) => {},         // Enrollment done
  onServerError: (err) => {}                  // Server error
});

// Methods
await recorder.initialize();        // Setup recorder
await recorder.startRecording();    // Start streaming
const blob = await recorder.stopRecording();  // Stop streaming
recorder.verifyVoice(phoneNumber);  // Request verification
recorder.enrollVoice(phoneNumber);  // Request enrollment
recorder.resetBuffer();             // Clear server buffer
recorder.getStats();                // Get streaming stats
recorder.disconnect();              // Cleanup
```

### createWebSocketClient(url, options)
```javascript
const ws = createWebSocketClient(url, {
  maxConnectionAttempts: 5,
  reconnectDelay: 3000,
  onOpen: () => {},
  onClose: () => {},
  onError: (err) => {},
  onMessage: (msg) => {}
});

// Methods
await ws.connect();                 // Connect
ws.disconnect();                    // Disconnect
ws.sendAudioChunk(base64Audio);     // Send audio
ws.sendVerification(phoneNumber);   // Send verify request
ws.sendEnrollment(phoneNumber);     // Send enroll request
ws.sendMessage(obj);                // Send custom message
ws.sendPing();                      // Keep-alive
ws.sendReset();                     // Reset buffer
ws.on('messageType', handler);      // Register handler
ws.isConnected();                   // Check connection
ws.getState();                      // Get state
```

### createAudioRecorder(options)
```javascript
const recorder = createAudioRecorder({
  websocket: wsConnection,          // WebSocket instance
  onChunkSent: (info) => {},        // Chunk streamed callback
  onError: (error) => {}            // Error callback
});

// Methods
await recorder.start();             // Start recording
const blob = await recorder.stop(); // Stop recording
recorder.getIsRecording();          // Check recording state
recorder.flushStreamData();         // Send buffered audio
recorder.notifyStreamComplete();    // Notify server
recorder.getStreamStats();          // Get stats
```

## WebSocket Message Format

### Audio Chunk
```javascript
{
  type: 'audio',
  data: 'base64EncodedPCM16...',
  sequence: 0,
  timestamp: 1234567890
}
```

### Verification Request
```javascript
{
  type: 'verify',
  phone_number: '+1234567890',
  timestamp: 1234567890
}
```

### Enrollment Request
```javascript
{
  type: 'enroll',
  phone_number: '+1234567890',
  timestamp: 1234567890
}
```

### Verification Result
```javascript
{
  type: 'verification_result',
  data: {
    phone_number: '+1234567890',
    is_match: true,
    confidence: 95.5,
    similarity_score: 0.95,
    threshold: 0.75
  }
}
```

## Configuration

### Environment Variables
```bash
# .env
REACT_APP_WS_URL=wss://api.example.com
```

### Audio Settings (in audioRecorder.js)
```javascript
const TARGET_SAMPLE_RATE = 16000;        // Output sample rate
const NUM_CHANNELS = 1;                  // Mono only
const STREAM_CHUNK_SIZE = 4096;          // Samples per buffer
const STREAM_BUFFER_THRESHOLD = 16000;   // ~1 second before streaming
```

## Common Patterns

### React Hook
```javascript
function useStreamingRecorder(onVerificationResult) {
  const [recording, setRecording] = useState(false);
  const [connected, setConnected] = useState(false);
  const recorderRef = useRef(null);

  useEffect(() => {
    const init = async () => {
      recorderRef.current = createStreamingRecorder({
        onWSOpen: () => setConnected(true),
        onWSClose: () => setConnected(false),
        onVerificationResult
      });
      await recorderRef.current.initialize();
    };
    init();
    return () => recorderRef.current?.disconnect();
  }, []);

  return {
    async start() {
      await recorderRef.current.startRecording();
      setRecording(true);
    },
    async stop() {
      await recorderRef.current.stopRecording();
      setRecording(false);
    },
    verify: (num) => recorderRef.current.verifyVoice(num),
    recording,
    connected
  };
}
```

### Error Handling
```javascript
try {
  await recorder.initialize();
  await recorder.startRecording();
} catch (error) {
  if (error.message.includes('WebSocket')) {
    console.error('Connection failed:', error);
  } else if (error.message.includes('getUserMedia')) {
    console.error('Microphone access denied:', error);
  } else {
    console.error('Unknown error:', error);
  }
}
```

### Connection Status Monitoring
```javascript
const wsClient = createWebSocketClient(url);

wsClient.on('error', (msg) => {
  console.error('Server error:', msg);
  if (msg.error === 'buffer_overflow') {
    wsClient.sendReset();
  }
});

wsClient.waitForConnection(5000)
  .then(() => console.log('Ready'))
  .catch(() => console.error('Connection timeout'));
```

## Performance Tips

1. **Reduce Streaming Frequency**
   - Increase `STREAM_BUFFER_THRESHOLD` for lower network overhead
   - Trade-off: Higher latency

2. **Reduce Audio Latency**
   - Decrease `STREAM_CHUNK_SIZE` for lower latency processing
   - Trade-off: Higher CPU overhead

3. **Monitor Connection**
   - Use `getStats()` to monitor stream quality
   - Implement automatic retry on failure

4. **Resource Cleanup**
   - Always call `disconnect()` when done
   - Clean up event listeners

## Debugging

### Enable Console Logging
```javascript
// All operations log to console
const recorder = createStreamingRecorder();
console.log(recorder.getStats());
```

### Monitor WebSocket Traffic
```javascript
const wsClient = createWebSocketClient(url);
wsClient.on('*', (msg) => console.log('WS:', msg.type, msg));
```

### Audio Diagnostics
```javascript
const stats = recorder.getStreamStats();
console.table({
  chunksStreamed: stats.chunksStreamed,
  bufferSize: stats.bufferSize,
  wsConnected: stats.websocketConnected,
  wsState: stats.websocketState
});
```

## Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|:------:|:-------:|:------:|:----:|
| WebSocket | ✅ | ✅ | ✅ | ✅ |
| getUserMedia | ✅ | ✅ | ✅ | ✅ |
| ScriptProcessor | ✅ | ✅ | ✅ | ✅ |
| Base64 | ✅ | ✅ | ✅ | ✅ |

## Troubleshooting

### "WebSocket not connected"
- Ensure backend WebSocket server is running
- Check firewall/proxy settings
- Verify correct URL

### "Microphone access denied"
- User rejected permission - ask again
- HTTPS required in production
- Check browser permissions settings

### "Audio quality low"
- Check microphone hardware
- Disable noise suppression if too aggressive
- Use wired microphone for better quality

### "Stream disconnects randomly"
- Check network stability
- Increase heartbeat interval
- Monitor server logs

## Related Documentation

- [FRONTEND_WEBSOCKET_STREAMING.md](FRONTEND_WEBSOCKET_STREAMING.md) - Full guide
- Backend: `websocket_handler.py`, `websocket_events.py`
- API: `services/api.js` (HTTP fallback)
