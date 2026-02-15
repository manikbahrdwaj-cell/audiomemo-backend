/**
 * WebSocket Client Service
 * Manages WebSocket connections for real-time audio streaming and verification
 */

class WebSocketClient {
  constructor(url, options = {}) {
    this.url = url;
    this.websocket = null;
    this.connecting = false;
    this.connectionAttempts = 0;
    this.maxConnectionAttempts = options.maxConnectionAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 3000;
    
    // Keep-alive configuration
    this.keepAliveInterval = options.keepAliveInterval || 30000; // 30 seconds
    this.keepAliveTimer = null;

    // Event handlers
    this.onOpen = options.onOpen || (() => {});
    this.onClose = options.onClose || (() => {});
    this.onError = options.onError || (err => console.error('WebSocket error:', err));
    this.onMessage = options.onMessage || (() => {});
    this.onConnectionFailure = options.onConnectionFailure || (() => {});

    // Message handlers registry
    this.messageHandlers = {};
  }

  /**
   * Connect to WebSocket server
   */
  async connect() {
    return new Promise((resolve, reject) => {
      try {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          resolve(this.websocket);
          return;
        }

        this.connecting = true;
        this.websocket = new WebSocket(this.url);

        this.websocket.onopen = () => {
          console.log('WebSocket connected:', this.url);
          this.connecting = false;
          this.connectionAttempts = 0;
          this.onOpen();
          // Start keep-alive timer
          this.startKeepAlive();
          resolve(this.websocket);
        };

        this.websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.onMessage(message);
            this.handleMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.connecting = false;
          this.onError(error);
          reject(error);
        };

        this.websocket.onclose = () => {
          console.log('WebSocket disconnected');
          this.connecting = false;
          this.stopKeepAlive();
          this.onClose();
          this.attemptReconnect();
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        this.connecting = false;
        this.onError(error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.websocket) {
      this.stopKeepAlive();
      this.websocket.close();
      this.websocket = null;
    }
  }

  /**
   * Send audio chunk for streaming
   */
  sendAudioChunk(audioData, metadata = {}) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'audio',
      data: audioData,
      timestamp: Date.now(),
      ...metadata
    };

    this.websocket.send(JSON.stringify(message));
  }

  /**
   * Send verification request
   */
  sendVerification(phoneNumber) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'verify',
      phone_number: phoneNumber,
      timestamp: Date.now()
    };

    this.websocket.send(JSON.stringify(message));
  }

  /**
   * Send enrollment request
   */
  sendEnrollment(phoneNumber) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'enroll',
      phone_number: phoneNumber,
      timestamp: Date.now()
    };

    this.websocket.send(JSON.stringify(message));
  }

  /**
   * Send custom message (synchronous)
   */
  sendMessage(message) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    if (typeof message === 'object') {
      this.websocket.send(JSON.stringify(message));
    } else {
      this.websocket.send(message);
    }
  }

  /**
   * Send message (async/Promise-based)
   * Ensures message is sent and returns a promise
   */
  async send(message) {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    try {
      const messageData = typeof message === 'object' ? JSON.stringify(message) : message;
      this.websocket.send(messageData);
      
      // Return a promise that resolves immediately
      // In a production system, you might wait for an ACK from server
      return new Promise((resolve) => {
        setTimeout(() => resolve(true), 0);
      });
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      throw error;
    }
  }

  /**
   * Send ping (keep-alive)
   */
  sendPing() {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      return;
    }

    const message = {
      type: 'ping',
      timestamp: Date.now()
    };

    this.websocket.send(JSON.stringify(message));
  }

  /**
   * Reset audio buffer on server
   */
  sendReset() {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'reset',
      timestamp: Date.now()
    };

    this.websocket.send(JSON.stringify(message));
  }

  /**
   * Register message type handler
   */
  on(messageType, handler) {
    if (!this.messageHandlers[messageType]) {
      this.messageHandlers[messageType] = [];
    }
    this.messageHandlers[messageType].push(handler);
  }

  /**
   * Handle incoming message
   */
  handleMessage(message) {
    const { type } = message;
    if (this.messageHandlers[type]) {
      this.messageHandlers[type].forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          console.error(`Error in handler for message type "${type}":`, error);
        }
      });
    }
  }

  /**
   * Attempt to reconnect
   */
  attemptReconnect() {
    if (this.connectionAttempts >= this.maxConnectionAttempts) {
      console.error('Max connection attempts reached');
      this.onConnectionFailure();
      return;
    }

    this.connectionAttempts++;
    console.log(`Reconnecting... (attempt ${this.connectionAttempts})`);

    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, this.reconnectDelay);
  }

  /**
   * Check connection status
   */
  isConnected() {
    return this.websocket && this.websocket.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection state
   */
  getState() {
    if (!this.websocket) return 'NOT_INITIALIZED';

    switch (this.websocket.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'CLOSED';
      default:
        return 'UNKNOWN';
    }
  }

  /**
   * Wait for connection to be ready
   */
  waitForConnection(timeout = 5000) {
    return new Promise((resolve, reject) => {
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
   * Start keep-alive heartbeat to prevent connection from closing
   */
  startKeepAlive() {
    this.stopKeepAlive(); // Clear any existing timer
    
    this.keepAliveTimer = setInterval(() => {
      if (this.isConnected()) {
        try {
          this.sendPing();
        } catch (error) {
          console.warn('Failed to send keep-alive ping:', error);
        }
      }
    }, this.keepAliveInterval);
    
    console.log('Keep-alive heartbeat started (interval: ' + this.keepAliveInterval + 'ms)');
  }

  /**
   * Stop keep-alive heartbeat
   */
  stopKeepAlive() {
    if (this.keepAliveTimer) {
      clearInterval(this.keepAliveTimer);
      this.keepAliveTimer = null;
      console.log('Keep-alive heartbeat stopped');
    }
  }

/**
 * Create and return a WebSocket client instance
 */
export function createWebSocketClient(url, options = {}) {
  return new WebSocketClient(url, options);
}

/**
 * Get WebSocket URL from environment or default
 */
export function getWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = process.env.REACT_APP_WS_URL || `${protocol}//${window.location.host}`;
  return `${host}/ws`;
}

export default WebSocketClient;
