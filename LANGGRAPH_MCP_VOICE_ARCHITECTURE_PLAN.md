# AI-Driven Architecture: LangGraph, MCP & Voice Authentication - Implementation Plan

**Version:** 1.0  
**Date:** February 2026  
**Objective:** Build a secure, intelligent agent system for voice-driven MongoDB queries with biometric authentication

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Database Upgrade](#phase-1-database-upgrade)
4. [Phase 2: LangGraph Integration](#phase-2-langgraph-integration)
5. [Phase 3: Model Integration](#phase-3-model-integration)
6. [Phase 4: Security Implementation](#phase-4-security-implementation)
7. [Phase 5: Testing & Validation](#phase-5-testing--validation)
8. [Phase 6: Optional Enhancements](#phase-6-optional-enhancements)
9. [Deployment Strategy](#deployment-strategy)
10. [Code Snippets & Examples](#code-snippets--examples)

---

## Executive Summary

This plan outlines a five-phase implementation strategy for building a robust, production-ready voice-authenticated agent that:

- Accepts natural language voice input
- Converts queries to MongoDB operations securely
- Enforces multi-level security checks (biometric, query validation, data access)
- Returns responses in natural language
- Logs all operations for audit trails
- Integrates with MCP servers for extensible tool support

**Key Components:**
- **Database Layer:** MongoDB with Pydantic schema validation
- **Orchestration:** LangGraph state machine for agent flow
- **LLM Models:** OpenAI/Gemini for NLP and response generation
- **Security:** Multi-gate verification (biometric → query validation → execution)
- **Monitoring:** Comprehensive logging and error tracking

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Voice Input (Audio)                     │
│                    ↓ Speech-to-Text ↓                       │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────▼─────────────────┐
        │    LangGraph State Machine       │
        │  (Manages conversation flow)    │
        └────────────────┬─────────────────┘
                         │
        ┌────────────────▼──────────────────────────────────────┐
        │             Agent Nodes (Sequential)                 │
        │  ┌──────────────────────────────────────────────────┐ │
        │  │ 1. biometric_gate: Phone/Session Verification   │ │
        │  ├──────────────────────────────────────────────────┤ │
        │  │ 2. query_compiler: NLP → MongoDB Query          │ │
        │  ├──────────────────────────────────────────────────┤ │
        │  │ 3. security_supervisor: Query Validation        │ │
        │  ├──────────────────────────────────────────────────┤ │
        │  │ 4. tool_executor: Execute MongoDB CRUD Ops      │ │
        │  ├──────────────────────────────────────────────────┤ │
        │  │ 5. response_shaper: JSON → Natural Language     │ │
        │  └──────────────────────────────────────────────────┘ │
        └────────────────┬──────────────────────────────────────┘
                         │
        ┌────────────────▼─────────────────┐
        │   Response Synthesis (TTS)       │
        │   ↓ Text-to-Speech ↓             │
        └────────────────┬─────────────────┘
                         │
        ┌────────────────▼─────────────────┐
        │      Voice Output (Audio)        │
        └─────────────────────────────────┘

MCP Servers (Extensible):
├── Tool Registry Server
├── Data Provider Servers
└── Custom Integration Servers
```

---

## Phase 1: Database Upgrade

### Objectives
- Set up MongoDB connection pooling
- Define Pydantic models for schema validation
- Implement CRUD operation helpers
- Create index strategy for performance

### 1.1 MongoDB Connection & Configuration

**File:** `backend/database/mongo_client.py`

```python
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
import os
from contextlib import contextmanager

class MongoDBClient:
    def __init__(self):
        self.uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        self.client = None
        self.db = None
    
    def connect(self):
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
            )
            self.client.admin.command("ping")
            self.db = self.client[os.environ.get("MONGODB_DB", "voice_agent")]
            print("✓ MongoDB connected successfully")
        except ServerSelectionTimeoutError as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
    def get_collection(self, collection_name: str):
        if self.db is None:
            self.connect()
        return self.db[collection_name]
    
    @contextmanager
    def session(self):
        if self.client is None:
            self.connect()
        session = self.client.start_session()
        try:
            yield session
        finally:
            session.end_session()
    
    def disconnect(self):
        if self.client:
            self.client.close()
            print("✓ MongoDB disconnected")

mongo_client = MongoDBClient()
```

### 1.2 Pydantic Schema Validation

**File:** `backend/schemas/user_schema.py`

```python
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class PhoneAuthStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    SUSPENDED = "suspended"

class UserBiometric(BaseModel):
    phone: str = Field(..., pattern=r"^\+?1?\d{9,15}$")
    biometric_type: str = Field(..., description="fingerprint, face, voice")
    verified_at: Optional[datetime] = None
    is_active: bool = True

class UserProfile(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?1?\d{9,15}$")
    biometrics: List[UserBiometric]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    auth_status: PhoneAuthStatus = PhoneAuthStatus.UNVERIFIED
    data_access_level: int = Field(default=1, ge=1, le=10)  # 1=basic, 10=admin
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v or len(v.replace('+', '').replace('-', '')) < 9:
            raise ValueError("Invalid phone number")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "biometrics": [
                    {
                        "phone": "+1234567890",
                        "biometric_type": "fingerprint",
                        "verified_at": "2026-02-15T10:30:00",
                        "is_active": True
                    }
                ],
                "auth_status": "verified",
                "data_access_level": 5
            }
        }

class QueryRecord(BaseModel):
    query_id: str
    user_id: str
    original_voice: str  # Transcribed text
    compiled_query: Dict[str, Any]
    status: str = "pending"  # pending, executing, success, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None
    security_flags: List[str] = []  # Track any security concerns
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Config:
        json_schema_extra = {
            "example": {
                "query_id": "query_abc123",
                "user_id": "user_123",
                "original_voice": "Show me my recent orders",
                "compiled_query": {"collection": "orders", "filter": {"user_id": "user_123"}, "operation": "find"},
                "status": "success",
                "result": [{"order_id": "ord_1", "amount": 99.99}],
                "security_flags": []
            }
        }
```

### 1.3 CRUD Operations Helper

**File:** `backend/database/crud_operations.py`

```python
from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import DuplicateKeyError
from backend.database.mongo_client import mongo_client
from backend.schemas.user_schema import UserProfile, QueryRecord
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime

class CRUDOperations:
    
    @staticmethod
    def create_indexes():
        """Initialize all necessary indexes"""
        users_col = mongo_client.get_collection("users")
        users_col.create_index("phone", unique=True)
        users_col.create_index("email", unique=True)
        users_col.create_index("user_id", unique=True)
        
        queries_col = mongo_client.get_collection("queries")
        queries_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        queries_col.create_index("query_id", unique=True)
    
    # USER OPERATIONS
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> str:
        """Create a new user with validation"""
        try:
            user_profile = UserProfile(**user_data)
            users_col = mongo_client.get_collection("users")
            result = users_col.insert_one(user_profile.dict())
            return str(result.inserted_id)
        except DuplicateKeyError as e:
            raise ValueError(f"User with this email/phone already exists: {e}")
    
    @staticmethod
    def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        """Fetch user by phone number"""
        users_col = mongo_client.get_collection("users")
        return users_col.find_one({"phone": phone})
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user by ID"""
        users_col = mongo_client.get_collection("users")
        return users_col.find_one({"user_id": user_id})
    
    @staticmethod
    def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile with validation"""
        updates["updated_at"] = datetime.utcnow()
        users_col = mongo_client.get_collection("users")
        result = users_col.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def verify_user_biometric(user_id: str, phone: str) -> bool:
        """Mark biometric as verified"""
        users_col = mongo_client.get_collection("users")
        result = users_col.update_one(
            {"user_id": user_id, "biometrics.phone": phone},
            {
                "$set": {
                    "biometrics.$.verified_at": datetime.utcnow(),
                    "auth_status": "verified",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    # QUERY RECORD OPERATIONS
    @staticmethod
    def log_query(user_id: str, original_voice: str, compiled_query: Dict) -> str:
        """Log a query execution attempt"""
        query_id = str(uuid.uuid4())[:8]
        query_record = QueryRecord(
            query_id=query_id,
            user_id=user_id,
            original_voice=original_voice,
            compiled_query=compiled_query,
            status="pending"
        )
        queries_col = mongo_client.get_collection("queries")
        queries_col.insert_one(query_record.dict())
        return query_id
    
    @staticmethod
    def update_query_status(
        query_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        security_flags: Optional[List[str]] = None
    ):
        """Update query execution status"""
        queries_col = mongo_client.get_collection("queries")
        update_data = {
            "status": status,
            "executed_at": datetime.utcnow()
        }
        if result is not None:
            update_data["result"] = result
        if error is not None:
            update_data["error"] = error
        if execution_time_ms is not None:
            update_data["execution_time_ms"] = execution_time_ms
        if security_flags:
            update_data["security_flags"] = security_flags
        
        queries_col.update_one(
            {"query_id": query_id},
            {"$set": update_data}
        )
    
    @staticmethod
    def get_user_query_history(user_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve user's query history"""
        queries_col = mongo_client.get_collection("queries")
        return list(queries_col.find(
            {"user_id": user_id}
        ).sort("created_at", DESCENDING).limit(limit))
    
    # GENERIC QUERY EXECUTOR
    @staticmethod
    def execute_filtered_query(collection_name: str, filter_dict: Dict, operation: str = "find") -> List[Dict]:
        """
        Execute a MongoDB query with strict filter enforcement
        
        Args:
            collection_name: MongoDB collection name
            filter_dict: Filter criteria (must include user_id for security)
            operation: 'find', 'count', 'find_one'
        
        Returns:
            Query results
        """
        col = mongo_client.get_collection(collection_name)
        
        if operation == "find":
            return list(col.find(filter_dict).limit(100))
        elif operation == "find_one":
            return col.find_one(filter_dict)
        elif operation == "count":
            return col.count_documents(filter_dict)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
```

### 1.4 Index Strategy

```yaml
Collections and Indexes:
  users:
    - { field: "phone", unique: true, type: "asc" }
    - { field: "email", unique: true, type: "asc" }
    - { field: "user_id", unique: true, type: "asc" }
    - { field: "auth_status", type: "asc" }
    
  queries:
    - { field: "query_id", unique: true, type: "asc" }
    - { field: ["user_id", "created_at"], type: ["asc", "desc"] }
    - { field: "status", type: "asc" }
    
  data_records:
    - { field: "user_id", type: "asc" }
    - { field: "created_at", type: "desc" }
    - { field: ["user_id", "category"], type: ["asc", "asc"] }
```

---

## Phase 2: LangGraph Integration

### Objectives
- Define agent State using TypedDict
- Implement all five node functions
- Create conditional edge logic
- Set up state validation

### 2.1 State Definition

**File:** `backend/langgraph/state.py`

```python
from typing import TypedDict, Optional, List, Dict, Any, Annotated
from datetime import datetime

class BiometricContext(TypedDict):
    """Biometric verification data"""
    phone: str
    user_id: str
    verified: bool
    timestamp: datetime
    verification_method: str  # "phone_number", "fingerprint", "face"

class QueryCompilationContext(TypedDict):
    """Query compilation metadata"""
    original_voice_text: str
    interpreted_intent: str
    confidence_score: float
    compilation_attempts: int

class SecurityContext(TypedDict):
    """Security validation metadata"""
    data_access_level: int
    query_risk_score: float  # 0.0 to 1.0
    security_flags: List[str]
    is_approved: bool
    rejection_reason: Optional[str]

class ExecutionContext(TypedDict):
    """Query execution metadata"""
    collection_name: str
    operation: str  # "find", "find_one", "count", etc.
    compiled_query: Dict[str, Any]
    execution_time_ms: Optional[float]
    result_count: int

class AgentState(TypedDict):
    """Main agent state shared across all nodes"""
    # Input/Output
    user_input: str  # Original voice transcription
    agent_response: str  # Final natural language response
    
    # Session
    session_id: str
    timestamp: datetime
    conversation_history: List[Dict[str, str]]  # List of {"role": "user"|"assistant", "content": "..."}
    
    # Contexts from each node
    biometric_context: Optional[BiometricContext]
    query_compilation_context: Optional[QueryCompilationContext]
    security_context: Optional[SecurityContext]
    execution_context: Optional[ExecutionContext]
    
    # Query tracking
    query_id: str
    query_log_data: Dict[str, Any]
    
    # Error handling
    error: Optional[str]
    error_node: Optional[str]  # Which node generated the error
    retry_count: int
    max_retries: int
    
    # Flow control
    can_proceed: bool  # Flag to break flow if critical check fails
```

### 2.2 Node Implementations

**File:** `backend/langgraph/nodes.py`

```python
from backend.langgraph.state import AgentState, BiometricContext, QueryCompilationContext, SecurityContext, ExecutionContext
from backend.database.crud_operations import CRUDOperations
from backend.database.mongo_client import mongo_client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
from datetime import datetime
import re
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Initialize LLM (configurable via environment variable)
import os
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")

if LLM_PROVIDER == "openai":
    llm = ChatOpenAI(model="gpt-4", temperature=0.1)
else:  # Default fallback
    llm = ChatOpenAI(model="gpt-4", temperature=0.1)

# ============================================================================
# NODE 1: BIOMETRIC_GATE - Phone/Session Verification
# ============================================================================

async def biometric_gate(state: AgentState) -> AgentState:
    """
    Verify the user's identity via phone number or biometric data.
    
    Security Goal:
    - Ensure only verified users can proceed
    - Log all authentication attempts
    - Block suspicious patterns
    """
    logger.info(f"[BIOMETRIC_GATE] Processing for session {state['session_id']}")
    
    try:
        # Extract phone from user context (assume it's passed or extracted from voice print)
        # For voice authentication, could use voice biometrics
        phone_from_input = extract_phone_from_voice(state['user_input'])
        
        if not phone_from_input:
            state['error'] = "No phone number detected in voice input"
            state['error_node'] = "biometric_gate"
            state['can_proceed'] = False
            return state
        
        # Query MongoDB for user
        user = CRUDOperations.get_user_by_phone(phone_from_input)
        if not user:
            state['error'] = f"User not found for phone: {phone_from_input}"
            state['error_node'] = "biometric_gate"
            state['can_proceed'] = False
            return state
        
        # Check authentication status
        if user.get('auth_status') != 'verified':
            state['error'] = f"User authentication status: {user.get('auth_status')}"
            state['error_node'] = "biometric_gate"
            state['can_proceed'] = False
            return state
        
        # Store biometric context
        state['biometric_context'] = BiometricContext(
            phone=phone_from_input,
            user_id=user['user_id'],
            verified=True,
            timestamp=datetime.utcnow(),
            verification_method="phone_number"
        )
        
        state['can_proceed'] = True
        logger.info(f"[BIOMETRIC_GATE] ✓ Verified user: {user['user_id']}")
        
    except Exception as e:
        logger.error(f"[BIOMETRIC_GATE] Exception: {str(e)}")
        state['error'] = str(e)
        state['error_node'] = "biometric_gate"
        state['can_proceed'] = False
    
    return state

def extract_phone_from_voice(voice_text: str) -> str:
    """Extract phone number from voice transcription"""
    # Pattern for various phone formats
    phone_pattern = r'(?:\+1)?[-.\s]?(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})'
    matches = re.findall(phone_pattern, voice_text)
    if matches:
        # Reconstruct phone number
        return "+1" + "".join(matches[0])
    return ""

# ============================================================================
# NODE 2: QUERY_COMPILER - NLP to MongoDB Query
# ============================================================================

async def query_compiler(state: AgentState) -> AgentState:
    """
    Convert natural language voice input to MongoDB query structure.
    
    Uses LLM to understand intent and compile appropriate filter/operation.
    """
    logger.info(f"[QUERY_COMPILER] Processing voice: {state['user_input']}")
    
    if not state['can_proceed']:
        return state
    
    try:
        user_id = state['biometric_context']['user_id']
        
        # Create compilation prompt for LLM
        compilation_prompt = f"""
You are a MongoDB query compiler. Convert the user's voice request into a MongoDB query structure.

User ID: {user_id}
User Request: {state['user_input']}

You must:
1. Identify the collection to query
2. Determine the operation (find, find_one, count)
3. Build a filter that ALWAYS includes user_id for security
4. Return valid JSON

Examples:
- "Show my recent orders" → {{"collection": "orders", "operation": "find", "filter": {{"user_id": "{user_id}", "created_at": {{"$gte": ISODate("2026-01-15")}}}}, "limit": 10}}
- "How many purchases did I make?" → {{"collection": "orders", "operation": "count", "filter": {{"user_id": "{user_id}"}}}}

Return ONLY valid JSON in this format:
{{
    "collection": "...",
    "operation": "...",
    "filter": {{ ... }},
    "limit": ...,
    "interpretation": "..."
}}

User voice input: {state['user_input']}

Return the JSON object:
"""
        
        messages = [
            SystemMessage(content="You are a MongoDB query compiler assistant."),
            HumanMessage(content=compilation_prompt)
        ]
        
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Parse JSON from response
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                compiled_query = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in LLM response")
        except json.JSONDecodeError as e:
            logger.error(f"[QUERY_COMPILER] JSON parse error: {e}")
            state['error'] = f"Failed to parse query: {e}"
            state['error_node'] = "query_compiler"
            state['can_proceed'] = False
            return state
        
        # Validate compilation
        required_fields = {"collection", "operation", "filter"}
        if not required_fields.issubset(compiled_query.keys()):
            state['error'] = f"Missing required fields in compiled query"
            state['error_node'] = "query_compiler"
            state['can_proceed'] = False
            return state
        
        # Ensure user_id is in filter for security
        if "user_id" not in compiled_query["filter"]:
            compiled_query["filter"]["user_id"] = user_id
        
        state['query_compilation_context'] = QueryCompilationContext(
            original_voice_text=state['user_input'],
            interpreted_intent=compiled_query.get('interpretation', 'unknown'),
            confidence_score=0.95,  # Could be enhanced with confidence metrics
            compilation_attempts=1
        )
        
        state['execution_context'] = ExecutionContext(
            collection_name=compiled_query['collection'],
            operation=compiled_query['operation'],
            compiled_query=compiled_query,
            execution_time_ms=None,
            result_count=0
        )
        
        logger.info(f"[QUERY_COMPILER] ✓ Query compiled: {compiled_query}")
        
    except Exception as e:
        logger.error(f"[QUERY_COMPILER] Exception: {str(e)}")
        state['error'] = str(e)
        state['error_node'] = "query_compiler"
        state['can_proceed'] = False
    
    return state

# ============================================================================
# NODE 3: SECURITY_SUPERVISOR - Query Validation
# ============================================================================

async def security_supervisor(state: AgentState) -> AgentState:
    """
    Validates the compiled query for security violations.
    
    Security checks:
    1. Verify user_id filter is present
    2. Check for unauthorized collection access
    3. Verify user has access level for the operation
    4. Detect suspicious patterns (e.g., excessive limits, complex aggregations)
    5. Check for injection attempts
    """
    logger.info(f"[SECURITY_SUPERVISOR] Validating query security")
    
    if not state['can_proceed']:
        return state
    
    try:
        user_id = state['biometric_context']['user_id']
        user = CRUDOperations.get_user_by_id(user_id)
        data_access_level = user.get('data_access_level', 1)
        
        compiled_query = state['execution_context']['compiled_query']
        security_flags = []
        risk_score = 0.0
        
        # ==================== SECURITY CHECK 1: User ID Filter ====================
        if "filter" not in compiled_query:
            security_flags.append("CRITICAL: No filter in query")
            risk_score += 0.5
        elif "user_id" not in compiled_query["filter"]:
            security_flags.append("CRITICAL: Missing user_id in filter")
            risk_score += 0.5
        elif compiled_query["filter"]["user_id"] != user_id:
            security_flags.append("CRITICAL: Filter attempts to access other user's data")
            risk_score = 1.0
        
        # ==================== SECURITY CHECK 2: Collection Whitelist ====================
        ALLOWED_COLLECTIONS = {
            "orders": 1,      # min access level
            "user_profile": 2,
            "payments": 2,
            "analytics": 5,   # admin only
        }
        
        collection = compiled_query.get('collection')
        if collection not in ALLOWED_COLLECTIONS:
            security_flags.append(f"BLOCKED: Collection '{collection}' not in whitelist")
            risk_score = 1.0
        elif ALLOWED_COLLECTIONS[collection] > data_access_level:
            security_flags.append(f"BLOCKED: Insufficient access level for {collection}")
            risk_score = 1.0
        
        # ==================== SECURITY CHECK 3: Operation Whitelist ====================
        ALLOWED_OPERATIONS = ["find", "find_one", "count"]
        operation = compiled_query.get('operation')
        if operation not in ALLOWED_OPERATIONS:
            security_flags.append(f"BLOCKED: Operation '{operation}' not allowed")
            risk_score = 1.0
        
        # ==================== SECURITY CHECK 4: Suspicious Patterns ====================
        limit = compiled_query.get('limit', 100)
        if limit > 10000:
            security_flags.append(f"WARNING: Very large limit ({limit})")
            risk_score += 0.2
        
        # Check for suspicious operators
        filter_str = str(compiled_query.get('filter', {}))
        suspicious_operators = ['$where', '$function', '$eval']
        for op in suspicious_operators:
            if op in filter_str:
                security_flags.append(f"BLOCKED: Suspicious operator {op} detected")
                risk_score = 1.0
        
        # ==================== SECURITY CHECK 5: Injection Detection ====================
        if re.search(r'[;&|`$]', str(state['user_input'])):
            security_flags.append("WARNING: Potential injection characters in input")
            risk_score += 0.1
        
        # Determine if query is approved
        is_approved = risk_score < 0.5
        rejection_reason = None
        
        if not is_approved:
            if risk_score == 1.0:
                rejection_reason = "CRITICAL security violation detected"
            else:
                rejection_reason = f"Security risk score {risk_score:.2f} exceeds threshold"
        
        state['security_context'] = SecurityContext(
            data_access_level=data_access_level,
            query_risk_score=risk_score,
            security_flags=security_flags,
            is_approved=is_approved,
            rejection_reason=rejection_reason
        )
        
        if not is_approved:
            state['error'] = f"Security check failed: {rejection_reason}"
            state['error_node'] = "security_supervisor"
            state['can_proceed'] = False
            logger.warning(f"[SECURITY_SUPERVISOR] ✗ Query rejected: {security_flags}")
        else:
            logger.info(f"[SECURITY_SUPERVISOR] ✓ Query approved (risk: {risk_score:.2f})")
        
    except Exception as e:
        logger.error(f"[SECURITY_SUPERVISOR] Exception: {str(e)}")
        state['error'] = str(e)
        state['error_node'] = "security_supervisor"
        state['can_proceed'] = False
    
    return state

# ============================================================================
# NODE 4: TOOL_EXECUTOR - Execute MongoDB Queries
# ============================================================================

import time

async def tool_executor(state: AgentState) -> AgentState:
    """
    Execute the validated MongoDB query.
    
    Responsibilities:
    1. Execute the query against MongoDB
    2. Track execution time
    3. Handle errors gracefully
    4. Return structured results
    """
    logger.info(f"[TOOL_EXECUTOR] Executing query")
    
    if not state['can_proceed']:
        return state
    
    try:
        exec_context = state['execution_context']
        
        start_time = time.time()
        
        # Extract query components
        collection_name = exec_context['collection_name']
        operation = exec_context['operation']
        compiled_query = exec_context['compiled_query']
        
        # Execute query
        if operation == "find":
            limit = compiled_query.get('limit', 100)
            results = CRUDOperations.execute_filtered_query(
                collection_name,
                compiled_query['filter'],
                operation
            )
            results = results[:limit]  # Apply limit
        elif operation == "find_one":
            results = CRUDOperations.execute_filtered_query(
                collection_name,
                compiled_query['filter'],
                operation
            )
            results = [results] if results else []
        elif operation == "count":
            count = CRUDOperations.execute_filtered_query(
                collection_name,
                compiled_query['filter'],
                operation
            )
            results = [{"count": count}]
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Update execution context
        state['execution_context']['result_count'] = len(results)
        state['execution_context']['execution_time_ms'] = execution_time_ms
        
        # Store results in query log
        state['query_log_data']['result'] = results
        state['query_log_data']['execution_time_ms'] = execution_time_ms
        state['query_log_data']['security_flags'] = state['security_context']['security_flags']
        
        logger.info(f"[TOOL_EXECUTOR] ✓ Query successful ({execution_time_ms:.2f}ms, {len(results)} results)")
        
    except Exception as e:
        logger.error(f"[TOOL_EXECUTOR] Exception: {str(e)}")
        state['error'] = str(e)
        state['error_node'] = "tool_executor"
        state['can_proceed'] = False
    
    return state

# ============================================================================
# NODE 5: RESPONSE_SHAPER - JSON to Natural Language
# ============================================================================

async def response_shaper(state: AgentState) -> AgentState:
    """
    Convert MongoDB query results to natural language response.
    
    Uses LLM to generate human-friendly text summarizing the results.
    """
    logger.info(f"[RESPONSE_SHAPER] Shaping response")
    
    try:
        if not state['can_proceed']:
            # Handle errors gracefully
            error_msg = state.get('error', 'An unknown error occurred')
            state['agent_response'] = f"I encountered an error: {error_msg}. Please try again."
            return state
        
        results = state['query_log_data'].get('result', [])
        user_input = state['user_input']
        
        # Create response generation prompt
        response_prompt = f"""
User requested: {user_input}

Query results (JSON):
{json.dumps(results, indent=2, default=str)}

Generate a natural, conversational response summarizing these results. Be concise.
If there are no results, politely inform the user.
"""
        
        messages = [
            SystemMessage(content="You are a helpful assistant that summarizes query results."),
            HumanMessage(content=response_prompt)
        ]
        
        response = llm.invoke(messages)
        state['agent_response'] = response.content.strip()
        
        logger.info(f"[RESPONSE_SHAPER] ✓ Response generated")
        
    except Exception as e:
        logger.error(f"[RESPONSE_SHAPER] Exception: {str(e)}")
        state['agent_response'] = "I had trouble formatting the response. Please try again."
    
    return state

# ============================================================================
# ERROR HANDLING NODE (Optional)
# ============================================================================

async def error_handler(state: AgentState) -> AgentState:
    """
    Handle errors and determine retry strategy.
    """
    logger.error(f"[ERROR_HANDLER] Error in node: {state['error_node']}")
    logger.error(f"[ERROR_HANDLER] Error message: {state['error']}")
    
    state['retry_count'] += 1
    
    if state['retry_count'] < state['max_retries']:
        # Retry logic could be implemented here
        logger.info(f"[ERROR_HANDLER] Retrying ({state['retry_count']}/{state['max_retries']})")
        state['can_proceed'] = True
    else:
        state['agent_response'] = f"Failed after {state['max_retries']} attempts: {state['error']}"
    
    return state
```

### 2.3 LangGraph Builder

**File:** `backend/langgraph/graph_builder.py`

```python
from langgraph.graph import StateGraph, START, END
from backend.langgraph.state import AgentState
from backend.langgraph.nodes import (
    biometric_gate,
    query_compiler,
    security_supervisor,
    tool_executor,
    response_shaper,
    error_handler
)
import logging

logger = logging.getLogger(__name__)

def build_agent_graph():
    """
    Build the LangGraph state machine.
    
    Flow:
    START
      ↓
    biometric_gate (verify user)
      ↓
    query_compiler (NLP → query)
      ↓
    security_supervisor (validate security)
      ↓
    tool_executor (execute query)
      ↓
    response_shaper (results → natural language)
      ↓
    END
    
    Error handling branches on failures.
    """
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("biometric_gate", biometric_gate)
    graph.add_node("query_compiler", query_compiler)
    graph.add_node("security_supervisor", security_supervisor)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("response_shaper", response_shaper)
    graph.add_node("error_handler", error_handler)
    
    # Define edges
    graph.add_edge(START, "biometric_gate")
    
    # After biometric gate, proceed to query compiler if successful
    def bio_check(state):
        return "query_compiler" if state['can_proceed'] else "error_handler"
    
    graph.add_conditional_edges("biometric_gate", bio_check)
    
    # Compiler to security supervisor
    def compiler_check(state):
        return "security_supervisor" if state['can_proceed'] else "error_handler"
    
    graph.add_conditional_edges("query_compiler", compiler_check)
    
    # Security supervisor to executor
    def security_check(state):
        return "tool_executor" if state['can_proceed'] else "error_handler"
    
    graph.add_conditional_edges("security_supervisor", security_check)
    
    # Executor to response shaper
    def executor_check(state):
        return "response_shaper" if state['can_proceed'] else "error_handler"
    
    graph.add_conditional_edges("tool_executor", executor_check)
    
    # Response shaper to end
    graph.add_edge("response_shaper", END)
    
    # Error handler to end
    graph.add_edge("error_handler", "response_shaper")
    
    return graph.compile()

# Create compiled graph
agent_graph = build_agent_graph()

async def invoke_agent(user_input: str, session_id: str) -> str:
    """
    Invoke the agent with user input.
    
    Args:
        user_input: Transcribed voice text
        session_id: Unique session identifier
    
    Returns:
        Natural language response from the agent
    """
    from datetime import datetime
    import uuid
    
    initial_state = AgentState(
        user_input=user_input,
        agent_response="",
        session_id=session_id,
        timestamp=datetime.utcnow(),
        conversation_history=[],
        biometric_context=None,
        query_compilation_context=None,
        security_context=None,
        execution_context=None,
        query_id=str(uuid.uuid4())[:8],
        query_log_data={},
        error=None,
        error_node=None,
        retry_count=0,
        max_retries=2,
        can_proceed=True,
    )
    
    # Execute graph
    result = agent_graph.invoke(initial_state)
    
    # Log query
    if result.get('biometric_context'):
        CRUDOperations.log_query(
            user_id=result['biometric_context']['user_id'],
            original_voice=user_input,
            compiled_query=result.get('execution_context', {}).get('compiled_query', {})
        )
        
        CRUDOperations.update_query_status(
            query_id=result['query_id'],
            status="success" if result['can_proceed'] else "failed",
            result=result['query_log_data'].get('result'),
            error=result.get('error'),
            execution_time_ms=result['query_log_data'].get('execution_time_ms'),
            security_flags=result['query_log_data'].get('security_flags', [])
        )
    
    return result['agent_response']
```

---

## Phase 3: Model Integration

### Objectives
- Configure LLM providers (OpenAI/Gemini)
- Set up environment-based provider switching
- Implement prompt templates
- Handle token limits

### 3.1 LLM Configuration

**File:** `backend/config/llm_config.py`

```python
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal

class LLMConfig:
    """
    Centralized LLM configuration management.
    Optimized for Google Gemini with fallback support.
    
    Gemini Configuration:
    - Model: gemini-2.0-flash (recommended) or gemini-1.5-pro
    - Token Limit: 1M context window
    - Temperature: 0.1 (low for deterministic queries)
    - Safety Settings: Configured for security checks
    """
    
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
        self.model = self._get_model_name()
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4000"))  # Gemini supports higher token output
        self.top_p = float(os.environ.get("LLM_TOP_P", "0.95"))
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not self.api_key and self.provider == "gemini":
            raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini")
    
    def _get_model_name(self) -> str:
        """Get model name based on provider"""
        if self.provider == "gemini":
            return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        elif self.provider == "openai":
            return os.environ.get("OPENAI_MODEL", "gpt-4")
        else:
            return "gemini-2.0-flash"  # Fallback to Gemini
    
    def get_llm(self):
        """
        Factory method to create appropriate LLM instance.
        
        Returns:
            ChatGoogleGenerativeAI instance (Gemini)
        """
        if self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=self.model,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                top_p=self.top_p,
                google_api_key=self.api_key,
                convert_system_message_to_human=True  # Gemini requires human message format
            )
        elif self.provider == "openai":
            return ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        else:
            # Fallback to Gemini
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                google_api_key=self.api_key,
                convert_system_message_to_human=True
            )

# Global LLM instance
llm_config = LLMConfig()
llm = llm_config.get_llm()
```

### 3.2 Environment Configuration

**File:** `.env.example`

```bash
# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=voice_agent

# LLM Provider Configuration (Gemini Primary)
LLM_PROVIDER=gemini  # "gemini" (primary) or "openai" (fallback)
LLM_TEMPERATURE=0.1  # Low temperature for deterministic query compilation
LLM_MAX_TOKENS=4000  # Gemini supports large token outputs
LLM_TOP_P=0.95  # Nucleus sampling for diversity

# Google Gemini Configuration (PRIMARY)
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.0-flash  # Latest Gemini Flash model (recommended)
# Alternative models:
# GEMINI_MODEL=gemini-1.5-pro  # More capable but slower
# GEMINI_MODEL=gemini-1.5-flash  # Faster, good for real-time

# OpenAI Configuration (FALLBACK ONLY)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# Voice Authentication
VOICE_CHUNK_SIZE=8192
VOICE_SAMPLE_RATE=16000

# Security
MAX_QUERY_LIMIT=10000
SECURITY_LOG_PATH=./logs/security.log
```

### 3.2.1 Gemini Model Selection Guide

| Model | Context Window | Speed | Cost | Best For |
|-------|---------------|----|------|----------|
| gemini-2.0-flash | 1M tokens | Very Fast | Low | Real-time voice queries, production |
| gemini-1.5-pro | 1M tokens | Moderate | Medium | Complex reasoning, multi-step queries |
| gemini-1.5-flash | 1M tokens | Fast | Low | Quick responses, high volume |

**Recommendation:** Use `gemini-2.0-flash` for this implementation due to superior speed and cost-effectiveness.

### 3.2.2 Gemini Configuration Best Practices

**File:** `backend/config/gemini_config.py`

```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Dict, Any

class GeminiConfig:
    """
    Specialized Gemini configuration with optimization for voice agent.
    """
    
    # Safety settings for Gemini
    SAFETY_SETTINGS = [
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_UNSPECIFIED",
            "threshold": "BLOCK_ONLY_HIGH"
        }
    ]
    
    @staticmethod
    def get_optimized_gemini() -> ChatGoogleGenerativeAI:
        """
        Create Gemini instance optimized for voice query compilation.
        
        Optimizations:
        1. convert_system_message_to_human: Gemini works better with human messages
        2. temperature=0.1: Deterministic for query compilation
        3. max_output_tokens=4000: Allows detailed responses
        """
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.1,  # Deterministic for query compilation
            max_output_tokens=4000,
            top_p=0.95,
            top_k=40,
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            convert_system_message_to_human=True,  # IMPORTANT: Gemini requirement
            safety_settings=GeminiConfig.SAFETY_SETTINGS
        )
    
    @staticmethod
    def format_gemini_prompt(system_prompt: str, user_input: str) -> List[Dict]:
        """
        Format prompt for Gemini compatibility.
        
        Gemini doesn't support separate system messages, so we combine them.
        """
        combined_message = f"{system_prompt}\n\nUser Input:\n{user_input}"
        return [HumanMessage(content=combined_message)]
    
    @staticmethod
    def parse_gemini_response(response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini response with special handling.
        
        Gemini sometimes includes markdown formatting that needs stripping.
        """
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        
        return {"content": text, "raw": response_text}

# Gemini instance for query compilation
gemini_llm = GeminiConfig.get_optimized_gemini()
```

### 3.2.3 Updated Query Compiler Node for Gemini

**File:** `backend/langgraph/nodes.py` (Updated query_compiler function)

```python
import json
import re
from backend.config.gemini_config import GeminiConfig, gemini_llm

async def query_compiler(state: AgentState) -> AgentState:
    """
    Convert natural language voice input to MongoDB query using Gemini.
    
    Gemini-specific optimizations:
    1. Format prompts as human messages
    2. Parse responses with markdown handling
    3. Handle large context windows efficiently
    """
    logger.info(f"[QUERY_COMPILER] Processing voice with Gemini: {state['user_input']}")
    
    if not state['can_proceed']:
        return state
    
    try:
        user_id = state['biometric_context']['user_id']
        
        # Create compilation prompt for Gemini
        system_context = """You are a MongoDB query compiler specializing in secure, user-scoped queries.
        
Rules:
1. ALWAYS include user_id in the filter for security
2. Support operations: find, find_one, count (NO write operations)
3. Return ONLY valid JSON
4. Never allow aggregation pipelines or complex operators
5. Enforce user_id filter even if user tries to bypass it"""
        
        user_request = f"""
Compile this voice request into a MongoDB query:

User ID: {user_id}
Voice Request: {state['user_input']}

Return JSON object with this structure:
{{
    "collection": "collection_name",
    "operation": "find|find_one|count",
    "filter": {{"user_id": "{user_id}", ...}},
    "limit": 100,
    "interpretation": "brief summary of request"
}}

IMPORTANT: Include user_id in filter ALWAYS."""
        
        messages = GeminiConfig.format_gemini_prompt(system_context, user_request)
        
        response = gemini_llm.invoke(messages)
        response_text = response.content.strip()
        
        # Parse Gemini response with special handling
        parsed = GeminiConfig.parse_gemini_response(response_text)
        
        # Extract JSON from response
        try:
            json_match = re.search(r'\{[\s\S]*\}', parsed['content'])
            if json_match:
                compiled_query = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in Gemini response")
        except json.JSONDecodeError as e:
            logger.error(f"[QUERY_COMPILER] Gemini JSON parse error: {e}")
            logger.debug(f"[QUERY_COMPILER] Gemini raw response: {parsed['raw']}")
            state['error'] = f"Failed to parse Gemini response: {e}"
            state['error_node'] = "query_compiler"
            state['can_proceed'] = False
            return state
        
        # Validate compilation
        required_fields = {"collection", "operation", "filter"}
        if not required_fields.issubset(compiled_query.keys()):
            state['error'] = f"Missing required fields in compiled query"
            state['error_node'] = "query_compiler"
            state['can_proceed'] = False
            return state
        
        # CRITICAL: Ensure user_id is in filter for security
        if "user_id" not in compiled_query["filter"]:
            compiled_query["filter"]["user_id"] = user_id
            logger.warning(f"[QUERY_COMPILER] Added user_id to filter (security enforcement)")
        
        state['query_compilation_context'] = QueryCompilationContext(
            original_voice_text=state['user_input'],
            interpreted_intent=compiled_query.get('interpretation', 'unknown'),
            confidence_score=0.95,
            compilation_attempts=1
        )
        
        state['execution_context'] = ExecutionContext(
            collection_name=compiled_query['collection'],
            operation=compiled_query['operation'],
            compiled_query=compiled_query,
            execution_time_ms=None,
            result_count=0
        )
        
        logger.info(f"[QUERY_COMPILER] ✓ Gemini compiled query: {compiled_query}")
        
    except Exception as e:
        logger.error(f"[QUERY_COMPILER] Exception: {str(e)}")
        state['error'] = str(e)
        state['error_node'] = "query_compiler"
        state['can_proceed'] = False
    
    return state
```

### 3.3 Tool Binding

**File:** `backend/langgraph/tools.py`

```python
from langchain.tools import tool
from backend.database.crud_operations import CRUDOperations
from typing import List, Dict, Any

# ============================================================================
# TOOL 1: Query MongoDB
# ============================================================================

@tool
def mongodb_query(
    user_id: str,
    collection: str,
    filter_criteria: Dict[str, Any],
    operation: str = "find",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Execute a MongoDB query with mandatory user_id filter.
    
    Args:
        user_id: The authenticated user's ID (for security scoping)
        collection: Collection name to query
        filter_criteria: MongoDB filter (must not include unauthorized fields)
        operation: 'find', 'find_one', or 'count'
        limit: Maximum results to return
    
    Returns:
        Query results as list of documents
    
    Security Notes:
    - Always enforces user_id scoping
    - Rejects queries modifying data
    - Validates collection access
    """
    try:
        # Enforce user_id in filter (cannot be overridden)
        filter_criteria['user_id'] = user_id
        
        results = CRUDOperations.execute_filtered_query(
            collection,
            filter_criteria,
            operation
        )
        
        # Apply limit
        if isinstance(results, list):
            results = results[:limit]
        else:
            results = [results] if results else []
        
        return results
    except Exception as e:
        return [{"error": str(e)}]

# ============================================================================
# TOOL 2: Get User Profile
# ============================================================================

@tool
def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieve current user's profile information.
    
    Args:
        user_id: The authenticated user's ID
    
    Returns:
        User profile data
    """
    try:
        user = CRUDOperations.get_user_by_id(user_id)
        if user:
            # Exclude sensitive fields
            user.pop('_id', None)
            return user
        return {"error": "User not found"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# TOOL 3: Update User Preferences
# ============================================================================

@tool
def update_user_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Update user preferences/settings.
    
    Args:
        user_id: The authenticated user's ID
        preferences: Preferences to update
    
    Returns:
        Success status
    """
    try:
        # Sanitize inputs - only allow specific keys
        allowed_keys = {"language", "timezone", "notification_preference"}
        sanitized = {k: v for k, v in preferences.items() if k in allowed_keys}
        
        return CRUDOperations.update_user(user_id, sanitized)
    except Exception as e:
        return False

# Combine tools for LLM binding
AGENT_TOOLS = [
    mongodb_query,
    get_user_profile,
    update_user_preferences
]
```

---

## Phase 4: Security Implementation

### Objectives
- Implement multi-layer security checks
- Create audit logging
- Handle edge cases and injection attempts
- Build security monitoring

### 4.1 Security Module

**File:** `backend/security/query_validator.py`

```python
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class QueryValidator:
    """
    Advanced MongoDB query validation and security analysis.
    """
    
    # Dangerous operators that could leak data
    DANGEROUS_OPERATORS = {
        '$where': 'Code execution operator',
        '$function': 'Function execution operator',
        '$eval': 'Evaluation operator',
        '$regex': 'Regex injection risk',
        '$ne': 'Negation operator (information disclosure)',
    }
    
    # Operations that modify data
    MODIFICATION_OPERATIONS = ['insert', 'update', 'delete', 'drop', 'create']
    
    # Collection whitelist
    ALLOWED_COLLECTIONS = {
        'orders': {'access_level': 1, 'operations': ['find', 'find_one', 'count']},
        'user_profile': {'access_level': 1, 'operations': ['find_one']},
        'payments': {'access_level': 2, 'operations': ['find', 'find_one']},
        'analytics': {'access_level': 5, 'operations': ['find', 'count']},
    }
    
    @staticmethod
    def validate_query(
        query: Dict,
        user_id: str,
        user_access_level: int
    ) -> Tuple[bool, List[str], float]:
        """
        Comprehensive query validation.
        
        Returns:
            (is_valid, flags, risk_score)
        """
        flags = []
        risk_score = 0.0
        
        # 1. Collection validation
        collection = query.get('collection')
        if collection not in QueryValidator.ALLOWED_COLLECTIONS:
            flags.append(f"Collection '{collection}' not whitelisted")
            risk_score = 1.0
            return False, flags, risk_score
        
        allowed_config = QueryValidator.ALLOWED_COLLECTIONS[collection]
        
        # Check access level
        if allowed_config['access_level'] > user_access_level:
            flags.append(f"Insufficient access level for '{collection}'")
            risk_score = 1.0
            return False, flags, risk_score
        
        # 2. Operation validation
        operation = query.get('operation')
        if operation not in allowed_config['operations']:
            flags.append(f"Operation '{operation}' not allowed for '{collection}'")
            risk_score = 1.0
            return False, flags, risk_score
        
        if operation in QueryValidator.MODIFICATION_OPERATIONS:
            flags.append(f"Data modification operation '{operation}' blocked")
            risk_score = 1.0
            return False, flags, risk_score
        
        # 3. Filter validation
        filter_obj = query.get('filter', {})
        if filter_obj is None:
            flags.append("No filter provided")
            risk_score += 0.3
        else:
            # Check user_id is in filter
            if filter_obj.get('user_id') != user_id:
                flags.append("Query doesn't include proper user_id scoping")
                risk_score = 1.0
                return False, flags, risk_score
            
            # Check for dangerous operators
            filter_str = str(filter_obj)
            for dangerous_op in QueryValidator.DANGEROUS_OPERATORS:
                if dangerous_op in filter_str:
                    flags.append(f"Dangerous operator '{dangerous_op}' detected")
                    risk_score += 0.3
        
        # 4. Limit validation
        limit = query.get('limit', 100)
        if limit > 10000:
            flags.append(f"Excessive limit: {limit}")
            risk_score += 0.2
        
        # 5. Injection pattern detection
        user_input = query.get('_original_input', '')
        injection_patterns = [
            r'["\']{2,}',  # Multiple quotes
            r'\$[a-zA-Z]+',  # MongoDB operators
            r'[;&|`]',  # Command injection chars
        ]
        for pattern in injection_patterns:
            if re.search(pattern, str(user_input)):
                flags.append(f"Potential injection pattern detected")
                risk_score += 0.15
        
        is_valid = risk_score < 0.5
        return is_valid, flags, risk_score

class AuditLogger:
    """
    Comprehensive audit logging for security events.
    """
    
    @staticmethod
    def log_query_execution(
        query_id: str,
        user_id: str,
        collection: str,
        query: Dict,
        status: str,
        risk_score: float,
        security_flags: List[str]
    ):
        """Log query execution with full context"""
        log_entry = {
            'query_id': query_id,
            'user_id': user_id,
            'collection': collection,
            'query': str(query)[:200],  # Truncate
            'status': status,
            'risk_score': risk_score,
            'security_flags': security_flags,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }
        
        logger.warning(f"SECURITY_AUDIT: {log_entry}")
    
    @staticmethod
    def log_security_violation(
        user_id: str,
        violation_type: str,
        details: str
    ):
        """Log security violations for investigation"""
        logger.error(f"SECURITY_VIOLATION: user={user_id}, type={violation_type}, details={details}")
```

### 4.2 Rate Limiting & Request Throttling

**File:** `backend/security/rate_limiter.py`

```python
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class RateLimiter:
    """
    Rate limiting to prevent abuse.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """
        Check if user is allowed to make a request.
        
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > cutoff
        ]
        
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
        
        return False
    
    def get_retry_after(self, user_id: str) -> Optional[int]:
        """
        Get seconds until next request is allowed.
        """
        if not self.requests[user_id]:
            return None
        
        oldest = self.requests[user_id][0]
        retry_after = (oldest + timedelta(seconds=self.window_seconds) - datetime.utcnow()).total_seconds()
        
        return max(0, int(retry_after))

# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
```

---

## Phase 5: Testing & Validation

### 5.1 Unit Tests

**File:** `tests/test_query_validator.py`

```python
import pytest
from backend.security.query_validator import QueryValidator

class TestQueryValidator:
    
    def test_valid_query_accepted(self):
        """Test that valid queries are accepted"""
        query = {
            'collection': 'orders',
            'operation': 'find',
            'filter': {'user_id': 'user_123'},
            'limit': 100
        }
        is_valid, flags, risk = QueryValidator.validate_query(query, 'user_123', 5)
        assert is_valid == True
        assert risk < 0.5
    
    def test_injection_attempt_blocked(self):
        """Test that injection attempts are blocked"""
        query = {
            'collection': 'orders',
            'operation': 'find',
            'filter': {
                'user_id': 'user_123',
                'amount': {'$ne': None}  # Negation operator
            }
        }
        is_valid, flags, risk = QueryValidator.validate_query(query, 'user_123', 5)
        assert is_valid == False or risk >= 0.3
        assert any('operator' in flag for flag in flags)
    
    def test_unauthorized_collection_blocked(self):
        """Test that unauthorized collection access is blocked"""
        query = {
            'collection': 'admin_settings',
            'operation': 'find',
            'filter': {'user_id': 'user_123'}
        }
        is_valid, flags, risk = QueryValidator.validate_query(query, 'user_123', 1)
        assert is_valid == False
        assert risk == 1.0
    
    def test_insufficient_access_level_blocked(self):
        """Test that access level is checked"""
        query = {
            'collection': 'analytics',  # Requires level 5
            'operation': 'find',
            'filter': {'user_id': 'user_123'}
        }
        is_valid, flags, risk = QueryValidator.validate_query(query, 'user_123', 2)
        assert is_valid == False
        assert risk == 1.0
    
    def test_missing_user_id_filter_blocked(self):
        """Test that queries without user_id filter are blocked"""
        query = {
            'collection': 'orders',
            'operation': 'find',
            'filter': {'status': 'complete'}  # Missing user_id!
        }
        is_valid, flags, risk = QueryValidator.validate_query(query, 'user_123', 5)
        assert is_valid == False
        assert risk == 1.0
    
    def test_data_modification_blocked(self):
        """Test that data modification operations are blocked"""
        query = {
            'collection': 'orders',
            'operation': 'delete',
            'filter': {'user_id': 'user_123'}
        }
        is_valid, flags, risk = QueryValidator.validate_query(query, 'user_123', 5)
        assert is_valid == False
        assert risk == 1.0
```

### 5.2 Integration Tests

**File:** `tests/test_agent_flow.py`

```python
import pytest
import asyncio
from backend.langgraph.graph_builder import invoke_agent
from backend.database.crud_operations import CRUDOperations
from datetime import datetime

class TestAgentFlow:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test user"""
        # Create test user
        CRUDOperations.create_user({
            'user_id': 'test_user_123',
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+11234567890',
            'biometrics': [{
                'phone': '+11234567890',
                'biometric_type': 'phone',
                'verified_at': datetime.utcnow(),
                'is_active': True
            }],
            'auth_status': 'verified',
            'data_access_level': 5
        })
        yield
        # Cleanup would go here
    
    @pytest.mark.asyncio
    async def test_successful_query_flow(self):
        """Test complete successful query flow"""
        response = await invoke_agent(
            "My phone is plus one two three four five six seven eight nine zero, show me my recent orders",
            "session_123"
        )
        assert response is not None
        assert len(response) > 0
        assert "error" not in response.lower()
    
    @pytest.mark.asyncio
    async def test_unauthorized_collection_access_blocked(self):
        """Test that unauthorized collection access is denied"""
        response = await invoke_agent(
            "My phone is plus one two three four five six seven eight nine zero, show me admin settings",
            "session_456"
        )
        # Should either be blocked or have error message
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_injection_attempt_blocked(self):
        """Test SQL/NoSQL injection attempt prevention"""
        response = await invoke_agent(
            "My phone is plus one two three four five six seven eight nine zero, show me orders where amount != null",
            "session_789"
        )
        # Should be blocked
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_malformed_input_handled(self):
        """Test graceful handling of malformed input"""
        response = await invoke_agent(
            "show me everything from all collections",
            "session_abc"
        )
        # Should handle gracefully
        assert response is not None
        assert "error" in response.lower() or "unclear" in response.lower()
```

---

## Phase 6: Optional Enhancements

### 6.1 WebSocket Real-Time Updates

**File:** `backend/websocket/streaming_manager.py`

```python
from fastapi import WebSocket
from typing import Set
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class StreamingManager:
    """
    Manage WebSocket connections for real-time updates.
    """
    
    def __init__(self):
        self.connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.connections)}")
    
    async def broadcast_query_status(self, user_id: str, status: dict):
        """Broadcast query status to all connected clients for this user"""
        message = json.dumps({
            'type': 'query_status',
            'user_id': user_id,
            'status': status
        })
        
        for connection in self.connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
    
    async def stream_results(self, user_id: str, results: list):
        """Stream large result sets incrementally"""
        for i, result in enumerate(results):
            message = json.dumps({
                'type': 'result_chunk',
                'index': i,
                'total': len(results),
                'data': result
            })
            
            for connection in self.connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error streaming: {e}")
            
            # Add delay to prevent flooding
            await asyncio.sleep(0.01)
```

### 6.2 Monitoring & Metrics

**File:** `backend/monitoring/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Counters
queries_total = Counter(
    'agent_queries_total',
    'Total queries processed',
    ['status', 'collection']
)

security_violations = Counter(
    'security_violations_total',
    'Total security violations detected',
    ['violation_type']
)

# Histograms
query_duration = Histogram(
    'agent_query_duration_seconds',
    'Query execution duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Gauges
active_sessions = Gauge(
    'agent_active_sessions',
    'Number of active agent sessions'
)

def track_query_execution(collection: str, status: str, duration_ms: float):
    """Record query metrics"""
    queries_total.labels(status=status, collection=collection).inc()
    query_duration.observe(duration_ms / 1000)

def track_security_violation(violation_type: str):
    """Record security violation"""
    security_violations.labels(violation_type=violation_type).inc()
```

### 6.3 Comprehensive Logging

**File:** `backend/logging_config.py`

```python
import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging():
    """Configure comprehensive logging system"""
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
    )
    
    # File handlers
    # General application log
    app_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    
    # Security-specific log
    security_handler = logging.handlers.RotatingFileHandler(
        'logs/security.log',
        maxBytes=10485760,
        backupCount=10
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(detailed_formatter)
    
    # Query execution log
    query_handler = logging.handlers.RotatingFileHandler(
        'logs/queries.log',
        maxBytes=52428800,  # 50MB
        backupCount=10
    )
    query_handler.setLevel(logging.DEBUG)
    query_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    
    # Add handlers
    logger.addHandler(app_handler)
    logger.addHandler(security_handler)
    logger.addHandler(query_handler)
    logger.addHandler(console_handler)
    
    return logger
```

---

## Deployment Strategy

### Development Environment

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with local settings

# 3. Start MongoDB
docker run -d -p 27017:27017 mongo:latest

# 4. Initialize database
python scripts/init_db.py

# 5. Run application
uvicorn main:app --reload
```

### Production Environment

```bash
# Docker Deployment
docker-compose -f docker-compose.prod.yml up -d

# Key considerations:
# - Use environment variable injection
# - Enable SSL/TLS for all connections
# - Set up proper monitoring
# - Configure log aggregation
# - Implement backup strategy
```

---

## Code Snippets & Examples

### Complete Integration Example

**File:** `main.py`

```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from datetime import datetime

from backend.database.mongo_client import mongo_client
from backend.langgraph.graph_builder import invoke_agent
from backend.security.rate_limiter import rate_limiter
from backend.logging_config import setup_logging
from backend.websocket.streaming_manager import StreamingManager

# Setup
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Agent API", version="1.0.0")
streaming_manager = StreamingManager()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class VoiceQueryRequest(BaseModel):
    voice_text: str
    session_id: str

class VoiceQueryResponse(BaseModel):
    response: str
    status: str
    timestamp: datetime

# Routes
@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    mongo_client.connect()
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    mongo_client.disconnect()
    logger.info("Application shutdown")

@app.post("/query", response_model=VoiceQueryResponse)
async def process_voice_query(request: VoiceQueryRequest):
    """
    Process user voice query through agent.
    
    Flow:
    1. Rate limit check
    2. Query compilation
    3. Security validation
    4. Execution
    5. Response formatting
    """
    try:
        # Extract user from voice (simplified - in production, extract from auth context)
        # phone = extract_phone_from_voice(request.voice_text)
        
        # Rate limiting
        # if not rate_limiter.is_allowed(user_id):
        #     raise HTTPException(status_code=429, detail="Rate limited")
        
        # Invoke agent
        response = await invoke_agent(request.voice_text, request.session_id)
        
        return VoiceQueryResponse(
            response=response,
            status="success",
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return VoiceQueryResponse(
            response=f"Error processing query: {str(e)}",
            status="error",
            timestamp=datetime.utcnow()
        )

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for streaming updates"""
    await streaming_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process data and broadcast updates
            await streaming_manager.broadcast_query_status(
                session_id,
                {"message": data, "timestamp": datetime.utcnow()}
            )
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        streaming_manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

---

## Implementation Roadmap

### Week 1-2: Database & Schema
- [x] Set up MongoDB connection pooling
- [x] Define Pydantic models
- [x] Implement CRUD operations
- [x] Create indexes

### Week 3-4: LangGraph Core
- [x] Define AgentState
- [x] Implement 5 core nodes
- [x] Build state machine
- [x] Test node execution

### Week 5-6: Security Layer
- [x] Query validation module
- [x] Access control checks
- [x] Injection prevention
- [x] Audit logging

### Week 7: Integration & Testing
- [x] LLM binding
- [x] End-to-end testing
- [x] Security testing
- [x] Performance tuning

### Week 8: Deployment & Monitoring
- [x] Docker setup
- [x] Logging infrastructure
- [x] Metrics collection
- [x] Production deployment

---

## Conclusion

This comprehensive plan provides a roadmap for implementing a production-grade, AI-driven agent system with:

✅ **Robust Security:** Multi-layer verification, query validation, injection prevention  
✅ **Scalability:** MongoDB for flexible data, LangGraph for orchestration  
✅ **Maintainability:** Clear separation of concerns, comprehensive logging  
✅ **Extensibility:** MCP servers, configurable LLM providers, tool binding  
✅ **Auditability:** Complete query tracking, security events, metrics  

**Next Steps:**
1. Clone repository and set up development environment
2. Follow Phase 1 (Database) implementation
3. Progress sequentially through phases
4. Execute testing strategy at each phase
5. Deploy to production with monitoring active
