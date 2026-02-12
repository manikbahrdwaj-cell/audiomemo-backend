"""
MongoDB Database Module
Handles voice embedding storage, vector search operations, and session management
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from typing import Optional, Dict, Any, List
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# MongoDB configuration
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "voice_biometric"

# Collection names
VOICE_EMBEDDINGS_COLLECTION = "voice_embeddings"
SESSIONS_COLLECTION = "sessions"
AUDIO_CHUNKS_COLLECTION = "audio_chunks"
SESSION_ANALYTICS_COLLECTION = "session_analytics"

# Global client instance
_client = None
_db = None
_embeddings_collection = None
_sessions_collection = None
_audio_chunks_collection = None
_analytics_collection = None

def get_database():
    """Get MongoDB database connection and initialize schemas"""
    global _client, _db, _embeddings_collection, _sessions_collection, _audio_chunks_collection, _analytics_collection
    
    if _client is None:
        logger.info(f"Connecting to MongoDB at {MONGODB_URL}...")
        _client = MongoClient(MONGODB_URL)
        _db = _client[DATABASE_NAME]
        
        # Get collection references
        _embeddings_collection = _db[VOICE_EMBEDDINGS_COLLECTION]
        _sessions_collection = _db[SESSIONS_COLLECTION]
        _audio_chunks_collection = _db[AUDIO_CHUNKS_COLLECTION]
        _analytics_collection = _db[SESSION_ANALYTICS_COLLECTION]
        
        # Initialize indexes for all collections
        _initialize_indexes()
        
        logger.info("MongoDB connection established with all collections initialized")
    
    return _embeddings_collection

def _initialize_indexes():
    """Initialize all MongoDB indexes for optimal performance"""
    
    # Voice Embeddings indexes
    _embeddings_collection.create_index("phone_number", unique=True)
    _embeddings_collection.create_index([("created_at", DESCENDING)])
    _embeddings_collection.create_index([("updated_at", DESCENDING)])
    logger.info("Voice embeddings indexes created")
    
    # Sessions indexes
    _sessions_collection.create_index("session_id", unique=True)
    _sessions_collection.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    _sessions_collection.create_index([("expires_at", ASCENDING)])  # For cleanup queries
    _sessions_collection.create_index([("created_at", DESCENDING)])
    _sessions_collection.create_index([("last_activity", DESCENDING)])
    _sessions_collection.create_index([("user_id", ASCENDING)])
    
    # TTL index: automatically delete expired sessions after 24 hours from expiration
    try:
        _sessions_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=86400)
        logger.info("Sessions TTL index created (24 hour cleanup)")
    except Exception as e:
        logger.info(f"Sessions TTL index already exists or error: {e}")
    
    logger.info("Sessions indexes created")
    
    # Audio Chunks indexes
    _audio_chunks_collection.create_index("session_id", unique=False)
    _audio_chunks_collection.create_index([("session_id", ASCENDING), ("chunk_index", ASCENDING)])
    _audio_chunks_collection.create_index([("created_at", DESCENDING)])
    logger.info("Audio chunks indexes created")
    
    # Session Analytics indexes
    _analytics_collection.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    _analytics_collection.create_index([("session_id", ASCENDING)])
    logger.info("Session analytics indexes created")

def store_voice_embedding(phone_number: str, embedding: np.ndarray) -> str:
    """
    Store or update a voice embedding for a phone number
    
    Args:
        phone_number: Unique identifier (phone number)
        embedding: 192-dimensional voice embedding
        
    Returns:
        Document ID of the stored/updated record
    """
    get_database()  # Ensure connection
    
    # Convert numpy array to list for MongoDB storage
    embedding_list = embedding.tolist()
    
    document = {
        "phone_number": phone_number,
        "embedding": embedding_list,
        "embedding_dimension": len(embedding_list),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Upsert: update if exists, insert if not
    result = _embeddings_collection.update_one(
        {"phone_number": phone_number},
        {
            "$set": {
                "embedding": embedding_list,
                "embedding_dimension": len(embedding_list),
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "phone_number": phone_number,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    if result.upserted_id:
        logger.info(f"Created new voice embedding for {phone_number}")
        return str(result.upserted_id)
    else:
        # Get existing document ID
        doc = _embeddings_collection.find_one({"phone_number": phone_number})
        logger.info(f"Updated voice embedding for {phone_number}")
        return str(doc["_id"])

def get_voice_embedding(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a voice embedding by phone number
    
    Args:
        phone_number: Phone number to look up
        
    Returns:
        Document with embedding or None if not found
    """
    get_database()  # Ensure connection
    document = _embeddings_collection.find_one({"phone_number": phone_number})
    
    if document:
        document["_id"] = str(document["_id"])
        return document
    return None

