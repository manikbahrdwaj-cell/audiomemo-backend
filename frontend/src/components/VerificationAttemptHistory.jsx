import React, { useState } from 'react';

/**
 * Displays verification attempt history and details
 * Shows all attempts made during verification session
 */
function VerificationAttemptHistory({ attempts = [] }) {
  const [expandedAttempt, setExpandedAttempt] = useState(null);

  if (!attempts || attempts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-center">
          <span className="material-icons text-5xl text-slate-300 dark:text-slate-700">history</span>
          <p className="text-slate-500 dark:text-slate-400 font-medium mt-4">No attempt history</p>
          <p className="text-slate-400 text-sm mt-2">Verification attempts will be shown here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-6">
      {/* Summary Statistics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
            Total Attempts
          </p>
          <p className="text-2xl font-bold text-slate-800 dark:text-white">
            {attempts.length}
          </p>
        </div>
        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-200 dark:border-emerald-800 p-4">
          <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-1">
            Passed
          </p>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {attempts.filter(a => a.success || a.result === 'match').length}
          </p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 p-4">
          <p className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wider mb-1">
            Failed
          </p>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">
            {attempts.filter(a => !a.success && a.result !== 'match').length}
          </p>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-4">
          <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider mb-1">
            Success Rate
          </p>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {attempts.length > 0
              ? ((attempts.filter(a => a.success || a.result === 'match').length / attempts.length) * 100).toFixed(0)
              : 0}%
          </p>
        </div>
      </div>

      {/* Attempts Timeline */}
      <div className="space-y-3">
        {attempts.map((attempt, index) => {
          const isExpanded = expandedAttempt === index;
          const isSuccess = attempt.success || attempt.result === 'match';
          const score = attempt.similarity_score || attempt.score || 0;
          const timestamp = attempt.timestamp ? new Date(attempt.timestamp) : null;

          return (
            <div
              key={index}
              className={`rounded-xl border transition-all ${
                isExpanded
                  ? 'border-primary bg-white dark:bg-slate-900 shadow-lg'
                  : `border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50 hover:border-slate-300 dark:hover:border-slate-600 cursor-pointer`
              }`}
            >
              {/* Attempt Header */}
              <button
                onClick={() => setExpandedAttempt(isExpanded ? null : index)}
                className="w-full p-4 flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-4 flex-grow">
                  {/* Status Indicator */}
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isSuccess
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                    }`}
                  >
                    <span className="material-icons text-lg">
                      {isSuccess ? 'check_circle' : 'cancel'}
                    </span>
                  </div>

                  {/* Attempt Info */}
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-slate-800 dark:text-white">
                        Attempt #{index + 1}
                      </p>
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          isSuccess
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                            : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'
                        }`}
                      >
                        {isSuccess ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Score: {score.toFixed(4)} • {timestamp?.toLocaleTimeString() || 'No timestamp'}
                    </p>
                  </div>

                  {/* Score Indicator */}
                  <div className="flex-shrink-0">
                    <div className="text-right">
                      <p className={`text-lg font-black ${
                        isSuccess
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}>
                        {(score * 100).toFixed(0)}%
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">confidence</p>
                    </div>
                  </div>

                  {/* Expand Icon */}
                  <span className={`material-icons text-slate-400 transition-transform ${
                    isExpanded ? 'rotate-180' : ''
                  }`}>
                    expand_more
                  </span>
                </div>
              </button>

              {/* Attempt Details */}
              {isExpanded && (
                <div className="border-t border-slate-200 dark:border-slate-700 px-4 py-4 space-y-4 bg-slate-50 dark:bg-slate-800/50">
                  {/* Grid of Details */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                        Attempt ID
                      </p>
                      <p className="text-sm font-mono text-slate-700 dark:text-slate-300 break-all">
                        {attempt.attempt_id || `attempt_${index + 1}`}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                        Duration
                      </p>
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        {attempt.audio_duration_seconds
                          ? `${attempt.audio_duration_seconds.toFixed(2)}s`
                          : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                        Similarity Score
                      </p>
                      <p className="text-sm font-mono text-slate-700 dark:text-slate-300">
                        {score.toFixed(6)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                        Threshold
                      </p>
                      <p className="text-sm font-mono text-slate-700 dark:text-slate-300">
                        {attempt.threshold_used
                          ? attempt.threshold_used.toFixed(4)
                          : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                        Result
                      </p>
                      <span className={`inline-block text-xs font-bold px-2 py-1 rounded ${
                        isSuccess
                          ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                          : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'
                      }`}>
                        {attempt.result ? attempt.result.toUpperCase() : (isSuccess ? 'MATCH' : 'MISMATCH')}
                      </span>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                        Timestamp
                      </p>
                      <p className="text-sm font-mono text-slate-700 dark:text-slate-300">
                        {timestamp?.toLocaleString() || 'N/A'}
                      </p>
                    </div>
                  </div>

                  {/* Score Comparison */}
                  <div className="pt-4 border-t border-slate-300 dark:border-slate-600">
                    <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-3">
                      Score Analysis
                    </p>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs text-slate-600 dark:text-slate-400">Against Threshold</span>
                          <span className={`text-xs font-bold ${
                            score >= (attempt.threshold_used || 0.85)
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}>
                            {score >= (attempt.threshold_used || 0.85) ? 'ABOVE' : 'BELOW'}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              isSuccess ? 'bg-emerald-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${Math.min((score / (attempt.threshold_used || 0.85)) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Error Message (if any) */}
                  {attempt.error && (
                    <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <p className="text-xs font-semibold text-red-700 dark:text-red-300 mb-1">Error</p>
                      <p className="text-xs text-red-600 dark:text-red-400">{attempt.error}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Statistics Summary */}
      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 p-6 mt-6">
        <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-4">
          Session Statistics
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mb-1">Average Score</p>
            <p className="text-2xl font-bold text-slate-800 dark:text-white">
              {(attempts.reduce((sum, a) => sum + (a.similarity_score || a.score || 0), 0) / attempts.length).toFixed(4)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mb-1">Best Score</p>
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {Math.max(...attempts.map(a => a.similarity_score || a.score || 0)).toFixed(4)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mb-1">Worst Score</p>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {Math.min(...attempts.map(a => a.similarity_score || a.score || 0)).toFixed(4)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VerificationAttemptHistory;
