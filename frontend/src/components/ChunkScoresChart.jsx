import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';

/**
 * Displays chunk verification scores as a bar chart
 * Shows match percentages for each chunk processed during verification
 */
function ChunkScoresChart({ chunks = [], threshold = 0.75 }) {
  if (!chunks || chunks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 py-12">
        <div className="text-center">
          <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="material-icons text-3xl text-slate-400">bar_chart</span>
          </div>
          <p className="text-slate-600 dark:text-slate-400 font-medium text-lg">No chunk data available</p>
          <p className="text-slate-400 text-sm mt-2">Chunk scores will appear after processing</p>
        </div>
      </div>
    );
  }

  // Transform chunks data for chart
  const chartData = chunks.map((chunk, index) => ({
    name: `Chunk ${index + 1}`,
    score: typeof chunk.similarity === 'number' ? chunk.similarity * 100 : parseFloat(chunk.similarity) || 0,
    chunkIndex: index + 1,
    raw: chunk,
  }));

  const thresholdPercent = threshold * 100;

  // Determine bar color based on threshold
  const getBarColor = (percentage) => {
    if (percentage >= thresholdPercent) {
      return '#10b981'; // emerald-500
    } else if (percentage >= thresholdPercent - 10) {
      return '#f59e0b'; // amber-500
    }
    return '#ef4444'; // red-500
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 dark:bg-slate-950 text-white p-3 rounded-lg border border-slate-700 shadow-lg">
          <p className="font-semibold">{data.name}</p>
          <p className="text-emerald-400 font-bold text-lg">
            {typeof data.score === 'number' ? data.score.toFixed(1) : data.score}%
          </p>
          <p className="text-xs text-slate-400 mt-1">
            {data.score >= thresholdPercent ? '✓ Above threshold' : '✗ Below threshold'}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full space-y-4">
      {/* Chart Container */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <div className="mb-4">
          <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
            Chunk Verification Scores
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Match percentage for each audio chunk processed
          </p>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="currentColor"
              opacity={0.1}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: 'currentColor', fontSize: 12 }}
              axisLine={{ stroke: 'currentColor', opacity: 0.2 }}
            />
            <YAxis
              label={{ value: 'Match Score (%)', angle: -90, position: 'insideLeft' }}
              domain={[0, 100]}
              tick={{ fill: 'currentColor', fontSize: 12 }}
              axisLine={{ stroke: 'currentColor', opacity: 0.2 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="score" fill="#8884d8" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Threshold Reference Line Info */}
        <div className="mt-4 flex items-center gap-2 text-sm">
          <div className="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-600" />
          <span className="text-slate-600 dark:text-slate-400">
            Threshold: <span className="font-semibold">{thresholdPercent.toFixed(1)}%</span>
          </span>
        </div>
      </div>

      {/* Chunk Details Table */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
            Detailed Chunk Results
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800/50">
                <th className="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">Chunk</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">Match Score</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700 dark:text-slate-300">Status</th>
              </tr>
            </thead>
            <tbody>
              {chartData.map((chunk, index) => (
                <tr
                  key={index}
                  className="border-b border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800/30 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">
                    {chunk.name}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-slate-300 dark:bg-slate-600 rounded-full overflow-hidden">
                        <div
                          className="h-full transition-all"
                          style={{
                            width: `${Math.min(chunk.score, 100)}%`,
                            backgroundColor: getBarColor(chunk.score),
                          }}
                        />
                      </div>
                      <span className="font-bold text-slate-800 dark:text-slate-200 w-12 text-right">
                        {chunk.score.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-bold ${
                        chunk.score >= thresholdPercent
                          ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                          : chunk.score >= thresholdPercent - 10
                          ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                          : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                      }`}
                    >
                      <span className="material-icons text-sm">
                        {chunk.score >= thresholdPercent ? 'check_circle' : 'cancel'}
                      </span>
                      {chunk.score >= thresholdPercent ? 'Match' : 'No Match'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Average Score
          </p>
          <p className="text-2xl font-bold text-slate-800 dark:text-white">
            {(chartData.reduce((sum, c) => sum + c.score, 0) / chartData.length).toFixed(1)}%
          </p>
        </div>
        <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Highest Score
          </p>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {Math.max(...chartData.map(c => c.score)).toFixed(1)}%
          </p>
        </div>
        <div className="p-4 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Chunks Passed
          </p>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {chartData.filter(c => c.score >= thresholdPercent).length} / {chartData.length}
          </p>
        </div>
      </div>
    </div>
  );
}

export default ChunkScoresChart;
