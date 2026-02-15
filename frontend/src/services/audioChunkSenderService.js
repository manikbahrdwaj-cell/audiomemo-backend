/**
 * Audio Chunk Sender Service
 * Sends audio chunks via WebSocket to backend
 * Handles chunking to message format and delivery confirmation
 */

import { MESSAGE_TYPES, RESPONSE_STATUS } from './webSocketConstants';
import EventEmitter from './webSocketEventEmitter';

export const CHUNK_SENDER_EVENTS = {
  CHUNK_SENT: 'chunk_sender:chunk_sent',
  CHUNK_ACKNOWLEDGED: 'chunk_sender:chunk_acknowledged',
  CHUNK_FAILED: 'chunk_sender:chunk_failed',
  SESSION_STARTED: 'chunk_sender:session_started',
  SESSION_COMPLETED: 'chunk_sender:session_completed',
  ERROR: 'chunk_sender:error',
};

/**
 * Convert Float32Array to Uint8Array for efficient transmission
 * This reduces chunk size by 4x compared to raw floats
 */
function float32ToUint8(floatArray) {
  const buffer = new Uint8Array(floatArray.length * 4);
  const view = new DataView(buffer.buffer);
  
  for (let i = 0; i < floatArray.length; i++) {
    view.setFloat32(i * 4, floatArray[i], true); // true = little-endian
  }
  
  return buffer;
}

/**
 * AudioChunkSenderService - Sends audio chunks via WebSocket
 */
class AudioChunkSenderService extends EventEmitter {
  constructor(webSocketClient, options = {}) {
    super();
    this.wsClient = webSocketClient;
    this.sessionId = null;
    this.phoneNumber = null;
    this.mode = options.mode || 'enrollment'; // 'enrollment' or 'verification'
    this.sessionConfig = options.sessionConfig || {};
    this.chunksSent = 0;
    this.chunksAcknowledged = 0;
    this.isSessionActive = false;
    this.pendingChunks = new Map();

    // Message handling
    this._setupMessageHandlers();
  }

  /**
   * Setup WebSocket message handlers
   */
  _setupMessageHandlers() {
    // Handle audio acknowledgments
    this.wsClient.on(MESSAGE_TYPES.AUDIO, (message) => {
      if (message.action === 'chunk_received') {
        this._handleChunkAcknowledgment(message);
      }
    });

    // Handle enrollment status
    this.wsClient.on(MESSAGE_TYPES.ENROLLMENT_STATUS, (message) => {
      if (message.status === 'completed' || message.status === 'error') {
        this.isSessionActive = false;
        this._emit(CHUNK_SENDER_EVENTS.SESSION_COMPLETED, message);
      }
    });

    // Handle verification status
    this.wsClient.on(MESSAGE_TYPES.VERIFY, (message) => {
      if (message.action === 'verification_complete') {
        this.isSessionActive = false;
        this._emit(CHUNK_SENDER_EVENTS.SESSION_COMPLETED, message);
      }
    });
  }

  /**
   * Start audio chunk sending session
   */
  async startSession(phoneNumber, mode = 'enrollment', config = {}) {
    try {
      this.phoneNumber = phoneNumber;
      this.mode = mode;
      this.sessionConfig = config;
      this.chunksSent = 0;
      this.chunksAcknowledged = 0;
      this.pendingChunks.clear();

      // For enrollment
      if (mode === 'enrollment') {
        const sessionMessage = {
          type: MESSAGE_TYPES.ENROLL,
          action: 'start_session',
          phone_number: phoneNumber,
          config: this.sessionConfig,
        };

        const response = await this.wsClient.sendMessage(sessionMessage, true);
        if (response && response.status === RESPONSE_STATUS.SUCCESS) {
          this.sessionId = response.session_id;
          this.isSessionActive = true;
          this._emit(CHUNK_SENDER_EVENTS.SESSION_STARTED, { sessionId: this.sessionId });
          return true;
        } else {
          throw new Error(response?.message || 'Failed to start enrollment session');
        }
      }

      // For verification
      else if (mode === 'verification') {
        const sessionMessage = {
          type: MESSAGE_TYPES.VERIFY,
          action: 'start_session',
          phone_number: phoneNumber,
          config: this.sessionConfig,
        };

        const response = await this.wsClient.sendMessage(sessionMessage, true);
        if (response && response.status === RESPONSE_STATUS.SUCCESS) {
          this.sessionId = response.session_id;
          this.isSessionActive = true;
          this._emit(CHUNK_SENDER_EVENTS.SESSION_STARTED, { sessionId: this.sessionId });
          return true;
        } else {
          throw new Error(response?.message || 'Failed to start verification session');
        }
      }

      return false;
    } catch (error) {
      this._emit(CHUNK_SENDER_EVENTS.ERROR, { error: error.message });
      throw error;
    }
  }

