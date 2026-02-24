"""
Helper functions for enrollment chunk and embedding management.
"""


from typing import Optional, Tuple, Any
import numpy as np
from app.services.enrollment_manager import get_enrollment_session
from app.services.enrollment_session import EnrollmentSession

# --- Copied helper functions from enrollment.py ---


def add_audio_chunk(session_id: str, audio_data: np.ndarray, duration_seconds: float, sample_rate: int = 16000, quality_score: float = 1.0) -> Tuple[bool, str, Optional[Any]]:
    """
    Add an audio chunk to the session by session_id.
    Returns (success, message, AudioChunkRecord or None)
    """
    session = get_enrollment_session(session_id)
    if session is None:
        return False, f"Session {session_id} not found", None
    try:
        chunk = session.add_chunk(audio_data, duration_seconds, sample_rate, quality_score)
        return True, "Chunk added", chunk
    except Exception as e:
        return False, str(e), None



def merge_audio_chunks(session_id: str) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
    """
    Merge all collected audio chunks into a single audio file by session_id.
    Returns (success, message, merged_audio)
    """
    session = get_enrollment_session(session_id)
    if session is None:
        return False, f"Session {session_id} not found", None
    return session.merge_audio_chunks()



def generate_embedding_from_merged_audio(session_id: str) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
    """
    Generate embedding from merged audio by session_id.
    Returns (success, message, embedding)
    """
    session = get_enrollment_session(session_id)
    if session is None:
        return False, f"Session {session_id} not found", None
    return session.generate_embedding_from_merged_audio()



def merge_and_generate_embedding(session_id: str) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
    """
    Complete workflow: merge audio chunks and generate single embedding by session_id.
    Returns (success, message, embedding)
    """
    session = get_enrollment_session(session_id)
    if session is None:
        return False, f"Session {session_id} not found", None
    return session.merge_and_generate_embedding()



def finalize_enrollment(session_id: str, force_single: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Finalize enrollment by storing the merged embedding by session_id.
    Returns (success, message, vector_id or None)
    """
    session = get_enrollment_session(session_id)
    if session is None:
        return False, f"Session {session_id} not found", None
    result = session.finalize_enrollment(force_single=force_single)
    # result: Tuple[bool, str, Optional[np.ndarray]]
    success, message, embedding = result
    # For backward compatibility, return vector_id if enrollment succeeded
    if success and hasattr(session, 'merged_embedding') and session.merged_embedding is not None:
        # Assume vector_id is stored in session metadata or can be retrieved
        vector_id = getattr(session, 'vector_id', None)
        if vector_id is None:
            # Try to get from message if present
            import re
            m = re.search(r'Vector ID: ([a-fA-F0-9\-]+)', message or '')
            if m:
                vector_id = m.group(1)
        return True, message, vector_id
    return success, message, None
