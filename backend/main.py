"""
Voice Biometric Authentication API
FastAPI backend for voice enrollment and verification
"""

# Patch torchaudio compatibility issues BEFORE any imports that use speechbrain
import torchaudio

if not hasattr(torchaudio, 'set_audio_backend'):
    def _dummy_set_audio_backend(backend):
        """Dummy function to satisfy speechbrain compatibility"""
        pass
    torchaudio.set_audio_backend = _dummy_set_audio_backend

if not hasattr(torchaudio, 'list_audio_backends'):
    def _dummy_list_audio_backends():
        """Dummy function to satisfy speechbrain compatibility"""
        return ['soundfile']
    torchaudio.list_audio_backends = _dummy_list_audio_backends

if not hasattr(torchaudio, 'get_audio_backend'):
    def _dummy_get_audio_backend():
        """Dummy function to satisfy speechbrain compatibility"""
        return 'soundfile'
    torchaudio.get_audio_backend = _dummy_get_audio_backend

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import json
import uuid
import io
import numpy as np

from voice_embedding import generate_embedding, calculate_cosine_similarity
from database import (
    store_voice_embedding,
    get_voice_embedding,
    check_enrollment,
    find_nearest_embedding
)
from websocket_handler import ConnectionManager, WebSocketMessageValidator, WebSocketMessageBuilder
from websocket_events import event_handler
from websocket_monitor import monitor
from websocket_router import WebSocketMessageRouter, RouteConfig, MessageType
from enrollment_service import (
    get_enrollment_manager,
    create_enrollment_session,
    get_enrollment_session,
    add_audio_chunk,
    finalize_enrollment,
    EnrollmentSessionConfig,
    get_confirmation_service
)
from verification_service import (
    get_verification_manager,
    create_verification_session,
    get_verification_session,
    add_verification_chunk,
    process_verification_session,
    VerificationSessionConfig
)
import soundfile as sf

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

# Enrollment Service Response Models
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


# Verification Session Response Models
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


# WebSocket Management
manager = ConnectionManager()

# Initialize enrollment confirmation service
confirmation_service = get_confirmation_service()
confirmation_service.set_connection_manager(manager)

# Initialize message router with routes
def _create_router() -> WebSocketMessageRouter:
    """Create and configure the message router"""
    router = WebSocketMessageRouter()
    
    # Wrapper functions to adapt event handlers for router
    async def handle_audio(message: dict):
        from websocket_handler import ClientConnection
        # Note: Connection will be passed explicitly in routing
        return {"type": "audio_processed", "status": "pending"}
    
    async def handle_verify(message: dict):
        return {"type": "verify_started", "status": "pending"}
    
    async def handle_enroll(message: dict):
        return {"type": "enroll_started", "status": "pending"}
    
    async def handle_ping(message: dict):
        return {"type": "pong", "status": "ok", "timestamp": datetime.now().isoformat()}
    
    async def handle_reset(message: dict):
        return {"type": "reset_acknowledged", "status": "ok"}
    
    async def handle_status(message: dict):
        return {"type": "status", "status": "ok"}
    
    # Register all routes
    routes = [
        RouteConfig(
            message_type=MessageType.AUDIO,
            handler=handle_audio,
            requires_fields=["data"],
            optional_fields=[],
            max_message_size=1_000_000,  # 1MB
            rate_limit=100  # 100 messages/sec
        ),
        RouteConfig(
            message_type=MessageType.VERIFY,
            handler=handle_verify,
            requires_fields=[],  # PHASE 2: Voice-first - no phone_number required
            optional_fields=[],
            rate_limit=10
        ),
        RouteConfig(
            message_type=MessageType.ENROLL,
            handler=handle_enroll,
            requires_fields=["phone_number"],
            optional_fields=[],
            rate_limit=5
        ),
        RouteConfig(
            message_type=MessageType.PING,
            handler=handle_ping,
            requires_fields=[],
            optional_fields=[],
            rate_limit=1000
        ),
        RouteConfig(
            message_type=MessageType.RESET,
            handler=handle_reset,
            requires_fields=[],
            optional_fields=[],
            rate_limit=10
        ),
        RouteConfig(
            message_type=MessageType.STATUS,
            handler=handle_status,
            requires_fields=[],
            optional_fields=[],
            rate_limit=10
        ),
    ]
    
    router.register_routes(routes)
    return router

