/**
 * React Hook for WebSocket Client
 * Provides easy integration of WebSocket client in React components
 * Handles connection lifecycle and cleanup
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import WebSocketClientWrapper, { getWebSocketUrl } from './webSocketClientWrapper';
import { CONNECTION_STATES, EVENT_TYPES } from './webSocketConstants';

/**
 * Hook to use WebSocket client connection
 *
 * @param {string} url - WebSocket URL (optional, uses default if not provided)
 * @param {object} options - WebSocket client options
 * @param {boolean} autoConnect - Automatically connect on mount (default: true)
 * @returns {object} - WebSocket client instance and connection state
 */
export function useWebSocket(url = null, options = {}, autoConnect = true) {
  const clientRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [state, setState] = useState(CONNECTION_STATES.NOT_INITIALIZED);
  const [error, setError] = useState(null);
  const [messageQueueSize, setMessageQueueSize] = useState(0);

  // Initialize client
  useEffect(() => {
    const wsUrl = url || getWebSocketUrl();

    clientRef.current = new WebSocketClientWrapper(wsUrl, {
      ...options,
      debug: process.env.NODE_ENV === 'development'
    });

    const client = clientRef.current;

    // Set up event listeners
    const unsubscribeConnected = client.on(EVENT_TYPES.CONNECTED, () => {
      setIsConnected(true);
      setError(null);
    });

    const unsubscribeDisconnected = client.on(EVENT_TYPES.DISCONNECTED, () => {
      setIsConnected(false);
    });

    const unsubscribeError = client.on(EVENT_TYPES.ERROR, (errorData) => {
      setError(errorData);
      console.error('WebSocket error:', errorData);
    });

    const unsubscribeStateChanged = client.on(EVENT_TYPES.STATE_CHANGED, ({ to }) => {
      setState(to);
    });

    const unsubscribeMessageQueued = client.on(EVENT_TYPES.MESSAGE_QUEUED, () => {
      setMessageQueueSize(client.getMessageQueueSize());
    });

    // Auto-connect if enabled
    if (autoConnect) {
      client.connect().catch(error => {
        console.error('Failed to connect:', error);
      });
    }

    // Cleanup on unmount
    return () => {
      unsubscribeConnected();
      unsubscribeDisconnected();
      unsubscribeError();
      unsubscribeStateChanged();
      unsubscribeMessageQueued();
      client.destroy();
      clientRef.current = null;
    };
  }, [url, options, autoConnect]);

  return {
    client: clientRef.current,
    isConnected,
    state,
    error,
    messageQueueSize
  };
}

/**
 * Hook to listen for specific message types
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @param {string} messageType - Message type to listen for
 * @param {function} handler - Message handler function
 */
export function useWebSocketMessage(client, messageType, handler) {
  useEffect(() => {
    if (!client || !messageType || !handler) return;

    return client.on(messageType, handler);
  }, [client, messageType, handler]);
}

/**
 * Hook to listen for WebSocket events
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @param {string} eventType - Event type to listen for
 * @param {function} handler - Event handler function
 */
export function useWebSocketEvent(client, eventType, handler) {
  useEffect(() => {
    if (!client || !eventType || !handler) return;

    return client.on(eventType, handler);
  }, [client, eventType, handler]);
}

/**
 * Hook for sending messages via WebSocket
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @returns {function} - Send message function
 */
export function useSendWebSocketMessage(client) {
  return useCallback(
    (message, options) => {
      if (!client) {
        console.error('WebSocket client not initialized');
        return false;
      }
      return client.sendMessage(message, options);
    },
    [client]
  );
}

/**
 * Hook for sending WebSocket request (with response)
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @returns {function} - Send request function
 */
export function useSendWebSocketRequest(client) {
  return useCallback(
    (message, timeout) => {
      if (!client) {
        console.error('WebSocket client not initialized');
        return Promise.reject(new Error('WebSocket client not initialized'));
      }
      return client.sendRequest(message, timeout);
    },
    [client]
  );
}

/**
 * Hook for sending audio chunks
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @returns {function} - Send audio chunk function
 */
export function useSendAudioChunk(client) {
  return useCallback(
    (audioData, metadata = {}) => {
      if (!client) {
        console.error('WebSocket client not initialized');
        return false;
      }
      return client.sendAudioChunk(audioData, metadata);
    },
    [client]
  );
}

/**
 * Hook for verification requests
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @returns {function} - Send verification function
 */
export function useSendVerification(client) {
  return useCallback(
    (phoneNumber) => {
      if (!client) {
        console.error('WebSocket client not initialized');
        return Promise.reject(new Error('WebSocket client not initialized'));
      }
      return client.sendVerification(phoneNumber);
    },
    [client]
  );
}

/**
 * Hook for enrollment requests
 *
 * @param {WebSocketClientWrapper} client - WebSocket client instance
 * @returns {function} - Send enrollment function
 */
export function useSendEnrollment(client) {
  return useCallback(
    (phoneNumber) => {
      if (!client) {
        console.error('WebSocket client not initialized');
        return Promise.reject(new Error('WebSocket client not initialized'));
      }
      return client.sendEnrollment(phoneNumber);
    },
    [client]
  );
}

export default useWebSocket;
