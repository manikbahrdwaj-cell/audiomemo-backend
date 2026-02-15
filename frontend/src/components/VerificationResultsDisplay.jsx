import React, { useState } from 'react';
import VerificationMetrics from './VerificationMetrics';
import VerificationConfidence from './VerificationConfidence';
import VerificationAttemptHistory from './VerificationAttemptHistory';

/**
 * Comprehensive display for verification results
 * Shows detailed session info, metrics, confidence scores, and attempt history
 */
function VerificationResultsDisplay({ result, threshold, verificationError }) {
  const [activeTab, setActiveTab] = useState('overview');

  if (!result && !verificationError) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12">
        <div className="text-center">
          <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="material-icons text-3xl text-slate-400">assessment</span>
          </div>
          <p className="text-slate-600 dark:text-slate-400 font-medium text-lg">No results yet</p>
          <p className="text-slate-400 text-sm mt-2">Complete a verification to see detailed analysis</p>
        </div>
      </div>
    );
  }

  if (!result && verificationError) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12">
        <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl w-full max-w-md">
          <div className="flex gap-3">
            <span className="material-icons text-red-600 dark:text-red-400 flex-shrink-0">error</span>
            <div>
              <p className="font-semibold text-red-700 dark:text-red-300">Verification Failed</p>
              <p className="text-sm text-red-600 dark:text-red-400 mt-2">{verificationError}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isMatch = result.isMatch;
  const score = result.score || 0;
  const confidence = (score * 100).toFixed(0);

  return (
    <div className="flex flex-col h-full">
      {/* Header with Status Badge */}
      <div className="flex justify-between items-start mb-6 pb-6 border-b border-slate-200 dark:border-slate-700">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Verification Results</h2>
          <p className="text-sm text-slate-500 mt-1">Detailed analysis of identity verification</p>
        </div>
        <div
          className={`px-4 py-2 rounded-full text-sm font-bold flex items-center gap-2 shadow-lg ${
            isMatch
              ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
              : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
          }`}
        >
          <span className="material-icons text-lg">{isMatch ? 'verified_user' : 'gpp_bad'}</span>
          {isMatch ? 'VERIFIED' : 'NOT VERIFIED'}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200 dark:border-slate-700">
        {[
          { id: 'overview', label: 'Overview', icon: 'dashboard' },
          { id: 'metrics', label: 'Metrics', icon: 'analytics' },
          { id: 'confidence', label: 'Confidence', icon: 'trending_up' },
          { id: 'history', label: 'Attempts', icon: 'history' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 flex items-center gap-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <span className="material-icons text-base">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-grow overflow-y-auto">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6 pb-6">
            {/* Primary Score Display */}
            <div className="grid grid-cols-2 gap-6">
              {/* Score Circle */}
              <div className="flex flex-col items-center justify-center">
                <div className="relative w-48 h-48 flex items-center justify-center mb-4">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                    <circle
                      className="text-slate-200 dark:text-slate-700"
                      cx="50"
                      cy="50"
                      fill="none"
                      r="45"
                      stroke="currentColor"
                      strokeWidth="6"
                    />
                    <circle
                      className={isMatch ? 'text-emerald-500' : 'text-red-500'}
                      cx="50"
                      cy="50"
                      fill="none"
                      r="45"
                      stroke="currentColor"
                      strokeDasharray="282.7"
                      strokeDashoffset={282.7 * (1 - score)}
                      strokeLinecap="round"
                      strokeWidth="6"
                      style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <div className="text-4xl font-black tabular-nums">
                      <span className={isMatch ? 'text-emerald-500' : 'text-red-500'}>{confidence}</span>
                      <span className="text-xl text-slate-400">%</span>
                    </div>
                    <div className="text-xs font-semibold text-slate-500 mt-1 uppercase tracking-wider">
                      Match Score
                    </div>
                  </div>
                </div>
                <div className="text-center mt-4">
                  <p className={`text-sm font-bold flex items-center justify-center gap-1 ${
                    isMatch ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    <span className="material-icons text-base">
                      {isMatch ? 'check_circle' : 'cancel'}
                    </span>
                    {isMatch ? 'Identity Verified' : 'Identity Not Verified'}
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    {isMatch
                      ? 'Voice pattern matches enrolled identity'
                      : 'Voice pattern does not match enrolled identity'}
                  </p>
                </div>
              </div>

              {/* Key Information */}
              <div className="space-y-4">
                {/* Phone Number */}
                <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                    Target Identity
                  </p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white">{result.phoneNumber}</p>
                  <p className="text-xs text-slate-500 mt-1">Phone Number</p>
                </div>

                {/* Threshold Comparison */}
                <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    Threshold Analysis
                  </p>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-600 dark:text-slate-300">Score</span>
                      <span className="font-bold text-slate-800 dark:text-white">
                        {score.toFixed(4)}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-300 dark:bg-slate-600 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          isMatch ? 'bg-emerald-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(score * 100, 100)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 mt-2">
                      <span>Threshold: {threshold.toFixed(2)}</span>
                      <span className={isMatch ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                        {isMatch ? 'ABOVE' : 'BELOW'} THRESHOLD
                      </span>
                    </div>
                  </div>
                </div>

                {/* Status Info */}
                <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    Session Information
                  </p>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-600 dark:text-slate-300">Status</span>
                      <span className={`text-xs font-bold px-2 py-1 rounded ${
                        isMatch
                          ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                          : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                      }`}>
                        {isMatch ? 'VERIFIED' : 'REJECTED'}
                      </span>
                    </div>
                    {result.timestamp && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-600 dark:text-slate-300">Timestamp</span>
                        <span className="text-xs font-mono text-slate-600 dark:text-slate-400">
                          {new Date(result.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Error Message */}
            {verificationError && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex gap-3">
                <span className="material-icons text-red-600 dark:text-red-400 flex-shrink-0">error</span>
                <div className="flex-grow">
                  <p className="text-sm font-semibold text-red-700 dark:text-red-300">Error</p>
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1">{verificationError}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Metrics Tab */}
        {activeTab === 'metrics' && (
          <VerificationMetrics result={result} threshold={threshold} />
        )}

        {/* Confidence Tab */}
        {activeTab === 'confidence' && (
          <VerificationConfidence result={result} score={score} />
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <VerificationAttemptHistory attempts={result.attempts} />
        )}
      </div>
    </div>
  );
}

export default VerificationResultsDisplay;
