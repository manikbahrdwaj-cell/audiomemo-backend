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

def generate_male_voice(frequency, duration, rate, variant=0):
    """
    Generate male speaker with distinct characteristics
    Variant: 0=enrollment, 1=same speaker variant, 2=different variant
    """
    t = np.linspace(0, duration, int(rate * duration), False)
    
    # Male speaker: Deep fundamental frequency with strong lower harmonics
    # Slower formant movements characteristic of male speech
    base_freq = frequency
    
    # Variant-specific modulation patterns
    if variant == 0:
        # Enrollment: Natural speech rhythm (3.5 Hz)
        mod_freq = 3.5
        freq_variation_amplitude = 12
        harmonic_strength = [1.0, 0.35, 0.18, 0.08]  # Strong fundamental
    elif variant == 1:
        # Same speaker, slight variation in tempo (3.2 Hz)
        mod_freq = 3.2
        freq_variation_amplitude = 11
        harmonic_strength = [1.0, 0.34, 0.17, 0.09]
    else:
        # Different variant with different rhythm (3.8 Hz)
        mod_freq = 3.8
        freq_variation_amplitude = 13
        harmonic_strength = [1.0, 0.36, 0.19, 0.07]
    
    # Amplitude modulation (speech envelope)
    envelope = 0.4 + 0.6 * np.sin(np.pi * np.sin(2 * np.pi * mod_freq * t))
    
    # Frequency variation (prosody line)
    freq_contour = base_freq + freq_variation_amplitude * np.sin(np.pi * t / duration)
    
    # Generate signal with multiple harmonics
    signal = np.zeros_like(t)
    for harmonic_num, strength in enumerate(harmonic_strength, 1):
        harmonic_freq = freq_contour * harmonic_num
        signal += strength * np.sin(2 * np.pi * harmonic_freq * t)
    
    # Apply envelope
    signal = signal * envelope
    
    # Add vocal tract characteristics with formant noise
    formant_noise = 0.08 * np.random.normal(0, 1, len(t))
    formant_noise = np.convolve(formant_noise, np.hanning(15), mode='same')
    signal = signal + formant_noise
    
    # Normalize
    signal = signal / np.max(np.abs(signal)) * 0.95
    
    return signal.astype(np.float32)


def generate_female_voice(frequency, duration, rate, variant=0):
    """
    Generate female speaker with distinct characteristics
    Variant: 0=enrollment, 1=same speaker variant, 2=different variant
    """
    t = np.linspace(0, duration, int(rate * duration), False)
    
    # Female speaker: Higher fundamental with different harmonic distribution
    # Faster articulation and more dynamic formant movements
    base_freq = frequency
    
    # Variant-specific modulation patterns
    if variant == 0:
        # Enrollment: Faster natural speech rhythm (4.5 Hz)
        mod_freq = 4.5
        freq_variation_amplitude = 15
        # MODIFIED: Even more harmonics with different distribution than child
        harmonic_strength = [1.0, 0.50, 0.35, 0.20, 0.12, 0.06, 0.02]  
    elif variant == 1:
        # Same speaker, slight variation (4.2 Hz)
        mod_freq = 4.2
        freq_variation_amplitude = 14
        harmonic_strength = [1.0, 0.51, 0.34, 0.19, 0.11, 0.07, 0.03]
    else:
        # Different variant with different rhythm (4.8 Hz)
        mod_freq = 4.8
        freq_variation_amplitude = 16
        harmonic_strength = [1.0, 0.49, 0.36, 0.21, 0.13, 0.05, 0.01]
    
    # Amplitude modulation (very dynamic for female - different from child)
    # Use double sine wave for distinctive pattern
    envelope = 0.25 + 0.75 * (0.5 + 0.5 * np.sin(np.pi * np.sin(2 * np.pi * mod_freq * t)))
    
    # Frequency variation (more pronounced prosody)
    freq_contour = base_freq + freq_variation_amplitude * np.sin(2 * np.pi * t / duration)
    
    # Generate signal with multiple harmonics (more than male)
    signal = np.zeros_like(t)
    for harmonic_num, strength in enumerate(harmonic_strength, 1):
        harmonic_freq = freq_contour * harmonic_num
        signal += strength * np.sin(2 * np.pi * harmonic_freq * t)
    
    # Apply envelope
    signal = signal * envelope
    
    # Add more complex vocal tract characteristics with filtering
    formant_noise = 0.12 * np.random.normal(0, 1, len(t))
    formant_noise = np.convolve(formant_noise, np.hanning(12), mode='same')
    signal = signal + formant_noise
    
    # Normalize
    signal = signal / np.max(np.abs(signal)) * 0.95
    
    return signal.astype(np.float32)


