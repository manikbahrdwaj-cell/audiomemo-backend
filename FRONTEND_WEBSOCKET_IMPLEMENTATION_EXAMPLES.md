/**
 * Frontend WebSocket Implementation Examples
 * Complete code examples for common scenarios
 */

// ============================================
// EXAMPLE 1: Basic Enrollment Component
// ============================================

import React, { useState } from 'react';
import { useEnrollmentService } from '../context/WebSocketContext';
import { useEnrollment } from '../hooks/useEnrollment';

export function BasicEnrollmentExample() {
  const [phone, setPhone] = useState('');
  const enrollmentService = useEnrollmentService();
  const { 
    startEnrollment, 
    submitChunk, 
    completeEnrollment, 
    progress, 
    error 
  } = useEnrollment(enrollmentService);

  const handleEnroll = async () => {
    try {
      // Start session
      await startEnrollment(phone);
      
      // Simulate recording and submitting 3 chunks
      for (let i = 0; i < 3; i++) {
        const audioBlob = new Blob(); // Replace with actual audio
        await submitChunk(audioBlob, i);
      }
      
      // Complete
      await completeEnrollment();
    } catch (err) {
      console.error('Enrollment failed:', err);
    }
  };

  return (
    <div>
      <input 
        value={phone} 
        onChange={(e) => setPhone(e.target.value)} 
        placeholder="Phone number"
      />
      <button onClick={handleEnroll}>Enroll</button>
      <p>Progress: {progress.toFixed(0)}%</p>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}

// ============================================
// EXAMPLE 2: Real-Time Verification Component
// ============================================

export function RealTimeVerificationExample() {
  const [phone, setPhone] = useState('');
  const [similarity, setSimilarity] = useState(null);
  const verificationService = useVerificationService();

  const handleVerify = async () => {
    // Start verification
    await verificationService.startVerification(phone, {
      similarity_threshold: 0.85,
      max_attempts: 3,
    });

    // Listen to real-time updates
    verificationService.on('verification:comparing', (data) => {
      setSimilarity(data.similarity);
    });

    verificationService.on('verification:verified', (data) => {
      alert('Verified! Similarity: ' + data.similarity);
    });
  };

  return (
    <div>
      <input 
        value={phone} 
        onChange={(e) => setPhone(e.target.value)}
        placeholder="Phone number"
      />
      <button onClick={handleVerify}>Verify</button>
      {similarity && (
        <p>Current Similarity: {(similarity * 100).toFixed(2)}%</p>
      )}
    </div>
  );
}

// ============================================
// EXAMPLE 3: Advanced Enrollment with Progress Tracking
// ============================================

export function AdvancedEnrollmentExample() {
  const [stats, setStats] = useState({
    totalChunks: 0,
    processedChunks: 0,
    failedChunks: 0,
    startTime: null,
    endTime: null,
  });

  const enrollmentService = useEnrollmentService();

  const handleEnrollWithTracking = async () => {
    const startTime = Date.now();
    
    try {
      // Start enrollment
      await enrollmentService.startEnrollment('+1-555-0000', {
        max_chunks: 5,
        auto_process: true,
      });

      // Track chunk events
      enrollmentService.on('enrollment:chunk_processed', (data) => {
        setStats(prev => ({
          ...prev,
          processedChunks: prev.processedChunks + 1,
        }));
      });

      enrollmentService.on('enrollment:error', (data) => {
        setStats(prev => ({
          ...prev,
          failedChunks: prev.failedChunks + 1,
        }));
      });

      // Track completion
      enrollmentService.on('enrollment:completed', (data) => {
        const endTime = Date.now();
        setStats(prev => ({
          ...prev,
          endTime: endTime,
          totalTime: endTime - startTime,
          vectorId: data.vectorId,
        }));
      });

      // Submit chunks (replace with actual recording)
      for (let i = 0; i < 5; i++) {
        const chunkData = new Blob();
        await enrollmentService.submitAudioChunk(chunkData, i);
      }

      // Complete
      await enrollmentService.completeEnrollment();
    } catch (error) {
      console.error('Enrollment failed:', error);
    }
  };

  return (
    <div>
      <button onClick={handleEnrollWithTracking}>
        Start Advanced Enrollment
      </button>
      
      <div>
        <p>Total Chunks: {stats.totalChunks}</p>
        <p>Processed: {stats.processedChunks}</p>
        <p>Failed: {stats.failedChunks}</p>
        {stats.totalTime && (
          <p>Time: {(stats.totalTime / 1000).toFixed(2)}s</p>
        )}
      </div>
    </div>
  );
}

// ============================================
// EXAMPLE 4: Error Recovery with Retry Logic
// ============================================

import { retryOperation } from '../utils/webSocketUtils';

export function EnrollmentWithRetryExample() {
  const enrollmentService = useEnrollmentService();

  const submitChunkWithRetry = async (audioBlob, chunkIndex) => {
    try {
      const result = await retryOperation(
        () => enrollmentService.submitAudioChunk(audioBlob, chunkIndex),
        3,  // Max attempts
        1000,  // Initial delay (1s)
        2  // Backoff multiplier
      );
      
      console.log('Chunk submitted successfully on retry');
      return result;
    } catch (error) {
      console.error('Failed to submit chunk after retries:', error);
      throw error;
    }
  };

  return (
    <button onClick={async () => {
      const audioBlob = new Blob();
      await submitChunkWithRetry(audioBlob, 0);
    }}>
      Submit with Retry
    </button>
  );
}

// ============================================
// EXAMPLE 5: Multi-Chunk Upload with Progress
// ============================================

export function MultiChunkUploadExample() {
  const [uploadProgress, setUploadProgress] = useState({
    current: 0,
    total: 0,
    percentage: 0,
  });

  const enrollmentService = useEnrollmentService();

  const uploadMultipleChunks = async (chunks) => {
    setUploadProgress({ current: 0, total: chunks.length, percentage: 0 });

    const sessionId = await enrollmentService.startEnrollment('+1-555-0000');

    for (let i = 0; i < chunks.length; i++) {
      try {
        await enrollmentService.submitAudioChunk(chunks[i], i);
        
        setUploadProgress(prev => ({
          current: i + 1,
          total: chunks.length,
          percentage: ((i + 1) / chunks.length) * 100,
        }));
      } catch (error) {
        console.error(`Failed to upload chunk ${i}:`, error);
      }
    }

    await enrollmentService.completeEnrollment();
  };

  return (
    <div>
      <div>
        Progress: {uploadProgress.current}/{uploadProgress.total}
      </div>
      <div style={{ width: '100%', backgroundColor: '#eee' }}>
        <div 
          style={{ 
            width: uploadProgress.percentage + '%',
            backgroundColor: '#0066cc',
            height: '20px',
            transition: 'width 0.3s',
          }}
        />
      </div>
      <p>{uploadProgress.percentage.toFixed(0)}%</p>
    </div>
  );
}

// ============================================
// EXAMPLE 6: Session Persistence
// ============================================

import { SessionPersistenceManager } from '../utils/webSocketUtils';

export function PersistentSessionExample() {
  const persistenceManager = new SessionPersistenceManager('enrollment_sessions_');
  const enrollmentService = useEnrollmentService();

  const resumeEnrollment = async (sessionId) => {
    // Load previous session data
    const sessionData = persistenceManager.loadSession(sessionId);
    
    if (sessionData) {
      console.log('Resuming session:', sessionData);
      
      // Resume upload for remaining chunks
      for (let i = sessionData.uploadedChunks; i < sessionData.totalChunks; i++) {
        const chunkData = new Blob();
        await enrollmentService.submitAudioChunk(chunkData, i);
      }

      await enrollmentService.completeEnrollment();
    }
  };

  const startNewEnrollmentWithPersistence = async (phone) => {
    const sessionId = await enrollmentService.startEnrollment(phone);

    // Save session data
    persistenceManager.saveSession(sessionId, {
      phone,
      uploadedChunks: 0,
      totalChunks: 5,
      status: 'active',
    });

    return sessionId;
  };

  return (
    <div>
      <button onClick={() => startNewEnrollmentWithPersistence('+1-555-0000')}>
        Start with Persistence
      </button>
    </div>
  );
}

// ============================================
// EXAMPLE 7: Connection Monitoring
// ============================================

import { WebSocketConnectionMonitor } from '../utils/webSocketUtils';

export function ConnectionMonitoringExample() {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const { wsClient } = useWebSocket();

  React.useEffect(() => {
    const monitor = new WebSocketConnectionMonitor(wsClient, (status) => {
      console.log('Connection status:', status);
      setConnectionStatus(status.status);
    });

    return () => {
      monitor.reset();
    };
  }, [wsClient]);

  return (
    <div>
      <p>Connection Status: {connectionStatus}</p>
      <div style={{
        width: '20px',
        height: '20px',
        backgroundColor: connectionStatus === 'connected' ? 'green' : 'red',
        borderRadius: '50%',
      }} />
    </div>
  );
}

// ============================================
// EXAMPLE 8: Complete Enrollment Workflow
// ============================================

export function CompleteEnrollmentWorkflowExample() {
  const [step, setStep] = useState(0);
  const [phone, setPhone] = useState('');
  const [recordings, setRecordings] = useState([]);
  const enrollmentService = useEnrollmentService();

  const steps = [
    {
      title: 'Enter Phone Number',
      component: (
        <div>
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+1-555-0000"
          />
          <button onClick={() => setStep(1)}>Next</button>
        </div>
      ),
    },
    {
      title: 'Record Audio Chunks (3 needed)',
      component: (
        <div>
          <p>Recordings: {recordings.length}/3</p>
          <button onClick={async () => {
            const audioBlob = new Blob();
            setRecordings([...recordings, audioBlob]);
            if (recordings.length === 2) setStep(2);
          }}>
            Record ({recordings.length}/3)
          </button>
        </div>
      ),
    },
    {
      title: 'Upload and Process',
      component: (
        <div>
          <button onClick={async () => {
            await enrollmentService.startEnrollment(phone);
            for (let i = 0; i < recordings.length; i++) {
              await enrollmentService.submitAudioChunk(recordings[i], i);
            }
            await enrollmentService.completeEnrollment();
          }}>
            Complete Enrollment
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <h2>{steps[step].title}</h2>
      {steps[step].component}
    </div>
  );
}

// ============================================
// EXAMPLE 9: Verification with Attempt Tracking
// ============================================

export function VerificationWithAttemptTrackingExample() {
  const [attempts, setAttempts] = useState([]);
  const [currentAttempt, setCurrentAttempt] = useState(null);
  const verificationService = useVerificationService();

  const makeVerificationAttempt = async (audioBlob) => {
    const attemptNumber = attempts.length + 1;
    
    setCurrentAttempt({
      number: attemptNumber,
      status: 'processing',
      similarity: null,
      result: null,
    });

    try {
      await verificationService.submitAudio(audioBlob);

      verificationService.on('verification:verified', (data) => {
        const attempt = {
          number: attemptNumber,
          status: 'verified',
          similarity: data.similarity,
          result: 'MATCH',
          timestamp: new Date(),
        };
        setAttempts([...attempts, attempt]);
        setCurrentAttempt(null);
      });

      verificationService.on('verification:rejected', (data) => {
        const attempt = {
          number: attemptNumber,
          status: 'rejected',
          similarity: data.similarity,
          result: 'MISMATCH',
          timestamp: new Date(),
        };
        setAttempts([...attempts, attempt]);
        setCurrentAttempt(null);
      });
    } catch (error) {
      console.error('Attempt failed:', error);
      setCurrentAttempt(null);
    }
  };

  return (
    <div>
      <h3>Verification Attempts</h3>
      <ul>
        {attempts.map((attempt, i) => (
          <li key={i}>
            Attempt {attempt.number}: {attempt.result} 
            (Similarity: {(attempt.similarity * 100).toFixed(2)}%)
          </li>
        ))}
      </ul>
      {currentAttempt && <p>Attempt {currentAttempt.number}: {currentAttempt.status}</p>}
    </div>
  );
}

// ============================================
// EXAMPLE 10: Form Validation Helper
// ============================================

export function validateEnrollmentForm(formData) {
  const errors = {};

  if (!formData.phone || !/^[\d+\-\s()]{7,}$/.test(formData.phone)) {
    errors.phone = 'Invalid phone number';
  }

  if (!formData.audioChunks || formData.audioChunks.length < 2) {
    errors.audio = 'At least 2 audio chunks required';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}
