import React, { useState, useRef } from 'react';
import { enrollVoice } from '../services/api';
import { splitAudioIntoBase64Chunks, getChunkDurationByMode } from '../utils/audioChunkSplitter';
import ChunkProcessingIndicator from './ChunkProcessingIndicator';
import VoiceSampleCard from './VoiceSampleCard';
import { useChunkProgress } from '../hooks/useChunkProgress';

const REQUIRED_SAMPLES = 5;
const MIN_SAMPLE_DURATION = 2; // seconds

function EnrollmentPage() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [samples, setSamples] = useState(Array(REQUIRED_SAMPLES).fill(null).map(() => ({ blob: null, duration: 0 })));
  const [recordingBlackout, setRecordingBlackout] = useState(-1); // tracks which sample is recording
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [chunkProgress, setChunkProgress] = useState(null);
  const [showChunkProgress, setShowChunkProgress] = useState(false);
  
  const wsRef = useRef(null);


  const handlePhoneChange = (e) => {
    const value = e.target.value.replace(/[^\d+\-\s]/g, '');
    setPhoneNumber(value);
    setResult(null);
    setError(null);
  };

  // Track which sample is currently recording
  const handleRecordingStart = (sampleNumber) => {
    setRecordingBlackout(sampleNumber);
  };

  // Clear recording state
  const handleRecordingStop = () => {
    setRecordingBlackout(-1);
  };

  // Update sample audio blob
  const handleAudioRecorded = (sampleIndex, audioBlob, duration) => {
    const newSamples = [...samples];
    newSamples[sampleIndex] = { blob: audioBlob, duration: duration || 0 };
    setSamples(newSamples);
  };

  // Count recorded samples
  const getRecordedCount = () => {
    return samples.filter(s => s.blob !== null).length;
  };

  // Validate all samples meet requirements
  const validateSamples = () => {
    const recordedCount = getRecordedCount();
    
    if (recordedCount === 0) {
      return { valid: false, message: 'Please record at least one voice sample' };
    }
    
    if (recordedCount < REQUIRED_SAMPLES) {
      return { valid: false, message: `Please record all ${REQUIRED_SAMPLES} voice samples. Current: ${recordedCount}/${REQUIRED_SAMPLES}` };
    }
    
    // Check minimum duration for each sample
    for (let i = 0; i < REQUIRED_SAMPLES; i++) {
      if (samples[i].duration < MIN_SAMPLE_DURATION) {
        return { valid: false, message: `Sample ${i + 1} is too short (${samples[i].duration.toFixed(1)}s). Minimum required: ${MIN_SAMPLE_DURATION}s` };
      }
    }
    
    return { valid: true, message: 'All samples valid' };
  };

  // Merge all audio samples into a single blob for backend processing
  const mergeAudioSamples = async () => {
    // For now, we'll send them individually to the backend
    // The backend will handle merging or processing them separately
    return samples.map(s => s.blob).filter(b => b !== null);
  };

  const handleSubmit = async () => {
    // Validate phone number
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number');
      return;
    }

    // Validate samples
    const validation = validateSamples();
    if (!validation.valid) {
      setError(validation.message);
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

      wsRef.current = ws;

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

      // Process each audio sample
      const audioBlobs = samples.map(s => s.blob).filter(b => b !== null);
      
      for (let sampleIndex = 0; sampleIndex < audioBlobs.length; sampleIndex++) {
        const audioBlob = audioBlobs[sampleIndex];
        
        await new Promise((resolve, reject) => {
          const reader = new FileReader();
          
          reader.onload = async () => {
            try {
              const base64Audio = reader.result.split(',')[1];
              
              // Split audio into chunks
              const audioChunks = splitAudioIntoBase64Chunks(base64Audio);
              const totalChunks = audioChunks.length;
              
              const chunkDurationMs = getChunkDurationByMode('enrollment');
              console.log(`Sample ${sampleIndex + 1}: Splitting audio into ${totalChunks} transmit chunks`);
              
              // Send each chunk sequentially
              for (let i = 0; i < audioChunks.length; i++) {
                const chunk = audioChunks[i];
                const isLastChunk = i === audioChunks.length - 1;
                
                ws.send(JSON.stringify({
                  type: "audio",
                  sample_number: sampleIndex + 1,
                  chunk_number: i,
                  total_chunks: totalChunks,
                  is_last: isLastChunk,
                  data: chunk
                }));
                
                console.log(`Sample ${sampleIndex + 1}, Chunk ${i + 1}/${totalChunks} sent`);
                
                if (!isLastChunk) {
                  await new Promise(res => setTimeout(res, 10));
                }
              }
              
              resolve();
            } catch (error) {
              reject(error);
            }
          };
          
          reader.onerror = () => reject(new Error('Failed to read audio file'));
          reader.readAsDataURL(audioBlob);
        });
      }

      // Send enrollment request with all samples info
      ws.send(JSON.stringify({
        type: "enroll",
        phone_number: phoneNumber.trim(),
        sample_count: audioBlobs.length
      }));

      // Listen for enrollment result
      const enrollmentResult = await new Promise((resolve, reject) => {
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
          120000
        ); // 120 second timeout for 5 samples
      });

      setResult({
        success: true,
        message: enrollmentResult?.message || `All ${REQUIRED_SAMPLES} voice samples enrolled successfully!`,
        vectorId: enrollmentResult?.vector_id,
        sampleCount: audioBlobs.length,
      });
      
      // Reset form
      setSamples(Array(REQUIRED_SAMPLES).fill(null).map(() => ({ blob: null, duration: 0 })));
      setPhoneNumber('');
    } catch (err) {
      const errorMessage = err.message || 'Failed to enroll voice samples. Please try again.';
      setError(errorMessage);
    } finally {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setShowChunkProgress(false);
      setIsSubmitting(false);
    }
  };


  const recordedCount = getRecordedCount();
  const isAllSamplesRecorded = recordedCount === REQUIRED_SAMPLES;

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
        <div className="max-w-4xl w-full">
          {/* Intro Text */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-800 dark:text-white mb-2">
              Multi-Sample Voice Enrollment
            </h1>
            <p className="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
              Register your unique voice signature with {REQUIRED_SAMPLES} separate samples to ensure robust biometric verification.
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
                    disabled={recordingBlackout !== -1 || isSubmitting}
                    className="block w-full pl-10 pr-3 py-3 border border-slate-300 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none disabled:opacity-50"
                  />
                </div>
                <p className="mt-2 text-xs text-slate-500">This number will be linked to your biometric voice print.</p>
              </div>

              {/* Sample Recording Progress */}
              <div className="mb-8 p-4 bg-slate-100 dark:bg-slate-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-slate-700 dark:text-slate-300">
                    Recording Progress
                  </h3>
                  <span className={`text-sm font-bold ${
                    isAllSamplesRecorded 
                      ? 'text-emerald-600 dark:text-emerald-400' 
                      : 'text-slate-600 dark:text-slate-400'
                  }`}>
                    {recordedCount}/{REQUIRED_SAMPLES}
                  </span>
                </div>
                <div className="w-full bg-slate-300 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      isAllSamplesRecorded ? 'bg-emerald-500' : 'bg-primary'
                    }`}
                    style={{ width: `${(recordedCount / REQUIRED_SAMPLES) * 100}%` }}
                  ></div>
                </div>
              </div>

              {/* Voice Sample Cards Grid */}
              <div className="mb-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-4">
                {samples.map((sample, index) => (
                  <VoiceSampleCard
                    key={index}
                    sampleNumber={index + 1}
                    audioBlob={sample.blob}
                    isRecording={recordingBlackout === index + 1}
                    onRecordingStart={handleRecordingStart}
                    onRecordingStop={handleRecordingStop}
                    onAudioRecorded={(blob, duration) => handleAudioRecorded(index, blob, duration)}
                  />
                ))}
              </div>

              {/* Error Messages */}
              {error && (
                <div className="mb-8 w-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                    <span className="material-icons text-lg">error</span>
                    <div>
                      <p className="font-semibold text-sm">Error</p>
                      <p className="text-xs opacity-75">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Success Message */}
              {result && (
                <div className="mb-8 w-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                    <span className="material-icons text-lg">verified</span>
                    <div>
                      <p className="font-semibold text-sm">{result.message}</p>
                      {result.vectorId && <p className="text-xs opacity-75">ID: {result.vectorId.substring(0, 12)}...</p>}
                    </div>
                  </div>
                </div>
              )}

              {/* Validation Status for Submit */}
              {recordedCount > 0 && recordedCount < REQUIRED_SAMPLES && (
                <div className="mb-8 w-full bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-300">
                    <span className="material-icons text-lg">warning</span>
                    <div>
                      <p className="font-semibold text-sm">Incomplete</p>
                      <p className="text-xs opacity-75">
                        {recordedCount} of {REQUIRED_SAMPLES} samples recorded. Record all samples to proceed.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                <button
                  onClick={handleSubmit}
                  disabled={!phoneNumber.trim() || !isAllSamplesRecorded || isSubmitting || recordingBlackout !== -1}
                  className={`w-full py-4 font-bold rounded-lg shadow-md transition-all flex items-center justify-center gap-2 ${
                    isAllSamplesRecorded && phoneNumber.trim()
                      ? 'bg-primary hover:bg-primary/90 text-white cursor-pointer'
                      : 'bg-slate-300 dark:bg-slate-700 text-slate-500 dark:text-slate-400 cursor-not-allowed opacity-50'
                  }`}
                >
                  {isSubmitting ? (
                    <>
                      <span className="animate-spin">⏳</span>
                      Enrolling {REQUIRED_SAMPLES} Samples...
                    </>
                  ) : (
                    <>
                      <span>Complete Multi-Sample Enrollment</span>
                      <span className="material-icons-round text-lg">check_circle</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Footer Status Bar */}
            <div className="bg-slate-50 dark:bg-slate-950 px-8 py-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Samples Ready: <span className={`font-semibold ${isAllSamplesRecorded ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-800 dark:text-slate-200'}`}>
                    {recordedCount}/{REQUIRED_SAMPLES}
                  </span>
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
              <span className="text-sm font-bold text-primary">5 Voice Samples</span>
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
