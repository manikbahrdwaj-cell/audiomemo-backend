"""
Shim module for backward compatibility. Re-exports all public symbols from split enrollment modules.
"""

from app.services.enrollment_status import EnrollmentStatus
from app.services.enrollment_chunk import AudioChunkRecord
from app.services.enrollment_config import EnrollmentSessionConfig
from app.services.enrollment_session import EnrollmentSession
from app.services.enrollment_manager import (
    EnrollmentServiceManager,
    get_enrollment_manager,
    create_enrollment_session,
    get_enrollment_session,
    remove_session,
    list_sessions,
    find_session_by_phone,
)
from app.services.enrollment_helpers import (
    add_audio_chunk,
    finalize_enrollment,
    merge_audio_chunks,
    generate_embedding_from_merged_audio,
    merge_and_generate_embedding,
)
from app.services.enrollment_confirmation import (
    EnrollmentConfirmationService,
    get_confirmation_service,
)
