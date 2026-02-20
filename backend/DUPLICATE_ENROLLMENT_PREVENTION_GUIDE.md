"""
DUPLICATE ENROLLMENT PREVENTION IMPLEMENTATION GUIDE

Voice Biometric Authentication System
Prevents duplicate enrollment of the same phone number
"""

# ==============================================================================
# ARCHITECTURE OVERVIEW
# ==============================================================================

"""
The duplicate enrollment prevention is implemented at multiple layers
to ensure robustness and prevent race conditions:

1. REST ENDPOINT LAYER (/enrollment/session)
   └─> Checks at session creation time
   └─> Returns HTTP 409 Conflict if already enrolled
   └─> Prevents session creation for duplicate phone numbers

2. ENROLLMENT SERVICE LAYER (finalize_enrollment)
   └─> Double-checks before storing embedding
   └─> Prevents race conditions from concurrent requests
   └─> Handles both session API and WebSocket flows

3. WEBSOCKET HANDLER LAYER (handle_enroll)
   └─> Checks before generating embedding
   └─> Returns WebSocket error event
   └─> Cleans up resources on duplicate attempt

4. DATABASE LAYER (check_enrollment)
   └─> Atomic query to check phone number existence
   └─> Uses MongoDB unique index on phone_number field
   └─> Foundation for all higher-layer checks
"""

# ==============================================================================
# IMPLEMENTATION DETAILS BY LAYER
# ==============================================================================

# ==============================================================================
# 1. DATABASE LAYER (database.py)
# ==============================================================================

"""
Function: check_enrollment(phone_number: str) -> bool
Location: database.py, line 183

Description:
  Checks if a phone number is already enrolled in the database.
  This is the atomic operation that all other layers depend on.

How it works:
  1. Queries the voice_embeddings collection
  2. Counts documents with matching phone_number
  3. Returns True if count > 0, False otherwise

Usage:
  from database import check_enrollment
  
  is_enrolled = check_enrollment("+1234567890")
  if is_enrolled:
      return error_response("Already enrolled")

Important Notes:
  - Uses MongoDB's count_documents() for atomic counting
  - Relies on unique index: _collection.create_index("phone_number", unique=True)
  - Very efficient O(1) lookup due to indexing
  - Thread-safe and process-safe at database level
"""

# ==============================================================================
# 2. REST ENDPOINT LAYER (main.py)
# ==============================================================================

"""
Endpoint: POST /enrollment/session
Location: main.py, line 666

Parameters:
  - phone_number: str (required)
  - max_chunks: int (default: 5)
  - merge_embeddings: bool (default: True)

Implementation Flow:
  1. Receives request to create enrollment session
  2. Checks if phone_number is already enrolled (check_enrollment)
  3. If already enrolled:
     └─> Logs warning with phone number
     └─> Raises HTTPException(status_code=409)
     └─> Response detail: "This number is already enrolled..."
  4. If not enrolled:
     └─> Creates EnrollmentSessionConfig
     └─> Creates new EnrollmentSession
     └─> Returns EnrollmentSessionResponse with session_id

HTTP Response Codes:
  - 200 OK: Session created successfully
  - 409 Conflict: Phone number already enrolled
    Response body: {
        "detail": "This number is already enrolled. Duplicate enrollment is not allowed."
    }

Error Handling:
  - Duplicate enrollment is treated as a client error (4xx)
  - Returns 409 instead of 400 to indicate conflict/idempotency issue
  - Frontend can display specific message to user
  - No server-side error logging (uses logger.warning, not logger.error)

Example Client Code (Python):
  import requests
  
  response = requests.post(
      "http://localhost:8000/enrollment/session",
      params={
          "phone_number": "+1234567890",
          "max_chunks": 5
      }
  )
  
  if response.status_code == 409:
      print("This number is already enrolled.")
      # Handle duplicate enrollment on frontend
  elif response.status_code == 200:
      session_id = response.json()["session_id"]
      # Proceed with enrollment
"""

# ==============================================================================
# 3. ENROLLMENT SERVICE LAYER (enrollment_service.py)
# ==============================================================================

