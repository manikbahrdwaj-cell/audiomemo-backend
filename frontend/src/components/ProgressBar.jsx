import React from 'react';
import '../styles/ProgressBar.css';

/**
 * ProgressBar Component
 * Displays a visual progress bar with percentage and status
 */
function ProgressBar({
  percentage = 0,
  status = 'processing',
  label = 'Processing',
  showPercentage = true,
  animated = true,
  size = 'medium',
  variant = 'primary'
}) {
  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'processing':
        return '#3b82f6';
      default:
        return '#6b7280';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'failed':
        return '✕';
      case 'processing':
        return '◌';
      default:
        return '';
    }
  };

  const sizeClass = `progress-bar--${size}`;
  const animatedClass = animated && status === 'processing' ? 'progress-bar--animated' : '';

  return (
    <div className={`progress-bar-container ${sizeClass}`}>
      <div className="progress-bar-header">
        <span className="progress-bar-label">
          <span className="progress-bar-status-icon">{getStatusIcon()}</span>
          {label}
        </span>
        {showPercentage && (
          <span className="progress-bar-percentage">
            {Math.round(percentage)}%
          </span>
        )}
      </div>
      
      <div className="progress-bar-track">
        <div
          className={`progress-bar-fill ${animatedClass}`}
          style={{
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: getStatusColor(),
          }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
