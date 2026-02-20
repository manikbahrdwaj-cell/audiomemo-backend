/**
 * Enhanced WebSocket Client Wrapper
 * Production-ready WebSocket client with:
 * - Automatic reconnection with exponential backoff
 * - Message queuing while disconnected
 * - Heartbeat/keep-alive mechanism
 * - Event-driven architecture
 * - Error handling and recovery
 * - Connection state management
 */

import EventEmitter from './webSocketEventEmitter';
import {
  MESSAGE_TYPES,
  CONNECTION_STATES,
  CONFIG_DEFAULTS,
  ERROR_CODES,
  ERROR_MESSAGES,
  EVENT_TYPES
} from './webSocketConstants';

class WebSocketClientWrapper extends EventEmitter {
  constructor(url, options = {}) {
    super();

    this.url = url;
    this.websocket = null;

    // Connection state
    this.state = CONNECTION_STATES.NOT_INITIALIZED;
    this.connecting = false;
    this.disconnecting = false;

    // Reconnection settings
    this.connectionAttempts = 0;
    this.maxConnectionAttempts = options.maxConnectionAttempts ??
      CONFIG_DEFAULTS.maxConnectionAttempts;
    this.reconnectDelay = options.initialReconnectDelay ??
      CONFIG_DEFAULTS.initialReconnectDelay;
    this.maxReconnectDelay = options.maxReconnectDelay ??
      CONFIG_DEFAULTS.maxReconnectDelay;
    this.reconnectDelayMultiplier = options.reconnectDelayMultiplier ??
      CONFIG_DEFAULTS.reconnectDelayMultiplier;

    // Heartbeat settings
    this.heartbeatInterval = options.heartbeatInterval ??
      CONFIG_DEFAULTS.heartbeatInterval;
    this.heartbeatTimeout = options.heartbeatTimeout ??
      CONFIG_DEFAULTS.heartbeatTimeout;
    this.heartbeatTimer = null;
    this.heartbeatResponseTimer = null;

    // Message settings
    this.messageQueue = [];
    this.messageQueueMaxSize = options.messageQueueMaxSize ??
      CONFIG_DEFAULTS.messageQueueMaxSize;
    this.maxMessageSize = options.maxMessageSize ??
      CONFIG_DEFAULTS.maxMessageSize;
    this.messageTimeout = options.messageTimeout ??
      CONFIG_DEFAULTS.messageTimeout;

    // Message handlers registry
    this.messageHandlers = {};

    // Pending requests (for request-response pattern)
    this.pendingRequests = new Map();
    this.requestIdCounter = 0;

    // Connection timeout
    this.connectionTimeout = options.connectionTimeout ??
      CONFIG_DEFAULTS.connectionTimeout;
    this.connectionTimeoutTimer = null;

    // Debug mode
    this.debug = options.debug ?? false;

    // Custom callbacks for backward compatibility
    this.onOpen = options.onOpen || (() => {});
    this.onClose = options.onClose || (() => {});
    this.onError = options.onError || (err => this.log('error', err));
    this.onMessageReceived = options.onMessage || (() => {});
    this.onConnectionFailure = options.onConnectionFailure || (() => {});

    this.log('info', `WebSocket client initialized with URL: ${url}`);
  }