"""
Method: EnrollmentSession.finalize_enrollment()
Location: enrollment_service.py, line 439

Description:
  This is the CRITICAL LAYER for duplicate prevention.
  It performs a second check before storing the embedding to prevent
  race conditions where two concurrent requests both created sessions.

Implementation Flow:
  1. Sets status to FINALIZING
  2. Validates minimum chunks requirement
  3. Determines final embedding (from merged audio or embeddings)
  4. *** DUPLICATE CHECK ***
     └─> Imports check_enrollment from database
     └─> Calls: if check_enrollment(self.phone_number):
     └─> If True (already enrolled):
        └─> Logs warning: "Phone number is already enrolled..."
        └─> Sets status to ERROR
        └─> Sets error_message
        └─> Returns: (False, error_msg, None)
  5. If not duplicate:
     └─> Calls store_voice_embedding()
     └─> Updates session status to COMPLETED
     └─> Returns: (True, success_msg, embedding)

Race Condition Prevention:
  Scenario: Two concurrent requests for same phone number
  
  Timeline:
  T1: Request A calls POST /enrollment/session
    └─> check_enrollment("+1234567890") returns False ✓
    └─> Session A created ✓
  
  T2: Request B calls POST /enrollment/session (same number)
    └─> check_enrollment("+1234567890") returns False ✓
    └─> Session B created ✓
  
  T3: Request A calls POST /enrollment/session/A/finalize
    └─> Checks check_enrollment("+1234567890") returns False
    └─> Stores embedding, status = COMPLETED ✓
    └─> Request A SUCCESS
  
  T4: Request B calls POST /enrollment/session/B/finalize
    └─> Checks check_enrollment("+1234567890") returns True (because of T3)
    └─> BLOCKS storage
    └─> Returns error: "Phone number already enrolled"
    └─> Request B BLOCKED ✓
  
  Result: First request wins, second request is rejected with 409 Conflict

Why This Matters:
  - REST endpoint check alone is not sufficient (vulnerable to race conditions)
  - finalize_enrollment check prevents actual database corruption
  - Ensures data consistency even with concurrent requests
  - MongoDB's unique index would catch violations, but this is cleaner

Return Values:
  - (True, message, embedding): Enrollment succeeded
  - (False, error_message, None): Enrollment failed (duplicate or error)

Log Output:
  When duplicate is detected:
    WARNING: Phone number +1234567890 is already enrolled...
  
  When enrollment succeeds:
    INFO: ✓ Enrollment completed for +1234567890...

Error Handling:
  - Sets EnrollmentSession.status = EnrollmentStatus.ERROR
  - Sets EnrollmentSession.error_message to detailed error text
  - Entire session is marked as failed
  - No partial data stored
"""

# ==============================================================================
# 4. WEBSOCKET HANDLER LAYER (websocket_events.py)
# ==============================================================================

"""
Method: WebSocketEventHandler.handle_enroll()
Location: websocket_events.py, line 287

Description:
  Handles voice enrollment via WebSocket.
  Includes duplicate check before storing embedding.

Implementation Flow:
  1. Receives enrollment message with phone_number
  2. Validates audio buffer exists and has sufficient audio
  3. Creates session_id and progress dispatcher
  4. *** DUPLICATE CHECK ***
     └─> Calls: if check_enrollment(phone_number):
     └─> If True (already enrolled):
        └─> Logs warning: "Duplicate enrollment attempt..."
        └─> Calls dispatcher.mark_failed(session_id, error_msg)
        └─> Creates error response: "Duplicate enrollment"
        └─> Clears audio buffer
        └─> Returns error message to client
  5. If not duplicate:
     └─> Generates embedding from audio
     └─> Stores in database via store_voice_embedding()
     └─> Marks dispatcher as completed
     └─> Sends success response to client

WebSocket Error Response:
  {
      "type": "error",
      "status": "error",
      "error_type": "duplicate_enrollment",
      "error_message": "This number is already enrolled. Duplicate enrollment is not allowed.",
      "timestamp": "2024-02-19T10:30:45.123456"
  }

WebSocket Success Response:
  {
      "type": "enrollment_success",
      "status": "success",
      "payload": {
          "phone_number": "+1234567890",
          "vector_id": "...",
          "message": "Voice enrolled successfully"
      },
      "timestamp": "2024-02-19T10:30:45.123456"
  }

Frontend Handling:
  JavaScript:
  const message = JSON.parse(event.data);
  
  if (message.error_type === 'duplicate_enrollment') {
      showError("This number is already enrolled.");
  } else if (message.type === 'enrollment_success') {
      showSuccess("Enrollment completed successfully!");
  }

Resource Cleanup:
  - Audio buffer is cleared even on error
  - Progress dispatcher is marked as failed
  - Connection state set to IDLE
  - No dangling resources
"""

# ═══════════════════════════════════════════════════════════════════════════
# FRONTEND IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════

