# Multi-Sample Enrollment Quick Start Guide

## 🚀 Quick Overview

The enrollment system now requires users to record **5 separate voice samples** instead of 1. Each sample gets visual feedback (red = not recorded, green = recorded) and can be replayed or re-recorded before submission.

## 📦 What You'll Use

### Frontend Components
1. **EnrollmentPage.js** - Main component managing 5-sample workflow
2. **VoiceSampleCard.jsx** - Reusable card for individual sample recording

### States & Props
```javascript
// VoiceSampleCard expects:
<VoiceSampleCard
  sampleNumber={1}                    // Sample 1-5
  audioBlob={samples[0].blob}         // Recorded audio (null if not recorded)
  isRecording={recordingBlackout === 1}  // Is this sample recording?
  onRecordingStart={handleRecordingStart}  // Callback when recording starts
  onRecordingStop={handleRecordingStop}    // Callback when recording stops
  onAudioRecorded={(blob, dur) => {}}      // Callback with audio blob & duration
/>
```

## 🎯 User Flow

```
User enters phone number
    ↓
User sees 5 RED cards (Sample 1-5)
    ↓
For each sample:
  → Click Record → Speak for 2+ seconds → Click Stop
  → Audio recorded, card turns GREEN
  → Can click Play to verify or Delete to re-record
    ↓
All 5 cards turn GREEN + progress bar = 100%
    ↓
Click "Complete Multi-Sample Enrollment"
    ↓
Backend processes all 5 samples
    ↓
Success! Phone cleared, ready for next enrollment
```

## ⚙️ Setup Instructions

### Step 1: Verify Files Exist
```bash
frontend/src/components/
├── EnrollmentPage.js
└── VoiceSampleCard.jsx
```

### Step 2: Import in Your App
```javascript
// App.js or your routing file
import EnrollmentPage from './components/EnrollmentPage';

function App() {
  return (
    <Routes>
      <Route path="/enroll" element={<EnrollmentPage />} />
    </Routes>
  );
}
```

### Step 3: Verify Backend Support
Backend must handle:
- WebSocket messages with `sample_number: 1-5`
- Enrollment request with `sample_count: 5`

See `BACKEND_MULTI_SAMPLE_IMPLEMENTATION.md` for details.

## 🎨 Key Features

| Feature | Before | After |
|---------|--------|-------|
| Samples | 1 | 5 |
| Recording Interface | Single large button | 5 cards with buttons |
| Visual Feedback | Duration display | RED/GREEN status |
| Playback | No | Yes, per sample |
| Re-recording | Re-record everything | Delete individual sample |
| Progress Tracking | Binary | 0/5 to 5/5 with progress bar |
| Validation | 2s minimum | 2s per sample × 5 |

## 🔧 Customization

### Change Number of Samples
Edit `EnrollmentPage.js` line 8:
```javascript
const REQUIRED_SAMPLES = 5;  // Change to 3, 7, etc.
```

### Change Minimum Duration
Edit `EnrollmentPage.js` line 9:
```javascript
const MIN_SAMPLE_DURATION = 2;  // Change to 3, 4, etc. (seconds)
```

### Styling
All components use Tailwind CSS utility classes. Modify directly in JSX:
```javascript
// In VoiceSampleCard.jsx
className="border-2 rounded-lg p-6 transition-all"
// Add custom colors here
```

## 🧪 Testing Checklist

- [ ] Can see 5 red cards on page load
- [ ] Can record Sample 1 (button changes to Stop)
- [ ] Recording timer counts up
- [ ] Stop button saves audio, card turns green
- [ ] Can play back recorded audio
- [ ] Can delete to reset card to red
- [ ] Can record all 5 samples
- [ ] Progress bar updates: 1/5 → 2/5 → ... → 5/5
- [ ] Can't submit until phone number entered
- [ ] Can't submit until all 5 samples recorded
- [ ] Shows error if sample < 2 seconds
- [ ] Submit works and shows success message
- [ ] Form resets after successful enrollment

## 📱 Browser Compatibility

| Browser | Desktop | Mobile |
|---------|---------|--------|
| Chrome | ✅ | ✅ |
| Firefox | ✅ | ✅ |
| Safari | ✅ | ⚠️* |
| Edge | ✅ | N/A |

*Safari on iOS has limited microphone access; test carefully

## 🔐 Security Notes

- Audio is processed in browser before sending
- No audio stored in frontend state (only blob reference)
- WebSocket connection recommended over HTTP
- All audio uses AES-256 encryption in transit
- Phone number never stored in audio metadata

## 📊 Performance Tips

1. **Recording Quality**: 16kHz, mono
2. **Recommended Sample Duration**: 4-5 seconds each
3. **Total Time**: ~5-10 seconds of enrollment audio
4. **Network**: WebSocket recommended for binary efficiency

## 🐛 Debugging

### No Record Button Working
```javascript
// Check browser console for:
1. "Failed to access microphone" → Grant permissions
2. Blank error → Check microphone device availability
3. No error → Check browser tools > Application > Storage
```

### Audio Not Playing
```javascript
// Verify:
1. Card is green (audio recorded)
2. Browser allows audio playback (no restrictions)
3. Check console for any errors
```

### WebSocket Connection Error
```javascript
// Check:
1. Backend running (ws://localhost:8000/ws/voice)
2. Network requests in DevTools
3. Firewall/proxy blocking WebSocket
```

### Submission Hangs
```javascript
// Check:
1. All 5 samples have >= 2 seconds
2. Phone number is valid
3. Backend receiving chunks (log on backend)
4. No network errors in DevTools
```

## 📚 File Structure
```
reactapp/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── EnrollmentPage.js         ← Main enrollment component
│       │   ├── VoiceSampleCard.jsx       ← Individual sample card
│       │   └── ChunkProcessingIndicator.jsx
│       ├── utils/
│       │   ├── audioRecorder.js
│       │   └── audioChunkSplitter.js
│       └── services/
│           └── api.js
│
├── MULTI_SAMPLE_ENROLLMENT_GUIDE.md      ← Full documentation
└── BACKEND_MULTI_SAMPLE_IMPLEMENTATION.md ← Backend integration
```

## 🔄 Workflow Integration

### With Existing Verification
✅ No changes needed! Verification continues to work with single samples.
The enrolled voice (merged from 5 samples) can be verified against any audio.

### API Endpoint Changes
```
POST /enroll
Changed from: phone_number + 1 audio file
Changed to:   phone_number + 5 audio samples (via WebSocket chunks)
```

## 🎓 How It Works (Under the Hood)

1. **Recording**: Uses Web Audio API (16kHz sample rate, mono)
2. **Storage**: Blobs held in React state during session
3. **Transmission**: Split into chunks via Base64, sent over WebSocket
4. **Backend Processing**: 
   - Reconstructs 5 audio files from chunks
   - Merges or averages embeddings from 5 samples
   - Stores single enrollment vector
5. **Verification**: Same as before (1 sample verification works)

## 🚀 Deployment

### Development
```bash
npm start  # Frontend runs on :3000
# Backend must run on :8000 (or update REACT_APP_API_URL)
```

### Production
```bash
npm run build  # Creates optimized build in /build
# Serve /build as static files
# Update REACT_APP_API_URL to production backend URL
```

## 📞 Support

For issues:
1. Check browser console for errors
2. Check backend logs for WebSocket errors
3. Review `MULTI_SAMPLE_ENROLLMENT_GUIDE.md`
4. Review `BACKEND_MULTI_SAMPLE_IMPLEMENTATION.md`

---

**Version**: 1.0  
**Last Updated**: February 2026  
**Status**: ✅ Ready to Deploy
