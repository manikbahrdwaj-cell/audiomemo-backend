"""
WebSocket Events Handler Module
Processes and handles various WebSocket message types
"""

import logging
import base64
import uuid
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.websocket.manager import (
    ClientConnection,
    WebSocketMessageBuilder,
    ConnectionState
)
from app.ml.embedding import generate_embedding, generate_embedding_with_chunking, calculate_cosine_similarity
from app.db.embeddings import (
    store_voice_embedding,
    find_nearest_embedding,
    verify_phone_number_embedding,
    check_enrollment,
    get_voice_embedding,
)
from app.db.verified_sessions import save_verified_session
from app.websocket.chunk_dispatcher import get_chunk_progress_dispatcher, ChunkProcessingStatus
from app.ml.similarity import EmbeddingSimilarityCalculator
import io
import soundfile as sf

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuration
SIMILARITY_THRESHOLD = settings.SIMILARITY_THRESHOLD
MIN_AUDIO_SIZE = 1000  # bytes


def calculate_chunk_similarities(
    audio_data: bytes, 
    enrolled_embedding: np.ndarray,
    num_chunks: int = 3
) -> List[Dict[str, Any]]:
    """
    Calculate similarity score for each audio chunk
    
    Args:
        audio_data: Raw audio bytes
        enrolled_embedding: Pre-computed enrolled embedding
        num_chunks: Number of chunks to split audio into
        
    Returns:
        List of chunk data with similarity scores
    """
    try:
        # Load audio data
        audio_buffer = io.BytesIO(audio_data)
        audio_samples, sample_rate = sf.read(audio_buffer, dtype='float32')
        
        # Ensure mono audio
        if len(audio_samples.shape) > 1:
            audio_samples = audio_samples.mean(axis=1)
        
        # Calculate chunk size
        chunk_size = len(audio_samples) // num_chunks
        if chunk_size == 0:
            return []
        
        chunks_data = []
        
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size if i < num_chunks - 1 else len(audio_samples)
            
            chunk_samples = audio_samples[start_idx:end_idx]
            
            if len(chunk_samples) == 0:
                continue
            
            # Generate embedding for this chunk
            chunk_audio_bytes = io.BytesIO()
            sf.write(chunk_audio_bytes, chunk_samples, sample_rate, format='WAV')
            chunk_audio_bytes.seek(0)
            
            chunk_embedding = generate_embedding_with_chunking(
                chunk_audio_bytes.read(),
                chunk_size_seconds=5.0,
                overlap_ratio=0.2,
                aggregation_method='mean'
            )
            
            if chunk_embedding is None:
                continue
            
            # Calculate similarity
            similarity = calculate_cosine_similarity(enrolled_embedding, chunk_embedding)
            
            chunks_data.append({
                "chunk_number": i + 1,
                "similarity": float(similarity),
                "duration_seconds": len(chunk_samples) / sample_rate,
                "start_sample": int(start_idx),
                "end_sample": int(end_idx),
            })
        
        return chunks_data
        
    except Exception as e:
        logger.warning(f"Failed to calculate chunk similarities: {str(e)}")
        return []


# Configuration


class AudioBuffer:
    """Buffer for accumulating audio chunks"""
    
    def __init__(self, max_size: int = 10_000_000):  # 10MB max
        self.data = b""
        self.max_size = max_size
        self.chunks_received = 0
        self.created_at = datetime.now()
    
    def add_chunk(self, chunk: bytes) -> bool:
        """Add a chunk to the buffer"""
        if len(self.data) + len(chunk) > self.max_size:
            return False
        
        self.data += chunk
        self.chunks_received += 1
        return True
    
    def get_data(self) -> bytes:
        """Get buffer data"""
        return self.data
    
    def get_size(self) -> int:
        """Get current buffer size in bytes"""
        return len(self.data)
    
    def is_valid(self) -> bool:
        """Check if buffer has minimum required audio"""
        return len(self.data) >= MIN_AUDIO_SIZE
    
    def clear(self):
        """Clear the buffer"""
        self.data = b""
        self.chunks_received = 0
    
    def get_info(self) -> Dict[str, Any]:
        """Get buffer information"""
        return {
            "size_bytes": len(self.data),
            "chunks_received": self.chunks_received,
            "is_valid": self.is_valid(),
            "created_at": self.created_at.isoformat()
        }


