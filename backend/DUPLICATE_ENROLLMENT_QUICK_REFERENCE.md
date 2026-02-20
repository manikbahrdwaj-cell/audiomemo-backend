# DUPLICATE ENROLLMENT PREVENTION - QUICK REFERENCE

## Summary of Changes

### Three-Layer Implementation to Prevent Duplicate Enrollment

```
┌─────────────────────────────────────────────────────────────┐
│                    DUPLICATE CHECK LAYERS                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  LAYER 1: REST ENDPOINT (main.py)                            │
│  ├─ Check before creating session                            │
│  ├─ Returns HTTP 409 Conflict if duplicate                   │
│  └─ Prevents wasted session creation                         │
│                                                               │
│  LAYER 2: ENROLLMENT SERVICE (enrollment_service.py)         │
│  ├─ Double-check in finalize_enrollment()                    │
│  ├─ CRITICAL: Prevents race conditions                       │
│  ├─ Final gate before database write                         │
│  └─ Sets session status to ERROR if duplicate                │
│                                                               │
│  LAYER 3: WEBSOCKET HANDLER (websocket_events.py)            │
│  ├─ Check before generating embedding                        │
│  ├─ Returns WebSocket error event                            │
│  ├─ Cleans up resources on duplicate                         │
│  └─ Logs warning for analysis                                │
│                                                               │
│  DATABASE: check_enrollment() (database.py)                  │
│  ├─ Atomic MongoDB query                                     │
│  ├─ Uses unique index on phone_number                        │
│  └─ Foundation for all three layers                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Changes

### 1. enrollment_service.py - finalize_enrollment() method

**Location:** Lines 439-490

**Added:**
```python
# Check for duplicate enrollment (prevent re-enrollment)
from database import check_enrollment
if check_enrollment(self.phone_number):
    error_msg = f"Phone number {self.phone_number} is already enrolled. Re-enrollment is not allowed."
    logger.warning(error_msg)
    self.status = EnrollmentStatus.ERROR
    self.error_message = error_msg
    return False, error_msg, None
```

**Effect:** 
- Prevents duplicate embedding storage
- Catches race conditions from concurrent requests
- Sets proper error status and message

---

### 2. main.py - /enrollment/session endpoint

**Location:** Lines 666-720

**Added:**
```python
# Check if phone number is already enrolled (duplicate prevention)
if check_enrollment(phone_number):
    logger.warning(f"Duplicate enrollment attempt for {phone_number}")
    raise HTTPException(
        status_code=409,
        detail=f"This number is already enrolled. Duplicate enrollment is not allowed."
    )
```

**Effect:**
- Returns HTTP 409 Conflict response
- Prevents session creation for enrolled numbers
- Early detection at REST API layer

---

### 3. websocket_events.py - handle_enroll() method

**Location:** Lines 287-361

**Added:**
```python
# Check if phone number is already enrolled (duplicate prevention)
if check_enrollment(phone_number):
    logger.warning(f"Duplicate enrollment attempt via WebSocket: {phone_number}")
    await dispatcher.mark_failed(session_id, "Phone number already enrolled")
    
    error_message = WebSocketMessageBuilder.create_error_message(
        "duplicate_enrollment",
        "This number is already enrolled. Duplicate enrollment is not allowed."
    )
    
    # Clear buffer
    buffer.clear()
    connection.set_state(ConnectionState.IDLE)
    
    return error_message
```

**Effect:**
- Sends WebSocket error event to client
- Cleans up resources properly
- Prevents embedding generation

---

## HTTP Response Codes

| Status | Meaning | Scenario |
|--------|---------|----------|
| **200** | OK | First enrollment successful |
| **409** | Conflict | Phone number already enrolled |
| **400** | Bad Request | Invalid session/missing chunks |
| **404** | Not Found | Session doesn't exist |

---

## WebSocket Error Response

**Error Type:** `duplicate_enrollment`

```json
{
    "type": "error",
    "status": "error",
    "error_type": "duplicate_enrollment",
    "error_message": "This number is already enrolled. Duplicate enrollment is not allowed.",
    "timestamp": "2024-02-19T10:30:45.123456"
}
```

---

## Frontend Implementation

### REST Endpoint Usage

```python
import requests

phone_number = "+1234567890"

response = requests.post(
    "http://localhost:8000/enrollment/session",
    params={"phone_number": phone_number}
)

if response.status_code == 409:
    print("This number is already enrolled.")
    # Show error to user, don't proceed
elif response.status_code == 200:
    session_id = response.json()["session_id"]
    # Proceed with enrollment
