/**
 * useVerification Hook
 * Custom React hook for verification WebSocket operations
 * Provides verification state management and event handling
 */

import { useState, useCallback, useEffect } from 'react';
import {
  VERIFICATION_EVENTS,
  VERIFICATION_STATUS,
  VERIFICATION_RESULT,
} from '../services/verificationWebSocketService';

export function useVerification(verificationService) {
  const [sessionId, setSessionId] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [status, setStatus] = useState(VERIFICATION_STATUS.INITIALIZING);
  const [attemptNumber, setAttemptNumber] = useState(0);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [remainingAttempts, setRemainingAttempts] = useState(3);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [similarity, setSimilarity] = useState(0);
  const [threshold, setThreshold] = useState(0.85);
  const [progress, setProgress] = useState(0);
  const [metrics, setMetrics] = useState(null);
  const [matchId, setMatchId] = useState(null);

  /**
   * Start verification session
   */
  const startVerification = useCallback(
    async (phone, config = {}) => {
      try {
        setError(null);
        setVerificationResult(null);
        setMetrics(null);
        setMatchId(null);
        setPhoneNumber(phone);
        setStatus(VERIFICATION_STATUS.ACTIVE);
        setAttemptNumber(0);
        setSimilarity(0);

        const newSessionId = await verificationService.startVerification(phone, config);
        setSessionId(newSessionId);
        setMaxAttempts(config.max_attempts || 3);
        setRemainingAttempts(config.max_attempts || 3);

        if (config.similarity_threshold) {
          setThreshold(config.similarity_threshold);
        }

        return newSessionId;
      } catch (err) {
        const errorMsg = err.message || 'Failed to start verification';
        setError(errorMsg);
        setStatus(VERIFICATION_STATUS.ERROR);
        throw err;
      }
    },
    [verificationService]
  );

  /**
   * Submit audio for verification
   */
  const submitAudio = useCallback(
    async (audioData, isChunk = false) => {
      try {
        if (!sessionId) {
          throw new Error('No active verification session');
        }

        setIsProcessing(true);
        setError(null);
        setStatus(VERIFICATION_STATUS.PROCESSING);

        await verificationService.submitAudio(audioData, isChunk);

        const newAttemptNumber = attemptNumber + 1;
        setAttemptNumber(newAttemptNumber);
        setProgress((newAttemptNumber / maxAttempts) * 100);
        setRemainingAttempts(Math.max(0, maxAttempts - newAttemptNumber));

        return true;
      } catch (err) {
        const errorMsg = err.message || 'Failed to submit audio';
        setError(errorMsg);
        throw err;
      } finally {
        setIsProcessing(false);
      }
    },
    [sessionId, attemptNumber, maxAttempts, verificationService]
  );

  /**
   * Cancel verification
   */
  const cancelVerification = useCallback(async () => {
    try {
      await verificationService.cancelVerification();
      setSessionId(null);
      setStatus(VERIFICATION_STATUS.CANCELLED);
      return true;
    } catch (err) {
      const errorMsg = err.message || 'Failed to cancel verification';
      setError(errorMsg);
      throw err;
    }
  }, [verificationService]);

  /**
   * Setup event listeners
   */
  useEffect(() => {
    if (!verificationService) return;

    const handleStatusChanged = (data) => {
      setStatus(data.status);
    };

    const handleProcessing = (data) => {
      setStatus(VERIFICATION_STATUS.PROCESSING);
    };

    const handleComparing = (data) => {
      setStatus(VERIFICATION_STATUS.COMPARING);
      if (data.similarity !== undefined) {
        setSimilarity(data.similarity);
      }
    };

    const handleVerified = (data) => {
      setStatus(VERIFICATION_STATUS.VERIFIED);
      const metrics = data.metrics || {};
      setMetrics(metrics);
      setMatchId(data.match_id || null);
      setVerificationResult({
        result: VERIFICATION_RESULT.MATCH,
        similarity: data.similarity,
        threshold: data.threshold,
        metrics: metrics,
        message: 'Voice verified successfully!',
      });
      setSimilarity(data.similarity);
      setSessionId(null);
    };

    const handleRejected = (data) => {
      setStatus(VERIFICATION_STATUS.REJECTED);
      const metrics = data.metrics || {};
      setMetrics(metrics);
      setMatchId(data.match_id || null);
      setVerificationResult({
        result: VERIFICATION_RESULT.MISMATCH,
        similarity: data.similarity,
        threshold: data.threshold,
        metrics: metrics,
        remainingAttempts: data.remainingAttempts,
        message: `Voice does not match. Remaining attempts: ${data.remainingAttempts}`,
      });
      setSimilarity(data.similarity);
      setRemainingAttempts(data.remainingAttempts || 0);
    };

    const handleCompleted = (data) => {
      setStatus(VERIFICATION_STATUS.COMPLETED);
      setVerificationResult({
        result: data.result,
        details: data.details,
        message: `Verification ${data.result}`,
      });
      setSessionId(null);
    };

    const handleError = (data) => {
      setError(data.error);
      setStatus(VERIFICATION_STATUS.FAILED);
    };

    const handleCancelled = () => {
      setStatus(VERIFICATION_STATUS.CANCELLED);
      setSessionId(null);
    };

    const handleAttemptLimitReached = () => {
      setError('Maximum verification attempts reached');
      setStatus(VERIFICATION_STATUS.FAILED);
      setRemainingAttempts(0);
    };

    verificationService.on(VERIFICATION_EVENTS.STATUS_CHANGED, handleStatusChanged);
    verificationService.on(VERIFICATION_EVENTS.PROCESSING, handleProcessing);
    verificationService.on(VERIFICATION_EVENTS.COMPARING, handleComparing);
    verificationService.on(VERIFICATION_EVENTS.VERIFIED, handleVerified);
    verificationService.on(VERIFICATION_EVENTS.REJECTED, handleRejected);
    verificationService.on(VERIFICATION_EVENTS.COMPLETED, handleCompleted);
    verificationService.on(VERIFICATION_EVENTS.ERROR, handleError);
    verificationService.on(VERIFICATION_EVENTS.CANCELLED, handleCancelled);
    verificationService.on(
      VERIFICATION_EVENTS.ATTEMPT_LIMIT_REACHED,
      handleAttemptLimitReached
    );

    return () => {
      verificationService.off(VERIFICATION_EVENTS.STATUS_CHANGED, handleStatusChanged);
      verificationService.off(VERIFICATION_EVENTS.PROCESSING, handleProcessing);
      verificationService.off(VERIFICATION_EVENTS.COMPARING, handleComparing);
      verificationService.off(VERIFICATION_EVENTS.VERIFIED, handleVerified);
      verificationService.off(VERIFICATION_EVENTS.REJECTED, handleRejected);
      verificationService.off(VERIFICATION_EVENTS.COMPLETED, handleCompleted);
      verificationService.off(VERIFICATION_EVENTS.ERROR, handleError);
      verificationService.off(VERIFICATION_EVENTS.CANCELLED, handleCancelled);
      verificationService.off(
        VERIFICATION_EVENTS.ATTEMPT_LIMIT_REACHED,
        handleAttemptLimitReached
      );
    };
  }, [verificationService]);

  return {
    // State
    sessionId,
    phoneNumber,
    status,
    attemptNumber,
    maxAttempts,
    remainingAttempts,
    isProcessing,
    error,
    verificationResult,
    similarity,
    threshold,
    progress,
    metrics,
    matchId,
    isActive: !!sessionId,

    // Methods
    startVerification,
    submitAudio,
    cancelVerification,

    // Computed
    canSubmitAudio: !!sessionId && !isProcessing && remainingAttempts > 0,
    isVerified: verificationResult?.result === VERIFICATION_RESULT.MATCH,
    isRejected: verificationResult?.result === VERIFICATION_RESULT.MISMATCH,
    isVerificationComplete:
      status === VERIFICATION_STATUS.VERIFIED ||
      status === VERIFICATION_STATUS.REJECTED ||
      remainingAttempts === 0,
  };
}
