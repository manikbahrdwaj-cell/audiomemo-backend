import React, { useState } from 'react';
import { exportResultAsJSON, exportResultAsCSV, generateVerificationSummary } from '../utils/verificationUtils';

/**
 * Component for exporting verification results
 * Provides options to download or copy results
 */
function VerificationResultExport({ result }) {
  const [exportFormat, setExportFormat] = useState('json');
  const [copied, setCopied] = useState(false);

  if (!result) return null;

  const handleExportJSON = () => {
    const json = exportResultAsJSON(result);
    downloadFile(json, 'verification-result.json', 'application/json');
  };

  const handleExportCSV = () => {
    const csv = exportResultAsCSV(result);
    downloadFile(csv, 'verification-result.csv', 'text/csv');
  };

  const handleCopySummary = () => {
    const summary = generateVerificationSummary(result);
    navigator.clipboard.writeText(summary).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleCopyJSON = () => {
    const json = exportResultAsJSON(result);
    navigator.clipboard.writeText(json).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const downloadFile = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 space-y-4">
      <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
        Export Results
      </h3>

      {/* Export Summary */}
      <div className="space-y-3">
        <button
          onClick={handleCopySummary}
          className="w-full flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="material-icons text-blue-600 dark:text-blue-400">description</span>
            <div className="text-left">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Summary</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Copy text summary</p>
            </div>
          </div>
          <span className="material-icons text-slate-400">
            {copied ? 'check' : 'content_copy'}
          </span>
        </button>

        {/* Export JSON */}
        <div className="flex gap-2">
          <button
            onClick={handleCopyJSON}
            className="flex-1 flex items-center justify-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800 transition-colors text-blue-700 dark:text-blue-300 font-semibold"
          >
            <span className="material-icons text-base">content_copy</span>
            Copy JSON
          </button>
          <button
            onClick={handleExportJSON}
            className="flex-1 flex items-center justify-center gap-2 p-3 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors text-slate-700 dark:text-slate-300 font-semibold"
          >
            <span className="material-icons text-base">download</span>
            JSON File
          </button>
        </div>

        {/* Export CSV */}
        <button
          onClick={handleExportCSV}
          className="w-full flex items-center justify-center gap-2 p-3 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors text-slate-700 dark:text-slate-300 font-semibold"
        >
          <span className="material-icons text-base">table_chart</span>
          Download CSV
        </button>
      </div>

      {/* Copy Feedback */}
      {copied && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-700 dark:text-emerald-300 text-sm">
          Copied to clipboard!
        </div>
      )}
    </div>
  );
}

export default VerificationResultExport;
