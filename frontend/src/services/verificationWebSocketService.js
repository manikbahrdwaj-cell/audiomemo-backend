/**
 * Verification WebSocket Service
 * Handles real-time voice verification with session management
 * Provides verification state tracking, attempt management, and result handling
 */

import EventEmitter from './webSocketEventEmitter';
import { MESSAGE_TYPES, RESPONSE_STATUS } from './webSocketConstants';

export const VERIFICATION_EVENTS = {
  SESSION_CREATED: 'verification:session_created',
  PROCESSING: 'verification:processing',
  ATTEMPT_SUBMITTED: 'verification:attempt_submitted',
  PROCESSING_AUDIO: 'verification:processing_audio',
  COMPARING: 'verification:comparing',
  STATUS_CHANGED: 'verification:status_changed',
  VERIFIED: 'verification:verified',
  REJECTED: 'verification:rejected',
  COMPLETED: 'verification:completed',
  ERROR: 'verification:error',
  CANCELLED: 'verification:cancelled',
  ATTEMPT_LIMIT_REACHED: 'verification:attempt_limit_reached',
};

export const VERIFICATION_STATUS = {
  INITIALIZING: 'initializing',
  ACTIVE: 'active',
  PROCESSING: 'processing',
  COMPARING: 'comparing',
  COMPLETED: 'completed',
  VERIFIED: 'verified',
  REJECTED: 'rejected',
  FAILED: 'failed',
  EXPIRED: 'expired',
  CANCELLED: 'cancelled',
};

export const VERIFICATION_RESULT = {
  MATCH: 'match',
  MISMATCH: 'mismatch',
  NOT_ENROLLED: 'not_enrolled',
  ERROR: 'error',
  TIMEOUT: 'timeout',
  CANCELLED: 'cancelled',
};

class VerificationWebSocketService extends EventEmitter {
  constructor(webSocketClient) {
    super();
    this.wsClient = webSocketClient;
    this.verificationSessions = new Map();
    this.currentSessionId = null;
    this.phoneNumber = null;
    this.sessionConfig = null;
    this.attemptCount = 0;
    this.maxAttempts = 3;

    this._setupMessageHandlers();
    this._setupErrorHandlers();
  }

  /**
   * Setup WebSocket message handlers for verification
   */
  _setupMessageHandlers() {
    console.log('Setting up WebSocket message handlers for verification');
    
    this.wsClient.on(MESSAGE_TYPES.VERIFY, (message) => {
      this._handleVerificationMessage(message);
    });

    this.wsClient.on(MESSAGE_TYPES.VERIFY_CONFIRMED, (message) => {
      this._handleVerificationConfirmation(message);
    });

    this.wsClient.on('verification_status', (message) => {
      this._handleVerificationStatus(message);
    });

    // Handle verification result messages from backend
    // CRITICAL: This listener receives the "verification_result" event from backend
    console.log('Registering listener for "verification_result" event');
    this.wsClient.on('verification_result', (message) => {
      console.log('verification_result event received in service:', message);
      this._handleVerificationResultMessage(message);
    });
  }

  /**
   * Setup error handlers
   */
  _setupErrorHandlers() {
    this.wsClient.on(MESSAGE_TYPES.ERROR, (message) => {
      if (message.context === 'verification') {
        this._handleVerificationError(message);
      }
    });
  }

  /**
   * Initiate verification session
   * @param {string} phoneNumber - Phone number to verify
   * @param {object} config - Verification configuration
   */
  async startVerification(phoneNumber, config = {}) {
    try {
      const sessionId = this._generateSessionId();
      this.currentSessionId = sessionId;
      this.phoneNumber = phoneNumber;
      this.attemptCount = 0;

      const defaultConfig = {
        similarity_threshold: 0.85,
        max_attempts: 3,
        attempt_timeout_seconds: 60,
        session_timeout_seconds: 300,
        ...config,
      };

      this.sessionConfig = defaultConfig;
      this.maxAttempts = defaultConfig.max_attempts;

      // Create verification session
      const verificationRequest = {
        type: MESSAGE_TYPES.VERIFY,
        action: 'start_session',
        session_id: sessionId,
        phone_number: phoneNumber,
        config: defaultConfig,
      };

      await this.wsClient.send(verificationRequest);

      this.emit(VERIFICATION_EVENTS.SESSION_CREATED, {
        sessionId,
        phoneNumber,
        config: defaultConfig,
      });

      return sessionId;
    } catch (error) {
      this.emit(VERIFICATION_EVENTS.ERROR, {
        error: error.message,
        stage: 'initialization',
      });
      throw error;
    }
  }

