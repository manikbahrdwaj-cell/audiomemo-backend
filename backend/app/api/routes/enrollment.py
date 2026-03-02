import logging

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from app.models.enrollment import (
    EnrollmentSessionResponse,
    AudioChunkResponse,
    EnrollmentChunkAddResponse,
    EnrollmentFinalizeResponse
)
from app.services.enrollment import (
    get_enrollment_manager,
    create_enrollment_session,
    get_enrollment_session,
    add_audio_chunk,
    finalize_enrollment,
    EnrollmentSessionConfig,
    get_confirmation_service
)
from app.db.embeddings import store_voice_embedding, get_voice_embedding, check_enrollment
from app.ml.embedding import generate_embedding

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/enrollment/session", response_model=EnrollmentSessionResponse)
async def create_new_enrollment_session(
    phone_number: str,
    max_chunks: int = 5,
    merge_embeddings: bool = True
):
    """
    Create a new enrollment session for collecting multiple audio chunks
    
    - Initializes a session to collect voice samples from the user
    - Returns session ID for tracking chunk uploads
    - Each session can collect up to max_chunks audio samples
    - Prevents duplicate enrollment of the same phone number
    - Returns existing active session if one already exists for the same mobile number
    
    Args:
        phone_number: Unique identifier (phone number)
        max_chunks: Maximum number of chunks to collect (default: 5)
        merge_embeddings: Whether to merge embeddings from multiple chunks
        
    Returns:
        EnrollmentSessionResponse with session details
        
    Raises:
        HTTPException: 409 Conflict if phone number already enrolled
    """
    from app.db.embeddings import check_enrollment

    logger.info(
        "create_new_enrollment_session() | phone=%s max_chunks=%d merge=%s",
        phone_number,
        max_chunks,
        merge_embeddings,
    )

    # Check if phone number is already enrolled (duplicate prevention)
    is_enrolled = check_enrollment(phone_number)
    if is_enrolled:
        logger.warning("Duplicate enrollment attempt | phone=%s", phone_number)
        raise HTTPException(
            status_code=409,
            detail="This number is already enrolled. Duplicate enrollment is not allowed.",
        )

    # Check for existing active session with the same phone number
    enrollment_manager = get_enrollment_manager()
    existing_session = enrollment_manager.find_session_by_phone(phone_number)

    if existing_session:
        logger.info(
            "Returning existing enrollment session | phone=%s session_id=%s",
            phone_number,
            existing_session.session_id,
        )
        return EnrollmentSessionResponse(
            session_id=existing_session.session_id,
            phone_number=existing_session.phone_number,
            status=existing_session.status.value,
            created_at=existing_session.created_at.isoformat(),
            started_at=existing_session.started_at.isoformat() if existing_session.started_at else None,
            chunks_collected=len(existing_session.chunks),
            max_chunks=existing_session.config.max_chunks,
            embeddings_generated=len(existing_session.embeddings),
            verified=False,
            error_message=None,
        )

    # Create session configuration
    config = EnrollmentSessionConfig(
        max_chunks=max_chunks,
        merge_embeddings=merge_embeddings,
        store_chunks=True,
    )

    # Create session
    session = create_enrollment_session(phone_number, config)
    logger.info(
        "Enrollment session created | phone=%s session_id=%s max_chunks=%d",
        phone_number,
        session.session_id,
        max_chunks,
    )

    return EnrollmentSessionResponse(
        session_id=session.session_id,
        phone_number=session.phone_number,
        status=session.status.value,
        created_at=session.created_at.isoformat(),
        started_at=session.started_at.isoformat() if session.started_at else None,
        chunks_collected=0,
        max_chunks=max_chunks,
        embeddings_generated=0,
        verified=False,  # Phone number not enrolled yet
        error_message=None
    )


