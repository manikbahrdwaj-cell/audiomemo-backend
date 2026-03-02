import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { createAudioRecorder, calculateDuration } from '../utils/audioRecorder';

/**
 * VoiceSampleCard Component
 * Reusable card for recording individual voice samples
 * Features: Record, Stop, Playback, Delete with visual feedback
 */
const VoiceSampleCard = forwardRef(function VoiceSampleCard({ sampleNumber, onAudioRecorded, audioBlob, isRecording, onRecordingStart, onRecordingStop }, ref) {
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
    return SAMPLE_PARAGRAPHS[sampleNumber] || '';
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

  // Determine card color based on recording status
  const getCardColor = () => {
    if (audioBlob) {
      return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800';
    }
    return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
  };

  const getStatusColor = () => {
    if (audioBlob) {
      return 'text-emerald-700 dark:text-emerald-300';
    }
    return 'text-red-700 dark:text-red-300';
  };

  const getStatusIcon = () => {
    return audioBlob ? 'check_circle' : 'circle';
  };

  const getStatusText = () => {
    return audioBlob ? 'Recorded' : 'Not Recorded';
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

      {/* Sample Paragraph - displayed when recording */}
      {localIsRecording && (
        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/30 border-2 border-blue-300 dark:border-blue-600 rounded-lg">
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2 text-center">
            📝 Please speak the following paragraph clearly:
          </p>
          <div className="p-3 bg-white dark:bg-slate-800 rounded border border-blue-200 dark:border-blue-700">
            <p className="text-sm text-center text-gray-800 dark:text-gray-200 font-medium leading-relaxed italic">
              "{getSampleParagraph()}"
            </p>
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-2 text-center">
            Speak naturally and clearly for best results.
          </p>
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
