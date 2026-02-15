# Getting Started with Embedding Operations

## 5-Minute Quick Start

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Start MongoDB
```bash
# On Windows
mongod

# On macOS/Linux
mongod --dbpath /usr/local/var/mongodb
```

### Step 3: Start the API
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Test with Sample Audio

**Using curl:**
```bash
# Enroll
curl -X POST http://localhost:8000/enroll \
  -F "phone_number=+1234567890" \
  -F "file=@audio.wav"

# Verify
curl -X POST http://localhost:8000/verify \
  -F "phone_number=+1234567890" \
  -F "file=@audio.wav"
```

**Using Python:**
```python
import requests

# Enroll
with open("audio.wav", "rb") as f:
    r = requests.post(
        "http://localhost:8000/enroll",
        files={"file": f},
        data={"phone_number": "+1234567890"}
    )
print(r.json())

# Verify
with open("audio.wav", "rb") as f:
    r = requests.post(
        "http://localhost:8000/verify",
        files={"file": f},
        data={"phone_number": "+1234567890"}
    )
print(r.json())
```

## Common Tasks

### Task 1: Enroll a User

```python
from voice_embedding import generate_embedding
from database import store_voice_embedding

# Load audio
with open("user_audio.wav", "rb") as f:
    audio_bytes = f.read()

# Generate embedding
embedding = generate_embedding(audio_bytes)

# Store
vector_id = store_voice_embedding("+1234567890", embedding)
print(f"Enrolled successfully: {vector_id}")
```

### Task 2: Verify a User

```python
from embedding_operations import EmbeddingService
from database import get_voice_embedding
import numpy as np

# Initialize service
service = EmbeddingService()

# Load verification audio
with open("verify_audio.wav", "rb") as f:
    verify_audio = f.read()

# Generate embedding
verify_emb, verify_metrics = service.generate(verify_audio, "verify")
print(f"Verification quality: {verify_metrics.quality_score:.3f}")

# Get enrolled embedding
stored_doc = get_voice_embedding("+1234567890")
stored_emb = np.array(stored_doc["embedding"])

# Compare
comparison = service.compare(
    verify_emb, stored_emb,
    "verify", "+1234567890"
)

if comparison.is_match:
    print(f"✓ MATCH (similarity: {comparison.cosine_similarity:.4f})")
else:
    print(f"✗ NOT MATCH (similarity: {comparison.cosine_similarity:.4f})")
```

### Task 3: Check if User is Enrolled

```python
from database import check_enrollment

if check_enrollment("+1234567890"):
    print("✓ User is enrolled")
else:
    print("✗ User is not enrolled")
```

### Task 4: Enroll Multiple Users

```python
from embedding_operations import EmbeddingService
from database import store_voice_embedding
import os

service = EmbeddingService()

# Load all audio files
audio_dir = "audio_files/"
for filename in os.listdir(audio_dir):
    if filename.endswith(".wav"):
        phone = filename[:-4]  # Remove .wav
        
        with open(os.path.join(audio_dir, filename), "rb") as f:
            audio = f.read()
        
        # Generate
        emb, metrics = service.generate(audio, phone)
        
        if emb is not None and metrics.quality_score > 0.5:
            # Store
            store_voice_embedding(phone, emb)
            print(f"✓ {phone}: quality={metrics.quality_score:.3f}")
        else:
            print(f"✗ {phone}: low quality")
```

### Task 5: Find Similar Users

```python
from embedding_operations import EmbeddingService
from database import find_nearest_embedding, get_voice_embedding
import numpy as np

service = EmbeddingService()

# Load unknown audio
with open("unknown.wav", "rb") as f:
    unknown_audio = f.read()

# Generate embedding
unknown_emb, _ = service.generate(unknown_audio, "unknown")

# Find nearest matches
matches = find_nearest_embedding(unknown_emb, limit=5)

print("Top matches:")
for match in matches:
    print(f"  {match['phone_number']}: {match['similarity_score']:.4f}")
```

### Task 6: Get Cache Statistics

```python
from embedding_operations import EmbeddingService

service = EmbeddingService()

# Perform some operations...

# Check cache stats
stats = service.get_cache_stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

## Configuration Examples

### High Security
```python
from embedding_operations import EmbeddingService, EmbeddingServiceConfig

config = EmbeddingServiceConfig(
    generation_method='chunked',      # More stable
    similarity_threshold=0.85,         # Stricter
    enable_quality_check=True,
    min_quality_score=0.6
)

service = EmbeddingService(config)
```

### High Performance
```python
config = EmbeddingServiceConfig(
    generation_method='standard',      # Faster
    similarity_threshold=0.75,
    enable_quality_check=False,        # Skip check
    use_cache=True,
    cache_size=500                     # Large cache
)

service = EmbeddingService(config)
```

### Balanced (Default)
```python
config = EmbeddingServiceConfig()
service = EmbeddingService(config)
```

## Testing Your Setup

### Test 1: Generate an Embedding
```python
from voice_embedding import generate_embedding
import numpy as np

# Create a test audio (you'll need a real audio.wav)
with open("audio.wav", "rb") as f:
    audio = f.read()

embedding = generate_embedding(audio)
print(f"Embedding shape: {embedding.shape}")
print(f"Embedding magnitude: {np.linalg.norm(embedding):.4f}")
assert embedding.shape == (192,), "Wrong shape!"
print("✓ Embedding generation working!")
```

### Test 2: Run the Test Suite
```bash
cd backend
python test_embedding_operations.py
```

This will run 27+ test cases covering all functionality.

### Test 3: Manual Quality Check
```python
from embedding_operations import EmbeddingStats
from voice_embedding import generate_embedding

