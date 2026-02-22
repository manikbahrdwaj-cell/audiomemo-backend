# Multi-Sample Enrollment: Quick Reference

## 🚀 Quick Start

### Frontend Usage
The `EnrollmentPage` component handles everything automatically:

```javascript
import EnrollmentPage from './components/EnrollmentPage';

export default function App() {
  return <EnrollmentPage />;
}
```

**That's it!** The component manages 5 sample recording, validation, and submission.

## 📱 UI Overview

```
┌─────────────────────────────────────┐
│  BioVoice ID - Multi-Sample Setup   │
├─────────────────────────────────────┤
│  Phone: +1 (555) 000-0000           │
├─────────────────────────────────────┤
│  Progress: 3/5 [======>-----]       │
├─────────────────────────────────────┤
│ Sample 1 [GREEN - Recorded]         │
│  ├─ Record  Play  Delete            │
│                                     │
│ Sample 2 [GREEN - Recorded]         │
│  ├─ Record  Play  Delete            │
│                                     │
│ Sample 3 [RED - Not Recorded]       │
│  ├─ Record                          │
│                                     │
│ Sample 4 [RED - Not Recorded]       │
│  ├─ Record                          │
│                                     │
│ Sample 5 [RED - Not Recorded]       │
│  ├─ Record                          │
├─────────────────────────────────────┤
│  [Complete Multi-Sample Enrollment] │
│  (Disabled until all 5 recorded)    │
└─────────────────────────────────────┘
```

## 🎤 Recording Flow

### Per Sample (Repeat for each):
1. Click **Record** button (blue)
2. Speak clearly (minimum 2 seconds)
3. Sample card shows real-time timer
4. Click **Stop Recording** button (red)
5. Card turns **GREEN** when recorded

### Before Submission:
- ✅ All 5 cards must be GREEN
- ✅ Phone number must be entered
- ✅ Each sample ≥ 2 seconds

## 📤 What Gets Sent to Backend

### Transmission
```
Sample 1 Audio          Sample 2 Audio          Sample 3 Audio          Sample 4 Audio          Sample 5 Audio
    ↓                       ↓                       ↓                       ↓                       ↓
  Chunks                   Chunks                 Chunks                 Chunks                 Chunks
    │                       │                       │                       │                       │
    └───────────┬───────────┴───────────┬───────────┴───────────┬───────────┘
                │
        WebSocket Messages:
        - {"type": "audio", "sample_number": 1, ...}
        - {"type": "audio", "sample_number": 2, ...}
        - {"type": "audio", "sample_number": 3, ...}
        - {"type": "audio", "sample_number": 4, ...}
        - {"type": "audio", "sample_number": 5, ...}
        - {"type": "enroll", "sample_count": 5}
```

## 🔧 Backend Requirements

### Minimal Changes

```python
# Only need to:
1. Accept "sample_number" in audio messages
2. Store 5 samples instead of 1
3. Process all 5 samples together
4. Return "sample_count": 5 in response

# Old message:
{type: "audio", chunk_number: 0, ...}

# New message:
{type: "audio", sample_number: 1, chunk_number: 0, ...}
```

## 📋 Component Props (if extending)

### VoiceSampleCard Props
```javascript
<VoiceSampleCard
  sampleNumber={1}                    // 1-5
  audioBlob={blob}                    // Recorded audio blob or null
  isRecording={false}                 // Is this sample being recorded?
  onRecordingStart={(num) => {}}      // Called when recording starts
  onRecordingStop={() => {}}          // Called when recording stops
  onAudioRecorded={(blob, dur) => {}} // Called when audio is captured
/>
```

## 🧪 Testing Checklist

- [ ] Record all 5 samples (each 2+ seconds)
- [ ] All cards turn GREEN
- [ ] Progress bar reaches 100%
- [ ] Click Play to hear each sample
- [ ] Delete a sample (card turns RED again)
- [ ] Re-record deleted sample (GREEN again)
- [ ] Submit with all 5 samples required before button activates
- [ ] Receive success message with vector ID
- [ ] Try submitting with only 4 samples (error message)

## 🎯 Key Differences from Old Version

| Feature | Old (1 Sample) | New (5 Samples) |
|---------|---|---|
| Samples Required | 1 | 5 |
| UI Components | Single record button | 5 sample cards |
| Recording | Sequential | One at a time |
| Validation | Duration only | Duration + all 5 |
| WebSocket message | No sample_number | Includes sample_number: 1-5 |
| Color feedback | N/A | RED = pending, GREEN = recorded |
| Backend processing | Simple | Merge/average samples |

## 🔄 Typical Enrollment Time

- **Per Sample**: 20-30 seconds (5s + 10s recording + UI processing)
- **Total for 5**: 2-3 minutes
- **Backend Processing**: 10-20 seconds (embedding generation)
- **Total End-to-End**: 3-4 minutes

## 💡 Pro Tips

1. **Speak naturally**: Don't force pronunciations
2. **Vary conditions**: Record samples with slightly different:
   - Speaking pace
   - Microphone distance
   - Background (if different quiet locations)
3. **Test microphone**: Ensure good recording quality first
4. **Use headphones**: Reduces echo/noise
5. **Re-record if needed**: Use Delete button freely

## 🛠️ Debug Console Output

When troubleshooting, look for these console logs:

```javascript
// Successful flow:
"Sample 1: Splitting audio into 8 transmit chunks"
"Sample 1, Chunk 1/8 sent"
"Sample 1, Chunk 2/8 sent"
// ... (up to chunk 8)
"Sample 2: Splitting audio into 7 transmit chunks"
// ... (repeat for samples 2-5)

// Error cases:
"Error: Sample 3 is too short (1.5s). Minimum required: 2s"
"Please record all 5 voice samples. Current: 4/5"
"Failed to read audio file"
```

## 📚 File Reference

| File | Purpose |
|------|---------|
| `EnrollmentPage.js` | Main enrollment container (5 samples) |
| `VoiceSampleCard.jsx` | Individual sample card (record/play/delete) |
| `audioRecorder.js` | Low-level audio capture |
| `audioChunkSplitter.js` | Split audio into transmission chunks |
| `api.js` | API calls (uses WebSocket for enrollment) |

## 🚨 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Please record all 5 samples" | Not all recorded | Record missing samples (RED cards) |
| "Recording too short" | Sample < 2s | Hold Record for 2+ seconds each |
| "Microphone access denied" | Browser permission | Grant microphone in browser settings |
| "WebSocket timeout" | Backend unresponsive | Verify backend running on correct port |
| Play button disabled | Sample not recorded | Record sample first |

## 📞 Support

For issues:
1. Check browser console (F12 → Console tab)
2. Verify all 5 samples show duration > 2s
3. Check backend WebSocket connection is active
4. Review error message for specific issue
5. See MULTI_SAMPLE_ENROLLMENT_GUIDE.md for detailed info

---

**Quick Reference Version**: 1.0  
**Last Updated**: February 2026
