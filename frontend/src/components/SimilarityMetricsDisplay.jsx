/**
 * SimilarityMetricsDisplay Component
 * Displays comprehensive similarity metrics with visual representations
 * Shows cosine similarity, distances, confidence levels, and match status
 */

import React from 'react';
import '../styles/SimilarityMetrics.css';

function SimilarityMetricsDisplay({ metrics = {}, threshold = 0.75, isMatch = false }) {
  if (!metrics || Object.keys(metrics).length === 0) {
    return null;
  }

  const {
    cosine_similarity = 0,
    cosine_distance = 0,
    euclidean_distance = 0,
    correlation_distance = 0,
    confidence = 0,
  } = metrics;

  // Normalize values for display
2  const cosineSimilarityPercent = Math.round(cosine_similarity * 100);
  const confidencePercent = Math.round(confidence * 100);
  const thresholdPercent = Math.round(threshold * 100);

  // Determine colors based on values
  const getSimilarityColor = (value) => {
    if (value >= threshold) return 'success'; // Green
    if (value >= threshold - 0.1) return 'warning'; // Yellow
    return 'danger'; // Red
  };

  const getConfidenceColor = (value) => {
    if (value >= 0.7) return 'success'; // Green
    if (value >= 0.4) return 'warning'; // Yellow
    return 'danger'; // Red
  };

  const similarityColor = getSimilarityColor(cosine_similarity);
  const confidenceColor = getConfidenceColor(confidence);
  const matchStatusColor = isMatch ? 'success' : 'danger';
  const matchStatusText = isMatch ? 'MATCH' : 'NO MATCH';

  return (
    <div className="similarity-metrics-container">
      {/* Main Match Status */}
      <div className={`match-status-banner ${matchStatusColor}`}>
        <div className="match-status-content">
          <span className="match-status-icon">
            {isMatch ? '✓' : '✗'}
          </span>
          <span className="match-status-text">{matchStatusText}</span>
        </div>
      </div>

      {/* Primary Metrics */}
      <div className="metrics-grid">
        {/* Cosine Similarity */}
        <div className="metric-card">
          <div className="metric-header">
            <h4 className="metric-title">Cosine Similarity</h4>
            <span className={`metric-badge ${similarityColor}`}>
              {cosineSimilarityPercent}%
            </span>
          </div>
          <div className="metric-body">
            <div className="progress-bar-container">
              <div
                className={`progress-bar ${similarityColor}`}
                style={{ width: `${cosineSimilarityPercent}%` }}
              />
            </div>
            <div className="metric-value">{cosine_similarity.toFixed(4)}</div>
            <div className="metric-threshold">
              Threshold: {thresholdPercent}%
              {cosine_similarity >= threshold && (
                <span className="metric-indicator">✓ Above threshold</span>
              )}
              {cosine_similarity < threshold && (
                <span className="metric-indicator danger">✗ Below threshold</span>
              )}
            </div>
          </div>
        </div>

        {/* Confidence Level */}
        <div className="metric-card">
          <div className="metric-header">
            <h4 className="metric-title">Confidence Level</h4>
            <span className={`metric-badge ${confidenceColor}`}>
              {confidencePercent}%
            </span>
          </div>
          <div className="metric-body">
            <div className="progress-bar-container">
              <div
                className={`progress-bar ${confidenceColor}`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
            <div className="metric-value">{confidence.toFixed(4)}</div>
            <div className="metric-description">
              {confidencePercent >= 70
                ? 'High confidence match'
                : confidencePercent >= 40
                ? 'Moderate confidence'
                : 'Low confidence match'}
            </div>
          </div>
        </div>
      </div>

      {/* Distance Metrics */}
      <div className="distance-metrics">
        <h4 className="section-title">Distance Metrics</h4>
        <div className="metrics-table">
          <div className="metric-row">
            <div className="metric-label">
              <span className="label-name">Cosine Distance</span>
              <span className="label-help">Lower is better</span>
            </div>
            <div className="metric-value-container">
              <div className="value">{cosine_distance.toFixed(4)}</div>
              <div className="value-scale">0 ← → 1</div>
            </div>
          </div>

          <div className="metric-row">
            <div className="metric-label">
              <span className="label-name">Euclidean Distance</span>
              <span className="label-help">Vector space distance</span>
            </div>
            <div className="metric-value-container">
              <div className="value">{euclidean_distance.toFixed(4)}</div>
            </div>
          </div>

          {correlation_distance !== null && correlation_distance !== undefined && (
            <div className="metric-row">
              <div className="metric-label">
                <span className="label-name">Correlation Distance</span>
                <span className="label-help">Pattern correlation</span>
              </div>
              <div className="metric-value-container">
                <div className="value">{correlation_distance.toFixed(4)}</div>
                <div className="value-scale">0 ← → 1</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Interpretation Guide */}
      <div className="interpretation-guide">
        <h4 className="section-title">How to Read These Metrics</h4>
        <ul className="guide-list">
          <li>
            <strong>Cosine Similarity:</strong> Measures angle between embeddings. 1.0 = identical, 0.0 = orthogonal
          </li>
          <li>
            <strong>Confidence:</strong> Derived from similarity vs threshold. Shows match reliability.
          </li>
          <li>
            <strong>Cosine Distance:</strong> 1 - Similarity. Normalized distance metric.
          </li>
          <li>
            <strong>Euclidean Distance:</strong> L2 norm of vector difference. Absolute distance.
          </li>
          <li>
            <strong>Correlation Distance:</strong> 1 - Pearson correlation. Pattern similarity.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default SimilarityMetricsDisplay;
