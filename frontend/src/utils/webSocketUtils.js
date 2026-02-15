/**
 * WebSocket Integration Utilities
 * Helper functions and utilities for WebSocket-based enrollment/verification
 */

/**
 * Convert Blob to ArrayBuffer
 */
export async function blobToArrayBuffer(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsArrayBuffer(blob);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
}

/**
 * Convert ArrayBuffer to Blob
 */
export function arrayBufferToBlob(buffer, type = 'audio/wav') {
  return new Blob([buffer], { type });
}

/**
 * Encode audio data for transmission
 */
export function encodeAudioData(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Decode audio data from transmission
 */
export function decodeAudioData(encoded) {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Validate phone number format
 */
export function isValidPhoneNumber(phoneNumber) {
  const phoneRegex = /^[\d+\-\s()]{7,}$/;
  return phoneRegex.test(phoneNumber.trim());
}

/**
 * Format phone number for display
 */
export function formatPhoneNumber(phoneNumber) {
  const cleaned = phoneNumber.replace(/\D/g, '').slice(-10);
  return `+1 (${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
}

/**
 * Validate audio duration
 */
export function validateAudioDuration(duration, minSeconds = 2, maxSeconds = 60) {
  return duration >= minSeconds && duration <= maxSeconds;
}

/**
 * Format duration for display
 */
export function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
}

/**
 * Calculate audio quality score (0-1)
 * Based on various metrics
 */
export function calculateQualityScore(audioMetrics) {
  const {
    amplitude = 0.5,
    noiseLevel = 0.3,
    frequencyBalance = 0.7,
    dynamicRange = 0.6,
  } = audioMetrics;

  let score = 0.5;

  // Amplitude contribution (amplitude 0.3-0.9 is good)
  if (amplitude >= 0.3 && amplitude <= 0.9) {
    score += 0.25;
  }

  // Noise level contribution (lower is better)
  if (noiseLevel < 0.4) {
    score += 0.25;
  }

  // Frequency balance contribution
  if (frequencyBalance > 0.6) {
    score += 0.25;
  }

  // Dynamic range contribution
  if (dynamicRange > 0.5) {
    score += 0.25;
  }

  return Math.min(1.0, score);
}

/**
 * Create enrollment batch request
 */
export function createEnrollmentBatchRequest(phoneNumber, audioChunks, sessionId) {
  return {
    type: 'enrollment_batch',
    phone_number: phoneNumber,
    session_id: sessionId,
    chunks: audioChunks.map((chunk, index) => ({
      index: index,
      data: chunk.data,
      timestamp: chunk.timestamp,
      duration: chunk.duration,
      quality: chunk.quality,
    })),
    total_chunks: audioChunks.length,
    metadata: {
      timestamp: new Date().toISOString(),
      client_version: '1.0.0',
    },
  };
}

/**
 * Parse enrollment response
 */
export function parseEnrollmentResponse(response) {
  return {
    success: response.status === 'success' || response.status === 'enrolled',
    vectorId: response.vector_id,
    sessionId: response.session_id,
    status: response.status,
    message: response.message,
    stats: {
      chunksProcessed: response.chunks_processed,
      embeddingDimensions: response.embedding_dimensions,
      processingTime: response.processing_time_ms,
    },
  };
}

/**
 * Parse verification response
 */
export function parseVerificationResponse(response) {
  return {
    success: response.result === 'match',
    result: response.result,
    similarity: response.similarity_score,
    threshold: response.threshold,
    message: response.message,
    attemptInfo: {
      attempt: response.attempt_number,
      remaining: response.remaining_attempts,
    },
  };
}

/**
 * Retry WebSocket operation with exponential backoff
 */
export async function retryOperation(
  operation,
  maxAttempts = 3,
  initialDelay = 1000,
  backoffMultiplier = 2
) {
  let lastError;
  let delay = initialDelay;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, delay));
        delay *= backoffMultiplier;
      }
    }
  }

  throw new Error(`Operation failed after ${maxAttempts} attempts: ${lastError.message}`);
}

/**
 * Create WebSocket message with metadata
 */
export function createWebSocketMessage(type, data, options = {}) {
  return {
    type,
    id: options.id || generateMessageId(),
    timestamp: new Date().toISOString(),
    data,
    metadata: {
      version: '1.0',
      client: 'frontend',
      ...options.metadata,
    },
  };
}

/**
 * Generate unique message ID
 */
export function generateMessageId() {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Validate WebSocket message
 */
export function validateWebSocketMessage(message) {
  const requiredFields = ['type', 'data'];

  for (const field of requiredFields) {
    if (!message.hasOwnProperty(field)) {
      throw new Error(`Missing required field: ${field}`);
    }
  }

  return true;
}

/**
 * Create connection monitor
 */
export class WebSocketConnectionMonitor {
  constructor(wsClient, onStatusChange) {
    this.wsClient = wsClient;
    this.onStatusChange = onStatusChange;
    this.isConnected = false;
    this.lastHeartbeat = null;
    this.missedHeartbeats = 0;
    this.maxMissedHeartbeats = 3;

    this._setupMonitoring();
  }

  _setupMonitoring() {
    this.wsClient.on('connected', () => {
      this.isConnected = true;
      this.missedHeartbeats = 0;
      this.onStatusChange({ status: 'connected' });
    });

    this.wsClient.on('disconnected', () => {
      this.isConnected = false;
      this.onStatusChange({ status: 'disconnected' });
    });

    this.wsClient.on('error', (error) => {
      this.onStatusChange({ status: 'error', error: error.message });
    });

    this.wsClient.on('heartbeat', () => {
      this.lastHeartbeat = Date.now();
      this.missedHeartbeats = 0;
      this.onStatusChange({ status: 'heartbeat', timestamp: this.lastHeartbeat });
    });
  }

  getStatus() {
    return {
      isConnected: this.isConnected,
      lastHeartbeat: this.lastHeartbeat,
      missedHeartbeats: this.missedHeartbeats,
      isHealthy:
        this.isConnected && this.missedHeartbeats < this.maxMissedHeartbeats,
    };
  }

  reset() {
    this.isConnected = false;
    this.lastHeartbeat = null;
    this.missedHeartbeats = 0;
  }
}

/**
 * Create session persistence manager
 */
export class SessionPersistenceManager {
  constructor(storagePrefix = 'ws_session_') {
    this.storagePrefix = storagePrefix;
  }

  saveSession(sessionId, data) {
    try {
      const key = this.storagePrefix + sessionId;
      localStorage.setItem(
        key,
        JSON.stringify({
          ...data,
          savedAt: new Date().toISOString(),
        })
      );
      return true;
    } catch (error) {
      console.error('Failed to save session:', error);
      return false;
    }
  }

  loadSession(sessionId) {
    try {
      const key = this.storagePrefix + sessionId;
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Failed to load session:', error);
      return null;
    }
  }

  deleteSession(sessionId) {
    try {
      const key = this.storagePrefix + sessionId;
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error('Failed to delete session:', error);
      return false;
    }
  }

  getAllSessions() {
    const sessions = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(this.storagePrefix)) {
        try {
          sessions.push(JSON.parse(localStorage.getItem(key)));
        } catch (error) {
          console.error('Failed to parse session:', error);
        }
      }
    }
    return sessions;
  }

  clearOldSessions(maxAgeMinutes = 60) {
    const now = Date.now();
    const maxAge = maxAgeMinutes * 60 * 1000;

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(this.storagePrefix)) {
        try {
          const session = JSON.parse(localStorage.getItem(key));
          const savedTime = new Date(session.savedAt).getTime();

          if (now - savedTime > maxAge) {
            localStorage.removeItem(key);
          }
        } catch (error) {
          console.error('Failed to process session:', error);
        }
      }
    }
  }
}
