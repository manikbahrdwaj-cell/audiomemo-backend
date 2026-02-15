/**
 * Enrollment WebSocket Service
 * Handles real-time enrollment with multi-chunk audio support
 * Provides enrollment session management, progress tracking, and error handling
 */

import EventEmitter from './webSocketEventEmitter';
import { MESSAGE_TYPES, RESPONSE_STATUS } from './webSocketConstants';

export const ENROLLMENT_EVENTS = {
  SESSION_CREATED: 'enrollment:session_created',
  CHUNK_RECEIVED: 'enrollment:chunk_received',
  CHUNK_PROCESSING: 'enrollment:chunk_processing',
  CHUNK_PROCESSED: 'enrollment:chunk_processed',
  PROGRESS_UPDATE: 'enrollment:progress_update',
  STATUS_CHANGED: 'enrollment:status_changed',
  COMPLETED: 'enrollment:completed',
  ERROR: 'enrollment:error',
  CANCELLED: 'enrollment:cancelled',
};

export const ENROLLMENT_STATUS = {
  INITIALIZING: 'initializing',
  ACTIVE: 'active',
  COLLECTING: 'collecting',
  PROCESSING: 'processing',
  FINALIZING: 'finalizing',
  COMPLETED: 'completed',
  ERROR: 'error',
  CANCELLED: 'cancelled',
};

class EnrollmentWebSocketService extends EventEmitter {
  constructor(webSocketClient) {
    super();
    this.wsClient = webSocketClient;
    this.enrollmentSessions = new Map();
    this.currentSessionId = null;
    this.audioChunks = [];
    this.sessionConfig = null;

    this._setupMessageHandlers();
    this._setupErrorHandlers();
  }

  /**
   * Setup WebSocket message handlers for enrollment
   */
  _setupMessageHandlers() {
    this.wsClient.on(MESSAGE_TYPES.ENROLLMENT_STATUS, (message) => {
      this._handleEnrollmentStatus(message);
    });

    this.wsClient.on(MESSAGE_TYPES.ENROLL, (message) => {
      this._handleEnrollmentMessage(message);
    });

    this.wsClient.on(MESSAGE_TYPES.ENROLLMENT_CONFIRMED, (message) => {
      this._handleEnrollmentConfirmation(message);
    });
  }

  /**
   * Setup error handlers
   */
  _setupErrorHandlers() {
    this.wsClient.on(MESSAGE_TYPES.ERROR, (message) => {
      if (message.context === 'enrollment') {
        this._handleEnrollmentError(message);
      }
    });
  }

  /**
   * Initiate enrollment session
   * @param {string} phoneNumber - Phone number for enrollment
   * @param {object} config - Enrollment configuration
   */
  async startEnrollment(phoneNumber, config = {}) {
    try {
      const sessionId = this._generateSessionId();
      this.currentSessionId = sessionId;
      this.audioChunks = [];

      const defaultConfig = {
        max_chunks: 10,
        chunk_timeout_seconds: 30,
        session_timeout_seconds: 300,
        min_chunks_required: 1,
        auto_process: true,
        merge_embeddings: true,
        ...config,
      };

      this.sessionConfig = defaultConfig;

      // Create enrollment session
      const enrollmentRequest = {
        type: MESSAGE_TYPES.ENROLL,
        action: 'start_session',
        session_id: sessionId,
        phone_number: phoneNumber,
        config: defaultConfig,
      };

      await this.wsClient.send(enrollmentRequest);

      this.emit(ENROLLMENT_EVENTS.SESSION_CREATED, {
        sessionId,
        phoneNumber,
        config: defaultConfig,
      });

      return sessionId;
    } catch (error) {
      this.emit(ENROLLMENT_EVENTS.ERROR, {
        error: error.message,
        stage: 'initialization',
      });
      throw error;
    }
  }

  /**
   * Submit audio chunk for enrollment
   * @param {ArrayBuffer|Blob} audioData - Audio data
   * @param {number} chunkIndex - Chunk index
   */
  async submitAudioChunk(audioData, chunkIndex = this.audioChunks.length) {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active enrollment session');
      }

      // Convert Blob to ArrayBuffer if needed
      const buffer = audioData instanceof Blob 
        ? await audioData.arrayBuffer() 
        : audioData;

      const chunkMessage = {
        type: MESSAGE_TYPES.AUDIO,
        action: 'submit_chunk',
        session_id: this.currentSessionId,
        chunk_index: chunkIndex,
        audio_data: this._bufferToBase64(buffer),
        timestamp: new Date().toISOString(),
      };

      await this.wsClient.send(chunkMessage);