def check_enrollment(phone_number: str) -> bool:
    """
    Check if a phone number is enrolled
    
    Args:
        phone_number: Phone number to check
        
    Returns:
        True if enrolled, False otherwise
    """
    get_database()  # Ensure connection
    count = _embeddings_collection.count_documents({"phone_number": phone_number})
    return count > 0

def find_nearest_embedding(
    query_embedding: np.ndarray, 
    phone_number: Optional[str] = None,
    limit: int = 1
) -> List[Dict[str, Any]]:
    """
    Find the nearest embeddings using cosine similarity
    
    For MongoDB Atlas with Vector Search enabled, this would use:
    $vectorSearch aggregation pipeline
    
    For local MongoDB, we calculate similarity manually
    
    Args:
        query_embedding: Query embedding vector
        phone_number: Optional - filter to specific phone number
        limit: Maximum number of results
        
    Returns:
        List of documents with similarity scores
    """
    get_database()  # Ensure connection
    
    # Build query
    query = {}
    if phone_number:
        query["phone_number"] = phone_number
    
    # Fetch all matching documents (for local MongoDB)
    # Note: For production with large datasets, use MongoDB Atlas Vector Search
    cursor = _embeddings_collection.find(query)
    
    results = []
    query_norm = np.linalg.norm(query_embedding)
    
    for doc in cursor:
        stored_embedding = np.array(doc["embedding"])
        stored_norm = np.linalg.norm(stored_embedding)
        
        if query_norm > 0 and stored_norm > 0:
            # Calculate cosine similarity
            similarity = np.dot(query_embedding, stored_embedding) / (query_norm * stored_norm)
            # Convert from [-1, 1] to [0, 1]
            similarity = (similarity + 1) / 2
        else:
            similarity = 0.0
        
        results.append({
            "phone_number": doc["phone_number"],
            "similarity_score": float(similarity),
            "_id": str(doc["_id"])
        })
    
    # Sort by similarity (descending) and limit
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:limit]

def delete_voice_embedding(phone_number: str) -> bool:
    """
    Delete a voice embedding by phone number
    
    Args:
        phone_number: Phone number to delete
        
    Returns:
        True if deleted, False if not found
    """
    get_database()  # Ensure connection
    result = _embeddings_collection.delete_one({"phone_number": phone_number})
    return result.deleted_count > 0

def get_all_enrollments() -> List[Dict[str, Any]]:
    """
    Get all enrolled phone numbers (without embeddings)
    
    Returns:
        List of enrollment records (phone_number, created_at, updated_at)
    """
    get_database()  # Ensure connection
    cursor = _embeddings_collection.find({}, {"phone_number": 1, "created_at": 1, "updated_at": 1})
    
    results = []
    for doc in cursor:
        results.append({
            "phone_number": doc["phone_number"],
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "_id": str(doc["_id"])
        })
    
    return results

# ==================== SESSION MANAGEMENT FUNCTIONS ====================

def create_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new session in MongoDB
    
    Session Schema:
    {
        "session_id": str - Unique session identifier (required)
        "user_id": str - User identifier (required)
        "status": str - Session status: 'active', 'paused', 'completed', 'expired' (default: 'active')
        "created_at": datetime - Session creation timestamp
        "last_activity": datetime - Last activity timestamp
        "expires_at": datetime - Session expiration timestamp
        "ip_address": str - Client IP address (optional)
        "user_agent": str - Client user agent (optional)
        "metadata": dict - Custom session metadata (optional)
        "audio_chunks_count": int - Number of audio chunks stored (default: 0)
        "total_audio_size": int - Total size of audio data in bytes (default: 0)
    }
    
    Args:
        session_data: Dictionary with session information
            Required: session_id, user_id
            Optional: status, ip_address, user_agent, metadata, expires_at
            
    Returns:
        Created session document with _id
    """
    get_database()  # Ensure connection
    
    # Prepare session document
    session = {
        "session_id": session_data["session_id"],
        "user_id": session_data["user_id"],
        "status": session_data.get("status", "active"),
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "expires_at": session_data.get("expires_at", datetime.utcnow() + timedelta(minutes=30)),
        "ip_address": session_data.get("ip_address"),
        "user_agent": session_data.get("user_agent"),
        "metadata": session_data.get("metadata", {}),
        "audio_chunks_count": 0,
        "total_audio_size": 0
    }
    
    result = _sessions_collection.insert_one(session)
    logger.info(f"Session created: {session_data['session_id']} for user {session_data['user_id']}")
    
    session["_id"] = str(result.inserted_id)
    return session

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a session by session_id
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session document or None if not found
    """
    get_database()  # Ensure connection
    
    session = _sessions_collection.find_one({"session_id": session_id})
    if session:
        session["_id"] = str(session["_id"])
        return session
    return None

