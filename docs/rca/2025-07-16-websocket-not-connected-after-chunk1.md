# RCA: "WebSocket not connected" after first verification chunk

**Date:** 2025-07-16  
**Severity:** High — verification fails silently after the first `chunk_result`

---

## Summary

After a successful first verification chunk (`is_match: true, final_status: null`), the frontend shows
"❌ WebSocket not connected" and stops sending audio. All subsequent verification attempts fail
without processing chunks 2–4.

---

## Root Cause Analysis

Five compounding bugs were identified:

### Bug 1 — `AudioChunkingService` constructor ignores `mode` option for `chunkSize`
**File:** `frontend/src/services/audioChunkingService.js`, constructor (line ~46)  
**Cause:** The constructor sets `this.chunkSize = options.chunkSize || AUDIO_CONFIG.ENROLLMENT_CHUNK_SAMPLES`
regardless of `options.mode`. When `mode: 'verification'` is passed, `chunkSize` stays at 16 000 samples (1 s)
instead of the correct 80 000 (5 s). Audio chunks fire every 1 s, not every 5 s.  
**Impact:** The backend receives 1-second WAV blobs and accumulates them correctly, but the architecture is
wrong and causes a high submit-rate that can race with Promise resolution.

### Bug 2 — `onclose` handler doesn't null `this.ws` (primary crash cause)
**File:** `frontend/src/services/realtimeVerificationService.js`, `connect()` → `this.ws.onclose` (line ~101)  
**Cause:** When the WebSocket closes for any reason (network hiccup, backend close, dev-server timeout),
`this.ws` is left pointing to the closed `WebSocket` object.  
**Effect:** The next call to `sendAudioChunk` hits `this.ws && this.ws.readyState === WebSocket.OPEN`.
`this.ws` is non-null (passes the first check) but `readyState` is `3` (CLOSED), so the `else` branch
fires: `reject(new Error('WebSocket not connected'))`.

### Bug 3 — `onerror` sets `isVerified = false`, making `isComplete = true`
**File:** `frontend/src/hooks/useRealtimeVerification.js`, ERROR handler (line ~85)  
**Cause:** `service.on(ERROR, () => { setIsVerified(false); ... })` — setting `isVerified` to `false`
(rather than leaving it at `null`) makes `isComplete = (isVerified !== null) = true`.  
**Effect:** The `useEffect` watching `isComplete` in `VerificationPageRealtime.jsx` fires
`handleStopRecording()`, cutting off the microphone stream before max chunks are reached.

### Bug 4 — `connectForVerification` accumulates event listeners on every call
**File:** `frontend/src/hooks/useRealtimeVerification.js`, `connectForVerification` (line ~44)  
**Cause:** `service.on(EVENT, handler)` is called inside `connectForVerification` without a matching
`service.off`. Re-calling `connectForVerification` (e.g. "Try Again") stacks duplicate handlers that
all fire for every event, leading to duplicate state updates and hard-to-trace bugs.

### Bug 5 — Backend `session_created` message omits `threshold`
**File:** `backend/app/api/routes/verification.py`, `websocket_verify_endpoint` (line ~780)  
**Cause:** The `session_created` JSON payload does not include a `threshold` key. The frontend's
`_handleMessage` keeps the value from the `connect()` call, but the results-summary UI may show an
incorrect threshold if the enrolled profile has a custom threshold.

---

## Impact

- Verification always fails after chunk 1 because the WS is considered disconnected.
- Recording stops, leaving the session in an inconsistent half-processed state.
- "Try Again" flow accumulates duplicate WebSocket event listeners, causing state corruption on
  the second attempt.

---

## Fix Required

### T01 — Fix `AudioChunkingService` constructor chunkSize for verification mode
**File:** `frontend/src/services/audioChunkingService.js`  
**Change:** After setting `this.mode`, conditionally set `this.chunkSize`:
```js
if (this.mode === 'verification') {
  this.chunkSize = AUDIO_CONFIG.VERIFICATION_CHUNK_SAMPLES;
}
```

