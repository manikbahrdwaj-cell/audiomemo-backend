import React, { useState, useRef } from 'react';
import { createAudioRecorder, calculateDuration } from '../utils/audioRecorder';
import { verifyVoice, checkEnrollment } from '../services/api';

function VerificationPage() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [enrollmentStatus, setEnrollmentStatus] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [error, setError] = useState(null);
  
  const recorderRef = useRef(null);
  const SIMILARITY_THRESHOLD = 0.75; // 75% match threshold

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s]/g, '');
    setPhoneNumber(value);
    setEnrollmentStatus(null);
    setVerificationResult(null);
    setError(null);
  };

  const handleCheckEnrollment = async () => {
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number');
      return;
    }

    setIsChecking(true);
    setError(null);
    setEnrollmentStatus(null);
    setVerificationResult(null);

    try {
      const response = await checkEnrollment(phoneNumber.trim());
      setEnrollmentStatus({
        enrolled: response.enrolled,
        message: response.enrolled 
          ? 'Identity found. You can now verify your voice.'
          : 'Identity not found. Please enroll first.',
      });
    } catch (err) {
      setError('Failed to check enrollment status. Please try again.');
    } finally {
      setIsChecking(false);
    }
  };

  const handleRecord = async () => {
    if (isRecording) {
      // Stop recording
      if (recorderRef.current) {
        const blob = await recorderRef.current.stop();
        if (blob) {
          setAudioBlob(blob);
          const duration = await calculateDuration(blob);
          setAudioDuration(duration);
        }
        recorderRef.current = null;
      }
      setIsRecording(false);
    } else {
      // Start recording
      setAudioBlob(null);
      setAudioDuration(0);
      setVerificationResult(null);
      setError(null);
      
      try {
        recorderRef.current = createAudioRecorder();
        await recorderRef.current.start();
        setIsRecording(true);
      } catch (err) {
        setError('Failed to access microphone. Please grant microphone permissions.');
        console.error('Recording error:', err);
      }
    }
  };

  const handleVerify = async () => {
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number');
      return;
    }

    if (!audioBlob) {
      setError('Please record your voice first');
      return;
    }

    if (audioDuration < 2) {
      setError('Recording too short. Please record at least 2 seconds of audio.');
      return;
    }

    setIsVerifying(true);
    setError(null);
    setVerificationResult(null);

    try {
      const response = await verifyVoice(phoneNumber.trim(), audioBlob);
      const score = response.similarity_score;
      const isMatch = score >= SIMILARITY_THRESHOLD;

      setVerificationResult({
        score: score,
        isMatch: isMatch,
        phoneNumber: phoneNumber.trim(),
        threshold: SIMILARITY_THRESHOLD,
      });
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to verify voice. Please try again.';
      setError(errorMessage);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="page-container">
      <h1 className="page-title">Verification Playground</h1>
      <p className="page-subtitle">Test voice verification against enrolled identities</p>

      <div className="card">
        <div className="form-group">
          <label className="form-label" htmlFor="phone">Phone Number Lookup</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              id="phone"
              type="tel"
              className="form-input"
              placeholder="Enter phone number to verify"
              value={phoneNumber}
              onChange={handlePhoneChange}
              disabled={isRecording || isVerifying}
              style={{ flex: 1 }}
            />
            <button
              className="btn btn-primary"
              onClick={handleCheckEnrollment}
              disabled={!phoneNumber.trim() || isChecking || isRecording || isVerifying}
              style={{ whiteSpace: 'nowrap' }}
            >
              {isChecking ? <span className="loading"></span> : 'Check'}
            </button>
          </div>
          
          {enrollmentStatus && (
            <div style={{ marginTop: '0.75rem' }}>
              <span className={`status-badge ${enrollmentStatus.enrolled ? 'status-verified' : 'status-not-verified'}`}>
                {enrollmentStatus.enrolled ? '✓ Enrolled' : '✗ Not Enrolled'}
              </span>
              <span style={{ marginLeft: '0.5rem', color: 'rgba(255,255,255,0.7)', fontSize: '0.875rem' }}>
                {enrollmentStatus.message}
              </span>
            </div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Test Voice Recording</label>
          <button
            className={`btn btn-record ${isRecording ? 'recording' : ''}`}
            onClick={handleRecord}
            disabled={isVerifying}
          >
            {isRecording ? (
              <>
                <span className="recording-dot"></span>
                Stop Recording
              </>
            ) : (
              '🎤 Record Test Voice'
            )}
          </button>

          {isRecording && (
            <div className="recording-status">
              <span className="recording-dot"></span>
              <span>Recording in progress... Speak clearly</span>
            </div>
          )}

          {audioBlob && !isRecording && (
            <div className="recording-status audio-ready">
              <span className="recording-dot"></span>
              <span>Audio ready ({audioDuration.toFixed(1)}s) - 16kHz mono WAV</span>
            </div>
          )}
        </div>

        <button
          className="btn btn-submit"
          onClick={handleVerify}
          disabled={!phoneNumber.trim() || !audioBlob || isVerifying || isRecording}
        >
          {isVerifying ? (
            <>
              <span className="loading"></span>
              Verifying...
            </>
          ) : (
            'Verify Voice'
          )}
        </button>

        {verificationResult && (
          <div className="score-container">
            <h3 style={{ marginBottom: '0.5rem' }}>Verification Result</h3>
            <div className="score-display">
              <div className="score-item">
                <div className="score-label">Target Identity</div>
                <div className="score-value" style={{ fontSize: '1.25rem', color: '#00d9ff' }}>
                  {verificationResult.phoneNumber}
                </div>
              </div>
              <div className="score-divider"></div>
              <div className="score-item">
                <div className="score-label">Similarity Score</div>
                <div className={`score-value ${verificationResult.isMatch ? 'match' : 'no-match'}`}>
                  {(verificationResult.score * 100).toFixed(1)}%
                </div>
              </div>
            </div>
            <div className="score-threshold">
              Threshold: {(verificationResult.threshold * 100)}% | 
              <strong style={{ 
                color: verificationResult.isMatch ? '#4ade80' : '#ff6b6b',
                marginLeft: '0.5rem' 
              }}>
                {verificationResult.isMatch ? 'MATCH - Identity Verified' : 'NO MATCH - Verification Failed'}
              </strong>
            </div>
          </div>
        )}

        {error && (
          <div className="result-container result-error">
            <div className="result-title">✗ Error</div>
            <p style={{ marginTop: '0.5rem' }}>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default VerificationPage;
