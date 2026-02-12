# Audio Chunker Documentation

## Overview

The **Audio Chunker** is a robust Node.js utility module for managing real-time audio streaming in WebSocket applications. It provides efficient chunking, buffering, validation, and conversion of audio data with full event support.

## Features

### Core Functionality
- **Efficient Chunking**: Split audio streams into manageable chunks
- **Buffer Management**: Automatic buffer accumulation with configurable limits
- **Real-time Streaming**: Process audio chunks as they arrive
- **Audio Validation**: Automated validation of audio data
- **WAV Conversion**: Convert audio buffers to WAV format for compatibility
- **Event-based Notifications**: Track chunks, errors, and progress
- **Statistics & Metrics**: Detailed audio statistics and analytics

### Advanced Features
- **Backwards Compatibility**: Works seamlessly with existing WebSocket handlers
- **Configurable**: Customizable chunk sizes, sample rates, and limits
- **Error Handling**: Comprehensive error handling with event emission
- **Stream Manager**: High-level abstraction for streaming operations
- **Duration Estimation**: Calculate estimated audio duration
- **Bitrate Calculation**: Compute average bitrate

## Installation

The audio-chunker is included in your backend project. Import it:

```javascript
const { AudioChunker, AudioStreamManager } = require('./audio-chunker');
```

## Quick Start

### Basic Usage

```javascript
// Create a chunker instance
const chunker = new AudioChunker({
    chunkSize: 4096,           // Chunk size in bytes
    maxBufferSize: 5 * 1024 * 1024, // Max 5MB
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16
});

// Add audio data
const audioData = Buffer.from(...);
const status = chunker.addData(audioData);

console.log(`Received ${status.bytesReceived} bytes`);
console.log(`Complete chunks: ${status.completeChunks}`);

// Get complete audio
const completeAudio = chunker.getCompleteAudio();

// Convert to WAV
const wavFile = chunker.toWAV();

// Validate audio
const validation = chunker.validate();
if (validation.isValid) {
    console.log('Audio is valid');
} else {
    console.log('Validation issues:', validation.issues);
}

// Reset for next session
chunker.reset();
```

## API Reference

### AudioChunker Class

#### Constructor

```javascript
new AudioChunker(config)
```

**Parameters:**
- `config` (Object): Configuration options
  - `chunkSize` (number): Size of each chunk in bytes (default: 4096)
  - `maxBufferSize` (number): Maximum buffer size in bytes (default: 5MB)
  - `sampleRate` (number): Sample rate in Hz (default: 16000)
  - `channels` (number): Number of audio channels (default: 1)
  - `bitDepth` (number): Bits per sample (default: 16)

#### Methods

##### addData(data)
Add audio data to the chunker.

```javascript
const status = chunker.addData(Buffer.from(...));
```

**Parameters:**
- `data` (Buffer): Audio data to add

**Returns:**
- `Object`: Status object with `bytesReceived`, `completeChunks`, `elapsedTimeMs`, etc.

**Throws:**
- Error if data is not a Buffer
- Error if buffer size exceeds maxBufferSize

---

##### getChunks()
Get all complete chunks.

```javascript
const chunks = chunker.getChunks();
```

**Returns:**
- `Array<Buffer>`: Array of audio chunks

---

##### peekChunk(index)
View a chunk without removing it.

```javascript
const chunk = chunker.peekChunk(0);
```

**Parameters:**
- `index` (number): Chunk index (default: 0)

**Returns:**
- `Buffer|null`: Chunk or null if not available

---

##### popChunk()
Get and remove the next chunk.

```javascript
const chunk = chunker.popChunk();
```

**Returns:**
- `Buffer|null`: Chunk or null if no chunks available

---

##### getBuffer()
Get remaining incomplete chunk data.

```javascript
const remaining = chunker.getBuffer();
```

**Returns:**
- `Buffer`: Remaining buffer data

---

##### getCompleteAudio()
Get all audio data (complete chunks + remaining buffer).

```javascript
const audio = chunker.getCompleteAudio();
```