### T02 — Null `this.ws` in `onclose` + emit meaningful error on unexpected close
**File:** `frontend/src/services/realtimeVerificationService.js`  
**Change:** In the `onclose` handler, set `this.ws = null` before emitting `CONNECTION_CLOSED`.
If the connection was not intentionally closed and verification is not yet complete, also emit
an ERROR event so the UI surfaces the disconnect instead of silently showing "WebSocket not connected"
on the next chunk.

### T03 — Keep `isVerified = null` for transient errors; only set false on definitive UNVERIFIED
**File:** `frontend/src/hooks/useRealtimeVerification.js`  
**Change:** In the ERROR handler, do NOT call `setIsVerified(false)`. Instead, only set `status`
and `error`. `isVerified = false` should only be set from the UNVERIFIED event.

### T04 — Remove event listeners before re-adding in `connectForVerification`
**File:** `frontend/src/hooks/useRealtimeVerification.js`  
**Change:** Call `service.removeAllListeners()` (or `service.off` for each event) at the start of
`connectForVerification` before re-registering handlers.

### T05 — Add `threshold` to backend `session_created` message
**File:** `backend/app/api/routes/verification.py`  
**Change:** Add `"threshold": session.threshold` to the `session_created` JSON payload.

---

## Verification Steps

1. Start backend: `cd backend && python run.py`
2. Start frontend: `cd frontend && npm start`
3. Enroll a phone number via the Enrollment page.
4. Go to Verification, enter the enrolled phone number, click "Initiate Call".
5. Speak continuously.
6. Confirm the Network tab shows binary WS frames every 5 seconds (not every 1 second).
7. Confirm chunk_result 1, 2, 3, 4 all arrive without any "WebSocket not connected" error.
8. Confirm final `chunk_result` has `final_status: "verified"` or `"unverified"`.
9. Click "Try Again", repeat steps 4–8 — confirm no duplicate event listener side-effects.

---

## Task List