"""
Frontend should display: "This number is already enrolled."

When using REST API:
  - Check for HTTP 409 status code
  - Display error message to user
  - Prevent UI from proceeding to audio collection

Example React Code:
  
  const createSession = async (phoneNumber) => {
      try {
          const response = await fetch('/enrollment/session', {
              method: 'POST',
              params: new URLSearchParams({
                  phone_number: phoneNumber,
                  max_chunks: 5
              })
          });
          
          if (response.status === 409) {
              // Duplicate enrollment
              setError("This number is already enrolled.");
              return null;
          }
          
          if (!response.ok) {
              throw new Error('Failed to create session');
          }
          
          const session = await response.json();
          return session.session_id;
      } catch (error) {
          setError(error.message);
          return null;
      }
  };

When using WebSocket:
  - Subscribe to 'error' messages
  - Check error_type === 'duplicate_enrollment'
  - Display message to user
  - Clear/disable recording UI

Example WebSocket Code:
  
  ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.status === 'error' && 
          message.error_type === 'duplicate_enrollment') {
          setError("This number is already enrolled.");
          setRecordingDisabled(true);
      }
  };
"""

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION & DATABASE
# ═══════════════════════════════════════════════════════════════════════════

"""
MongoDB Configuration:

Collection: voice_embeddings

Indexes:
  - Unique index on phone_number field
    db.voice_embeddings.createIndex(
        { "phone_number": 1 },
        { unique: true }
    )

Document Structure:
  {
      "_id": ObjectId(...),
      "phone_number": "+1234567890",
      "embedding": [0.123, 0.456, ...],  # Vector array
      "created_at": ISODate(...),
      "updated_at": ISODate(...)
  }

Unique Index Behavior:
  - Automatically prevents duplicate phone_number entries at MongoDB level
  - Raises DuplicateKeyError if attempted
  - Our application-level check prevents this error from being reached
  - Acts as last-line-of-defense safety net
"""

# ═══════════════════════════════════════════════════════════════════════════
# ERROR HANDLING POLICY
# ═══════════════════════════════════════════════════════════════════════════

"""
HTTP Status Codes:

409 Conflict (RECOMMENDED):
  - Semantically correct for duplicate enrollment
  - Indicates the request conflicts with existing state
  - Idempotency safe (repeated requests have same effect)
  - Client should not retry immediately
  - Example: "POST /enrollment/session -> 409 Conflict"

Alternative: 400 Bad Request
  - Less semantically correct
  - Implies client sent malformed request
  - Not recommended for this use case

Alternative: 403 Forbidden
  - Implies permission issue
  - Not appropriate here (user has permission, just already enrolled)

Status Code Justification:
  RFC 7231 & RFC 7232 define 409 for conflicts with existing resources
  Duplicate enrollment is a resource conflict scenario
  Using 409 allows frontend to distinguish from other 400-series errors
"""

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING SPECIFICATION
# ═══════════════════════════════════════════════════════════════════════════

"""
Log Level Policy:

REST Endpoint (main.py):
  logger.warning(f"Duplicate enrollment attempt for {phone_number}")
  - Use WARNING level (not ERROR)
  - This is expected behavior, not a system error
  - Helps track duplicate enrollment attempts
  
Enrollment Service (enrollment_service.py):
  logger.warning(f"Phone number {phone_number} is already enrolled...")
  - Use WARNING level
  - Detects race conditions
  - Helps with monitoring/alerting
  
WebSocket Handler (websocket_events.py):
  logger.warning(f"Duplicate enrollment attempt via WebSocket: {phone_number}")
  - Use WARNING level
  - Track WebSocket duplicate attempts
  - Monitor API abuse patterns

Logging Output Examples:
  
  Scenario 1: REST endpoint duplicate attempt
  WARNING:backend.main:Duplicate enrollment attempt for +1234567890
  
  Scenario 2: Race condition prevented at finalize
  WARNING:backend.enrollment_service:Phone number +1234567890 is already enrolled. Re-enrollment is not allowed.
  
  Scenario 3: WebSocket duplicate attempt
  WARNING:backend.websocket_events:Duplicate enrollment attempt via WebSocket: +1234567890

Monitoring/Alerting:
  - Monitor for repeated WARNING logs with same phone number
  - Could indicate:
    * User trying to re-enroll
    * Accidental double-click in UI
    * Malicious duplicate enrollment attempts
    * Testing/development activity
"""

# ═══════════════════════════════════════════════════════════════════════════
# TESTING STRATEGY
# ═══════════════════════════════════════════════════════════════════════════

