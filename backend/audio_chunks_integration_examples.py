"""
Example: Integrating Audio Chunks with Enrollment and Verification Services

This file shows how to use the new audio chunking system with your existing
enrollment_service.py and verification_service.py
"""

import numpy as np
import logging
from typing import Optional, Dict, Any

from audio_chunk_receiver import get_chunk_receiver, ChunkReceiverStatus
from enrollment_service import (
    get_enrollment_manager,
    create_enrollment_session,
    EnrollmentSessionConfig,
)
from verification_service import (
    get_verification_manager,
    create_verification_session,
)
from voice_embedding import generate_embedding, calculate_cosine_similarity
from database import store_voice_embedding, get_voice_embedding

logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Enrollment with Chunked Audio
# ============================================================================

async def enrollment_with_chunks(phone_number: str, session_id: str) -> Dict[str, Any]:
    """
    Process enrollment using chunked audio
    
    Frontend sends 1-second chunks via WebSocket
    Backend receives and merges them, then creates enrollment
    
    Args:
        phone_number: User's phone number
        session_id: WebSocket session ID for chunk receiving
        
    Returns:
        Enrollment result dict
    """
    logger.info(f"Processing enrollment for {phone_number} (chunks session: {session_id})")
    
    try:
        # Step 1: Get the chunk receiver
        chunk_receiver = get_chunk_receiver()
        
        # Step 2: Wait for chunks to be received and merged
        # (This happens via WebSocket in real-time)
        # Frontend sends chunks → Backend buffered them
        
        # Step 3: Process the session to get merged audio and embedding
        success, embedding, error = chunk_receiver.process_session(session_id)
        
        if not success:
            return {
                'success': False,
                'error': f'Chunk processing failed: {error}',
                'phone_number': phone_number
            }
        
        logger.info(
            f"Chunks processed successfully. "
            f"Embedding shape: {embedding.shape}, "
            f"Total duration: {chunk_receiver.get_session_info(session_id)['merged_duration_ms']:.0f}ms"
        )
        
        # Step 4: Create enrollment session with the embedding
        enrollment_manager = get_enrollment_manager()
        enrollment_session = create_enrollment_session(
            phone_number=phone_number,
            config=EnrollmentSessionConfig(
                max_chunks=1,  # We already merged all chunks
                auto_process=True,
                merge_embeddings=False,  # No need, we have single embedding
            )
        )
        
        # Step 5: Store the embedding
        try:
            store_voice_embedding(phone_number, embedding)
            logger.info(f"Enrollment successful for {phone_number}")
            
            return {
                'success': True,
                'phone_number': phone_number,
                'message': 'Enrollment completed successfully',
                'embedding_shape': list(embedding.shape),
                'session_id': enrollment_session.session_id,
            }
        
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to store embedding: {str(e)}',
                'phone_number': phone_number
            }
        
        finally:
            # Cleanup chunk receiver session
            chunk_receiver.cleanup_session(session_id)
    
    except Exception as e:
        logger.error(f"Enrollment error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number
        }


# ============================================================================
# EXAMPLE 2: Verification with Chunked Audio
# ============================================================================

async def verification_with_chunks(
    phone_number: str,
    session_id: str,
    threshold: float = 0.75
) -> Dict[str, Any]:
    """
    Process verification using chunked audio
    
    Frontend sends 5-second chunks via WebSocket
    Backend receives and merges them, then compares with enrollment
    
    Args:
        phone_number: User's phone number
        session_id: WebSocket session ID for chunk receiving
        threshold: Similarity threshold for verification
        
    Returns:
        Verification result dict
    """
    logger.info(
        f"Processing verification for {phone_number} "
        f"(chunks session: {session_id}, threshold: {threshold})"
    )
    
    try:
        # Step 1: Get chunk receiver
        chunk_receiver = get_chunk_receiver()
        
        # Step 2: Process chunks to get merged audio and embedding
        success, verification_embedding, error = chunk_receiver.process_session(session_id)
        
        if not success:
            return {
                'success': False,
                'verified': False,
                'error': f'Chunk processing failed: {error}',
                'phone_number': phone_number
            }
        
        logger.info(f"Verification embedding generated: shape {verification_embedding.shape}")
        
        # Step 3: Get enrolled embedding from database
        enrolled_embedding = get_voice_embedding(phone_number)
        
        if enrolled_embedding is None:
            return {
                'success': False,
                'verified': False,
                'error': f'No enrollment found for {phone_number}',
                'phone_number': phone_number
            }
        
        # Step 4: Calculate similarity
        similarity_score = calculate_cosine_similarity(
            verification_embedding,
            enrolled_embedding
        )
        
        verified = similarity_score >= threshold
        
        logger.info(
            f"Verification result: similarity={similarity_score:.4f}, "
            f"verified={verified} (threshold={threshold})"
        )
        
        # Session info for details
        session_info = chunk_receiver.get_session_info(session_id)
        
        return {
            'success': True,
            'verified': verified,
            'phone_number': phone_number,
            'similarity_score': float(similarity_score),
            'threshold': threshold,
            'message': 'Verification PASSED' if verified else 'Verification FAILED',
            'merged_duration_ms': session_info['merged_duration_ms'],
            'chunks_processed': session_info['chunks_received'],
        }
    
    except Exception as e:
        logger.error(f"Verification error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'verified': False,
            'error': str(e),
            'phone_number': phone_number
        }
    
    finally:
        # Cleanup chunk receiver session
        chunk_receiver.cleanup_session(session_id)


# ============================================================================
# EXAMPLE 3: WebSocket Integration (in main.py)
# ============================================================================