message_router = _create_router()


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice streaming and verification
    
    Message types supported:
    - 'audio': Audio chunk (base64 encoded)
    - 'verify': Start verification process
    - 'enroll': Start enrollment process
    - 'ping': Keep-alive message
    - 'reset': Reset audio buffer
    - 'status': Get connection status
    """
    # Generate unique client ID
    client_id = str(uuid.uuid4())
    
    # Connect the client
    connection = await manager.connect(websocket, client_id)
    monitor.create_connection(client_id)
    logger.info(f"Voice WebSocket connection established: {client_id}")
    
    try:
        while True:
            try:
                # Receive message from client with timeout to prevent hanging
                data = await websocket.receive_text()
                
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected (from receive_text)")
                raise  # Re-raise to be caught by outer except
            except Exception as e:
                logger.error(f"Error receiving message from {client_id}: {str(e)}", exc_info=True)
                # Don't break the loop on receive errors, continue waiting
                continue
            
            try:
                message = json.loads(data)
                message_type = message.get('type')
                
                monitor.record_message_received(client_id)
                logger.info(f"WebSocket message from {client_id}: type={message_type}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {client_id}: {str(e)}")
                response = WebSocketMessageBuilder.create_error_message(
                    "invalid_json",
                    "Invalid JSON format"
                )
                await connection.send_json(response)
                monitor.record_message_sent(client_id)
                monitor.record_error(client_id, "invalid_json")
                continue
            except Exception as e:
                logger.error(f"Error parsing message from {client_id}: {str(e)}", exc_info=True)
                response = WebSocketMessageBuilder.create_error_message(
                    "parse_error",
                    f"Error parsing message: {str(e)}"
                )
                try:
                    await connection.send_json(response)
                    monitor.record_message_sent(client_id)
                except Exception as send_err:
                    logger.error(f"Error sending error response to {client_id}: {str(send_err)}")
                monitor.record_error(client_id, "parse_error")
                continue
            
            # Route through the message router
            route = message_router.get_route(message_type)
            
            if route is None:
                response = WebSocketMessageBuilder.create_error_message(
                    "unknown_type",
                    f"Unknown message type: {message_type}"
                )
                try:
                    await connection.send_json(response)
                    monitor.record_message_sent(client_id)
                except Exception as send_err:
                    logger.error(f"Error sending response to {client_id}: {str(send_err)}")
                monitor.record_error(client_id, "unknown_type")
                continue
            
            # Validate message using router validator
            is_valid, error_msg = message_router.validator.validate_message(message, route)
            if not is_valid:
                response = WebSocketMessageBuilder.create_error_message(
                    "validation_error",
                    error_msg
                )
                try:
                    await connection.send_json(response)
                    monitor.record_message_sent(client_id)
                except Exception as send_err:
                    logger.error(f"Error sending validation error to {client_id}: {str(send_err)}")
                monitor.record_error(client_id, "validation_error")
                continue
            
            # Check rate limit
            if route.rate_limit:
                is_allowed, limit_msg = message_router.rate_limiter.check_limit(
                    client_id, message_type, route.rate_limit
                )
                if not is_allowed:
                    response = WebSocketMessageBuilder.create_error_message(
                        "rate_limit",
                        limit_msg
                    )
                    try:
                        await connection.send_json(response)
                        monitor.record_message_sent(client_id)
                    except Exception as send_err:
                        logger.error(f"Error sending rate limit error to {client_id}: {str(send_err)}")
                    monitor.record_error(client_id, "rate_limit")
                    continue
            
            # Route message to appropriate handler based on type
            response = None
            try:
                if message_type == 'audio':
                    response = await event_handler.handle_audio_chunk(connection, message)
                    monitor.record_audio_chunk(client_id, len(message.get('data', '')))
                
                elif message_type == 'verify':
                    monitor.record_verification(client_id)
                    response = await event_handler.handle_verify(connection, message)
                
                elif message_type == 'enroll':
                    monitor.record_enrollment(client_id)
                    response = await event_handler.handle_enroll(connection, message)
                
                elif message_type == 'ping':
                    response = await event_handler.handle_ping(connection)
                
                elif message_type == 'reset':
                    response = await event_handler.handle_reset(connection)
                
                elif message_type == 'status':
                    response = await event_handler.handle_status(connection)
                
                else:
                    response = WebSocketMessageBuilder.create_error_message(
                        "unknown_type",
                        f"Unknown message type: {message_type}"
                    )
                    monitor.record_error(client_id, "unknown_type")
            
            except Exception as e:
                logger.error(f"Error handling {message_type}: {str(e)}", exc_info=True)
                response = WebSocketMessageBuilder.create_error_message(
                    "handler_error",
                    f"Error processing message: {str(e)}"
                )
                monitor.record_error(client_id, "handler_error")
            
            # Send response - make sure response exists before sending
            if response is not None:
                try:
                    await connection.send_json(response)
                    monitor.record_message_sent(client_id)
                    
                    # Record errors if present
                    if response.get('status') == 'error':
                        monitor.record_error(client_id, response.get('error_type', 'unknown'))
                except Exception as send_err:
                    logger.error(f"Error sending response to {client_id}: {str(send_err)}", exc_info=True)
                    monitor.record_error(client_id, "send_error")
                    # Don't exit loop on send error, client may reconnect
            else:
                logger.warning(f"No response generated for {message_type} from {client_id}")
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        monitor.close_connection(client_id)
        event_handler.cleanup_buffer(client_id)
        logger.info(f"Client {client_id} disconnected from voice WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {str(e)}", exc_info=True)
        manager.disconnect(client_id)
        monitor.close_connection(client_id)
        event_handler.cleanup_buffer(client_id)
        monitor.record_error(client_id, "connection_error")


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Voice Biometric API is running"
    )


@app.get("/ws/routes")
async def get_websocket_routes():
    """Get information about all registered WebSocket routes"""
    return {
        "routes": message_router.get_routes_info(),
        "total_routes": len(message_router.routes)
    }


@app.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "active_connections": manager.get_connection_count(),
        "connections": manager.get_all_connections(),
        "aggregate_stats": monitor.get_aggregate_stats(),
        "health_status": monitor.get_health_status()
    }


@app.get("/ws/monitor")
async def get_websocket_monitor():
    """Get detailed WebSocket monitoring data"""
    return {
        "active_stats": monitor.get_all_active_stats(),
        "historical_stats": monitor.get_historical_stats(limit=20),
        "recent_events": monitor.get_recent_events(limit=50),
        "health": monitor.get_health_status()
    }


@app.get("/ws/health")
async def get_websocket_health():
    """Get WebSocket infrastructure health status"""
    return monitor.get_health_status()


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


# ============================================================================
# ENROLLMENT SERVICE ENDPOINTS - Multi-Chunk Voice Enrollment
# ============================================================================

@app.post("/enrollment/session", response_model=EnrollmentSessionResponse)
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
    logger.info(f"Creating enrollment session for {phone_number} (max_chunks: {max_chunks})")
    
    # Check if phone number is already enrolled (duplicate prevention)
    is_enrolled = check_enrollment(phone_number)
    if is_enrolled:
        logger.warning(f"Duplicate enrollment attempt for {phone_number}")
        raise HTTPException(
            status_code=409,
            detail=f"This number is already enrolled. Duplicate enrollment is not allowed."
        )
    
    # Check for existing active session with the same phone number
    enrollment_manager = get_enrollment_manager()
    existing_session = enrollment_manager.find_session_by_phone(phone_number)
    
    if existing_session:
        logger.info(f"Found existing enrollment session {existing_session.session_id[:8]} for {phone_number}")
        return EnrollmentSessionResponse(
            session_id=existing_session.session_id,
            phone_number=existing_session.phone_number,
            status=existing_session.status.value,
            created_at=existing_session.created_at.isoformat(),
            started_at=existing_session.started_at.isoformat() if existing_session.started_at else None,
            chunks_collected=len(existing_session.chunks),
            max_chunks=existing_session.config.max_chunks,
            embeddings_generated=len(existing_session.embeddings),
            verified=False,  # Phone number not enrolled yet
            error_message=None
        )
    
    # Create session configuration
    config = EnrollmentSessionConfig(
        max_chunks=max_chunks,
        merge_embeddings=merge_embeddings,
        store_chunks=True  # Store chunks for quality verification
    )
    
    # Create session
    session = create_enrollment_session(phone_number, config)
    
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


@app.post("/enrollment/session/{session_id}/chunk", response_model=EnrollmentChunkAddResponse)
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
    logger.info(f"Adding audio chunk to session {session_id[:8]}")
    
    # Validate file type
    if not file.filename.endswith(('.wav', '.WAV')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a WAV file."
        )
    
    # Get session
    session = get_enrollment_session(session_id)
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
        success, message, chunk = add_audio_chunk(
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
            logger.info(f"Generated embedding for chunk: {embedding.shape if embedding is not None else 'Failed'}")
        
        chunk_response = AudioChunkResponse(
            chunk_id=chunk.chunk_id,
            chunk_number=len(session.chunks),
            total_chunks=session.config.max_chunks,
            duration_seconds=chunk.duration_seconds,
            timestamp=chunk.timestamp.isoformat(),
            has_embedding=chunk.embedding is not None,
            quality_score=chunk.quality_score
        ) if chunk else None
        
        return EnrollmentChunkAddResponse(
            success=True,
            message=f"Chunk added ({len(session.chunks)}/{session.config.max_chunks})",
            chunk=chunk_response,
            session_status=session.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding chunk to session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process audio chunk: {str(e)}"
        )


@app.get("/enrollment/session/{session_id}", response_model=EnrollmentSessionResponse)
async def get_enrollment_session_status(session_id: str):
    """
    Get the current status of an enrollment session
    
    Args:
        session_id: Session ID from create_enrollment_session
        
    Returns:
        EnrollmentSessionResponse with current session details
    """
    logger.info(f"Getting status for session {session_id[:8]}")
    
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


@app.post("/enrollment/session/{session_id}/finalize", response_model=EnrollmentFinalizeResponse)
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
    logger.info(f"Finalizing enrollment session {session_id[:8]}")
    
    session = get_enrollment_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        success, message, vector_id = finalize_enrollment(session_id, force_single)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=message
            )
        
        # Send confirmation to registered client if available
        if vector_id:
            try:
                confirmation_sent, confirmation_id = await confirmation_service.send_enrollment_confirmation(
                    session_id=session_id,
                    phone_number=session.phone_number,
                    vector_id=vector_id,
                    chunks_processed=len(session.chunks),
                    success=True,
                    message=message
                )
                
                if confirmation_sent:
                    logger.info(f"✓ Confirmation sent: {confirmation_id[:8]}")
                else:
                    logger.info(f"⚠ No client registered for session {session_id[:8]} - confirmation not sent")
            
            except Exception as e:
                logger.warning(f"Failed to send confirmation: {str(e)}")
                # Don't fail the enrollment if confirmation fails
        
        return EnrollmentFinalizeResponse(
            success=True,
            message=message,
            phone_number=session.phone_number,
            vector_id=vector_id,
            chunks_processed=len(session.chunks),
            enrollment_status=session.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing enrollment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize enrollment: {str(e)}"
        )


@app.post("/enrollment/session/{session_id}/register-client")
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
    logger.info(f"Registering client {client_id[:8]} for session {session_id[:8]}")
    
    session = get_enrollment_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        success = confirmation_service.register_session_client(session_id, client_id)
        
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
        logger.error(f"Error registering client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register client: {str(e)}"
        )


@app.post("/enrollment/confirmation/send")
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
    logger.info(f"Sending enrollment confirmation for session {session_id[:8]}")
    
    try:
        sent, confirmation_id = await confirmation_service.send_enrollment_confirmation(
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
        logger.error(f"Error sending confirmation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send confirmation: {str(e)}"
        )


@app.get("/enrollment/confirmation/history")
async def get_confirmation_history(limit: int = 100):
    """
    Get history of sent confirmations
    
    Args:
        limit: Maximum number of confirmations to return
        
    Returns:
        List of confirmation records
    """
    logger.info("Retrieving confirmation history")
    
    history = confirmation_service.get_confirmation_history(limit)
    
    return {
        "total": len(history),
        "confirmations": history
    }


@app.delete("/enrollment/session/{session_id}")
async def cancel_enrollment_session(session_id: str):
    """
    Cancel and remove an enrollment session
    
    Args:
        session_id: Session ID to cancel
        
    Returns:
        Success/failure message
    """
    logger.info(f"Cancelling enrollment session {session_id[:8]}")
    
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


@app.get("/enrollment/sessions")
async def list_enrollment_sessions():
    """
    List all active enrollment sessions
    
    Returns:
        List of all enrollment sessions with summaries
    """
    logger.info("Listing all enrollment sessions")
    
    manager = get_enrollment_manager()
    sessions = manager.list_sessions()
    
    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }


@app.post("/enrollment/cleanup")
async def cleanup_expired_enrollment_sessions(max_age_hours: int = 1):
    """
    Clean up expired enrollment sessions
    
    Args:
        max_age_hours: Maximum age for a session in hours
        
    Returns:
        Number of sessions cleaned up
    """
    logger.info(f"Cleaning up enrollment sessions older than {max_age_hours} hours")
    
    manager = get_enrollment_manager()
    cleanup_count = manager.cleanup_expired_sessions(max_age_seconds=max_age_hours * 3600)
    
    return {
        "success": True,
        "sessions_cleaned": cleanup_count,
        "message": f"Cleaned up {cleanup_count} expired enrollment session(s)"
    }


# ==== VERIFICATION SESSION ENDPOINTS ====

@app.post("/verification/session", response_model=VerificationSessionResponse)
async def create_new_verification_session(
    phone_number: str = Form(..., description="Phone number to verify against")
):
    """
    Create a new verification session for multi-chunk verification
    
    - Session collects multiple audio chunks
    - Each chunk generates an embedding
    - Embeddings are compared against enrolled embedding
    - Returns session ID for subsequent chunk uploads
    - Returns existing active session if one already exists for the same mobile number
    
    Args:
        phone_number: Phone number of enrolled user to verify
        
    Returns:
        VerificationSessionResponse with session details
    """
    logger.info(f"Creating verification session for phone number: {phone_number}")
    
    try:
        # Check if phone number is enrolled
        if not check_enrollment(phone_number):
            raise HTTPException(
                status_code=404,
                detail=f"Phone number {phone_number} is not enrolled"
            )
        
        # Check for existing active session with the same phone number
        from verification_service import find_verification_session_by_phone
        existing_session = find_verification_session_by_phone(phone_number)
        
        if existing_session:
            logger.info(f"Found existing verification session {existing_session.session_id[:8]} for {phone_number}")
            return VerificationSessionResponse(
                session_id=existing_session.session_id,
                phone_number=existing_session.phone_number,
                status=existing_session.status.value,
                created_at=existing_session.created_at.isoformat(),
                started_at=existing_session.started_at.isoformat() if existing_session.started_at else None,
                chunks_collected=len(existing_session.chunks),
                max_chunks=existing_session.config.max_chunks,
                verified=True,  # Phone number is enrolled
                error_message=None
            )
        
        # Create session
        session = create_verification_session(phone_number)
        
        return VerificationSessionResponse(
            session_id=session.session_id,
            phone_number=session.phone_number,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            started_at=session.started_at.isoformat() if session.started_at else None,
            chunks_collected=len(session.chunks),
            max_chunks=session.config.max_chunks,
            verified=True,  # Phone number is enrolled
            error_message=session.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating verification session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create verification session: {str(e)}"
        )


@app.post("/verification/session/{session_id}/chunk", response_model=VerificationChunkAddResponse)
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
        VerificationChunkAddResponse with chunk details
    """
    logger.info(f"Adding audio chunk to verification session {session_id[:8]}")
    
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
            logger.info(f"Generated embedding for verification chunk: {embedding.shape if embedding is not None else 'Failed'}")
        
        chunk_response = VerificationChunkResponse(
            chunk_id=chunk.chunk_id,
            chunk_number=len(session.chunks),
            total_chunks=session.config.max_chunks,
            duration_seconds=chunk.duration_seconds,
            timestamp=chunk.timestamp.isoformat(),
            has_embedding=chunk.embedding is not None,
            quality_score=chunk.quality_score
        ) if chunk else None
        
        return VerificationChunkAddResponse(
            success=True,
            message=f"Chunk added ({len(session.chunks)}/{session.config.max_chunks})",
            chunk=chunk_response,
            session_status=session.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding chunk to verification session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process audio chunk: {str(e)}"
        )


