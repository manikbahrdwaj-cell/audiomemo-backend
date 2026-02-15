import React, { useState, useRef } from 'react';
import { createAudioRecorder, calculateDuration } from '../utils/audioRecorder';
import { verifyVoice, checkEnrollment } from '../services/api';
import { splitAudioIntoBase64Chunks, getChunkDurationByMode } from '../utils/audioChunkSplitter';
import ChunkProcessingIndicator from './ChunkProcessingIndicator';
import VerificationResultsDisplay from './VerificationResultsDisplay';

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
  const [threshold, setThreshold] = useState(0.75);
  const [recordingTime, setRecordingTime] = useState(0);
  const [chunkProgress, setChunkProgress] = useState(null);
  const [showChunkProgress, setShowChunkProgress] = useState(false);
  
  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const wsRef = useRef(null);

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
      setRecordingTime(0);
      if (timerRef.current) clearInterval(timerRef.current);
    } else {
      setAudioBlob(null);
      setAudioDuration(0);
      setVerificationResult(null);
      setError(null);
      setRecordingTime(0);
      
      try {
        recorderRef.current = createAudioRecorder();
        await recorderRef.current.start();
        setIsRecording(true);
        
        timerRef.current = setInterval(() => {
          setRecordingTime(t => t + 1);
        }, 1000);
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
    setShowChunkProgress(true);

    try {
      // Set up WebSocket for real-time progress tracking
      const ws = new WebSocket(
        (process.env.REACT_APP_WS_URL || 'ws://localhost:8000') + '/ws/voice'
      );

      wsRef.current = ws;
      let verificationResultReceived = false;

      // Unified WebSocket message handler
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'chunk_progress') {
            setChunkProgress(message.payload);
          }

          if (message.type === 'error' || message.status === 'error') {
            setError(message.message || message.payload?.error_message || "Verification failed");
            setShowChunkProgress(false);
          }
        } catch (error) {
          console.error('Error processing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
        setShowChunkProgress(false);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        if (!verificationResultReceived) {
          setError('Connection lost during verification');
          setShowChunkProgress(false);
        }
      };

      // Wait for WebSocket to open
      await new Promise((resolve, reject) => {
        ws.onopen = resolve;
        setTimeout(() => reject(new Error('WebSocket connection timeout')), 5000);
      });

      // Convert audio blob to base64
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const base64Audio = reader.result.split(',')[1];

          // Split audio into chunks
          const audioChunks = splitAudioIntoBase64Chunks(base64Audio);
          const totalChunks = audioChunks.length;
          
          // Verification uses 5-second chunks
          const chunkDurationMs = getChunkDurationByMode('verification');
          console.log(`Splitting audio into ${totalChunks} transmit chunks for verification (backend will use ${chunkDurationMs}ms chunks)`);
          
          // Send each chunk sequentially
          for (let i = 0; i < audioChunks.length; i++) {
            const chunk = audioChunks[i];
            const isLastChunk = i === audioChunks.length - 1;
            
            // Send audio chunk message
            ws.send(JSON.stringify({
              type: "audio",
              chunk_number: i,
              total_chunks: totalChunks,
              is_last: isLastChunk,
              data: chunk
            }));
            
            // Log progress
            console.log(`Sent chunk ${i + 1}/${totalChunks}`);
            
            // Small delay between chunks to avoid overwhelming the connection
            if (!isLastChunk) {
              await new Promise(resolve => setTimeout(resolve, 10));
            }
          }

          ws.send(JSON.stringify({
            type: "verify",
            phone_number: phoneNumber.trim()
          }));

          // Listen for verification result
          const result = await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Verification timeout'));
            }, 60000); // 60 second timeout

            const originalOnMessage = ws.onmessage;
            ws.onmessage = (event) => {
              try {
                const message = JSON.parse(event.data);
                console.log('WebSocket message received:', message);

                if (message.type === 'verification_result') {
                  clearTimeout(timeout);
                  verificationResultReceived = true;
                  console.log('Verification result payload:', message.payload);
                  resolve(message);
                  return;
                }

                if (message.type === 'error' || message.status === 'error') {
                  clearTimeout(timeout);
                  console.error('Verification error:', message);
                  reject(
                    new Error(message.payload?.error_message || message.message || 'Verification failed')
                  );
                  return;
                }

                // Call original handler for chunk_progress
                if (originalOnMessage) {
                  originalOnMessage.call(ws, event);
                }
              } catch (error) {
                console.error('Error parsing message:', error);
              }
            };
          });

          console.log('Result received:', result);
          

          
          if (!result) {
            throw new Error("Invalid verification response structure");
          }

          const score = Number(result?.data?.similarity_score ?? 0);

          console.log("Extracted Score:", score);
          const isMatch = score >= threshold;

          setVerificationResult({
            score: score,
            isMatch: isMatch,
            phoneNumber: phoneNumber.trim(),
            threshold: threshold,
          });
        } catch (error) {
          setError(error?.message || 'Failed to verify voice. Please try again.');
        } finally {
          setShowChunkProgress(false);
          if (ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
          wsRef.current = null;
        }
      };

      reader.onerror = () => {
        setError('Failed to read audio file');
        setShowChunkProgress(false);
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };

      reader.readAsDataURL(audioBlob);
    } catch (err) {
      const errorMessage = err.message || 'Failed to verify voice. Please try again.';
      setError(errorMessage);
      setShowChunkProgress(false);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    } finally {
      setIsVerifying(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark flex flex-col">
      {/* Header */}
      <header className="border-b border-primary/10 bg-white dark:bg-background-dark px-8 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white">
            <span className="material-icons">fingerprint</span>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Verification Playground</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Voice Biometric Identity Diagnostic System</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs font-medium">System Online</span>
          </div>
        </div>
      </header>

      <main className="flex-grow flex p-6 gap-6 h-[calc(100vh-73px)] overflow-hidden">
        {/* Left Side: Control & Input Zone */}
        <section className="w-2/5 flex flex-col gap-6 overflow-y-auto">
          {/* Lookup Card */}
          <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-primary/10 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
              <span className="material-icons text-sm">person_search</span>
              Identify Target
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5 text-slate-600 dark:text-slate-400">
                  Phone Number / Identity ID
                </label>
                <div className="relative">
                  <input
                    className="w-full pl-10 pr-4 py-2.5 bg-background-light dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
                    placeholder="+1 (555) 000-0000"
                    type="tel"
                    value={phoneNumber}
                    onChange={handlePhoneChange}
                    disabled={isRecording || isVerifying}
                  />
                  <span className="material-icons absolute left-3 top-2.5 text-slate-400 text-sm">phone</span>
                </div>
              </div>
              <button
                onClick={handleCheckEnrollment}
                disabled={!phoneNumber.trim() || isChecking}
                className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20"
              >
                <span className="material-icons text-lg">search</span>
                {isChecking ? 'Checking...' : 'Retrieve Enrollment'}
              </button>
              {enrollmentStatus && (
                <div className={`p-3 rounded-lg ${enrollmentStatus.enrolled 
                  ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800' 
                  : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'}`}>
                  <p className={`text-xs font-semibold ${enrollmentStatus.enrolled 
                    ? 'text-emerald-700 dark:text-emerald-300' 
                    : 'text-red-700 dark:text-red-300'}`}>
                    {enrollmentStatus.enrolled ? '✓ Enrolled' : '✗ Not Enrolled'}
                  </p>
                  <p className="text-xs text-opacity-75 mt-1">{enrollmentStatus.message}</p>
                </div>
              )}
            </div>
          </div>

          {/* Recording Interface */}
          <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-primary/10 shadow-sm flex-grow flex flex-col">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
              <span className="material-icons text-sm">mic</span>
              Live Capture
            </h2>
            <div className="flex-grow flex flex-col items-center justify-center gap-8 py-4">
              {/* Real-time Signal Feedback */}
              <div className="w-full h-32 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700 relative overflow-hidden flex items-center justify-center">
                <div className="flex items-center gap-1 h-full px-4">
                  {[...Array(16)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1 bg-primary rounded-full"
                      style={{
                        height: isRecording 
                          ? `${20 + Math.random() * 60}px`
                          : `${[16, 32, 48, 96, 80, 112, 96, 48, 24, 56, 88, 72, 96, 40, 24, 16][i]}px`,
                        opacity: 0.3 + (isRecording ? Math.random() * 0.7 : 0.7)
                      }}
                    ></div>
                  ))}
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-background-light/50 dark:from-background-dark/50 to-transparent pointer-events-none"></div>
              </div>

              <div className="text-center">
                <button
                  onClick={handleRecord}
                  disabled={isVerifying}
                  className="group relative flex items-center justify-center"
                >
                  <div className="absolute inset-0 bg-primary/20 rounded-full scale-125 group-active:scale-150 transition-transform"></div>
                  <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center text-white relative z-10 shadow-xl hover:shadow-2xl transition-shadow">
                    <span className="material-icons text-3xl">{isRecording ? 'stop' : 'mic'}</span>
                  </div>
                </button>
                <p className="mt-6 text-sm font-medium text-slate-600 dark:text-slate-400">
                  {isRecording ? 'Recording in progress...' : 'Click to start test recording'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {isRecording ? formatTime(recordingTime) : 'Recommended phrase: "Verify my identity today"'}
                </p>
              </div>
            </div>

            <div className="pt-6 mt-auto border-t border-slate-100 dark:border-slate-800">
              <div className="flex justify-between items-center mb-4">
                <span className="text-xs font-semibold text-slate-500">MATCH THRESHOLD</span>
                <span className="text-xs font-bold text-primary">{threshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-primary"
              />
            </div>
          </div>
        </section>

        {/* Right Side: Analysis & Result Zone */}
        <section className="w-3/5 flex flex-col gap-6 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 p-8 rounded-xl border border-primary/10 shadow-sm flex flex-col h-full">
            {/* Chunk Processing Indicator */}
            {showChunkProgress && (
              <ChunkProcessingIndicator
                isVisible={showChunkProgress}
                progress={chunkProgress}
                onComplete={() => {
                  // Progress will be handled by the verification result
                }}
                onError={(errorMsg) => {
                  setError(errorMsg || 'Processing failed');
                }}
              />
            )}

            {/* Verification Results Display Component */}
            <VerificationResultsDisplay
              result={verificationResult}
              threshold={threshold}
              verificationError={error}
            />
          </div>
        </section>
      </main>

      {/* Action Bar */}
      <div className="bg-white dark:bg-background-dark border-t border-primary/10 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <button
            onClick={handleVerify}
            disabled={!audioBlob || isVerifying || isRecording}
            className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-white font-bold py-2.5 px-6 rounded-lg transition-all flex items-center gap-2"
          >
            {isVerifying ? (
              <>
                <span className="animate-spin">⏳</span>
                Verifying...
              </>
            ) : (
              <>
                <span className="material-icons">verified_user</span>
                Verify Voice
              </>
            )}
          </button>
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Recording Time: {formatTime(recordingTime)}
        </div>
      </div>
    </div>
  );
}

export default VerificationPage;
