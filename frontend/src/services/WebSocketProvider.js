/**
 * WebSocket Context Provider
 * Manages global WebSocket state and provides it to all components
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import webSocketService from './websocketService';

const WebSocketContext = createContext(null);

/**
 * Initial state
 */
const initialState = {
  connected: false,
  connecting: false,
  error: null,
  clientId: null,
  status: 'idle', // idle, connecting, connected, reconnecting, disconnected, error
  connectionQuality: 'unknown', // excellent, good, fair, poor, unknown
  connectionAttempts: 0,
  sessionData: null,
  recentErrors: []
};

/**
 * Reducer function
 */
function wsReducer(state, action) {
  switch (action.type) {
    case 'CONNECTING':
      return { ...state, connecting: true, status: 'connecting', error: null };
    
    case 'CONNECTED':
      return {
        ...state,
        connected: true,
        connecting: false,
        status: 'connected',
        clientId: action.payload,
        error: null,
        connectionAttempts: 0
      };
    
    case 'DISCONNECTED':
      return {
        ...state,
        connected: false,
        connecting: false,
        status: 'disconnected',
        clientId: null
      };
    
    case 'ERROR':
      return {
        ...state,
        error: action.payload,
        status: 'error',
        connecting: false,
        recentErrors: [
          ...state.recentErrors.slice(-4),
          { message: action.payload, timestamp: Date.now() }
        ]
      };
    
    case 'RECONNECTING':
      return {
        ...state,
        connecting: true,
        status: 'reconnecting',
        connectionAttempts: action.payload.attempt || state.connectionAttempts + 1
      };
    
    case 'SET_SESSION_DATA':
      return {
        ...state,
        sessionData: action.payload
      };
    
    case 'UPDATE_CONNECTION_QUALITY':
      return {
        ...state,
        connectionQuality: action.payload
      };
    
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null
      };
    
    default:
      return state;
  }
}

/**
 * WebSocket Provider Component
 */
export function WebSocketProvider({ children, wsUrl = null }) {
  const [state, dispatch] = useReducer(wsReducer, initialState);

  // Initialize connection
  useEffect(() => {
    const initializeConnection = async () => {
      // Set custom URL if provided
      if (wsUrl) {
        webSocketService.url = wsUrl;
      }

      dispatch({ type: 'CONNECTING' });

      try {
        if (!webSocketService.isConnected()) {
          await webSocketService.connect();
        } else {
          dispatch({
            type: 'CONNECTED',
            payload: webSocketService.client?.clientId
          });
        }
      } catch (error) {
        dispatch({
          type: 'ERROR',
          payload: error.message || 'Failed to connect'
        });
      }
    };

    initializeConnection();

    // Register event listeners
    const unsubConnect = webSocketService.on('connected', () => {
      dispatch({
        type: 'CONNECTED',
        payload: webSocketService.client?.clientId
      });
    });

    const unsubDisconnect = webSocketService.on('disconnected', () => {
      dispatch({ type: 'DISCONNECTED' });
    });

    const unsubError = webSocketService.on('error', (error) => {
      dispatch({
        type: 'ERROR',
        payload: error.message || String(error)
      });
    });

    const unsubReconnecting = webSocketService.on('reconnecting', (data) => {
      dispatch({
        type: 'RECONNECTING',
        payload: data
      });
    });

    const unsubReconnected = webSocketService.on('reconnected', () => {
      dispatch({
        type: 'CONNECTED',
        payload: webSocketService.client?.clientId
      });
    });

    return () => {
      unsubConnect();
      unsubDisconnect();
      unsubError();
      unsubReconnecting();
      unsubReconnected();
    };
  }, [wsUrl]);

  // Context methods
  const connect = useCallback(async () => {
    if (state.connected) return;
    dispatch({ type: 'CONNECTING' });
    try {
      await webSocketService.connect();
    } catch (error) {
      dispatch({
        type: 'ERROR',
        payload: error.message || 'Connection failed'
      });
      throw error;
    }
  }, [state.connected]);

  const disconnect = useCallback(() => {
    webSocketService.disconnect();
    dispatch({ type: 'DISCONNECTED' });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  const setSessionData = useCallback((data) => {
    dispatch({
      type: 'SET_SESSION_DATA',
      payload: data
    });
  }, []);

  const getStatus = useCallback(() => {
    return webSocketService.getStatus();
  }, []);

  const value = {
    // State
    connected: state.connected,
    connecting: state.connecting,
    error: state.error,
    clientId: state.clientId,
    status: state.status,
    connectionQuality: state.connectionQuality,
    connectionAttempts: state.connectionAttempts,
    sessionData: state.sessionData,
    recentErrors: state.recentErrors,

    // Methods
    connect,
    disconnect,
    clearError,
    setSessionData,
    getStatus,
    
    // Direct service access for advanced usage
    service: webSocketService
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
export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider');
  }
  return context;
}

export default WebSocketContext;