  /**
   * Send audio chunk to backend
   * @param {Object} chunkInfo - Chunk information from AudioChunkingService
   * @returns {Promise<boolean>} - True if chunk was properly queued/sent
   */
  async sendChunk(chunkInfo) {
    if (!this.isSessionActive) {
      console.warn('Cannot send chunk: session not active');
      return false;
    }

    try {
      const { samples, sampleCount, durationMs, chunkNumber } = chunkInfo;

      // Convert float samples to uint8 for efficient transmission
      const audioBuffer = float32ToUint8(samples);

      // Create message
      const chunkMessage = {
        type: MESSAGE_TYPES.AUDIO,
        action: 'send_chunk',
        session_id: this.sessionId,
        phone_number: this.phoneNumber,
        mode: this.mode,
        chunk_number: chunkNumber,
        audio_data: Array.from(audioBuffer), // Convert to array for JSON serialization
        sample_count: sampleCount,
        sample_rate: 16000,
        duration_ms: durationMs,
        timestamp: new Date().toISOString(),
      };

      // Store pending chunk for timeout handling
      const chunkId = `${this.sessionId}_${chunkNumber}`;
      this.pendingChunks.set(chunkId, {
        timestamp: Date.now(),
        chunk: chunkMessage,
      });

      // Send message (fire and forget for low-latency, but track for acks)
      this.wsClient.send(JSON.stringify(chunkMessage));

      this.chunksSent++;
      this._emit(CHUNK_SENDER_EVENTS.CHUNK_SENT, {
        chunkNumber,
        totalSent: this.chunksSent,
      });

      return true;
    } catch (error) {
      this._emit(CHUNK_SENDER_EVENTS.CHUNK_FAILED, {
        chunkNumber: chunkInfo.chunkNumber,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Handle chunk acknowledgment from backend
   */
  _handleChunkAcknowledgment(message) {
    const { session_id, chunk_number, status } = message;

    if (session_id !== this.sessionId) {
      return;
    }

    const chunkId = `${session_id}_${chunk_number}`;
    this.pendingChunks.delete(chunkId);

    if (status === RESPONSE_STATUS.SUCCESS) {
      this.chunksAcknowledged++;
      this._emit(CHUNK_SENDER_EVENTS.CHUNK_ACKNOWLEDGED, {
        chunkNumber: chunk_number,
        totalAcknowledged: this.chunksAcknowledged,
      });
    } else {
      this._emit(CHUNK_SENDER_EVENTS.CHUNK_FAILED, {
        chunkNumber: chunk_number,
        error: message.error || 'Unknown error',
      });
    }
  }

  /**
   * Finalize session and process all chunks
   */
  async finalizeSession() {
    if (!this.isSessionActive) {
      console.warn('Session not active');
      return false;
    }

    try {
      const messageType =
        this.mode === 'enrollment' ? MESSAGE_TYPES.ENROLLMENT_STATUS : MESSAGE_TYPES.VERIFY;

      const finalizeMessage = {
        type: messageType,
        action: 'finalize_session',
        session_id: this.sessionId,
        phone_number: this.phoneNumber,
        total_chunks: this.chunksSent,
      };

      const response = await this.wsClient.sendMessage(finalizeMessage, true);

      if (response && response.status === RESPONSE_STATUS.SUCCESS) {
        this.isSessionActive = false;
        this._emit(CHUNK_SENDER_EVENTS.SESSION_COMPLETED, {
          status: 'completed',
          result: response,
        });
        return true;
      } else {
        throw new Error(response?.message || 'Failed to finalize session');
      }
    } catch (error) {
      this.isSessionActive = false;
      this._emit(CHUNK_SENDER_EVENTS.ERROR, { error: error.message });
      throw error;
    }
  }

  /**
   * Cancel session
   */
  async cancelSession() {
    if (!this.isSessionActive) {
      return true;
    }

    try {
      const messageType =
        this.mode === 'enrollment' ? MESSAGE_TYPES.ENROLLMENT_STATUS : MESSAGE_TYPES.VERIFY;

      const cancelMessage = {
        type: messageType,
        action: 'cancel_session',
        session_id: this.sessionId,
      };

      await this.wsClient.send(JSON.stringify(cancelMessage));
      this.isSessionActive = false;
      return true;
    } catch (error) {
      console.error('Error cancelling session:', error);
      this.isSessionActive = false;
      return false;
    }
  }

  /**
   * Get session statistics
   */
  getStats() {
    return {
      sessionId: this.sessionId,
      phoneNumber: this.phoneNumber,
      mode: this.mode,
      isSessionActive: this.isSessionActive,
      chunksSent: this.chunksSent,
      chunksAcknowledged: this.chunksAcknowledged,
      pendingChunks: this.pendingChunks.size,
    };
  }

  /**
   * Event emitter pattern
   */
  on(event, callback) {
    super.on(event, callback);
  }

  off(event, callback) {
    super.off(event, callback);
  }

  _emit(event, data = null) {
    super.emit(event, data);
  }
}

export default AudioChunkSenderService;
