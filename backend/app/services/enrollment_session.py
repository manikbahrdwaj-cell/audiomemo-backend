"""
Enrollment session management for multi-chunk voice enrollment.
"""


import uuid
import io
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import numpy as np

from app.services.enrollment_config import EnrollmentSessionConfig
from app.services.enrollment_status import EnrollmentStatus
from app.services.enrollment_chunk import AudioChunkRecord
from app.ml.audio_merger import MergeMode, AudioMerger, AudioMergeConfig
from app.ml.embedding import generate_embedding_with_chunking
from app.db.embeddings import store_voice_embedding

logger = logging.getLogger(__name__)


@dataclass
class EnrollmentSession:
    """Session for managing voice enrollment with multiple chunks"""
    session_id: str
    phone_number: str
    config: EnrollmentSessionConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: EnrollmentStatus = EnrollmentStatus.INITIALIZING
    error_message: Optional[str] = None
    
    # Audio chunks collected during session
    chunks: List[AudioChunkRecord] = field(default_factory=list)
    
    # Aggregated embeddings
    embeddings: List[np.ndarray] = field(default_factory=list)
    merged_embedding: Optional[np.ndarray] = None
    
    # Audio merging fields
    merged_audio: Optional[np.ndarray] = None  # Merged audio from all chunks
    merged_audio_sample_rate: int = 16000
    merged_audio_timestamp: Optional[datetime] = None
    merged_audio_embedding: Optional[np.ndarray] = None  # Embedding from merged audio
    
    # Session metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_chunk(self, audio_data: np.ndarray, duration_seconds: float, 
                  sample_rate: int = 16000, quality_score: float = 1.0) -> AudioChunkRecord:
        """
        Add an audio chunk to the session
        
        Args:
            audio_data: Audio waveform as numpy array
            duration_seconds: Duration of the audio in seconds
            sample_rate: Sample rate of the audio
            quality_score: Quality confidence score (0-1)
            
        Returns:
            AudioChunkRecord with chunk details
            
        Raises:
            ValueError: If session is full or invalid state
        """
        if self.status not in [EnrollmentStatus.ACTIVE, EnrollmentStatus.COLLECTING]:
            raise ValueError(f"Cannot add chunks in {self.status} state")
        
        if len(self.chunks) >= self.config.max_chunks:
            raise ValueError(f"Session has reached max chunks limit ({self.config.max_chunks})")
        
        if quality_score < self.config.quality_threshold:
            logger.warning(f"Audio quality score {quality_score} below threshold {self.config.quality_threshold}")
        
        # Create chunk record
        chunk = AudioChunkRecord(
            chunk_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            duration_seconds=duration_seconds,
            audio_data=audio_data,
            sample_rate=sample_rate,
            quality_score=quality_score
        )
        
        self.chunks.append(chunk)
        self.status = EnrollmentStatus.COLLECTING
        
        logger.info(
            f"Added chunk {len(self.chunks)}/{self.config.max_chunks} "
            f"to session {self.session_id[:8]}: {duration_seconds:.2f}s"
        )
        
        return chunk
    
    def process_chunk(self, chunk_idx: int) -> Optional[np.ndarray]:
        """
        Generate embedding for a specific chunk
        
        Uses 1-second audio chunks (16,000 samples at 16kHz) for enrollment
        to capture fine-grained voice characteristics
        
        Args:
            chunk_idx: Index of chunk to process
            
        Returns:
            Generated embedding or None if failed
        """
        if chunk_idx >= len(self.chunks):
            raise IndexError(f"Chunk index {chunk_idx} out of range")
        
        chunk = self.chunks[chunk_idx]
        
        try:
            # Convert numpy array to bytes for embedding generation
            audio_bytes = io.BytesIO()
            # For embedding generation, we need WAV format
            # Create a simple WAV header and append the audio data
            import soundfile as sf
            sf.write(audio_bytes, chunk.audio_data, chunk.sample_rate, format='WAV')
            audio_bytes.seek(0)
            
            # Generate embedding with 1-second chunks for enrollment
            # 1-second chunks = 16,000 samples at 16kHz
            embedding = generate_embedding_with_chunking(
                audio_bytes.read(),
                chunk_size_seconds=1.0,          # 1-second chunks
                overlap_ratio=0.2,               # 20% overlap
                aggregation_method='mean'        # Average chunk embeddings
            )
            
            chunk.embedding = embedding
            chunk.embedding_timestamp = datetime.utcnow()
            
            self.embeddings.append(embedding)
            
            logger.info(
                f"Processed chunk {chunk_idx + 1}/{len(self.chunks)} "
                f"for session {self.session_id[:8]}: "
                f"embedding shape {embedding.shape} "
                f"(1-second chunking mode)"
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx}: {str(e)}")
            chunk.error = str(e)
            return None
    
    def process_all_chunks(self) -> List[np.ndarray]:
        """
        Process all chunks in the session
        
        Returns:
            List of generated embeddings
        """
        logger.info(f"Processing {len(self.chunks)} chunks for session {self.session_id[:8]}")
        
        self.status = EnrollmentStatus.PROCESSING
        
        processed = []
        for idx in range(len(self.chunks)):
            embedding = self.process_chunk(idx)
            if embedding is not None:
                processed.append(embedding)
        
        logger.info(f"Successfully processed {len(processed)}/{len(self.chunks)} chunks")
        
        return processed
    
    def merge_audio_chunks(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Merge all collected audio chunks into a single audio file
        
        Returns:
            Tuple of (success, message, merged_audio)
        """
        if not self.chunks:
            return False, "No audio chunks to merge", None
        
        if len(self.chunks) == 1:
            # Single chunk - no merge needed
            self.merged_audio = self.chunks[0].audio_data
            self.merged_audio_sample_rate = self.chunks[0].sample_rate
            self.merged_audio_timestamp = datetime.utcnow()
            logger.info(f"Single chunk detected - no merge needed")
            return True, "Single chunk (no merge required)", self.merged_audio
        
        try:
            logger.info(
                f"Merging {len(self.chunks)} audio chunks for session {self.session_id[:8]} "
                f"using {self.config.audio_merge_mode.value} mode"
            )
            
            # Create audio merger with configured settings
            merge_config = AudioMergeConfig(
                mode=self.config.audio_merge_mode,
                sample_rate=16000,
                crossfade_duration_ms=self.config.audio_merge_crossfade_ms,
                overlap_duration_ms=self.config.audio_merge_crossfade_ms
            )
            
            merger = AudioMerger(merge_config)
            
            # Extract audio data and sample rates from chunks
            audio_segments = [chunk.audio_data for chunk in self.chunks]
            sample_rates = [chunk.sample_rate for chunk in self.chunks]
            
            # Merge audio segments
            merged_audio, sample_rate = merger.merge_audio_segments(
                audio_segments,
                sample_rates
            )
            
            self.merged_audio = merged_audio
            self.merged_audio_sample_rate = sample_rate
            self.merged_audio_timestamp = datetime.utcnow()
            
            total_duration = len(merged_audio) / sample_rate
            orig_duration = sum(chunk.duration_seconds for chunk in self.chunks)
            
            logger.info(
                f"✓ Successfully merged {len(self.chunks)} chunks into {len(merged_audio)} samples "
                f"({total_duration:.2f}s, original total: {orig_duration:.2f}s)"
            )
            
            return True, f"Merged {len(self.chunks)} chunks successfully", merged_audio
            
        except Exception as e:
            error_msg = f"Error merging audio chunks: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def generate_embedding_from_merged_audio(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Generate embedding from merged audio
        
        Returns:
            Tuple of (success, message, embedding)
        """
        if self.merged_audio is None:
            return False, "No merged audio available - merge chunks first", None
        
        try:
            logger.info(
                f"Generating embedding from merged audio "
                f"({len(self.merged_audio)} samples, {self.merged_audio_sample_rate} Hz)"
            )
            
            # Convert audio to WAV bytes for embedding generation
            audio_bytes = io.BytesIO()
            import soundfile as sf
            sf.write(
                audio_bytes,
                self.merged_audio,
                self.merged_audio_sample_rate,
                format='WAV'
            )
            audio_bytes.seek(0)
            
            # Generate embedding with 1-second chunks for enrollment
            # 1-second chunks = 16,000 samples at 16kHz
            embedding = generate_embedding_with_chunking(
                audio_bytes.read(),
                chunk_size_seconds=1.0,          # 1-second chunks
                overlap_ratio=0.2,               # 20% overlap
                aggregation_method='mean'        # Average chunk embeddings
            )
            
            self.merged_audio_embedding = embedding
            
            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                self.merged_audio_embedding = embedding / norm
            
            logger.info(
                f"✓ Generated embedding from merged audio: shape {self.merged_audio_embedding.shape}"
            )
            
            return True, "Embedding generated successfully", self.merged_audio_embedding
            
        except Exception as e:
            error_msg = f"Error generating embedding from merged audio: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def merge_and_generate_embedding(self) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Complete workflow: merge audio chunks and generate single embedding
        
        Returns:
            Tuple of (success, message, embedding)
        """
        logger.info(
            f"Starting merge and generate workflow for session {self.session_id[:8]}"
        )
        
        self.status = EnrollmentStatus.PROCESSING
        
        # Step 1: Merge audio chunks
        success, message, merged_audio = self.merge_audio_chunks()
        if not success:
            logger.error(f"Failed to merge audio: {message}")
            return False, f"Audio merge failed: {message}", None
        
        # Step 2: Generate embedding from merged audio
        success, message, embedding = self.generate_embedding_from_merged_audio()
        if not success:
            logger.error(f"Failed to generate embedding: {message}")
            return False, f"Embedding generation failed: {message}", None
        
        logger.info(
            f"✓ Merge and generate workflow completed successfully"
        )
        
        return True, "Merge and embedding generation successful", embedding
    
    def merge_embeddings_strategy(self) -> Optional[np.ndarray]:
        """
        Merge multiple embeddings using configured strategy
        
        Returns:
            Merged embedding or None if failed
        """
        if not self.embeddings:
            logger.warning("No embeddings to merge")
            return None
        
        if len(self.embeddings) == 1:
            self.merged_embedding = self.embeddings[0]
            return self.merged_embedding
        
        try:
            # Stack embeddings for averaging
            embedding_matrix = np.array(self.embeddings)  # Shape: (n_chunks, 192)
            
            if self.config.merge_mode == MergeMode.CONCATENATE:
                # Average embeddings (most common for voice biometrics)
                self.merged_embedding = np.mean(embedding_matrix, axis=0)
                logger.info(f"Merged {len(self.embeddings)} embeddings using averaging")
                
            elif self.config.merge_mode == MergeMode.OVERLAP:
                # Weighted average giving more weight to recent chunks
                weights = np.linspace(0.5, 1.0, len(self.embeddings))
                weights = weights / weights.sum()
                self.merged_embedding = np.average(embedding_matrix, axis=0, weights=weights)
                logger.info(f"Merged {len(self.embeddings)} embeddings with time-weighted averaging")
                
            elif self.config.merge_mode == MergeMode.MIX:
                # Simple averaging (same as CONCATENATE for embeddings)
                self.merged_embedding = np.mean(embedding_matrix, axis=0)
                logger.info(f"Merged {len(self.embeddings)} embeddings using averaging")
            
            else:
                # Default to averaging
                self.merged_embedding = np.mean(embedding_matrix, axis=0)
                logger.info(f"Merged {len(self.embeddings)} embeddings using default averaging")
            
            # Normalize the merged embedding
            norm = np.linalg.norm(self.merged_embedding)
            if norm > 0:
                self.merged_embedding = self.merged_embedding / norm
            
            return self.merged_embedding
            
        except Exception as e:
            logger.error(f"Error merging embeddings: {str(e)}")
            return None
    
    def finalize_enrollment(self, force_single: bool = False) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Finalize enrollment by storing the merged embedding
        Supports both embedding merging and audio merging strategies
        
        Args:
            force_single: Use single best embedding if merge fails
            
        Returns:
            Tuple of (success, message, final_embedding)
        """
        self.status = EnrollmentStatus.FINALIZING
        
        # Check minimum chunks requirement
        if len(self.chunks) < self.config.min_chunks_required:
            return False, f"Insufficient chunks. Need {self.config.min_chunks_required}, got {len(self.chunks)}", None
        
        final_embedding = None
        embedding_source = None
        
        # Strategy 1: Use merged audio embedding if configured and chunks > 1
        if self.config.merge_audio and len(self.chunks) > 1:
            logger.info("Using audio merge strategy")
            success, message, embedding = self.merge_and_generate_embedding()
            if success and embedding is not None:
                final_embedding = embedding
                embedding_source = f"merged_audio({len(self.chunks)}_chunks)"
                logger.info(f"✓ Using embedding from merged audio ({len(self.chunks)} chunks)")
            else:
                logger.warning(f"Audio merge strategy failed: {message}. Falling back to embedding merge.")
        
        # Strategy 2: Use merged embeddings if audio merge failed or not configured
        if final_embedding is None:
            # Process any unprocessed chunks
            if len(self.embeddings) < len(self.chunks):
                self.process_all_chunks()
            
            # Check if we have any valid embeddings
            if not self.embeddings:
                return False, "No valid embeddings generated", None
            
            # Merge embeddings if configured
            if self.config.merge_embeddings and len(self.embeddings) > 1:
                final_embedding = self.merge_embeddings_strategy()
                
                if final_embedding is None and not force_single:
                    return False, "Failed to merge embeddings", None
                elif final_embedding is None:
                    # Fall back to best embedding
                    final_embedding = self.embeddings[0]
                    embedding_source = "best_single_embedding"
                    logger.warning("Using single best embedding due to merge failure")
                else:
                    embedding_source = f"merged_embeddings({len(self.embeddings)}_embeddings)"
            else:
                # Use first (or only) embedding
                final_embedding = self.embeddings[0]
                embedding_source = "single_embedding"
        
        # Check for duplicate enrollment (prevent re-enrollment)
        from app.db.embeddings import check_enrollment
        if check_enrollment(self.phone_number):
            error_msg = f"Phone number {self.phone_number} is already enrolled. Re-enrollment is not allowed."
            logger.warning(error_msg)
            self.status = EnrollmentStatus.ERROR
            self.error_message = error_msg
            return False, error_msg, None
        
        # Store in database
        try:
            vector_id = store_voice_embedding(self.phone_number, final_embedding)
            
            self.merged_embedding = final_embedding
            self.status = EnrollmentStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            
            logger.info(
                f"✓ Enrollment completed for {self.phone_number}. "
                f"Session: {self.session_id[:8]}, Vector ID: {vector_id[:8]}, "
                f"Chunks: {len(self.chunks)}, Source: {embedding_source}"
            )
            
            return True, f"Enrollment completed with {len(self.chunks)} chunk(s) - {embedding_source}", final_embedding
            
        except Exception as e:
            error_msg = f"Failed to store embedding: {str(e)}"
            logger.error(error_msg)
            self.status = EnrollmentStatus.ERROR
            self.error_message = error_msg
            return False, error_msg, None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "chunks_collected": len(self.chunks),
            "max_chunks": self.config.max_chunks,
            "embeddings_generated": len(self.embeddings),
            "has_merged_embedding": self.merged_embedding is not None,
            "has_merged_audio": self.merged_audio is not None,
            "merged_audio_duration_seconds": len(self.merged_audio) / self.merged_audio_sample_rate if self.merged_audio is not None else None,
            "has_merged_audio_embedding": self.merged_audio_embedding is not None,
            "merged_audio_timestamp": self.merged_audio_timestamp.isoformat() if self.merged_audio_timestamp else None,
            "merge_audio_enabled": self.config.merge_audio,
            "audio_merge_mode": self.config.audio_merge_mode.value,
            "error_message": self.error_message,
            "chunks": [chunk.to_dict() for chunk in self.chunks]
        }
    
    def cleanup(self) -> None:
        """Clean up session resources (especially audio data if not storing)"""
        if not self.config.store_chunks:
            for chunk in self.chunks:
                chunk.audio_data = None
            logger.info(f"Cleaned up audio data for session {self.session_id[:8]}")