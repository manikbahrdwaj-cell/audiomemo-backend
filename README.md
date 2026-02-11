# Voice Biometric Authentication System

A voice-based biometric authentication system using ECAPA-TDNN embeddings for speaker verification.

## Project Structure

```
reactapp/
├── frontend/                 # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── EnrollmentPage.js    # Voice enrollment UI
│   │   │   └── VerificationPage.js  # Voice verification UI
│   │   ├── services/
│   │   │   └── api.js               # API client
│   │   ├── utils/
│   │   │   └── audioRecorder.js     # 16kHz mono WAV recorder
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   └── package.json
│
└── backend/                  # FastAPI backend
    ├── main.py               # API endpoints
    ├── voice_embedding.py    # ECAPA-TDNN embedding generation
    ├── database.py           # MongoDB operations
    └── requirements.txt
```

## Features

### Identity Enrollment Page
- Phone number input for unique identification
- Browser-side audio recording with real-time feedback
- Audio downsampling to 16kHz mono WAV format
- Voice vector generation and storage in MongoDB

### Verification Playground
- Phone number lookup to check enrollment status
- Voice recording for verification testing
- Cosine similarity score display
- Match/No Match result visualization

## Technical Specifications

### Audio Processing
- Sample Rate: 16,000 Hz (downsampled from browser's native rate)
- Channels: 1 (Mono)
- Format: 16-bit PCM WAV
- Linear interpolation for high-quality downsampling

### Voice Embeddings
- Model: ECAPA-TDNN (SpeechBrain)
- Embedding Dimension: 192
- Trained on: VoxCeleb dataset

### API Endpoints
- `POST /enroll` - Register a new voice identity
- `POST /verify` - Verify voice against enrolled identity
- `GET /check/{phone_number}` - Check enrollment status

## Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- MongoDB (local or Atlas)

### Backend Setup

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or: source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start MongoDB (if using local):
   ```bash
   mongod
   ```

5. Run the API server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm start
   ```

4. Open http://localhost:3000 in your browser

## Usage

### Enrolling a Voice
1. Go to the Enrollment page
2. Enter a phone number
3. Click "Start Recording" and speak clearly for 3+ seconds
4. Click "Stop Recording"
5. Click "Submit Enrollment"

### Verifying a Voice
1. Go to the Verification page
2. Enter the enrolled phone number
3. Click "Check" to verify enrollment
4. Click "Record Test Voice" and speak
5. Click "Verify Voice" to see the similarity score

## Configuration

### MongoDB Connection
Default: `mongodb://localhost:27017`

To change, edit `backend/database.py`:
```python
MONGODB_URL = "your_mongodb_connection_string"
```

### Similarity Threshold
Default: 0.75 (75% match required)

Adjustable in `backend/main.py` and `frontend/src/components/VerificationPage.js`

## Notes

- First model load may take 1-2 minutes to download ECAPA-TDNN weights
- For best results, use a quiet environment when recording
- Minimum recommended recording length: 3 seconds
- MongoDB Atlas Vector Search can be enabled for production scalability