"""
Integration into existing websocket_endpoint:

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    connection = await connection_manager.connect(websocket, client_id)
    audio_handler = get_audio_chunk_handler()
    
    try:
        while True:
            message_text = await websocket.receive_text()
            message = json.loads(message_text)
            message_type = message.get('type')
            
            # Handle audio chunks
            if message_type == 'audio':
                response = await audio_handler.handle_audio_message(message, connection)
                await connection.send_json(response)
            
            # Handle enrollment with chunks
            elif message_type == 'enrollment_status':
                action = message.get('action')
                
                if action == 'finalize_session':
                    session_id = message.get('session_id')
                    phone_number = message.get('phone_number')
                    
                    # Process chunks and create enrollment
                    result = await enrollment_with_chunks(
                        phone_number=phone_number,
                        session_id=session_id
                    )
                    await connection.send_json({
                        'type': 'enrollment_status',
                        'status': 'completed',
                        'result': result
                    })
            
            # Handle verification with chunks
            elif message_type == 'verify':
                action = message.get('action')
                
                if action == 'finalize_session':
                    session_id = message.get('session_id')
                    phone_number = message.get('phone_number')
                    threshold = message.get('threshold', 0.75)
                    
                    # Process chunks and verify
                    result = await verification_with_chunks(
                        phone_number=phone_number,
                        session_id=session_id,
                        threshold=threshold
                    )
                    await connection.send_json({
                        'type': 'verify',
                        'status': 'completed',
                        'result': result
                    })
    
    except WebSocketDisconnect:
        # Cleanup any pending sessions
        session_id = connection.get_metadata('chunk_session_id')
        if session_id:
            get_audio_chunk_handler().chunk_receiver.cleanup_session(session_id)
        connection_manager.disconnect(client_id)
"""


# ============================================================================
# EXAMPLE 4: Testing Locally Without Frontend
# ============================================================================

def test_enrollment_with_simulated_chunks():
    """Test enrollment processing with simulated audio chunks"""
    import asyncio
    from audio_chunk_receiver import ChunkReceiverStatus
    
    print("=" * 60)
    print("TEST: Enrollment with Simulated Chunks")
    print("=" * 60)
    
    # Create receiver and session
    chunk_receiver = get_chunk_receiver()
    session = chunk_receiver.create_session(
        phone_number='+1234567890',
        mode='enrollment'
    )
    
    print(f"\nCreated session: {session.session_id}")
    print(f"Mode: {session.mode}")
    print(f"Status: {session.status.value}")
    
    # Simulate receiving 5 chunks (1 second each)
    print("\n--- Simulating Chunk Reception ---")
    for i in range(5):
        # Create random audio
        audio_data = np.random.randn(16000).astype(np.float32)
        
        # Add to session
        success, error = chunk_receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=i + 1,
            audio_data=audio_data,
            sample_rate=16000,
            duration_ms=1000
        )
        
        print(f"Chunk {i + 1}: {'✅ Received' if success else '❌ Failed'}")
        if error:
            print(f"  Error: {error}")
    
    # Process session
    print("\n--- Processing Session ---")
    success, embedding, error = chunk_receiver.process_session(session.session_id)
    
    if success:
        print(f"✅ Success!")
        print(f"Embedding shape: {embedding.shape}")
        print(f"Embedding (first 5 values): {embedding[:5]}")
        
        # Get session info
        info = chunk_receiver.get_session_info(session.session_id)
        print(f"\nSession Info:")
        print(f"  Total duration: {info['merged_duration_ms']:.0f}ms")
        print(f"  Chunks received: {info['chunks_received']}")
        print(f"  Status: {info['status']}")
        print(f"  Processing time: {info['processing_time_ms']:.0f}ms")
    else:
        print(f"❌ Failed: {error}")
    
    # Cleanup
    chunk_receiver.cleanup_session(session.session_id)
    print("\n✅ Session cleaned up")


def test_verification_with_simulated_chunks():
    """Test verification processing with simulated audio chunks"""
    import asyncio
    
    print("\n" + "=" * 60)
    print("TEST: Verification with Simulated Chunks")
    print("=" * 60)
    
    # Create receiver and session
    chunk_receiver = get_chunk_receiver()
    session = chunk_receiver.create_session(
        phone_number='+1234567890',
        mode='verification'
    )
    
    print(f"\nCreated session: {session.session_id}")
    print(f"Mode: {session.mode}")
    
    # Simulate receiving 2 chunks (5 seconds each for verification)
    print("\n--- Simulating Chunk Reception (5-second chunks) ---")
    for i in range(2):
        # Create random audio (80,000 samples = 5 seconds)
        audio_data = np.random.randn(80000).astype(np.float32)
        
        success, error = chunk_receiver.add_chunk(
            session_id=session.session_id,
            chunk_number=i + 1,
            audio_data=audio_data,
            sample_rate=16000,
            duration_ms=5000
        )
        
        print(f"Chunk {i + 1} (5s): {'✅ Received' if success else '❌ Failed'}")
    
    # Process
    print("\n--- Processing Session ---")
    success, embedding, error = chunk_receiver.process_session(session.session_id)
    
    if success:
        print(f"✅ Success!")
        print(f"Embedding shape: {embedding.shape}")
        print(f"Total duration: ~10 seconds")
    else:
        print(f"❌ Failed: {error}")
    
    chunk_receiver.cleanup_session(session.session_id)


# ============================================================================

if __name__ == '__main__':
    # Run tests
    test_enrollment_with_simulated_chunks()
    test_verification_with_simulated_chunks()
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)
