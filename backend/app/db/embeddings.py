import logging
import time
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.connection import get_database

logger = logging.getLogger(__name__)


def store_voice_embedding(phone_number: str, embedding: np.ndarray) -> str:
    """
    Store or update a voice embedding for a phone number
    
    Args:
        phone_number: Unique identifier (phone number)
        embedding: 192-dimensional voice embedding
        
    Returns:
        Document ID of the stored/updated record
    """
    logger.info(
        "store_voice_embedding() | phone=%s embedding_dim=%d norm=%.4f",
        phone_number,
        len(embedding),
        float(np.linalg.norm(embedding)),
    )
    t0 = time.perf_counter()

    collection = get_database()

    # Convert numpy array to list for MongoDB storage
    embedding_list = embedding.tolist()

    now = datetime.utcnow()
    # Upsert: update if exists, insert if not
    result = collection.update_one(
        {"phone_number": phone_number},
        {
            "$set": {
                "embedding": embedding_list,
                "embedding_dimension": len(embedding_list),
                "updated_at": now,
            },
            "$setOnInsert": {
                "phone_number": phone_number,
                "created_at": now,
            },
        },
        upsert=True,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1_000

    if result.upserted_id:
        doc_id = str(result.upserted_id)
        logger.info(
            "DB INSERT voice embedding | phone=%s doc_id=%s elapsed=%.2fms",
            phone_number,
            doc_id,
            elapsed_ms,
        )
        return doc_id
    else:
        doc = collection.find_one({"phone_number": phone_number})
        doc_id = str(doc["_id"])
        logger.info(
            "DB UPDATE voice embedding | phone=%s doc_id=%s elapsed=%.2fms",
            phone_number,
            doc_id,
            elapsed_ms,
        )
        return doc_id


def get_voice_embedding(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a voice embedding by phone number

    Args:
        phone_number: Phone number to look up

    Returns:
        Document with embedding or None if not found
    """
    logger.debug("get_voice_embedding() | phone=%s", phone_number)
    t0 = time.perf_counter()

    collection = get_database()
    document = collection.find_one({"phone_number": phone_number})

    elapsed_ms = (time.perf_counter() - t0) * 1_000

    if document:
        document["_id"] = str(document["_id"])
        dim = len(document.get("embedding", []))
        logger.info(
            "DB FOUND voice embedding | phone=%s dim=%d elapsed=%.2fms",
            phone_number,
            dim,
            elapsed_ms,
        )
        return document

    logger.info(
        "DB NOT FOUND voice embedding | phone=%s elapsed=%.2fms",
        phone_number,
        elapsed_ms,
    )
    return None


def check_enrollment(phone_number: str) -> bool:
    """
    Check if a phone number is enrolled

    Args:
        phone_number: Phone number to check

    Returns:
        True if enrolled, False otherwise
    """
    logger.debug("check_enrollment() | phone=%s", phone_number)
    t0 = time.perf_counter()

    collection = get_database()
    count = collection.count_documents({"phone_number": phone_number})

    elapsed_ms = (time.perf_counter() - t0) * 1_000
    enrolled = count > 0
    logger.debug(
        "check_enrollment() result | phone=%s enrolled=%s elapsed=%.2fms",
        phone_number,
        enrolled,
        elapsed_ms,
    )
    return enrolled


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
    phone_number: str,
) -> Optional[Dict[str, Any]]:
    """
    Optimised verification: indexed phone_number lookup + cosine similarity.

    Args:
        query_embedding: Query embedding vector from input voice
        phone_number: Phone number to verify against

    Returns:
        Dict with phone_number and similarity_score, or None if not found
    """
    logger.info(
        "verify_phone_number_embedding() | phone=%s query_norm=%.4f",
        phone_number,
        float(np.linalg.norm(query_embedding)),
    )
    t0 = time.perf_counter()

    collection = get_database()

    # Fast indexed lookup
    doc = collection.find_one({"phone_number": phone_number})
    db_ms = (time.perf_counter() - t0) * 1_000

    if not doc:
        logger.info(
            "verify_phone_number_embedding() NOT FOUND | phone=%s db_time=%.2fms",
            phone_number,
            db_ms,
        )
        return None

    # Calculate cosine similarity
    stored_embedding = np.array(doc["embedding"])
    stored_norm = np.linalg.norm(stored_embedding)
    query_norm = np.linalg.norm(query_embedding)

    if query_norm > 0 and stored_norm > 0:
        similarity = np.dot(query_embedding, stored_embedding) / (query_norm * stored_norm)
        similarity = (similarity + 1) / 2
    else:
        similarity = 0.0

    total_ms = (time.perf_counter() - t0) * 1_000
    logger.info(
        "verify_phone_number_embedding() result | phone=%s "
        "similarity=%.6f stored_norm=%.4f query_norm=%.4f db_time=%.2fms total_time=%.2fms",
        phone_number,
        float(similarity),
        float(stored_norm),
        float(query_norm),
        db_ms,
        total_ms,
    )

    return {
        "phone_number": doc["phone_number"],
        "similarity_score": float(similarity),
        "_id": str(doc["_id"]),
        "embedding": doc.get("embedding"),
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