/**
 * Real-Time Verification Page Component
 * Fully automatic verification without manual verify button
 * - User enters phone number
 * - Clicks "Receive Call"
 * - Verification starts automatically
 * - Live similarity per chunk shown in real-time
 * - Auto-stops when verified or max chunks reached
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import AudioChunkingService from '../services/audioChunkingService';
import { useRealtimeVerification } from '../hooks/useRealtimeVerification';
import { REALTIME_VERIFICATION_STATUS } from '../services/realtimeVerificationService';
import { encodeWAV } from '../utils/wavEncoder';

function VerificationPageRealtime() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [threshold, setThreshold] = useState(0.75);
  
  // References
  const timerRef = useRef(null);
  const chunkingServiceRef = useRef(null);
  
  // Real-time verification hook
  const verification = useRealtimeVerification();

  // Initialize audio service on mount
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
      verification.disconnect();
    };
  }, []);

  // Stop recording when verification complete
  useEffect(() => {
    if (verification.isComplete && isRecording && chunkingServiceRef.current) {
      console.log('[VerificationPageRealtime] Stopping recording - verification complete');
      handleStopRecording();
    }
  }, [verification.isComplete]);

  const handleChunkReady = async (chunkInfo) => {
    console.log('[VerificationPageRealtime] Chunk ready:', chunkInfo.chunkNumber);
    
    try {
      // Encode as proper WAV file with RIFF headers
      const wavBlob = encodeWAV(chunkInfo.samples, chunkInfo.sampleRate);
      console.log('[VerificationPageRealtime] Created WAV blob size:', wavBlob.size, 'bytes');
      
      // Submit chunk to verification service
      await verification.submitAudioChunk(wavBlob);
    } catch (error) {
      console.error('Failed to submit chunk:', error);
    }
  };

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s()]/g, '');
    setPhoneNumber(value);
  };

  const handleThresholdChange = (e) => {
    setThreshold(parseFloat(e.target.value));
  };

  const handleStartVerification = async () => {
    if (!phoneNumber.trim()) {
      alert('Please enter a phone number');
      return;
    }

    try {
      console.log('[VerificationPageRealtime] Starting verification for:', phoneNumber);
      await verification.connectForVerification(phoneNumber.trim(), threshold);
      console.log('[VerificationPageRealtime] Verification connection established');
    } catch (err) {
      console.error('[VerificationPageRealtime] Failed to start verification:', err);
      alert(err.message || 'Failed to start verification');
    }
  };

  const handleStartRecording = async () => {
    if (!verification.isReady) {
      alert('Please start verification first');
      return;
    }

    console.log('[VerificationPageRealtime] Starting recording and verification');
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
      alert('Failed to access microphone');
    }
  };

  const handleStopRecording = () => {
    console.log('[VerificationPageRealtime] Stopping recording');
    if (chunkingServiceRef.current) {
      chunkingServiceRef.current.stopRecording();
    }
    setIsRecording(false);
    setRecordingTime(0);
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const handleCancelVerification = () => {
    console.log('[VerificationPageRealtime] Cancelling verification');
    if (isRecording) {
      handleStopRecording();
    }
    verification.disconnect();
  };

  const handleNewAttempt = () => {
    console.log('[VerificationPageRealtime] Starting new attempt');
    verification.disconnect();
  };

  // Utility functions
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status) => {
    const colors = {
      [REALTIME_VERIFICATION_STATUS.READY]: 'text-blue-600',
      [REALTIME_VERIFICATION_STATUS.PROCESSING]: 'text-yellow-600',
      [REALTIME_VERIFICATION_STATUS.VERIFIED]: 'text-green-600',
      [REALTIME_VERIFICATION_STATUS.UNVERIFIED]: 'text-red-600',
      [REALTIME_VERIFICATION_STATUS.ERROR]: 'text-red-600',
    };
    return colors[status] || 'text-gray-600';
  };

  const getSimilarityColor = (similarity) => {
    if (similarity >= threshold) return 'text-green-600';
    if (similarity >= threshold - 0.1) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getStatusText = (status) => {
    const text = {
      [REALTIME_VERIFICATION_STATUS.INITIALIZING]: 'Initializing...',
      [REALTIME_VERIFICATION_STATUS.READY]: 'Ready to record',
      [REALTIME_VERIFICATION_STATUS.PROCESSING]: 'Processing chunk...',
      [REALTIME_VERIFICATION_STATUS.VERIFIED]: 'VERIFIED! ✓',
      [REALTIME_VERIFICATION_STATUS.UNVERIFIED]: 'Not verified',
      [REALTIME_VERIFICATION_STATUS.ERROR]: 'Error occurred',
    };
    return text[status] || status;
  };

  const progressPercentage = verification.getProgressPercentage();

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Voice Verification</h1>

      {/* Initial Setup Section */}
      {!verification.isReady && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h2 className="text-lg font-semibold mb-4 text-gray-800">Setup Verification</h2>

          {/* Phone Number Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={handlePhoneChange}
              placeholder="+1-555-0000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Threshold Configuration */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Similarity Threshold: {threshold.toFixed(2)}
            </label>
            <input
              type="range"
              min="0.70"
              max="0.99"
              step="0.01"
              value={threshold}
              onChange={handleThresholdChange}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <p className="text-xs text-gray-500 mt-2">
              0.75 recommended. Lower = more lenient, Higher = stricter.
            </p>
          </div>

          {/* Error during setup */}
          {verification.error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">❌ {verification.error}</p>
            </div>
          )}

          {/* Start Button */}
          <button
            onClick={handleStartVerification}
            disabled={!phoneNumber.trim()}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 transition"
          >
            Initialize Verification
          </button>

          <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
            <p className="font-semibold mb-2">How it works:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Enter your phone number</li>
              <li>Click "Initialize Verification"</li>
              <li>Click "Receive Call"</li>
              <li>Verification runs automatically on each chunk</li>
              <li>Recording stops when verified or limit reached</li>
            </ol>
          </div>
        </div>
      )}

      {/* Active Verification Section */}
      {verification.isReady && (
        <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200">
          <h2 className="text-lg font-semibold mb-4 text-gray-800">Recording & Verification</h2>

          {/* Status Bar */}
          <div className="mb-6 p-4 bg-white rounded-lg border border-green-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-700">Status</span>
              <span className={`font-semibold ${getStatusColor(verification.status)}`}>
                {getStatusText(verification.status)}
              </span>
            </div>

            {/* Chunk Progress */}
            <div className="mb-3">
              <div className="flex justify-between mb-2">
                <span className="text-xs font-medium text-gray-600">Progress</span>
                <span className="text-xs font-medium text-gray-600">
                  {verification.currentChunk}/{verification.maxChunks}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>

            {/* Current Similarity Score */}
            {verification.currentChunk > 0 && (
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Latest Chunk</span>
                <span className={`font-semibold ${getSimilarityColor(verification.similarityScore)}`}>
                  {(verification.similarityScore * 100).toFixed(1)}% match
                  {verification.similarityScore >= threshold && <span className="ml-2">✓</span>}
                </span>
              </div>
            )}
          </div>

          {/* Recording Controls */}
          <div className="mb-6">
            <div className="flex gap-4 mb-4">
              {!isRecording ? (
                <button
                  onClick={handleStartRecording}
                  className="flex-1 px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition"
                >
                  📞 Receive Call
                </button>
              ) : (
                <>
                  <button
                    onClick={handleStopRecording}
                    className="flex-1 px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition"
                  >
                    📞 End Call
                  </button>
                  <div className="flex items-center justify-center px-4 py-3 bg-red-100 rounded-lg">
                    <span className="text-red-600 font-semibold">{formatTime(recordingTime)}</span>
                  </div>
                </>
              )}
            </div>

            {/* Stop Button */}
            {verification.isReady && !verification.isComplete && (
              <button
                onClick={handleCancelVerification}
                className="w-full px-6 py-2 bg-gray-500 text-white rounded-lg font-semibold hover:bg-gray-600 transition text-sm"
              >
                Cancel Verification
              </button>
            )}
          </div>

          {/* Chunk Results List with Live Chart */}
          {verification.chunkResults.length > 0 && (
            <div className="mb-6">
              <h3 className="font-medium text-gray-700 mb-3">Chunk Results</h3>
              
              {/* Live Bar Chart */}
              <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={verification.chunkResults.map((result) => ({
                    name: `Chunk ${result.chunkNumber}`,
                    score: result.similarityScore * 100,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: '#666', fontSize: 11 }}
                      axisLine={{ stroke: '#ccc' }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fill: '#666', fontSize: 11 }}
                      axisLine={{ stroke: '#ccc' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: 'none',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                      formatter={(value) => `${value.toFixed(1)}%`}
                    />
                    <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                      {verification.chunkResults.map((result, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={result.isMatch ? '#10b981' : (result.similarityScore >= threshold ? '#f59e0b' : '#ef4444')}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Detailed List */}
              <div className="space-y-2">
                {verification.chunkResults.map((result, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border ${
                      result.isMatch
                        ? 'bg-green-50 border-green-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">
                        Chunk {result.chunkNumber}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-semibold ${getSimilarityColor(result.similarityScore)}`}>
                          {(result.similarityScore * 100).toFixed(1)}%
                        </span>
                        {result.isMatch && <span className="text-green-600 font-bold">✓ Match</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Message */}
          {verification.error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">❌ {verification.error}</p>
            </div>
          )}
        </div>
      )}

      {/* Verification Complete Section */}
      {verification.isComplete && (
        <div className={`mb-6 p-6 rounded-lg border ${
          verification.isVerified
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <h2 className={`text-2xl font-bold mb-4 ${
            verification.isVerified ? 'text-green-700' : 'text-red-700'
          }`}>
            {verification.isVerified ? '✓ VERIFIED' : '✗ NOT VERIFIED'}
          </h2>

          {/* Summary */}
          <div className="mb-4 space-y-2">
            <p className="text-sm text-gray-700">
              <span className="font-medium">Chunks Processed:</span> {verification.currentChunk}/{verification.maxChunks}
            </p>
            <p className="text-sm text-gray-700">
              <span className="font-medium">Threshold:</span> {(verification.threshold * 100).toFixed(0)}%
            </p>
            {verification.isVerified && (
              <p className="text-sm text-gray-700">
                <span className="font-medium">Verified at chunk:</span> {verification.chunkResults.find(r => r.isMatch)?.chunkNumber}
              </p>
            )}
          </div>

          {/* Results Table */}
          {verification.chunkResults.length > 0 && (
            <div className="mb-6">
              {/* Chart Visualization */}
              <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
                <h3 className="text-sm font-bold text-gray-700 mb-4 uppercase tracking-wider">
                  Chunk Verification Scores
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={verification.chunkResults.map((result, index) => ({
                    name: `Chunk ${result.chunkNumber}`,
                    score: result.similarityScore * 100,
                    chunkNumber: result.chunkNumber,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: '#666', fontSize: 12 }}
                      axisLine={{ stroke: '#ccc' }}
                    />
                    <YAxis
                      label={{ value: 'Match Score (%)', angle: -90, position: 'insideLeft' }}
                      domain={[0, 100]}
                      tick={{ fill: '#666', fontSize: 12 }}
                      axisLine={{ stroke: '#ccc' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: 'none',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                      formatter={(value) => `${value.toFixed(1)}%`}
                      labelStyle={{ color: '#fff' }}
                    />
                    <Bar dataKey="score" radius={[8, 8, 0, 0]}>
                      {verification.chunkResults.map((result, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={result.isMatch ? '#10b981' : (result.similarityScore >= (verification.threshold - 0.1) ? '#f59e0b' : '#ef4444')}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>

                {/* Threshold Reference Line Info */}
                <div className="mt-4 flex items-center gap-2 text-sm">
                  <div className="w-3 h-3 rounded-full bg-gray-300" />
                  <span className="text-gray-600">
                    Threshold: <span className="font-semibold">{(verification.threshold * 100).toFixed(1)}%</span>
                  </span>
                </div>
              </div>

              {/* Detailed Results Table */}
              <div className="p-4 bg-white rounded-lg border border-gray-200">
                <h3 className="text-sm font-bold text-gray-700 mb-4 uppercase tracking-wider">
                  Detailed Chunk Results
                </h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-300">
                      <th className="text-left py-2">Chunk</th>
                      <th className="text-right py-2">Similarity</th>
                      <th className="text-right py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {verification.chunkResults.map((result, index) => (
                      <tr key={index} className="border-b border-gray-200">
                        <td className="py-2">{result.chunkNumber}</td>
                        <td className="text-right font-semibold">
                          {(result.similarityScore * 100).toFixed(1)}%
                        </td>
                        <td className="text-right">
                          {result.isMatch ? (
                            <span className="text-green-600 font-bold">✓ Match</span>
                          ) : (
                            <span className="text-red-600">✗ No match</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* New Attempt Button */}
          <button
            onClick={handleNewAttempt}
            className={`w-full px-6 py-3 text-white rounded-lg font-semibold transition ${
              verification.isVerified
                ? 'bg-blue-600 hover:bg-blue-700'
                : 'bg-gray-600 hover:bg-gray-700'
            }`}
          >
            {verification.isVerified ? 'Start New Verification' : 'Try Again'}
          </button>
        </div>
      )}
    </div>
  );
}

export default VerificationPageRealtime;
