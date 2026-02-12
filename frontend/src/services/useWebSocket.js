/**
 * React Hook for WebSocket Integration
 * Manages WebSocket connection, audio recording, and voice operations
 */

import { useEffect, useRef, useCallback, useState, useReducer } from 'react';
import WebSocketClient from './websocketClient';

// Initial state
const initialState = {
  // Connection state
  connected: false,
  connecting: false,
  error: null,
  clientId: null,
  sessionId: null,

  // Audio state
  isRecording: false,
  bytesReceived: 0,
  chunksReceived: 0,
  
  // Operation state
  enrollmentInProgress: false,
  verificationInProgress: false,
  processingAudio: false,
  
  // Results
  lastResult: null,
  enrollmentResult: null,
  verificationResult: null,
  
  // Status messages
  statusMessage: '',
  
  // Statistics
  stats: {
    audioChunksRecorded: 0,
    totalAudioSize: 0,
    averageChunkSize: 0,
    recordingDuration: 0
  }
};

/**
 * State reducer
 */
function stateReducer(state, action) {
  switch (action.type) {
    case 'CONNECTING':
      return { ...state, connecting: true, error: null };
    
    case 'CONNECTED':
      return {
        ...state,
        connected: true,
        connecting: false,
        clientId: action.payload.clientId,
        error: null
      };
    
    case 'DISCONNECTED':
      return {
        ...state,
        connected: false,
        connecting: false,
        clientId: null,
        error: null
      };
    
    case 'CONNECTION_ERROR':
      return {
        ...state,
        connected: false,
        connecting: false,
        error: action.payload
      };
    
    case 'SESSION_INITIALIZED':
      return {
        ...state,
        sessionId: action.payload.sessionId,
        statusMessage: 'Session initialized'
      };
    
    case 'RECORDING_STARTED':
      return {
        ...state,
        isRecording: true,
        statusMessage: 'Recording audio...',
        stats: {
          ...state.stats,
          audioChunksRecorded: 0,
          totalAudioSize: 0
        }
      };
    
    case 'RECORDING_STOPPED':
      return {
        ...state,
        isRecording: false,
        statusMessage: 'Recording stopped'
      };
    
    case 'AUDIO_CHUNK_SENT':
      return {
        ...state,
        stats: {
          ...state.stats,
          audioChunksRecorded: state.stats.audioChunksRecorded + 1,
          totalAudioSize: state.stats.totalAudioSize + action.payload.bytes,
          averageChunkSize: (state.stats.totalAudioSize + action.payload.bytes) / 
                           (state.stats.audioChunksRecorded + 1)
        }
      };
    
    case 'AUDIO_RECEIVED':
      return {
        ...state,
        bytesReceived: action.payload.totalBytes,
        chunksReceived: action.payload.chunkCount,
        statusMessage: `Audio received: ${action.payload.totalBytes} bytes (${action.payload.chunkCount} chunks)`
      };
    
    case 'ENROLLMENT_STARTED':
      return {
        ...state,
        enrollmentInProgress: true,
        statusMessage: 'Enrollment started - Please speak your enrollment phrase',
        enrollmentResult: null
      };
    
    case 'ENROLLMENT_COMPLETED':
      return {
        ...state,
        enrollmentInProgress: false,
        enrollmentResult: action.payload,
        lastResult: action.payload,
        statusMessage: 'Enrollment completed'
      };
    
    case 'VERIFICATION_STARTED':
      return {
        ...state,
        verificationInProgress: true,
        statusMessage: 'Verification started - Please speak to verify your identity',
        verificationResult: null
      };
    
    case 'VERIFICATION_COMPLETED':
      return {
        ...state,
        verificationInProgress: false,
        verificationResult: action.payload,
        lastResult: action.payload,
        statusMessage: 'Verification completed'
      };
    
    case 'PROCESSING_AUDIO':
      return {
        ...state,
        processingAudio: true,
        statusMessage: 'Processing audio...'
      };
    
    case 'PROCESSING_COMPLETE':
      return {
        ...state,
        processingAudio: false
      };
    
    case 'UPDATE_STATUS':
      return {
        ...state,
        statusMessage: action.payload
      };
    
    case 'ERROR':
      return {
        ...state,
        error: action.payload,
        statusMessage: `Error: ${action.payload}`,
        enrollmentInProgress: false,
        verificationInProgress: false,
        processingAudio: false
      };
    
    default:
      return state;
  }
}

