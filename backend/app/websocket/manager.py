"""
WebSocket Handler Module
Manages WebSocket connections and provides utilities for real-time communication
"""

from fastapi import WebSocket
from typing import List, Callable, Optional, Dict, Any
import logging
import json
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Enum for connection states"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    IDLE = "idle"
    PROCESSING = "processing"


class ClientConnection:
    """Represents a single WebSocket client connection"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.state = ConnectionState.IDLE
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    async def send_json(self, message: Dict[str, Any]) -> bool:
        """Send a JSON message to the client"""
        try:
            await self.websocket.send_json(message)
            logger.debug(f"Message sent to {self.client_id}: {message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {str(e)}")
            return False
    
    async def send_text(self, text: str) -> bool:
        """Send a text message to the client"""
        try:
            await self.websocket.send_text(text)
            logger.debug(f"Text sent to {self.client_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send text to {self.client_id}: {str(e)}")
            return False
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.now()
    
    def set_state(self, state: ConnectionState):
        """Update connection state"""
        old_state = self.state
        self.state = state
        logger.debug(f"Client {self.client_id} state changed: {old_state.value} -> {state.value}")
    
    def set_metadata(self, key: str, value: Any):
        """Store metadata for the connection"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Retrieve metadata for the connection"""
        return self.metadata.get(key, default)


class ConnectionManager:
    """
    Manages multiple WebSocket connections
    Handles connection/disconnection and broadcast operations
    """
    
    def __init__(self):
        self.active_connections: Dict[str, ClientConnection] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> ClientConnection:
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        connection = ClientConnection(websocket, client_id)
        self.active_connections[client_id] = connection
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # Trigger connection callbacks
        await self._trigger_callbacks("on_connect", connection)
        
        return connection
    
    def disconnect(self, client_id: str):
        """Remove a disconnected WebSocket"""
        if client_id in self.active_connections:
            connection = self.active_connections.pop(client_id)
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
            
            # Trigger disconnection callbacks (async safe)
            # Note: Callbacks should handle their own async operations
    
    def get_connection(self, client_id: str) -> Optional[ClientConnection]:
        """Get a specific connection by ID"""
        return self.active_connections.get(client_id)
    
    def get_all_connections(self) -> List[ClientConnection]:
        """Get all active connections"""
        return list(self.active_connections.values())
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    async def broadcast(self, message: Dict[str, Any], exclude_client: Optional[str] = None):
        """Broadcast a message to all connected clients"""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            if exclude_client and client_id == exclude_client:
                continue
            
            success = await connection.send_json(message)
            if not success:
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_to_group(self, group_id: str, message: Dict[str, Any], 
                                 exclude_client: Optional[str] = None):
        """Broadcast a message to clients in a specific group"""
        for connection in self.active_connections.values():
            if connection.get_metadata("group") != group_id:
                continue
            
            if exclude_client and connection.client_id == exclude_client:
                continue
            
            await connection.send_json(message)
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for an event"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        logger.debug(f"Registered callback for event: {event}")
    
    async def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger all callbacks registered for an event"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    if hasattr(callback, "__await__"):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for {event}: {str(e)}")


class WebSocketMessageBuilder:
    """Helper class for building WebSocket messages"""
    
    @staticmethod
    def create_message(message_type: str, data: Optional[Dict[str, Any]] = None,
                      status: str = "ok", **kwargs) -> Dict[str, Any]:
        """Create a formatted WebSocket message"""
        message = {
            "type": message_type,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            message["data"] = data
        
        message.update(kwargs)
        return message
    
    @staticmethod
    def create_error_message(error_type: str, message: str) -> Dict[str, Any]:
        """Create an error message"""
        return {
            "type": "error",
            "error_type": error_type,
            "message": message,
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_success_message(message_type: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a success message"""
        return WebSocketMessageBuilder.create_message(
            message_type, 
            data=data, 
            status="ok"
        )
    
    @staticmethod
    def create_progress_message(current: int, total: int, message: str = "") -> Dict[str, Any]:
        """Create a progress message"""
        return {
            "type": "progress",
            "current": current,
            "total": total,
            "message": message,
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }


class WebSocketMessageValidator:
    """Validates incoming WebSocket messages"""
    
    REQUIRED_FIELDS = {
        "audio": ["data"],
        "verify": ["phone_number"],
        "enroll": ["phone_number"],
        "ping": [],
        "reset": [],
    }
    
    @staticmethod
    def validate(message_type: str, message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a WebSocket message
        
        Returns:
            (is_valid, error_message)
        """
        if message_type not in WebSocketMessageValidator.REQUIRED_FIELDS:
            return False, f"Unknown message type: {message_type}"
        
        required_fields = WebSocketMessageValidator.REQUIRED_FIELDS[message_type]
        
        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"
        
        return True, None
    
    @staticmethod
    def get_message_type(data: str) -> Optional[str]:
        """Extract message type from JSON string"""
        try:
            message = json.loads(data)
            return message.get("type")
        except json.JSONDecodeError:
            return None
