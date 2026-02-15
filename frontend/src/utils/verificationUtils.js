/**
 * Verification Results Utilities
 * Helper functions for formatting and processing verification data
 */

/**
 * Format similarity score for display
 * @param {number} score - Similarity score (0-1)
 * @returns {string} Formatted score string
 */
export const formatScore = (score) => {
  if (typeof score !== 'number' || isNaN(score)) return 'N/A';
  return score.toFixed(4);
};

/**
 * Format percentage for display
 * @param {number} score - Value between 0-1
 * @returns {string} Formatted percentage
 */
export const formatPercentage = (score) => {
  if (typeof score !== 'number' || isNaN(score)) return 'N/A';
  return `${(score * 100).toFixed(1)}%`;
};

/**
 * Format duration in seconds to readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration
 */
export const formatDuration = (seconds) => {
  if (typeof seconds !== 'number' || isNaN(seconds)) return 'N/A';
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(2);
  return `${minutes}m ${secs}s`;
};

/**
 * Format timestamp for display
 * @param {string|Date} timestamp - ISO timestamp or Date object
 * @returns {string} Formatted timestamp
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'N/A';
  try {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleString();
  } catch {
    return 'Invalid timestamp';
  }
};

/**
 * Get confidence level label based on score
 * @param {number} score - Similarity score (0-1)
 * @returns {object} Label and color info
 */
export const getConfidenceLevel = (score) => {
  const percentage = score * 100;

  if (percentage >= 80) {
    return {
      label: 'Very High',
      color: 'emerald',
      icon: 'verified_user',
      textColor: 'text-emerald-700 dark:text-emerald-300',
      bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
      borderColor: 'border-emerald-200 dark:border-emerald-800',
    };
  } else if (percentage >= 60) {
    return {
      label: 'High',
      color: 'lime',
      icon: 'check_circle',
      textColor: 'text-lime-700 dark:text-lime-300',
      bgColor: 'bg-lime-100 dark:bg-lime-900/30',
      borderColor: 'border-lime-200 dark:border-lime-800',
    };
  } else if (percentage >= 40) {
    return {
      label: 'Medium',
      color: 'amber',
      icon: 'info',
      textColor: 'text-amber-700 dark:text-amber-300',
      bgColor: 'bg-amber-100 dark:bg-amber-900/30',
      borderColor: 'border-amber-200 dark:border-amber-800',
    };
  } else if (percentage >= 20) {
    return {
      label: 'Low',
      color: 'orange',
      icon: 'warning',
      textColor: 'text-orange-700 dark:text-orange-300',
      bgColor: 'bg-orange-100 dark:bg-orange-900/30',
      borderColor: 'border-orange-200 dark:border-orange-800',
    };
  } else {
    return {
      label: 'Very Low',
      color: 'red',
      icon: 'cancel',
      textColor: 'text-red-700 dark:text-red-300',
      bgColor: 'bg-red-100 dark:bg-red-900/30',
      borderColor: 'border-red-200 dark:border-red-800',
    };
  }
};

/**
 * Get status color and icon based on verification result
 * @param {boolean} isMatch - Whether verification matched
 * @returns {object} Status styling information
 */
export const getVerificationStatus = (isMatch) => {
  return isMatch
    ? {
        label: 'VERIFIED',
        icon: 'verified_user',
        textColor: 'text-emerald-700 dark:text-emerald-300',
        bgColor: 'bg-emerald-100 dark:bg-emerald-900/30',
        borderColor: 'border-emerald-200 dark:border-emerald-800',
        accentColor: 'emerald',
      }
    : {
        label: 'NOT VERIFIED',
        icon: 'gpp_bad',
        textColor: 'text-red-700 dark:text-red-300',
        bgColor: 'bg-red-100 dark:bg-red-900/30',
        borderColor: 'border-red-200 dark:border-red-800',
        accentColor: 'red',
      };
};

/**
 * Calculate success rate from attempts
 * @param {array} attempts - Array of attempt objects
 * @returns {number} Success rate as percentage (0-100)
 */
export const calculateSuccessRate = (attempts) => {
  if (!attempts || attempts.length === 0) return 0;
  const successful = attempts.filter(a => a.success || a.result === 'match').length;
  return (successful / attempts.length) * 100;
};

/**
 * Get statistics from attempts
 * @param {array} attempts - Array of attempt objects
 * @returns {object} Statistics object
 */
