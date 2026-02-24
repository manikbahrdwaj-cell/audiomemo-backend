"""
Chunk Progress Dispatcher Module
Handles real-time progress updates for audio chunk processing via WebSocket
"""

import logging
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ChunkProcessingStatus(Enum):
    """Status of chunk processing operations"""
    PENDING = "pending"
    STARTED = "started"
    PROCESSING_CHUNK = "processing_chunk"
    EMBEDDING_GENERATED = "embedding_generated"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ChunkProgress:
    """Data class for chunk processing progress"""
    session_id: str
    status: ChunkProcessingStatus
    current_chunk: int = 0
    total_chunks: int = 0
    percentage: float = 0.0
    duration_ms: float = 0.0
    chunks_processed: List[Dict[str, Any]] = None
    current_chunk_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.chunks_processed is None:
            self.chunks_processed = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_chunk": self.current_chunk,
            "total_chunks": self.total_chunks,
            "percentage": round(self.percentage, 2),
            "duration_ms": round(self.duration_ms, 2),
            "chunks_processed": self.chunks_processed,
            "current_chunk_info": self.current_chunk_info,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


class ChunkProgressDispatcher:
    """
    Manages and dispatches real-time progress updates for chunk processing
    
    Features:
    - Track progress across multiple sessions
    - Emit events to multiple subscribers
    - Support async callbacks
    - Rate limiting for progress updates
    """
    
    def __init__(self, update_throttle_ms: int = 100):
        """
        Initialize ChunkProgressDispatcher
        
        Args:
            update_throttle_ms: Minimum milliseconds between progress updates
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.update_throttle_ms = update_throttle_ms
        self.last_update_time: Dict[str, float] = {}
    
    def create_session(self, session_id: str, total_chunks: int) -> None:
        """
        Create a new tracking session for chunk processing
        
        Args:
            session_id: Unique identifier for the session
            total_chunks: Total number of chunks to process
        """
        self.sessions[session_id] = {
            "total_chunks": total_chunks,
            "current_chunk": 0,
            "chunks_processed": [],
            "start_time": datetime.now(),
            "status": ChunkProcessingStatus.PENDING,
            "error": None,
        }
        self.last_update_time[session_id] = 0
        logger.info(f"Session {session_id} created with {total_chunks} chunks")
    
    def start_processing(self, session_id: str) -> None:
        """Mark session as started"""
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = ChunkProcessingStatus.STARTED
            self.sessions[session_id]["start_time"] = datetime.now()
    
    async def update_chunk_progress(
        self,
        session_id: str,
        chunk_index: int,
        chunk_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update progress for a single chunk
        
        Args:
            session_id: Session identifier
            chunk_index: Index of current chunk (0-based)
            chunk_info: Optional metadata about the chunk
        """
        if session_id not in self.sessions:
            logger.warning(f"Unknown session: {session_id}")
            return
        
        session = self.sessions[session_id]
        session["status"] = ChunkProcessingStatus.PROCESSING_CHUNK
        session["current_chunk"] = chunk_index
        
        chunk_data = {
            "chunk_index": chunk_index,
            "timestamp": datetime.now().isoformat(),
        }
        if chunk_info:
            chunk_data.update(chunk_info)
        
        session["chunks_processed"].append(chunk_data)
        
        # Create progress object
        total_chunks = session["total_chunks"]
        percentage = ((chunk_index + 1) / total_chunks * 100) if total_chunks > 0 else 0
        duration_ms = (datetime.now() - session["start_time"]).total_seconds() * 1000
        
        progress = ChunkProgress(
            session_id=session_id,
            status=ChunkProcessingStatus.PROCESSING_CHUNK,
            current_chunk=chunk_index + 1,
            total_chunks=total_chunks,
            percentage=percentage,
            duration_ms=duration_ms,
            chunks_processed=session["chunks_processed"],
            current_chunk_info=chunk_data,
        )
        
        # Emit with throttling
        await self._emit_progress(progress)
    
    async def mark_chunk_embedded(
        self,
        session_id: str,
        chunk_index: int,
        embedding_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark a chunk as having its embedding generated
        
        Args:
            session_id: Session identifier
            chunk_index: Index of chunk with embedding
            embedding_info: Optional metadata about the embedding
        """
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        # Update last chunk info
        if session["chunks_processed"] and session["chunks_processed"][-1].get("chunk_index") == chunk_index:
            if embedding_info:
                session["chunks_processed"][-1].update(embedding_info)
        
        total_chunks = session["total_chunks"]
        percentage = ((chunk_index + 1) / total_chunks * 100) if total_chunks > 0 else 0
        duration_ms = (datetime.now() - session["start_time"]).total_seconds() * 1000
        
        progress = ChunkProgress(
            session_id=session_id,
            status=ChunkProcessingStatus.EMBEDDING_GENERATED,
            current_chunk=chunk_index + 1,
            total_chunks=total_chunks,
            percentage=percentage,
            duration_ms=duration_ms,
            chunks_processed=session["chunks_processed"],
            current_chunk_info={"chunk_index": chunk_index, "embedding_generated": True},
        )
        
        await self._emit_progress(progress)
    
    async def mark_completed(self, session_id: str) -> None:
        """Mark processing as completed"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        duration_ms = (datetime.now() - session["start_time"]).total_seconds() * 1000
        
        progress = ChunkProgress(
            session_id=session_id,
            status=ChunkProcessingStatus.COMPLETED,
            current_chunk=session["current_chunk"],
            total_chunks=session["total_chunks"],
            percentage=100.0,
            duration_ms=duration_ms,
            chunks_processed=session["chunks_processed"],
        )
        
        session["status"] = ChunkProcessingStatus.COMPLETED
        await self._emit_progress(progress)
        
        # Clean up old session after a delay
        asyncio.create_task(self._cleanup_session_delayed(session_id, delay_seconds=5))
    
    async def mark_failed(self, session_id: str, error_message: str) -> None:
        """Mark processing as failed"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        session["status"] = ChunkProcessingStatus.FAILED
        session["error"] = error_message
        duration_ms = (datetime.now() - session["start_time"]).total_seconds() * 1000
        
        progress = ChunkProgress(
            session_id=session_id,
            status=ChunkProcessingStatus.FAILED,
            current_chunk=session["current_chunk"],
            total_chunks=session["total_chunks"],
            percentage=0.0,
            duration_ms=duration_ms,
            chunks_processed=session["chunks_processed"],
            error_message=error_message,
        )
        
        await self._emit_progress(progress)
        
        # Clean up after delay
        asyncio.create_task(self._cleanup_session_delayed(session_id, delay_seconds=3))
    
    async def subscribe(self, callback: Callable) -> str:
        """
        Subscribe to progress updates
        
        Args:
            callback: Async callable that accepts ChunkProgress
            
        Returns:
            Subscriber ID for unsubscribing
        """
        import uuid
        subscriber_id = str(uuid.uuid4())
        if "progress" not in self.subscribers:
            self.subscribers["progress"] = []
        self.subscribers["progress"].append(callback)
        logger.debug(f"Subscriber registered: {subscriber_id}")
        return subscriber_id
    
    async def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from progress updates"""
        if "progress" in self.subscribers:
            try:
                self.subscribers["progress"].remove(callback)
            except ValueError:
                pass
    
    async def _emit_progress(self, progress: ChunkProgress) -> None:
        """Emit progress to all subscribers"""
        if "progress" not in self.subscribers:
            return
        
        # Check throttling
        import time
        current_time = time.time() * 1000
        last_time = self.last_update_time.get(progress.session_id, 0)
        
        if current_time - last_time < self.update_throttle_ms:
            return
        
        self.last_update_time[progress.session_id] = current_time
        
        # Emit to all subscribers
        tasks = []
        for callback in self.subscribers.get("progress", []):
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(progress))
            else:
                try:
                    callback(progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {str(e)}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _cleanup_session_delayed(self, session_id: str, delay_seconds: int = 5) -> None:
        """Clean up session after a delay"""
        await asyncio.sleep(delay_seconds)
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.last_update_time:
            del self.last_update_time[session_id]
        logger.debug(f"Session {session_id} cleaned up")
    
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a session"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        duration_ms = (datetime.now() - session["start_time"]).total_seconds() * 1000
        total_chunks = session["total_chunks"]
        percentage = ((session["current_chunk"] + 1) / total_chunks * 100) if total_chunks > 0 else 0
        
        return {
            "session_id": session_id,
            "status": session["status"].value,
            "current_chunk": session["current_chunk"],
            "total_chunks": total_chunks,
            "percentage": round(percentage, 2),
            "duration_ms": round(duration_ms, 2),
            "chunks_processed": len(session["chunks_processed"]),
            "error": session["error"],
        }


# Global instance
_dispatcher_instance: Optional[ChunkProgressDispatcher] = None


def get_chunk_progress_dispatcher() -> ChunkProgressDispatcher:
    """Get or create global dispatcher instance"""
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = ChunkProgressDispatcher()
    return _dispatcher_instance
