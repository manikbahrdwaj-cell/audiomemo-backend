/**
 * WebSocket Client for Real-time Voice Streaming
 * Handles bidirectional communication and audio chunking
 */

const MESSAGE_TYPES = {
  // Server -> Client
  CONNECTION: 'connection',
  INITIALIZED: 'initialized',
  ENROLLMENT_STARTED: 'enrollment-started',
  VERIFICATION_STARTED: 'verification-started',
  AUDIO_RECEIVED: 'audio-received',
  CHUNK_PROCESSED: 'chunk-processed',
  PROCESSING: 'processing',
  RESULT: 'result',
  ERROR: 'error',
  STATUS: 'status',
  PONG: 'pong',

  // Client -> Server
  INIT: 'init',
  START_ENROLLMENT: 'start-enrollment',
  START_VERIFICATION: 'start-verification',
  AUDIO_DATA: 'audio',
  STOP_AUDIO: 'stop-audio',
  GET_STATUS: 'get-status',
  PING: 'ping'
};

// Audio configuration
const AUDIO_CONFIG = {
  SAMPLE_RATE: 16000,
  CHANNELS: 1,
  BITS_PER_SAMPLE: 16,
  ENROLLMENT_CHUNK_SIZE: 16000, // 1 second at 16kHz
  VERIFICATION_CHUNK_SIZE: 80000, // 5 seconds at 16kHz
  STREAM_CHUNK_SIZE: 4096 // Send chunks of 4KB for streaming
};

class WebSocketClient {
  constructor(wsUrl = null) {
    this.wsUrl = wsUrl || this.getDefaultUrl();
    this.ws = null;
    this.connected = false;
    this.connecting = false;
    this.clientId = null;
    this.sessionId = null;
    this.userId = null;
    
    // Audio state
    this.audioContext = null;
    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.isRecording = false;
    
    // Chunk processing
    this.audioBuffer = [];
    this.totalBytesReceived = 0;
    this.chunkCount = 0;
    
    // Session state
    this.currentAction = null; // 'enroll' or 'verify'
    this.processingMode = 'streaming'; // 'streaming' or 'batch'
    
    // Event listeners
    this.listeners = new Map();
    
    // Reconnection
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    
    // Heartbeat
    this.heartbeatInterval = null;
    this.heartbeatTimeout = 30000;
  }

