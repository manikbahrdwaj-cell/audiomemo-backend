import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import EnrollmentPage from './components/EnrollmentPage';
import VerificationPageRealtime from './components/VerificationPageRealtime';
import './App.css';
import './styles/verification-results.css';

function Navigation() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-8">
            <h1 className="text-xl font-bold text-primary">Voice Biometric</h1>
            <div className="flex gap-1">
              <Link
                to="/"
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  isActive('/') 
                    ? 'bg-primary text-white' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                Enroll
              </Link>
              <Link
                to="/verify"
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  isActive('/verify') 
                    ? 'bg-primary text-white' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                Verify
              </Link>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <Navigation />
      <Routes>
        <Route path="/" element={<EnrollmentPage />} />
        <Route path="/verify" element={<VerificationPageRealtime />} />
      </Routes>
    </Router>
  );
}

export default App;
