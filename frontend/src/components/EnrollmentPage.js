import React, { useState, useRef } from 'react';
import { createAudioRecorder, calculateDuration } from '../utils/audioRecorder';
import { enrollVoice } from '../services/api';
import { splitAudioIntoBase64Chunks, getChunkDurationByMode } from '../utils/audioChunkSplitter';
import ChunkProcessingIndicator from './ChunkProcessingIndicator';
import { useChunkProgress } from '../hooks/useChunkProgress';

function EnrollmentPage() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [chunkProgress, setChunkProgress] = useState(null);
  const [showChunkProgress, setShowChunkProgress] = useState(false);
  
  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const wsRef = useRef(null);

  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s]/g, '');
    setPhoneNumber(value);
    setResult(null);
    setError(null);
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
      setResult(null);
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
    setShowChunkProgress(true);

    try {
      // Set up WebSocket for real-time progress tracking
      const ws = new WebSocket(
        (process.env.REACT_APP_WS_URL || 'ws://localhost:8000') + '/ws/voice'
      );

      // Store WebSocket reference for progress updates
      wsRef.current = ws;

      // WebSocket message handler for progress updates
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'chunk_progress') {
            setChunkProgress(message.payload);
          }
        } catch (error) {
          console.error('Error processing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      // Wait for WebSocket to open
      await new Promise((resolve, reject) => {
        ws.onopen = resolve;
        ws.onerror = reject;
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
          
          // Enrollment uses 1-second chunks
          const chunkDurationMs = getChunkDurationByMode('enrollment');
          console.log(`Splitting audio into ${totalChunks} transmit chunks for enrollment (backend will use ${chunkDurationMs}ms chunks)`);
          
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
            type: "enroll",
            phone_number: phoneNumber.trim()
          }));

          // Listen for enrollment result
          const result = await new Promise((resolve, reject) => {
            const messageHandler = (event) => {
              try {
                const message = JSON.parse(event.data);

                if (message.type === 'enrollment_success') {
                  removeMessageHandler();
                  resolve(message.payload);
                } else if (message.type === 'error' || message.status === 'error') {
                  removeMessageHandler();
                  reject(
                    new Error(message.payload?.error_message || 'Enrollment failed')
                  );
                }
              } catch (error) {
                console.error('Error parsing message:', error);
              }
            };

            const removeMessageHandler = () => {
              ws.removeEventListener('message', messageHandler);
            };

            ws.addEventListener('message', messageHandler);
            setTimeout(
              () => {
                removeMessageHandler();
                reject(new Error('Enrollment timeout'));
              },
              60000
            ); // 60 second timeout
          });

          setResult({
            success: true,
            message: result?.message || 'Voice enrolled successfully!',
            vectorId: result?.vector_id,
          });
          setAudioBlob(null);
          setAudioDuration(0);
          setPhoneNumber('');
        } catch (error) {
          setError(error.message || 'Failed to enroll voice. Please try again.');
        } finally {
          ws.close();
          setShowChunkProgress(false);
          wsRef.current = null;
        }
      };

      reader.onerror = () => {
        setError('Failed to read audio file');
        setShowChunkProgress(false);
      };

      reader.readAsDataURL(audioBlob);
    } catch (err) {
      const errorMessage = err.message || 'Failed to enroll voice. Please try again.';
      setError(errorMessage);
      setShowChunkProgress(false);
    } finally {
      setIsSubmitting(false);
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
      <header className="w-full py-4 px-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded flex items-center justify-center text-white">
            <span className="material-icons-round text-xl">fingerprint</span>
          </div>
          <span className="font-bold text-xl tracking-tight text-slate-800 dark:text-white">
            BioVoice <span className="text-primary">ID</span>
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span className="material-icons-round text-sm">dns</span>
          <span>System Status: <span className="text-emerald-500 font-medium uppercase text-xs">Operational</span></span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex items-center justify-center p-6 lg:p-12">
        <div className="max-w-2xl w-full">
          {/* Intro Text */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-800 dark:text-white mb-2">Voice Identity Enrollment</h1>
            <p className="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
              Register your unique voice signature to enable seamless biometric verification for your account.
            </p>
          </div>

          {/* Enrollment Card */}
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            {/* Chunk Processing Indicator */}
            <ChunkProcessingIndicator
              isVisible={showChunkProgress}
              progress={chunkProgress}
              onComplete={() => {
                // Progress will be handled by the enrollment result
              }}
              onError={(errorMsg) => {
                setError(errorMsg || 'Processing failed');
              }}
            />

            <div className="p-8">
              {/* Phone Input */}
              <div className="mb-8">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2" htmlFor="phone-number">
                  Unique Identifier (Phone Number)
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="material-icons-round text-slate-400">phone</span>
                  </div>
                  <input
                    id="phone-number"
                    name="phone-number"
                    type="tel"
                    placeholder="+1 (555) 000-0000"
                    value={phoneNumber}
                    onChange={handlePhoneChange}
                    disabled={isRecording || isSubmitting}
                    className="block w-full pl-10 pr-3 py-3 border border-slate-300 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none disabled:opacity-50"
                  />
                </div>
                <p className="mt-2 text-xs text-slate-500">This number will be linked to your biometric voice print.</p>
              </div>

              {/* Waveform Area */}
              <div className="mb-8 bg-slate-900 rounded-lg p-6 relative h-48 flex items-center justify-center overflow-hidden">
                <div className="flex items-end gap-1 h-20 w-full justify-center px-4">
                  {/* Visualizer bars */}
                  {[...Array(13)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1.5 bg-primary rounded-full transition-all"
                      style={{
                        height: isRecording 
                          ? `${20 + Math.random() * 60}px`
                          : `${[16, 32, 48, 80, 96, 128, 96, 64, 32, 48, 96, 64, 32][i]}px`,
                      }}
                    ></div>
                  ))}
                </div>
                {/* Overlay timer */}
                <div className="absolute top-4 right-4 flex items-center gap-2">
                  {isRecording && <div className="w-2 h-2 bg-red-500 rounded-full animate-ping"></div>}
                  <span className="text-xs font-mono text-white/70 tracking-widest uppercase">
                    {formatTime(recordingTime)} / 00:10
                  </span>
                </div>
                <div className="absolute bottom-4 left-0 w-full text-center">
                  <span className="text-xs text-slate-500 uppercase tracking-widest font-semibold">Voice Activity Monitor</span>
                </div>
              </div>

              {/* Action Controls */}
              <div className="flex flex-col items-center gap-6">
                {/* Big Record Button */}
                <div className="relative group">
                  <div className="absolute -inset-2 bg-primary/20 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                  <button
                    onClick={handleRecord}
                    disabled={isSubmitting}
                    className="relative w-20 h-20 bg-primary hover:bg-primary/90 disabled:opacity-50 rounded-full flex items-center justify-center text-white shadow-lg transition-transform active:scale-95 focus:outline-none focus:ring-4 focus:ring-primary/50"
                  >
                    <span className="material-icons-round text-4xl">{isRecording ? 'stop' : 'mic'}</span>
                  </button>
                  <p className="text-center mt-4 text-sm font-medium text-slate-600 dark:text-slate-400">
                    {isRecording ? 'Recording...' : 'Click to start recording'}
                  </p>
                </div>

                {/* Status Info */}
                {audioBlob && !isRecording && (
                  <div className="w-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="material-icons text-lg">check_circle</span>
                      <div>
                        <p className="font-semibold text-sm">Audio Ready</p>
                        <p className="text-xs opacity-75">Duration: {audioDuration.toFixed(2)}s</p>
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="w-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                      <span className="material-icons text-lg">error</span>
                      <div>
                        <p className="font-semibold text-sm">Error</p>
                        <p className="text-xs opacity-75">{error}</p>
                      </div>
                    </div>
                  </div>
                )}

                {result && (
                  <div className="w-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                      <span className="material-icons text-lg">verified</span>
                      <div>
                        <p className="font-semibold text-sm">{result.message}</p>
                        {result.vectorId && <p className="text-xs opacity-75">ID: {result.vectorId.substring(0, 12)}...</p>}
                      </div>
                    </div>
                  </div>
                )}

                {/* Submit Button */}
                <div className="w-full pt-4 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={handleSubmit}
                    disabled={!phoneNumber.trim() || !audioBlob || isSubmitting || isRecording}
                    className="w-full py-4 bg-primary disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-lg shadow-md hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <span className="animate-spin">⏳</span>
                        Enrolling...
                      </>
                    ) : (
                      <>
                        <span>Complete Enrollment</span>
                        <span className="material-icons-round text-lg">check_circle</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Footer Status Bar */}
            <div className="bg-slate-50 dark:bg-slate-950 px-8 py-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Vector Status: <span className="text-slate-800 dark:text-slate-200 font-semibold">Ready for Processing</span>
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="material-icons-round text-sm">security</span>
                <span>AES-256 Encrypted</span>
              </div>
            </div>
          </div>

          {/* Steps Progress */}
          <div className="mt-8 flex justify-center gap-8">
            <div className="flex items-center gap-2 opacity-50">
              <span className="w-6 h-6 rounded-full border border-slate-400 flex items-center justify-center text-xs font-bold">1</span>
              <span className="text-sm font-medium">Identity</span>
            </div>
            <div className="w-8 border-t-2 border-slate-200 dark:border-slate-800 self-center"></div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white">2</span>
              <span className="text-sm font-bold text-primary">Voice Capture</span>
            </div>
            <div className="w-8 border-t-2 border-slate-200 dark:border-slate-800 self-center"></div>
            <div className="flex items-center gap-2 opacity-50">
              <span className="w-6 h-6 rounded-full border border-slate-400 flex items-center justify-center text-xs font-bold">3</span>
              <span className="text-sm font-medium">Verification</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="p-6 text-center text-slate-400 dark:text-slate-600 text-xs">
        © 2024 BioVoice Security Solutions. All biometric data is anonymized and stored securely.
      </footer>
    </div>
  );
}

export default EnrollmentPage;
