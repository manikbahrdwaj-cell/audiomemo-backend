# Phase 3.5 Update Guide - VerificationPage Component

## Quick Start

The VerificationPage has been updated to use WebSocket for real-time voice verification with live similarity display and match tracking.

---

## New Features at a Glance

### 1. Real-Time Similarity Display
```
┌─────────────────────────────────────┐
│  Real-Time Similarity               │
│  85.3%  ██████████████░ (above threshold)  │
└─────────────────────────────────────┘
```
- Shows live match score as user speaks
- Color coded: Green (match) / Orange (no match)
- Updates in real-time during recording

### 2. Match Counter
```
┌─────────────────────┐
│  ✓ 3 Matches        │  (in header)
└─────────────────────┘
```
- Tracks successful verifications
- Visible in top-right header
- Increments automatically on successful match

### 3. Connection Quality Indicator
```
┌────────────────────┐
│ ● Online (fair)    │  (green when connected)
│ (42ms latency)     │  (orange when disconnecting)
└────────────────────┘
```
- Shows WebSocket connection status
- Displays network latency
- Quality levels: excellent, good, fair, poor

### 4. Recent Scores Log
```
┌─────────────────────────────────┐
│ RECENT ATTEMPTS                 │
│ [88%]  [76%]  [92%]  [81%]  [79%]  │
│ (green=match, red=no match)     │
└─────────────────────────────────┘
```
- Shows last 5 verification scores
- Color-coded by match status
- Visible below threshold slider

### 5. Success Rate Display
```
Footer: Success Rate: 80%
```
- Calculates: (matches / total attempts) * 100
- Updates after each verification
- Shows in action bar

---

## Component Structure

```javascript
import { useVerification, useConnectionQuality } from '../services/useWebSocket';

function VerificationPage() {
  // New WebSocket hooks
  const { verifying, recording, result, status, startVerification, startRecording, stopRecording } = useVerification(phoneNumber);
  const { latency, quality } = useConnectionQuality();
  
  // New state variables
  const [matchAttempts, setMatchAttempts] = useState(0);
  const [recentScores, setRecentScores] = useState([]);
  const [realTimeSimilarity, setRealTimeSimilarity] = useState(null);
}
```

---

## Usage Flow

### Step 1: Enter Phone Number & Check Enrollment
```
[+1 (555) 000-0000]
    ↓
[Retrieve Enrollment]
    ↓
"✓ Enrolled - You can now verify"
```

### Step 2: Record Voice
```
[🎤 Click to start]
    ↓
    Recording...
    [Real-Time Score: 89.2%]
    ⏱️ 00:05
    ↓
[Stop Recording]
```

### Step 3: View Results
```
┌──────────────────┐
│ VERIFIED ✓       │
├──────────────────┤
│ Score: 85.4%     │
│ Quality: High    │
│ Confidence: 90%  │
└──────────────────┘
```

### Step 4: Try Again or Clear
```
[New Verification] [Clear]
```

---

## State Management

```javascript
// Header - Connection Status
wsConnected && quality       // Display online/signal quality
latency                      // Show network latency

// Header - Match Counter
matchAttempts               // Show total successful matches

// Left Panel - Real-Time Score
realTimeSimilarity          // Display during recording
status.includes('processing') // Show loading state

// Left Panel - Recent Scores
recentScores               // Last 5 scores, color-coded

// Right Panel - Results
result                     // Full verification result with score
result.isMatch            // Determines badge color/text

// Action Bar - Statistics
matchAttempts / recentScores.length   // Success rate %
recordingTime             // Elapsed recording duration
```

---

## Key State Updates

### When Recording Starts
```javascript
await startVerification()  // Initialize WebSocket session
await startRecording()    // Begin audio capture
setRecordingTime(0)       // Reset timer
setRealTimeSimilarity(null) // Clear previous score
```

### Real-Time Score Updates (During Recording)
```javascript
// WebSocket event: onMessage
if (message.type === 'similarity-update') {
  setRealTimeSimilarity(message.score)  // Update live
}
```

### When Recording Completes
```javascript
await stopRecording()     // End audio capture
setStatus('processing')   // Show processing state
// Wait for verification-result event...
```

### When Verification Result Arrives
```javascript
// WebSocket event: 'message:verification-result'
setResult({
  score: 0.854,
  isMatch: true,
  ...
})
setRealTimeSimilarity(result.score) // Final score
setRecentScores([...prev, result.score].slice(-5))
if (result.isMatch) setMatchAttempts(prev => prev + 1)
```

---

## UI Elements Reference

### Color Coding

**Match Status:**
- 🟢 Green (emerald) = Match successful
- 🔴 Red = No match / Verification failed
- 🟠 Orange = Processing / Connecting

