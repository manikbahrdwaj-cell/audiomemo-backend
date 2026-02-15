import { useState, useCallback, useEffect, useRef } from 'react';

/**
 * useChunkProgress Hook
 * Manages chunk processing progress updates from WebSocket
 * 
 * Usage:
 * const { progress, startTracking, stopTracking } = useChunkProgress(websocketConnection);
 */
export function useChunkProgress(webSocketConnection = null) {
  const [progress, setProgress] = useState(null);
  const [isTracking, setIsTracking] = useState(false);
  const messageListenerRef = useRef(null);

  // Handle incoming progress messages
  const handleProgressMessage = useCallback((event) => {
    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      
      if (data.type === 'chunk_progress') {
        setProgress(data.payload);
      }
    } catch (error) {
      console.error('Error parsing progress message:', error);
    }
  }, []);

  // Start tracking progress
  const startTracking = useCallback(() => {
    if (!webSocketConnection) {
      console.warn('No WebSocket connection available for progress tracking');
      return;
    }

    if (isTracking) {
      return;
    }

    setIsTracking(true);
    setProgress(null);

    // Register message listener
    messageListenerRef.current = handleProgressMessage;
    if (webSocketConnection.addEventListener) {
      webSocketConnection.addEventListener('message', messageListenerRef.current);
    }
  }, [webSocketConnection, isTracking, handleProgressMessage]);

  // Stop tracking progress
  const stopTracking = useCallback(() => {
    if (!isTracking) {
      return;
    }

    setIsTracking(false);

    // Unregister message listener
    if (messageListenerRef.current && webSocketConnection) {
      if (webSocketConnection.removeEventListener) {
        webSocketConnection.removeEventListener('message', messageListenerRef.current);
      }
    }
    messageListenerRef.current = null;
  }, [isTracking, webSocketConnection]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTracking();
    };
  }, [stopTracking]);

  return {
    progress,
    isTracking,
    startTracking,
    stopTracking,
    resetProgress: () => setProgress(null),
  };
}

/**
 * useChunkProgressWithParser Hook
 * Advanced hook that parses and manages progress with custom handlers
 */
export function useChunkProgressWithParser(
  webSocketConnection = null,
  onChunkStart = null,
  onChunkComplete = null,
  onProcessingComplete = null,
  onProcessingError = null
) {
  const [progress, setProgress] = useState(null);
  const [processedChunks, setProcessedChunks] = useState([]);
  const [isTracking, setIsTracking] = useState(false);
  const lastChunkRef = useRef(null);

  const handleProgressMessage = useCallback(
    (event) => {
      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

        if (data.type === 'chunk_progress') {
          const payload = data.payload;
          setProgress(payload);

          // Handle chunk transitions
          if (
            lastChunkRef.current &&
            payload.current_chunk > lastChunkRef.current.current_chunk
          ) {
            // New chunk started
            if (onChunkStart) {
              onChunkStart(payload.current_chunk);
            }
          }

          // Handle embedding generation
          if (
            payload.status === 'embedding_generated' &&
            onChunkComplete
          ) {
            onChunkComplete(
              payload.current_chunk,
              payload.current_chunk_info
            );
          }

          // Handle completion
          if (payload.status === 'completed' && onProcessingComplete) {
            onProcessingComplete({
              totalChunks: payload.total_chunks,
              duration: payload.duration_ms,
              timestamp: payload.timestamp,
            });
          }

          // Handle errors
          if (payload.status === 'failed' && onProcessingError) {
            onProcessingError(payload.error_message);
          }

          lastChunkRef.current = payload;
        }
      } catch (error) {
        console.error('Error parsing progress message:', error);
      }
    },
    [onChunkStart, onChunkComplete, onProcessingComplete, onProcessingError]
  );

  const startTracking = useCallback(() => {
    if (!webSocketConnection) {
      console.warn('No WebSocket connection available');
      return;
    }

    setIsTracking(true);
    setProgress(null);
    setProcessedChunks([]);
    lastChunkRef.current = null;

    if (webSocketConnection.addEventListener) {
      webSocketConnection.addEventListener('message', handleProgressMessage);
    }
  }, [webSocketConnection, handleProgressMessage]);

  const stopTracking = useCallback(() => {
    setIsTracking(false);
    if (webSocketConnection && webSocketConnection.removeEventListener) {
      webSocketConnection.removeEventListener('message', handleProgressMessage);
    }
  }, [webSocketConnection, handleProgressMessage]);

  useEffect(() => {
    return () => {
      stopTracking();
    };
  }, [stopTracking]);

  return {
    progress,
    isTracking,
    processedChunks,
    startTracking,
    stopTracking,
    resetProgress: () => {
      setProgress(null);
      setProcessedChunks([]);
      lastChunkRef.current = null;
    },
  };
}

export default useChunkProgress;