@app.get("/verification/session/{session_id}/status")
async def get_verification_session_status(session_id: str):
    """
    Get the status of a verification session
    
    Args:
        session_id: Session ID
        
    Returns:
        Session status with chunks collected, embeddings, etc.
    """
    session = get_verification_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "success": True,
        "session_id": session.session_id,
        "phone_number": session.phone_number,
        "status": session.status.value,
        "created_at": session.created_at.isoformat(),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "chunks_collected": len(session.chunks),
        "max_chunks": session.config.max_chunks,
        "min_chunks_required": session.config.min_chunks_required,
        "error_message": session.error_message,
        "verification_result": session.verification_result
    }


@app.post("/verification/session/{session_id}/finalize", response_model=VerificationFinalizeResponse)
async def finalize_verification_session(session_id: str):
    """
    Finalize verification session and perform verification
    
    - Processes all collected audio chunks
    - Generates embeddings for each chunk
    - Compares against enrolled embedding
    - Returns verification result
    
    Args:
        session_id: Session ID from create_verification_session
        
    Returns:
        VerificationFinalizeResponse with verification result
    """
    logger.info(f"Finalizing verification session {session_id[:8]}")
    
    session = get_verification_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        # Process verification session
        success, message, result = process_verification_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=message
            )
        
        return VerificationFinalizeResponse(
            success=True,
            message="Verification completed",
            phone_number=session.phone_number,
            chunks_processed=result.get("chunks_processed", 0),
            average_similarity=result.get("average_similarity", 0.0),
            min_similarity=result.get("min_similarity", 0.0),
            max_similarity=result.get("max_similarity", 0.0),
            threshold=result.get("threshold", 0.75),
            is_match=result.get("is_match", False),
            verification_status=session.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing verification session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize verification: {str(e)}"
        )


@app.post("/verification/session/{session_id}/cancel")
async def cancel_verification_session(session_id: str):
    """
    Cancel a verification session
    
    Args:
        session_id: Session ID
        
    Returns:
        Success message
    """
    session = get_verification_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    session.status = session.status.__class__.CANCELLED
    logger.info(f"Verification session {session_id} cancelled")
    
    return {
        "success": True,
        "message": "Verification session cancelled",
        "session_id": session_id
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