"""
Test Coverage (see test_duplicate_enrollment_prevention.py):

1. Basic Functionality Tests:
   ✓ test_first_enrollment_succeeds
     - Verify first enrollment completes successfully
   
   ✓ test_duplicate_enrollment_rejected_at_finalize
     - Verify duplicate enrollment fails
     - Check error message contains "already enrolled"
   
   ✓ test_different_phone_numbers_can_enroll
     - Verify system works for multiple users
   
   ✓ test_enrollment_error_status_set_correctly
     - Verify session status = ERROR
     - Verify error_message is populated

2. Data Integrity Tests:
   ✓ test_duplicate_enrollment_prevents_overwrite
     - Verify original embedding is not overwritten
     - Compare document IDs before/after

3. Race Condition Tests:
   ✓ test_check_happens_before_storage
     - Simulate concurrent requests
     - Verify second request fails at finalize
     - Verify first request data is intact

4. Logging Tests:
   ✓ test_logging_on_duplicate
     - Mock logger and verify warning called
     - Check log message content

5. Integration Tests:
   ✓ test_full_enrollment_flow_with_duplicate_prevention
     - End-to-end scenario
     - Both REST and WebSocket paths

Running Tests:
  pytest test_duplicate_enrollment_prevention.py -v
  pytest test_duplicate_enrollment_prevention.py::TestDuplicateEnrollmentPrevention -v
  pytest test_duplicate_enrollment_prevention.py::TestRaceConditionPrevention -v
"""

# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════

"""
Implementation Verification:

✓ Code Changes:
  [✓] enrollment_service.py finalize_enrollment() includes duplicate check
  [✓] main.py /enrollment/session endpoint includes duplicate check
  [✓] websocket_events.py handle_enroll() includes duplicate check
  [✓] All imports of check_enrollment present
  [✓] Proper error messages set
  [✓] Status codes correct (409 for HTTP)

✓ Error Handling:
  [✓] HTTP 409 returned for REST duplicate attempts
  [✓] WebSocket error event sent for duplicate attempts
  [✓] Error messages informative and consistent
  [✓] Resources cleaned up on error path
  [✓] No data corruption on race conditions

✓ Logging:
  [✓] WARNING level used (not ERROR)
  [✓] Phone number logged
  [✓] Duplicate attempts tracked
  [✓] Race conditions logged appropriately

✓ Database:
  [✓] check_enrollment() function exists and works
  [✓] Unique index on phone_number
  [✓] No duplicate phone numbers in collection
  [✓] Atomic operations at database level

✓ Frontend Compatibility:
  [✓] HTTP 409 status code can be detected
  [✓] Error message can be displayed
  [✓] WebSocket error event can be handled
  [✓] User message clear: "This number is already enrolled."

✓ Testing:
  [✓] Unit tests pass
  [✓] Integration tests pass
  [✓] Race condition scenario tested
  [✓] Data integrity verified
"""

# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT NOTES
# ═══════════════════════════════════════════════════════════════════════════

"""
Before Deploying:

1. Database Verification:
   - Ensure MongoDB unique index exists on voice_embeddings.phone_number
   - Check for any existing duplicates in database
   - If duplicates exist, manually clean before deploying

2. Backend Configuration:
   - Verify all three layers have duplicate checks in place
   - Confirm logging is configured properly
   - Test with concurrent requests using load testing tools

3. Frontend Update:
   - Update UI to display "This number is already enrolled"
   - Handle HTTP 409 status code
   - Subscribe to duplicate_enrollment WebSocket error

4. Rollout Strategy:
   - Deploy to staging first
   - Test with same phone number enrolled multiple times
   - Verify error messages display correctly
   - Load test with concurrent requests
   - Monitor logs for WARNING messages
   - Deploy to production

5. Monitoring Post-Deployment:
   - Watch for duplicate enrollment attempts
   - Monitor for unexpected errors
   - Track 409 response rates
   - Set up alerts for suspicious patterns
   - Review logs regularly
"""

# ═══════════════════════════════════════════════════════════════════════════
# MIGRATION PATH (FOR EXISTING SYSTEMS)
# ═══════════════════════════════════════════════════════════════════════════

"""
If Migrating Existing System:

Step 1: Clean Data
  - Identify any duplicate phone_number entries in database
  - Keep only the most recent enrollment per phone number
  - Delete obsolete entries
  - Example MongoDB query:
    db.voice_embeddings.deleteMany({
        "phone_number": {$in: [list_of_duplicates]}
    })

Step 2: Create Unique Index
  - If not already present:
    db.voice_embeddings.createIndex(
        { "phone_number": 1 },
        { unique: true }
    )

Step 3: Deploy Code Changes
  - Deploy this implementation to backend
  - All three layers will now enforce duplicate prevention

Step 4: Update Frontend
  - Deploy UI changes to handle 409 status code
  - Update error message display

Step 5: Verification
  - Run test suite
  - Attempt duplicate enrollments
  - Verify all layers reject duplicates
  - Check logs for warnings
"""

print("Duplicate Enrollment Prevention Implementation Guide")
print("=" * 70)
print("Ready for deployment and testing")