```json
[
  {
    "id": "T01",
    "title": "Fix chunkSize for verification mode",
    "type": "bug_fix",
    "priority": "medium",
    "layer": "frontend",
    "file": "frontend/src/services/audioChunkingService.js",
    "function_or_class": "AudioChunkingService constructor",
    "description": "The constructor sets `this.chunkSize = options.chunkSize || AUDIO_CONFIG.ENROLLMENT_CHUNK_SAMPLES` but never checks `this.mode`. When `mode: 'verification'` is passed, chunkSize stays at 16000 (1 second). Add a conditional after setting `this.mode`: if (this.mode === 'verification') { this.chunkSize = AUDIO_CONFIG.VERIFICATION_CHUNK_SAMPLES; }. This ensures onChunkReady fires every 5 seconds in verification mode.",
    "depends_on": [],
    "context_files": [
      "frontend/src/services/audioChunkingService.js",
      "frontend/src/components/VerificationPageRealtime.jsx"
    ],
    "acceptance_criteria": [
      "AudioChunkingService({ mode: 'verification' }) results in chunkSize = 80000",
      "AudioChunkingService({ mode: 'enrollment' }) results in chunkSize = 16000",
      "AudioChunkingService({}) defaults to chunkSize = 16000"
    ],
    "estimated_lines_changed": 3
  },
  {
    "id": "T02",
    "title": "Null this.ws in onclose handler",
    "type": "bug_fix",
    "priority": "high",
    "layer": "frontend",
    "file": "frontend/src/services/realtimeVerificationService.js",
    "function_or_class": "connect",
    "description": "The `onclose` event handler does not set `this.ws = null`. This leaves a stale closed WebSocket reference. Any subsequent call to sendAudioChunk passes the `this.ws &&` null check but fails the `this.ws.readyState === WebSocket.OPEN` check, throwing 'WebSocket not connected'. Fix: set `this.ws = null` as the first statement in `onclose`. Also, if `this.status` is not COMPLETED and not VERIFIED/UNVERIFIED, emit an ERROR event with message 'Connection lost unexpectedly' so the UI can surface the disconnect.",
    "depends_on": [],
    "context_files": [
      "frontend/src/services/realtimeVerificationService.js",
      "frontend/src/hooks/useRealtimeVerification.js"
    ],
    "acceptance_criteria": [
      "After onclose fires, this.ws is null",
      "sendAudioChunk called after onclose throws 'WebSocket not connected' via the null check path",
      "If verification is incomplete, ERROR event is emitted with message 'Connection lost unexpectedly'"
    ],
    "estimated_lines_changed": 8
  },
  {
    "id": "T03",
    "title": "Don't set isVerified=false on transient error",
    "type": "bug_fix",
    "priority": "high",
    "layer": "frontend",
    "file": "frontend/src/hooks/useRealtimeVerification.js",
    "function_or_class": "connectForVerification",
    "description": "The ERROR event handler calls `setIsVerified(false)`. `isVerified` is typed as `null | boolean` where `null` means pending, `true` means verified, `false` means definitively failed. A transient WebSocket error is not a definitive 'unverified' verdict. Setting `isVerified = false` makes `isComplete = true`, triggering the stop-recording effect and showing the 'Try Again' screen prematurely. Fix: remove `setIsVerified(false)` from the ERROR handler. Only the UNVERIFIED event handler should set `isVerified = false`.",
    "depends_on": [],
    "context_files": [
      "frontend/src/hooks/useRealtimeVerification.js",
      "frontend/src/components/VerificationPageRealtime.jsx"
    ],
    "acceptance_criteria": [
      "After ERROR event, isVerified remains null",
      "isComplete stays false after ERROR event (isVerified is still null)",
      "Recording is NOT stopped on WS error"
    ],
    "estimated_lines_changed": 1
  },
  {
    "id": "T04",
    "title": "Clear listeners before re-adding in connectForVerification",
    "type": "bug_fix",
    "priority": "medium",
    "layer": "frontend",
    "file": "frontend/src/hooks/useRealtimeVerification.js",
    "function_or_class": "connectForVerification",
    "description": "connectForVerification calls service.on() for SESSION_CREATED, CHUNK_RESULT, VERIFIED, UNVERIFIED, ERROR, CONNECTION_CLOSED on every invocation. If the user clicks 'Try Again' which calls disconnect() and then connectForVerification again, all six handlers accumulate. On the second session, every event fires twice. Fix: call service.removeAllListeners() (see webSocketEventEmitter.js for the API) at the beginning of connectForVerification, before any service.on() call. If removeAllListeners does not exist in the EventEmitter, add it.",
    "depends_on": [],
    "context_files": [
      "frontend/src/hooks/useRealtimeVerification.js",
      "frontend/src/services/realtimeVerificationService.js",
      "frontend/src/services/webSocketEventEmitter.js"
    ],
    "acceptance_criteria": [
      "Second call to connectForVerification does not double-fire any event handler",
      "Only the latest handler set is active for each event"
    ],
    "estimated_lines_changed": 5
  },
  {
    "id": "T05",
    "title": "Add threshold to session_created payload",
    "type": "bug_fix",
    "priority": "low",
    "layer": "route",
    "file": "backend/app/api/routes/verification.py",
    "function_or_class": "websocket_verify_endpoint",
    "description": "The session_created JSON sent to the client does not include a 'threshold' field. Add `'threshold': session.threshold` to the send_json call. The session object is RealtimeVerificationSession which stores the threshold used for this session. This allows the frontend to display the accurate threshold and avoids relying on the client-supplied value.",
    "depends_on": [],
    "context_files": [
      "backend/app/api/routes/verification.py",
      "backend/app/services/verification_streaming.py"
    ],
    "acceptance_criteria": [
      "session_created JSON includes a 'threshold' key with the float value",
      "Frontend _handleMessage correctly reads message.threshold"
    ],
    "estimated_lines_changed": 1
  }
]
```