export const getAttemptStatistics = (attempts) => {
  if (!attempts || attempts.length === 0) {
    return {
      totalAttempts: 0,
      successfulAttempts: 0,
      failedAttempts: 0,
      successRate: 0,
      averageScore: 0,
      bestScore: 0,
      worstScore: 0,
    };
  }

  const successful = attempts.filter(a => a.success || a.result === 'match').length;
  const failed = attempts.length - successful;
  const scores = attempts.map(a => a.similarity_score || a.score || 0);

  return {
    totalAttempts: attempts.length,
    successfulAttempts: successful,
    failedAttempts: failed,
    successRate: (successful / attempts.length) * 100,
    averageScore: scores.reduce((sum, score) => sum + score, 0) / scores.length,
    bestScore: Math.max(...scores),
    worstScore: Math.min(...scores),
  };
};

/**
 * Determine if score is above threshold
 * @param {number} score - Similarity score
 * @param {number} threshold - Threshold value
 * @returns {object} Comparison object
 */
export const compareWithThreshold = (score, threshold) => {
  const isAbove = score >= threshold;
  const difference = isAbove ? score - threshold : threshold - score;

  return {
    isAbove,
    difference: difference,
    differencePercentage: (difference * 100).toFixed(2),
    status: isAbove ? 'ABOVE' : 'BELOW',
  };
};

/**
 * Get color gradient based on score
 * @param {number} score - Score value (0-1)
 * @returns {object} Color gradient info
 */
export const getScoreGradient = (score) => {
  if (score >= 0.9) {
    return {
      from: 'from-emerald-600',
      to: 'to-emerald-500',
      color: 'emerald',
    };
  } else if (score >= 0.8) {
    return {
      from: 'from-lime-600',
      to: 'to-lime-500',
      color: 'lime',
    };
  } else if (score >= 0.7) {
    return {
      from: 'from-amber-600',
      to: 'to-amber-500',
      color: 'amber',
    };
  } else if (score >= 0.5) {
    return {
      from: 'from-orange-600',
      to: 'to-orange-500',
      color: 'orange',
    };
  } else {
    return {
      from: 'from-red-600',
      to: 'to-red-500',
      color: 'red',
    };
  }
};

/**
 * Parse verification result from API response
 * @param {object} response - API response object
 * @returns {object} Parsed result object
 */
export const parseVerificationResult = (response) => {
  if (!response) return null;

  return {
    score: response.similarity_score || response.score || 0,
    isMatch: response.verified || (response.similarity_score >= 0.85),
    phoneNumber: response.phone_number || 'Unknown',
    threshold: response.threshold_used || 0.85,
    timestamp: response.timestamp || new Date().toISOString(),
    sessionId: response.session_id || null,
    attempts: response.attempts || [],
    duration: response.audio_duration_seconds || 0,
    confusionScore: response.confusion_score || null,
    error: response.error || null,
    raw: response,
  };
};

/**
 * Generate verification report summary
 * @param {object} result - Parsed verification result
 * @returns {string} Summary text
 */
export const generateVerificationSummary = (result) => {
  if (!result) return 'No verification result available.';

  const { score, isMatch, threshold, phoneNumber } = result;
  const difference = Math.abs(score - threshold);

  if (isMatch) {
    return `Voice verification SUCCESSFUL for ${phoneNumber}. Score ${score.toFixed(4)} exceeds threshold ${threshold.toFixed(2)} by ${(difference * 100).toFixed(1)}%.`;
  } else {
    return `Voice verification FAILED for ${phoneNumber}. Score ${score.toFixed(4)} is below threshold ${threshold.toFixed(2)} by ${(difference * 100).toFixed(1)}%.`;
  }
};

/**
 * Export result data as JSON
 * @param {object} result - Verification result
 * @returns {string} JSON string
 */
export const exportResultAsJSON = (result) => {
  return JSON.stringify(result, null, 2);
};

/**
 * Export result data as CSV
 * @param {object} result - Verification result
 * @returns {string} CSV string
 */
export const exportResultAsCSV = (result) => {
  if (!result) return '';

  const lines = [
    'Verification Result Report',
    `Date: ${new Date().toLocaleString()}`,
    '',
    'Summary',
    `Status,${result.isMatch ? 'VERIFIED' : 'NOT VERIFIED'}`,
    `Phone Number,${result.phoneNumber}`,
    `Score,${result.score.toFixed(4)}`,
    `Threshold,${result.threshold.toFixed(2)}`,
    `Duration,${result.duration}`,
    '',
    'Attempts',
  ];

  if (result.attempts && result.attempts.length > 0) {
    lines.push('Attempt Number,Score,Result,Duration,Timestamp');
    result.attempts.forEach((attempt, index) => {
      const score = attempt.similarity_score || attempt.score || 0;
      const resultStatus = attempt.result || (score >= 0.85 ? 'MATCH' : 'MISMATCH');
      const duration = attempt.audio_duration_seconds || 0;
      const timestamp = attempt.timestamp || 'N/A';
      lines.push(`${index + 1},${score.toFixed(4)},${resultStatus},${duration},${timestamp}`);
    });
  }

  return lines.join('\n');
};
