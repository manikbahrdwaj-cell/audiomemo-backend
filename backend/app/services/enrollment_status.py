"""
Enrollment session status enumeration.
"""

from enum import Enum


class EnrollmentStatus(Enum):
    """Enrollment session status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    COLLECTING = "collecting"  # Collecting audio chunks
    PROCESSING = "processing"  # Processing chunks into embeddings
    FINALIZING = "finalizing"  # Merging embeddings
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"