  /**
   * Submit audio for verification
   * @param {ArrayBuffer|Blob} audioData - Audio data to verify
   * @param {boolean} isChunk - Whether this is a chunk or complete audio
   */
  async submitAudio(audioData, isChunk = false) {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active verification session');
      }

      this.attemptCount++;

      if (this.attemptCount > this.maxAttempts) {
        this.emit(VERIFICATION_EVENTS.ATTEMPT_LIMIT_REACHED, {
          sessionId: this.currentSessionId,
          maxAttempts: this.maxAttempts,
        });
        throw new Error('Maximum verification attempts reached');
      }

      // Convert Blob to ArrayBuffer if needed
      const buffer = audioData instanceof Blob
        ? await audioData.arrayBuffer()
        : audioData;

      this.emit(VERIFICATION_EVENTS.PROCESSING_AUDIO, {
        sessionId: this.currentSessionId,
        attemptNumber: this.attemptCount,
        audioSize: buffer.byteLength,
      });

      const audioMessage = {
        type: MESSAGE_TYPES.AUDIO,
        action: 'verify_audio',
        session_id: this.currentSessionId,
        attempt_number: this.attemptCount,
        audio_data: this._bufferToBase64(buffer),
        is_chunk: isChunk,
        timestamp: new Date().toISOString(),
      };

      await this.wsClient.send(audioMessage);

      this.emit(VERIFICATION_EVENTS.ATTEMPT_SUBMITTED, {
        sessionId: this.currentSessionId,
        attemptNumber: this.attemptCount,
        remainingAttempts: this.maxAttempts - this.attemptCount,
      });