@router.post("/enrollment/session/{session_id}/chunk", response_model=EnrollmentChunkAddResponse)
async def add_audio_chunk_to_session(
    session_id: str,
    file: UploadFile = File(..., description="WAV audio file"),
    quality_score: float = 1.0
):
    """
    Add an audio chunk to an active enrollment session
    
    - Upload a single audio chunk for enrollment
    - Can call this endpoint multiple times with different audio samples
    - Each chunk is processed into a voice embedding
    
    Args:
        session_id: Session ID from create_enrollment_session
        file: WAV audio file
        quality_score: Optional quality confidence score (0-1)
        
    Returns:
        EnrollmentChunkAddResponse with chunk details and session status
    """
    from app.db.embeddings import check_enrollment
    from app.services.enrollment import get_enrollment_session
    from app.services.enrollment import add_audio_chunk
    import soundfile as sf
    import numpy as np
    import io

    logger.info(
        "add_audio_chunk_to_session() | session_id=%s filename=%s quality_score=%.2f",
        session_id,
        file.filename,
        quality_score,
    )

    # Validate file type
    if not file.filename.endswith(('.wav', '.WAV')):
        logger.warning("Invalid file type | session_id=%s filename=%s", session_id, file.filename)
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a WAV file.",
        )

    # Get session
    session = get_enrollment_session(session_id)
    if not session:
        logger.warning("Session not found | session_id=%s", session_id)
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    try:
        # Read audio file
        audio_bytes = await file.read()
        logger.debug(
            "Audio file read | session_id=%s size=%d bytes", session_id, len(audio_bytes)
        )

        if len(audio_bytes) < 1000:
            logger.warning(
                "Audio file too small | session_id=%s size=%d bytes", session_id, len(audio_bytes)
            )
            raise HTTPException(
                status_code=400,
                detail="Audio file too small. Please record a longer sample.",
            )

        # Load audio using soundfile
        audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))

        # Convert to numpy array if needed
        if isinstance(audio_data, list):
            audio_data = np.array(audio_data)

        # Ensure mono audio
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Calculate duration
        duration_seconds = len(audio_data) / sample_rate
        quality_score = max(0.0, min(1.0, quality_score))

        logger.info(
            "Audio loaded | session_id=%s duration=%.3fs sample_rate=%d channels=%s quality=%.2f",
            session_id,
            duration_seconds,
            sample_rate,
            "mono" if len(audio_data.shape) == 1 else f"{audio_data.shape[1]}ch",
            quality_score,
        )

        # Add chunk to session
        logger.debug("Adding chunk to enrollment session | session_id=%s", session_id)
        success, message, chunk = add_audio_chunk(
            session_id,
            audio_data,
            duration_seconds,
            sample_rate,
            quality_score,
        )

        if not success:
            logger.warning(
                "Failed to add chunk | session_id=%s reason=%s", session_id, message
            )
            raise HTTPException(status_code=400, detail=message)

        # If auto_process is enabled, generate embedding
        if session.config.auto_process and chunk:
            logger.debug(
                "Auto-processing chunk %d | session_id=%s",
                len(session.chunks) - 1,
                session_id,
            )
            embedding = session.process_chunk(len(session.chunks) - 1)

        logger.info(
            "Chunk added successfully | session_id=%s chunk=%d/%d has_embedding=%s",
            session_id,
            len(session.chunks),
            session.config.max_chunks,
            chunk.embedding is not None if chunk else False,
        )

        chunk_response = AudioChunkResponse(
            chunk_id=chunk.chunk_id,
            chunk_number=len(session.chunks),
            total_chunks=session.config.max_chunks,
            duration_seconds=chunk.duration_seconds,
            timestamp=chunk.timestamp.isoformat(),
            has_embedding=chunk.embedding is not None,
            quality_score=chunk.quality_score,
        ) if chunk else None

        return EnrollmentChunkAddResponse(
            success=True,
            message=f"Chunk added ({len(session.chunks)}/{session.config.max_chunks})",
            chunk=chunk_response,
            session_status=session.status.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error adding chunk | session_id=%s error=%s",
            session_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to process audio chunk: {str(e)}")


@router.get("/enrollment/session/{session_id}", response_model=EnrollmentSessionResponse)
async def get_enrollment_session_status(session_id: str):
    """
    Get the current status of an enrollment session
    
    Args:
        session_id: Session ID from create_enrollment_session
        
    Returns:
        EnrollmentSessionResponse with current session details
    """
    from app.services.enrollment import get_enrollment_session
    
    session = get_enrollment_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return EnrollmentSessionResponse(
        session_id=session.session_id,
        phone_number=session.phone_number,
        status=session.status.value,
        created_at=session.created_at.isoformat(),
        started_at=session.started_at.isoformat() if session.started_at else None,
        chunks_collected=len(session.chunks),
        max_chunks=session.config.max_chunks,
        embeddings_generated=len(session.embeddings),
        error_message=session.error_message
    )


@router.post("/enrollment/session/{session_id}/finalize", response_model=EnrollmentFinalizeResponse)
async def finalize_enrollment_session(session_id: str, force_single: bool = False):
    """
    Finalize an enrollment session and store the merged embedding
    
    - Merges embeddings from all chunks if configured
    - Stores the final embedding in the database
    - Session must have at least min_chunks_required chunks
    - Sends confirmation to registered client if one exists

    Args:
        session_id: Session ID from create_enrollment_session
        force_single: If True, uses single best embedding if merge fails
        
    Returns:
        EnrollmentFinalizeResponse with enrollment result
    """
    from app.services.enrollment import get_enrollment_session, finalize_enrollment
    from app.services.enrollment import get_confirmation_service

    logger.info(
        "finalize_enrollment_session() | session_id=%s force_single=%s",
        session_id,
        force_single,
    )

    session = get_enrollment_session(session_id)
    if not session:
        logger.warning("Session not found for finalize | session_id=%s", session_id)
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    logger.info(
        "Finalizing enrollment | session_id=%s phone=%s chunks=%d",
        session_id,
        session.phone_number,
        len(session.chunks),
    )

    try:
        success, message, vector_id = finalize_enrollment(session_id, force_single)

        if not success:
            logger.warning(
                "Enrollment finalization failed | session_id=%s reason=%s", session_id, message
            )
            raise HTTPException(status_code=400, detail=message)

        logger.info(
            "Enrollment finalized successfully | session_id=%s phone=%s vector_id=%s chunks=%d",
            session_id,
            session.phone_number,
            vector_id,
            len(session.chunks),
        )

        # Send confirmation to registered client if available
        if vector_id:
            try:
                confirmation_sent, confirmation_id = await get_confirmation_service().send_enrollment_confirmation(
                    session_id=session_id,
                    phone_number=session.phone_number,
                    vector_id=vector_id,
                    chunks_processed=len(session.chunks),
                    success=True,
                    message=message,
                )
                if confirmation_sent:
                    logger.info(
                        "Enrollment confirmation sent | session_id=%s confirmation_id=%s",
                        session_id,
                        confirmation_id,
                    )
                else:
                    logger.debug(
                        "No client registered for confirmation | session_id=%s", session_id
                    )
            except Exception as e:
                logger.warning(
                    "Confirmation send failed (non-fatal) | session_id=%s error=%s",
                    session_id,
                    e,
                )

        return EnrollmentFinalizeResponse(
            success=True,
            message=message,
            phone_number=session.phone_number,
            vector_id=vector_id,
            chunks_processed=len(session.chunks),
            enrollment_status=session.status.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error finalizing enrollment | session_id=%s error=%s",
            session_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to finalize enrollment: {str(e)}")


@router.post("/enrollment/session/{session_id}/register-client")
async def register_client_for_session(session_id: str, client_id: str):
    """
    Register a WebSocket client with an enrollment session
    When the enrollment is finalized, a confirmation will be sent to this client
    
    Args:
        session_id: Enrollment session ID
        client_id: WebSocket client ID
        
    Returns:
        Success/failure message
    """
    from app.services.enrollment import get_enrollment_session
    from app.services.enrollment import get_confirmation_service
    
    session = get_enrollment_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        success = get_confirmation_service().register_session_client(session_id, client_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to register client"
            )
        
        return {
            "success": True,
            "message": f"Client {client_id} registered for session {session_id}",
            "session_id": session_id,
            "client_id": client_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register client: {str(e)}"
        )


@router.post("/enrollment/confirmation/send")
async def send_enrollment_confirmation(
    session_id: str,
    phone_number: str,
    vector_id: str,
    chunks_processed: int,
    success: bool = True,
    message: str = ""
):
    """
    Send enrollment confirmation to the registered client for a session
    
    Args:
        session_id: Enrollment session ID
        phone_number: Phone number that was enrolled
        vector_id: The embedding vector ID in the database
        chunks_processed: Number of chunks processed
        success: Whether enrollment was successful
        message: Additional message
        
    Returns:
        Confirmation details
    """
    from app.services.enrollment import get_confirmation_service
    
    try:
        sent, confirmation_id = await get_confirmation_service().send_enrollment_confirmation(
            session_id=session_id,
            phone_number=phone_number,
            vector_id=vector_id,
            chunks_processed=chunks_processed,
            success=success,
            message=message
        )
        
        if not sent:
            raise HTTPException(
                status_code=400,
                detail="Failed to send confirmation - client may not be connected"
            )
        
        return {
            "success": True,
            "message": "Confirmation sent successfully",
            "confirmation_id": confirmation_id,
            "session_id": session_id,
            "phone_number": phone_number
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send confirmation: {str(e)}"
        )


@router.get("/enrollment/confirmation/history")
async def get_confirmation_history(limit: int = 100):
    """
    Get history of sent confirmations
    
    Args:
        limit: Maximum number of confirmations to return
        
    Returns:
        List of confirmation records
    """
    from app.services.enrollment import get_confirmation_service
    
    history = get_confirmation_service().get_confirmation_history(limit)
    
    return {
        "total": len(history),
        "confirmations": history
    }


@router.delete("/enrollment/session/{session_id}")
async def cancel_enrollment_session(session_id: str):
    """
    Cancel and remove an enrollment session
    
    Args:
        session_id: Session ID to cancel
        
    Returns:
        Success/failure message
    """
    from app.services.enrollment import get_enrollment_manager
    
    manager = get_enrollment_manager()
    success = manager.remove_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "success": True,
        "message": f"Session {session_id} cancelled and removed"
    }


@router.get("/enrollment/sessions")
async def list_enrollment_sessions():
    """
    List all active enrollment sessions
    
    Returns:
        List of all enrollment sessions with summaries
    """
    from app.services.enrollment import get_enrollment_manager
    
    manager = get_enrollment_manager()
    sessions = manager.list_sessions()
    
    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }


