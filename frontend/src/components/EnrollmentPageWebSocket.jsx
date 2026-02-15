/**
 * Enhanced Enrollment Component with WebSocket Support
 * Real-time enrollment with multi-chunk audio support and progress tracking
 */

import React, { useState, useRef, useEffect } from 'react';
import AudioChunkingService, { CHUNK_EVENTS, AUDIO_CONFIG } from '../services/audioChunkingService';
import { useEnrollmentService } from '../context/WebSocketContext';
import { useEnrollment } from '../hooks/useEnrollment';
import { ENROLLMENT_STATUS } from '../services/enrollmentWebSocketService';

function EnrollmentPageWebSocket() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioChunks, setAudioChunks] = useState([]);
  const [totalRecordingTime, setTotalRecordingTime] = useState(0);
  const [totalChunksGenerated, setTotalChunksGenerated] = useState(0);

  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const chunkingServiceRef = useRef(null);
  const enrollmentService = useEnrollmentService();
  const enrollment = useEnrollment(enrollmentService);

  // Initialize audio chunking service
  useEffect(() => {
    const initializeAudioService = async () => {
      try {
        const service = new AudioChunkingService({
          mode: 'enrollment',
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
    // Convert Float32Array to Blob
    const buffer = new ArrayBuffer(chunkInfo.samples.length * 2);
    const view = new Int16Array(buffer);
    for (let i = 0; i < chunkInfo.samples.length; i++) {
      view[i] = Math.max(-1, Math.min(1, chunkInfo.samples[i])) * 0x7FFF;
    }
    
    const blob = new Blob([buffer], { type: 'audio/wav' });
    
    // Update chunks display
    setAudioChunks((prev) => [...prev, {
      blob,
      chunkNumber: chunkInfo.chunkNumber,
      durationMs: chunkInfo.durationMs,
    }]);

    // Submit chunk to enrollment service
    try {
      await enrollment.submitChunk(blob, chunkInfo.chunkNumber);
      setTotalChunksGenerated(chunkInfo.chunkNumber);
    } catch (error) {
      console.error('Failed to submit chunk:', error);
    }
  };

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s]/g, '');
    setPhoneNumber(value);
  };

  const handleRecord = async () => {
    if (isRecording) {
      // Stop recording
      if (chunkingServiceRef.current) {
        chunkingServiceRef.current.stopRecording();
        
        // Update total recording time
        const stats = chunkingServiceRef.current.getStats();
        setTotalRecordingTime(totalRecordingTime + Math.round(stats.recordedTimeMs / 1000));
      }
      setIsRecording(false);
      setRecordingTime(0);
      if (timerRef.current) clearInterval(timerRef.current);
    } else {
      // Start recording
      if (!enrollment.isActive) {
        alert('Please start enrollment first');
        return;
      }
      
      setRecordingTime(0);
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
      }
    }
  };

  const handleStartEnrollment = async () => {
    if (!phoneNumber.trim()) {
      alert('Please enter a phone number');
      return;
    }

    try {
      // Reset chunk tracking when starting new enrollment
      setTotalRecordingTime(0);
      setTotalChunksGenerated(0);
      setAudioChunks([]);
      
      await enrollment.startEnrollment(phoneNumber.trim(), {
        max_chunks: 10,
        auto_process: true,
      });
    } catch (err) {
      console.error('Failed to start enrollment:', err);
    }
  };

  const handleCompleteEnrollment = async () => {
    try {
      await enrollment.completeEnrollment();
    } catch (err) {
      console.error('Failed to complete enrollment:', err);
    }
  };

  const handleCancelEnrollment = async () => {
    try {
      await enrollment.cancelEnrollment();
      setAudioChunks([]);
      setTotalRecordingTime(0);
      setTotalChunksGenerated(0);
      setRecordingTime(0);
    } catch (err) {
      console.error('Failed to cancel enrollment:', err);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const statusColor = {
    [ENROLLMENT_STATUS.ACTIVE]: 'text-blue-600',
    [ENROLLMENT_STATUS.COLLECTING]: 'text-blue-600',
    [ENROLLMENT_STATUS.PROCESSING]: 'text-yellow-600',
    [ENROLLMENT_STATUS.FINALIZING]: 'text-yellow-600',
    [ENROLLMENT_STATUS.COMPLETED]: 'text-green-600',
    [ENROLLMENT_STATUS.ERROR]: 'text-red-600',
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Voice Enrollment</h1>

      {/* Phone Number Input */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Phone Number
        </label>
        <input
          type="tel"
          value={phoneNumber}
          onChange={handlePhoneChange}
          disabled={enrollment.isActive}
          placeholder="+1-555-0000"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
        />
      </div>

      {/* Enrollment Status */}
      {enrollment.isActive && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-gray-700">Enrollment Status</span>
            <span className={`font-semibold ${statusColor[enrollment.status] || 'text-gray-600'}`}>
              {enrollment.status}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${enrollment.progress}%` }}
            />
          </div>

          <div className="text-sm text-gray-600">
            <p>Chunks collected: {enrollment.audioChunksCollected} / 10</p>
            <p>Total recording time: {formatTime(totalRecordingTime)}</p>
            <p>Chunks generated: <span className="font-semibold text-blue-600">{totalChunksGenerated}</span></p>
            <p>Session ID: {enrollment.sessionId?.slice(-8)}...</p>
          </div>
        </div>
      )}

      {/* Recording Section */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-4 text-gray-800">Record Audio</h2>

        <div className="flex gap-4 mb-4">
          <button
            onClick={handleRecord}
            disabled={!enrollment.isActive || enrollment.isProcessing}
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

      {/* Error Message */}
      {enrollment.error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">❌ {enrollment.error}</p>
        </div>
      )}

      {/* Success Message */}
      {enrollment.successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-700">✓ {enrollment.successMessage}</p>
          <p className="text-sm text-green-700 mt-2">
            📊 <span className="font-semibold">{totalChunksGenerated} chunks</span> were generated from <span className="font-semibold">{formatTime(totalRecordingTime)}</span> of audio
          </p>
          {enrollment.stats.vectorId && (
            <p className="text-xs text-green-600 mt-2">Vector ID: {enrollment.stats.vectorId}</p>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {!enrollment.isActive ? (
          <button
            onClick={handleStartEnrollment}
            disabled={!phoneNumber.trim()}
            className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition"
          >
            Start Enrollment
          </button>
        ) : (
          <>
            <button
              onClick={handleCompleteEnrollment}
              disabled={enrollment.audioChunksCollected === 0 || enrollment.isProcessing}
              className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400 transition"
            >
              Complete Enrollment
            </button>
            <button
              onClick={handleCancelEnrollment}
              className="px-6 py-3 bg-gray-500 text-white rounded-lg font-semibold hover:bg-gray-600 transition"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default EnrollmentPageWebSocket;
