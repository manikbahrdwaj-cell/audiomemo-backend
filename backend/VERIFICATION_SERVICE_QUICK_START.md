# VERIFICATION SERVICE - QUICK START GUIDE

Get started with voice verification in minutes.

## Prerequisite: Enrollment

Before verification, ensure a phone number is enrolled:
```python
from enrollment_service import get_enrollment_manager
from voice_embedding import generate_embedding

# During enrollment:
enrollment_manager = get_enrollment_manager()
session = enrollment_manager.create_session("+1-234-567-8900")
# ... collect audio chunks and finalize ...
# This stores embedding in MongoDB
```

## Step 1: Initialize Verification Manager

```python
from verification_service import get_verification_manager

manager = get_verification_manager()
```

## Step 2: Create Verification Session

```python
# Create session for a phone number
phone_number = "+1-234-567-8900"

try:
    session = manager.create_session(phone_number)
    print(f"Session created: {session.session_id}")
except ValueError as e:
    print(f"Error: {e}")
    # Phone not enrolled, enrollment required first
```

**What Happens:**
- ✓ Phone number validated
- ✓ Enrolled embedding retrieved from MongoDB
- ✓ Session initialized with configuration
- ✓ Session ID returned for tracking

## Step 3: Perform Verification

```python
import numpy as np
import soundfile as sf

# Load audio from user
audio_data, sample_rate = sf.read("speaker.wav")
audio_data = audio_data.astype(np.float32)

# Verify voice
result, similarity_score, error = await manager.verify(
    session.session_id,
    audio_data,
    sample_rate
)

# Check result
from verification_service import VerificationResult

if result == VerificationResult.MATCH:
    print(f"✓ Successfully verified!")
    print(f"  Score: {similarity_score:.4f}")
elif result == VerificationResult.MISMATCH:
    print(f"✗ Voice doesn't match (score: {similarity_score:.4f})")
elif result == VerificationResult.NOT_ENROLLED:
    print(f"✗ Phone not enrolled")
else:
    print(f"✗ Error: {error}")
```

## Step 4: Get Session Summary

```python
summary = manager.get_session_summary(session.session_id)

print(f"Phone: {summary['phone_number']}")
print(f"Status: {summary['status']}")
print(f"Verified: {summary['verified']}")
print(f"Score: {summary['final_similarity_score']:.4f}")
print(f"Attempts: {summary['attempts']}/{summary['max_attempts']}")
```

## Complete Example

```python
import asyncio
import soundfile as sf
import numpy as np
from verification_service import (
    get_verification_manager,
    VerificationResult,
    VerificationSessionConfig
)

async def verify_speaker(phone_number: str, audio_path: str):
    """Complete verification workflow"""
    
    # 1. Initialize manager with custom config if needed
    manager = get_verification_manager()
    
    # 2. Create session (retrieves enrollment from MongoDB)
    try:
        session = manager.create_session(phone_number)
        print(f"✓ Verification session created\n")
    except ValueError as e:
        print(f"✗ Failed to create session: {e}")
        return False
    
    # 3. Load audio
    audio_data, sr = sf.read(audio_path)
    audio_data = audio_data.astype(np.float32)
    print(f"✓ Loaded audio: {len(audio_data)} samples at {sr}Hz\n")
    
    # 4. Perform verification
    print("Verifying speaker...")
    result, score, error = await manager.verify(
        session.session_id,
        audio_data,
        sr
    )
    
    # 5. Display results
    print(f"\n{'='*50}")
    print("VERIFICATION RESULT")
    print(f"{'='*50}")
    print(f"Phone Number: {phone_number}")
    print(f"Result: {result.value.upper()}")
    print(f"Similarity Score: {score:.4f}")
    print(f"Threshold Used: {session.config.similarity_threshold}")
    
    if result == VerificationResult.MATCH:
        print(f"Status: ✓ VERIFIED")
        return True
    else:
        print(f"Status: ✗ NOT VERIFIED")
        if error:
            print(f"Error: {error}")
        return False
    
    # 6. Get full summary for record keeping
    summary = manager.get_session_summary(session.session_id)
    print(f"\nFull Summary:")
    print(f"  Attempts: {summary['attempts']}/{summary['max_attempts']}")
    print(f"  Remaining: {summary['remaining_attempts']}")
    print(f"  Status: {summary['status']}")

# Run
if __name__ == "__main__":
    asyncio.run(verify_speaker(
        phone_number="+1-234-567-8900",
        audio_path="verification_sample.wav"
    ))
```

## Common Tasks

### Task 1: Handle Multiple Verification Attempts

```python
for attempt in range(3):
    result, score, error = await manager.verify(
        session.session_id,
        audio_data,
        sample_rate
    )
    
    if result == VerificationResult.MATCH:
        print(f"✓ Verified on attempt {attempt + 1}")
        break
    else:
        remaining = session.get_remaining_attempts()
        print(f"Attempt {attempt + 1} failed. {remaining} attempts remaining.")
    
    if remaining <= 0:
        print("✗ Verification failed - too many attempts")
        break
```

### Task 2: Use Custom Configuration

```python
from verification_service import VerificationSessionConfig

# Create stricter config for high-security application
strict_config = VerificationSessionConfig(
    similarity_threshold=0.92,  # Higher = stricter
    max_attempts=2,
    session_timeout_seconds=120
)

# Use with manager
manager = get_verification_manager(strict_config)
session = manager.create_session("+1-234-567-8900")
```

### Task 3: Check Verification History

