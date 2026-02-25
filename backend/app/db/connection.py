import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from app.core.config import settings

# MongoDB configuration
MONGODB_URL = settings.MONGODB_URL
DATABASE_NAME = settings.DATABASE_NAME

# Global client instance
_client = None
_db = None
_collection = None
_enrollment_sessions_collection = None
_audio_chunks_collection = None
_enrollment_history_collection = None

def get_database():
    """Get MongoDB database connection"""
    global _client, _db, _collection
    
    if _client is None:
        logging.info(f"Connecting to MongoDB at {MONGODB_URL}...")
        _client = MongoClient(MONGODB_URL)
        _db = _client[DATABASE_NAME]
        _collection = _db["voice_embeddings"]
        
        # Create indexes
        _collection.create_index("phone_number", unique=True)
        
        # Create vector search index (for MongoDB Atlas)
        # Note: For local MongoDB, we'll use manual cosine similarity calculation
        # Atlas Vector Search requires specific index creation through Atlas UI or API
        
        logging.info("MongoDB connection established")
    
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
        
        logging.info("Enrollment sessions collection initialized")
    
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
        
        logging.info("Audio chunks collection initialized")
    
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
        
        logging.info("Enrollment history collection initialized")
    
    return _enrollment_history_collection

def get_db_instance():
    """Return the raw PyMongo Database object (initializes connection if needed)."""
    global _db
    if _db is None:
        get_database()  # Initialize connection and set _db
    return _db
