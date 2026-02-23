"""
Test Voice Verification with Proper WAV Encoding
Tests that audio chunks are properly encoded as WAV and processed by the backend
"""

import asyncio
import json
import base64
import logging
import soundfile as sf
import numpy as np
from datetime import datetime
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_wav(duration_seconds=5, sample_rate=16000):
    """Create a test WAV file with synthetic audio"""
    num_samples = duration_seconds * sample_rate
    
    # Generate a simple sine wave (440 Hz)
    frequency = 440
    t = np.linspace(0, duration_seconds, num_samples, False)
    audio = np.sin(2 * np.pi * frequency * t) * 0.3
    
    # Create WAV file in memory
    import io
    with io.BytesIO() as f:
        sf.write(f, audio, sample_rate, format='WAV')
        wav_bytes = f.getvalue()
    
    return wav_bytes, audio


async def test_verification_with_realphone():
    """Test verification flow with WebSocket connection"""
    
    # First, create a test enrollment so we have a phone to verify
    phone_number = "9876543210"
    
    # Get stored embedding for the phone
    from database import get_voice_embedding
    
    embedding = get_voice_embedding(phone_number)
    if embedding is None:
        logger.error(f"Phone {phone_number} not enrolled. Enrolling now...")
        # Enroll a test phone
        from voice_embedding import generate_embedding
        from database import store_voice_embedding
        
        wav_bytes, audio = create_test_wav(duration_seconds=5, sample_rate=16000)
        test_embedding = generate_embedding(wav_bytes)
        store_voice_embedding(phone_number, test_embedding)
        logger.info(f"Enrolled test phone: {phone_number}")
    
    # Now test verification via WebSocket
    logger.info(f"Testing verification WebSocket for phone: {phone_number}")
    
    ws_url = f"ws://localhost:8000/ws/verify/{phone_number}"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("Connected to verification WebSocket")
            
            # Receive session ready message
            response = await websocket.recv()
            session_msg = json.loads(response)
            logger.info(f"Received message: {session_msg}")
            
            if session_msg.get("type") != "session_ready":
                logger.error(f"Unexpected message type: {session_msg.get('type')}")
                return False
            
            session_id = session_msg.get("session_id")
            max_chunks = session_msg.get("max_chunks", 4)
            threshold = session_msg.get("threshold", 0.75)
            
            logger.info(f"Session created: {session_id}, Max chunks: {max_chunks}, Threshold: {threshold}")
            
            # Send audio chunks
            logger.info("Sending audio chunks for verification...")
            
            # Create test WAV chunks
            chunk_size_seconds = 5
            wav_bytes, audio = create_test_wav(duration_seconds=chunk_size_seconds, sample_rate=16000)
            
            # Encode as base64 and send
            audio_base64 = base64.b64encode(wav_bytes).decode('utf-8')
            
            message = {
                "type": "audio",
                "data": audio_base64
            }
            
            logger.info(f"Sending audio chunk (WAV size: {len(wav_bytes)} bytes)")
            await websocket.send(json.dumps(message))
            
            # Receive chunk result
            response = await websocket.recv()
            result_msg = json.loads(response)
            logger.info(f"Received result: {result_msg}")
            
            if result_msg.get("type") == "chunk_result":
                chunk_number = result_msg.get("chunk_number")
                similarity = result_msg.get("similarity_score")
                is_match = result_msg.get("is_match")
                final_status = result_msg.get("final_status")
                
                logger.info(f"Chunk {chunk_number}: Similarity={similarity:.4f}, Match={is_match}")
                
                if final_status:
                    logger.info(f"Verification result: {final_status}")
                    if final_status == "verified":
                        logger.info("✓ Verification PASSED - Similarity score exceeded threshold")
                        return True
                    else:
                        logger.info("✗ Verification FAILED - Similarity score below threshold")
                        # Continue to next chunk
                        return False
                else:
                    logger.info("Continue sending chunks...")
                    # Send another chunk
                    await websocket.send(json.dumps(message))
                    response = await websocket.recv()
                    result_msg = json.loads(response)
                    logger.info(f"Chunk 2 result: {result_msg}")
                    
            
            return result_msg.get("final_status") == "verified"
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        return False


def test_wav_encoding():
    """Test that WAV files are properly created with RIFF headers"""
    import io
    import struct
    
    # Create test audio
    sample_rate = 16000
    duration = 5
    samples = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration)) * 0.3
    
    # Use soundfile to create proper WAV
    with io.BytesIO() as f:
        sf.write(f, samples, sample_rate, format='WAV')
        wav_bytes = f.getvalue()
    
    # Verify WAV format
    logger.info(f"Created WAV file: {len(wav_bytes)} bytes")
    
    # Check RIFF header
    if wav_bytes[:4] != b'RIFF':
        logger.error("Invalid WAV file: missing RIFF header")
        return False
    
    if wav_bytes[8:12] != b'WAVE':
        logger.error("Invalid WAV file: missing WAVE marker")
        return False
    
    logger.info("✓ WAV file has proper RIFF headers")
    
    # Try to load the WAV
    try:
        audio, sr = sf.read(io.BytesIO(wav_bytes))
        logger.info(f"✓ WAV file loaded successfully: {len(audio)} samples at {sr} Hz")
        return True
    except Exception as e:
        logger.error(f"Failed to load WAV: {str(e)}")
        return False


if __name__ == "__main__":
    # Test WAV encoding
    print("\n=== Testing WAV Encoding ===")
    if test_wav_encoding():
        print("WAV encoding test PASSED")
    else:
        print("WAV encoding test FAILED")
    
    # Test verification
    print("\n=== Testing Verification WebSocket ===")
    try:
        result = asyncio.run(test_verification_with_realphone())
        if result:
            print("✓ VERIFICATION TEST PASSED")
        else:
            print("✗ VERIFICATION TEST FAILED")
    except Exception as e:
        print(f"Test error: {str(e)}")
