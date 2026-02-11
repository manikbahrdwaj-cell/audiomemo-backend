#!/usr/bin/env python
"""
Test script for Voice Biometric API
Tests enrollment and verification endpoints
"""

import requests
import struct
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def create_test_wav(filename, duration_ms=2000, sample_rate=16000):
    """Create a test WAV file"""
    num_samples = int(sample_rate * duration_ms / 1000)
    
    # WAV file parameters
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    
    # Create silence (all zeros)
    audio_data = b'\x00' * (num_samples * 2)  # 16-bit samples
    
    # Create WAV header
    wav_header = b'RIFF'
    file_size = 36 + len(audio_data)
    wav_header += struct.pack('<I', file_size)
    wav_header += b'WAVE'
    
    # Format subchunk
    wav_header += b'fmt '
    wav_header += struct.pack('<I', 16)  # Subchunk1Size
    wav_header += struct.pack('<H', 1)   # AudioFormat (1 = PCM)
    wav_header += struct.pack('<H', num_channels)
    wav_header += struct.pack('<I', sample_rate)
    wav_header += struct.pack('<I', byte_rate)
    wav_header += struct.pack('<H', block_align)
    wav_header += struct.pack('<H', bits_per_sample)
    
    # Data subchunk
    wav_header += b'data'
    wav_header += struct.pack('<I', len(audio_data))
    
    # Write to file
    with open(filename, 'wb') as f:
        f.write(wav_header)
        f.write(audio_data)
    
    print("[OK] Created test WAV file: " + filename)

def test_health():
    """Test the health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check Endpoint")
    print("="*60)
    
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print("Status Code: " + str(response.status_code))
        print("Response: " + str(response.json()))
        if response.status_code == 200:
            print("[OK] Health check PASSED")
            return True
        else:
            print("[FAIL] Health check FAILED")
            return False
    except Exception as e:
        print("[ERROR] Health check ERROR: " + str(e))
        return False

def test_enroll(phone_number, wav_file):
    """Test the enrollment endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Enrollment Endpoint")
    print("="*60)
    print("Phone Number: " + phone_number)
    print("WAV File: " + wav_file)
    
    try:
        with open(wav_file, 'rb') as f:
            files = {'file': ('voice.wav', f, 'audio/wav')}
            data = {'phone_number': phone_number}
            
            response = requests.post(
                "http://localhost:8000/enroll",
                data=data,
                files=files,
                timeout=120
            )
        
        print("Status Code: " + str(response.status_code))
        print("Response: " + str(response.json()))
        
        if response.status_code == 200:
            print("[OK] Enrollment PASSED")
            return response.json()
        else:
            detail = response.json().get('detail', 'Unknown error')
            print("[FAIL] Enrollment FAILED: " + str(detail))
            return None
            
    except Exception as e:
        print("[ERROR] Enrollment ERROR: " + str(e))
        import traceback
        traceback.print_exc()
        return None

def test_check_enrollment(phone_number):
    """Test the enrollment check endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Check Enrollment Status")
    print("="*60)
    print("Phone Number: " + phone_number)
    
    try:
        response = requests.get(
            "http://localhost:8000/check/" + phone_number,
            timeout=5
        )
        
        print("Status Code: " + str(response.status_code))
        print("Response: " + str(response.json()))
        
        if response.status_code == 200:
            print("[OK] Check enrollment PASSED")
            return response.json()
        else:
            print("[FAIL] Check enrollment FAILED")
            return None
            
    except Exception as e:
        print("[ERROR] Check enrollment ERROR: " + str(e))
        return None

def test_verify(phone_number, wav_file):
    """Test the verification endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Verification Endpoint")
    print("="*60)
    print("Phone Number: " + phone_number)
    print("WAV File: " + wav_file)
    
    try:
        with open(wav_file, 'rb') as f:
            files = {'file': ('voice.wav', f, 'audio/wav')}
            data = {'phone_number': phone_number}
            
            response = requests.post(
                "http://localhost:8000/verify",
                data=data,
                files=files,
                timeout=120
            )
        
        print("Status Code: " + str(response.status_code))
        print("Response: " + str(response.json()))
        
        if response.status_code == 200:
            result = response.json()
            sim_score = result['similarity_score']
            is_match = result['is_match']
            print("Similarity Score: {:.4f}".format(sim_score))
            print("Is Match: " + str(is_match))
            print("[OK] Verification PASSED")
            return result
        else:
            detail = response.json().get('detail', 'Unknown error')
            print("[FAIL] Verification FAILED: " + str(detail))
            return None
            
    except Exception as e:
        print("[ERROR] Verification ERROR: " + str(e))
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*60)
    print("VOICE BIOMETRIC API TEST SUITE")
    print("="*60)
    
    # Create test WAV file
    test_wav = "test_voice.wav"
    create_test_wav(test_wav)
    
    phone = "1234567890"
    
    # Test health
    if not test_health():
        print("\n[CRITICAL] Backend is not responding. Exiting.")
        return False
    
    # Test enrollment
    enroll_result = test_enroll(phone, test_wav)
    if not enroll_result:
        print("\n[ERROR] Enrollment failed. Check MongoDB connection and model loading.")
        return False
    
    # Test check enrollment
    check_result = test_check_enrollment(phone)
    if not check_result:
        print("\n[ERROR] Check enrollment failed.")
        return False
    
    if check_result['enrolled']:
        print("\n[OK] Phone number " + phone + " is enrolled")
        
        # Test verification
        verify_result = test_verify(phone, test_wav)
        if verify_result:
            score = verify_result['similarity_score']
            print("\n[OK] Verification completed with score: {:.4f}".format(score))
        else:
            print("\n[ERROR] Verification failed")
            return False
    else:
        print("\n[ERROR] Phone number " + phone + " is not enrolled")
        return False
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


