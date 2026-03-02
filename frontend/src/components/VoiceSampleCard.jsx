import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { createAudioRecorder, calculateDuration } from '../utils/audioRecorder';

/**
 * VoiceSampleCard Component
 * Reusable card for recording individual voice samples
 * Features: Record, Stop, Playback, Delete with visual feedback
 */
/**
 * validationState shape:
 *   null                                             – not yet validated
 *   { status: 'validating' }                         – Whisper call in-flight
 *   { status: 'matched',  transcription, similarity } – text matched
 *   { status: 'mismatch', transcription, similarity } – text did NOT match
 */
const VoiceSampleCard = forwardRef(function VoiceSampleCard({ sampleNumber, onAudioRecorded, audioBlob, isRecording, onRecordingStart, onRecordingStop, validationState, expectedText }, ref) {
  const [recordingTime, setRecordingTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [localIsRecording, setLocalIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState(null);
  
  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const audioRef = useRef(null);
  const urlRef = useRef(null);

  // Expose stopRecording so the parent can imperatively halt this card's recording
  // before starting a new one on a different card.
  useImperativeHandle(ref, () => ({
    stopRecording: async () => {
      if (!recorderRef.current) return;
      const blob = await recorderRef.current.stop();
      if (blob) {
        const dur = await calculateDuration(blob);
        setDuration(dur);
        onAudioRecorded(blob, dur);
      }
      recorderRef.current = null;
      setLocalIsRecording(false);
      setRecordingTime(0);
      if (timerRef.current) clearInterval(timerRef.current);
      onRecordingStop();
    },
  }));

  // Sample paragraphs for each sample number
  const SAMPLE_PARAGRAPHS = {
    1: "The quick brown fox jumps over the lazy dog. This is a pangram that contains every letter of the English alphabet.",
    2: "She sells seashells by the seashore. The shells she sells are surely seashells.",
    3: "Peter Piper picked a peck of pickled peppers. A peck of pickled peppers Peter Piper picked.",
    4: "How much wood would a woodchuck chuck if a woodchuck could chuck wood? Wood would a woodchuck chuck.",
    5: "Please speak clearly and naturally. This sample will help create a unique voice profile for verification.",
  };

  const getSampleParagraph = () => {
    return expectedText || SAMPLE_PARAGRAPHS[sampleNumber] || '';
  };

  // Manage audio URL creation and cleanup
  useEffect(() => {
    if (audioBlob) {
      // Revoke old URL if it exists
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
      }
      // Create new URL for the blob
      const newURL = URL.createObjectURL(audioBlob);
      urlRef.current = newURL;
      setAudioURL(newURL);
    } else {
      // Clean up URL when blob is removed
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
      }
      setAudioURL(null);
    }

    // Cleanup on unmount
    return () => {
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
      }
    };
  }, [audioBlob]);

  // Determine card color based on recording + validation status
  const getCardColor = () => {
    if (audioBlob) {
      if (!validationState || validationState.status === 'validating') {
        return 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700';
      }
      if (validationState.status === 'matched') {
        return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800';
      }
      if (validationState.status === 'mismatch') {
        return 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700';
      }
    }
    return 'bg-slate-50 dark:bg-slate-900/30 border-slate-200 dark:border-slate-700';
  };

  const getStatusColor = () => {
    if (audioBlob) {
      if (!validationState || validationState.status === 'validating') {
        return 'text-amber-700 dark:text-amber-300';
      }
      if (validationState.status === 'matched') return 'text-emerald-700 dark:text-emerald-300';
      if (validationState.status === 'mismatch') return 'text-red-700 dark:text-red-300';
    }
    return 'text-slate-500 dark:text-slate-400';
  };

  const getStatusIcon = () => {
    if (!audioBlob) return 'circle';
    if (!validationState || validationState.status === 'validating') return 'pending';
    if (validationState.status === 'matched') return 'check_circle';
    if (validationState.status === 'mismatch') return 'cancel';
    return 'check_circle';
  };

  const getStatusText = () => {
    if (!audioBlob) return 'Not Recorded';
    if (!validationState) return 'Recorded';
    if (validationState.status === 'validating') return 'Validating…';
    if (validationState.status === 'matched') return 'Validated';
    if (validationState.status === 'mismatch') return 'Text Mismatch';
    return 'Recorded';
  };

  // Start recording
  const handleStartRecord = async () => {
    try {
      setLocalIsRecording(true);
      onRecordingStart(sampleNumber);
      
      recorderRef.current = createAudioRecorder();
      await recorderRef.current.start();
      setRecordingTime(0);
      
      timerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1);
      }, 1000);
    } catch (err) {
      setLocalIsRecording(false);
      onRecordingStart(-1);
      console.error('Recording error:', err);
    }
  };

  // Stop recording
  const handleStopRecord = async () => {
    if (recorderRef.current) {
      const blob = await recorderRef.current.stop();
      if (blob) {
        const dur = await calculateDuration(blob);
        setDuration(dur);
        onAudioRecorded(blob, dur);
      }
      recorderRef.current = null;
    }
    
    setLocalIsRecording(false);
    setRecordingTime(0);
    if (timerRef.current) clearInterval(timerRef.current);
    onRecordingStop();
  };

  // Delete/Re-record
  const handleDelete = () => {
    onAudioRecorded(null, 0);
    setDuration(0);
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  };

  // Play audio
  const handlePlay = async () => {
    if (!audioRef.current || !audioBlob) {
      console.error('Audio element or blob not available');
      return;
    }

    try {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        // Ensure audio is loadedmetadata before playing
        if (audioRef.current.readyState < 1) {
          // Audio not yet loaded, wait for it
          await new Promise((resolve, reject) => {
            const handleCanPlay = () => {
              audioRef.current.removeEventListener('canplay', handleCanPlay);
              resolve();
            };
            const handleError = (err) => {
              audioRef.current.removeEventListener('error', handleError);
              reject(err);
            };
            audioRef.current.addEventListener('canplay', handleCanPlay);
            audioRef.current.addEventListener('error', handleError);
            setTimeout(() => reject(new Error('Audio load timeout')), 5000);
          });
        }
        
        // Reset playback position
        audioRef.current.currentTime = 0;
        
        // Play with error handling
        const playPromise = audioRef.current.play();
        if (playPromise !== undefined) {
          await playPromise;
        }
        setIsPlaying(true);
      }
    } catch (error) {
      console.error('Playback error:', error);
      setIsPlaying(false);
      alert('Error playing audio: ' + (error.message || 'Unknown error'));
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className={`border-2 rounded-lg p-6 transition-all ${getCardColor()}`}>
      {/* Header with sample number and status */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
            <span className="text-lg font-bold text-primary">
              {sampleNumber}
            </span>
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 dark:text-white">
              Sample {sampleNumber}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Voice recording
            </p>
          </div>
        </div>
        <div className={`flex items-center gap-1 ${getStatusColor()}`}>
          <span className="material-icons text-sm">{getStatusIcon()}</span>
          <span className="text-xs font-medium">{getStatusText()}</span>
        </div>
      </div>

      {/* Sample Paragraph — always visible so users know which phrase to speak */}
      <div className={`mb-4 p-4 rounded-lg border-2 ${
        localIsRecording
          ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-600'
          : 'bg-white dark:bg-slate-800/60 border-slate-200 dark:border-slate-700'
      }`}>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
          {localIsRecording ? '🎙 Speak this phrase:' : '📝 Expected phrase:'}
        </p>
        <p className="text-sm text-slate-800 dark:text-slate-200 font-medium leading-relaxed italic">
          "{getSampleParagraph()}"
        </p>
        {localIsRecording && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
            Speak naturally and clearly for best results.
          </p>
        )}
      </div>

      {/* Validating spinner */}
      {audioBlob && validationState?.status === 'validating' && (
        <div className="mb-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 flex items-center gap-2 text-amber-700 dark:text-amber-300">
          <span className="material-icons text-base animate-spin">sync</span>
          <span className="text-xs font-medium">Checking transcription…</span>
        </div>
      )}

      {/* Validation result banner */}
      {audioBlob && validationState && validationState.status !== 'validating' && (
        <div className={`mb-4 p-3 rounded-lg flex items-start gap-2 ${
          validationState.status === 'matched'
            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200'
            : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
        }`}>
          <span className="material-icons text-base mt-0.5">
            {validationState.status === 'matched' ? 'check_circle' : 'warning'}
          </span>
          <div className="flex-1 min-w-0">
            {validationState.status === 'mismatch' && (
              <p className="font-semibold text-xs mb-1">Speak the same lines displayed below.</p>
            )}
            <p className="text-xs opacity-80 truncate">
              Heard: "{validationState.transcription || '(nothing)'}"
            </p>
            <p className="text-xs opacity-60 mt-0.5">
              Match: {Math.round((validationState.similarity || 0) * 100)}%
            </p>
          </div>
        </div>
      )}

      {/* Recording Time Information */}
      {(localIsRecording || audioBlob) && (
        <div className="mb-4 p-3 bg-white/50 dark:bg-slate-800/50 rounded-lg">
          {localIsRecording ? (
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">
                  Recording: {formatTime(recordingTime)}
                </span>
              </div>
              <span className="text-xs text-slate-500">(Max 10s)</span>
            </div>
          ) : audioBlob ? (
            <div className="text-sm text-slate-700 dark:text-slate-300">
              <p className="font-mono font-semibold">
                Duration: {formatTime(duration)}
              </p>
            </div>
          ) : null}
        </div>
      )}

      {/* Hidden Audio Element for Playback */}
      {audioURL && (
        <audio
          ref={audioRef}
          src={audioURL}
          preload="auto"
          crossOrigin="anonymous"
          onEnded={handleAudioEnded}
          onError={(e) => {
            console.error('Audio element error:', e);
            setIsPlaying(false);
          }}
        />
      )}

      {/* Control Buttons */}
      <div className="flex gap-3">
        {!localIsRecording ? (
          <>
            {/* Record Button */}
            <button
              onClick={handleStartRecord}
              disabled={isRecording && isRecording !== sampleNumber}
              className="flex-1 py-2 px-4 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2"
            >
              <span className="material-icons text-lg">mic</span>
              Record
            </button>

            {/* Play Button (only if audio exists) */}
            {audioBlob && (
              <button
                onClick={handlePlay}
                className={`flex-1 py-2 px-4 ${
                  isPlaying 
                    ? 'bg-orange-500 hover:bg-orange-600' 
                    : 'bg-purple-500 hover:bg-purple-600'
                } text-white rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2`}
              >
                <span className="material-icons text-lg">
                  {isPlaying ? 'stop' : 'play_arrow'}
                </span>
                {isPlaying ? 'Stop' : 'Play'}
              </button>
            )}

            {/* Delete Button (only if audio exists) */}
            {audioBlob && (
              <button
                onClick={handleDelete}
                className="flex-1 py-2 px-4 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2"
              >
                <span className="material-icons text-lg">delete</span>
                Delete
              </button>
            )}
          </>
        ) : (
          <>
            {/* Stop Button (when recording) */}
            <button
              onClick={handleStopRecord}
              className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-sm transition-colors flex items-center justify-center gap-2 animate-pulse"
            >
              <span className="material-icons text-lg">stop</span>
              Stop Recording
            </button>
          </>
        )}
      </div>
    </div>
  );
});

export default VoiceSampleCard;
