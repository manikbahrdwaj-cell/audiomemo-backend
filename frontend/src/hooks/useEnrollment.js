/**
 * useEnrollment Hook
 * Custom React hook for enrollment WebSocket operations
 * Provides enrollment state management and event handling
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { ENROLLMENT_EVENTS, ENROLLMENT_STATUS } from '../services/enrollmentWebSocketService';

export function useEnrollment(enrollmentService) {
  const [sessionId, setSessionId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [status, setStatus] = useState(ENROLLMENT_STATUS.INITIALIZING);
  const [audioChunksCollected, setAudioChunksCollected] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [stats, setStats] = useState({
    vectorId: null,
    chunksProcessed: 0,
    embeddingStats: null,
  });

  const progressRef = useRef(0);

  /**
   * Start enrollment session
   */
  const startEnrollment = useCallback(
    async (phone, config = {}) => {
      try {
        setError(null);
        setSuccessMessage(null);
        setPhoneNumber(phone);
        setStatus(ENROLLMENT_STATUS.ACTIVE);
        setAudioChunksCollected(0);

        const newSessionId = await enrollmentService.startEnrollment(phone, config);
        setSessionId(newSessionId);

        return newSessionId;
      } catch (err) {
        const errorMsg = err.message || 'Failed to start enrollment';
        setError(errorMsg);
        setStatus(ENROLLMENT_STATUS.ERROR);
        throw err;
      }
    },
    [enrollmentService]
  );

  /**
   * Submit audio chunk
   */
  const submitChunk = useCallback(
    async (audioData, chunkIndex) => {
      try {
        if (!sessionId) {
          throw new Error('No active enrollment session');
        }

        setIsProcessing(true);
        setError(null);

        await enrollmentService.submitAudioChunk(audioData, chunkIndex);

        setAudioChunksCollected((prev) => prev + 1);
        progressRef.current = (audioChunksCollected + 1) / 10 * 100;
        setProgress(progressRef.current);

        return true;
      } catch (err) {
        const errorMsg = err.message || 'Failed to submit audio chunk';
        setError(errorMsg);
        throw err;
      } finally {
        setIsProcessing(false);
      }
    },
    [sessionId, audioChunksCollected, enrollmentService]
  );

  /**
   * Complete enrollment
   */
  const completeEnrollment = useCallback(async () => {
    try {
      if (!sessionId) {
        throw new Error('No active enrollment session');
      }

      setIsProcessing(true);
      setError(null);
      setStatus(ENROLLMENT_STATUS.FINALIZING);

      await enrollmentService.completeEnrollment();
      return true;
    } catch (err) {
      const errorMsg = err.message || 'Failed to complete enrollment';
      setError(errorMsg);
      setStatus(ENROLLMENT_STATUS.ERROR);
      throw err;
    } finally {
      setIsProcessing(false);
    }
  }, [sessionId, enrollmentService]);

  /**
   * Cancel enrollment
   */
  const cancelEnrollment = useCallback(async () => {
    try {
      await enrollmentService.cancelEnrollment();
      setSessionId(null);
      setStatus(ENROLLMENT_STATUS.CANCELLED);
      return true;
    } catch (err) {
      const errorMsg = err.message || 'Failed to cancel enrollment';
      setError(errorMsg);
      throw err;
    }
  }, [enrollmentService]);

  /**
   * Setup event listeners
   */
  useEffect(() => {
    if (!enrollmentService) return;

    const handleStatusChanged = (data) => {
      setStatus(data.status);
      if (data.error) {
        setError(data.error);
      }
    };

    const handleChunkProcessed = (data) => {
      setStatus(ENROLLMENT_STATUS.PROCESSING);
    };

    const handleCompleted = (data) => {
      setStatus(ENROLLMENT_STATUS.COMPLETED);
      setStats({
        vectorId: data.vectorId,
        chunksProcessed: data.chunksProcessed,
        embeddingStats: data.embeddingStats,
      });
      setSuccessMessage(
        `Enrollment completed successfully! ${data.chunksProcessed} chunks processed.`
      );
      setSessionId(null);
    };

    const handleError = (data) => {
      setError(data.error);
      setStatus(ENROLLMENT_STATUS.ERROR);
    };

    const handleCancelled = () => {
      setStatus(ENROLLMENT_STATUS.CANCELLED);
      setSessionId(null);
    };

    enrollmentService.on(ENROLLMENT_EVENTS.STATUS_CHANGED, handleStatusChanged);
    enrollmentService.on(ENROLLMENT_EVENTS.CHUNK_PROCESSED, handleChunkProcessed);
    enrollmentService.on(ENROLLMENT_EVENTS.COMPLETED, handleCompleted);
    enrollmentService.on(ENROLLMENT_EVENTS.ERROR, handleError);
    enrollmentService.on(ENROLLMENT_EVENTS.CANCELLED, handleCancelled);

    return () => {
      enrollmentService.off(ENROLLMENT_EVENTS.STATUS_CHANGED, handleStatusChanged);
      enrollmentService.off(ENROLLMENT_EVENTS.CHUNK_PROCESSED, handleChunkProcessed);
      enrollmentService.off(ENROLLMENT_EVENTS.COMPLETED, handleCompleted);
      enrollmentService.off(ENROLLMENT_EVENTS.ERROR, handleError);
      enrollmentService.off(ENROLLMENT_EVENTS.CANCELLED, handleCancelled);
    };
  }, [enrollmentService]);

  return {
    // State
    sessionId,
    phoneNumber,
    status,
    audioChunksCollected,
    progress,
    isProcessing,
    error,
    successMessage,
    stats,
    isActive: !!sessionId,

    // Methods
    startEnrollment,
    submitChunk,
    completeEnrollment,
    cancelEnrollment,

    // Computed
    canSubmitChunk: !!sessionId && !isProcessing,
    isEnrollmentComplete: status === ENROLLMENT_STATUS.COMPLETED,
  };
}
