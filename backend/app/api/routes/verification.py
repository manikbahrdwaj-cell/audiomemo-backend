from fastapi import APIRouter, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from app.models.verification import (
    VerificationSessionResponse,
    VerificationChunkAddResponse,
    VerificationFinalizeResponse,
    VerifyResponse
)
from app.services.verification import (
    get_verification_manager,
    create_verification_session,
    get_verification_session,
    add_verification_chunk,
    process_verification_session,
    VerificationSessionConfig
)
from app.services.verification_streaming import (
    get_verification_streaming_manager
)
from app.db.embeddings import get_voice_embedding, check_enrollment
from app.ml.embedding import generate_embedding, calculate_cosine_similarity
from app.websocket.manager import ConnectionManager
from app.websocket.events import event_handler
from app.websocket.monitor import monitor
from app.websocket.router import WebSocketMessageRouter, RouteConfig, MessageType

router = APIRouter()

@router.post("/verification/session", response_model=VerificationSessionResponse)
async def create_new_verification_session(
    phone_number: str,
    max_chunks: int = 5,
    merge_embeddings: bool = True,
    verification_type: str = "voice"
):
    """
    Create a new verification session for comparing voice samples
    
    - Initializes a session to collect verification audio chunks
    - Must use an enrolled phone number
    - Returns session ID for tracking chunk uploads
    - Each session can collect up to max_chunks audio samples
    
    Args:
        phone_number: Phone number to verify (must be enrolled)
        max_chunks: Maximum number of chunks to collect (default: 5)
        merge_embeddings: Whether to merge embeddings from multiple chunks
        verification_type: Type of verification (default: "voice")
        
    Returns:
        VerificationSessionResponse with session details
        
    Raises:
        HTTPException: 404 if phone number not enrolled
        HTTPException: 409 if session already exists for this phone number
    """
    from app.db.embeddings import check_enrollment
    
    # Check if phone number is enrolled
    is_enrolled = check_enrollment(phone_number)
    if not is_enrolled:
        raise HTTPException(
            status_code=404,
            detail=f"Phone number {phone_number} is not enrolled. Please enroll first."
        )
    
    # Check for existing active session with the same phone number
    verification_manager = get_verification_manager()
    existing_session = verification_manager.find_session_by_phone(phone_number)
    
    if existing_session:
        return VerificationSessionResponse(
            session_id=existing_session.session_id,
            phone_number=existing_session.phone_number,
            status=existing_session.status.value,
            created_at=existing_session.created_at.isoformat(),
            started_at=existing_session.started_at.isoformat() if existing_session.started_at else None,
            chunks_collected=len(existing_session.chunks),
            max_chunks=existing_session.config.max_chunks,
            embeddings_generated=len(existing_session.embeddings),
            verified=False,
            error_message=None
        )
    
    # Create session configuration
    config = VerificationSessionConfig(
        max_chunks=max_chunks
    )
    
    # Create session
    session = create_verification_session(phone_number, config)
    
    return VerificationSessionResponse(
        session_id=session.session_id,
        phone_number=session.phone_number,
        status=session.status.value,
        created_at=session.created_at.isoformat(),
        started_at=session.started_at.isoformat() if session.started_at else None,
        chunks_collected=0,
        max_chunks=max_chunks,
        embeddings_generated=0,
        verified=False,
        error_message=None
    )


