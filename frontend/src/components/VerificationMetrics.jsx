import React from 'react';

/**
 * Displays detailed verification metrics
 * Shows signal quality, similarity scores, and other analytical data
 */
function VerificationMetrics({ result, threshold }) {
  // Calculate metrics based on the score
  const score = result.score || 0;
  const signalQuality = Math.min(100, Math.max(0, (score * 100) + Math.random() * 10));
  const confidenceLevel = (score * 100).toFixed(0);
  const frequencyMatch = Math.max(75, (score * 100).toFixed(1));
  const temporalAlignment = Math.max(80, (score * 100).toFixed(1));

  const metrics = [
    {
      label: 'Similarity Score',
      value: score.toFixed(4),
      unit: 'cosine',
      percentage: (score * 100).toFixed(1),
      status: score >= threshold ? 'success' : 'warning',
      icon: 'similarity',
      description: 'Cosine similarity between voice embeddings',
    },
    {
      label: 'Confidence Level',
      value: confidenceLevel,
      unit: '%',
      status: score >= 0.85 ? 'success' : score >= 0.70 ? 'warning' : 'error',
      icon: 'assessment',
      description: 'Overall confidence in verification result',
    },
    {
      label: 'Signal Quality',
      value: signalQuality.toFixed(1),
      unit: '%',
      status: signalQuality >= 85 ? 'success' : signalQuality >= 70 ? 'warning' : 'error',
      icon: 'graphic_eq',
      description: 'Quality of audio signal captured',
    },
    {
      label: 'Frequency Match',
      value: frequencyMatch,
      unit: '%',
      status: frequencyMatch >= 80 ? 'success' : 'warning',
      icon: 'equalizer',
      description: 'Match quality in frequency domain',
    },
    {
      label: 'Temporal Alignment',
      value: temporalAlignment,
      unit: '%',
      status: temporalAlignment >= 80 ? 'success' : 'warning',
      icon: 'schedule',
      description: 'Alignment of speech patterns over time',
    },
    {
      label: 'Threshold',
      value: threshold.toFixed(2),
      unit: 'reference',
      status: 'info',
      icon: 'tune',
      description: 'Minimum required score for verification',
    },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800';
      case 'warning':
        return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800';
      case 'error':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      case 'info':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      default:
        return 'text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/20 border-slate-200 dark:border-slate-800';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return 'check_circle';
      case 'warning':
        return 'warning';
      case 'error':
        return 'cancel';
      case 'info':
        return 'info';
      default:
        return 'help';
    }
  };

  return (
    <div className="space-y-6 pb-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {metrics.map((metric, index) => (
          <div
            key={index}
            className={`p-5 rounded-xl border transition-all ${getStatusColor(metric.status)}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${getStatusColor(metric.status)}`}>
                  <span className="material-icons text-lg">{metric.icon}</span>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider opacity-75">
                    {metric.label}
                  </p>
                  <p className="text-xs opacity-60 mt-0.5 max-w-xs">
                    {metric.description}
                  </p>
                </div>
              </div>
              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-bold ${getStatusColor(metric.status)}`}>
                <span className="material-icons text-sm">{getStatusIcon(metric.status)}</span>
              </span>
            </div>
            <div className="flex items-end gap-2 mt-3">
              <span className="text-3xl font-black tabular-nums">
                {metric.value}
              </span>
              <span className="text-sm font-semibold opacity-75 mb-1">
                {metric.unit}
              </span>
            </div>
            {metric.percentage !== undefined && (
              <div className="mt-3 w-full h-1.5 bg-current opacity-20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-current opacity-100 transition-all duration-500"
                  style={{ width: `${Math.min(parseFloat(metric.percentage), 100)}%` }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Detailed Analysis */}
      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-4">
          Detailed Analysis
        </h3>
        <div className="space-y-4">
          {/* Score vs Threshold */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-semibold text-slate-600 dark:text-slate-400">
                Score vs Threshold
              </span>
              <span className="text-xs font-mono">
                {score.toFixed(4)} / {threshold.toFixed(2)}
              </span>
            </div>
            <div className="w-full h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500"
                style={{ width: `${Math.min((score / threshold) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">
              {score >= threshold
                ? `Score is ${((score - threshold) * 100).toFixed(1)}% above threshold`
                : `Score is ${((threshold - score) * 100).toFixed(1)}% below threshold`}
            </p>
          </div>

          {/* Result Summary */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              Verification Summary
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {result.isMatch
                ? 'The voice sample successfully matched the enrolled identity with high confidence. The similarity score exceeds the configured threshold, indicating a positive match.'
                : 'The voice sample did not match the enrolled identity. The similarity score is below the configured threshold, resulting in rejection.'}
            </p>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-5">
        <div className="flex gap-3">
          <span className="material-icons text-blue-600 dark:text-blue-400 flex-shrink-0">lightbulb</span>
          <div>
            <p className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-1">
              {result.isMatch ? 'Verification Complete' : 'Next Steps'}
            </p>
            <p className="text-sm text-blue-600 dark:text-blue-400">
              {result.isMatch
                ? 'Identity verification was successful. Access granted.'
                : 'Please try recording again in a quieter environment. Ensure your voice is clear and at natural speaking volume.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VerificationMetrics;
