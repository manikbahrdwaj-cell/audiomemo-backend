import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import EnrollmentPage from './components/EnrollmentPage';
import VerificationPage from './components/VerificationPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="nav">
          <div className="nav-brand">🔊 Voice Biometric</div>
          <div className="nav-links">
            <NavLink 
              to="/" 
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              end
            >
              Enrollment
            </NavLink>
            <NavLink 
              to="/verify" 
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              Verification
            </NavLink>
          </div>
        </nav>

        <main>
          <Routes>
            <Route path="/" element={<EnrollmentPage />} />
            <Route path="/verify" element={<VerificationPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
