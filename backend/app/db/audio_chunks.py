import logging
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
from app.db.connection import get_audio_chunks_collection

logger = logging.getLogger(__name__)

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