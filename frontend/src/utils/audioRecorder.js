/**
 * Browser-Side Audio Streaming & Recording Utility
 * Supports real-time WebSocket streaming and local recording
 * Forces microphone input to 16,000 Hz, mono channel
 * Exports as WAV blob for ECAPA-TDNN compatibility
 */

const TARGET_SAMPLE_RATE = 16000;
const NUM_CHANNELS = 1;
const STREAM_CHUNK_SIZE = 4096; // Samples per chunk
const STREAM_BUFFER_THRESHOLD = 16000; // Stream when buffer reaches ~1 second of audio

/**
 * Creates an audio recorder with WebSocket streaming and local recording
 * @param {Object} options - Configuration options
 * @param {WebSocket} options.websocket - WebSocket connection for streaming (optional)
 * @param {Function} options.onChunkSent - Callback when chunk is sent (optional)
 * @param {Function} options.onError - Error callback (optional)
 * @returns {Object} Recorder controller with start, stop, and streaming methods
 */
export function createAudioRecorder(options = {}) {
  let mediaStream = null;
  let audioContext = null;
  let scriptProcessor = null;
  let recordedChunks = [];
  let isRecording = false;
  let sourceAudioRate = 48000;
  
  // WebSocket streaming configuration
  const websocket = options.websocket;
  const onChunkSent = options.onChunkSent || (() => {});
  const onError = options.onError || (err => console.error(err));
  
  // Streaming buffer
  let streamBuffer = new Float32Array(0);
  let chunksStreamed = 0;

  const start = async () => {
    try {
      // Request microphone access with high quality settings
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: { ideal: 48000 },
          channelCount: { exact: 1 },
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // Create audio context
      audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: mediaStream.getAudioTracks()[0].getSettings().sampleRate || 48000,
      });

      sourceAudioRate = audioContext.sampleRate;
      
      const source = audioContext.createMediaStreamSource(mediaStream);
      
      // Use ScriptProcessorNode for raw PCM access
      // Buffer size of 4096 provides good balance between latency and performance
      scriptProcessor = audioContext.createScriptProcessor(STREAM_CHUNK_SIZE, 1, 1);
      
      recordedChunks = [];
      streamBuffer = new Float32Array(0);
      chunksStreamed = 0;
      isRecording = true;

      scriptProcessor.onaudioprocess = (event) => {
        if (!isRecording) return;
        
        const inputData = event.inputBuffer.getChannelData(0);
        const dataCopy = new Float32Array(inputData);
        
        // Store locally for final blob
        recordedChunks.push(dataCopy);
        
        // Stream to WebSocket if available
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          streamAudioChunk(dataCopy);
        }
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);

      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      onError(error);
      throw error;
    }
  };
  
  /**
   * Streams audio chunk via WebSocket
   * Buffers and downsamples before sending
   */
  const streamAudioChunk = (float32Data) => {
    try {
      // Append to stream buffer
      const newBuffer = new Float32Array(streamBuffer.length + float32Data.length);
      newBuffer.set(streamBuffer, 0);
      newBuffer.set(float32Data, streamBuffer.length);
      streamBuffer = newBuffer;
      
      // Send when buffer reaches threshold (approximately 1 second of audio)
      const downsampleRatio = sourceAudioRate / TARGET_SAMPLE_RATE;
      const downsampledLength = Math.floor(streamBuffer.length / downsampleRatio);
      
      if (downsampledLength >= STREAM_BUFFER_THRESHOLD) {
        sendStreamChunk();
      }
    } catch (error) {
      console.error('Error streaming audio chunk:', error);
      onError(error);
    }
  };
  
  /**
   * Sends buffered audio chunk via WebSocket
   */
  const sendStreamChunk = () => {
    try {
      if (streamBuffer.length === 0) return;
      
      // Downsample buffer
      const downsampledAudio = downsample(
        streamBuffer,
        sourceAudioRate,
        TARGET_SAMPLE_RATE
      );
      
      // Convert to 16-bit PCM and create blob for base64 encoding
      const pcmData = convertToPCM16(downsampledAudio);
      const base64Data = arrayBufferToBase64(pcmData);
      
      // Create WebSocket message
      const message = {
        type: 'audio',
        data: base64Data,
        sequence: chunksStreamed,
        timestamp: Date.now()
      };
      
      // Send via WebSocket
      websocket.send(JSON.stringify(message));
      
      chunksStreamed++;
      streamBuffer = new Float32Array(0);
      
      onChunkSent({
        sequence: chunksStreamed - 1,
        size: pcmData.byteLength,
        timestamp: message.timestamp
      });
      
      console.log(`Audio chunk ${chunksStreamed} streamed: ${pcmData.byteLength} bytes`);
    } catch (error) {
      console.error('Error sending stream chunk:', error);
      onError(error);
    }
  };


  const stop = async () => {
    isRecording = false;

    // Send any remaining audio in the stream buffer
    if (websocket && websocket.readyState === WebSocket.OPEN && streamBuffer.length > 0) {
      sendStreamChunk();
      
      // Send final message to indicate stream complete
      const finalMessage = {
        type: 'audio_complete',
        chunks_received: chunksStreamed,
        timestamp: Date.now()
      };
      websocket.send(JSON.stringify(finalMessage));
    }

    if (scriptProcessor) {
      scriptProcessor.disconnect();
      scriptProcessor = null;
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    if (recordedChunks.length === 0) {
      return null;
    }

    // Calculate total length
    const totalLength = recordedChunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const mergedAudio = new Float32Array(totalLength);

    let offset = 0;
    for (const chunk of recordedChunks) {
      mergedAudio.set(chunk, offset);
      offset += chunk.length;
    }

    // Downsample to 16kHz
    const downsampledAudio = downsample(mergedAudio, sourceAudioRate, TARGET_SAMPLE_RATE);

    // Close audio context
    if (audioContext) {
      await audioContext.close();
      audioContext = null;
    }

    // Convert to WAV blob
    const wavBlob = encodeWAV(downsampledAudio, TARGET_SAMPLE_RATE);
    
    recordedChunks = [];
    streamBuffer = new Float32Array(0);
    
    return wavBlob;
  };
  
  /**
   * Flush remaining audio in stream buffer
   * Call before stopping if streaming
   */
  const flushStreamData = () => {
    if (streamBuffer.length > 0) {
      sendStreamChunk();
    }
  };
  
  /**
   * Send stream complete message
   */
  const notifyStreamComplete = () => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      const message = {
        type: 'audio_complete',
        chunks_received: chunksStreamed,
        timestamp: Date.now()
      };
      websocket.send(JSON.stringify(message));
      console.log('Stream complete notification sent');
    }
  };
  
  /**
   * Get stream statistics
   */
  const getStreamStats = () => {
    return {
      chunksStreamed,
      bufferSize: streamBuffer.length,
      isStreaming: websocket && websocket.readyState === WebSocket.OPEN,
      websocketReady: websocket ? websocket.readyState === WebSocket.OPEN : false,
      recordedChunks: recordedChunks.length
    };
  };

  const getIsRecording = () => isRecording;

  return { 
    start, 
    stop, 
    getIsRecording,
    flushStreamData,
    notifyStreamComplete,
    getStreamStats,
    sendStreamChunk
  };
}