**Button States:**
- 🔵 Blue = Ready for recording
- 🔴 Red = Currently recording
- ⚫ Disabled = Verifying or no content

**Progress Bars:**
- 100% width = Score 100% match
- 80% width = Score 0.80 match
- Fills from left to right

---

## Event Flow Diagram

```
User Input
    ↓
handleRecord() / handleVerify()
    ↓
useVerification Hook Methods
    ├─ startVerification()     → Backend: Initialize session
    ├─ startRecording()        → Browser: Capture audio
    └─ stopRecording()         → Browser: Stop audio
    ↓
WebSocket Events
    ├─ 'connected'              → Update wsConnected state
    ├─ 'similarity-update'       → Update realTimeSimilarity
    └─ 'message:verification-result' → Update result & scores
    ↓
State Updates
    ├─ setResult()
    ├─ setRealTimeSimilarity()
    ├─ setRecentScores()
    ├─ setMatchAttempts()
    └─ setRecordingTime()
    ↓
Component Re-renders
    ↓
UI Shows New Data
```

---

## Threshold Slider

The threshold slider (0.0 → 1.0) determines if a match is successful:

```javascript
const isMatch = similarityScore >= threshold

// Examples:
if (score >= 0.75) → VERIFIED ✓
if (score <  0.75) → REJECTED ✗
```

- Default: 0.75 (75%)
- Adjustable during idle (disabled while recording)
- Changes instantly update color coding

---

## Error Handling

### Connection Lost
```
Status: 🟠 Connecting...
Message: "Failed to start recording..."
```

### Recording Error
```
Error: "Failed to start recording. Please ensure 
       microphone access and WebSocket connection."
```

### Verification Timeout
```
Error: "Request timeout: start-verification"
```

### Enrollment Not Found
```
Status: ✗ Not Enrolled
Message: "Identity not found. Please enroll first."
```

---

## Performance Tips

1. **Keep Recent Scores Small** - Array limited to 5 entries
2. **Connection Quality Checked Every 30s** - Not on every render
3. **State Updates Batched** - React handles optimally
4. **No Unnecessary Re-renders** - useEffect dependencies set

---

## Testing Scenarios

### Successful Match ✓
1. Phone: +1 555 000-0001
2. Speak: "Verify my identity today"
3. Expected: Similarity > 0.75, badge shows "VERIFIED ✓"

### Failed Match ✗
1. Using unregistered phone number
2. Or speaking different phrase
3. Expected: Similarity < 0.75, badge shows "REJECTED ✗"

### Connection Quality
1. Watch header for latency display
2. Should show: "Online (excellent/good/fair)" 
3. Latency in parentheses: (25ms)

### Recent Scores
1. Perform 5+ verifications
2. Recent scores panel populates
3. Shows last 5 attempts with colors

### Success Rate
1. Perform 10 verifications
2. Action bar shows: "Success Rate: 70%"
3. Formula: 7 matches / 10 attempts

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

All browsers supporting:
- WebSocket
- getUserMedia (audio recording)
- ES6+ JavaScript

---

## Migration from Old Code

If upgrading from REST API version:

```javascript
// OLD (REST API)
const [audioBlob, setAudioBlob] = useState(null);
const [verificationResult, setVerificationResult] = useState(null);
const [isRecording, setIsRecording] = useState(false);
const [isVerifying, setIsVerifying] = useState(false);

// NEW (WebSocket)
const { verifying, recording, result, status, startVerification, startRecording, stopRecording } = useVerification(phoneNumber);
const [matchAttempts, setMatchAttempts] = useState(0);
const [recentScores, setRecentScores] = useState([]);
const [realTimeSimilarity, setRealTimeSimilarity] = useState(null);
```

Key differences:
- No manual audio blob management
- No manual verification API calls
- Real-time scores via WebSocket
- Automatic state management

---

## Troubleshooting

### Q: Real-time scores not showing?
A: Check that WebSocket is connected (header should show "Online"). Backend must emit similarity updates.

### Q: Match counter not incrementing?
A: Verify result includes `isMatch: true` field. Check threshold is set correctly.

### Q: Recording won't start?
A: Check browser permissions for microphone. Verify WebSocket connection established.

### Q: Latency shows very high?
A: Normal in development. May indicate slow network or backend processing.

### Q: "Connecting..." never resolves?
A: Backend WebSocket service may not be running. Check `REACT_APP_WS_URL` env variable.

---

## Files Modified

- `frontend/src/components/VerificationPage.js` - Main component
- Uses existing:
  - `frontend/src/services/useWebSocket.js` - Hooks
  - `frontend/src/services/websocketService.js` - Service
  - `frontend/src/services/api.js` - REST API (limited use)

---

## Next Reference

See [PHASE_3_5_COMPLETION_REPORT.md](../PHASE_3_5_COMPLETION_REPORT.md) for full technical documentation.
