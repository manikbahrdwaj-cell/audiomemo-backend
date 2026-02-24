from fastapi import APIRouter
from app.models.common import HealthResponse, CheckResponse
from app.db.embeddings import check_enrollment

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Voice Biometric API is running"
    )


@router.get("/check/{phone_number}", response_model=CheckResponse)
async def check_enrollment_status(phone_number: str):
    """
    Check if a phone number is enrolled
    
    - Returns enrollment status for the given phone number
    """
    from app.db.embeddings import check_enrollment
    
    enrolled = check_enrollment(phone_number)
    
    return CheckResponse(
        phone_number=phone_number,
        enrolled=enrolled
    )