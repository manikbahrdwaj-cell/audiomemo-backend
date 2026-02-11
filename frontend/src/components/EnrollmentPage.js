import React, { useState, useRef } from 'react';
import { createAudioRecorder, calculateDuration } from '../utils/audioRecorder';
import { enrollVoice } from '../services/api';

function EnrollmentPage() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  const recorderRef = useRef(null);

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s]/g, '');
    setPhoneNumber(value);
    setResult(null);
    setError(null);
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
      setResult(null);
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

  const handleSubmit = async () => {
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

    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await enrollVoice(phoneNumber.trim(), audioBlob);
      setResult({
        success: true,
        message: response.message || 'Voice enrolled successfully!',
        vectorId: response.vector_id,
      });
      // Reset for next enrollment
      setAudioBlob(null);
      setAudioDuration(0);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to enroll voice. Please try again.';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-container">
      <h1 className="page-title">Identity Enrollment</h1>
      <p className="page-subtitle">Register your voice for biometric authentication</p>

      <div className="card">
        <div className="form-group">
          <label className="form-label" htmlFor="phone">Phone Number</label>
          <input
            id="phone"
            type="tel"
            className="form-input"
            placeholder="Enter your phone number"
            value={phoneNumber}
            onChange={handlePhoneChange}
            disabled={isRecording || isSubmitting}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Voice Sample</label>
          <button
            className={`btn btn-record ${isRecording ? 'recording' : ''}`}
            onClick={handleRecord}
            disabled={isSubmitting}
          >
            {isRecording ? (
              <>
                <span className="recording-dot"></span>
                Stop Recording
              </>
            ) : (
              '🎤 Start Recording'
            )}
          </button>

          {isRecording && (
            <div className="recording-status">
              <span className="recording-dot"></span>
              <span>Recording in progress... Speak clearly for at least 3 seconds</span>
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
          onClick={handleSubmit}
          disabled={!phoneNumber.trim() || !audioBlob || isSubmitting || isRecording}
        >
          {isSubmitting ? (
            <>
              <span className="loading"></span>
              Enrolling...
            </>
          ) : (
            'Submit Enrollment'
          )}
        </button>

        {result && (
          <div className="result-container result-success">
            <div className="result-title">✓ {result.message}</div>
            {result.vectorId && (
              <p style={{ fontSize: '0.875rem', opacity: 0.8, marginTop: '0.5rem' }}>
                Vector ID: {result.vectorId}
              </p>
            )}
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

export default EnrollmentPage;
