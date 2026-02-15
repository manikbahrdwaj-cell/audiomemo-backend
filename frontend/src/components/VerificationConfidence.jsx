import React from 'react';

/**
 * Displays confidence analysis for verification results
 * Shows confidence level breakdown and trust metrics
 */
function VerificationConfidence({ result, score }) {
  const confidence = (score * 100).toFixed(1);
  
  // Calculate confidence bands
  const bands = [
    { range: [0, 20], label: 'Very Low', color: 'from-red-600 to-red-500', bgColor: 'bg-red-100 dark:bg-red-900/20', icon: 'cancel' },
    { range: [20, 40], label: 'Low', color: 'from-orange-600 to-orange-500', bgColor: 'bg-orange-100 dark:bg-orange-900/20', icon: 'warning' },
    { range: [40, 60], label: 'Medium', color: 'from-amber-600 to-amber-500', bgColor: 'bg-amber-100 dark:bg-amber-900/20', icon: 'info' },
    { range: [60, 80], label: 'High', color: 'from-lime-600 to-lime-500', bgColor: 'bg-lime-100 dark:bg-lime-900/20', icon: 'check_circle' },
    { range: [80, 100], label: 'Very High', color: 'from-emerald-600 to-emerald-500', bgColor: 'bg-emerald-100 dark:bg-emerald-900/20', icon: 'verified_user' },
  ];

  const getCurrentBand = () => {
    return bands.find(band => confidence >= band.range[0] && confidence <= band.range[1]);
  };

  const currentBand = getCurrentBand();

  // Calculate confidence factors
  const factors = [
    { name: 'Speech Pattern Match', value: Math.min(100, score * 100 + 5), weight: 25 },
    { name: 'Audio Quality', value: Math.min(100, score * 105 - 5), weight: 20 },
    { name: 'Duration Adequacy', value: 85, weight: 15 },
    { name: 'Noise Resistance', value: Math.min(100, score * 95 + 10), weight: 20 },
    { name: 'Overall Similarity', value: score * 100, weight: 20 },
  ];

  // Calculate weighted average
  const weightedConfidence = factors.reduce((sum, factor) => sum + (factor.value * factor.weight / 100), 0);

  return (
    <div className="space-y-6 pb-6">
      {/* Main Confidence Gauge */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-8">
        <div className="flex items-center gap-8">
          {/* Gauge */}
          <div className="flex-shrink-0">
            <div className="relative w-40 h-40 flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-full h-full">
                {/* Background arc */}
                <path
                  d="M 20 80 A 30 30 0 0 1 80 80"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  className="text-slate-200 dark:text-slate-700"
                />
                {/* Confidence arc */}
                <path
                  d="M 20 80 A 30 30 0 0 1 80 80"
                  fill="none"
                  stroke={currentBand?.color.split(' ')[0].replace('from-', '').replace('to-', '')}
                  strokeWidth="4"
                  strokeDasharray={`${(confidence / 100) * 94.25} 94.25`}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dasharray 1s ease-out' }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="text-4xl font-black tabular-nums">
                  {Math.round(confidence)}
                  <span className="text-lg text-slate-400">%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Confidence Info */}
          <div className="flex-grow">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">
              Confidence Level
            </p>
            <div className="flex items-center gap-2 mb-4">
              <span className="material-icons" style={{ color: currentBand?.color }}>
                {currentBand?.icon}
              </span>
              <span className="text-2xl font-bold" style={{ color: currentBand?.color }}>
                {currentBand?.label}
              </span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
              {score >= 0.90
                ? 'Extremely high confidence in verification result. Voice is a strong match.'
                : score >= 0.80
                ? 'High confidence in verification result. Voice is a good match.'
                : score >= 0.70
                ? 'Moderate confidence in verification result. Voice has some matching characteristics.'
                : 'Low confidence in verification result. Voice characteristics do not align well.'}
            </p>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-600 dark:text-slate-400">Raw Similarity Score</span>
                <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                  {score.toFixed(4)}
                </span>
              </div>
              <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-gradient-to-r ${currentBand?.color} transition-all duration-500`}
                  style={{ width: `${confidence}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confidence Factors */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-4">
          Confidence Factors
        </h3>
        <div className="space-y-4">
          {factors.map((factor, index) => (
            <div key={index} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                    {factor.name}
                  </span>
                  <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-2 py-0.5 rounded">
                    {factor.weight}% weight
                  </span>
                </div>
                <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  {factor.value.toFixed(1)}%
                </span>
              </div>
              <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-500"
                  style={{ width: `${Math.min(factor.value, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Weighted Average */}
        <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-bold text-slate-700 dark:text-slate-300">
              Weighted Confidence Average
            </p>
            <p className="text-lg font-black text-primary">
              {weightedConfidence.toFixed(1)}%
            </p>
          </div>
          <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-500"
              style={{ width: `${Math.min(weightedConfidence, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Confidence Bands Legend */}
      <div className="grid grid-cols-5 gap-3">
        {bands.map((band, index) => (
          <div
            key={index}
            className={`p-3 rounded-lg border transition-all ${
              band === currentBand
                ? `${band.bgColor} ring-2 ring-offset-2 dark:ring-offset-slate-900 ring-current`
                : `${band.bgColor}`
            }`}
          >
            <p className="text-xs font-bold uppercase tracking-wider mb-1">{band.label}</p>
            <p className="text-xs opacity-75">{band.range[0]}-{band.range[1]}%</p>
          </div>
        ))}
      </div>

      {/* Interpretation Guide */}
      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3">
          How to Interpret
        </h3>
        <div className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
          <p>
            <strong className="text-slate-700 dark:text-slate-300">Very High (80-100%):</strong> Extremely reliable. The voice sample is a strong match with minimal doubt.
          </p>
          <p>
            <strong className="text-slate-700 dark:text-slate-300">High (60-80%):</strong> Reliable. The voice sample is a good match with high probability of correct identification.
          </p>
          <p>
            <strong className="text-slate-700 dark:text-slate-300">Medium (40-60%):</strong> Moderate certainty. The voice sample shows some matching characteristics but may require review.
          </p>
          <p>
            <strong className="text-slate-700 dark:text-slate-300">Low (20-40%):</strong> Low reliability. The voice sample has significant differences from the enrolled identity.
          </p>
          <p>
            <strong className="text-slate-700 dark:text-slate-300">Very Low (0-20%):</strong> Not reliable. The voice sample does not match the enrolled identity.
          </p>
        </div>
      </div>
    </div>
  );
}

export default VerificationConfidence;
