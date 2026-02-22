# Voice Biometric Multi-Sample Enrollment Upgrade Guide

## Overview
The enrollment frontend has been upgraded to support **5 separate voice samples** instead of a single recording. This provides more robust biometric verification with better accuracy.

## 📋 What's Changed

### Frontend Components

#### 1. **VoiceSampleCard Component** (`VoiceSampleCard.jsx`)
A reusable card component for recording individual voice samples with:
- **Record Button**: Start/begin recording
- **Stop Button**: Stop recording (visible when recording)
- **Play Button**: Playback recorded audio
- **Delete Button**: Re-record the sample
- **Visual Feedback**: 
  - RED card = Not recorded
  - GREEN card = Successfully recorded
  - Real-time recording timer

#### 2. **Updated EnrollmentPage Component** (`EnrollmentPage.js`)
Enhanced to manage 5 samples with:
- Multi-sample state management
- Progress tracking (X/5 samples recorded)
- Progress bar visualization
- Sample validation (all 5 required)
- Batch submission of all 5 samples

## 🎯 Component Structure

### State Management
```javascript
const [samples, setSamples] = useState(Array(5).fill(null).map(() => ({ 
  blob: null,      // Audio blob from recording
  duration: 0      // Duration in seconds
})));

const [recordingBlackout, setRecordingBlackout] = useState(-1); // Which sample is recording
const [isSubmitting, setIsSubmitting] = useState(false);
const [error, setError] = useState(null);
const [result, setResult] = useState(null);
```

### Key Functions

#### `handleAudioRecorded(sampleIndex, audioBlob, duration)`
Updates the audio blob and duration for a specific sample.

#### `handleRecordingStart(sampleNumber)` / `handleRecordingStop()`
Manages recording state to prevent simultaneous recordings.

#### `validateSamples()`
Validates:
- All 5 samples are recorded
- Each sample is at least 2 seconds long
- Returns validation message if any check fails

#### `handleSubmit()`
Processes all 5 samples:
1. Establishes WebSocket connection
2. Sends each sample's audio chunks sequentially
3. Sends enrollment request with `sample_count: 5`
4. Waits for enrollment result

## 📤 API Integration

### WebSocket Message Protocol

#### Audio Transmission (per chunk)
```javascript
{
  type: "audio",
  sample_number: 1,        // NEW: Which sample (1-5)
  chunk_number: 0,         // Chunk index within sample
  total_chunks: 8,         // Total chunks for this sample
  is_last: false,          // Is this the last chunk?
  data: "base64..."        // Base64 audio data
}
```

#### Enrollment Request
```javascript
{
  type: "enroll",
  phone_number: "+1-555-0000",
  sample_count: 5           // NEW: Number of samples sent
}
```

### Expected Backend Response
```javascript
{
  type: "enrollment_success",
  payload: {
    message: "All 5 voice samples enrolled successfully!",
    vector_id: "uuid-string",
    sample_count: 5
  }
}
```

## ✅ Validation Rules

1. **Phone Number**: Required, non-empty
2. **Sample Count**: Exactly 5 samples required
3. **Sample Duration**: Each sample ≥ 2 seconds
4. **Recording Quality**: Only one sample can be recorded at a time

## 🎨 UI Features

### Visual Indicators
- **RED cards**: Samples not yet recorded
- **GREEN cards**: Samples successfully recorded
- **Progress bar**: Real-time progress (0-100%)
- **Sample counter**: X/5 displayed in header
- **Status messages**: 
  - Incomplete warning when some samples missing
  - Error alerts for validation failures
  - Success confirmation with vector ID

### User Experience
- Disabled phone input while recording
- Disabled submit button until all 5 samples recorded
- Clear validation messages
- Recording timer (MM:SS format)
- Playback capability before submission
- Easy re-recording (delete button)

## 🔧 Backend Requirements

### Changes Needed
1. **Update enrollment endpoint** to accept multiple audio samples:
   - Parse `sample_number` from WebSocket messages
   - Store samples individually or merge them
   - Track `sample_count` in the request

2. **Update database schema** (if applicable):
   - Option A: Store all 5 samples separately with sample indices
   - Option B: Merge samples into a single preprocessed audio
   - Include metadata: `enrollment_sample_count`, `sample_timestamps`

