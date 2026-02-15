import React, { useState, useEffect } from 'react';
import ProgressBar from './ProgressBar';
import '../styles/ChunkProcessingIndicator.css';

/**
 * ChunkProcessingIndicator Component
 * Displays real-time chunk processing feedback with details
 */
function ChunkProcessingIndicator({
  isVisible = false,
  progress = null,
  onComplete = () => {},
  onError = () => {}
}) {
  const [displayedProgress, setDisplayedProgress] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [animatedChunks, setAnimatedChunks] = useState([]);

  useEffect(() => {
    if (progress) {
      setDisplayedProgress(progress);
      
      // Update status message
      if (progress.status === 'completed') {
        setStatusMessage('Processing complete!');
        onComplete();
      } else if (progress.status === 'failed') {
        setStatusMessage(`Error: ${progress.error_message}`);
        onError(progress.error_message);
      } else if (progress.status === 'processing_chunk') {
        setStatusMessage(`Processing chunk ${progress.current_chunk} of ${progress.total_chunks}`);
      } else if (progress.status === 'embedding_generated') {
        setStatusMessage(`Generated embedding for chunk ${progress.current_chunk}`);
      } else if (progress.status === 'started') {
        setStatusMessage('Starting processing...');
      }

      // Update animated chunks list (show last 5)
      if (progress.chunks_processed) {
        const lastChunks = progress.chunks_processed.slice(-5);
        setAnimatedChunks(lastChunks);
      }
    }
  }, [progress, onComplete, onError]);

  if (!isVisible || !displayedProgress) {
    return null;
  }

  const statusColor = {
    completed: 'indicator-status--success',
    failed: 'indicator-status--error',
    processing_chunk: 'indicator-status--processing',
    embedding_generated: 'indicator-status--processing',
    started: 'indicator-status--info',
  }[displayedProgress.status] || 'indicator-status--info';

  const duration = Math.round(displayedProgress.duration_ms);
  const durationSeconds = (duration / 1000).toFixed(2);

  return (
    <div className="chunk-processing-indicator">
      <div className="indicator-header">
        <h3 className="indicator-title">
          <span className="indicator-icon">🔊</span>
          Audio Processing
        </h3>
        <span className={`indicator-status ${statusColor}`}>
          {displayedProgress.status.replace(/_/g, ' ').toUpperCase()}
        </span>
      </div>

      <div className="indicator-content">
        {/* Main Progress Bar */}
        <ProgressBar
          percentage={displayedProgress.percentage}
          status={displayedProgress.status === 'failed' ? 'failed' : 
                  displayedProgress.status === 'completed' ? 'completed' : 'processing'}
          label="Overall Progress"
          showPercentage={true}
          animated={displayedProgress.status !== 'completed'}
          size="medium"
        />

        {/* Stats Grid */}
        <div className="indicator-stats">
          <div className="stat-item">
            <div className="stat-label">Chunks Processed</div>
            <div className="stat-value">
              {displayedProgress.current_chunk}/{displayedProgress.total_chunks}
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Duration</div>
            <div className="stat-value">{durationSeconds}s</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Session ID</div>
            <div className="stat-value stat-value--muted">
              {displayedProgress.session_id.substring(0, 8)}...
            </div>
          </div>
        </div>

        {/* Status Message */}
        {statusMessage && (
          <div className={`indicator-message ${statusColor}`}>
            {statusMessage}
          </div>
        )}

        {/* Current Chunk Info */}
        {displayedProgress.current_chunk_info && (
          <div className="indicator-current-chunk">
            <div className="chunk-info-label">Current Chunk:</div>
            <div className="chunk-info-details">
              Chunk #{displayedProgress.current_chunk_info.chunk_index + 1}
              {displayedProgress.current_chunk_info.embedding_generated && (
                <span className="chunk-embedding-badge">✓ Embedded</span>
              )}
            </div>
          </div>
        )}

        {/* Error Details */}
        {displayedProgress.error_message && (
          <div className="indicator-error">
            <div className="error-label">Error Details:</div>
            <div className="error-message">{displayedProgress.error_message}</div>
          </div>
        )}

        {/* Recent Chunks */}
        {animatedChunks.length > 0 && (
          <div className="indicator-chunks-list">
            <div className="chunks-label">Recent Chunks:</div>
            <div className="chunks-container">
              {animatedChunks.map((chunk, index) => (
                <div
                  key={`${chunk.chunk_index}-${index}`}
                  className={`chunk-badge ${
                    chunk.embedding_generated ? 'chunk-badge--embedded' : 'chunk-badge--processing'
                  }`}
                  title={`Chunk ${chunk.chunk_index}`}
                >
                  {chunk.chunk_index}
                  {chunk.embedding_generated && <span className="badge-checkmark">✓</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Loading Animation */}
      {displayedProgress.status !== 'completed' && displayedProgress.status !== 'failed' && (
        <div className="indicator-loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      )}
    </div>
  );
}

export default ChunkProcessingIndicator;
