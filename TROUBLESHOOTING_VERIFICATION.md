# Quick Troubleshooting Guide

## Issue: Frontend Not Displaying Verification Message

### Step 1: Check Backend Logs
```bash
# Expected logs for SUCCESS:
✓ Voice verification successful for +1-555-1234 (score: 0.92)
Created LangGraph session: <session-id>
Stored verified session in MongoDB: <session-id>
Sending verification result to frontend: SUCCESS

# Expected logs for FAILURE:
✗ Voice verification failed for +1-555-1234 (score: 0.72, threshold: 0.75)
Sending verification result to frontend: FAILED
```

**Problem:** Backend logs show "Generating embedding" but NOT "Sending verification result"
- **Solution:** The `handle_verify()` method may be returning early without reaching the end
- Check for early `return` statements or exceptions
- Verify audio buffer is valid

---

### Step 2: Check Browser Console (F12 → Console)

#### Expected SUCCESS logs:
```javascript
[WS] [INFO] Message received: verification_result
[WS] [INFO] Emitting event: verification_result
verification_result event received in service: {event: "verification_result", type: "verification_result", status: "success", data: {...}}
Processing verification result: {is_match: true, phone_number: "+1-555-1234", similarity_score: 0.92}
✓ Voice verification PASSED - Emitting VERIFIED event
✓ Voice verified successfully {result: "match", similarity: 0.92, ...}
```

#### Expected FAILURE logs:  
```javascript
[WS] [INFO] Message received: verification_result
[WS] [INFO] Emitting event: verification_result
verification_result event received in service: {event: "verification_result", type: "verification_result", status: "failed", data: {...}}
Processing verification result: {is_match: false, phone_number: "+1-555-1234", similarity_score: 0.72}
✗ Voice verification FAILED - Emitting REJECTED event
✗ Voice verification rejected {result: "mismatch", similarity: 0.72, ...}
```

**Problem:** No "Emitting event: verification_result" log
- **Solution:** Your backend is not sending the correct response format
- Check that backend is using the new updated `websocket_events.py`
- Verify `handle_verify()` includes `"event": "verification_result"`

**Problem:** "Emitting event" logged but NO service logs follow
- **Solution:** The event listener was not properly registered
- Check that verificationService listener is set up before backend response arrives
- Look for: "Registering listener for 'verification_result' event"

---

### Step 3: Network Tab Debugging

**In Browser Dev Tools → Network → WS tab:**

1. Click on the `/ws/voice` WebSocket connection
2. Go to Messages tab
3. Look for the last message sent TO backend (should be `verify` message)
4. Look for response message FROM backend

#### Expected response:
```json
{
  "event": "verification_result",
  "type": "verification_result",
  "status": "success",
  "data": {
    "status": "success",
    "is_match": true,
    "message": "This voice is matched with this mobile number: +1-555-1234",
    "phone_number": "+1-555-1234",
    "session_id": "uuid-string",
    "similarity_score": 0.92,
    "threshold": 0.75,
    "metrics": {...}
  },
  "timestamp": "2026-02-19T..."
}
```

**Problem:** Response has `"type": "verification_success"` or `"type": "error"`
- **Solution:** You're still using the OLD code
- Restart backend with latest changes
- Ensure you have the new `websocket_events.py`

---

### Step 4: Checklist for Verification

- [ ] Backend sends response with `"event": "verification_result"`
- [ ] Response includes `"data"` object with all results  
- [ ] Data includes `"is_match": true/false` boolean
- [ ] Data includes `"message"` string
- [ ] Frontend console shows "Emitting event: verification_result"
- [ ] Frontend console shows "verification_result event received in service"
- [ ] Frontend console shows "✓ Voice verified successfully" OR "✗ Voice verification rejected"
- [ ] UI updates to show success/failure message

---

## Common Issues and Fixes

### Issue 1: "No message type in response"
**Cause:** Backend response is missing `"type"` field
**Fix:** Update backend to include both `"type"` and `"event"` fields

### Issue 2: "event listener never called"  
**Cause:** Backend uses old event type like `"verification_success"`
**Fix:** Restart backend, verify latest websocket_events.py is loaded

### Issue 3: "Frontend shows generic error instead of message"
**Cause:** Response data structure doesn't match expected format
**Fix:** Compare your response against the expected format above
- Must have `data.is_match` (boolean)
- Must have `data.message` (string)

### Issue 4: "MongoDB stores session but UI shows failure"
**Cause:** Response sent before session saved
**Fix:** Verify backend completes all database operations before returning

### Issue 5: "CORS error when connecting"
**Cause:** Frontend URL not in allowed origins
**Fix:** Check `main.py` CORS middleware:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    ...
)
```

---

## Testing Commands

### Reset Everything
```bash
# Terminal 1: Backend
cd backend
python main.py  # Make sure latest code is loaded

# Terminal 2: Frontend  
cd frontend
npm start

# Open browser to http://localhost:3000
# F12 to open dev tools
# Go to VerificationPageWebSocket
# Check console for logs
```

### Test with curl (without frontend)
```bash
# Start backend first

# Test WebSocket with wscat
npm install -g wscat

# In another terminal:
wscat -c ws://localhost:8000/ws/voice

# Send verify message:
{
  "type": "verify"
}

# You should see response with "event": "verification_result"
```

---

## Still Not Working?

1. Add debug logging to your handler:
```python
# In handle_verify() at the end, before return:
logger.info(f"DEBUG: About to return result_message: {result_message}")
logger.info(f"DEBUG: Event field: {result_message.get('event')}")
logger.info(f"DEBUG: Data keys: {result_message.get('data', {}).keys()}")
```

2. Check that response is actually being sent:
```python
# After the handler returns:
logger.info(f"DEBUG: Returning from handle_verify with: {response is not None}")
```

3. Verify WebSocket connection is active:
```javascript
// In browser console:
console.log('WebSocket ready state:', ws.readyState);  // Should be 1 (OPEN)
console.log('Verification service initialized:', verificationService != null);
```

4. Check that audio buffer has data:
```python
# In handle_verify(), after getting buffer:
logger.info(f"Buffer size: {buffer.get_size()} bytes")
logger.info(f"Buffer valid: {buffer.is_valid()}")
```

---

## Success Indicators

You'll know it's working when:

✅ Backend logs show "Sending verification result to frontend: SUCCESS/FAILED"
✅ Browser console shows "✓ Voice verification PASSED" or "✗ Voice verification FAILED"  
✅ UI displays green "✓ Verified" OR red "✗ Not Verified" message
✅ Message shows matching phone number or "No phone number is matched with this voice"
✅ Progress bar completes
✅ Similarity score displays