**Returns:**
- `Buffer`: Complete audio buffer

---

##### reset()
Clear all state and prepare for new session.

```javascript
chunker.reset();
```

---

##### getStatus()
Get current chunker status.

```javascript
const status = chunker.getStatus();
```

**Returns:**
```javascript
{
    bytesReceived: 8192,
    completeChunks: 2,
    pendingChunkBytes: 512,
    totalChunksProcessed: 2,
    elapsedTimeMs: 1234,
    bytesPerSecond: 6655,
    estimatedDurationSeconds: 1.234
}
```

---

##### getStats()
Get comprehensive audio statistics.

```javascript
const stats = chunker.getStats();
```

**Returns:**
```javascript
{
    totalBytes: 8192,
    completeChunks: 2,
    chunkSize: 4096,
    totalChunksCreated: 2,
    incompleteChunkBytes: 512,
    estimatedDurationSeconds: 1.234,
    averageBitrate: 256,  // kbps
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16
}
```

---

##### validate()
Validate audio data.

```javascript
const validation = chunker.validate();
```

**Returns:**
```javascript
{
    isValid: true,
    issues: [],
    audioStats: { /* stats object */ }
}
```

**Validation Checks:**
- Ensures minimum audio data (0.5 seconds)
- Checks for complete chunks
- Validates buffer consistency

---

##### toWAV()
Convert audio to WAV format.

```javascript
const wavBuffer = chunker.toWAV();
```

**Returns:**
- `Buffer`: WAV formatted audio data

**Note:** Automatically includes proper WAV header with RIFF, fmt, and data chunks.

---

##### processChunks(callback)
Iterate through chunks asynchronously.

```javascript
await chunker.processChunks(async (chunk, index, total) => {
    console.log(`Processing chunk ${index + 1}/${total}`);
    // Process chunk
});
```

**Parameters:**
- `callback` (Function): Async function called for each chunk
  - `chunk` (Buffer): Current chunk
  - `index` (number): Chunk index
  - `total` (number): Total number of chunks

---

##### hasChunks()
Check if there are complete chunks.

```javascript
if (chunker.hasChunks()) {
    // Process chunks
}
```

**Returns:**
- `boolean`: True if chunks exist

---

##### getChunkCount()
Get number of complete chunks.

```javascript
const count = chunker.getChunkCount();
```

**Returns:**
- `number`: Number of complete chunks

---

##### clearChunks()
Clear chunks without resetting configuration.

```javascript
chunker.clearChunks();
```

---

### Events

The AudioChunker extends EventEmitter and emits the following events:

#### 'chunk' Event
Emitted when a complete chunk is available.

```javascript
chunker.on('chunk', (chunkInfo) => {
    console.log(`Chunk #${chunkInfo.chunkNumber}: ${chunkInfo.chunkSize} bytes`);
});
```

**Data:**
```javascript
{
    chunk: Buffer,
    chunkNumber: number,
    chunkSize: number
}
```

---

#### 'error' Event
Emitted when an error occurs.

```javascript
chunker.on('error', (error) => {
    console.error('Error:', error.message);
});
```

---

### AudioStreamManager Class

High-level manager for streaming operations.

#### Constructor

```javascript
new AudioStreamManager(config)
```

**Parameters:** Same as AudioChunker config

#### Methods

##### addData(data)
Add data to stream.

```javascript
const status = manager.addData(Buffer.from(...));
```

---

##### startStreaming(onChunk)
Start processing chunks with callback.

```javascript
await manager.startStreaming(async (chunk, index, total) => {
    // Process each chunk
});
```

---

##### finishStream()
Finish streaming and get complete audio.

```javascript
const audio = manager.finishStream();
```

**Returns:**
- `Buffer`: Complete audio data

---

##### getChunker()
Get reference to internal AudioChunker.

```javascript
const chunker = manager.getChunker();
```

---

## Integration Examples

### WebSocket Handler Integration

```javascript
const { AudioChunker } = require('./audio-chunker');

