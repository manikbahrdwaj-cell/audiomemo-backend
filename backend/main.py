"""
Voice Biometric Authentication API
FastAPI backend for voice enrollment and verification
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging

from voice_embedding import generate_embedding, calculate_cosine_similarity
from database import (
    store_voice_embedding,
    get_voice_embedding,
    check_enrollment,
    find_nearest_embedding
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Voice Biometric API",
    description="Voice enrollment and verification using ECAPA-TDNN embeddings",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class EnrollResponse(BaseModel):
    success: bool
    message: str
    phone_number: str
    vector_id: Optional[str] = None

class VerifyResponse(BaseModel):
    success: bool
    phone_number: str
    similarity_score: float
    is_match: bool
    threshold: float

class CheckResponse(BaseModel):
    phone_number: str
    enrolled: bool

class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Voice Biometric API is running"
    )


@app.post("/enroll", response_model=EnrollResponse)
async def enroll_voice(
    phone_number: str = Form(..., description="Unique identifier (phone number)"),
    file: UploadFile = File(..., description="WAV audio file for enrollment")
):
    """
    Enroll a new voice identity
    
    - Receives phone_number and audio file
    - Generates 192-dimensional ECAPA-TDNN embedding
    - Stores embedding in MongoDB
    """
    logger.info(f"Enrollment request for phone number: {phone_number}")
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.WAV')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a WAV file."
        )
    
    try:
        # Read audio file
        audio_bytes = await file.read()
        
        if len(audio_bytes) < 1000:
            raise HTTPException(
                status_code=400,
                detail="Audio file too small. Please record a longer sample."
            )
        
        logger.info(f"Processing audio file: {len(audio_bytes)} bytes")
        
        # Generate voice embedding
        embedding = generate_embedding(audio_bytes)
        logger.info(f"Generated embedding with shape: {embedding.shape}")
        
        # Store in MongoDB
        vector_id = store_voice_embedding(phone_number, embedding)
        logger.info(f"Stored embedding with ID: {vector_id}")
        
        return EnrollResponse(
            success=True,
            message="Voice enrolled successfully",
            phone_number=phone_number,
            vector_id=vector_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enrollment failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process voice enrollment: {str(e)}"
        )


@app.post("/verify", response_model=VerifyResponse)
async def verify_voice(
    phone_number: str = Form(..., description="Phone number to verify against"),
    file: UploadFile = File(..., description="WAV audio file for verification")
):
    """
    Verify a voice against enrolled identity
    
    - Receives phone_number and audio file
    - Generates query embedding from audio
    - Compares against stored embedding using cosine similarity
    - Returns confidence score
    """
    logger.info(f"Verification request for phone number: {phone_number}")
    
    # Similarity threshold for positive match
    SIMILARITY_THRESHOLD = 0.75
    
    # Check if phone number is enrolled
    if not check_enrollment(phone_number):
        raise HTTPException(
            status_code=404,
            detail=f"Phone number {phone_number} is not enrolled. Please enroll first."
        )
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.WAV')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a WAV file."
        )
    
    try:
        # Read audio file
        audio_bytes = await file.read()
        
        if len(audio_bytes) < 1000:
            raise HTTPException(
                status_code=400,
                detail="Audio file too small. Please record a longer sample."
            )
        
        logger.info(f"Processing verification audio: {len(audio_bytes)} bytes")
        
        # Generate query embedding
        query_embedding = generate_embedding(audio_bytes)
        logger.info(f"Generated query embedding with shape: {query_embedding.shape}")
        
        # Find nearest match for this phone number
        results = find_nearest_embedding(
            query_embedding=query_embedding,
            phone_number=phone_number,
            limit=1
        )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No embedding found for phone number: {phone_number}"
            )
        
        similarity_score = results[0]["similarity_score"]
        is_match = similarity_score >= SIMILARITY_THRESHOLD
        
        logger.info(f"Verification result: score={similarity_score:.4f}, match={is_match}")
        
        return VerifyResponse(
            success=True,
            phone_number=phone_number,
            similarity_score=similarity_score,
            is_match=is_match,
            threshold=SIMILARITY_THRESHOLD
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process voice verification: {str(e)}"
        )


@app.get("/check/{phone_number}", response_model=CheckResponse)
async def check_enrollment_status(phone_number: str):
    """
    Check if a phone number is enrolled
    
    - Returns enrollment status for the given phone number
    """
    logger.info(f"Checking enrollment status for: {phone_number}")
    
    enrolled = check_enrollment(phone_number)
    
    return CheckResponse(
        phone_number=phone_number,
        enrolled=enrolled
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