  /**
   * Get default WebSocket URL
   */
  getDefaultUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_WS_HOST || window.location.hostname;
    const port = process.env.REACT_APP_WS_PORT || '8001';
    return `${protocol}//${host}:${port}`;
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    return new Promise((resolve, reject) => {
      if (this.connected || this.connecting) {
        resolve();
        return;
      }

      this.connecting = true;
      this.emit('connecting');

      try {
        this.ws = new WebSocket(this.wsUrl);
        
        this.ws.onopen = () => {
          console.log('[WSClient] Connected to server');
          this.connected = true;
          this.connecting = false;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.emit('connected');
          resolve();
        };

        this.ws.onmessage = (event) => this.handleMessage(event);
        
        this.ws.onerror = (error) => {
          console.error('[WSClient] WebSocket error:', error);
          this.emit('error', error.message);
          if (!this.connected) {
            reject(new Error('Failed to connect to WebSocket server'));
          }
        };

        this.ws.onclose = () => {
          console.log('[WSClient] Connection closed');
          this.connected = false;
          this.connecting = false;
          this.stopHeartbeat();
          this.emit('disconnected');
          this.attemptReconnect();
        };

      } catch (error) {
        console.error('[WSClient] Connection error:', error);
        this.connecting = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from server
   */
  disconnect() {
    if (this.ws) {
      this.stopHeartbeat();
      this.ws.close();
      this.ws = null;
      this.connected = false;
    }
  }

  /**
   * Attempt automatic reconnection
   */
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`[WSClient] Attempting reconnection in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(err => {
          console.error('[WSClient] Reconnection failed:', err);
        });
      }, delay);
    } else {
      console.error('[WSClient] Max reconnection attempts reached');
      this.emit('reconnection-failed');
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.connected) {
        this.ping();
      }
    }, this.heartbeatTimeout);
  }

  /**
   * Stop heartbeat
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Send ping
   */
  ping() {
    this.send({
      type: MESSAGE_TYPES.PING,
      timestamp: Date.now()
    });
  }

  /**
   * Handle incoming messages
   */
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      console.log('[WSClient] Message received:', message.type);

      switch (message.type) {
        case MESSAGE_TYPES.CONNECTION:
          this.clientId = message.clientId;
          this.emit('connection-ack', message);
          break;

        case MESSAGE_TYPES.INITIALIZED:
          this.sessionId = message.sessionId || this.sessionId;
          this.emit('initialized', message);
          break;

        case MESSAGE_TYPES.ENROLLMENT_STARTED:
          this.currentAction = 'enroll';
          this.emit('enrollment-started', message);
          break;

        case MESSAGE_TYPES.VERIFICATION_STARTED:
          this.currentAction = 'verify';
          this.emit('verification-started', message);
          break;

        case MESSAGE_TYPES.AUDIO_RECEIVED:
          this.totalBytesReceived = message.totalBytes;
          this.chunkCount = message.chunkCount;
          this.emit('audio-received', message);
          break;

        case MESSAGE_TYPES.CHUNK_PROCESSED:
          this.emit('chunk-processed', message);
          break;

        case MESSAGE_TYPES.PROCESSING:
          this.emit('processing', message);
          break;

        case MESSAGE_TYPES.RESULT:
          this.emit('result', message);
          break;

        case MESSAGE_TYPES.PONG:
          this.emit('pong', message);
          break;

        case MESSAGE_TYPES.ERROR:
          this.emit('server-error', message);
          break;

        default:
          console.warn('[WSClient] Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('[WSClient] Message handling error:', error);
      this.emit('error', error.message);
    }
  }

  /**
   * Initialize session
   */
  initialize(userId, action = 'enroll') {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error('Not connected to WebSocket server'));
        return;
      }

      this.userId = userId;
      this.currentAction = action;

      const onInitialized = (message) => {
        this.removeListener('initialized', onInitialized);
        this.removeListener('server-error', onError);
        resolve(message);
      };

      const onError = (message) => {
        this.removeListener('initialized', onInitialized);
        this.removeListener('server-error', onError);
        reject(new Error(message.error || 'Initialization failed'));
      };

      this.on('initialized', onInitialized);
      this.on('server-error', onError);

      this.send({
        type: MESSAGE_TYPES.INIT,
        userId: userId,
        action: action,
        timestamp: Date.now()
      });
    });
  }

  /**
   * Start enrollment
   */
  startEnrollment() {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error('Not connected'));
        return;
      }

      const onStarted = (message) => {
        this.removeListener('enrollment-started', onStarted);
        this.removeListener('server-error', onError);
        this.processingMode = 'streaming';
        resolve(message);
      };

      const onError = (message) => {
        this.removeListener('enrollment-started', onStarted);
        this.removeListener('server-error', onError);
        reject(new Error(message.error || 'Failed to start enrollment'));
      };

      this.on('enrollment-started', onStarted);
      this.on('server-error', onError);

      this.send({
        type: MESSAGE_TYPES.START_ENROLLMENT,
        timestamp: Date.now()
      });
    });
  }

  /**
   * Start verification
   */
  startVerification(enrolledUserId = null) {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error('Not connected'));
        return;
      }

      const onStarted = (message) => {
        this.removeListener('verification-started', onStarted);
        this.removeListener('server-error', onError);
        this.processingMode = 'streaming';
        resolve(message);
      };

      const onError = (message) => {
        this.removeListener('verification-started', onStarted);
        this.removeListener('server-error', onError);
        reject(new Error(message.error || 'Failed to start verification'));
      };

      this.on('verification-started', onStarted);
      this.on('server-error', onError);

      this.send({
        type: MESSAGE_TYPES.START_VERIFICATION,
        enrolledUserId: enrolledUserId || this.userId,
        timestamp: Date.now()
      });
    });
  }

  /**
   * Send audio data chunk
   */
  sendAudioChunk(audioData) {
    if (!this.connected) {
      console.warn('[WSClient] Not connected, cannot send audio');
      return false;
    }

    try {
      if (audioData instanceof ArrayBuffer) {
        this.ws.send(audioData);
      } else if (audioData instanceof Blob) {
        this.ws.send(audioData);
      } else {
        console.error('[WSClient] Invalid audio data format');
        return false;
      }
      return true;
    } catch (error) {
      console.error('[WSClient] Failed to send audio:', error);
      this.emit('error', error.message);
      return false;
    }
  }

  /**
   * Stop audio and process
   */
  stopAudio() {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error('Not connected'));
        return;
      }

      const onResult = (message) => {
        this.removeListener('result', onResult);
        this.removeListener('server-error', onError);
        this.audioBuffer = [];
        this.totalBytesReceived = 0;
        this.chunkCount = 0;
        resolve(message);
      };

      const onError = (message) => {
        this.removeListener('result', onResult);
        this.removeListener('server-error', onError);
        reject(new Error(message.error || 'Failed to process audio'));
      };

      this.on('result', onResult);
      this.on('server-error', onError);

      // Send stop signal
      this.send({
        type: MESSAGE_TYPES.STOP_AUDIO,
        timestamp: Date.now()
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.listeners.has('result')) {
          onError({ error: 'Processing timeout' });
        }
      }, 30000);
    });
  }

  /**
   * Get status
   */
  getStatus() {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error('Not connected'));
        return;
      }

      const onStatus = (message) => {
        this.removeListener('status', onStatus);
        resolve(message);
      };

      this.on('status', onStatus);

      this.send({
        type: MESSAGE_TYPES.GET_STATUS,
        timestamp: Date.now()
      });

      // Timeout after 5 seconds
      setTimeout(() => {
        if (this.listeners.has('status')) {
          reject(new Error('Status request timeout'));
        }
      }, 5000);
    });
  }

  /**
   * Send JSON message
   */
  send(message) {
    if (!this.connected) {
      console.warn('[WSClient] Not connected, cannot send message');
      return false;
    }

    try {
      const json = JSON.stringify(message);
      this.ws.send(json);
      return true;
    } catch (error) {
      console.error('[WSClient] Failed to send message:', error);
      this.emit('error', error.message);
      return false;
    }
  }

  /**
   * Start recording audio
   */
  async startRecording() {
    try {
      // Get audio context
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      const source = this.audioContext.createMediaStreamSource(stream);
      
      // Create processor for real-time audio
      const processorScript = `
        class AudioProcessor extends AudioWorkletProcessor {
          constructor() {
            super();
            this.buffer = [];
          }

          process(inputs, outputs) {
            const input = inputs[0];
            if (input.length > 0) {
              const channelData = input[0];
              this.port.postMessage({
                type: 'audiodata',
                data: Array.from(channelData)
              });
            }
            return true;
          }
        }
        registerProcessor('audio-processor', AudioProcessor);
      `;

      // Fallback: Use ScriptProcessorNode
      const bufferSize = 4096;
      const processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

      processor.onaudioprocess = (event) => {
        const audioData = event.inputData.getChannelData(0);
        this.handleAudioFrame(audioData);
      };

      source.connect(processor);
      processor.connect(this.audioContext.destination);

      this.recordedChunks = [];
      this.isRecording = true;

      console.log('[WSClient] Recording started');
      this.emit('recording-started');
      
      return true;
    } catch (error) {
      console.error('[WSClient] Failed to start recording:', error);
      this.emit('error', error.message);
      return false;
    }
  }

  /**
   * Handle audio frame (called in real-time)
   */
  handleAudioFrame(audioData) {
    if (!this.isRecording || !this.connected) return;

    // Convert float32 to int16 PCM
    const pcmData = this.floatTo16BitPCM(audioData);
    this.recordedChunks.push(pcmData);

    // Determine chunk size based on action
    const chunkSize = this.currentAction === 'enroll' 
      ? AUDIO_CONFIG.ENROLLMENT_CHUNK_SIZE 
      : AUDIO_CONFIG.VERIFICATION_CHUNK_SIZE;

    // Calculate current audio duration
    const totalSamples = this.recordedChunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const durationSamples = chunkSize;

    // Send chunks as they reach the threshold
    if (totalSamples >= durationSamples) {
      this.flushAudioChunks(durationSamples);
    }
  }

  /**
   * Flush audio chunks and send over WebSocket
   */
  flushAudioChunks(targetSamples) {
    let currentSize = 0;
    const chunksToSend = [];

    while (this.recordedChunks.length > 0 && currentSize < targetSamples) {
      const chunk = this.recordedChunks.shift();
      chunksToSend.push(chunk);
      currentSize += chunk.length;
    }

    if (chunksToSend.length > 0) {
      // Combine chunks into single buffer
      const combined = new Uint8Array(currentSize * 2);
      let offset = 0;

      for (const chunk of chunksToSend) {
        for (let i = 0; i < chunk.length; i++) {
          const int16 = chunk[i];
          combined[offset++] = int16 & 0xFF;
          combined[offset++] = (int16 >> 8) & 0xFF;
        }
      }

      // Send over WebSocket
      this.sendAudioChunk(combined.buffer);

      console.log(`[WSClient] Sent audio chunk: ${combined.byteLength} bytes`);
      this.emit('chunk-sent', { bytes: combined.byteLength });
    }
  }

  /**
   * Stop recording
   */
  stopRecording() {
    return new Promise((resolve) => {
      if (!this.isRecording) {
        resolve();
        return;
      }

      this.isRecording = false;

      // Flush remaining audio
      const totalSamples = this.recordedChunks.reduce((sum, chunk) => sum + chunk.length, 0);
      if (totalSamples > 0) {
        this.flushAudioChunks(totalSamples);
      }

      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }

      console.log('[WSClient] Recording stopped');
      this.emit('recording-stopped');
      resolve();
    });
  }

  /**
   * Convert Float32 audio to Int16 PCM
   */
  floatTo16BitPCM(float32Array) {
    const int16Array = new Int16Array(float32Array.length);

    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    return int16Array;
  }

  /**
   * Event listener management
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  removeListener(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data = null) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[WSClient] Error in event listener for '${event}':`, error);
        }
      });
    }
  }

  /**
   * Get connection status
   */
  isConnected() {
    return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      connected: this.connected,
      clientId: this.clientId,
      sessionId: this.sessionId,
      userId: this.userId,
      currentAction: this.currentAction,
      totalBytesReceived: this.totalBytesReceived,
      chunkCount: this.chunkCount,
      isRecording: this.isRecording,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

export default WebSocketClient;
