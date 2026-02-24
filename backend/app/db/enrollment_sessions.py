import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.connection import get_enrollment_sessions_collection

def save_enrollment_session(session_data: Dict[str, Any]) -> str:
    """
    Save an enrollment session to MongoDB
    
    Args:
        session_data: Session data dictionary
        
    Returns:
        Session document ID
    """
    collection = get_enrollment_sessions_collection()
    
    # Ensure session_id is present
    if "session_id" not in session_data:
        raise ValueError("session_data must contain 'session_id'")
    
    result = collection.update_one(
        {"session_id": session_data["session_id"]},
        {
            "$set": {
                **session_data,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    if result.upserted_id:
        logging.info(f"Created enrollment session {session_data['session_id'][:8]}")
        return str(result.upserted_id)
    else:
        doc = collection.find_one({"session_id": session_data["session_id"]})
        logging.info(f"Updated enrollment session {session_data['session_id'][:8]}")
        return str(doc["_id"])


def get_enrollment_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve an enrollment session by session ID
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Session document or None if not found
    """
    collection = get_enrollment_sessions_collection()
    doc = collection.find_one({"session_id": session_id})
    
    if doc:
        doc["_id"] = str(doc["_id"])
        return doc
    return None


def update_enrollment_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update an enrollment session
    
    Args:
        session_id: Session ID to update
        updates: Dictionary of updates
        
    Returns:
        True if updated, False if not found
    """
    collection = get_enrollment_sessions_collection()
    
    updates["updated_at"] = datetime.utcnow()
    
    result = collection.update_one(
        {"session_id": session_id},
        {"$set": updates}
    )
    
    return result.modified_count > 0


def delete_enrollment_session(session_id: str) -> bool:
    """
    Delete an enrollment session
    
    Args:
        session_id: Session ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    collection = get_enrollment_sessions_collection()
    result = collection.delete_one({"session_id": session_id})
    return result.deleted_count > 0


def get_enrollment_sessions_for_phone(phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get all enrollment sessions for a phone number
    
    Args:
        phone_number: Phone number to search
        limit: Maximum number of sessions to return
        
    Returns:
        List of enrollment sessions
    """
    collection = get_enrollment_sessions_collection()
    cursor = collection.find({"phone_number": phone_number}).sort("created_at", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def get_active_enrollment_sessions(phone_number: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get active enrollment sessions (in progress, collecting, processing)
    
    Args:
        phone_number: Optional filter by phone number
        
    Returns:
        List of active enrollment sessions
    """
    collection = get_enrollment_sessions_collection()
    
    query = {
        "status": {
            "$in": ["initializing", "active", "collecting", "processing"]
        }
    }
    
    if phone_number:
        query["phone_number"] = phone_number
    
    cursor = collection.find(query).sort("created_at", -1)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def cleanup_expired_enrollment_sessions(max_age_seconds: int = 3600) -> int:
    """
    Delete expired enrollment sessions
    
    Args:
        max_age_seconds: Maximum age for a session
        
    Returns:
        Number of sessions deleted
    """
    collection = get_enrollment_sessions_collection()
    
    cutoff_time = datetime.utcnow() - __import__('datetime').timedelta(seconds=max_age_seconds)
    
    result = collection.delete_many({
        "created_at": {"$lt": cutoff_time}
    })
    
    if result.deleted_count > 0:
        logging.info(f"Cleaned up {result.deleted_count} expired enrollment sessions")
    
    return result.deleted_count