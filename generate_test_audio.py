#!/usr/bin/env python3
"""
Generate synthetic test audio files for different speakers
"""

import numpy as np
from scipy import signal
from scipy.io import wavfile
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_RATE = 16000
DURATION = 3  # seconds

def generate_speaker_audio(filename, pitch_multiplier, noise_level=0.05):
    """
    Generate synthetic speech-like audio with different characteristics
    
    Args:
        filename: Output WAV file path
        pitch_multiplier: Frequency multiplier for pitch (higher = higher pitch)
        noise_level: Amount of background noise to add
    """
    # Create time array
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION))
    
    # Generate multiple frequency components to simulate speech formants
    # Different formant frequencies for different "speakers"
    f1 = 500 * pitch_multiplier  # First formant
    f2 = 1500 * pitch_multiplier  # Second formant
    f3 = 2500 * pitch_multiplier  # Third formant
    
    # Create base signal with formant frequencies
    signal_main = (
        0.3 * np.sin(2 * np.pi * f1 * t) +
        0.2 * np.sin(2 * np.pi * f2 * t) +
        0.1 * np.sin(2 * np.pi * f3 * t)
    )
    
    # Add some frequency modulation to make it more speech-like
    modulation = 0.5 * (1 + np.sin(2 * np.pi * 2 * t))  # 2 Hz modulation
    signal_main = signal_main * modulation
    
    # Add octaves for harmonic richness
    signal_main += 0.15 * np.sin(2 * np.pi * f1 * 0.5 * t)  # Sub-harmonic
    signal_main += 0.1 * np.sin(2 * np.pi * f1 * 2 * t)  # Harmonic
    
    # Add realistic background noise
    noise = np.random.normal(0, noise_level, len(signal_main))
    signal_final = signal_main + noise
    
    # Normalize to prevent clipping
    signal_final = signal_final / np.max(np.abs(signal_final)) * 0.9
    
    # Apply envelope to make it more natural
    envelope = signal.windows.hann(len(signal_final))
    signal_final = signal_final * envelope
    
    # Convert to 16-bit PCM
    audio_data = np.int16(signal_final * 32767)
    
    # Write WAV file
    wavfile.write(filename, SAMPLE_RATE, audio_data)
    print(f"✓ Generated: {filename}")

def main():
    print("Generating synthetic test audio for different speakers...\n")
    
    # Speaker 1 (original baseline)
    generate_speaker_audio(
        os.path.join(OUTPUT_DIR, "test_voice_speaker1.wav"),
        pitch_multiplier=0.9,
        noise_level=0.05
    )
    
    # Speaker 2 (higher pitch)
    generate_speaker_audio(
        os.path.join(OUTPUT_DIR, "test_voice_speaker2.wav"),
        pitch_multiplier=1.3,
        noise_level=0.05
    )
    
    # Speaker 3 (lower pitch, different noise)
    generate_speaker_audio(
        os.path.join(OUTPUT_DIR, "test_voice_speaker3.wav"),
        pitch_multiplier=0.7,
        noise_level=0.08
    )
    
    # Different recording of Speaker 1 (should still match)
    generate_speaker_audio(
        os.path.join(OUTPUT_DIR, "test_voice_speaker1_variant.wav"),
        pitch_multiplier=0.9,
        noise_level=0.06
    )
    
    print("\n✓ All test audio files generated successfully!")
    print("\nGenerated files:")
    print("  - test_voice_speaker1.wav")
    print("  - test_voice_speaker2.wav")
    print("  - test_voice_speaker3.wav")
    print("  - test_voice_speaker1_variant.wav")

if __name__ == "__main__":
    main()
