from pydantic import BaseModel
from typing import Optional, List

class VerifyResponse(BaseModel):
    success: bool
    phone_number: str
    similarity_score: float
    is_match: bool
    threshold: float

class VerificationSessionResponse(BaseModel):
    session_id: str
    phone_number: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    chunks_collected: int
    max_chunks: int
    verified: bool = True  # Whether the phone number is enrolled
    error_message: Optional[str] = None

class VerificationChunkResponse(BaseModel):
    chunk_id: str
    chunk_number: int
    total_chunks: int
    duration_seconds: float
    timestamp: str
    has_embedding: bool
    quality_score: float

class VerificationChunkAddResponse(BaseModel):
    success: bool
    message: str
    chunk: Optional[VerificationChunkResponse] = None
    session_status: Optional[str] = None

class VerificationFinalizeResponse(BaseModel):
    success: bool
    message: str
    phone_number: str
    chunks_processed: int
    average_similarity: float
    min_similarity: float
    max_similarity: float
    threshold: float
    is_match: bool
    verification_status: str