/**
 * Audio Chunking Service
 * Captures microphone audio and splits into fixed-size chunks
 * Supports different chunk sizes for enrollment (1s) and verification (5s)
 */

/**
 * Constants for audio chunking
 */
export const AUDIO_CONFIG = {
  SAMPLE_RATE: 16000,
  ENROLLMENT_CHUNK_DURATION_MS: 1000,     // 1 second
  VERIFICATION_CHUNK_DURATION_MS: 5000,   // 5 seconds
  ENROLLMENT_CHUNK_SAMPLES: 16000,        // 1 second at 16kHz
  VERIFICATION_CHUNK_SAMPLES: 80000,      // 5 seconds at 16kHz
  BUFFER_SIZE: 4096,                      // Processing buffer size
};

export const CHUNK_EVENTS = {
  RECORDING_STARTED: 'recording:started',
  CHUNK_READY: 'chunk:ready',
  RECORDING_STOPPED: 'recording:stopped',
  RECORDING_ERROR: 'recording:error',
  CHUNK_ERROR: 'chunk:error',
};

/**
 * AudioChunkingService - Captures and chunks microphone audio
 */
class AudioChunkingService {
  constructor(options = {}) {
    // Audio context and nodes
    this.audioContext = null;
    this.mediaStream = null;
    this.mediaStreamSource = null;
    this.scriptProcessor = null;

    // Buffering and chunking
    this.audioBuffer = [];
    this.chunkSize = options.chunkSize || AUDIO_CONFIG.ENROLLMENT_CHUNK_SAMPLES;
    this.mode = options.mode || 'enrollment'; // 'enrollment' or 'verification'
    this.sampleRate = options.sampleRate || AUDIO_CONFIG.SAMPLE_RATE;

    // State tracking
    this.isRecording = false;
    this.recordedTime = 0;
    this.chunkCount = 0;

    // Callbacks
    this.onChunkReady = options.onChunkReady || (() => {});
    this.onRecordingStarted = options.onRecordingStarted || (() => {});
    this.onRecordingStopped = options.onRecordingStopped || (() => {});
    this.onError = options.onError || (() => {});

    // Event emitter for flexibility
    this.eventListeners = {};
  }

