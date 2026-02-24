"""
MongoDB Database Module
Handles voice embedding storage and vector search operations
"""

# ---------------------------------------------------------------------------
# Backward-compat re-exports — real implementations live in sub-modules.
# Any code that still imports from app.db.mongodb continues to work.
# ---------------------------------------------------------------------------
from app.db.connection import (
    get_database,
    get_enrollment_sessions_collection,
    get_audio_chunks_collection,
    get_enrollment_history_collection,
)
from app.db.embeddings import (
    store_voice_embedding,
    get_voice_embedding,
    check_enrollment,
    find_nearest_embedding,
    verify_phone_number_embedding,
    delete_voice_embedding,
    get_all_enrollments,
)
from app.db.enrollment_sessions import (
    save_enrollment_session,
    get_enrollment_session,
    update_enrollment_session,
    delete_enrollment_session,
    get_enrollment_sessions_for_phone,
    get_active_enrollment_sessions,
    cleanup_expired_enrollment_sessions,
)
from app.db.audio_chunks import (
    save_audio_chunk,
    get_audio_chunks_for_session,
)
from app.db.enrollment_history import (
    save_enrollment_history,
    get_enrollment_history_for_phone,
    get_recent_enrollments,
    get_enrollment_stats,
)
from app.db.verified_sessions import (
    save_verified_session,
    get_verified_session,
    update_verified_session,
    delete_verified_session,
    get_verified_sessions_for_phone,
    get_active_verified_sessions,
    get_recent_verifications,
)
