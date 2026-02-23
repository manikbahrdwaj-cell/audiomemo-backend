# Fix for WebSocket Connection Timeout Error

## Problem Identified
When clicking "Initialize Verification", you were getting:
- ❌ Connection timeout error
- ❌ WebSocket error  
- ❌ "Connection failed" message

### Root Cause
Your frontend (running on port 3000) was trying to connect to the WebSocket endpoint on **the same host** (port 3000), but your backend is running on **port 8000**. The React dev server doesn't have WebSocket endpoints, so the connection would time out after 5 seconds.

---

## What I Fixed

### 1. **Created Frontend Environment Configuration** (`frontend/.env.local`)
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```
This tells the frontend to use the backend server (port 8000) instead of its own dev server.

### 2. **Updated WebSocket Connection Logic** (`frontend/src/services/realtimeVerificationService.js`)
- Now uses `REACT_APP_WS_URL` environment variable
- Falls back to auto-detection if env var is not set
- Increased connection timeout from 5s to 10s
- Added better error messages showing the backend URL being attempted

### 3. **Created Startup Guide** (`STARTUP_GUIDE.md`)
Quick reference for starting both servers

### 4. **Created PowerShell Helper Script** (`start.ps1`)
Easy way to check prerequisites and start servers:
```powershell
# Check everything is ready
.\start.ps1 -Check

# Start backend in Terminal 1
.\start.ps1 -Backend

# Start frontend in Terminal 2  
.\start.ps1 -Frontend
```

---

## How to Use the Fix

### Option 1: Manual Start (Recommended)

**Terminal 1 - Backend:**
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm start
```

**Terminal 3 - (Optional) MongoDB:**
```powershell
mongod
```

### Option 2: Using the Script

**Terminal 1:**
```powershell
.\start.ps1 -Backend
```

**Terminal 2:**
```powershell
.\start.ps1 -Frontend
```

**Check Prerequisites:**
```powershell
.\start.ps1 -Check
```

---

## Expected Behavior After Fix

✅ Frontend opens at: `http://localhost:3000`

✅ Click "Initialize Verification" → Connection succeeds within 1-2 seconds

✅ Browser console shows: `[RealTimeVerification] Connected for phone: +1-555-0000`

✅ Can now record and verify voice

---

## Configuration Details

### Frontend Configuration (`.env.local`)
| Variable | Purpose | Default |
|----------|---------|---------|
| `REACT_APP_API_URL` | REST API endpoint | `http://localhost:8000` |
| `REACT_APP_WS_URL` | WebSocket endpoint | Auto-detect from host |

### Backend Configuration (`.env`)
| Variable | Purpose | Default |
|----------|---------|---------|
| `MONGODB_URI` | Database connection | `mongodb://localhost:27017` |

### Port Mapping
| Service | Port | URL |
|---------|------|-----|
| Frontend (React) | 3000 | `http://localhost:3000` |
| Backend (FastAPI) | 8000 | `http://localhost:8000` |
| MongoDB | 27017 | `mongodb://localhost:27017` |
| WebSocket | 8000 | `ws://localhost:8000` |

---

## Troubleshooting

### Still getting timeout?

1. **Verify backend is running:**
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/health"
   ```
   Should return: `{"status": "ok"}`

2. **Check MongoDB is running:**
   ```powershell
   mongod --version
   # Start it if needed:
   mongod
   ```

3. **Check frontend sees correct URL:**
   - Open browser DevTools (F12)
   - Console
   - Look for: `[RealTimeVerification] Connecting to ws://localhost:8000/ws/verify/...`

4. **Clear cache and restart:**
   ```powershell
   # Frontend
   npm cache clean --force
   npm start
   ```

### Backend on different port?

Update `frontend/.env.local`:
```env
REACT_APP_WS_URL=ws://localhost:YOUR_PORT
```

### Remote backend?

Update `frontend/.env.local`:
```env
REACT_APP_WS_URL=ws://your-server.com:8000
# For production with HTTPS:
REACT_APP_WS_URL=wss://your-server.com:8000
```

---

## Files Modified

1. ✅ `frontend/.env.local` - Created with backend URL config
2. ✅ `frontend/src/services/realtimeVerificationService.js` - Updated to use env config
3. ✅ `STARTUP_GUIDE.md` - Created
4. ✅ `start.ps1` - Created

---

## Next Steps

1. Start both backend and frontend services
2. Navigate to `http://localhost:3000` 
3. Try "Initialize Verification" again
4. Connection should work now! ✅

If you still have issues, check the browser console (F12) for detailed error messages.