def test_health():
    """Test the health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check Endpoint")
    print("="*60)
    
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✓ Health check PASSED")
            return True
        else:
            print("✗ Health check FAILED")
            return False
    except Exception as e:
        print(f"✗ Health check ERROR: {e}")
        return False

def test_enroll(phone_number, wav_file):
    """Test the enrollment endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Enrollment Endpoint")
    print("="*60)
    print(f"Phone Number: {phone_number}")
    print(f"WAV File: {wav_file}")
    
    try:
        with open(wav_file, 'rb') as f:
            files = {'file': ('voice.wav', f, 'audio/wav')}
            data = {'phone_number': phone_number}
            
            response = requests.post(
                "http://localhost:8000/enroll",
                data=data,
                files=files,
                timeout=120
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✓ Enrollment PASSED")
            return response.json()
        else:
            print(f"✗ Enrollment FAILED: {response.json().get('detail', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"✗ Enrollment ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_check_enrollment(phone_number):
    """Test the enrollment check endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Check Enrollment Status")
    print("="*60)
    print(f"Phone Number: {phone_number}")
    
    try:
        response = requests.get(
            f"http://localhost:8000/check/{phone_number}",
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✓ Check enrollment PASSED")
            return response.json()
        else:
            print(f"✗ Check enrollment FAILED")
            return None
            
    except Exception as e:
        print(f"✗ Check enrollment ERROR: {e}")
        return None

def test_verify(phone_number, wav_file):
    """Test the verification endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Verification Endpoint")
    print("="*60)
    print(f"Phone Number: {phone_number}")
    print(f"WAV File: {wav_file}")
    
    try:
        with open(wav_file, 'rb') as f:
            files = {'file': ('voice.wav', f, 'audio/wav')}
            data = {'phone_number': phone_number}
            
            response = requests.post(
                "http://localhost:8000/verify",
                data=data,
                files=files,
                timeout=120
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Similarity Score: {result['similarity_score']:.4f}")
            print(f"Is Match: {result['is_match']}")
            print("✓ Verification PASSED")
            return result
        else:
            print(f"✗ Verification FAILED: {response.json().get('detail', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"✗ Verification ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*60)
    print("VOICE BIOMETRIC API TEST SUITE")
    print("="*60)
    
    # Create test WAV file
    test_wav = "test_voice.wav"
    create_test_wav(test_wav)
    
    phone = "1234567890"
    
    # Test health
    if not test_health():
        print("\n✗ Backend is not responding. Exiting.")
        return False
    
    # Test enrollment
    enroll_result = test_enroll(phone, test_wav)
    if not enroll_result:
        print("\n✗ Enrollment failed. Check MongoDB connection.")
        print("Install MongoDB locally or configure MongoDB Atlas for testing.")
        return False
    
    # Test check enrollment
    check_result = test_check_enrollment(phone)
    if not check_result:
        print("\n✗ Check enrollment failed.")
        return False
    
    if check_result['enrolled']:
        print(f"✓ Phone number {phone} is enrolled")
        
        # Test verification
        verify_result = test_verify(phone, test_wav)
        if verify_result:
            print(f"\n✓ Verification completed with score: {verify_result['similarity_score']:.4f}")
        else:
            print("\n✗ Verification failed")
            return False
    else:
        print(f"\n✗ Phone number {phone} is not enrolled")
        return False
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
