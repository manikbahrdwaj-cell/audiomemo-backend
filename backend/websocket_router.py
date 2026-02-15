"""
WebSocket Message Router Module
Centralized message routing and handler management
"""

import logging
from typing import Dict, Callable, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Enumeration of supported message types"""
    # Audio operations
    AUDIO = "audio"
    
    # Verification and enrollment
    VERIFY = "verify"
    VERIFY_CONFIRMED = "verify_confirmed"
    ENROLL = "enroll"
    ENROLLMENT_STATUS = "enrollment_status"
    ENROLLMENT_CONFIRMED = "enrollment_confirmed"
    
    # System control
    PING = "ping"
    RESET = "reset"
    STATUS = "status"
    
    # Configuration
    CONFIG = "config"
    
    # Error handling
    ERROR = "error"


@dataclass
class RouteConfig:
    """Configuration for a message route"""
    message_type: MessageType
    handler: Callable
    requires_auth: bool = False
    requires_fields: list = None
    optional_fields: list = None
    max_message_size: int = None
    rate_limit: Optional[int] = None  # Max messages per second, None = no limit
    
    def __post_init__(self):
        if self.requires_fields is None:
            self.requires_fields = []
        if self.optional_fields is None:
            self.optional_fields = []


class MessageValidator:
    """Validates messages against route configuration"""
    
    @staticmethod
    def validate_message(message: Dict[str, Any], route: RouteConfig) -> Tuple[bool, Optional[str]]:
        """
        Validate a message against route requirements
        
        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        for field in route.requires_fields:
            if field not in message:
                return False, f"Missing required field: {field}"
        
        # Check message size if configured
        if route.max_message_size:
            message_size = len(str(message))
            if message_size > route.max_message_size:
                return False, f"Message size exceeds limit: {message_size} > {route.max_message_size}"
        
        return True, None


class RateLimit:
    """Rate limiter for message types"""
    
    def __init__(self):
        self.connection_limits: Dict[str, Dict[str, Any]] = {}
    
    def check_limit(self, client_id: str, message_type: str, limit: int) -> Tuple[bool, str]:
        """
        Check if client has exceeded rate limit
        
        Returns:
            (is_allowed, message)
        """
        key = f"{client_id}:{message_type}"
        now = datetime.now()
        
        if key not in self.connection_limits:
            self.connection_limits[key] = {
                "count": 1,
                "window_start": now
            }
            return True, "OK"
        
        window_data = self.connection_limits[key]
        elapsed = (now - window_data["window_start"]).total_seconds()
        
        # Reset window if 1 second has passed
        if elapsed >= 1:
            window_data["count"] = 1
            window_data["window_start"] = now
            return True, "OK"
        
        # Check limit within current window
        if window_data["count"] >= limit:
            return False, f"Rate limit exceeded: {limit} messages per second"
        
        window_data["count"] += 1
        return True, "OK"
    
    def cleanup_old_limits(self):
        """Clean up old rate limit records (older than 1 minute)"""
        cutoff = datetime.now()
        cutoff_seconds = 60
        
        keys_to_delete = []
        for key, data in self.connection_limits.items():
            elapsed = (cutoff - data["window_start"]).total_seconds()
            if elapsed > cutoff_seconds:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.connection_limits[key]


class WebSocketMessageRouter:
    """
    Centralized message router for WebSocket messages
    Manages routes, validation, and handler dispatch
    """
    
    def __init__(self):
        self.routes: Dict[str, RouteConfig] = {}
        self.validator = MessageValidator()
        self.rate_limiter = RateLimit()
    
    def register_route(self, route_config: RouteConfig):
        """Register a message route"""
        route_key = route_config.message_type.value
        self.routes[route_key] = route_config
        logger.info(f"Registered route: {route_key}")
    
    def register_routes(self, routes: list[RouteConfig]):
        """Register multiple routes at once"""
        for route in routes:
            self.register_route(route)
    
    def get_route(self, message_type: str) -> Optional[RouteConfig]:
        """Get route configuration for a message type"""
        return self.routes.get(message_type)
    
    async def route_message(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a message to the appropriate handler
        
        Returns:
            Response message
        """
        try:
            message_type = message.get("type")
            
            # Validate message type
            if not message_type:
                return self._error_response("missing_type", "Message type is required")
            
            # Get route
            route = self.get_route(message_type)
            if not route:
                return self._error_response("unknown_type", f"Unknown message type: {message_type}")
            
            # Validate message
            is_valid, error_msg = self.validator.validate_message(message, route)
            if not is_valid:
                return self._error_response("validation_error", error_msg)
            
            # Check rate limit
            if route.rate_limit:
                is_allowed, limit_msg = self.rate_limiter.check_limit(
                    client_id, message_type, route.rate_limit
                )
                if not is_allowed:
                    return self._error_response("rate_limit", limit_msg)
            
            # Call handler
            logger.debug(f"Routing message {message_type} from {client_id}")
            response = await route.handler(message)
            
            # Add routing metadata
            if isinstance(response, dict):
                response["_routed_at"] = datetime.now().isoformat()
                response["_route"] = message_type
            
            return response
        
        except Exception as e:
            logger.error(f"Error routing message: {str(e)}", exc_info=True)
            return self._error_response("routing_error", f"Error processing message: {str(e)}")
    
    @staticmethod
    def _error_response(error_type: str, message: str) -> Dict[str, Any]:
        """Create an error response"""
        return {
            "type": "error",
            "status": "error",
            "error_type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_routes_info(self) -> Dict[str, Any]:
        """Get information about all registered routes"""
        routes_info = {}
        for key, route in self.routes.items():
            routes_info[key] = {
                "message_type": route.message_type.value,
                "requires_auth": route.requires_auth,
                "requires_fields": route.requires_fields,
                "optional_fields": route.optional_fields,
                "max_message_size": route.max_message_size,
                "rate_limit": route.rate_limit
            }
        return routes_info
    
    def cleanup(self):
        """Cleanup routine (e.g., rate limit records)"""
        self.rate_limiter.cleanup_old_limits()


# Global router instance
router = WebSocketMessageRouter()