@router.post("/verification/session/{session_id}/chunk", response_model=VerificationChunkAddResponse)
async def add_audio_chunk_to_verification_session(
    session_id: str,
    file: UploadFile = File(..., description="WAV audio file"),
    quality_score: float = 1.0
):
    """
    Add an audio chunk to an active verification session
    
    - Upload a single audio chunk for verification
    - Can call this endpoint multiple times with different audio samples
    - Each chunk is processed into a voice embedding
    
    Args:
        session_id: Session ID from create_verification_session
        file: WAV audio file
        quality_score: Optional quality confidence score (0-1)
        
    Returns:
        VerificationChunkAddResponse with chunk details and session status
    """
    import soundfile as sf
    import numpy as np
    import io
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.WAV')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a WAV file."
        )
    
    # Get session
    session = get_verification_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        # Read audio file
        audio_bytes = await file.read()
        
        if len(audio_bytes) < 1000:
            raise HTTPException(
                status_code=400,
                detail="Audio file too small. Please record a longer sample."
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
        
        # Validate quality score
        quality_score = max(0.0, min(1.0, quality_score))
        
        # Add chunk to session
        success, message, chunk = add_verification_chunk(
            session_id,
            audio_data,
            duration_seconds,
            sample_rate,
            quality_score
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=message
            )
        
        # If auto_process is enabled, generate embedding
        if session.config.auto_process and chunk:
            embedding = session.process_chunk(len(session.chunks) - 1)
        
        chunk_response = {
            "chunk_id": chunk.chunk_id,
            "chunk_number": len(session.chunks),
            "total_chunks": session.config.max_chunks,
            "duration_seconds": chunk.duration_seconds,
            "timestamp": chunk.timestamp.isoformat(),
            "has_embedding": chunk.embedding is not None,
            "quality_score": chunk.quality_score
        } if chunk else None
        
        return VerificationChunkAddResponse(
            success=True,
            message=f"Chunk added ({len(session.chunks)}/{session.config.max_chunks})",
            chunk=chunk_response,
            session_status=session.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process audio chunk: {str(e)}"
        )


@router.get("/verification/session/{session_id}", response_model=VerificationSessionResponse)
async def get_verification_session_status(session_id: str):
    """
    Get the current status of a verification session
    
    Args:
        session_id: Session ID from create_verification_session
        
    Returns:
        VerificationSessionResponse with current session details
    """
    from app.services.verification import get_verification_session
    
    session = get_verification_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return VerificationSessionResponse(
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


@router.post("/verification/session/{session_id}/finalize", response_model=VerificationFinalizeResponse)
async def finalize_verification_session(session_id: str, force_single: bool = False):
    """
    Finalize a verification session and perform voice verification
    
    - Merges embeddings from all chunks if configured
    - Compares the final embedding against the enrolled voice
    - Returns verification result with confidence score
    - Session must have at least min_chunks_required chunks
    
    Args:
        session_id: Session ID from create_verification_session
        force_single: If True, uses single best embedding if merge fails
        
    Returns:
        VerificationFinalizeResponse with verification result
    """
    session = get_verification_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        verified, similarity, message = process_verification_session(session_id)
        
        if session.status.value == "failed":
            raise HTTPException(
                status_code=400,
                detail=message
            )
        
        return VerificationFinalizeResponse(
            success=True,
            message=message,
            phone_number=session.phone_number,
            chunks_processed=len(session.chunks),
            average_similarity=float(similarity),
            min_similarity=float(similarity),
            max_similarity=float(similarity),
            threshold=session.config.verification_threshold,
            is_match=verified,
            verification_status=session.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize verification: {str(e)}"
        )


@router.post("/verification/verify", response_model=VerifyResponse)
async def verify_voice_from_enrollment(
    phone_number: str,
    file: UploadFile = File(..., description="WAV audio file to verify"),
    quality_score: float = 1.0
):
    """
    Perform a one-time voice verification against enrolled voice
    
    - Verifies a single audio file against the enrolled voice
    - No session required
    - Returns verification result with confidence score
    
    Args:
        phone_number: Phone number to verify (must be enrolled)
        file: WAV audio file to verify
        quality_score: Optional quality confidence score (0-1)
        
    Returns:
        VerificationResult with verification details
    """
    from app.db.embeddings import check_enrollment
    import numpy as np
    
    # Check if phone number is enrolled
    is_enrolled = check_enrollment(phone_number)
    if not is_enrolled:
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
        
        # Generate embedding and compare against enrolled voice
        THRESHOLD = 0.75
        query_embedding = generate_embedding(audio_bytes)
        enrolled_embedding = get_voice_embedding(phone_number)
        if enrolled_embedding is None:
            raise HTTPException(
                status_code=404,
                detail=f"No enrolled embedding found for {phone_number}"
            )
        similarity = calculate_cosine_similarity(np.array(enrolled_embedding), query_embedding)
        
        return VerifyResponse(
            success=True,
            phone_number=phone_number,
            similarity_score=float(similarity),
            is_match=bool(similarity >= THRESHOLD),
            threshold=THRESHOLD
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify voice: {str(e)}"
        )


@router.get("/verification/sessions")
async def list_verification_sessions():
    """
    List all active verification sessions
    
    Returns:
        List of all verification sessions with summaries
    """
    from app.services.verification import get_verification_manager
    
    manager = get_verification_manager()
    sessions = manager.list_sessions()
    
    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }


@router.delete("/verification/session/{session_id}")
async def cancel_verification_session(session_id: str):
    """
    Cancel and remove a verification session
    
    Args:
        session_id: Session ID to cancel
        
    Returns:
        Success/failure message
    """
    from app.services.verification import get_verification_manager
    
    manager = get_verification_manager()
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


@router.post("/verification/cleanup")
async def cleanup_expired_verification_sessions(max_age_hours: int = 1):
    """
    Clean up expired verification sessions
    
    Args:
        max_age_hours: Maximum age for a session in hours
        
    Returns:
        Number of sessions cleaned up
    """
    from app.services.verification import get_verification_manager
    
    manager = get_verification_manager()
    cleanup_count = manager.cleanup_expired_sessions(max_age_seconds=max_age_hours * 3600)
    
    return {
        "success": True,
        "sessions_cleaned": cleanup_count,
        "message": f"Cleaned up {cleanup_count} expired verification session(s)"
    }


@router.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket, phone_number: str):
    """
    WebSocket endpoint for real-time voice streaming verification
    
    - Establishes WebSocket connection for streaming audio
    - Handles real-time voice verification
    - Supports multiple simultaneous connections
    - Uses streaming verification service
    
    Args:
        websocket: WebSocket connection
        phone_number: Phone number to verify (must be enrolled)
    """
    from app.websocket.manager import ConnectionManager
    from app.services.verification_streaming import get_verification_streaming_manager
    from app.db.embeddings import check_enrollment
    
    # Check if phone number is enrolled
    is_enrolled = check_enrollment(phone_number)
    if not is_enrolled:
        await websocket.close(code=1002, reason=f"Phone number {phone_number} is not enrolled")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Add to manager
    manager = ConnectionManager()
    manager.add_connection(websocket, phone_number)
    
    try:
        # Initialize streaming verification service
        streaming_service = get_verification_streaming_manager()
        
        # Process messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle incoming messages
                await streaming_service.handle_message(websocket, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                # Log error and send error message
                await websocket.send_text(f"Error: {str(e)}")
                continue
                
    except Exception as e:
        # Log error
        pass
    finally:
        # Remove connection
        manager.remove_connection(websocket)


@router.websocket("/ws/verify/{phone_number}")
async def websocket_verify_endpoint(websocket: WebSocket, phone_number: str):
    """
    WebSocket endpoint for real-time voice verification
    
    - Establishes WebSocket connection for streaming verification
    - Handles real-time voice verification
    - Supports multiple simultaneous connections
    - Uses streaming verification service
    
    Args:
        websocket: WebSocket connection
        phone_number: Phone number to verify (must be enrolled)
    """
    from app.websocket.manager import ConnectionManager
    from app.services.verification_streaming import get_verification_streaming_manager
    from app.db.embeddings import check_enrollment
    
    # Check if phone number is enrolled
    is_enrolled = check_enrollment(phone_number)
    if not is_enrolled:
        await websocket.close(code=1002, reason=f"Phone number {phone_number} is not enrolled")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Add to manager
    manager = ConnectionManager()
    manager.add_connection(websocket, phone_number)
    
    try:
        # Initialize streaming verification service
        streaming_service = get_verification_streaming_manager()
        
        # Process messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle incoming messages
                await streaming_service.handle_message(websocket, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                # Log error and send error message
                await websocket.send_text(f"Error: {str(e)}")
                continue
                
    except Exception as e:
        # Log error
        pass
    finally:
        # Remove connection
        manager.remove_connection(websocket)