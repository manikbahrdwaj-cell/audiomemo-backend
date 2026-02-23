# Quick Startup Guide - Voice Biometric

## Prerequisites Check

### 1. Backend Server (Port 8000)
```powershell
# Start the backend server
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Development Server (Port 3000)
```powershell
# In a new terminal, start the frontend
cd frontend
npm start
```

### 3. MongoDB (Default: Port 27017)
Ensure MongoDB is running locally or configured in `.env`

---

## Verify Setup

### Check Backend
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET
```
Expected: `{"status": "ok", "message": "Voice Biometric API is running"}`

### Check Frontend
Navigate to: `http://localhost:3000`

### Check WebSocket Connection
Open browser DevTools (F12) → Console
Try clicking "Initialize Verification" with a phone number
You should see connection logs in the console

---

## Common Issues & Fixes

### ❌ WebSocket Connection Timeout
**Cause**: Backend not running or unreachable

**Fix**:
1. Verify backend is running on port 8000
2. Check `.env` or backend configuration
3. Frontend `.env.local` should have: `REACT_APP_WS_URL=ws://localhost:8000`

### ❌ Backend on Different Port
**Fix**: Update frontend `.env.local`:
```
REACT_APP_API_URL=http://localhost:<YOUR_PORT>
REACT_APP_WS_URL=ws://localhost:<YOUR_PORT>
```

### ❌ MongoDB Connection Error
**Fix**: 
1. Start MongoDB locally: `mongod`
2. Or update `.env` with MongoDB URI

---

## Quick Test Commands

### Terminal 1: Start Backend
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Start Frontend
```powershell
cd frontend
npm start
```

### Terminal 3: Optional - Test Backend Health
```powershell
# Check if backend is running
curl http://localhost:8000/health

# Or in PowerShell:
Invoke-WebRequest -Uri "http://localhost:8000/health"
```

Once both are running, you should be able to click "Initialize Verification" without timeout errors!
