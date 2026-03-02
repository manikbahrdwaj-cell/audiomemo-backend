"""
Real-Time Verification Streaming Service
Handles WebSocket-based voice verification with automatic chunk processing
"""

import logging
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
import numpy as np
import io

from app.ml.embedding import generate_embedding, calculate_cosine_similarity
from app.db.embeddings import get_voice_embedding
from app.db.verified_sessions import save_verified_session
from app.agent.session_cache import set_verified as agent_set_verified
from app.db.embeddings import get_user_id_for_phone

logger = logging.getLogger(__name__)


class StreamingVerificationStatus(Enum):
    """Status of streaming verification session"""
    INITIALIZED = "initialized"
    RETRIEVING_EMBEDDING = "retrieving_embedding"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING_CHUNK = "processing_chunk"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ChunkVerificationResult:
    """Result of verifying a single chunk"""
    chunk_number: int
    similarity_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_match: bool = False
    embedding: Optional[np.ndarray] = None


@dataclass
class StreamingVerificationSession:
    """Real-time verification session with streaming chunks"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: str = ""
    enrolled_embedding: Optional[np.ndarray] = None
    threshold: float = 0.75
    max_chunks: int = 4
    
    status: StreamingVerificationStatus = StreamingVerificationStatus.INITIALIZED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    
    # Audio buffer for accumulating chunks (5-second accumulation)
    audio_buffer: List[bytes] = field(default_factory=list)
    buffer_duration_seconds: float = 0.0
    target_duration_seconds: float = 5.0
    sample_rate: int = 16000
    
    # Chunk tracking (now tracks processed 5-second chunks)
    chunks_processed: int = 0
    chunk_results: List[ChunkVerificationResult] = field(default_factory=list)
    
    # WebSocket client_id — populated by the caller so the agent session cache
    # can be keyed to the connection rather than the internal session UUID.
    client_id: str = ""

    # Final result
    final_status: Optional[str] = None
    verified_at_chunk: Optional[int] = None
    
    def __repr__(self) -> str:
        return (
            f"StreamingVerificationSession(id={self.session_id[:8]}, "
            f"phone={self.phone_number}, "
            f"status={self.status.value}, "
            f"chunks={self.chunks_processed}/{self.max_chunks}, "
            f"buffer={self.buffer_duration_seconds:.2f}s)"
        )


class RealtimeVerificationManager:
    """
    Manages real-time verification sessions
    Handles automatic chunk processing and threshold detection
    """
    
    def __init__(self):
        self.sessions: Dict[str, StreamingVerificationSession] = {}
        self.chunk_locks: Dict[str, asyncio.Lock] = {}
    
    async def create_session(self, phone_number: str, threshold: float = 0.75) -> Optional[StreamingVerificationSession]:
        """
        Create a new streaming verification session
        
        Returns:
            Session object or None if phone number not found
        """
        try:
            # Retrieve stored embedding
            logger.info(f"Retrieving embedding for phone number: {phone_number}")
            embedded_doc = get_voice_embedding(phone_number)
            
            if embedded_doc is None:
                logger.warning(f"No enrollment found for phone number: {phone_number}")
                return None
            
            # Extract embedding array from document
            enrolled_embedding = np.array(embedded_doc.get("embedding", []), dtype=np.float32)
            
            # Create session
            session = StreamingVerificationSession(
                phone_number=phone_number,
                enrolled_embedding=enrolled_embedding,
                threshold=threshold
            )
            
            self.sessions[session.session_id] = session
            self.chunk_locks[session.session_id] = asyncio.Lock()
            
            session.status = StreamingVerificationStatus.READY
            session.started_at = datetime.utcnow()
            
            logger.info(f"Created streaming verification session: {session}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating verification session: {str(e)}")
            return None
    
    async def process_chunk(self, session_id: str, chunk_audio: bytes, sample_rate: int = 16000) -> Optional[Dict]:
        """
        Process incoming audio by accumulating into 5-second chunks.
        
        Args:
            session_id: Session ID
            chunk_audio: Audio data in bytes (WAV format)
            sample_rate: Sample rate of audio
            
        Returns:
            {
                "buffering": true/false,
                "buffer_duration": float,
                "chunk_number": int (when processed),
                "similarity_score": float (when processed),
                "is_match": bool (when processed),
                "final_status": str (when complete)
            }
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return None
        
        # Use lock to prevent concurrent chunk processing
        async with self.chunk_locks[session_id]:
            try:
                # Check if already completed
                if session.final_status is not None:
                    logger.warning(
                        f"Session {session_id} already completed with status: {session.final_status}"
                    )
                    return {
                        "final_status": session.final_status,
                        "verified_at_chunk": session.verified_at_chunk,
                        "chunk_number": session.chunks_processed,
                        "max_chunks": session.max_chunks
                    }
                
                # Calculate incoming chunk duration
                try:
                    import soundfile as sf
                    audio_data, _ = sf.read(io.BytesIO(chunk_audio))
                    
                    if isinstance(audio_data, list):
                        audio_data = np.array(audio_data)
                    
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    
                    chunk_duration = len(audio_data) / sample_rate
                except Exception as e:
                    logger.error(f"Error reading audio chunk: {str(e)}")
                    return {
                        "error": "Failed to read audio chunk",
                        "chunk_number": session.chunks_processed
                    }
                
                # Add chunk to buffer
                session.audio_buffer.append(chunk_audio)
                session.buffer_duration_seconds += chunk_duration
                session.sample_rate = sample_rate
                
                logger.debug(
                    f"Added {chunk_duration:.3f}s to buffer. "
                    f"Total buffer: {session.buffer_duration_seconds:.3f}s / {session.target_duration_seconds}s"
                )
                
                # Check if buffer has enough audio to process
                if session.buffer_duration_seconds < session.target_duration_seconds:
                    # Not enough data yet, return buffering status
                    return {
                        "type": "buffering",
                        "buffer_duration": session.buffer_duration_seconds,
                        "target_duration": session.target_duration_seconds,
                        "buffering": True
                    }
                
                # Buffer has 5+ seconds, process it
                session.status = StreamingVerificationStatus.PROCESSING_CHUNK
                session.chunks_processed += 1
                
                logger.info(
                    f"Buffer ready ({session.buffer_duration_seconds:.3f}s). "
                    f"Processing chunk {session.chunks_processed}/{session.max_chunks} for session {session_id[:8]}"
                )
                
                # Merge all buffered audio
                try:
                    merged_audio = self._merge_audio_chunks(session.audio_buffer, sample_rate)
                    
                    # Generate embedding for merged 5-second chunk
                    chunk_embedding = generate_embedding(merged_audio)
                    
                except Exception as e:
                    logger.error(f"Error generating embedding for chunk: {str(e)}")
                    session.status = StreamingVerificationStatus.ERROR
                    return {
                        "error": "Failed to generate embedding",
                        "chunk_number": session.chunks_processed
                    }
                
                # Compare with enrolled embedding
                similarity_score = float(calculate_cosine_similarity(
                    session.enrolled_embedding,
                    chunk_embedding
                ))
                
                logger.info(
                    f"Chunk {session.chunks_processed} similarity: {similarity_score:.4f} "
                    f"(threshold: {session.threshold:.2f})"
                )
                
                # Store result
                result = ChunkVerificationResult(
                    chunk_number=session.chunks_processed,
                    similarity_score=similarity_score,
                    is_match=similarity_score >= session.threshold,
                    embedding=chunk_embedding
                )
                session.chunk_results.append(result)
                
                # Clear buffer for next 5-second accumulation
                session.audio_buffer = []
                session.buffer_duration_seconds = 0.0
                
                # Prepare response
                response = {
                    "type": "chunk_result",
                    "chunk_number": session.chunks_processed,
                    "max_chunks": session.max_chunks,
                    "similarity_score": similarity_score,
                    "threshold": session.threshold,
                    "is_match": result.is_match,
                    "final_status": None
                }
                
                # Early exit: first matching chunk triggers immediate verification
                if result.is_match:
                    session.final_status = "verified"
                    session.verified_at_chunk = session.chunks_processed
                    session.status = StreamingVerificationStatus.VERIFIED
                    response["final_status"] = "verified"
                    self._save_session_to_database(session)
                elif session.chunks_processed >= session.max_chunks:
                    session.final_status = "unverified"
                    session.verified_at_chunk = None
                    session.status = StreamingVerificationStatus.UNVERIFIED
                    response["final_status"] = "unverified"
                    self._save_session_to_database(session)
                else:
                    session.status = StreamingVerificationStatus.RECORDING
                
                return response
                
            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                session.status = StreamingVerificationStatus.ERROR
                return {
                    "error": f"Error processing chunk: {str(e)}",
                    "chunk_number": session.chunks_processed
                }
    
    def _merge_audio_chunks(self, audio_chunks: List[bytes], sample_rate: int) -> bytes:
        """
        Merge multiple audio chunks into a single audio buffer.
        
        Args:
            audio_chunks: List of audio bytes
            sample_rate: Sample rate of audio
            
        Returns:
            Merged audio as bytes in WAV format
        """
        import soundfile as sf
        
        merged_audio = []
        
        # Read and concatenate all chunks
        for chunk_bytes in audio_chunks:
            try:
                audio_data, _ = sf.read(io.BytesIO(chunk_bytes))
                
                if isinstance(audio_data, list):
                    audio_data = np.array(audio_data)
                
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                merged_audio.append(audio_data)
            except Exception as e:
                logger.warning(f"Error reading chunk during merge: {str(e)}")
                continue
        
        # Concatenate all audio data
        if not merged_audio:
            raise ValueError("No valid audio chunks to merge")
        
        concatenated = np.concatenate(merged_audio)
        
        # Write merged audio to bytes
        output_buffer = io.BytesIO()
        sf.write(output_buffer, concatenated, sample_rate, format='WAV')
        output_buffer.seek(0)
        
        return output_buffer.read()
    
    async def cancel_session(self, session_id: str) -> bool:
        """Cancel a verification session"""
        session = self.sessions.get(session_id)
        if session:
            session.status = StreamingVerificationStatus.CANCELLED
            session.final_status = "cancelled"
            logger.info(f"Session {session_id} cancelled")
            # Save cancelled session to database
            self._save_session_to_database(session)
            return True
        return False
    
    def get_session(self, session_id: str) -> Optional[StreamingVerificationSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    def cleanup_session(self, session_id: str):
        """Clean up session resources"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.chunk_locks:
            del self.chunk_locks[session_id]
        logger.info(f"Cleaned up session {session_id}")
    
    def _save_session_to_database(self, session: StreamingVerificationSession):
        """
        Save verification session result to database
        
        Args:
            session: StreamingVerificationSession to save
        """
        try:
            # Calculate average similarity score from all chunks
            if session.chunk_results:
                avg_similarity = sum(r.similarity_score for r in session.chunk_results) / len(session.chunk_results)
                min_similarity = min(r.similarity_score for r in session.chunk_results)
                max_similarity = max(r.similarity_score for r in session.chunk_results)
            else:
                avg_similarity = 0.0
                min_similarity = 0.0
                max_similarity = 0.0
            
            # Determine session status
            session_status = "verified" if session.final_status == "verified" else "unverified"
            
            # Prepare session data for storage
            session_data = {
                "session_id": session.session_id,
                "phone_number": session.phone_number,
                "session_status": session_status,
                "created_at": session.created_at,
                "started_at": session.started_at,
                "verified_at": datetime.utcnow() if session.final_status == "verified" else None,
                "final_status": session.final_status,
                "verified_at_chunk": session.verified_at_chunk,
                "chunks_processed": session.chunks_processed,
                "max_chunks": session.max_chunks,
                "threshold": session.threshold,
                "average_similarity": float(avg_similarity),
                "min_similarity": float(min_similarity),
                "max_similarity": float(max_similarity),
                "is_match": session.final_status == "verified",
                "chunk_results": [
                    {
                        "chunk_number": r.chunk_number,
                        "similarity_score": float(r.similarity_score),
                        "is_match": r.is_match,
                        "timestamp": r.timestamp
                    }
                    for r in session.chunk_results
                ]
            }
            
            # Save to database
            doc_id = save_verified_session(session_data)
            logger.info(
                f"Saved verification session {session.session_id[:8]} to database "
                f"(status: {session.final_status}, avg_similarity: {avg_similarity:.4f})"
            )
            
            # Write to agent session cache so subsequent audio is routed to
            # voice-agent mode.  Use client_id when set, fall back to session_id.
            if session.final_status == "verified":
                cache_key = session.client_id or session.session_id
                try:
                    user_id = get_user_id_for_phone(session.phone_number)
                    if user_id is None:
                        # No embedding doc found — fall back so agent still runs.
                        logger.warning(
                            "No embedding _id found for phone=%s; using phone as user_id",
                            session.phone_number,
                        )
                        user_id = session.phone_number
                    agent_set_verified(
                        client_id=cache_key,
                        phone_number=session.phone_number,
                        user_id=user_id,
                    )
                    logger.info(
                        f"AgentSessionCache populated for client {cache_key[:8]} "
                        f"(phone={session.phone_number}, user_id={user_id})"
                    )
                except Exception as cache_err:
                    logger.warning(f"Failed to write AgentSessionCache: {cache_err}")

            return doc_id

        except Exception as e:
            logger.error(
                f"Failed to save session {session.session_id[:8]} to database: {str(e)}",
                exc_info=True
            )


# Global instance
_verification_manager: Optional[RealtimeVerificationManager] = None


def get_verification_streaming_manager() -> RealtimeVerificationManager:
    """Get or create the verification manager instance"""
    global _verification_manager
    if _verification_manager is None:
        _verification_manager = RealtimeVerificationManager()
    return _verification_manager