```python
history = manager.get_verification_history(
    phone_number="+1-234-567-8900",
    limit=10
)

for record in history:
    print(f"{record['timestamp']}: {record['result']} "
          f"(score: {record['similarity_score']:.4f})")
```

### Task 4: Cancel Session

```python
if manager.cancel_session(session.session_id):
    print("✓ Session cancelled")
else:
    print("✗ Session not found")
```

### Task 5: Get Statistics

```python
stats = manager.get_statistics()

print(f"Total Sessions: {stats['total_sessions']}")
print(f"Verified: {stats['verified_sessions']}/{stats['completed_sessions']}")
print(f"Success Rate: {stats['success_rate']:.1%}")
print(f"Avg Score: {stats['avg_similarity_score']:.4f}")
```

## Error Handling Patterns

### Pattern 1: Try-Except for Session Creation

```python
from verification_service import VerificationSessionConfig

try:
    session = manager.create_session(phone_number)
    print("✓ Session created")
except ValueError as e:
    if "not enrolled" in str(e).lower():
        print("Need enrollment first")
    elif "invalid" in str(e).lower():
        print("Invalid phone number format")
    else:
        print(f"Error: {e}")
```

### Pattern 2: Handle Verification Results

```python
from verification_service import VerificationResult

result, score, error = await manager.verify(...)

match result:
    case VerificationResult.MATCH:
        print("✓ Verified")
    case VerificationResult.MISMATCH:
        print(f"✗ Not matched (score: {score:.4f})")
    case VerificationResult.NOT_ENROLLED:
        print("✗ Phone not enrolled")
    case VerificationResult.TIMEOUT:
        print("✗ Session timed out")
    case VerificationResult.ERROR:
        print(f"✗ Error: {error}")
```

### Pattern 3: Comprehensive Try-Catch

```python
async def safe_verification(phone_number, audio_data, sr):
    """Safe verification with full error handling"""
    
    try:
        # Create session
        session = manager.create_session(phone_number)
        
        # Check if session valid
        if not session.can_attempt_verification():
            return False, 0.0, "Session not valid for verification"
        
        # Verify
        result, score, error = await manager.verify(
            session.session_id,
            audio_data,
            sr
        )
        
        return (
            result == VerificationResult.MATCH,
            score,
            error or None
        )
        
    except ValueError as e:
        return False, 0.0, f"Validation error: {e}"
    except Exception as e:
        return False, 0.0, f"Unexpected error: {e}"
```

## Integration with FastAPI

```python
from fastapi import FastAPI, HTTPException, File, UploadFile
from verification_service import get_verification_manager, VerificationResult
import soundfile as sf

app = FastAPI()
manager = get_verification_manager()

@app.post("/verify/start/{phone}")
async def start_verification(phone: str):
    try:
        session = manager.create_session(phone)
        return {"session_id": session.session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/verify/{session_id}")
async def verify_audio(session_id: str, file: UploadFile = File(...)):
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Read and verify
    audio_bytes = await file.read()
    audio, sr = sf.read(audio_bytes)
    
    result, score, error = await manager.verify(session_id, audio, sr)
    
    return {
        "verified": result == VerificationResult.MATCH,
        "score": score,
        "error": error
    }

@app.get("/verify/{session_id}/summary")
async def get_summary(session_id: str):
    summary = manager.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary
```

## Testing

Run the test suite:
```bash
python test_verification_service.py
```

This verifies:
- ✓ Manager initialization
- ✓ MongoDB integration
- ✓ Session management
- ✓ Error handling
- ✓ Statistics collection

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Phone number not enrolled" | Enroll first using enrollment_service |
| High false rejections | Lower threshold (0.80 instead of 0.85) |
| High false acceptances | Increase threshold (0.90 instead of 0.85) |
| Session expired | Increase session_timeout_seconds |
| MongoDB connection error | Check MongoDB is running and accessible |
| Audio embedding failed | Check audio format and duration |

## Configuration Quick Reference

```python
# Default (Recommended)
config = VerificationSessionConfig()  # threshold=0.85

# Strict (High Security)
config = VerificationSessionConfig(
    similarity_threshold=0.92,
    max_attempts=2
)

# Lenient (High Acceptance)
config = VerificationSessionConfig(
    similarity_threshold=0.75,
    max_attempts=5
)
```

## Performance Tips

1. **Reuse Manager Instance**
   ```python
   manager = get_verification_manager()  # Singleton - reuse!
   ```

2. **Batch Operations**
   ```python
   for phone in phones:
       session = manager.create_session(phone)
       # ... verify
   ```

3. **Clean Up Expired Sessions**
   ```python
   manager.cleanup_expired_sessions()  # Call periodically
   ```

4. **Check Statistics**
   ```python
   stats = manager.get_statistics()
   # Monitor success rates and adjust thresholds
   ```

## Next: Advanced Usage

- See [VERIFICATION_SERVICE_API_REFERENCE.md](./VERIFICATION_SERVICE_API_REFERENCE.md) for full API
- See [verification_service_examples.py](./verification_service_examples.py) for more examples
- See [VERIFICATION_SERVICE_IMPLEMENTATION_SUMMARY.md](./VERIFICATION_SERVICE_IMPLEMENTATION_SUMMARY.md) for architecture

---

**Need Help?**
1. Check examples: `python verification_service_examples.py`
2. Run tests: `python test_verification_service.py`
3. Read API docs: `VERIFICATION_SERVICE_API_REFERENCE.md`
