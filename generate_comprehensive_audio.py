#!/usr/bin/env python3
"""
Generate test audio files for comprehensive testing
Creates synthetic audio with different voice characteristics:
- Male speaker (deep voice)
- Female speaker (higher pitch)
- Child (very high pitch)
- Animal sounds (dog bark, cat meow)
- Background noise
- Whispered speech
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Configuration
SAMPLE_RATE = 16000  # 16kHz for speech
TEST_AUDIO_DIR = Path(__file__).parent / "test_audio_files"
DURATION = 3  # seconds per audio file

def create_test_audio_dir():
    """Create test audio directory"""
    TEST_AUDIO_DIR.mkdir(exist_ok=True)
    print(f"✓ Test audio directory ready: {TEST_AUDIO_DIR}")

def generate_tone_speech(frequency, duration, rate, modulation=True):
    """
    Generate synthetic speech-like audio using tones
    Simulates human voice characteristics
    """
    t = np.linspace(0, duration, int(rate * duration), False)
    
    # Base carrier frequency (voice pitch)
    base_signal = np.sin(2 * np.pi * frequency * t)
    
    if modulation:
        # Add amplitude modulation (speech-like pattern)
        modulation_freq = np.random.uniform(3, 8)  # 3-8 Hz = natural speech rate
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * modulation_freq * t)
        base_signal = base_signal * modulation
        
        # Add frequency variation (prosody)
        freq_variation = np.sin(2 * np.pi * 1.5 * t)
        signal = np.sin(2 * np.pi * (frequency + 10 * freq_variation) * t)
        signal = signal * modulation
    else:
        signal = base_signal
    
    # Add harmonics for naturalness
    signal += 0.3 * np.sin(4 * np.pi * frequency * t) * 0.5 * (0.5 + 0.5 * np.sin(2 * np.pi * 5 * t))
    signal += 0.15 * np.sin(6 * np.pi * frequency * t) * 0.3
    
    # Normalize
    signal = signal / np.max(np.abs(signal)) * 0.95
    
    # Add slight background noise for realism
    noise = np.random.normal(0, 0.02, len(signal))
    signal = signal + noise
    signal = signal / np.max(np.abs(signal)) * 0.95
    
    return signal.astype(np.float32)

def generate_animal_sound(animal_type, duration, rate):
    """Generate animal sound effects"""
    t = np.linspace(0, duration, int(rate * duration), False)
    
    if animal_type == "dog":
        # Dog bark: rapid chirp sound
        bark_count = 3
        bark_duration = duration / bark_count
        signal = np.array([])
        
        for i in range(bark_count):
            bark_t = np.linspace(0, bark_duration, int(rate * bark_duration), False)
            # Start high, end low (bark characteristic)
            freq_sweep = np.linspace(800, 400, len(bark_t))
            bark = np.sin(2 * np.pi * freq_sweep * bark_t)
            
            # Add envelope (fade in/out)
            envelope = np.sin(np.pi * bark_t / bark_duration) ** 2
            bark = bark * envelope * 0.7
            
            signal = np.concatenate([signal, bark])
        
        # Pad to match duration
        if len(signal) < int(rate * duration):
            pad_amount = int(rate * duration) - len(signal)
            signal = np.concatenate([signal, np.zeros(pad_amount)])
        else:
            signal = signal[:int(rate * duration)]
    
    elif animal_type == "cat":
        # Cat meow: varying frequency tone
        meow_segments = 2
        segment_duration = duration / meow_segments
        signal = np.array([])
        
        for i in range(meow_segments):
            meow_t = np.linspace(0, segment_duration, int(rate * segment_duration), False)
            # Meow: high frequency with variation
            freq = 700 + 300 * np.sin(np.pi * meow_t / segment_duration)
            meow = 0.7 * np.sin(2 * np.pi * freq * meow_t)
            
            # Add amplitude variation
            envelope = np.sin(np.pi * meow_t / segment_duration)
            meow = meow * envelope
            
            signal = np.concatenate([signal, meow])
        
        # Pad to match duration
        if len(signal) < int(rate * duration):
            pad_amount = int(rate * duration) - len(signal)
            signal = np.concatenate([signal, np.zeros(pad_amount)])
        else:
            signal = signal[:int(rate * duration)]
    
    else:
        signal = np.zeros(int(rate * duration))
    
    # Normalize
    signal = signal / np.max(np.abs(signal)) * 0.95
    return signal.astype(np.float32)

def generate_noise(duration, rate, noise_type="ambient"):
    """Generate noise signals"""
    num_samples = int(rate * duration)
    
    if noise_type == "ambient":
        # Brown noise (ambient room noise)
        white_noise = np.random.normal(0, 1, num_samples)
        # Simple brown noise filter
        signal = np.zeros_like(white_noise)
        signal[0] = white_noise[0]
        for i in range(1, len(white_noise)):
            signal[i] = 0.7 * signal[i-1] + 0.3 * white_noise[i]
        signal = signal / np.max(np.abs(signal)) * 0.5
    else:
        signal = np.random.normal(0, 0.4, num_samples)
    
    return signal.astype(np.float32)

def save_audio(signal, filename, rate=SAMPLE_RATE):
    """Save audio file"""
    filepath = TEST_AUDIO_DIR / filename
    sf.write(filepath, signal, rate)
    duration = len(signal) / rate
    print(f"  ✓ {filename:<40} ({duration:.1f}s, {len(signal)} samples)")

def generate_speaker_voices():
    """Generate voices for different speakers"""
    print("\n[1] Generating Speaker Voices...")
    
    # Speaker 1: Male (lower pitch: 100-150 Hz)
    print("  ⌘ Speaker 1 - Male voice (deep pitch)")
    male_freq = 120
    male_voice = generate_tone_speech(male_freq, DURATION, SAMPLE_RATE)
    save_audio(male_voice, "test_speaker1_enroll.wav")
    
    # Male speaker variant (same person, slightly different)
    male_voice_var = generate_tone_speech(male_freq + 5, DURATION, SAMPLE_RATE)
    save_audio(male_voice_var, "test_speaker1_verify.wav")
    
    # Male variant 2
    male_voice_var2 = generate_tone_speech(male_freq - 3, DURATION, SAMPLE_RATE)
    save_audio(male_voice_var2, "test_speaker1_variant.wav")
    
    # Speaker 2: Female (higher pitch: 200-250 Hz)
    print("  ⌘ Speaker 2 - Female voice (higher pitch)")
    female_freq = 220
    female_voice = generate_tone_speech(female_freq, DURATION, SAMPLE_RATE)
    save_audio(female_voice, "test_speaker2_enroll.wav")
    
    # Female speaker variant
    female_voice_var = generate_tone_speech(female_freq + 8, DURATION, SAMPLE_RATE)
    save_audio(female_voice_var, "test_speaker2_verify.wav")
    
    # Female variant 2
    female_voice_var2 = generate_tone_speech(female_freq - 5, DURATION, SAMPLE_RATE)
    save_audio(female_voice_var2, "test_speaker2_variant.wav")
    
    # Speaker 3: Child (very high pitch: 300-350 Hz)
    print("  ⌘ Speaker 3 - Child voice (very high pitch)")
    child_freq = 320
    child_voice = generate_tone_speech(child_freq, DURATION, SAMPLE_RATE)
    save_audio(child_voice, "test_speaker3_enroll.wav")
    
    # Child speaker variant
    child_voice_var = generate_tone_speech(child_freq + 12, DURATION, SAMPLE_RATE)
    save_audio(child_voice_var, "test_speaker3_verify.wav")

def generate_animal_sounds():
    """Generate animal sound effects"""
    print("\n[2] Generating Animal Sounds (for rejection testing)...")
    
    print("  ⌘ Dog bark sound")
    dog_sound = generate_animal_sound("dog", DURATION, SAMPLE_RATE)
    save_audio(dog_sound, "animal_dog_bark.wav")
    
    print("  ⌘ Cat meow sound")
    cat_sound = generate_animal_sound("cat", DURATION, SAMPLE_RATE)
    save_audio(cat_sound, "animal_cat_meow.wav")

def generate_edge_cases():
    """Generate edge case audio"""
    print("\n[3] Generating Edge Case Audio...")
    
    print("  ⌘ Ambient noise (no speech)")
    noise = generate_noise(DURATION, SAMPLE_RATE, "ambient")
    save_audio(noise, "ambient_noise.wav")
    
    print("  ⌘ Whispered speech")
    # Whisper: lower amplitude, higher frequencies
    male_freq = 120
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
    whisper = 0.3 * np.sin(2 * np.pi * male_freq * t)  # Lower amplitude
    whisper += 0.2 * np.sin(2 * np.pi * (male_freq * 2) * t)  # More high frequencies
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 5 * t)
    whisper = whisper * modulation
    whisper = whisper / np.max(np.abs(whisper)) * 0.5  # Very quiet
    save_audio(whisper.astype(np.float32), "whisper_sound.wav")

def verify_audio_files():
    """Verify all audio files were created"""
    print("\n[4] Verifying Generated Files...")
    
    expected_files = [
        # Speakers
        "test_speaker1_enroll.wav", "test_speaker1_verify.wav", "test_speaker1_variant.wav",
        "test_speaker2_enroll.wav", "test_speaker2_verify.wav", "test_speaker2_variant.wav",
        "test_speaker3_enroll.wav", "test_speaker3_verify.wav",
        # Animals
        "animal_dog_bark.wav", "animal_cat_meow.wav",
        # Edge cases
        "ambient_noise.wav", "whisper_sound.wav"
    ]
    
    actual_files = list(TEST_AUDIO_DIR.glob("*.wav"))
    created_count = len(actual_files)
    expected_count = len(expected_files)
    
    print(f"\n  Created: {created_count} files")
    print(f"  Expected: {expected_count} files")
    
    for filename in expected_files:
        filepath = TEST_AUDIO_DIR / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"    ✓ {filename:<40} ({size:>10,} bytes)")
        else:
            print(f"    ✗ {filename:<40} (MISSING)")

def print_summary():
    """Print generation summary"""
    print("\n" + "="*70)
    print("TEST AUDIO GENERATION COMPLETE")
    print("="*70)
    print(f"\nLocation: {TEST_AUDIO_DIR}")
    print("\nGenerated Audio Categories:")
    print("  1️⃣  SPEAKER VOICES (3 speakers with variations)")
    print("     • Speaker 1 (Male): test_speaker1_*.wav")
    print("     • Speaker 2 (Female): test_speaker2_*.wav")
    print("     • Speaker 3 (Child): test_speaker3_*.wav")
    print("\n  2️⃣  ANIMAL SOUNDS (for rejection testing)")
    print("     • Dog bark: animal_dog_bark.wav")
    print("     • Cat meow: animal_cat_meow.wav")
    print("\n  3️⃣  EDGE CASES (noise, whispers, etc.)")
    print("     • Ambient noise: ambient_noise.wav")
    print("     • Whispered speech: whisper_sound.wav")
    print("\n  Sample Rate: 16 kHz (standard for speech)")
    print("  Duration: 3 seconds per file")
    print("\nReady to run tests with: python comprehensive_test_suite.py")

def main():
    """Main generation process"""
    print("\n" + "="*70)
    print("VOICE BIOMETRIC TEST AUDIO GENERATOR")
    print("="*70)
    
    create_test_audio_dir()
    
    try:
        generate_speaker_voices()
        generate_animal_sounds()
        generate_edge_cases()
        verify_audio_files()
        print_summary()
    except Exception as e:
        print(f"\n✗ Error during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