      this.audioChunks.push({
        index: chunkIndex,
        timestamp: new Date(),
        size: buffer.byteLength,
      });

      this.emit(ENROLLMENT_EVENTS.CHUNK_RECEIVED, {
        sessionId: this.currentSessionId,
        chunkIndex,
        totalChunks: this.audioChunks.length,
      });

      return true;
    } catch (error) {
      this.emit(ENROLLMENT_EVENTS.ERROR, {
        error: error.message,
        stage: 'chunk_submission',
        chunkIndex,
      });
      throw error;
    }
  }

  /**
   * Complete enrollment session
   */
  async completeEnrollment() {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active enrollment session');
      }

      const completeMessage = {
        type: MESSAGE_TYPES.ENROLL,
        action: 'complete',
        session_id: this.currentSessionId,
      };

      await this.wsClient.send(completeMessage);
      return true;
    } catch (error) {
      this.emit(ENROLLMENT_EVENTS.ERROR, {
        error: error.message,
        stage: 'completion',
      });
      throw error;
    }
  }

  /**
   * Cancel enrollment session
   */
  async cancelEnrollment() {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active enrollment session');
      }

      const cancelMessage = {
        type: MESSAGE_TYPES.ENROLL,
        action: 'cancel',
        session_id: this.currentSessionId,
      };

      await this.wsClient.send(cancelMessage);
      this._cleanup();

      this.emit(ENROLLMENT_EVENTS.CANCELLED, {
        sessionId: this.currentSessionId,
      });

      return true;
    } catch (error) {
      this.emit(ENROLLMENT_EVENTS.ERROR, {
        error: error.message,
        stage: 'cancellation',
      });
      throw error;
    }
  }

  /**
   * Get enrollment progress
   */
  getProgress() {
    return {
      sessionId: this.currentSessionId,
      audioChunksCollected: this.audioChunks.length,
      maxChunks: this.sessionConfig?.max_chunks || 10,
      progressPercentage: this.sessionConfig 
        ? (this.audioChunks.length / this.sessionConfig.max_chunks) * 100 
        : 0,
    };
  }

  /**
   * Handle enrollment status updates from server
   */
  _handleEnrollmentStatus(message) {
    const { session_id, status, progress, error, timestamp } = message;

    if (session_id === this.currentSessionId) {
      this.emit(ENROLLMENT_EVENTS.STATUS_CHANGED, {
        status,
        progress,
        error,
        timestamp,
      });
    }
  }

  /**
   * Handle enrollment messages
   */
  _handleEnrollmentMessage(message) {
    const { action, session_id, status, details } = message;

    if (action === 'chunk_processed') {
      this.emit(ENROLLMENT_EVENTS.CHUNK_PROCESSED, {
        sessionId: session_id,
        chunkIndex: details.chunk_index,
        embedding: details.embedding,
        quality: details.quality_score,
      });
    }

    if (action === 'processing') {
      this.emit(ENROLLMENT_EVENTS.PROCESSING, {
        sessionId: session_id,
        stage: details.stage,
        progress: details.progress,
      });
    }
  }

  /**
   * Handle enrollment confirmation
   */
  _handleEnrollmentConfirmation(message) {
    const {
      session_id,
      status,
      vector_id,
      phone_number,
      chunks_processed,
      embedding_stats,
    } = message;

    if (session_id === this.currentSessionId) {
      this.emit(ENROLLMENT_EVENTS.COMPLETED, {
        sessionId: session_id,
        vectorId: vector_id,
        phoneNumber: phone_number,
        status,
        chunksProcessed: chunks_processed,
        embeddingStats: embedding_stats,
      });

      this._cleanup();
    }
  }

  /**
   * Handle enrollment errors
   */
  _handleEnrollmentError(message) {
    const { session_id, error, details } = message;

    if (session_id === this.currentSessionId) {
      this.emit(ENROLLMENT_EVENTS.ERROR, {
        sessionId: session_id,
        error,
        details,
      });
    }
  }

  /**
   * Convert ArrayBuffer to Base64 string
   */
  _bufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Generate unique session ID
   */
  _generateSessionId() {
    return `enroll_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Cleanup enrollment session
   */
  _cleanup() {
    this.currentSessionId = null;
    this.audioChunks = [];
    this.sessionConfig = null;
  }

  /**
   * Get session info
   */
  getSessionInfo() {
    return {
      sessionId: this.currentSessionId,
      audioChunks: this.audioChunks,
      config: this.sessionConfig,
      isActive: !!this.currentSessionId,
    };
  }
}

export default EnrollmentWebSocketService;
