/**
 * Enhanced Verification Component with WebSocket Support
 * Real-time voice verification with attempt tracking and result handling
 */

import React, { useState, useRef, useEffect } from 'react';
import AudioChunkingService, { CHUNK_EVENTS, AUDIO_CONFIG } from '../services/audioChunkingService';
import { useVerificationService } from '../context/WebSocketContext';
import { useVerification } from '../hooks/useVerification';
import SimilarityMetricsDisplay from './SimilarityMetricsDisplay';
import {
  VERIFICATION_STATUS,
  VERIFICATION_RESULT,
} from '../services/verificationWebSocketService';
import { encodeWAV } from '../utils/wavEncoder';

function VerificationPageWebSocket() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [threshold, setThreshold] = useState(0.85);
  const [audioChunks, setAudioChunks] = useState([]);
  const [totalChunksGenerated, setTotalChunksGenerated] = useState(0);

  const timerRef = useRef(null);
  const chunkingServiceRef = useRef(null);
  const verificationService = useVerificationService();
  const verification = useVerification(verificationService);

  // Initialize audio chunking service
  useEffect(() => {
    const initializeAudioService = async () => {
      try {
        const service = new AudioChunkingService({
          mode: 'verification',
          onChunkReady: handleChunkReady,
          onRecordingStarted: () => console.log('Recording started'),
          onRecordingStopped: () => console.log('Recording stopped'),
          onError: (error) => console.error('Audio error:', error),
        });
        
        await service.initialize();
        chunkingServiceRef.current = service;
      } catch (error) {
        console.error('Failed to initialize audio service:', error);
      }
    };

    initializeAudioService();

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (chunkingServiceRef.current) {
        chunkingServiceRef.current.cleanup().catch(console.error);
      }
    };
  }, []);

  const handleChunkReady = async (chunkInfo) => {
    // Encode as proper WAV file with RIFF headers
    const wavBlob = encodeWAV(chunkInfo.samples, chunkInfo.sampleRate);
    
    // Update chunks display
    setAudioChunks((prev) => [...prev, {
      blob: wavBlob,
      chunkNumber: chunkInfo.chunkNumber,
      durationMs: chunkInfo.durationMs,
    }]);

    // Submit chunk to verification service
    try {
      await verification.submitAudio(wavBlob, true);
      setTotalChunksGenerated(chunkInfo.chunkNumber);
    } catch (error) {
      console.error('Failed to submit chunk:', error);
    }
  };

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s]/g, '');
    setPhoneNumber(value);
  };

  const handleThresholdChange = (e) => {
    setThreshold(parseFloat(e.target.value));
  };

  const handleRecord = async () => {
    if (isRecording) {
      // Stop recording
      if (chunkingServiceRef.current) {
        chunkingServiceRef.current.stopRecording();
      }
      setIsRecording(false);
      setRecordingTime(0);
      if (timerRef.current) clearInterval(timerRef.current);
    } else {
      // Start recording
      if (!verification.isActive) {
        alert('Please start verification first');
        return;
      }

      setRecordingTime(0);
      setAudioChunks([]);
      setTotalChunksGenerated(0);
      
      try {
        if (chunkingServiceRef.current) {
          chunkingServiceRef.current.startRecording();
          setIsRecording(true);

          timerRef.current = setInterval(() => {
            setRecordingTime((t) => t + 1);
          }, 1000);
        }
      } catch (err) {
        console.error('Recording error:', err);
        alert('Failed to access microphone');
      }
    }
  };

  const handleStartVerification = async () => {
    if (!phoneNumber.trim()) {
      alert('Please enter a phone number');
      return;
    }

    try {
      await verification.startVerification(phoneNumber.trim(), {
        similarity_threshold: threshold,
        max_attempts: 3,
      });
    } catch (err) {
      console.error('Failed to start verification:', err);
    }
  };

  const handleCancelVerification = async () => {
    try {
      await verification.cancelVerification();
    } catch (err) {
      console.error('Failed to cancel verification:', err);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status) => {
    const colors = {
      [VERIFICATION_STATUS.ACTIVE]: 'text-blue-600',
      [VERIFICATION_STATUS.PROCESSING]: 'text-yellow-600',
      [VERIFICATION_STATUS.COMPARING]: 'text-yellow-600',
      [VERIFICATION_STATUS.VERIFIED]: 'text-green-600',
      [VERIFICATION_STATUS.REJECTED]: 'text-red-600',
      [VERIFICATION_STATUS.FAILED]: 'text-red-600',
    };
    return colors[status] || 'text-gray-600';
  };

  const getSimilarityColor = (similarity, threshold) => {
    if (similarity >= threshold) return 'text-green-600';
    if (similarity >= threshold - 0.1) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Voice Verification</h1>

      {/* Phone Number Input */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Phone Number
        </label>
        <input
          type="tel"
          value={phoneNumber}
          onChange={handlePhoneChange}
          disabled={verification.isActive}
          placeholder="+1-555-0000"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
        />
      </div>

      {/* Threshold Configuration */}
      {!verification.isActive && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Similarity Threshold: {threshold.toFixed(2)}
          </label>
          <input
            type="range"
            min="0.7"
            max="0.99"
            step="0.01"
            value={threshold}
            onChange={handleThresholdChange}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <p className="text-xs text-gray-500 mt-2">
            Higher threshold = stricter matching. 0.85 is recommended.
          </p>
        </div>
      )}

      {/* Verification Status */}
      {verification.isActive && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium text-gray-700">Verification Status</span>
            <span className={`font-semibold ${getStatusColor(verification.status)}`}>
              {verification.status}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${verification.progress}%` }}
            />
          </div>

          <div className="text-sm text-gray-600 space-y-1">
            <p>Attempt: {verification.attemptNumber} / {verification.maxAttempts}</p>
            <p>Remaining attempts: {verification.remainingAttempts}</p>
            {verification.similarity > 0 && (
              <p className={`font-semibold ${getSimilarityColor(verification.similarity, verification.threshold)}`}>
                Similarity: {(verification.similarity * 100).toFixed(2)}% (Threshold: {(verification.threshold * 100).toFixed(0)}%)
              </p>
            )}
            {verification.metrics && (
              <p className="text-xs text-gray-500 mt-2">
                Detailed metrics available below
              </p>
            )}
          </div>

          {/* Display metrics during comparison if available */}
          {verification.metrics && verification.status === VERIFICATION_STATUS.COMPARING && (
            <div className="mt-4">
              <SimilarityMetricsDisplay
                metrics={verification.metrics}
                threshold={verification.threshold}
                isMatch={verification.similarity >= verification.threshold}
              />
            </div>
          )}
        </div>
      )}

      {/* Recording Section */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-800">Record Audio</h2>

        <div className="flex gap-4 mb-4">
          <button
            onClick={handleRecord}
            disabled={!verification.isActive || verification.isProcessing}
            className="flex-1 px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400 transition"
          >
            {isRecording ? '⏹ Stop Recording' : '🎤 Record'}
          </button>

          {isRecording && (
            <div className="flex items-center justify-center px-4 py-3 bg-red-100 rounded-lg">
              <span className="text-red-600 font-semibold">{formatTime(recordingTime)}</span>
            </div>
          )}
        </div>

        {/* Audio Chunks List */}
        {audioChunks.length > 0 && (
          <div className="mt-4">
            <h3 className="font-medium text-gray-700 mb-2">Audio Chunks Generated ({totalChunksGenerated})</h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {audioChunks.map((chunk, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded"
                >
                  <span className="text-sm text-gray-600">
                    Chunk {chunk.chunkNumber} ({(chunk.blob.size / 1024).toFixed(2)} KB) - {(chunk.durationMs / 1000).toFixed(1)}s
                  </span>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                    Submitted
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Similarity Metrics Display */}
      {verification.metrics && verification.verificationResult && (
        <div className="mb-6">
          <SimilarityMetricsDisplay
            metrics={verification.metrics}
            threshold={verification.threshold}
            isMatch={verification.isVerified}
          />
        </div>
      )}

      {/* Verification Result (fallback when metrics not available) */}
      {verification.verificationResult && !verification.metrics && (
        <div className={`mb-6 p-4 rounded-lg border ${
          verification.isVerified 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <h3 className={`font-semibold mb-2 ${
            verification.isVerified ? 'text-green-700' : 'text-red-700'
          }`}>
            {verification.isVerified ? '✓ Verified' : '✗ Not Verified'}
          </h3>
          <p className={`text-sm ${
            verification.isVerified ? 'text-green-600' : 'text-red-600'
          }`}>
            {verification.verificationResult.message}
          </p>
          <p className={`text-sm font-semibold mt-2 ${getSimilarityColor(verification.similarity, verification.threshold)}`}>
            Similarity Score: {(verification.similarity * 100).toFixed(2)}% (Threshold: {(verification.threshold * 100).toFixed(0)}%)
          </p>
          {verification.verificationResult.remainingAttempts !== undefined && (
            <p className="text-xs text-gray-600 mt-2">
              Remaining attempts: {verification.verificationResult.remainingAttempts}
            </p>
          )}
        </div>
      )}

      {/* Error Message */}
      {verification.error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">❌ {verification.error}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {!verification.isActive ? (
          <button
            onClick={handleStartVerification}
            disabled={!phoneNumber.trim()}
            className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition"
          >
            Start Verification
          </button>
        ) : verification.isVerificationComplete ? (
          <button
            onClick={handleCancelVerification}
            className="w-full px-6 py-3 bg-gray-500 text-white rounded-lg font-semibold hover:bg-gray-600 transition"
          >
            Start New Verification
          </button>
        ) : (
          <button
            onClick={handleCancelVerification}
            className="w-full px-6 py-3 bg-gray-500 text-white rounded-lg font-semibold hover:bg-gray-600 transition"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
        <h3 className="font-semibold mb-2">Tips for Best Results</h3>
        <ul className="list-disc list-inside space-y-1">
          <li>Record in a quiet environment</li>
          <li>Speak clearly and naturally</li>
          <li>Maintain the same distance from the microphone as during enrollment</li>
          <li>You have {verification.maxAttempts} attempts to verify</li>
        </ul>
      </div>
    </div>
  );
}

export default VerificationPageWebSocket;
