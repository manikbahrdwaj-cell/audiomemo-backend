/**
 * Real-Time Verification WebSocket Service
 * Handles automatic verification on recording start with live chunk processing
 */

import EventEmitter from './webSocketEventEmitter';

export const REALTIME_VERIFICATION_EVENTS = {
  SESSION_CREATED: 'realtimeVerification:session_created',
  CHUNK_RESULT: 'realtimeVerification:chunk_result',
  VERIFIED: 'realtimeVerification:verified',
  UNVERIFIED: 'realtimeVerification:unverified',
  ERROR: 'realtimeVerification:error',
  CONNECTION_CLOSED: 'realtimeVerification:connection_closed',
  GREETING_AUDIO: 'realtimeVerification:greeting_audio',
  AGENT_RESPONSE: 'realtimeVerification:agent_response',
  AGENT_THINKING: 'realtimeVerification:agent_thinking',
};

export const REALTIME_VERIFICATION_STATUS = {
  INITIALIZING: 'initializing',
  READY: 'ready',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  VERIFIED: 'verified',
  UNVERIFIED: 'unverified',
  ERROR: 'error',
};

class RealtimeVerificationService extends EventEmitter {
  constructor() {
    super();
    this.ws = null;
    this.phoneNumber = null;
    this.sessionId = null;
    this.status = REALTIME_VERIFICATION_STATUS.INITIALIZING;
    this.chunkResults = [];
    this.maxChunks = 4;
    this.threshold = 0.75;
    this.isVerified = false;
    this.verificationError = null;
    this.maxChunksReached = false;
  }

