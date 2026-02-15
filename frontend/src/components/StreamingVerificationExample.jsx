/**
 * Streaming Verification Component Example
 * Demonstrates how to use the streaming recorder for real-time voice verification
 */

import React, { useState, useRef, useEffect } from 'react';
import { createStreamingRecorder } from '../utils/streamingRecorder';
import '../styles/StreamingVerification.css';

export function StreamingVerificationExample() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [recording, setRecording] = useState(false);
  const [connected, setConnected] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const recorderRef = useRef(null);
  const statsIntervalRef = useRef(null);

  // Initialize streaming recorder on mount
  useEffect(() => {
    const initializeRecorder = async () => {
      try {
        recorderRef.current = createStreamingRecorder({
          onWSOpen: () => {
            console.log('WebSocket connected');
            setConnected(true);
            setError(null);
          },
          onWSClose: () => {
            console.log('WebSocket disconnected');
            setConnected(false);
          },
          onWSError: (error) => {
            console.error('WebSocket error:', error);
            setError(`Connection error: ${error.message}`);
          },
          onChunkStreamed: (info) => {
            console.log(`Audio chunk ${info.sequence} streamed: ${info.size} bytes`);
          },
          onVerificationResult: (result) => {
            console.log('Verification result received:', result);
            setVerifying(false);
            setRecording(false);
            setResult({
              success: true,
              isMatch: result.is_match,
              confidence: result.confidence,
              score: result.similarity_score,
              threshold: result.threshold,
              timestamp: new Date().toLocaleTimeString()
            });
          },
          onServerError: (error) => {
            console.error('Server error:', error);
            setVerifying(false);
            setError(`Server error: ${error.message}`);
          }
        });

        await recorderRef.current.initialize();
        console.log('Streaming recorder initialized');
      } catch (error) {
        console.error('Failed to initialize recorder:', error);
        setError(`Initialization failed: ${error.message}`);
      }
    };

    initializeRecorder();

    // Cleanup on unmount
    return () => {
      if (recorderRef.current) {
        recorderRef.current.disconnect();
      }
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
    };
  }, []);

  // Update stats periodically during recording
  useEffect(() => {
    if (recording && recorderRef.current) {
      statsIntervalRef.current = setInterval(() => {
        const currentStats = recorderRef.current.getStats();
        setStats(currentStats);
      }, 500);

      return () => {
        if (statsIntervalRef.current) {
          clearInterval(statsIntervalRef.current);
        }
      };
    }
  }, [recording]);

  const handleStartRecording = async () => {
    if (!connected) {
      setError('WebSocket not connected. Please wait...');
      return;
    }

    try {
      setError(null);
      setResult(null);
      await recorderRef.current.startRecording();
      setRecording(true);
      console.log('Recording started');
    } catch (error) {
      console.error('Failed to start recording:', error);
      setError(`Recording failed: ${error.message}`);
    }
  };

  const handleStopRecording = async () => {
    try {
      const audioBlob = await recorderRef.current.stopRecording();
      setRecording(false);
      console.log('Recording stopped, audio blob size:', audioBlob?.size);

      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setError(`Stop failed: ${error.message}`);
    }
  };

  const handleVerify = async () => {
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number');
      return;
    }

    if (!connected) {
      setError('WebSocket not connected');
      return;
    }

    try {
      setError(null);
      setResult(null);
      setVerifying(true);

      // Send verification request
      recorderRef.current.verifyVoice(phoneNumber);
      console.log('Verification request sent for:', phoneNumber);
    } catch (error) {
      console.error('Verification failed:', error);
      setError(`Verification failed: ${error.message}`);
      setVerifying(false);
    }
  };

  const handleReset = async () => {
    try {
      recorderRef.current.resetBuffer();
      setResult(null);
      setError(null);
      console.log('Buffer reset');
    } catch (error) {
      console.error('Reset failed:', error);
      setError(`Reset failed: ${error.message}`);
    }
  };

  return (
    <div className="streaming-verification-container">
      <div className="verification-card">
        <h1>Voice Verification with Streaming</h1>

        {/* Connection Status */}
        <div className={`status-badge ${connected ? 'connected' : 'disconnected'}`}>
          <span className="status-dot"></span>
          {connected ? 'Connected' : 'Disconnecting...'}
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {/* Phone Number Input */}
        <div className="form-group">
          <label htmlFor="phone-input">Phone Number:</label>
          <input
            id="phone-input"
            type="tel"
            placeholder="+1 (555) 000-0000"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            disabled={recording || verifying}
            className="phone-input"
          />
        </div>

        {/* Recording Controls */}
        <div className="recording-controls">
          <button
            onClick={handleStartRecording}
            disabled={recording || !connected || verifying}
            className="btn btn-primary"
          >
            <span className="btn-icon">🎤</span>
            Start Recording
          </button>

          <button
            onClick={handleStopRecording}
            disabled={!recording}
            className="btn btn-danger"
          >
            <span className="btn-icon">⏹️</span>
            Stop Recording
          </button>

          <button
            onClick={handleVerify}
            disabled={!connected || recording || !phoneNumber.trim()}
            className="btn btn-success"
          >
            <span className="btn-icon">✓</span>
            Verify
          </button>

          <button
            onClick={handleReset}
            disabled={!connected || recording}
            className="btn btn-secondary"
          >
            <span className="btn-icon">🔄</span>
            Reset
          </button>
        </div>

        {/* Status Indicators */}
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">Recording:</span>
            <span className={`status-value ${recording ? 'active' : ''}`}>
              {recording ? '🔴 Recording' : '⚪ Idle'}
            </span>
          </div>

          <div className="status-item">
            <span className="status-label">Verifying:</span>
            <span className={`status-value ${verifying ? 'active' : ''}`}>
              {verifying ? '🔵 Processing' : '⚪ Idle'}
            </span>
          </div>
        </div>

        {/* Live Statistics */}
        {recording && stats && (
          <div className="stats-panel">
            <h3>Live Stream Statistics</h3>
            <div className="stats-grid">
              <div className="stat">
                <span className="stat-label">Chunks Streamed:</span>
                <span className="stat-value">{stats.chunksStreamed}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Buffer Size:</span>
                <span className="stat-value">{Math.round(stats.bufferSize)} samples</span>
              </div>
              <div className="stat">
                <span className="stat-label">WS State:</span>
                <span className="stat-value">{stats.websocketState}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Recorded Chunks:</span>
                <span className="stat-value">{stats.recordedChunks}</span>
              </div>
            </div>
          </div>
        )}

        {/* Verification Result */}
        {result && result.success && (
          <div className={`result-card ${result.isMatch ? 'match' : 'no-match'}`}>
            <h3>
              {result.isMatch ? '✅ Voice Verified' : '❌ Voice Not Verified'}
            </h3>
            <div className="result-details">
              <div className="result-item">
                <span className="result-label">Confidence:</span>
                <span className="result-value">{result.confidence.toFixed(1)}%</span>
              </div>
              <div className="result-item">
                <span className="result-label">Similarity Score:</span>
                <span className="result-value">{result.score.toFixed(4)}</span>
              </div>
              <div className="result-item">
                <span className="result-label">Threshold:</span>
                <span className="result-value">{result.threshold.toFixed(4)}</span>
              </div>
              <div className="result-item">
                <span className="result-label">Time:</span>
                <span className="result-value">{result.timestamp}</span>
              </div>
            </div>
          </div>
        )}

        {/* Information Panel */}
        <div className="info-panel">
          <h4>Instructions:</h4>
          <ol>
            <li>Wait for "Connected" status</li>
            <li>Enter phone number to verify</li>
            <li>Click "Start Recording" and speak clearly</li>
            <li>Click "Stop Recording" when done</li>
            <li>Click "Verify" to process the audio</li>
            <li>Wait for verification result</li>
          </ol>
        </div>
      </div>
    </div>
  );
}

export default StreamingVerificationExample;