def update_session(session_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update a session's data
    
    Args:
        session_id: Session identifier
        update_data: Fields to update (e.g., {"status": "completed", "metadata": {...}})
        
    Returns:
        True if updated, False if session not found
    """
    get_database()  # Ensure connection
    
    # Always update last_activity
    update_data["last_activity"] = datetime.utcnow()
    
    result = _sessions_collection.update_one(
        {"session_id": session_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        logger.info(f"Session updated: {session_id}")
        return True
    return False

def delete_session(session_id: str) -> bool:
    """
    Delete a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if deleted, False if session not found
    """
    get_database()  # Ensure connection
    
    result = _sessions_collection.delete_one({"session_id": session_id})
    if result.deleted_count > 0:
        logger.info(f"Session deleted: {session_id}")
        # Also delete associated audio chunks
        _audio_chunks_collection.delete_many({"session_id": session_id})
        return True
    return False

def get_user_sessions(user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all sessions for a user, optionally filtered by status
    
    Args:
        user_id: User identifier
        status: Optional status filter ('active', 'completed', etc.)
        
    Returns:
        List of session documents
    """
    get_database()  # Ensure connection
    
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    sessions = list(_sessions_collection.find(query).sort("created_at", DESCENDING))
    for session in sessions:
        session["_id"] = str(session["_id"])
    
    return sessions

def get_active_sessions() -> List[Dict[str, Any]]:
    """
    Retrieve all active sessions
    
    Returns:
        List of active session documents
    """
    get_database()  # Ensure connection
    
    sessions = list(_sessions_collection.find(
        {"status": "active", "expires_at": {"$gt": datetime.utcnow()}}
    ).sort("last_activity", DESCENDING))
    
    for session in sessions:
        session["_id"] = str(session["_id"])
    
    return sessions

def cleanup_expired_sessions() -> int:
    """
    Delete all expired sessions
    
    Returns:
        Number of sessions deleted
    """
    get_database()  # Ensure connection
    
    result = _sessions_collection.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    
    if result.deleted_count > 0:
        logger.info(f"Cleaned up {result.deleted_count} expired sessions")
    
    return result.deleted_count

def extend_session(session_id: str, additional_minutes: int = 30) -> bool:
    """
    Extend a session's expiration time
    
    Args:
        session_id: Session identifier
        additional_minutes: Minutes to add to expiration time
        
    Returns:
        True if extended, False if session not found
    """
    get_database()  # Ensure connection
    
    session = _sessions_collection.find_one({"session_id": session_id})
    if not session:
        return False
    
    new_expires_at = session["expires_at"] + timedelta(minutes=additional_minutes)
    
    result = _sessions_collection.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "expires_at": new_expires_at,
                "last_activity": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


# ==================== AUDIO CHUNKS MANAGEMENT ====================

def save_audio_chunk(session_id: str, chunk_index: int, audio_data: bytes) -> str:
    """
    Save an audio chunk for a session
    
    Audio Chunk Schema:
    {
        "session_id": str - Session identifier
        "chunk_index": int - Index of this chunk in the stream
        "audio_data": bytes - Binary audio data
        "created_at": datetime - Creation timestamp
        "size_bytes": int - Size of audio_data in bytes
    }
    
    Args:
        session_id: Session identifier
        chunk_index: Index of this chunk
        audio_data: Binary audio data
        
    Returns:
        Document ID of the saved chunk
    """
    get_database()  # Ensure connection
    
    chunk = {
        "session_id": session_id,
        "chunk_index": chunk_index,
        "audio_data": audio_data,
        "created_at": datetime.utcnow(),
        "size_bytes": len(audio_data)
    }
    
    result = _audio_chunks_collection.insert_one(chunk)
    
    # Update session audio tracking
    _sessions_collection.update_one(
        {"session_id": session_id},
        {
            "$inc": {
                "audio_chunks_count": 1,
                "total_audio_size": len(audio_data)
            }
        }
    )
    
    logger.info(f"Saved audio chunk {chunk_index} for session {session_id} ({len(audio_data)} bytes)")
    return str(result.inserted_id)

def get_audio_chunks(session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all audio chunks for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of audio chunks sorted by chunk_index
    """
    get_database()  # Ensure connection
    
    chunks = list(_audio_chunks_collection.find(
        {"session_id": session_id}
    ).sort("chunk_index", ASCENDING))
    
    for chunk in chunks:
        chunk["_id"] = str(chunk["_id"])
    
    return chunks

def delete_audio_chunks(session_id: str) -> int:
    """
    Delete all audio chunks for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Number of chunks deleted
    """
    get_database()  # Ensure connection
    
    result = _audio_chunks_collection.delete_many({"session_id": session_id})
    
    if result.deleted_count > 0:
        logger.info(f"Deleted {result.deleted_count} audio chunks for session {session_id}")
    
    return result.deleted_count


# ==================== SESSION ANALYTICS ====================

def record_session_event(session_id: str, user_id: str, event_type: str, event_data: Dict[str, Any]) -> str:
    """
    Record a session event for analytics
    
    Session Analytics Schema:
    {
        "session_id": str - Session identifier
        "user_id": str - User identifier
        "event_type": str - Type of event ('created', 'audio_added', 'verification', 'completed', etc.)
        "details": dict - Event-specific details
        "created_at": datetime - Event timestamp
        "date": str - Date in YYYY-MM-DD format for daily aggregation
    }
    
    Args:
        session_id: Session identifier
        user_id: User identifier
        event_type: Type of event
        event_data: Event details
        
    Returns:
        Document ID of the recorded event
    """
    get_database()  # Ensure connection
    
    now = datetime.utcnow()
    event = {
        "session_id": session_id,
        "user_id": user_id,
        "event_type": event_type,
        "details": event_data,
        "created_at": now,
        "date": now.strftime("%Y-%m-%d")
    }
    
    result = _analytics_collection.insert_one(event)
    logger.info(f"Recorded event: {event_type} for session {session_id}")
    
    return str(result.inserted_id)

def get_session_events(session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all events for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of events sorted by creation time
    """
    get_database()  # Ensure connection
    
    events = list(_analytics_collection.find(
        {"session_id": session_id}
    ).sort("created_at", DESCENDING))
    
    for event in events:
        event["_id"] = str(event["_id"])
    
    return events

def get_user_analytics(user_id: str, days: int = 7) -> Dict[str, Any]:
    """
    Get analytics for a user over the past N days
    
    Args:
        user_id: User identifier
        days: Number of days to look back
        
    Returns:
        Analytics summary dictionary
    """
    get_database()  # Ensure connection
    
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    events = list(_analytics_collection.find({
        "user_id": user_id,
        "date": {"$gte": start_date}
    }).sort("created_at", DESCENDING))
    
    # Aggregate event counts by type
    event_counts = {}
    for event in events:
        event_type = event["event_type"]
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    return {
        "user_id": user_id,
        "period_days": days,
        "total_events": len(events),
        "event_types": event_counts,
        "events": [{"_id": str(e["_id"]), **{k: v for k, v in e.items() if k != "_id"}} for e in events]
    }

def get_session_statistics() -> Dict[str, Any]:
    """
    Get overall session statistics
    
    Returns:
        Dictionary with session statistics
    """
    get_database()  # Ensure connection
    
    now = datetime.utcnow()
    
    # Count sessions by status
    total_sessions = _sessions_collection.count_documents({})
    active_sessions = _sessions_collection.count_documents({
        "status": "active",
        "expires_at": {"$gt": now}
    })
    expired_sessions = _sessions_collection.count_documents({
        "expires_at": {"$lt": now}
    })
    
    # Average session duration
    completed_sessions = list(_sessions_collection.find(
        {"status": "completed"}
    ).limit(100))
    
    durations = []
    for session in completed_sessions:
        duration = (session.get("expires_at", now) - session["created_at"]).total_seconds()
        durations.append(duration)
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Audio statistics
    audio_stats = _sessions_collection.aggregate([
        {"$group": {
            "_id": None,
            "total_audio_size": {"$sum": "$total_audio_size"},
            "avg_audio_size": {"$avg": "$total_audio_size"},
            "total_chunks": {"$sum": "$audio_chunks_count"}
        }}
    ])
    
    audio_data = list(audio_stats)[0] if list(_sessions_collection.find({})) else {}
    
    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "expired_sessions": expired_sessions,
        "avg_session_duration_seconds": avg_duration,
        "audio": {
            "total_size_bytes": audio_data.get("total_audio_size", 0),
            "avg_size_per_session": audio_data.get("avg_audio_size", 0),
            "total_chunks": audio_data.get("total_chunks", 0)
        },
        "timestamp": now.isoformat()
    }