  /**
   * Internal logging method
   */
  log(level, message, data = null) {
    if (!this.debug) return;

    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [WS] [${level.toUpperCase()}]`;

    if (data) {
      console.log(`${prefix} ${message}`, data);
    } else {
      console.log(`${prefix} ${message}`);
    }
  }

  /**
   * Connect to WebSocket server
   */
  async connect() {
    return new Promise((resolve, reject) => {
      try {
        // If already connected, resolve immediately
        if (this.state === CONNECTION_STATES.CONNECTED) {
          this.log('info', 'Already connected');
          resolve(this);
          return;
        }

        // If already connecting, wait for existing connection
        if (this.state === CONNECTION_STATES.CONNECTING) {
          this.log('info', 'Connection already in progress');
          const checkConnection = setInterval(() => {
            if (this.state === CONNECTION_STATES.CONNECTED) {
              clearInterval(checkConnection);
              resolve(this);
            }
          }, 100);
          return;
        }

        this.setState(CONNECTION_STATES.CONNECTING);
        this.connecting = true;

        // Set connection timeout
        this.connectionTimeoutTimer = setTimeout(() => {
          this.log('error', 'Connection timeout');
          this.handleConnectionError(
            ERROR_CODES.CONNECTION_TIMEOUT,
            new Error('Connection timeout')
          );
          reject(new Error('WebSocket connection timeout'));
        }, this.connectionTimeout);

        this.log('info', `Attempting to connect to ${this.url}`);

        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
          this.clearConnectionTimeout();
          this.log('info', 'WebSocket connected');
          this.connecting = false;
          this.connectionAttempts = 0;
          this.reconnectDelay = CONFIG_DEFAULTS.initialReconnectDelay;
          this.setState(CONNECTION_STATES.CONNECTED);
          this.startHeartbeat();
          this.processMessageQueue();
          this.emit(EVENT_TYPES.CONNECTED);
          this.onOpen();
          resolve(this);
        };

        this.websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            this.log('error', 'Failed to parse WebSocket message', error);
            this.emit(EVENT_TYPES.ERROR, {
              code: ERROR_CODES.INVALID_MESSAGE,
              message: ERROR_MESSAGES[ERROR_CODES.INVALID_MESSAGE],
              error
            });
          }
        };

        this.websocket.onerror = (error) => {
          this.log('error', 'WebSocket error', error);
          this.clearConnectionTimeout();
          this.connecting = false;
          const wsError = error instanceof Event ? new Error('WebSocket error') : error;
          this.handleConnectionError(ERROR_CODES.CONNECTION_FAILED, wsError);
          reject(wsError);
        };

        this.websocket.onclose = () => {
          this.log('info', 'WebSocket disconnected');
          this.clearConnectionTimeout();
          this.connecting = false;
          this.stopHeartbeat();

          if (!this.disconnecting) {
            this.setState(CONNECTION_STATES.DISCONNECTED);
            this.emit(EVENT_TYPES.DISCONNECTED);
            this.onClose();
            this.attemptReconnect();
          } else {
            this.setState(CONNECTION_STATES.DISCONNECTED);
            this.emit(EVENT_TYPES.DISCONNECTED);
            this.onClose();
            this.disconnecting = false;
          }
        };
      } catch (error) {
        this.log('error', 'Failed to create WebSocket', error);
        this.connecting = false;
        this.setState(CONNECTION_STATES.ERROR);
        this.handleConnectionError(ERROR_CODES.UNKNOWN_ERROR, error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    this.log('info', 'Disconnecting WebSocket');
    this.disconnecting = true;
    this.stopHeartbeat();
    this.clearConnectionTimeout();

    if (this.websocket) {
      this.setState(CONNECTION_STATES.DISCONNECTING);
      this.websocket.close();
      this.websocket = null;
    }
  }

  /**
   * Handle incoming message
   */
  handleMessage(message) {
    this.log('info', `Message received: ${message.type || message.event}`);
    this.emit(EVENT_TYPES.MESSAGE, message);
    this.onMessageReceived(message);

    // Handle ping/pong for heartbeat
    if (message.type === MESSAGE_TYPES.PING) {
      this.sendMessage({ type: MESSAGE_TYPES.PONG, timestamp: Date.now() });
      return;
    }

    if (message.type === MESSAGE_TYPES.PONG) {
      this.clearHeartbeatResponseTimer();
      this.emit(EVENT_TYPES.HEARTBEAT);
      return;
    }

    // Handle responses to pending requests
    if (message.request_id && this.pendingRequests.has(message.request_id)) {
      const pending = this.pendingRequests.get(message.request_id);
      this.pendingRequests.delete(message.request_id);
      clearTimeout(pending.timeout);

      if (message.status === 'error') {
        pending.reject(new Error(message.error || 'Request failed'));
      } else {
        pending.resolve(message);
      }
      return;
    }

    // Route to specific message handlers by type
    const handlers = this.messageHandlers[message.type];
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          this.log('error', `Error in handler for message type "${message.type}"`, error);
        }
      });
    }

    // CRITICAL: Also emit events by "event" field if present
    // This allows backend messages with "event" field to trigger frontend listeners
    // Example: Backend sends {event: "verification_result", ...}
    if (message.event) {
      this.log('info', `Emitting event: ${message.event}`);
      this.emit(message.event, message);
    }
  }

  /**
   * Send message
   */
  sendMessage(message, options = {}) {
    if (!this.isConnected()) {
      const shouldQueue = options.queue !== false;
      if (shouldQueue) {
        return this.queueMessage(message);
      } else {
        const error = {
          code: ERROR_CODES.NOT_CONNECTED,
          message: ERROR_MESSAGES[ERROR_CODES.NOT_CONNECTED]
        };
        this.emit(EVENT_TYPES.ERROR, error);
        throw new Error(ERROR_MESSAGES[ERROR_CODES.NOT_CONNECTED]);
      }
    }

    try {
      const payload = JSON.stringify(message);

      if (payload.length > this.maxMessageSize) {
        throw new Error(`Message size exceeds limit: ${payload.length} > ${this.maxMessageSize}`);
      }

      this.websocket.send(payload);
      this.log('info', `Message sent: ${message.type || 'unknown'}`);
      this.emit(EVENT_TYPES.MESSAGE_SENT, message);
      return true;
    } catch (error) {
      this.log('error', 'Failed to send message', error);
      this.emit(EVENT_TYPES.ERROR, {
        code: ERROR_CODES.MESSAGE_SEND_FAILED,
        message: ERROR_MESSAGES[ERROR_CODES.MESSAGE_SEND_FAILED],
        error
      });
      return false;
    }
  }

  /**
   * Send message and wait for response (request-response pattern)
   */
  async sendRequest(message, timeout = this.messageTimeout) {
    return new Promise((resolve, reject) => {
      const requestId = ++this.requestIdCounter;
      message.request_id = requestId;

      const timeoutTimer = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error('Request timeout'));
      }, timeout);

      this.pendingRequests.set(requestId, {
        resolve,
        reject,
        timeout: timeoutTimer
      });

      try {
        this.sendMessage(message, { queue: false });
      } catch (error) {
        this.pendingRequests.delete(requestId);
        clearTimeout(timeoutTimer);
        reject(error);
      }
    });
  }

  /**
   * Queue message for sending when connected
   */
  queueMessage(message) {
    if (this.messageQueue.length >= this.messageQueueMaxSize) {
      const error = {
        code: ERROR_CODES.MESSAGE_QUEUE_FULL,
        message: ERROR_MESSAGES[ERROR_CODES.MESSAGE_QUEUE_FULL]
      };
      this.emit(EVENT_TYPES.ERROR, error);
      this.log('warn', `Message queue full, dropping message: ${message.type}`);
      return false;
    }

    this.messageQueue.push(message);
    this.emit(EVENT_TYPES.MESSAGE_QUEUED, message);
    this.log('info', `Message queued: ${message.type} (queue size: ${this.messageQueue.length})`);
    return true;
  }

  /**
   * Process queued messages
   */
  processMessageQueue() {
    if (!this.isConnected()) return;

    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.sendMessage(message, { queue: false });
    }

    this.log('info', 'Message queue processed');
  }

  /**
   * Register message type handler
   */
  on(eventOrType, handler) {
    // If it's a message type, register as message handler
    if (Object.values(MESSAGE_TYPES).includes(eventOrType)) {
      if (!this.messageHandlers[eventOrType]) {
        this.messageHandlers[eventOrType] = [];
      }
      this.messageHandlers[eventOrType].push(handler);
      return () => this.offMessageType(eventOrType, handler);
    }

    // Otherwise use event emitter
    return super.on(eventOrType, handler);
  }

  /**
   * Unregister message type handler
   */
  offMessageType(messageType, handler) {
    if (this.messageHandlers[messageType]) {
      this.messageHandlers[messageType] = this.messageHandlers[messageType].filter(h => h !== handler);
    }
  }

  /**
   * Send audio chunk
   */
  sendAudioChunk(audioData, metadata = {}) {
    const message = {
      type: MESSAGE_TYPES.AUDIO,
      data: audioData,
      timestamp: Date.now(),
      ...metadata
    };
    return this.sendMessage(message);
  }

  /**
   * Send verification request
   */
  sendVerification(phoneNumber) {
    const message = {
      type: MESSAGE_TYPES.VERIFY,
      phone_number: phoneNumber,
      timestamp: Date.now()
    };
    return this.sendRequest(message);
  }

  /**
   * Send enrollment request
   */
  sendEnrollment(phoneNumber) {
    const message = {
      type: MESSAGE_TYPES.ENROLL,
      phone_number: phoneNumber,
      timestamp: Date.now()
    };
    return this.sendRequest(message);
  }

  /**
   * Send reset command
   */
  sendReset() {
    const message = {
      type: MESSAGE_TYPES.RESET,
      timestamp: Date.now()
    };
    return this.sendMessage(message);
  }

  /**
   * Start heartbeat mechanism
   */
  startHeartbeat() {
    this.stopHeartbeat();
    this.log('info', 'Starting heartbeat');

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.sendMessage(
          {
            type: MESSAGE_TYPES.PING,
            timestamp: Date.now()
          },
          { queue: false }
        );

        // Set timeout for pong response
        this.heartbeatResponseTimer = setTimeout(() => {
          this.log('warn', 'Heartbeat timeout - no pong response');
          this.disconnect();
        }, this.heartbeatTimeout);
      }
    }, this.heartbeatInterval);
  }

  /**
   * Stop heartbeat mechanism
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearHeartbeatResponseTimer();
  }

  /**
   * Clear heartbeat response timer
   */
  clearHeartbeatResponseTimer() {
    if (this.heartbeatResponseTimer) {
      clearTimeout(this.heartbeatResponseTimer);
      this.heartbeatResponseTimer = null;
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  attemptReconnect() {
    if (this.connectionAttempts >= this.maxConnectionAttempts) {
      this.log('error', 'Max reconnection attempts reached');
      this.setState(CONNECTION_STATES.ERROR);
      this.emit(EVENT_TYPES.ERROR, {
        code: ERROR_CODES.MAX_ATTEMPTS_REACHED,
        message: ERROR_MESSAGES[ERROR_CODES.MAX_ATTEMPTS_REACHED]
      });
      this.onConnectionFailure();
      return;
    }

    this.connectionAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(this.reconnectDelayMultiplier, this.connectionAttempts - 1),
      this.maxReconnectDelay
    );

    this.log('info', `Reconnecting in ${delay}ms (attempt ${this.connectionAttempts}/${this.maxConnectionAttempts})`);
    this.setState(CONNECTION_STATES.RECONNECTING);
    this.emit(EVENT_TYPES.RECONNECT_ATTEMPT, { attempt: this.connectionAttempts, delay });

    setTimeout(() => {
      this.connect().catch(error => {
        this.log('error', 'Reconnection failed', error);
      });
    }, delay);
  }

  /**
   * Handle connection error
   */
  handleConnectionError(code, error) {
    this.setState(CONNECTION_STATES.ERROR);
    this.emit(EVENT_TYPES.ERROR, {
      code,
      message: ERROR_MESSAGES[code],
      error
    });
    this.onError(error);
  }

  /**
   * Update connection state
   */
  setState(newState) {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;
      this.log('info', `State changed: ${oldState} -> ${newState}`);
      this.emit(EVENT_TYPES.STATE_CHANGED, { from: oldState, to: newState });
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected() {
    return this.websocket && this.websocket.readyState === WebSocket.OPEN;
  }

  /**
   * Clear connection timeout timer
   */
  clearConnectionTimeout() {
    if (this.connectionTimeoutTimer) {
      clearTimeout(this.connectionTimeoutTimer);
      this.connectionTimeoutTimer = null;
    }
  }

  /**
   * Get connection state
   */
  getState() {
    return this.state;
  }

  /**
   * Get connection readyState
   */
  getReadyState() {
    if (!this.websocket) return null;
    return {
      code: this.websocket.readyState,
      name: ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][this.websocket.readyState]
    };
  }

  /**
   * Get information about the connection
   */
  getConnectionInfo() {
    return {
      state: this.state,
      readyState: this.getReadyState(),
      isConnected: this.isConnected(),
      connectionAttempts: this.connectionAttempts,
      messageQueueSize: this.messageQueue.length,
      pendingRequests: this.pendingRequests.size,
      url: this.url
    };
  }

  /**
   * Get message queue size
   */
  getMessageQueueSize() {
    return this.messageQueue.length;
  }

  /**
   * Clear message queue
   */
  clearMessageQueue() {
    const size = this.messageQueue.length;
    this.messageQueue = [];
    this.log('info', `Message queue cleared (${size} messages dropped)`);
    return size;
  }

  /**
   * Wait for connection to be ready
   */
  waitForConnection(timeout = 5000) {
    return new Promise((resolve, reject) => {
      if (this.isConnected()) {
        resolve();
        return;
      }

      const startTime = Date.now();
      const checkConnection = () => {
        if (this.isConnected()) {
          resolve();
        } else if (Date.now() - startTime > timeout) {
          reject(new Error('Connection timeout'));
        } else {
          setTimeout(checkConnection, 100);
        }
      };

      checkConnection();
    });
  }

  /**
   * Close all connections and clean up
   */
  destroy() {
    this.log('info', 'Destroying WebSocket client');
    this.disconnect();
    this.stopHeartbeat();
    this.clearConnectionTimeout();
    this.clearMessageQueue();
    this.messageHandlers = {};
    this.pendingRequests.clear();
    this.removeAllListeners();
    this.websocket = null;
  }
}

/**
 * Factory function to create WebSocket client
 */
export function createWebSocketClient(url, options = {}) {
  return new WebSocketClientWrapper(url, options);
}

/**
 * Get WebSocket URL from environment or construct from window
 */
export function getWebSocketUrl(basePath = '/ws') {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

  // Check environment variables
  if (process.env.REACT_APP_WS_URL) {
    return process.env.REACT_APP_WS_URL;
  }

  // Check for custom host
  if (process.env.REACT_APP_WS_HOST) {
    return `${protocol}//${process.env.REACT_APP_WS_HOST}${basePath}`;
  }

  // Use current window location
  return `${protocol}//${window.location.host}${basePath}`;
}

export default WebSocketClientWrapper;