function handleInitialization(ws, clientConnection, { userId, action }) {
    clientConnection.sessionData = { userId, action };
    
    // Initialize chunker
    clientConnection.chunker = new AudioChunker({
        chunkSize: 4096,
        maxBufferSize: 5 * 1024 * 1024
    });
    
    // Listen to events
    clientConnection.chunker.on('chunk', (info) => {
        console.log(`Chunk received: #${info.chunkNumber}`);
    });
}

function handleAudioData(ws, clientConnection, data) {
    try {
        const status = clientConnection.chunker.addData(data);
        
        // Send periodic updates
        if (status.totalChunksProcessed % 10 === 0) {
            ws.send(JSON.stringify({
                type: 'audio-received',
                bytesReceived: status.bytesReceived,
                chunkCount: status.completeChunks
            }));
        }
    } catch (error) {
        ws.send(JSON.stringify({
            type: 'error',
            message: error.message
        }));
    }
}

async function handleStopAudio(ws, clientConnection) {
    const chunker = clientConnection.chunker;
    
    // Validate audio
    const validation = chunker.validate();
    if (!validation.isValid) {
        ws.send(JSON.stringify({
            type: 'error',
            issues: validation.issues
        }));
        return;
    }
    
    // Convert to WAV and send to API
    const wavFile = chunker.toWAV();
    const result = await sendToAPI(wavFile);
    
    // Send response
    ws.send(JSON.stringify({
        type: 'result',
        success: result.success,
        data: result.data
    }));
    
    // Reset for next session
    chunker.reset();
}
```

## Configuration Examples

### Low Latency
```javascript
const chunker = new AudioChunker({
    chunkSize: 2048,  // Smaller chunks for lower latency
    sampleRate: 16000
});
```

### High Performance
```javascript
const chunker = new AudioChunker({
    chunkSize: 8192,  // Larger chunks for better performance
    maxBufferSize: 10 * 1024 * 1024,
    sampleRate: 16000
});
```

### CD Quality Audio
```javascript
const chunker = new AudioChunker({
    chunkSize: 4096,
    sampleRate: 44100,  // CD quality
    bitDepth: 16,
    channels: 2         // Stereo
});
```

## Error Handling

The module provides comprehensive error handling:

```javascript
const chunker = new AudioChunker();

// Register error handler
chunker.on('error', (error) => {
    console.error('Buffer overflow:', error.message);
    console.error('Current size:', error.currentSize);
    console.error('Max size:', error.maxSize);
});

// Try-catch for validation
try {
    const status = chunker.addData(audioData);
} catch (error) {
    console.error('Failed to add audio:', error.message);
}
```

## Performance Considerations

1. **Chunk Size**: Large chunks reduce event overhead but increase latency
2. **Buffer Limit**: Set appropriate max buffer size for your use case
3. **Event Handlers**: Don't perform heavy processing in event handlers
4. **Memory**: Monitor memory usage with large audio files

## Testing

Run the included test suite:

```bash
node test-audio-chunker.js
```

Or with a test framework:

```bash
npm test
```

## Troubleshooting

### Buffer Overflow Error
**Problem**: "Buffer size limit exceeded"

**Solution**: Increase `maxBufferSize` or reduce chunk processing delays

```javascript
const chunker = new AudioChunker({
    maxBufferSize: 10 * 1024 * 1024  // 10MB instead of 5MB
});
```

### Validation Fails
**Problem**: "Insufficient audio data"

**Solution**: Ensure minimum 0.5 seconds of audio

```javascript
// At 16kHz, 1 channel, 16-bit: need ~16KB minimum
const minBytes = 16000 * 0.5 * 2;  // ~16KB
```

### Memory Issues
**Problem**: High memory usage with streaming

**Solution**: Clear chunks after processing

```javascript
while (chunker.hasChunks()) {
    const chunk = chunker.popChunk();
    await processChunk(chunk);
}
```

## License

MIT

## Support

For issues or questions, refer to the integration examples in `AUDIO_CHUNKER_USAGE.js` or the test file `test-audio-chunker.js`.