3. **Update embedding generation**:
   - Generate single embedding from merged audio
   - Or generate per-sample embeddings and average them
   - Store reference for future verification

### Sample Processing Logic (Example)
```python
# Pseudo-code for backend
@ws_handler
async def handle_enrollment_request(message):
    if message['type'] == 'audio':
        sample_num = message['sample_number']  # 1-5
        # Store audio chunk for this sample
        store_audio_chunk(sample_num, message)
    
    elif message['type'] == 'enroll':
        phone = message['phone_number']
        sample_count = message['sample_count']  # 5
        
        # Retrieve all 5 samples
        all_samples = retrieve_audio_samples(5)
        
        # Option 1: Merge samples
        merged_audio = merge_audio_samples(all_samples)
        
        # Option 2: Average embeddings
        embeddings = [extract_embedding(s) for s in all_samples]
        avg_embedding = np.mean(embeddings, axis=0)
        
        # Enroll
        result = enroll_voice(phone, merged_audio, avg_embedding)
```

## 📊 Migration Path

### If You Have Existing Code Using Single Sample:
1. **Keep existing verification logic** - no changes needed
2. **Deprecate old enrollment** - mark as legacy
3. **Update API endpoint** to handle both:
   - Check `sample_count` in request
   - Route to appropriate handler

### Example Wrapper:
```python
async def enroll(phone_number, samples):
    """
    Handle both single and multi-sample enrollment
    
    Args:
        phone_number: User identifier
        samples: List of audio blobs (1 or 5)
    """
    if len(samples) == 1:
        # Legacy single-sample enrollment
        return legacy_enroll(phone_number, samples[0])
    elif len(samples) == 5:
        # New multi-sample enrollment
        return multi_sample_enroll(phone_number, samples)
```

## 🧪 Testing

### Frontend Testing
1. Record all 5 samples successfully
2. Verify each sample shows GREEN card
3. Delete a sample and verify card changes back to RED
4. Try submitting without all 5 samples (should show error)
5. Submit all 5 and verify success message

### Backend Testing
1. Verify receiving all 5 samples via WebSocket
2. Track sample numbers correctly
3. Merge/process samples correctly
4. Generate correct embedding
5. Verify enrollment successful

## 📝 Code Examples

### Using the Component
```javascript
import EnrollmentPage from './components/EnrollmentPage';

function App() {
  return <EnrollmentPage />;
}
```

### Accessing Recorded Samples (if needed)
The samples are managed internally in the component state, but you can extend it to expose them:

```javascript
// Add ref callback
const handleSubmit = async () => {
  // Access samples directly
  const recordedAudio = samples.map(s => s.blob);
  // Send to backend...
};
```

## 🐛 Troubleshooting

### Issue: "Please record all 5 voice samples"
**Solution**: Ensure each sample is at least 2 seconds and click Record/Stop for each.

### Issue: Recording stuck (sample card shows recording)
**Solution**: 
- Click "Stop Recording" button
- If issue persists, check browser console for errors
- Verify microphone permissions

### Issue: Play button doesn't work
**Solution**: Ensure sample was fully recorded (duration > 0)

### Issue: WebSocket timeout during submission
**Solution**: Ensure backend WebSocket endpoint is running and accessible

## 🚀 Deployment Checklist

- [ ] VoiceSampleCard.jsx created in `/components`
- [ ] EnrollmentPage.js updated with multi-sample logic
- [ ] Backend WebSocket handler updated for `sample_number`
- [ ] Backend enrollment logic handles 5 samples
- [ ] Database schema supports multiple samples per enrollment
- [ ] Test with 5 samples end-to-end
- [ ] Verify backward compatibility (if applicable)
- [ ] Update API documentation
- [ ] Test microphone permissions on all browsers
- [ ] Test on mobile browsers (if applicable)

## 📚 Related Files

- **Component**: `/frontend/src/components/EnrollmentPage.js`
- **Card Component**: `/frontend/src/components/VoiceSampleCard.jsx`
- **Audio Utilities**: `/frontend/src/utils/audioRecorder.js`
- **Backend API**: Backend enrollment endpoint
- **Services**: `/frontend/src/services/api.js`

---

**Version**: 1.0  
**Last Updated**: February 2026  
**Status**: Production Ready