```

### WebSocket Usage

```javascript
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.error_type === 'duplicate_enrollment') {
        showError("This number is already enrolled.");
        disableRecording();
    }
};
```

---

## React Component Example

```jsx
const EnrollmentForm = () => {
    const [error, setError] = useState(null);
    const [sessionId, setSessionId] = useState(null);

    const handleCreateSession = async (phoneNumber) => {
        try {
            const response = await fetch('/enrollment/session?' + 
                new URLSearchParams({ phone_number: phoneNumber }), 
                { method: 'POST' }
            );

            if (response.status === 409) {
                setError("This number is already enrolled.");
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to create session');
            }

            const data = await response.json();
            setSessionId(data.session_id);
            setError(null);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div>
            {error && <div className="error">{error}</div>}
            {!sessionId && (
                <input 
                    type="tel" 
                    placeholder="Phone number"
                    onBlur={(e) => handleCreateSession(e.target.value)}
                />
            )}
            {sessionId && <RecordingInterface sessionId={sessionId} />}
        </div>
    );
};
```

---

## Testing

### Run Tests
```bash
# All duplicate prevention tests
pytest test_duplicate_enrollment_prevention.py -v

# Specific test class
pytest test_duplicate_enrollment_prevention.py::TestDuplicateEnrollmentPrevention -v

# Race condition tests
pytest test_duplicate_enrollment_prevention.py::TestRaceConditionPrevention -v
```

### Manual Testing Checklist

- [ ] Create enrollment session for "+1234567890"
- [ ] Complete first enrollment
- [ ] Attempt to create second session for same number → Should get 409 Conflict
- [ ] Test with different phone number → Should succeed
- [ ] Test concurrent requests with same phone number → Both should handle gracefully
- [ ] Check logs for WARNING messages
- [ ] Verify error message displays correctly in frontend

---

## Error Messages

### REST API Error Response (409 Conflict)

```json
{
    "detail": "This number is already enrolled. Duplicate enrollment is not allowed."
}
```

### Logging

```
WARNING:backend.main:Duplicate enrollment attempt for +1234567890
WARNING:backend.enrollment_service:Phone number +1234567890 is already enrolled. Re-enrollment is not allowed.
WARNING:backend.websocket_events:Duplicate enrollment attempt via WebSocket: +1234567890
```

---

## Database Configuration

### MongoDB Unique Index

**Already configured in database.py:**
```python
_collection.create_index("phone_number", unique=True)
```

**Verify index exists:**
```javascript
db.voice_embeddings.getIndexes()
```

**Expected output includes:**
```javascript
{
    "v": 2,
    "key": { "phone_number": 1 },
    "name": "phone_number_1",
    "unique": true
}
```

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                    FRONTEND                             │
│                 (React/JavaScript)                      │
└─────────────────────┬──────────────────────────────────┘
                      │
          ┌───────────┴──────────┐
          │                      │
    ┌─────▼─────┐         ┌──────▼──────┐
    │ REST API  │         │  WebSocket  │
    │  /enroll  │         │  /ws/voice  │
    │  session  │         │             │
    └─────┬─────┘         └──────┬──────┘
          │                      │
    ┌─────▼──────────────────────▼──────┐
    │      LAYER 1: Check               │
    │   /enrollment/session endpoint     │
    │   check_enrollment(phone_number)   │
    │   ↓ Return 409 if exists          │
    └─────┬──────────────────────────────┘
          │
    ┌─────▼──────────────────────────────┐
    │   LAYER 2 & 3: Collect Audio &    │
    │   Process Embedding                │
    └─────┬──────────────────────────────┘
          │
    ┌─────▼──────────────────────────────┐
    │   LAYER 2: Finalize (CRITICAL)     │
    │   finalize_enrollment() method      │
    │   check_enrollment(phone_number)    │
    │   ↓ Prevent race conditions        │
    └─────┬──────────────────────────────┘
          │
    ┌─────▼──────────────────────────────┐
    │   LAYER 3: WebSocket Handler       │
    │   handle_enroll() method            │
    │   check_enrollment(phone_number)    │
    │   ↓ Return error event             │
    └─────┬──────────────────────────────┘
          │
    ┌─────▼──────────────────────────────┐
    │   DATABASE LAYER                   │
    │   check_enrollment(phone_number)    │
    │   MongoDB unique index on phone #   │
    │   Last-line-of-defense             │
    └─────┬──────────────────────────────┘
          │
    ┌─────▼──────────────────────────────┐
    │   MONGODB COLLECTION               │
    │   voice_embeddings                 │
    │   Unique index: phone_number       │
    └────────────────────────────────────┘
```

---

## Key Points

✅ **Three-layer defense** against duplicate enrollment  
✅ **Race condition safe** - check happens before database write  
✅ **HTTP 409 Conflict** - semantically correct status code  
✅ **Clean error messages** - user understands what happened  
✅ **Proper logging** - WARNING level for tracking  
✅ **Resource cleanup** - no dangling resources on error  
✅ **No re-enrollment** - existing data is protected  

---

## Deployment Checklist

- [ ] Code changes reviewed
- [ ] Tests pass locally
- [ ] MongoDB unique index verified
- [ ] Frontend updated to handle 409
- [ ] Error messages display correctly
- [ ] Logs are monitored
- [ ] Load test with concurrent requests
- [ ] Deploy to staging first
- [ ] Verify 409 responses work
- [ ] Deploy to production with monitoring

---

## Support / Questions

If duplicate enrollment is detected in frontend:
1. Check logs for WARNING messages
2. Verify phone number format matches database
3. Confirm MongoDB index exists
4. Test with different phone number
5. Check database for existing enrollment

---

*Generated: February 2026*
*Voice Biometric Authentication System*