/**
 * useWebSocket Hook
 */
export function useWebSocket(wsUrl = null) {
  const clientRef = useRef(null);
  const [state, dispatch] = useReducer(stateReducer, initialState);
  const recordingStartTimeRef = useRef(null);

  /**
   * Initialize WebSocket client
   */
  useEffect(() => {
    const initializeClient = async () => {
      if (!clientRef.current) {
        clientRef.current = new WebSocketClient(wsUrl);

        // Set up event listeners
        clientRef.current.on('connecting', () => {
          dispatch({ type: 'CONNECTING' });
        });

        clientRef.current.on('connected', () => {
          const stats = clientRef.current.getStats();
          dispatch({
            type: 'CONNECTED',
            payload: { clientId: stats.clientId }
          });
        });

        clientRef.current.on('disconnected', () => {
          dispatch({ type: 'DISCONNECTED' });
        });

        clientRef.current.on('server-error', (message) => {
          dispatch({
            type: 'ERROR',
            payload: message.error || 'Server error'
          });
        });

        clientRef.current.on('error', (message) => {
          dispatch({
            type: 'CONNECTION_ERROR',
            payload: message
          });
        });

        clientRef.current.on('initialized', (message) => {
          dispatch({
            type: 'SESSION_INITIALIZED',
            payload: { sessionId: message.sessionId || Date.now() }
          });
        });

        clientRef.current.on('enrollment-started', () => {
          dispatch({ type: 'ENROLLMENT_STARTED' });
        });

        clientRef.current.on('verification-started', () => {
          dispatch({ type: 'VERIFICATION_STARTED' });
        });

        clientRef.current.on('audio-received', (message) => {
          dispatch({
            type: 'AUDIO_RECEIVED',
            payload: {
              totalBytes: message.totalBytes,
              chunkCount: message.chunkCount
            }
          });
        });

        clientRef.current.on('chunk-sent', (data) => {
          dispatch({
            type: 'AUDIO_CHUNK_SENT',
            payload: { bytes: data.bytes }
          });
        });

        clientRef.current.on('processing', () => {
          dispatch({ type: 'PROCESSING_AUDIO' });
        });

        clientRef.current.on('result', (message) => {
          dispatch({ type: 'PROCESSING_COMPLETE' });

          if (message.action === 'enroll') {
            dispatch({
              type: 'ENROLLMENT_COMPLETED',
              payload: message.data
            });
          } else if (message.action === 'verify') {
            dispatch({
              type: 'VERIFICATION_COMPLETED',
              payload: message.data
            });
          }
        });

        clientRef.current.on('recording-started', () => {
          recordingStartTimeRef.current = Date.now();
          dispatch({ type: 'RECORDING_STARTED' });
        });

        clientRef.current.on('recording-stopped', () => {
          if (recordingStartTimeRef.current) {
            const duration = (Date.now() - recordingStartTimeRef.current) / 1000;
            dispatch({
              type: 'UPDATE_STATUS',
              payload: `Recording stopped (${duration.toFixed(2)}s)`
            });
          }
          dispatch({ type: 'RECORDING_STOPPED' });
        });

        // Connect to server
        try {
          await clientRef.current.connect();
        } catch (error) {
          dispatch({
            type: 'CONNECTION_ERROR',
            payload: error.message
          });
        }
      }
    };

    initializeClient();

    // Cleanup on unmount
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
      }
    };
  }, [wsUrl]);

  /**
   * Initialize session
   */
  const initialize = useCallback(async (userId, action = 'enroll') => {
    if (!clientRef.current || !clientRef.current.isConnected()) {
      dispatch({
        type: 'ERROR',
        payload: 'WebSocket not connected'
      });
      return false;
    }

    try {
      await clientRef.current.initialize(userId, action);
      return true;
    } catch (error) {
      dispatch({
        type: 'ERROR',
        payload: error.message
      });
      return false;
    }
  }, []);

  /**
   * Start enrollment
   */
  const startEnrollment = useCallback(async () => {
    if (!clientRef.current || !clientRef.current.isConnected()) {
      dispatch({
        type: 'ERROR',
        payload: 'WebSocket not connected'
      });
      return false;
    }

    try {
      await clientRef.current.startEnrollment();
      return true;
    } catch (error) {
      dispatch({
        type: 'ERROR',
        payload: error.message
      });
      return false;
    }
  }, []);

  /**
   * Start verification
   */
  const startVerification = useCallback(async (enrolledUserId = null) => {
    if (!clientRef.current || !clientRef.current.isConnected()) {
      dispatch({
        type: 'ERROR',
        payload: 'WebSocket not connected'
      });
      return false;
    }

    try {
      await clientRef.current.startVerification(enrolledUserId);
      return true;
    } catch (error) {
      dispatch({
        type: 'ERROR',
        payload: error.message
      });
      return false;
    }
  }, []);

  /**
   * Start recording audio
   */
  const startRecording = useCallback(async () => {
    if (!clientRef.current) {
      dispatch({
        type: 'ERROR',
        payload: 'WebSocket client not initialized'
      });
      return false;
    }

    try {
      const success = await clientRef.current.startRecording();
      if (!success) {
        dispatch({
          type: 'ERROR',
          payload: 'Failed to start recording'
        });
      }
      return success;
    } catch (error) {
      dispatch({
        type: 'ERROR',
        payload: error.message
      });
      return false;
    }
  }, []);

  /**
   * Stop recording and process
   */
  const stopRecordingAndProcess = useCallback(async () => {
    if (!clientRef.current) {
      dispatch({
        type: 'ERROR',
        payload: 'WebSocket client not initialized'
      });
      return null;
    }

    try {
      await clientRef.current.stopRecording();

      // Wait for result
      const result = await clientRef.current.stopAudio();
      return result;
    } catch (error) {
      dispatch({
        type: 'ERROR',
        payload: error.message
      });
      return null;
    }
  }, []);

  /**
   * Get connection status
   */
  const isConnected = useCallback(() => {
    return clientRef.current && clientRef.current.isConnected();
  }, []);

  /**
   * Get client statistics
   */
  const getStats = useCallback(() => {
    if (!clientRef.current) return null;
    return clientRef.current.getStats();
  }, []);

  /**
   * Disconnect
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      dispatch({ type: 'DISCONNECTED' });
    }
  }, []);

  return {
    // State
    connected: state.connected,
    connecting: state.connecting,
    error: state.error,
    clientId: state.clientId,
    sessionId: state.sessionId,
    isRecording: state.isRecording,
    enrollmentInProgress: state.enrollmentInProgress,
    verificationInProgress: state.verificationInProgress,
    processingAudio: state.processingAudio,
    statusMessage: state.statusMessage,
    bytesReceived: state.bytesReceived,
    chunksReceived: state.chunksReceived,
    
    // Results
    lastResult: state.lastResult,
    enrollmentResult: state.enrollmentResult,
    verificationResult: state.verificationResult,
    
    // Statistics
    stats: state.stats,
    
    // Methods
    initialize,
    startEnrollment,
    startVerification,
    startRecording,
    stopRecordingAndProcess,
    isConnected,
    getStats,
    disconnect
  };
}

export default useWebSocket;
