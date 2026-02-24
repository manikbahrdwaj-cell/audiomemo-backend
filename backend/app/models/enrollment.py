from pydantic import BaseModel
from typing import Optional, List

class EnrollResponse(BaseModel):
    success: bool
    message: str
    phone_number: str
    vector_id: Optional[str] = None

class EnrollmentSessionResponse(BaseModel):
    session_id: str
    phone_number: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    chunks_collected: int
    max_chunks: int
    embeddings_generated: int
    verified: bool = False  # Whether the phone number is already enrolled
    error_message: Optional[str] = None

class AudioChunkResponse(BaseModel):
    chunk_id: str
    chunk_number: int
    total_chunks: int
    duration_seconds: float
    timestamp: str
    has_embedding: bool
    quality_score: float

class EnrollmentChunkAddResponse(BaseModel):
    success: bool
    message: str
    chunk: Optional[AudioChunkResponse] = None
    session_status: Optional[str] = None

class EnrollmentFinalizeResponse(BaseModel):
    success: bool
    message: str
    phone_number: str
    vector_id: Optional[str] = None
    chunks_processed: int
    enrollment_status: str