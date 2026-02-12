import React, { useState } from 'react';

function AdminDashboard() {
  const [searchPhone, setSearchPhone] = useState('');

  // Mock transaction logs
  const mockLogs = [
    { id: 1, timestamp: '2024-11-24 14:22:18', phone: '+1 (555) ••• ••89', type: 'VERIFY', score: 0.962, latency: 342, status: 'SUCCESS' },
    { id: 2, timestamp: '2024-11-24 14:21:45', phone: '+1 (555) ••• ••12', type: 'ENROLL', score: null, latency: 812, status: 'SUCCESS' },
    { id: 3, timestamp: '2024-11-24 14:19:02', phone: '+1 (555) ••• ••44', type: 'VERIFY', score: 0.428, latency: 298, status: 'LOW_SCORE' },
    { id: 4, timestamp: '2024-11-24 14:18:33', phone: '+1 (555) ••• ••77', type: 'VERIFY', score: 0.914, latency: 315, status: 'SUCCESS' },
    { id: 5, timestamp: '2024-11-24 14:15:10', phone: '+1 (555) ••• ••05', type: 'VERIFY', score: 0.988, latency: 322, status: 'SUCCESS' },
  ];

  const stats = [
    { label: 'Enrollments (24h)', value: '1,482', icon: 'person_add', color: 'primary' },
    { label: 'Verifications (24h)', value: '8,921', icon: 'verified_user', color: 'primary' },
    { label: 'Avg. Similarity', value: '0.942', icon: 'analytics', color: 'primary' },
    { label: 'Failures (24h)', value: '24', icon: 'report_problem', color: 'red' },
  ];

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark flex flex-col">
      {/* Top Navigation */}
      <nav className="border-b border-primary/10 bg-white dark:bg-slate-900 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="bg-primary p-1.5 rounded-lg shadow-sm">
            <span className="material-icons text-white text-xl">fingerprint</span>
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight">
              Voice<span className="text-primary text-sm font-medium ml-1">ADMIN</span>
            </h1>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              <span className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">System Live</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm font-medium border-slate-200 dark:border-slate-800 px-6">
          <div className="flex flex-col items-end">
            <span className="text-slate-500 text-[10px] uppercase tracking-widest">Global Status</span>
            <span className="text-primary">All Systems Operational</span>
          </div>
        </div>
      </nav>

      <div className="flex flex-1 overflow-hidden">
        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Quick Stats Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {stats.map((stat, i) => (
              <div key={i} className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center gap-4">
                <div className={`p-3 bg-${stat.color === 'red' ? 'red' : 'primary'}/10 rounded-lg`}>
                  <span className={`material-icons text-${stat.color === 'red' ? 'red' : 'primary'}-500`}>
                    {stat.icon}
                  </span>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase font-bold tracking-tight">{stat.label}</p>
                  <p className="text-xl font-bold">{stat.value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Logs Table */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            {/* Table Header */}
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <h2 className="font-bold">Transaction Logs</h2>
                <span className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-500 font-medium">
                  {mockLogs.length} Total
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <span className="material-icons absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">search</span>
                  <input
                    type="text"
                    placeholder="Search phone number..."
                    value={searchPhone}
                    onChange={(e) => setSearchPhone(e.target.value)}
                    className="pl-9 pr-4 py-1.5 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-primary focus:border-primary w-64"
                  />
                </div>
                <button className="flex items-center gap-2 px-3 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                  <span className="material-icons text-sm">filter_list</span>
                  Filters
                </button>
                <button className="flex items-center gap-2 px-3 py-1.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
                  <span className="material-icons text-sm">file_download</span>
                  Export
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-800/50 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-100 dark:border-slate-800">
                    <th className="px-6 py-3">Timestamp</th>
                    <th className="px-6 py-3">Phone Number</th>
                    <th className="px-6 py-3">Type</th>
                    <th className="px-6 py-3">Similarity Score</th>
                    <th className="px-6 py-3">Latency</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
                  {mockLogs.map((log) => (
                    <tr key={log.id} className={`hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors ${log.status === 'LOW_SCORE' ? 'bg-red-50/20 dark:bg-red-900/10' : ''}`}>
                      <td className="px-6 py-4 font-mono text-xs whitespace-nowrap">{log.timestamp}</td>
                      <td className="px-6 py-4 font-medium">{log.phone}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          log.type === 'VERIFY' 
                            ? 'bg-primary/10 text-primary' 
                            : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                        }`}>
                          {log.type}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {log.score ? (
                          <div className="flex items-center gap-2">
                            <div className="w-12 bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                              <div 
                                className={`h-full ${log.score > 0.75 ? 'bg-primary' : 'bg-red-500'}`}
                                style={{ width: `${log.score * 100}%` }}
                              ></div>
                            </div>
                            <span className="font-mono text-xs font-bold">{log.score.toFixed(3)}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400">N/A</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-500 font-mono text-xs">{log.latency}ms</td>
                      <td className="px-6 py-4">
                        <div className={`flex items-center gap-1.5 font-bold text-xs uppercase ${
                          log.status === 'SUCCESS' 
                            ? 'text-emerald-600 dark:text-emerald-400' 
                            : 'text-red-600 dark:text-red-400'
                        }`}>
                          <span className="material-icons text-sm">
                            {log.status === 'SUCCESS' ? 'check_circle' : 'cancel'}
                          </span>
                          {log.status === 'SUCCESS' ? 'Success' : 'Low Score'}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="text-primary hover:underline text-xs font-bold">VIEW JSON</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="p-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Showing <span className="font-bold text-slate-900 dark:text-slate-200">1-{mockLogs.length}</span> of {mockLogs.length} logs
              </p>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800" disabled>
                  <span className="material-icons text-sm">chevron_left</span>
                </button>
                <button className="px-3 py-1 bg-primary text-white text-xs font-bold rounded">1</button>
                <button className="px-3 py-1 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-bold rounded">2</button>
                <button className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
                  <span className="material-icons text-sm">chevron_right</span>
                </button>
              </div>
            </div>
          </div>

          {/* Analytics Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-6">
            {/* Volume Distribution */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
              <h3 className="text-sm font-bold mb-4 flex items-center gap-2">
                <span className="material-icons text-primary text-lg">insights</span>
                Volume Distribution (Last 12h)
              </h3>
              <div className="h-48 flex items-end justify-between gap-1 px-2">
                {[30, 45, 38, 60, 75, 55, 95, 85, 40, 35, 25, 15].map((h, i) => (
                  <div key={i} className="w-full bg-primary/20 rounded-t-sm relative group" style={{ height: `${(h / 95) * 100}%` }}>
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-[10px] py-0.5 px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                      {Math.round((h / 95) * 100 * 2.5)} req
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-2 text-[10px] text-slate-400 font-bold uppercase">
                <span>08:00 AM</span>
                <span>02:00 PM</span>
                <span>08:00 PM</span>
              </div>
            </div>

            {/* Recent Errors */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
              <h3 className="text-sm font-bold mb-4 flex items-center gap-2">
                <span className="material-icons text-primary text-lg">history</span>
                Recent API Errors
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-900/30">
                  <span className="material-icons text-red-500 text-lg">error_outline</span>
                  <div className="flex-1">
                    <p className="text-xs font-bold text-red-700 dark:text-red-400">422 Unprocessable Entity</p>
                    <p className="text-[10px] text-red-600/70 dark:text-red-400/70 truncate">
                      /enroll: Missing required 'audio_payload' field in JSON body
                    </p>
                  </div>
                  <span className="text-[10px] text-red-500/50 font-mono whitespace-nowrap">2m ago</span>
                </div>
                <div className="flex items-center gap-3 p-3 bg-orange-50 dark:bg-orange-900/10 rounded-lg border border-orange-100 dark:border-orange-900/30">
                  <span className="material-icons text-orange-500 text-lg">timer</span>
                  <div className="flex-1">
                    <p className="text-xs font-bold text-orange-700 dark:text-orange-400">504 Gateway Timeout</p>
                    <p className="text-[10px] text-orange-600/70 dark:text-orange-400/70 truncate">
                      /verify: Voice template generation exceeded 1500ms
                    </p>
                  </div>
                  <span className="text-[10px] text-orange-500/50 font-mono whitespace-nowrap">14m ago</span>
                </div>
                <div className="flex items-center justify-center pt-2">
                  <button className="text-[10px] font-bold text-primary uppercase tracking-wider hover:underline">
                    View All Critical Alerts
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default AdminDashboard;
