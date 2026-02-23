"""
MongoDB Database Module
Handles voice embedding storage and vector search operations
"""

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from typing import Optional, Dict, Any, List
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# MongoDB configuration
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "voice_biometric"
COLLECTION_NAME = "voice_embeddings"

# Global client instance
_client = None
_db = None
_collection = None
_enrollment_sessions_collection = None
_audio_chunks_collection = None
_enrollment_history_collection = None
_langchain_sessions_collection = None

def get_database():
    """Get MongoDB database connection"""
    global _client, _db, _collection
    
    if _client is None:
        logger.info(f"Connecting to MongoDB at {MONGODB_URL}...")
        _client = MongoClient(MONGODB_URL)
        _db = _client[DATABASE_NAME]
        _collection = _db[COLLECTION_NAME]
        
        # Create indexes
        _collection.create_index("phone_number", unique=True)
        
        # Create vector search index (for MongoDB Atlas)
        # Note: For local MongoDB, we'll use manual cosine similarity calculation
        # Atlas Vector Search requires specific index creation through Atlas UI or API
        
        logger.info("MongoDB connection established")
    
    return _collection

def get_enrollment_sessions_collection():
    """Get enrollment sessions collection"""
    global _enrollment_sessions_collection
    
    if _enrollment_sessions_collection is None:
        _db = _client[DATABASE_NAME] if _client else None
        if _db is None:
            get_database()  # Initialize connection
            _db = _client[DATABASE_NAME]
        
        _enrollment_sessions_collection = _db["enrollment_sessions"]
        
        # Create indexes
        _enrollment_sessions_collection.create_index("session_id", unique=True)
        _enrollment_sessions_collection.create_index("phone_number")
        _enrollment_sessions_collection.create_index("status")
        _enrollment_sessions_collection.create_index("created_at")
        
        logger.info("Enrollment sessions collection initialized")
    
    return _enrollment_sessions_collection

def get_audio_chunks_collection():
    """Get audio chunks collection"""
    global _audio_chunks_collection
    
    if _audio_chunks_collection is None:
        _db = _client[DATABASE_NAME] if _client else None
        if _db is None:
            get_database()  # Initialize connection
            _db = _client[DATABASE_NAME]
        
        _audio_chunks_collection = _db["audio_chunks"]
        
        # Create indexes
        _audio_chunks_collection.create_index("session_id")
        _audio_chunks_collection.create_index("chunk_id", unique=True)
        _audio_chunks_collection.create_index("phone_number")
        _audio_chunks_collection.create_index("created_at")
        
        logger.info("Audio chunks collection initialized")
    
    return _audio_chunks_collection

def get_enrollment_history_collection():
    """Get enrollment history collection"""
    global _enrollment_history_collection
    
    if _enrollment_history_collection is None:
        _db = _client[DATABASE_NAME] if _client else None
        if _db is None:
            get_database()  # Initialize connection
            _db = _client[DATABASE_NAME]
        
        _enrollment_history_collection = _db["enrollment_history"]
        
        # Create indexes
        _enrollment_history_collection.create_index("phone_number")
        _enrollment_history_collection.create_index("session_id")
        _enrollment_history_collection.create_index("completed_at")
        _enrollment_history_collection.create_index([("completed_at", -1)])  # For sorting
        
        logger.info("Enrollment history collection initialized")
    
    return _enrollment_history_collection