      return true;
    } catch (error) {
      this.emit(VERIFICATION_EVENTS.ERROR, {
        error: error.message,
        stage: 'audio_submission',
        attemptNumber: this.attemptCount,
      });
      throw error;
    }
  }

  /**
   * Cancel verification session
   */
  async cancelVerification() {
    try {
      if (!this.currentSessionId) {
        throw new Error('No active verification session');
      }

      const cancelMessage = {
        type: MESSAGE_TYPES.VERIFY,
        action: 'cancel',
        session_id: this.currentSessionId,
      };

      await this.wsClient.send(cancelMessage);
      this._cleanup();

      this.emit(VERIFICATION_EVENTS.CANCELLED, {
        sessionId: this.currentSessionId,
      });

      return true;
    } catch (error) {
      this.emit(VERIFICATION_EVENTS.ERROR, {
        error: error.message,
        stage: 'cancellation',
      });
      throw error;
    }
  }

  /**
   * Get verification progress
   */
  getProgress() {
    return {
      sessionId: this.currentSessionId,
      phoneNumber: this.phoneNumber,
      attemptNumber: this.attemptCount,
      maxAttempts: this.maxAttempts,
      remainingAttempts: Math.max(0, this.maxAttempts - this.attemptCount),
      progressPercentage: (this.attemptCount / this.maxAttempts) * 100,
    };
  }

  /**
   * Handle verification messages
   */
  _handleVerificationMessage(message) {
    const { action, session_id, status, details, result } = message;

    if (action === 'processing') {
      this.emit(VERIFICATION_EVENTS.PROCESSING, {
        sessionId: session_id,
        stage: details?.stage,
        progress: details?.progress,
      });
    }

    if (action === 'comparing') {
      this.emit(VERIFICATION_EVENTS.COMPARING, {
        sessionId: session_id,
        similarity: details?.similarity_score,
        threshold: details?.threshold,
      });
    }

    if (action === 'result') {
      this._handleVerificationResult(session_id, result, details);
    }
  }

  /**
   * Handle verification result
   */
  _handleVerificationResult(sessionId, result, details) {
    if (result === VERIFICATION_RESULT.MATCH) {
      this.emit(VERIFICATION_EVENTS.VERIFIED, {
        sessionId,
        result,
        similarity: details?.similarity_score,
        similarity_score: details?.similarity_score,
        threshold: details?.threshold,
        confidence: details?.confidence,
        metrics: details?.metrics, // Include metrics with cosine_similarity
        attemptNumber: this.attemptCount,
      });
    } else if (result === VERIFICATION_RESULT.MISMATCH) {
      this.emit(VERIFICATION_EVENTS.REJECTED, {
        sessionId,
        result,
        similarity: details?.similarity_score,
        similarity_score: details?.similarity_score,
        threshold: details?.threshold,
        confidence: details?.confidence,
        metrics: details?.metrics, // Include metrics with cosine_similarity
        remainingAttempts: this.maxAttempts - this.attemptCount,
      });
    } else {
      this.emit(VERIFICATION_EVENTS.COMPLETED, {
        sessionId,
        result,
        details,
        metrics: details?.metrics, // Include metrics with cosine_similarity
      });
    }
  }

  /**
   * Handle verification status updates
   */
  _handleVerificationStatus(message) {
    const { session_id, status, details } = message;

    if (session_id === this.currentSessionId) {
      this.emit(VERIFICATION_EVENTS.STATUS_CHANGED, {
        status,
        details,
      });
    }
  }

  /**
   * Handle verification confirmation
   */
  _handleVerificationConfirmation(message) {
    const {
      session_id,
      status,
      result,
      similarity,
      threshold,
      attempt_info,
    } = message;

    if (session_id === this.currentSessionId) {
      if (result === VERIFICATION_RESULT.MATCH) {
        this.emit(VERIFICATION_EVENTS.VERIFIED, {
          sessionId: session_id,
          status,
          result,
          similarity,
          threshold,
          attemptInfo: attempt_info,
        });
      } else {
        this.emit(VERIFICATION_EVENTS.REJECTED, {
          sessionId: session_id,
          status,
          result,
          similarity,
          threshold,
          remainingAttempts: this.maxAttempts - this.attemptCount,
        });
      }

      this._cleanup();
    }
  }

  /**
   * Handle direct verification result message from backend
   * This handles the comprehensive verification result with all metrics
   */
  _handleVerificationResultMessage(message) {
    const { data, status } = message;
    
    console.log('Verification result message received:', { data, status });
    
    if (!data) {
      console.warn('Verification result message missing data field', message);
      return;
    }

    const {
      phone_number,
      similarity_score,
      is_match,
      threshold,
      confidence,
      metrics,
      match_id,
      timestamp,
    } = data;

    console.log('Processing verification result:', { is_match, phone_number, similarity_score });

    // Emit verified/rejected event based on is_match
    if (is_match) {
      console.log('✓ Voice verification PASSED - Emitting VERIFIED event');
      this.emit(VERIFICATION_EVENTS.VERIFIED, {
        sessionId: this.currentSessionId,
        result: VERIFICATION_RESULT.MATCH,
        similarity: similarity_score,
        similarity_score,
        threshold,
        confidence,
        metrics, // Include complete metrics object with cosine_similarity
        match_id,
        timestamp,
        phoneNumber: phone_number,
      });
    } else {
      console.log('✗ Voice verification FAILED - Emitting REJECTED event');
      this.emit(VERIFICATION_EVENTS.REJECTED, {
        sessionId: this.currentSessionId,
        result: VERIFICATION_RESULT.MISMATCH,
        similarity: similarity_score,
        similarity_score,
        threshold,
        confidence,
        metrics, // Include complete metrics object with cosine_similarity
        match_id,
        timestamp,
        phoneNumber: phone_number,
        remainingAttempts: this.maxAttempts - this.attemptCount,
      });
    }

    this._cleanup();
  }

  /**
   * Handle verification errors
   */
  _handleVerificationError(message) {
    const { session_id, error, details } = message;

    if (session_id === this.currentSessionId) {
      this.emit(VERIFICATION_EVENTS.ERROR, {
        sessionId: session_id,
        error,
        details,
      });
    }
  }

  /**
   * Convert ArrayBuffer to Base64
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
    return `verify_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Cleanup verification session
   */
  _cleanup() {
    this.currentSessionId = null;
    this.phoneNumber = null;
    this.sessionConfig = null;
    this.attemptCount = 0;
  }

  /**
   * Get session info
   */
  getSessionInfo() {
    return {
      sessionId: this.currentSessionId,
      phoneNumber: this.phoneNumber,
      attemptCount: this.attemptCount,
      maxAttempts: this.maxAttempts,
      config: this.sessionConfig,
      isActive: !!this.currentSessionId,
    };
  }
}

export default VerificationWebSocketService;