def generate_child_voice(frequency, duration, rate, variant=0):
    """
    Generate child speaker with distinct characteristics
    Variant: 0=enrollment, 1=same speaker variant, 2=different variant
    """
    t = np.linspace(0, duration, int(rate * duration), False)
    
    # Child speaker: Very high pitch with bright timbre
    # Rapid articulation and higher formant frequencies
    base_freq = frequency
    
    # Variant-specific modulation patterns
    if variant == 0:
        # Enrollment: Very fast speech rhythm (6.5 Hz - faster than female's 4.5)
        mod_freq = 6.5
        freq_variation_amplitude = 20
        # MODIFIED: Different harmonic distribution focusing on higher frequencies
        # More emphasis on 2nd harmonic (characteristic of child voice)
        harmonic_strength = [0.85, 0.60, 0.25, 0.10, 0.04, 0.02]  
    elif variant == 1:
        # Same speaker, slight variation (6.2 Hz)
        mod_freq = 6.2
        freq_variation_amplitude = 19
        harmonic_strength = [0.85, 0.61, 0.24, 0.11, 0.03, 0.02]
    else:
        # Different variant with different rhythm (6.8 Hz)
        mod_freq = 6.8
        freq_variation_amplitude = 21
        harmonic_strength = [0.85, 0.59, 0.26, 0.09, 0.05, 0.03]
    
    # Amplitude modulation (very dynamic AND unique - rapid breathing pattern)
    # Triple sine for very different pattern from female
    modulation_a = 0.5 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
    modulation_b = 0.3 * np.sin(2 * np.pi * (mod_freq * 1.7) * t)  # Subharmonic
    envelope = (modulation_a + modulation_b) * 0.7 + 0.3
    
    # Frequency variation (rapid pitch changes characteristic of child)
    freq_contour = base_freq + freq_variation_amplitude * np.sin(np.pi * np.sin(2 * np.pi * 1.2 * t / duration))
    
    # Generate signal with modified harmonics
    signal = np.zeros_like(t)
    for harmonic_num, strength in enumerate(harmonic_strength, 1):
        harmonic_freq = freq_contour * harmonic_num
        signal += strength * np.sin(2 * np.pi * harmonic_freq * t)
    
    # Apply envelope with increased jitter (natural vocal variability in children)
    jitter = 0.04 * np.sin(2 * np.pi * 22 * t)  # Higher frequency jitter
    jitter += 0.02 * np.random.normal(0, 1, len(t))  # Random jitter
    signal = signal * (envelope * (1 + jitter))
    
    # Add bright noise with different filter characteristics (higher frequencies)
    formant_noise = 0.16 * np.random.normal(0, 1, len(t))
    formant_noise = np.convolve(formant_noise, np.hanning(6), mode='same')  # Shorter filter
    signal = signal + formant_noise
    
    # Normalize
    signal = signal / np.max(np.abs(signal)) * 0.95
    
    return signal.astype(np.float32)


def generate_tone_speech(frequency, duration, rate, modulation=True):
    """
    Legacy function for backwards compatibility
    Generates simple tone-based speech
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
    """Generate voices for different speakers with distinct characteristics"""
    print("\n[1] Generating Speaker Voices...")
    
    # Speaker 1: Male (lower pitch: 100-150 Hz)
    # Characteristics: Deep fundamental, slower modulation, strong lower harmonics
    print("  ⌘ Speaker 1 - Male voice (deep pitch, slower articulation)")
    male_freq = 120
    male_voice = generate_male_voice(male_freq, DURATION, SAMPLE_RATE, variant=0)
    save_audio(male_voice, "test_speaker1_enroll.wav")
    
    # Male speaker - same person, slight variation in tempo and rhythm
    male_voice_var = generate_male_voice(male_freq, DURATION, SAMPLE_RATE, variant=1)
    save_audio(male_voice_var, "test_speaker1_verify.wav")
    
    # Male speaker - same person, different variant with different prosody
    male_voice_var2 = generate_male_voice(male_freq, DURATION, SAMPLE_RATE, variant=2)
    save_audio(male_voice_var2, "test_speaker1_variant.wav")
    
    # Speaker 2: Female (higher pitch: 200-250 Hz)
    # Characteristics: Higher fundamental, faster modulation, more harmonics
    print("  ⌘ Speaker 2 - Female voice (higher pitch, faster articulation)")
    female_freq = 220
    female_voice = generate_female_voice(female_freq, DURATION, SAMPLE_RATE, variant=0)
    save_audio(female_voice, "test_speaker2_enroll.wav")
    
    # Female speaker - same person, slight variation in tempo
    female_voice_var = generate_female_voice(female_freq, DURATION, SAMPLE_RATE, variant=1)
    save_audio(female_voice_var, "test_speaker2_verify.wav")
    
    # Female speaker - same person, different variant
    female_voice_var2 = generate_female_voice(female_freq, DURATION, SAMPLE_RATE, variant=2)
    save_audio(female_voice_var2, "test_speaker2_variant.wav")
    
    # Speaker 3: Child (very high pitch: 300-350 Hz)
    # Characteristics: Very high pitch, rapid modulation, bright timbre with many harmonics
    print("  ⌘ Speaker 3 - Child voice (very high pitch, rapid articulation)")
    child_freq = 320
    child_voice = generate_child_voice(child_freq, DURATION, SAMPLE_RATE, variant=0)
    save_audio(child_voice, "test_speaker3_enroll.wav")
    
    # Child speaker - same person, slight variation
    child_voice_var = generate_child_voice(child_freq, DURATION, SAMPLE_RATE, variant=1)
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