def store_voice_embedding(phone_number: str, embedding: np.ndarray) -> str:
    """
    Store or update a voice embedding for a phone number
    
    Args:
        phone_number: Unique identifier (phone number)
        embedding: 192-dimensional voice embedding
        
    Returns:
        Document ID of the stored/updated record
    """
    collection = get_database()
    
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
    result = collection.update_one(
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
        doc = collection.find_one({"phone_number": phone_number})
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
    collection = get_database()
    document = collection.find_one({"phone_number": phone_number})
    
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
    collection = get_database()
    count = collection.count_documents({"phone_number": phone_number})
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
    collection = get_database()
    
    # Build query
    query = {}
    if phone_number:
        query["phone_number"] = phone_number
    
    # Fetch all matching documents (for local MongoDB)
    # Note: For production with large datasets, use MongoDB Atlas Vector Search
    cursor = collection.find(query)
    
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

def verify_phone_number_embedding(
    query_embedding: np.ndarray,
    phone_number: str
) -> Optional[Dict[str, Any]]:
    """
    Optimized verification: Check if phone number exists and compare embedding
    
    This function is optimized for verification flow:
    1. Uses indexed query on phone_number (much faster)
    2. Fetches only ONE document (the registered user)
    3. Calculates similarity with that one embedding
    4. Returns result immediately without searching through all documents
    
    Args:
        query_embedding: Query embedding vector from input voice
        phone_number: Phone number to verify against
        
    Returns:
        Dict with phone_number and similarity_score, or None if not found
    """
    collection = get_database()
    
    # Fast indexed lookup - only returns the ONE document with this phone_number
    doc = collection.find_one({"phone_number": phone_number})
    
    if not doc:
        # Phone number not enrolled
        return None
    
    # Calculate similarity with the stored embedding
    stored_embedding = np.array(doc["embedding"])
    
    query_norm = np.linalg.norm(query_embedding)
    stored_norm = np.linalg.norm(stored_embedding)
    
    if query_norm > 0 and stored_norm > 0:
        # Calculate cosine similarity
        similarity = np.dot(query_embedding, stored_embedding) / (query_norm * stored_norm)
        # Convert from [-1, 1] to [0, 1]
        similarity = (similarity + 1) / 2
    else:
        similarity = 0.0
    
    return {
        "phone_number": doc["phone_number"],
        "similarity_score": float(similarity),
        "_id": str(doc["_id"]),
        "embedding": doc.get("embedding")  # Include embedding for detailed metrics
    }

def delete_voice_embedding(phone_number: str) -> bool:
    """
    Delete a voice embedding by phone number
    
    Args:
        phone_number: Phone number to delete
        
    Returns:
        True if deleted, False if not found
    """
    collection = get_database()
    result = collection.delete_one({"phone_number": phone_number})
    return result.deleted_count > 0

def get_all_enrollments() -> List[Dict[str, Any]]:
    """
    Get all enrolled phone numbers (without embeddings)
    
    Returns:
        List of enrollment records (phone_number, created_at, updated_at)
    """
    collection = get_database()
    cursor = collection.find({}, {"phone_number": 1, "created_at": 1, "updated_at": 1})
    
    results = []
    for doc in cursor:
        results.append({
            "phone_number": doc["phone_number"],
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "_id": str(doc["_id"])
        })
    
    return results

# ==================== ENROLLMENT SESSION OPERATIONS ====================

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
        logger.info(f"Created enrollment session {session_data['session_id'][:8]}")
        return str(result.upserted_id)
    else:
        doc = collection.find_one({"session_id": session_data["session_id"]})
        logger.info(f"Updated enrollment session {session_data['session_id'][:8]}")
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
        logger.info(f"Cleaned up {result.deleted_count} expired enrollment sessions")
    
    return result.deleted_count


# ==================== AUDIO CHUNKS OPERATIONS ====================

def save_audio_chunk(chunk_data: Dict[str, Any]) -> str:
    """
    Save an audio chunk to MongoDB
    
    Args:
        chunk_data: Audio chunk data dictionary
        
    Returns:
        Chunk document ID
    """
    collection = get_audio_chunks_collection()
    
    # Ensure chunk_id is present
    if "chunk_id" not in chunk_data:
        raise ValueError("chunk_data must contain 'chunk_id'")
    
    # Remove audio_data if present (too large for storage) - store metadata only
    chunk_data_copy = chunk_data.copy()
    if "audio_data" in chunk_data_copy:
        # Replace with size info instead
        audio_array = chunk_data_copy["audio_data"]
        if isinstance(audio_array, np.ndarray):
            chunk_data_copy["audio_data_size"] = int(audio_array.nbytes)
            chunk_data_copy["audio_samples"] = int(audio_array.shape[0])
        del chunk_data_copy["audio_data"]
    
    result = collection.insert_one({
        **chunk_data_copy,
        "created_at": datetime.utcnow()
    })
    
    logger.info(f"Saved audio chunk {chunk_data['chunk_id'][:8]} for session {chunk_data.get('session_id', 'unknown')[:8]}")
    return str(result.inserted_id)


def get_audio_chunks_for_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all audio chunks for an enrollment session
    
    Args:
        session_id: Session ID to retrieve chunks for
        
    Returns:
        List of audio chunk records
    """
    collection = get_audio_chunks_collection()
    cursor = collection.find({"session_id": session_id}).sort("created_at", 1)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


# ==================== ENROLLMENT HISTORY OPERATIONS ====================

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
    
    logger.info(
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


# ==================== VERIFIED SESSIONS OPERATIONS ====================

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
    
    logger.info("Verified sessions collection initialized")
    
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
        logger.info(f"Created verified session {session_data['session_id'][:8]} for {session_data.get('phone_number')}")
        return str(result.upserted_id)
    else:
        doc = collection.find_one({"session_id": session_data["session_id"]})
        logger.info(f"Updated verified session {session_data['session_id'][:8]}")
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


# ========== LANGCHAIN SESSION STORAGE ==========

def get_langchain_sessions_collection():
    """Get LangChain sessions collection"""
    global _langchain_sessions_collection, _db, _client
    
    if _langchain_sessions_collection is None:
        if _db is None:
            get_database()  # Initialize connection
            _db = _client[DATABASE_NAME]
        
        _langchain_sessions_collection = _db["langchain_sessions"]
        
        # Create indexes for efficient querying
        _langchain_sessions_collection.create_index("session_id", unique=True)
        _langchain_sessions_collection.create_index("phone_number")
        _langchain_sessions_collection.create_index("langgraph_thread_id")
        _langchain_sessions_collection.create_index("session_status")
        _langchain_sessions_collection.create_index("last_activity")
        
        # Create TTL index for automatic expiration (expire after 24 hours)
        try:
            _langchain_sessions_collection.create_index(
                "start_time",
                expireAfterSeconds=86400  # 24 hours
            )
        except Exception as e:
            logger.warning(f"Failed to create TTL index on start_time: {str(e)} (may already exist)")
        
        logger.info("LangChain sessions collection initialized")
    
    return _langchain_sessions_collection


def save_langchain_session(session_data: Dict[str, Any]) -> str:
    """
    Save a LangChain session to MongoDB
    
    Args:
        session_data: LangChain session data dictionary
        
    Returns:
        Session document ID
    """
    collection = get_langchain_sessions_collection()
    
    # Ensure session_id is present
    if "metadata" not in session_data:
        raise ValueError("session_data must contain 'metadata'")
    
    if "session_id" not in session_data["metadata"]:
        raise ValueError("metadata must contain 'session_id'")
    
    session_id = session_data["metadata"]["session_id"]
    
    # Ensure phone_number is in top level for easy querying
    if "phone_number" not in session_data:
        session_data["phone_number"] = session_data["metadata"].get("phone_number")
    
    # Ensure status is in top level
    if "session_status" not in session_data:
        session_data["session_status"] = session_data["metadata"].get("session_status")
    
    result = collection.update_one(
        {"session_id": session_id},
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
        logger.info(
            f"Created LangChain session {session_id[:16]} "
            f"for {session_data.get('phone_number')}"
        )
        return str(result.upserted_id)
    else:
        doc = collection.find_one({"session_id": session_id})
        logger.info(f"Updated LangChain session {session_id[:16]}")
        return str(doc["_id"])


def get_langchain_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a LangChain session by ID
    
    Args:
        session_id: The LangChain session ID
        
    Returns:
        Session data dict or None if not found
    """
    collection = get_langchain_sessions_collection()
    doc = collection.find_one({"session_id": session_id})
    
    if doc:
        doc["_id"] = str(doc["_id"])
        return doc
    
    return None


def update_langchain_session_status(session_id: str, status: str) -> bool:
    """
    Update the status of a LangChain session
    
    Args:
        session_id: The session ID
        status: New status value
        
    Returns:
        True if updated, False if not found
    """
    collection = get_langchain_sessions_collection()
    
    result = collection.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "session_status": status,
                "metadata.session_status": status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


def add_conversation_turn(
    session_id: str,
    role: str,
    content: str,
    turn_metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Add a conversation turn to LangChain session history
    
    Args:
        session_id: The session ID
        role: Role of speaker ("user" or "assistant")
        content: Message content
        turn_metadata: Optional metadata about the turn
        
    Returns:
        True if added, False if session not found
    """
    collection = get_langchain_sessions_collection()
    
    turn = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow(),
        "metadata": turn_metadata or {}
    }
    
    result = collection.update_one(
        {"session_id": session_id},
        {
            "$push": {
                "metadata.conversation_history": turn,
                "conversation_history": turn
            },
            "$inc": {
                "metadata.current_turn": 1
            },
            "$set": {
                "last_activity": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0


def get_langchain_sessions_by_phone(phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get all LangChain sessions for a phone number
    
    Args:
        phone_number: The phone number
        limit: Maximum results to return
        
    Returns:
        List of session documents
    """
    collection = get_langchain_sessions_collection()
    cursor = collection.find(
        {"phone_number": phone_number}
    ).sort("start_time", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def get_active_langchain_sessions(status: str = "active", limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all active LangChain sessions
    
    Args:
        status: Session status to filter by
        limit: Maximum results to return
        
    Returns:
        List of session documents
    """
    collection = get_langchain_sessions_collection()
    cursor = collection.find(
        {"session_status": status}
    ).sort("last_activity", -1).limit(limit)
    
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


def get_langchain_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a summary of a LangChain session
    
    Args:
        session_id: The session ID
        
    Returns:
        Session summary dict or None if not found
    """
    doc = get_langchain_session(session_id)
    if not doc:
        return None
    
    metadata = doc.get("metadata", {})
    start_time = metadata.get("start_time", doc.get("start_time"))
    end_time = metadata.get("end_time", doc.get("end_time"))
    last_activity = metadata.get("last_activity", doc.get("last_activity"))
    
    # Calculate duration
    if isinstance(start_time, datetime) and (isinstance(end_time, datetime) or end_time is None):
        end = end_time or datetime.utcnow()
        duration = (end - start_time).total_seconds()
    else:
        duration = 0
    
    return {
        "session_id": session_id,
        "phone_number": metadata.get("phone_number"),
        "status": metadata.get("session_status"),
        "thread_id": metadata.get("langgraph_thread_id"),
        "verification_score": metadata.get("verification_score", 0.0),
        "duration_seconds": duration,
        "conversation_turns": metadata.get("current_turn", 0),
        "messages": len(metadata.get("conversation_history", [])),
        "started_at": start_time.isoformat() if isinstance(start_time, datetime) else start_time,
        "last_activity": last_activity.isoformat() if isinstance(last_activity, datetime) else last_activity,
        "voice_verified": metadata.get("voice_verified", True),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at")
    }


def delete_expired_langchain_sessions(ttl_seconds: int = 86400) -> int:
    """
    Delete expired LangChain sessions
    
    Args:
        ttl_seconds: Sessions older than this are considered expired
        
    Returns:
        Number of sessions deleted
    """
    collection = get_langchain_sessions_collection()
    cutoff_time = datetime.utcnow() - __import__('datetime').timedelta(seconds=ttl_seconds)
    
    result = collection.delete_many({
        "start_time": {"$lt": cutoff_time}
    })
    
    if result.deleted_count > 0:
        logger.info(f"Deleted {result.deleted_count} expired LangChain sessions")
    
    return result.deleted_count
