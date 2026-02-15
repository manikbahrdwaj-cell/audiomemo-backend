# Frontend WebSocket Audio Streaming Guide

## Overview

The frontend audio streaming implementation provides real-time WebSocket streaming of audio chunks from the browser microphone to the backend for processing. This enables low-latency voice verification and enrollment.

## Architecture

### Components

1. **audioRecorder.js** - Core audio recording and streaming engine
   - Captures audio from microphone at source sample rate
   - Downsamples audio chunks in real-time
   - Streams chunks via WebSocket as they're recorded
   - Maintains local recording buffer for final blob export

2. **websocketClient.js** - WebSocket connection management
   - Handles WebSocket connection lifecycle
   - Provides message sending API
   - Implements reconnection logic
   - Manages message handlers registry

3. **streamingRecorder.js** - High-level integration layer
   - Combines audio recording and WebSocket streaming
   - Provides simple API for applications
   - Handles event callbacks
   - Manages connection and resource cleanup

## Key Features

### Real-Time Streaming
- Audio chunks are streamed as they're recorded
- ~1 second buffer threshold before sending
- Base64 encoding for WebSocket transmission
- Sequence numbering for chunk tracking

### Dual-Channel Support
- **Streaming Channel**: Real-time chunks sent to WebSocket
- **Local Storage Channel**: Full audio buffered for final blob export

### Downsampling
- Source audio: 48kHz (or device native rate)
- Target rate: 16kHz (required by ECAPA-TDNN model)
- Linear interpolation method for quality

### WebSocket Protocol
- Message types: `audio`, `verify`, `enroll`, `audio_complete`, `ping`, `reset`
- JSON format with metadata
- Base64-encoded PCM16 audio data

## API Reference

### Audio Recorder

```javascript
import { createAudioRecorder } from './utils/audioRecorder';

const recorder = createAudioRecorder({
  websocket: wsConnection,  // WebSocket instance (optional)
  onChunkSent: (info) => {  // Called when chunk sent
    console.log(`Chunk ${info.sequence}: ${info.size} bytes`);
  },
  onError: (error) => {     // Called on error
    console.error(error);
  }
});

// Start recording
await recorder.start();

// Stop recording and get final WAV blob
const audioBlob = await recorder.stop();

// Get current stats
const stats = recorder.getStreamStats();

// Manual stream flush and completion
recorder.flushStreamData();
recorder.notifyStreamComplete();
```

### WebSocket Client

```javascript
import { createWebSocketClient, getWebSocketUrl } from './services/websocketClient';

const wsClient = createWebSocketClient(getWebSocketUrl(), {
  onOpen: () => console.log('Connected'),
  onClose: () => console.log('Disconnected'),
  onError: (err) => console.error('Error:', err),
  onMessage: (msg) => console.log('Message:', msg)
});

// Connect
await wsClient.connect();

// Register message handlers
wsClient.on('verification_result', (msg) => {
  console.log('Verification result:', msg.data);
});

// Send verification
wsClient.sendVerification('+1234567890');

// Send enrollment
wsClient.sendEnrollment('+1234567890');

// Check connection status
if (wsClient.isConnected()) {
  console.log('Connected');
}

// Get connection state
console.log(wsClient.getState()); // 'OPEN', 'CLOSED', etc.

// Graceful disconnect
wsClient.disconnect();
```

### Streaming Recorder (Recommended)

```javascript
import { createStreamingRecorder } from './utils/streamingRecorder';

const streamingRecorder = await createStreamingRecorder({
  websocketUrl: 'ws://localhost:8000/ws',  // Optional
  onWSOpen: () => console.log('WebSocket connected'),
  onWSClose: () => console.log('WebSocket disconnected'),
  onChunkStreamed: (info) => {
    console.log(`Streamed: ${info.size} bytes`);
  },
  onVerificationResult: (result) => {
    console.log('Verification:', result);
  },
  onEnrollmentResult: (result) => {
    console.log('Enrollment:', result);
  }
});

// Initialize
await streamingRecorder.initialize();

// Start recording and streaming
await streamingRecorder.startRecording();

// Perform operations during recording
streamingRecorder.resetBuffer();

// Stop recording
const audioBlob = await streamingRecorder.stopRecording();

// Request verification/enrollment
streamingRecorder.verifyVoice('+1234567890');

// Get statistics
const stats = streamingRecorder.getStats();

// Cleanup
streamingRecorder.disconnect();
```

## Usage Examples

### Basic Streaming Verification

```javascript
import { createStreamingRecorder } from './utils/streamingRecorder';

async function streamingVerification(phoneNumber) {
  const streamingRecorder = createStreamingRecorder({
    onVerificationResult: (result) => {
      console.log('Verification Result:', {
        isMatch: result.is_match,
        confidence: result.confidence,
        score: result.similarity_score
      });
    }
  });

  try {
    await streamingRecorder.initialize();
    await streamingRecorder.startRecording();
    
    // Record for 5 seconds
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    await streamingRecorder.stopRecording();
    streamingRecorder.verifyVoice(phoneNumber);
  } catch (error) {
    console.error('Verification failed:', error);
  } finally {
    streamingRecorder.disconnect();
  }
}
```

### React Component Hook

