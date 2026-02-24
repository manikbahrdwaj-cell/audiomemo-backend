import logging
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.connection import get_database

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
        logging.info(f"Created new voice embedding for {phone_number}")
        return str(result.upserted_id)
    else:
        # Get existing document ID
        doc = collection.find_one({"phone_number": phone_number})
        logging.info(f"Updated voice embedding for {phone_number}")
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