/**
 * Hook for Real-Time Voice Verification
 * Manages automatic verification with live chunk processing
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import RealtimeVerificationService, {
  REALTIME_VERIFICATION_EVENTS,
  REALTIME_VERIFICATION_STATUS,
} from '../services/realtimeVerificationService';

export function useRealtimeVerification() {
  // Service instance
  const serviceRef = useRef(null);

  // State
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isReady, setIsReady] = useState(false);
  const [status, setStatus] = useState(REALTIME_VERIFICATION_STATUS.INITIALIZING);
  const [chunkResults, setChunkResults] = useState([]);
  const [currentChunk, setCurrentChunk] = useState(0);
  const [maxChunks, setMaxChunks] = useState(4);
  const [threshold, setThreshold] = useState(0.75);
  const [isVerified, setIsVerified] = useState(null); // null = pending, true/false = complete
  const [error, setError] = useState(null);
  const [similarityScore, setSimilarityScore] = useState(0);

  // Agent-mode state (populated after biometric verification succeeds)
  const [agentMessages, setAgentMessages] = useState([]);
  const [isAgentThinking, setIsAgentThinking] = useState(false);

  // Initialize service on mount
  useEffect(() => {
    serviceRef.current = new RealtimeVerificationService();
    return () => {
      if (serviceRef.current) {
        serviceRef.current.disconnect();
      }
    };
  }, []);

  /**
   * Connect to verification WebSocket
   */
  const connectForVerification = useCallback(async (phone, thresholdValue = 0.75) => {
    console.log('[useRealtimeVerification] Connecting for phone:', phone);
    try {
      setPhoneNumber(phone);
      setStatus(REALTIME_VERIFICATION_STATUS.INITIALIZING);
      setError(null);
      setIsVerified(null);
      setChunkResults([]);
      setCurrentChunk(0);

      const service = serviceRef.current;

      // Clear any listeners from a previous session before re-registering
      service.removeAllListeners();

      // Setup event listeners
      service.on(REALTIME_VERIFICATION_EVENTS.SESSION_CREATED, (data) => {
        console.log('[useRealtimeVerification] Session created:', data);
        setIsReady(true);
        setStatus(REALTIME_VERIFICATION_STATUS.READY);
        setMaxChunks(data.maxChunks || 4);
        setThreshold(data.threshold || 0.75);
      });

      service.on(REALTIME_VERIFICATION_EVENTS.CHUNK_RESULT, (result) => {
        console.log('[useRealtimeVerification] Chunk result:', result);
        setCurrentChunk(result.chunkNumber);
        setSimilarityScore(result.similarityScore);
        setChunkResults((prev) => [...prev, result]);
      });

      service.on(REALTIME_VERIFICATION_EVENTS.VERIFIED, (data) => {
        console.log('[useRealtimeVerification] Verification SUCCESS');
        setStatus(REALTIME_VERIFICATION_STATUS.VERIFIED);
        setIsVerified(true);
        setChunkResults(data.results || []);
        // Reset agent state for this session
        setAgentMessages([]);
        setIsAgentThinking(false);
      });

      service.on(REALTIME_VERIFICATION_EVENTS.UNVERIFIED, (data) => {
        console.log('[useRealtimeVerification] Verification FAILED');
        setStatus(REALTIME_VERIFICATION_STATUS.UNVERIFIED);
        setIsVerified(false);
        setChunkResults(data.results || []);
      });

      service.on(REALTIME_VERIFICATION_EVENTS.AGENT_RESPONSE, (data) => {
        setIsAgentThinking(false);
        const now = new Date();
        setAgentMessages((prev) => [
          ...prev,
          // User bubble — Whisper transcription of what was spoken
          ...(data.transcript ? [{ role: 'user', text: data.transcript, timestamp: now }] : []),
          // Assistant bubble — agent spoken response
          { role: 'assistant', text: data.text, audioBase64: data.audioBase64, timestamp: now },
        ]);
      });

      service.on(REALTIME_VERIFICATION_EVENTS.AGENT_THINKING, () => {
        setIsAgentThinking(true);
      });

      service.on(REALTIME_VERIFICATION_EVENTS.ERROR, (data) => {
        console.error('[useRealtimeVerification] Error:', data);
        setStatus(REALTIME_VERIFICATION_STATUS.ERROR);
        // Do NOT set isVerified=false here — that would make isComplete=true and
        // stop recording on a transient error. Only UNVERIFIED sets isVerified=false.
        setError(data.message || 'Verification error');
      });

      service.on(REALTIME_VERIFICATION_EVENTS.CONNECTION_CLOSED, () => {
        console.log('[useRealtimeVerification] Connection closed');
        // Service will handle cleanup
      });

      // Connect to WebSocket
      await service.connect(phone, thresholdValue);
    } catch (err) {
      console.error('[useRealtimeVerification] Connection failed:', err);
      setStatus(REALTIME_VERIFICATION_STATUS.ERROR);
      setError(err.message || 'Failed to connect for verification');
      // Do NOT set isVerified=false here — that makes isComplete=true which
      // hides the setup form and shows the "NOT VERIFIED" result screen.
      // Keep isVerified=null so the setup form stays visible and the error
      // is shown inline above the "Initiate Call" button.
      throw err;
    }
  }, []);

  /**
   * Submit audio chunk for verification
   */
  const submitAudioChunk = useCallback(async (audioBlob) => {
    console.log('[useRealtimeVerification] Submitting audio chunk');
    try {
      if (!serviceRef.current) {
        throw new Error('Verification service not initialized');
      }

      const service = serviceRef.current;

      // Check if already completed
      const state = service.getState();
      if (state.status === REALTIME_VERIFICATION_STATUS.COMPLETED) {
        console.log('[useRealtimeVerification] Verification already completed');
        return;
      }

      await service.sendAudioChunk(audioBlob);
    } catch (err) {
      console.error('[useRealtimeVerification] Error submitting chunk:', err);
      // "WebSocket not connected" is an expected race condition when the user ends
      // the call while a chunk is still in-flight. Don't surface it as a UI error.
      if (err.message !== 'WebSocket not connected') {
        setError(err.message || 'Failed to submit audio chunk');
      }
      throw err;
    }
  }, []);

  /**
   * Add a user message to agent history (called by component before sending audio)
   */
  const addUserAgentMessage = useCallback((text) => {
    setAgentMessages((prev) => [
      ...prev,
      { role: 'user', text, timestamp: new Date() },
    ]);
  }, []);

  /**
   * Check if verification is complete
   */
  const isComplete = isVerified !== null;

  /**
   * Check if should stop recording
   */
  const shouldStopRecording = useCallback(() => {
    if (!serviceRef.current) return false;
    const state = serviceRef.current.getState();
    return state.status === REALTIME_VERIFICATION_STATUS.COMPLETED;
  }, []);

  /**
   * Disconnect and cleanup
   */
  const disconnect = useCallback(() => {
    console.log('[useRealtimeVerification] Disconnecting');
    if (serviceRef.current) {
      serviceRef.current.disconnect();
    }
    setIsReady(false);
    setStatus(REALTIME_VERIFICATION_STATUS.INITIALIZING);
    setIsVerified(null);
    setChunkResults([]);
    setError(null);
    setAgentMessages([]);
    setIsAgentThinking(false);
  }, []);

  /**
   * Get progress percentage
   */
  const getProgressPercentage = useCallback(() => {
    if (maxChunks === 0) return 0;
    return Math.min(100, Math.round((currentChunk / maxChunks) * 100));
  }, [currentChunk, maxChunks]);

  return {
    // State
    phoneNumber,
    status,
    isReady,
    isVerified,
    isComplete,
    error,
    chunkResults,
    currentChunk,
    maxChunks,
    threshold,
    similarityScore,

    // Actions
    connectForVerification,
    submitAudioChunk,
    disconnect,
    addUserAgentMessage,

    // Agent state
    agentMessages,
    isAgentThinking,

    // Utilities
    shouldStopRecording,
    getProgressPercentage,
  };
}
