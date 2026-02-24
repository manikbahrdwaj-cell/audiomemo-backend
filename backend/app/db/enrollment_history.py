import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.connection import get_enrollment_history_collection, get_enrollment_sessions_collection

def save_enrollment_history(history_data: Dict[str, Any]) -> str:
    """
    Save an enrollment completion record
    
    Args:
        history_data: Enrollment history data
        
    Returns:
        History document ID
    """
    collection = get_enrollment_history_collection()
    
    result = collection.insert_one({
        **history_data,
        "created_at": datetime.utcnow()
    })
    
    logging.info(
        f"Saved enrollment history for {history_data.get('phone_number')} "
        f"(session: {history_data.get('session_id')[:8]})"
    )
    return str(result.inserted_id)


def get_enrollment_history_for_phone(phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get enrollment history for a phone number
    
    Args:
        phone_number: Phone number to retrieve history for
        limit: Maximum number of records to return
        
    Returns:
        List of enrollment history records
    """
    collection = get_enrollment_history_collection()
    cursor = collection.find(
        {"phone_number": phone_number}
    ).sort("completed_at", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def get_recent_enrollments(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent enrollment completions
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of enrollment records
    """
    collection = get_enrollment_history_collection()
    cursor = collection.find(
        {"status": "completed"}
    ).sort("completed_at", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def get_enrollment_stats(phone_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Get enrollment statistics
    
    Args:
        phone_number: Optional filter by phone number
        
    Returns:
        Dictionary with enrollment statistics
    """
    sessions_coll = get_enrollment_sessions_collection()
    history_coll = get_enrollment_history_collection()
    
    query = {}
    if phone_number:
        query["phone_number"] = phone_number
    
    # Count by status
    status_query = query.copy()
    all_statuses = ["initializing", "active", "collecting", "processing", "completed", "error", "cancelled"]
    status_counts = {
        status: sessions_coll.count_documents({**status_query, "status": status})
        for status in all_statuses
    }
    
    # Total and recent completions
    total_sessions = sessions_coll.count_documents(query)
    total_completions = history_coll.count_documents({**query, "status": "completed"})
    
    return {
        "total_sessions": total_sessions,
        "by_status": status_counts,
        "total_completions": total_completions,
        "filtered_by_phone": phone_number is not None
    }