```javascript
import { useState, useEffect, useRef } from 'react';
import { createStreamingRecorder } from './utils/streamingRecorder';

function useStreamingRecorder() {
  const [recording, setRecording] = useState(false);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState(null);
  const recorderRef = useRef(null);

  useEffect(() => {
    const initializeRecorder = async () => {
      if (!recorderRef.current) {
        recorderRef.current = createStreamingRecorder({
          onWSOpen: () => setConnected(true),
          onWSClose: () => setConnected(false),
          onChunkStreamed: () => {
            setStats(recorderRef.current.getStats());
          }
        });
        await recorderRef.current.initialize();
      }
    };

    initializeRecorder();

    return () => {
      if (recorderRef.current) {
        recorderRef.current.disconnect();
      }
    };
  }, []);

  const startRecording = async () => {
    if (recorderRef.current && connected) {
      await recorderRef.current.startRecording();
      setRecording(true);
    }
  };

  const stopRecording = async () => {
    if (recorderRef.current) {
      const blob = await recorderRef.current.stopRecording();
      setRecording(false);
      return blob;
    }
  };

  const verify = (phoneNumber) => {
    if (recorderRef.current && connected) {
      recorderRef.current.verifyVoice(phoneNumber);
    }
  };

  return {
    startRecording,
    stopRecording,
    verify,
    recording,
    connected,
    stats
  };
}
```

## Message Flow

### Verification Flow

```
Client                          Server
  |                               |
  |-- WebSocket Connect --------->|
  |<------ Connection ACK --------|
  |                               |
  |-- start recording --------> [Audio Streaming begins]
  |-- Audio Chunk 1 (base64) ---->|
  |-- Audio Chunk 2 (base64) ---->|  [Accumulates chunks]
  |-- Audio Chunk N (base64) ---->|
  |                               |
  |-- audio_complete msg -------->|  [Signals end]
  |                               |
  |-- verify message ------------>|  [Requests verification]
  |                               |  [Processes accumulated audio]
  |                               |  [Generates embedding]
  |                               |  [Compares with enrollment]
  |<-- verification_result ------|  [Sends result]
  |                               |
```

## Performance Considerations

### Streaming Chunk Size
- **Current**: ~1 second of audio (STREAM_BUFFER_THRESHOLD: 16000 samples)
- **Reason**: Balances latency vs network efficiency
- **Adjustable**: Modify STREAM_BUFFER_THRESHOLD in audioRecorder.js

### Downsampling
- Linear interpolation provides good quality
- CPU overhead is minimal
- Alternative: Implement Sinc interpolation for higher quality

### WebSocket Buffer
- Default max message size: 1MB
- PCM16 at 16kHz: ~32KB per second
- Supports ~30+ seconds per chunk

### Connection Optimization
- Heartbeat/ping every 30 seconds (configurable)
- Automatic reconnection with exponential backoff
- Max 5 connection attempts before failure

## Configuration

### Environment Variables

```bash
# WebSocket URL (defaults to relative path)
REACT_APP_WS_URL=wss://api.example.com

# Or set per instance
const wsClient = createWebSocketClient('wss://api.example.com/ws');
```

### Audio Recorder Settings

Edit `audioRecorder.js`:
```javascript
const TARGET_SAMPLE_RATE = 16000;        // Target downsample rate
const NUM_CHANNELS = 1;                  // Mono audio
const STREAM_CHUNK_SIZE = 4096;          // Samples per audioproces buffer
const STREAM_BUFFER_THRESHOLD = 16000;   // Samples before streaming
```

### WebSocket Client Settings

```javascript
const wsClient = createWebSocketClient(url, {
  maxConnectionAttempts: 5,   // Max reconnection tries
  reconnectDelay: 3000        // Milliseconds between retries
});
```

## Error Handling

### Common Issues

1. **WebSocket Connection Failed**
   - Check backend server is running
   - Verify WebSocket endpoint is correct
   - Check firewall/proxy settings
   - Review browser console for CORS issues

2. **Microphone Access Denied**
   - User rejected permission
   - Check HTTPS requirement (most browsers)
   - Verify unsecured context is allowed in development

3. **Audio Quality Issues**
   - Check browser audio input settings
   - Verify microphone device capabilities
   - Noise suppression might be too aggressive

4. **Streaming Timeout**
   - Check network connectivity
   - Verify server is processing messages
   - Check server logs for errors

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| WebSocket | ✅ | ✅ | ✅ | ✅ |
| getUserMedia | ✅ | ✅ | ✅ | ✅ |
| AudioContext | ✅ | ✅ | ✅ | ✅ |
| ScriptProcessor | ✅ | ✅ | ✅ | ✅ |
| Base64 | ✅ | ✅ | ✅ | ✅ |

## Debugging

### Enable Logging

```javascript
// In audioRecorder.js or services
const DEBUG = true;

if (DEBUG) {
  console.log('Audio stats:', recorder.getStreamStats());
  console.log('WebSocket state:', wsClient.getState());
}
```

### Monitor WebSocket Traffic

```javascript
wsClient.on('*', (msg) => {
  console.log('WS Message:', msg.type, msg);
});
```

### Audio Diagnostics

```javascript
const stats = streamingRecorder.getStats();
console.table({
  chunksStreamed: stats.chunksStreamed,
  bufferSize: stats.bufferSize,
  isStreaming: stats.isStreaming,
  websocketState: stats.websocketState
});
```

## Next Steps

- Implement retry logic for failed verifications
- Add audio level meter UI
- Implement progressive audio quality adjustment
- Add support for multiple concurrent streams
- Implement client-side audio preprocessing (VAD, etc.)

## Related Files

- Backend: `websocket_handler.py`, `websocket_events.py`
- Frontend: `audioRecorder.js`, `websocketClient.js`, `streamingRecorder.js`
- API: `services/api.js` (fallback HTTP endpoint)
