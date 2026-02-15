/**
 * WebSocket Context Provider
 * Manages WebSocket connection and services globally
 * Provides enrollment and verification services to all components
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import WebSocketClientWrapper from '../services/webSocketClientWrapper';
import EnrollmentWebSocketService from '../services/enrollmentWebSocketService';
import VerificationWebSocketService from '../services/verificationWebSocketService';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children, wsUrl = 'ws://localhost:8000/ws/voice' }) {
  const [wsClient, setWsClient] = useState(null);
  const [enrollmentService, setEnrollmentService] = useState(null);
  const [verificationService, setVerificationService] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);

  /**
   * Initialize WebSocket client and services
   */
  const initializeWebSocket = useCallback(async () => {
    try {
      const client = new WebSocketClientWrapper(wsUrl, {
        maxConnectionAttempts: 5,
        initialReconnectDelay: 3000,
        maxReconnectDelay: 30000,
        heartbeatInterval: 30000,
        debug: process.env.NODE_ENV === 'development',
      });

      // Setup connection event handlers
      client.on('connected', () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
      });

      client.on('disconnected', () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
      });

      client.on('error', (error) => {
        console.error('WebSocket error:', error);
        setConnectionError(error.message);
      });

      // Connect to server
      await client.connect();
      setWsClient(client);

      // Create service instances
      const enrollment = new EnrollmentWebSocketService(client);
      const verification = new VerificationWebSocketService(client);

      setEnrollmentService(enrollment);
      setVerificationService(verification);

      return { client, enrollment, verification };
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      setConnectionError(error.message);
      throw error;
    }
  }, [wsUrl]);

  /**
   * Initialize on mount
   */
  useEffect(() => {
    initializeWebSocket().catch((error) => {
      console.error('WebSocket initialization error:', error);
    });

    return () => {
      if (wsClient) {
        wsClient.disconnect();
      }
    };
  }, [initializeWebSocket]);

  const value = {
    wsClient,
    enrollmentService,
    verificationService,
    isConnected,
    connectionError,
    reconnect: initializeWebSocket,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

/**
 * Hook to use WebSocket context
 */
export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}

/**
 * Hook to use enrollment service
 */
export function useEnrollmentService() {
  const { enrollmentService } = useWebSocket();
  if (!enrollmentService) {
    throw new Error('Enrollment service not initialized');
  }
  return enrollmentService;
}

/**
 * Hook to use verification service
 */
export function useVerificationService() {
  const { verificationService } = useWebSocket();
  if (!verificationService) {
    throw new Error('Verification service not initialized');
  }
  return verificationService;
}
