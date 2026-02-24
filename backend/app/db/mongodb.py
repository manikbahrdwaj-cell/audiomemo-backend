
"""
MongoDB Database Module (DEPRECATED)
This file is deprecated. All database operations should be imported directly from their domain-specific modules.
Any code that still imports from app.db.mongodb should be refactored to use the correct module.
"""

import warnings
warnings.warn(
    "app.db.mongodb is deprecated. Please import database operations from their domain-specific modules.",
    DeprecationWarning
)
