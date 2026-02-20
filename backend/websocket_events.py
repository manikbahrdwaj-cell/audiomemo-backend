"""
WebSocket Events Handler Module
Processes and handles various WebSocket message types
"""

import logging
import base64
import uuid
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime

from websocket_handler import (
    ClientConnection,
    WebSocketMessageBuilder,
    ConnectionState
)
from voice_embedding import generate_embedding
from database import (
    store_voice_embedding, 
    find_nearest_embedding, 
    check_enrollment, 
    get_voice_embedding,
    save_verified_session
)
from chunk_progress_dispatcher import get_chunk_progress_dispatcher, ChunkProcessingStatus
from embedding_similarity_operations import EmbeddingSimilarityCalculator
from session_service import get_verified_session_manager

logger = logging.getLogger(__name__)

# Configuration
SIMILARITY_THRESHOLD = 0.75
MIN_AUDIO_SIZE = 1000  # bytes


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
        Handle voice-first verification (Phase 2)
        
        Flow:
        1. User records voice (no phone number required)
        2. Backend generates embedding
        3. Backend searches ALL enrolled embeddings
        4. If best match > threshold, create verified session
        5. Return matched phone_number and session_id
        """
        try:
            client_id = connection.client_id
            
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
                # Generate embedding from user's voice
                logger.info("Generating embedding for voice-first verification...")
                query_embedding = generate_embedding(buffer.get_data())
                
                # PHASE 2: Search across ALL enrolled embeddings (no phone_number filter)
                logger.info("Searching across all enrolled embeddings...")
                results = find_nearest_embedding(
                    query_embedding=query_embedding,
                    phone_number=None,  # Search ALL enrollments
                    limit=1
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
            
            if not results:
                connection.set_state(ConnectionState.IDLE)
                logger.warning("No enrolled embeddings found in system")
                return WebSocketMessageBuilder.create_error_message(
                    "no_match",
                    "No record found for this voice in the system."
                )
            
            # Get best match
            best_match = results[0]
            matched_phone_number = best_match["phone_number"]
            similarity_score = best_match["similarity_score"]
            
            logger.info(
                f"Best match: {matched_phone_number} "
                f"with similarity score {similarity_score:.4f}"
            )
            
            # Get comprehensive similarity metrics
            calculator = EmbeddingSimilarityCalculator(metric='cosine')
            comprehensive_metrics = {}
            
            try:
                # Get the full enrollment document to access embedding
                enrolled_doc = get_voice_embedding(matched_phone_number)
                if enrolled_doc and "embedding" in enrolled_doc:
                    enrolled_emb = np.array(enrolled_doc["embedding"], dtype=np.float32)
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
                
                session_manager = get_verified_session_manager()
                
                # Create verified session
                verified_session = session_manager.create_verified_session(
                    phone_number=matched_phone_number,
                    verification_score=similarity_score,
                    similarity_metrics=comprehensive_metrics
                )
                
                # Create LangChain session
                try:
                    langgraph_session_id = session_manager.create_langgraph_session(verified_session)
                    logger.info(f"Created LangGraph session: {langgraph_session_id}")
                except Exception as e:
                    logger.warning(f"Failed to create LangGraph session: {str(e)}")
                    langgraph_session_id = None
                
                # Store verified session in MongoDB
                try:
                    session_doc = verified_session.to_dict()
                    session_doc["langgraph_session_id"] = langgraph_session_id
                    save_verified_session(session_doc)
                    logger.info(f"Stored verified session in MongoDB: {verified_session.session_id[:8]}")
                except Exception as e:
                    logger.error(f"Failed to store verified session in MongoDB: {str(e)}")
                
                # Update connection state
                connection.set_state(ConnectionState.IDLE)
                connection.set_metadata("verified_phone", matched_phone_number)
                connection.set_metadata("session_id", verified_session.session_id)
                connection.set_metadata("verified_at", datetime.now().isoformat())
                
                # Log before sending response
                logger.info("Sending verification result to frontend: SUCCESS")
                
                # Build response with correct event name for frontend
                result_message = {
                    "event": "verification_result",
                    "type": "verification_result",
                    "status": "success",
                    "data": {
                        "status": "success",
                        "is_match": True,
                        "message": f"This voice is matched with this mobile number: {matched_phone_number}",
                        "phone_number": matched_phone_number,
                        "session_id": verified_session.session_id,
                        "langgraph_session_id": langgraph_session_id,
                        "similarity_score": float(similarity_score),
                        "threshold": SIMILARITY_THRESHOLD,
                        "confidence": comprehensive_metrics.get("confidence", min(similarity_score * 100, 100.0)),
                        "metrics": comprehensive_metrics,
                        "timestamp": datetime.now().isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                # FAILURE: No match above threshold
                logger.info(
                    f"✗ Voice verification failed for {matched_phone_number} "
                    f"(score: {similarity_score:.4f}, threshold: {SIMILARITY_THRESHOLD})"
                )
                
                # Update connection state
                connection.set_state(ConnectionState.IDLE)
                
                # Log before sending response
                logger.info("Sending verification result to frontend: FAILED")
                
                # Build response with correct event name for frontend
                result_message = {
                    "event": "verification_result",
                    "type": "verification_result",
                    "status": "failed",
                    "data": {
                        "status": "failed",
                        "is_match": False,
                        "message": "No phone number is matched with this voice.",
                        "phone_number": None,
                        "best_match_phone": matched_phone_number,
                        "best_match_score": float(similarity_score),
                        "threshold": SIMILARITY_THRESHOLD,
                        "similarity_score": float(similarity_score),
                        "confidence": comprehensive_metrics.get("confidence", min(similarity_score * 100, 100.0)),
                        "metrics": comprehensive_metrics,
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
