import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.connection import get_database, _client, DATABASE_NAME  # used to access _db for collection init

_db = None

def get_verified_sessions_collection():
    """Get verified sessions collection for voice-first verification"""
    global _db
    
    if _db is None:
        get_database()  # Initialize connection
        _db = _client[DATABASE_NAME]
    
    verified_sessions_collection = _db["verified_sessions"]
    
    # Create indexes
    verified_sessions_collection.create_index("session_id", unique=True)
    verified_sessions_collection.create_index("phone_number")
    verified_sessions_collection.create_index("session_status")
    verified_sessions_collection.create_index("created_at")
    verified_sessions_collection.create_index("verified_at")
    
    logging.info("Verified sessions collection initialized")
    
    return verified_sessions_collection


def save_verified_session(session_data: Dict[str, Any]) -> str:
    """
    Save a verified session after successful voice biometric authentication
    
    Args:
        session_data: Verified session data dictionary
        
    Returns:
        Session document ID
    """
    collection = get_verified_sessions_collection()
    
    # Ensure session_id is present
    if "session_id" not in session_data:
        raise ValueError("session_data must contain 'session_id'")
    
    # Make a copy to avoid modifying the original
    update_data = session_data.copy()
    
    # Remove created_at/updated_at from update data to avoid conflicts
    # These fields will be set by $setOnInsert (on insert) and $set (on update)
    update_data.pop("created_at", None)
    update_data.pop("updated_at", None)
    
    result = collection.update_one(
        {"session_id": session_data["session_id"]},
        {
            "$set": {
                **update_data,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    if result.upserted_id:
        logging.info(f"Created verified session {session_data['session_id'][:8]} for {session_data.get('phone_number')}")
        return str(result.upserted_id)
    else:
        doc = collection.find_one({"session_id": session_data["session_id"]})
        logging.info(f"Updated verified session {session_data['session_id'][:8]}")
        return str(doc["_id"])


def get_verified_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a verified session by session ID
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Session document or None if not found
    """
    collection = get_verified_sessions_collection()
    doc = collection.find_one({"session_id": session_id})
    
    if doc:
        doc["_id"] = str(doc["_id"])
        return doc
    return None


def update_verified_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a verified session
    
    Args:
        session_id: Session ID to update
        updates: Dictionary of updates
        
    Returns:
        True if updated, False if not found
    """
    collection = get_verified_sessions_collection()
    
    updates["updated_at"] = datetime.utcnow()
    
    result = collection.update_one(
        {"session_id": session_id},
        {"$set": updates}
    )
    
    return result.modified_count > 0


def delete_verified_session(session_id: str) -> bool:
    """
    Delete a verified session
    
    Args:
        session_id: Session ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    collection = get_verified_sessions_collection()
    result = collection.delete_one({"session_id": session_id})
    return result.deleted_count > 0


def get_verified_sessions_for_phone(phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get all verified sessions for a phone number
    
    Args:
        phone_number: Phone number to search
        limit: Maximum number of sessions to return
        
    Returns:
        List of verified sessions
    """
    collection = get_verified_sessions_collection()
    cursor = collection.find({"phone_number": phone_number}).sort("created_at", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def get_active_verified_sessions(phone_number: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get active verified sessions (verified, active status)
    
    Args:
        phone_number: Optional filter by phone number
        
    Returns:
        List of active verified sessions
    """
    collection = get_verified_sessions_collection()
    
    query = {
        "session_status": {
            "$in": ["verified", "active"]
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


def get_recent_verifications(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recently verified sessions
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        List of recent verified sessions
    """
    collection = get_verified_sessions_collection()
    cursor = collection.find(
        {"session_status": "verified"}
    ).sort("verified_at", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results