  /**
   * Initialize audio context and media stream
   */
  async initialize() {
    try {
      // Create audio context
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContext({ sampleRate: this.sampleRate });

      // Request microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
          sampleRate: this.sampleRate,
        },
      });

      // Create media stream source
      this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Create script processor for audio sampling
      this.scriptProcessor = this.audioContext.createScriptProcessor(
        AUDIO_CONFIG.BUFFER_SIZE,
        1, // input channels
        1  // output channels
      );

      // Handle audio processing
      this.scriptProcessor.onaudioprocess = (event) => this._onAudioProcess(event);

      // Connect nodes
      this.mediaStreamSource.connect(this.scriptProcessor);
      this.scriptProcessor.connect(this.audioContext.destination);

      this._emit(CHUNK_EVENTS.RECORDING_STARTED);
      this.onRecordingStarted();

      return true;
    } catch (error) {
      const errorMsg = `Audio initialization failed: ${error.message}`;
      console.error(errorMsg);
      this._emit(CHUNK_EVENTS.RECORDING_ERROR, { error: errorMsg });
      this.onError(error);
      return false;
    }
  }

  /**
   * Set chunking mode (enrollment or verification)
   */
  setMode(mode) {
    if (mode === 'enrollment') {
      this.chunkSize = AUDIO_CONFIG.ENROLLMENT_CHUNK_SAMPLES;
      this.mode = 'enrollment';
    } else if (mode === 'verification') {
      this.chunkSize = AUDIO_CONFIG.VERIFICATION_CHUNK_SAMPLES;
      this.mode = 'verification';
    } else {
      throw new Error(`Invalid mode: ${mode}. Must be 'enrollment' or 'verification'`);
    }
  }

  /**
   * Start recording audio
   */
  startRecording() {
    if (this.isRecording) {
      console.warn('Recording already in progress');
      return;
    }

    if (!this.mediaStreamSource) {
      console.error('Audio context not initialized. Call initialize() first.');
      return;
    }

    this.isRecording = true;
    this.audioBuffer = [];
    this.recordedTime = 0;
    this.chunkCount = 0;

    this._emit(CHUNK_EVENTS.RECORDING_STARTED);
    this.onRecordingStarted();
  }

  /**
   * Stop recording audio
   */
  stopRecording() {
    if (!this.isRecording) {
      return;
    }

    this.isRecording = false;

    // Emit final chunk if there's remaining data
    if (this.audioBuffer.length > 0) {
      this._emitChunk(this.audioBuffer);
      this.audioBuffer = [];
    }

    this._emit(CHUNK_EVENTS.RECORDING_STOPPED);
    this.onRecordingStopped();
  }

  /**
   * Process audio data from script processor
   */
  _onAudioProcess(event) {
    if (!this.isRecording) {
      return;
    }

    // Extract audio data from input channel
    const inputData = event.inputBuffer.getChannelData(0);

    // Convert to regular array and add to buffer
    for (let i = 0; i < inputData.length; i++) {
      this.audioBuffer.push(inputData[i]);
    }

    // Check if we have enough samples for a chunk
    while (this.audioBuffer.length >= this.chunkSize) {
      // Extract chunk
      const chunk = this.audioBuffer.splice(0, this.chunkSize);
      this._emitChunk(chunk);
    }

    // Update recorded time
    this.recordedTime += (inputData.length / this.sampleRate) * 1000;
  }

  /**
   * Emit a chunk
   */
  _emitChunk(chunk) {
    this.chunkCount += 1;

    // Convert to Float32Array
    const chunkData = new Float32Array(chunk);

    const chunkInfo = {
      chunkNumber: this.chunkCount,
      samples: chunkData,
      sampleCount: chunkData.length,
      sampleRate: this.sampleRate,
      durationMs: (chunkData.length / this.sampleRate) * 1000,
      timestamp: new Date().toISOString(),
      mode: this.mode,
    };

    this._emit(CHUNK_EVENTS.CHUNK_READY, chunkInfo);
    this.onChunkReady(chunkInfo);
  }

  /**
   * Pause recording (can be resumed)
   */
  pauseRecording() {
    this.isRecording = false;
  }

  /**
   * Resume recording
   */
  resumeRecording() {
    if (!this.mediaStreamSource) {
      console.error('Audio context not initialized');
      return;
    }
    this.isRecording = true;
  }

  /**
   * Cleanup and release resources
   */
  async cleanup() {
    try {
      this.isRecording = false;

      // Stop all media tracks
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach((track) => track.stop());
        this.mediaStream = null;
      }

      // Disconnect and close audio context
      if (this.scriptProcessor) {
        this.scriptProcessor.disconnect();
        this.scriptProcessor.onaudioprocess = null;
        this.scriptProcessor = null;
      }

      if (this.mediaStreamSource) {
        this.mediaStreamSource.disconnect();
        this.mediaStreamSource = null;
      }

      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = null;
      }

      this.audioBuffer = [];
      this.chunkCount = 0;
      this.recordedTime = 0;

      console.log('Audio resources cleaned up');
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }

  /**
   * Get recording statistics
   */
  getStats() {
    return {
      isRecording: this.isRecording,
      chunkCount: this.chunkCount,
      recordedTimeMs: this.recordedTime,
      recordedTimeSeconds: this.recordedTime / 1000,
      bufferSize: this.audioBuffer.length,
      chunkSize: this.chunkSize,
      mode: this.mode,
    };
  }

  /**
   * Event emitter pattern
   */
  on(event, callback) {
    if (!this.eventListeners[event]) {
      this.eventListeners[event] = [];
    }
    this.eventListeners[event].push(callback);
  }

  off(event, callback) {
    if (!this.eventListeners[event]) {
      return;
    }
    this.eventListeners[event] = this.eventListeners[event].filter((cb) => cb !== callback);
  }

  _emit(event, data = null) {
    if (!this.eventListeners[event]) {
      return;
    }
    this.eventListeners[event].forEach((callback) => callback(data));
  }
}

export default AudioChunkingService;