  /**
   * Connect and initiate verification for a phone number
   * @param {string} phoneNumber - Phone number to verify
   * @param {number} threshold - Similarity threshold (default 0.75)
   * @returns {Promise<boolean>} - True if connection successful
   */
  async connect(phoneNumber, threshold = 0.75) {
    return new Promise((resolve, reject) => {
      try {
        this.phoneNumber = phoneNumber;
        this.threshold = threshold;
        this.chunkResults = [];

        // Create WebSocket URL
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsBaseUrl = process.env.REACT_APP_WS_URL || `${wsProtocol}//${window.location.host}`;
        const wsUrl = `${wsBaseUrl}/ws/verify/${encodeURIComponent(phoneNumber)}`;

        console.log(`[RealTimeVerification] Connecting to ${wsUrl}`);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log(`[RealTimeVerification] Connected for phone: ${phoneNumber}`);
          this.status = REALTIME_VERIFICATION_STATUS.READY;
          this.emit(REALTIME_VERIFICATION_EVENTS.SESSION_CREATED, {
            phoneNumber,
            threshold,
          });
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this._handleMessage(message);
          } catch (e) {
            console.error('[RealTimeVerification] Error parsing message:', e);
            this.verificationError = 'Invalid message format';
            this.emit(REALTIME_VERIFICATION_EVENTS.ERROR, {
              error: 'invalid_message_format',
            });
          }
        };

        this.ws.onerror = (event) => {
          console.error('[RealTimeVerification] WebSocket error:', event);
          this.status = REALTIME_VERIFICATION_STATUS.ERROR;
          this.verificationError = 'WebSocket error occurred';
          
          // Provide detailed error information
          const errorMessage = event.message || 'WebSocket connection failed. Make sure backend is running on port 8000.';
          
          this.emit(REALTIME_VERIFICATION_EVENTS.ERROR, {
            error: 'websocket_error',
            message: errorMessage,
          });
          reject(new Error(errorMessage));
        };

        this.ws.onclose = (event) => {
          console.log(`[RealTimeVerification] Connection closed. Code: ${event.code}, Reason: ${event.reason}`);
          // Null out the reference so sendAudioChunk detects the close immediately
          this.ws = null;

          const wasCompleted =
            this.status === REALTIME_VERIFICATION_STATUS.COMPLETED ||
            this.status === REALTIME_VERIFICATION_STATUS.VERIFIED ||
            this.status === REALTIME_VERIFICATION_STATUS.UNVERIFIED;

          if (!wasCompleted) {
            // Unexpected close mid-session — surface it as an error
            const reason = event.reason || `WebSocket closed (code ${event.code})`;
            this.status = REALTIME_VERIFICATION_STATUS.ERROR;
            this.verificationError = reason;
            this.emit(REALTIME_VERIFICATION_EVENTS.ERROR, {
              error: 'connection_closed',
              message: 'Connection lost unexpectedly. Please try again.',
            });
          }

          this.emit(REALTIME_VERIFICATION_EVENTS.CONNECTION_CLOSED, {
            code: event.code,
            reason: event.reason,
          });
        };

        // Timeout for connection (10 seconds)
        const connectionTimeout = setTimeout(() => {
          if (this.status === REALTIME_VERIFICATION_STATUS.INITIALIZING) {
            this.ws.close();
            reject(new Error('Connection timeout - Backend may not be running. Ensure backend is started on port 8000.'));
          }
        }, 10000);

        // Clear timeout when connection established or error
        const originalResolve = resolve;
        const wrappedResolve = (value) => {
          clearTimeout(connectionTimeout);
          originalResolve(value);
        };
        resolve = wrappedResolve;

      } catch (e) {
        console.error('[RealTimeVerification] Connection error:', e);
        this.status = REALTIME_VERIFICATION_STATUS.ERROR;
        this.verificationError = e.message;
        this.emit(REALTIME_VERIFICATION_EVENTS.ERROR, {
          error: 'connection_error',
          message: e.message,
        });
        reject(e);
      }
    });
  }

  /**
   * Send audio chunk for verification
   * @param {ArrayBuffer|Blob} audioData - Audio chunk data
   * @returns {Promise<void>}
   */
  async sendAudioChunk(audioData) {
    // Helper: check whether the connection is actually usable right now.
    const isOpen = () => this.ws && this.ws.readyState === WebSocket.OPEN;

    return new Promise((resolve, reject) => {
      if (!isOpen()) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      try {
        if (audioData instanceof ArrayBuffer) {
          // Synchronous path — no FileReader, no race window.
          if (!isOpen()) { reject(new Error('WebSocket not connected')); return; }
          this.ws.send(audioData);
          this.status = REALTIME_VERIFICATION_STATUS.PROCESSING;
          console.log('[RealTimeVerification] Sent audio chunk (ArrayBuffer, bytes:', audioData.byteLength, ')');
          resolve();
          return;
        }

        if (audioData instanceof Blob) {
          // Async FileReader path — re-check connection inside onload because
          // ws.onclose may fire and null out this.ws while the FileReader runs.
          const reader = new FileReader();

          reader.onload = () => {
            const arrayBuffer = reader.result;
            // Re-check: onclose may have nulled this.ws during the async read.
            if (!isOpen()) {
              reject(new Error('WebSocket not connected'));
              return;
            }
            try {
              this.ws.send(arrayBuffer);
              this.status = REALTIME_VERIFICATION_STATUS.PROCESSING;
              console.log('[RealTimeVerification] Sent audio chunk (binary, bytes:', arrayBuffer.byteLength, ')');
              resolve();
            } catch (sendErr) {
              console.error('[RealTimeVerification] Error during ws.send:', sendErr);
              reject(sendErr);
            }
          };

          reader.onerror = () => reject(new Error('Failed to read audio data'));
          reader.readAsArrayBuffer(audioData);
          return;
        }

        reject(new Error('Invalid audio data type'));
      } catch (e) {
        console.error('[RealTimeVerification] Error sending chunk:', e);
        reject(e);
      }
    });
  }

  /**
   * Handle incoming WebSocket message
   * @private
   */
  _handleMessage(message) {
    const { type } = message;

    console.log(`[RealTimeVerification] Received message type: ${type}`, message);

    if (type === 'session_created' || type === 'session_ready') {
      // Backend sends "session_created"; legacy clients may use "session_ready"
      this.sessionId = message.session_id;
      this.maxChunks = message.max_chunks || 4;
      this.threshold = message.threshold || this.threshold;
      console.log(`[RealTimeVerification] Session ready. Max chunks: ${this.maxChunks}, Threshold: ${this.threshold}`);
      this.emit(REALTIME_VERIFICATION_EVENTS.SESSION_CREATED, {
        sessionId: this.sessionId,
        maxChunks: this.maxChunks,
        threshold: this.threshold,
      });
    } else if (type === 'chunk_result') {
      const result = {
        chunkNumber: message.chunk_number,
        maxChunks: message.max_chunks,
        similarityScore: message.similarity_score,
        threshold: message.threshold,
        isMatch: message.is_match,
      };

      this.chunkResults.push(result);
      console.log(
        `[RealTimeVerification] Chunk ${result.chunkNumber} result:`,
        `Similarity: ${(result.similarityScore * 100).toFixed(2)}%`,
        `Match: ${result.isMatch}`
      );

      // Check if verification completed
      if (message.final_status) {
        if (message.final_status === 'verified') {
          console.log(`[RealTimeVerification] VERIFIED at chunk ${result.chunkNumber}`);
          this.status = REALTIME_VERIFICATION_STATUS.VERIFIED;
          this.isVerified = true;
          this.emit(REALTIME_VERIFICATION_EVENTS.VERIFIED, {
            verifiedAtChunk: message.verified_at_chunk,
            results: [...this.chunkResults],
          });
          // Do NOT set COMPLETED — keep the WebSocket alive for agent mode.
        } else if (message.final_status === 'unverified') {
          console.log(`[RealTimeVerification] UNVERIFIED after ${result.chunkNumber} chunks`);
          this.status = REALTIME_VERIFICATION_STATUS.UNVERIFIED;
          this.isVerified = false;
          this.maxChunksReached = true;
          this.emit(REALTIME_VERIFICATION_EVENTS.UNVERIFIED, {
            results: [...this.chunkResults],
          });
          this.status = REALTIME_VERIFICATION_STATUS.COMPLETED;
        }
      } else {
        // Emit chunk result for live update
        this.emit(REALTIME_VERIFICATION_EVENTS.CHUNK_RESULT, result);

        // Check if max chunks reached
        if (result.chunkNumber >= result.maxChunks) {
          this.maxChunksReached = true;
        }
      }
    } else if (type === 'error') {
      console.error('[RealTimeVerification] Error received:', message);
      this.status = REALTIME_VERIFICATION_STATUS.ERROR;
      this.verificationError = message.message || 'Unknown error';
      this.emit(REALTIME_VERIFICATION_EVENTS.ERROR, {
        error: message.error,
        message: message.message,
      });
    } else if (type === 'greeting_audio') {
      this.emit(REALTIME_VERIFICATION_EVENTS.GREETING_AUDIO, {
        audioBase64: message.data || '',
        text: message.text || '',
      });
    } else if (type === 'agent_audio') {
      this.emit(REALTIME_VERIFICATION_EVENTS.AGENT_RESPONSE, {
        audioBase64: message.data || '',
        transcript: message.transcript || '',
        text: message.text || '',
      });
    } else if (type === 'agent_thinking' || type === 'agent_listening') {
      this.emit(REALTIME_VERIFICATION_EVENTS.AGENT_THINKING, {});
    } else if (type === 'audio_ack') {
      // Synchronous ACK from server — ignore silently.
    } else if (type === 'cancelled') {
      console.log('[RealTimeVerification] Verification cancelled');
      this.status = REALTIME_VERIFICATION_STATUS.COMPLETED;
    }
  }

  /**
   * Send keep-alive ping
   */
  sendPing() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }

  /**
   * Cancel ongoing verification
   */
  cancel() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'cancel' }));
      this.ws.close();
    }
  }

  /**
   * Close connection
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Get current verification state
   */
  getState() {
    return {
      phoneNumber: this.phoneNumber,
      sessionId: this.sessionId,
      status: this.status,
      isVerified: this.isVerified,
      chunkResults: [...this.chunkResults],
      maxChunks: this.maxChunks,
      threshold: this.threshold,
      maxChunksReached: this.maxChunksReached,
      error: this.verificationError,
    };
  }
}

export default RealtimeVerificationService;
