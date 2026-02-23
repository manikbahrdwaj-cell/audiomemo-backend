"""
Simple test to verify WAV file creation and processing
"""

import soundfile as sf
import numpy as np
import io
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from voice_embedding import generate_embedding, preprocess_audio

def create_wav_file(duration_seconds=5, sample_rate=16000):
    """Create a WAV file with proper RIFF headers"""
    num_samples = duration_seconds * sample_rate
    frequency = 440  # 440 Hz sine wave
    t = np.linspace(0, duration_seconds, num_samples, False)
    audio = np.sin(2 * np.pi * frequency * t) * 0.3
    
    with io.BytesIO() as f:
        sf.write(f, audio, sample_rate, format='WAV')
        wav_bytes = f.getvalue()
    
    return wav_bytes

def test_wav_processing():
    """Test that the backend can process WAV files"""
    print("=" * 60)
    print("Testing WAV File Processing")
    print("=" * 60)
    
    # Create a test WAV file
    print("\n1. Creating test WAV file...")
    wav_bytes = create_wav_file(duration_seconds=5, sample_rate=16000)
    print(f"   Created {len(wav_bytes)} bytes")
    
    # Verify RIFF headers
    print("\n2. Verifying WAV format...")
    if wav_bytes[:4] != b'RIFF':
        print("   ERROR: Missing RIFF header")
        return False
    if wav_bytes[8:12] != b'WAVE':
        print("   ERROR: Missing WAVE marker")
        return False
    print("   ✓ Valid RIFF WAV format")
    
    # Test preprocess_audio
    print("\n3. Testing preprocess_audio...")
    try:
        waveform = preprocess_audio(wav_bytes)
        print(f"   ✓ Audio preprocessed: {waveform.shape}")
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test generate_embedding
    print("\n4. Testing generate_embedding...")
    try:
        embedding = generate_embedding(wav_bytes)
        print(f"   ✓ Embedding generated: shape={embedding.shape}")
        print(f"   Embedding sample: {embedding[:5]}")
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_wav_processing()
    sys.exit(0 if success else 1)