@router.post("/enrollment/validate-sample")
async def validate_enrollment_sample(
    file: UploadFile = File(...),
    expected_text: str = Form(...),
    sample_number: int = Form(1),
):
    """
    Transcribe a recorded audio sample with Whisper and compare it against
    the expected phrase using fuzzy matching (85 % similarity threshold).

    Used during enrollment so the frontend can reject samples where the user
    spoke something different from the displayed text.

    Args:
        file:          WAV audio file uploaded from the browser.
        expected_text: The phrase the user was asked to read aloud.
        sample_number: 1-based index of the sample (1–5).

    Returns:
        JSON with ``matched`` (bool), ``transcription`` (str),
        ``similarity`` (float 0-1) and ``sample_number`` (int).
    """
    from app.services.sample_validation import validate_sample_text

    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    try:
        result = await validate_sample_text(
            audio_bytes=audio_bytes,
            expected_text=expected_text,
            sample_number=sample_number,
        )
    except Exception as exc:
        logger.error("validate_enrollment_sample failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")

    return result


@router.post("/enrollment/cleanup")
async def cleanup_expired_enrollment_sessions(max_age_hours: int = 1):
    """
    Clean up expired enrollment sessions
    
    Args:
        max_age_hours: Maximum age for a session in hours
        
    Returns:
        Number of sessions cleaned up
    """
    from app.services.enrollment import get_enrollment_manager
    
    manager = get_enrollment_manager()
    cleanup_count = manager.cleanup_expired_sessions(max_age_seconds=max_age_hours * 3600)
    
    return {
        "success": True,
        "sessions_cleaned": cleanup_count,
        "message": f"Cleaned up {cleanup_count} expired enrollment session(s)"
    }