class WebSocketEventHandler:
    """Handles WebSocket events and message processing"""
    
    def __init__(self):
        self.audio_buffers: Dict[str, AudioBuffer] = {}
    
    async def handle_audio_chunk(self, connection: ClientConnection, 
                                 message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming audio chunk"""
        try:
            client_id = connection.client_id

            # ------------------------------------------------------------------
            # Agent mode: if this client has a verified session in the cache,
            # route the audio to VoiceAgentOrchestrator instead of the biometric
            # buffer path.  The orchestrator sends all async TTS frames directly
            # via send_ws; we only return a synchronous ACK here.
            # ------------------------------------------------------------------
            from app.agent.session_cache import get as get_agent_session
            from app.services.voice_agent import get_voice_agent

            agent_session = get_agent_session(client_id)
            if agent_session is not None:
                audio_data_b64 = message.get("data", "")
                try:
                    audio_bytes = base64.b64decode(audio_data_b64)
                except Exception as decode_err:
                    logger.error(f"Failed to decode audio data for agent: {decode_err}")
                    return WebSocketMessageBuilder.create_error_message(
                        "decode_error",
                        f"Failed to decode audio data: {decode_err}"
                    )

                await get_voice_agent().process_audio_chunk(
                    client_id=client_id,
                    audio_bytes=audio_bytes,
                    sample_rate=16000,
                    send_ws=connection.send_json,
                )
                return {"type": "audio_ack", "status": "ok"}

            # ------------------------------------------------------------------
            # Biometric buffer path (unauthenticated / still verifying)
            # ------------------------------------------------------------------

            # Ensure buffer exists
            if client_id not in self.audio_buffers:
                self.audio_buffers[client_id] = AudioBuffer()
            
            buffer = self.audio_buffers[client_id]
            
            # Decode audio data
            audio_data_b64 = message.get("data", "")
            try:
                audio_data = base64.b64decode(audio_data_b64)
            except Exception as e:
                logger.error(f"Failed to decode audio data: {str(e)}")
                return WebSocketMessageBuilder.create_error_message(
                    "decode_error",
                    f"Failed to decode audio data: {str(e)}"
                )
            
            # Add to buffer
            if not buffer.add_chunk(audio_data):
                return WebSocketMessageBuilder.create_error_message(
                    "buffer_overflow",
                    "Audio buffer size exceeded"
                )
            
            # Send acknowledgment
            return WebSocketMessageBuilder.create_success_message(
                "audio_received",
                {
                    "size": buffer.get_size(),
                    "chunks": buffer.chunks_received
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling audio chunk: {str(e)}")
            return WebSocketMessageBuilder.create_error_message(
                "audio_error",
                f"Error processing audio: {str(e)}"
            )
    
    async def handle_verify(self, connection: ClientConnection,
                           message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle optimized phone-number based voice verification
        
        Flow:
        1. Receive phone_number from client
        2. Check if phone_number exists in database
        3. If not exists: return error "Phone number not registered"
        4. If exists: fetch only that user's embedding
        5. Generate embedding from input voice
        6. Compare ONLY with that user's embedding (no looping through all users)
        7. Return similarity score and verification result
        
        Optimization: Uses indexed query on phone_number, avoids full collection scan
        """
        try:
            client_id = connection.client_id
            phone_number = message.get("phone_number", "").strip()
            
            # Validate phone number input
            if not phone_number:
                return WebSocketMessageBuilder.create_error_message(
                    "invalid_phone",
                    "Phone number is required for verification"
                )
            
            # Get audio buffer
            if client_id not in self.audio_buffers:
                return WebSocketMessageBuilder.create_error_message(
                    "no_audio",
                    "No audio data available"
                )
            
            buffer = self.audio_buffers[client_id]
            
            # Validate audio size
            if not buffer.is_valid():
                return WebSocketMessageBuilder.create_error_message(
                    "insufficient_audio",
                    f"Audio data too small (min: {MIN_AUDIO_SIZE} bytes)"
                )
            
            # Update connection state
            connection.set_state(ConnectionState.PROCESSING)
            
            # Create a session ID for this verification process
            verification_session_id = str(uuid.uuid4())
            dispatcher = get_chunk_progress_dispatcher()
            
            # Estimate number of chunks
            audio_data = buffer.get_data()
            estimated_chunks = max(1, len(audio_data) // (16000 * 2))  # 2 bytes per sample
            dispatcher.create_session(verification_session_id, estimated_chunks)
            dispatcher.start_processing(verification_session_id)
            
            # Subscribe to progress updates and send them to the client
            async def send_progress(progress):
                try:
                    await connection.send_json({
                        "type": "chunk_progress",
                        "payload": progress.to_dict()
                    })
                except Exception as e:
                    logger.error(f"Failed to send progress update: {str(e)}")
            
            progress_sub_id = await dispatcher.subscribe(send_progress)
            
            try:
                # OPTIMIZATION STEP 1: Check if phone number is registered
                logger.info(f"Checking if phone number {phone_number} is registered...")
                if not check_enrollment(phone_number):
                    logger.warning(f"Phone number {phone_number} is not registered")
                    await dispatcher.mark_failed(
                        verification_session_id, 
                        f"Phone number {phone_number} is not registered"
                    )
                    
                    connection.set_state(ConnectionState.IDLE)
                    buffer.clear()
                    
                    return WebSocketMessageBuilder.create_error_message(
                        "phone_not_registered",
                        f"Phone number {phone_number} is not registered. Please enroll first."
                    )
                
                logger.info(f"✓ Phone number {phone_number} is registered, proceeding with verification...")
                
                # OPTIMIZATION STEP 2: Generate embedding from input voice
                logger.info("Generating embedding for input voice...")
                query_embedding = generate_embedding(buffer.get_data())
                
                # OPTIMIZATION STEP 3: Use optimized phone-number based lookup
                # This function:
                # - Uses indexed query on phone_number (O(1) lookup)
                # - Fetches ONLY that user's embedding
                # - Returns immediately without searching ALL documents
                logger.info(f"Comparing voice with stored profile for {phone_number}...")
                result = verify_phone_number_embedding(
                    query_embedding=query_embedding,
                    phone_number=phone_number
                )
                
                # Mark as completed
                await dispatcher.mark_completed(verification_session_id)
                
            except Exception as e:
                await dispatcher.mark_failed(verification_session_id, str(e))
                raise
            finally:
                await dispatcher.unsubscribe(send_progress)
            
            # Clear buffer
            buffer.clear()
            
            # ==================== VERIFICATION RESULT HANDLING ====================
            
            if not result:
                connection.set_state(ConnectionState.IDLE)
                logger.warning(f"No embedding found for {phone_number}")
                return WebSocketMessageBuilder.create_error_message(
                    "no_embedding",
                    f"No voice profile found for phone number {phone_number}"
                )
            
            matched_phone_number = result["phone_number"]
            similarity_score = result["similarity_score"]
            
            logger.info(
                f"Verification comparison: {matched_phone_number} "
                f"with similarity score {similarity_score:.4f}"
            )
            
            # Get comprehensive similarity metrics
            calculator = EmbeddingSimilarityCalculator(metric='cosine')
            comprehensive_metrics = {}
            
            try:
                # Get the full enrollment document (we already have it in result)
                if "embedding" in result:
                    enrolled_emb = np.array(result["embedding"], dtype=np.float32)
                    query_emb = np.array(query_embedding, dtype=np.float32)
                    
                    comparison_result = calculator.compare(
                        query_emb,
                        enrolled_emb,
                        emb1_id="query",
                        emb2_id="enrolled",
                        threshold=SIMILARITY_THRESHOLD
                    )
                    
                    comprehensive_metrics = {
                        "cosine_similarity": float(comparison_result.cosine_similarity),
                        "cosine_distance": float(comparison_result.cosine_distance),
                        "euclidean_distance": float(comparison_result.euclidean_distance),
                        "correlation_distance": float(comparison_result.correlation_distance) if comparison_result.correlation_distance else None,
                        "confidence": float(comparison_result.confidence),
                    }
                else:
                    comprehensive_metrics = {
                        "cosine_similarity": float(similarity_score),
                        "cosine_distance": float(1.0 - similarity_score),
                    }
            except Exception as e:
                logger.warning(f"Failed to compute comprehensive metrics: {str(e)}")
                comprehensive_metrics = {
                    "cosine_similarity": float(similarity_score),
                    "cosine_distance": float(1.0 - similarity_score),
                }
            
            # ==================== VERIFICATION DECISION ====================
            
            is_match = similarity_score >= SIMILARITY_THRESHOLD
            
            if is_match:
                # SUCCESS: Create verified session
                logger.info(
                    f"✓ Voice verification successful for {matched_phone_number} "
                    f"(score: {similarity_score:.4f})"
                )
                
                # Update connection state
                connection.set_state(ConnectionState.IDLE)
                connection.set_metadata("verified_phone", matched_phone_number)
                connection.set_metadata("verified_at", datetime.now().isoformat())

                # Register verified session in the agent session cache so that
                # subsequent audio chunks from this connection are routed to
                # VoiceAgentOrchestrator (T18).
                try:
                    from app.agent.session_cache import set_verified as _agent_set_verified
                    _agent_set_verified(
                        client_id=connection.client_id,
                        phone_number=matched_phone_number,
                    )
                except Exception as _cache_err:
                    logger.warning("Failed to write AgentSessionCache: %s", _cache_err)
                
                # Log before sending response
                logger.info("Sending verification result to frontend: SUCCESS")
                
                # Calculate per-chunk similarities
                enrolled_emb = np.array(result["embedding"], dtype=np.float32) if "embedding" in result else None
                chunk_similarities = []
                if enrolled_emb is not None:
                    chunk_similarities = calculate_chunk_similarities(
                        audio_data,
                        enrolled_emb,
                        num_chunks=3
                    )
                
                # Build response with correct event name for frontend
                result_message = {
                    "event": "verification_result",
                    "type": "verification_result",
                    "status": "success",
                    "data": {
                        "status": "success",
                        "is_match": True,
                        "message": f"Voice verification successful for {matched_phone_number}",
                        "phone_number": matched_phone_number,
                        "similarity_score": float(similarity_score),
                        "threshold": SIMILARITY_THRESHOLD,
                        "confidence": comprehensive_metrics.get("confidence", min(similarity_score * 100, 100.0)),
                        "metrics": comprehensive_metrics,
                        "chunks": chunk_similarities,
                        "timestamp": datetime.now().isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                # FAILURE: Voice doesn't match the registered profile for this phone number
                logger.info(
                    f"✗ Voice verification failed for {matched_phone_number} "
                    f"(score: {similarity_score:.4f}, threshold: {SIMILARITY_THRESHOLD})"
                )
                
                # Update connection state
                connection.set_state(ConnectionState.IDLE)
                
                # Log before sending response
                logger.info("Sending verification result to frontend: FAILED")
                
                # Calculate per-chunk similarities for failed verification too
                enrolled_emb = np.array(result["embedding"], dtype=np.float32) if "embedding" in result else None
                chunk_similarities = []
                if enrolled_emb is not None:
                    chunk_similarities = calculate_chunk_similarities(
                        audio_data,
                        enrolled_emb,
                        num_chunks=3
                    )
                
                # Build response with correct event name for frontend
                result_message = {
                    "event": "verification_result",
                    "type": "verification_result",
                    "status": "failed",
                    "data": {
                        "status": "failed",
                        "is_match": False,
                        "message": f"This voice does not match the registered profile for {matched_phone_number}",
                        "phone_number": None,
                        "registered_phone": matched_phone_number,
                        "similarity_score": float(similarity_score),
                        "threshold": SIMILARITY_THRESHOLD,
                        "confidence": comprehensive_metrics.get("confidence", min(similarity_score * 100, 100.0)),
                        "metrics": comprehensive_metrics,
                        "chunks": chunk_similarities,
                        "timestamp": datetime.now().isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            connection.set_metadata("last_verification", datetime.now().isoformat())
            
            return result_message
        
        except Exception as e:
            logger.error(f"Verification error: {str(e)}", exc_info=True)
            if client_id in self.audio_buffers:
                self.audio_buffers[client_id].clear()
            connection.set_state(ConnectionState.ERROR)
            return WebSocketMessageBuilder.create_error_message(
                "verification_error",
                f"Verification failed: {str(e)}"
            )
    
    async def handle_enroll(self, connection: ClientConnection,
                           message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice enrollment"""
        try:
            client_id = connection.client_id
            phone_number = message.get("phone_number")
            
            # Get buffer
            if client_id not in self.audio_buffers:
                return WebSocketMessageBuilder.create_error_message(
                    "no_audio",
                    "No audio data available"
                )
            
            buffer = self.audio_buffers[client_id]
            
            # Validate audio size
            if not buffer.is_valid():
                return WebSocketMessageBuilder.create_error_message(
                    "insufficient_audio",
                    f"Audio data too small (min: {MIN_AUDIO_SIZE} bytes)"
                )
            
            # Update connection state
            connection.set_state(ConnectionState.PROCESSING)
            
            # Create a session ID for this enrollment process
            session_id = str(uuid.uuid4())
            dispatcher = get_chunk_progress_dispatcher()
            
            # Estimate number of chunks (1 second chunks at 16kHz = 16000 samples)
            audio_data = buffer.get_data()
            estimated_chunks = max(1, len(audio_data) // (16000 * 2))  # 2 bytes per sample
            dispatcher.create_session(session_id, estimated_chunks)
            dispatcher.start_processing(session_id)
            
            # Subscribe to progress updates and send them to the client
            async def send_progress(progress):
                try:
                    await connection.send_json({
                        "type": "chunk_progress",
                        "payload": progress.to_dict()
                    })
                except Exception as e:
                    logger.error(f"Failed to send progress update: {str(e)}")
            
            progress_sub_id = await dispatcher.subscribe(send_progress)
            
            try:
                # Check if phone number is already enrolled (duplicate prevention)
                if check_enrollment(phone_number):
                    logger.warning(f"Duplicate enrollment attempt via WebSocket: {phone_number}")
                    await dispatcher.mark_failed(session_id, "Phone number already enrolled")
                    
                    error_message = WebSocketMessageBuilder.create_error_message(
                        "duplicate_enrollment",
                        "This number is already enrolled. Duplicate enrollment is not allowed."
                    )
                    
                    # Clear buffer
                    buffer.clear()
                    connection.set_state(ConnectionState.IDLE)
                    
                    return error_message
                
                # Generate embedding
                logger.info(f"Generating embedding for enrollment: {phone_number}")
                embedding = generate_embedding(buffer.get_data())
                
                # Store in database
                vector_id = store_voice_embedding(phone_number, embedding)
                
                # Mark as completed
                await dispatcher.mark_completed(session_id)
            except Exception as e:
                await dispatcher.mark_failed(session_id, str(e))
                raise
            finally:
                await dispatcher.unsubscribe(send_progress)
            
            # Clear buffer
            buffer.clear()
            
            # Update connection state and metadata
            connection.set_state(ConnectionState.IDLE)
            connection.set_metadata("enrolled_phone", phone_number)
            connection.set_metadata("last_enrollment", datetime.now().isoformat())
            
            result_message = WebSocketMessageBuilder.create_success_message(
                "enrollment_success",
                {
                    "phone_number": phone_number,
                    "vector_id": vector_id,
                    "message": "Voice enrolled successfully"
                }
            )
            
            logger.info(f"Enrollment completed: phone={phone_number}, vector_id={vector_id}")
            
            return result_message
        
        except Exception as e:
            logger.error(f"Enrollment error: {str(e)}")
            if client_id in self.audio_buffers:
                self.audio_buffers[client_id].clear()
            connection.set_state(ConnectionState.ERROR)
            return WebSocketMessageBuilder.create_error_message(
                "enrollment_error",
                f"Enrollment failed: {str(e)}"
            )
    
    async def handle_ping(self, connection: ClientConnection) -> Dict[str, Any]:
        """Handle keep-alive ping"""
        connection.update_heartbeat()
        
        return WebSocketMessageBuilder.create_success_message(
            "pong",
            {
                "connection_id": connection.client_id,
                "uptime": (datetime.now() - connection.connected_at).total_seconds()
            }
        )
    
    async def handle_reset(self, connection: ClientConnection) -> Dict[str, Any]:
        """Handle audio buffer reset"""
        client_id = connection.client_id
        
        if client_id in self.audio_buffers:
            self.audio_buffers[client_id].clear()
        
        return WebSocketMessageBuilder.create_success_message(
            "reset_acknowledged",
            {
                "message": "Audio buffer cleared"
            }
        )
    
    async def handle_status(self, connection: ClientConnection) -> Dict[str, Any]:
        """Handle status request"""
        client_id = connection.client_id
        
        buffer_info = None
        if client_id in self.audio_buffers:
            buffer_info = self.audio_buffers[client_id].get_info()
        
        return WebSocketMessageBuilder.create_success_message(
            "status",
            {
                "connection_id": client_id,
                "state": connection.state.value,
                "connected_at": connection.connected_at.isoformat(),
                "uptime_seconds": (datetime.now() - connection.connected_at).total_seconds(),
                "last_heartbeat": connection.last_heartbeat.isoformat(),
                "buffer": buffer_info,
                "metadata": connection.metadata
            }
        )
    
    def cleanup_buffer(self, client_id: str):
        """Clean up audio buffer for a disconnected client"""
        if client_id in self.audio_buffers:
            del self.audio_buffers[client_id]
            logger.debug(f"Cleaned up audio buffer for {client_id}")
    
    def cleanup_all_buffers(self):
        """Clean up all audio buffers"""
        self.audio_buffers.clear()
        logger.info("Cleaned up all audio buffers")


# Global event handler instance
event_handler = WebSocketEventHandler()