/**
 * Converts Float32Array audio to 16-bit PCM
 * Used for WebSocket streaming
 */
function convertToPCM16(samples) {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  let offset = 0;

  for (let i = 0; i < samples.length; i++) {
    // Clamp to [-1, 1] and convert to 16-bit PCM
    const sample = Math.max(-1, Math.min(1, samples[i]));
    const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    view.setInt16(offset, intSample, true);
    offset += 2;
  }

  return buffer;
}

/**
 * Converts ArrayBuffer to Base64 string
 * Used for WebSocket message encoding
 */
function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Downsamples audio data from source rate to target rate
 * Uses linear interpolation for quality
 */
function downsample(audioData, sourceSampleRate, targetSampleRate) {
  if (sourceSampleRate === targetSampleRate) {
    return audioData;
  }

  const ratio = sourceSampleRate / targetSampleRate;
  const newLength = Math.round(audioData.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, audioData.length - 1);
    const fraction = srcIndex - srcIndexFloor;

    // Linear interpolation
    result[i] = audioData[srcIndexFloor] * (1 - fraction) + audioData[srcIndexCeil] * fraction;
  }

  return result;
}

/**
 * Encodes Float32Array audio data to WAV format
 * Standard 16-bit PCM WAV format
 */
function encodeWAV(samples, sampleRate) {
  const numChannels = NUM_CHANNELS;
  const bitsPerSample = 16;
  const blockAlign = numChannels * (bitsPerSample / 8);
  const byteRate = sampleRate * blockAlign;
  const dataLength = samples.length * (bitsPerSample / 8);
  
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  // RIFF chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeString(view, 8, 'WAVE');

  // fmt sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Write audio data - convert float to 16-bit PCM
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    // Clamp to [-1, 1] and convert to 16-bit
    const sample = Math.max(-1, Math.min(1, samples[i]));
    const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    view.setInt16(offset, intSample, true);
    offset += 2;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Writes a string to a DataView at the specified offset
 */
function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

/**
 * Calculates the duration of recorded audio in seconds
 */
export function calculateDuration(blob) {
  return new Promise((resolve) => {
    const audio = new Audio(URL.createObjectURL(blob));
    audio.addEventListener('loadedmetadata', () => {
      resolve(audio.duration);
    });
    audio.addEventListener('error', () => {
      resolve(0);
    });
  });
}