with open("audio.wav", "rb") as f:
    embedding = generate_embedding(f.read())

quality = EmbeddingStats.calculate_embedding_quality(embedding)
print(f"Quality Score: {quality:.3f}")

if quality > 0.8:
    print("✓ Excellent")
elif quality > 0.6:
    print("✓ Good")
elif quality > 0.5:
    print("⚠ Acceptable")
else:
    print("✗ Poor")
```

## API Testing

### Using Postman

1. **POST /enroll**
   - URL: `http://localhost:8000/enroll`
   - Body: Form Data
   - Fields: `phone_number` (text), `file` (file)

2. **POST /verify**
   - URL: `http://localhost:8000/verify`
   - Body: Form Data
   - Fields: `phone_number` (text), `file` (file)

3. **GET /check/{phone_number}**
   - URL: `http://localhost:8000/check/+1234567890`
   - Method: GET

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Enroll
with open("audio.wav", "rb") as f:
    r = requests.post(
        f"{BASE_URL}/enroll",
        files={"file": f},
        data={"phone_number": "+1234567890"}
    )
    print("Enroll:", r.json())

# Check
r = requests.get(f"{BASE_URL}/check/+1234567890")
print("Check:", r.json())

# Verify
with open("audio.wav", "rb") as f:
    r = requests.post(
        f"{BASE_URL}/verify",
        files={"file": f},
        data={"phone_number": "+1234567890"}
    )
    print("Verify:", r.json())
```

## WebSocket Testing

### Using JavaScript
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/voice");

ws.onopen = () => {
    console.log("Connected");
    
    // Send ping
    ws.send(JSON.stringify({type: "ping"}));
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    console.log("Received:", msg);
};

// Send an enrollment request
setTimeout(() => {
    ws.send(JSON.stringify({
        type: "enroll",
        phone_number: "+1234567890"
    }));
}, 1000);
```

## Troubleshooting

### Problem: "Module not found: embedding_operations"
**Solution:** Make sure you've created `embedding_operations.py` in the backend directory.

### Problem: "CUDA out of memory"
**Solution:** The system falls back to CPU automatically. This is normal.

### Problem: Low quality embeddings
**Solution:**
- Use longer audio (3-5 seconds)
- Record in quiet environment
- Use clear speech/microphone

### Problem: Verification not matching
**Solution:**
- Lower the threshold (0.70-0.75 instead of 0.75-0.80)
- Check audio quality on both enrollment and verification
- Use multiple enrollment samples

### Problem: MongoDB connection error
**Solution:**
- Make sure MongoDB is running: `mongod`
- Check MONGODB_URL in `database.py`
- Verify MongoDB is on localhost:27017

### Problem: Model loading fails
**Solution:**
- The model will auto-download from HuggingFace
- Ensure internet connection is available
- Model is cached in `~/.cache/huggingface/hub/`
- Check disk space (~4GB needed)

## Next Steps

1. **Try the Quick Reference**: See `EMBEDDING_OPERATIONS_QUICK_REFERENCE.md`
2. **Read the Full Guide**: See `EMBEDDING_OPERATIONS_GUIDE.md`
3. **Review API Docs**: See `EMBEDDING_OPERATIONS_API.md`
4. **Explore the Code**: Check `embedding_operations.py`
5. **Run Tests**: Execute `test_embedding_operations.py`
6. **Try the Examples**: Adapt the examples above for your use case

## Key Files

| File | Purpose |
|------|---------|
| `embedding_operations.py` | High-level API (START HERE) |
| `voice_embedding.py` | Core embedding generation |
| `database.py` | MongoDB operations |
| `main.py` | REST/WebSocket API |
| `test_embedding_operations.py` | Test suite |
| `EMBEDDING_OPERATIONS_GUIDE.md` | Full documentation |
| `EMBEDDING_OPERATIONS_QUICK_REFERENCE.md` | Quick lookup |
| `EMBEDDING_OPERATIONS_API.md` | API documentation |

## Performance Tips

1. **Use GPU**: Automatically used if CUDA is available
2. **Enable Caching**: Default is enabled, helps with repeated users
3. **Batch Process**: Better for enrolling many users
4. **Audio Duration**: 2-5 seconds optimal
5. **Chunk Long Audio**: Auto-enabled for >10 second audio

## Common Error Codes

| Error | Meaning | Solution |
|-------|---------|----------|
| 400 | Invalid input | Check file format, phone number |
| 404 | Not found | User not enrolled, enroll first |
| 500 | Server error | Check logs, restart server |
| Rate limit | Too many requests | Slow down request rate |

## Success Checklist

- [x] Installed dependencies
- [x] Started MongoDB
- [x] Started API server
- [x] Successfully enrolled a user
- [x] Successfully verified a user
- [x] Checked embedding quality
- [x] Tested batch operations
- [x] Read documentation

You're ready to use embedding operations!

## More Information

For detailed information on any topic, see:

- **Quick answers**: `EMBEDDING_OPERATIONS_QUICK_REFERENCE.md`
- **Complete guide**: `EMBEDDING_OPERATIONS_GUIDE.md`
- **API usage**: `EMBEDDING_OPERATIONS_API.md`
- **Architecture**: `EMBEDDING_OPERATIONS_IMPLEMENTATION_SUMMARY.md`
- **All docs**: `EMBEDDING_OPERATIONS_INDEX.md`
