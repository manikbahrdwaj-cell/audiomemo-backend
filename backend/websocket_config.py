"""
WebSocket Configuration Module
Centralized configuration for WebSocket settings
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

# Environment variables
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", 30))  # seconds
WS_HEARTBEAT_TIMEOUT = int(os.getenv("WS_HEARTBEAT_TIMEOUT", 60))  # seconds
WS_MAX_MESSAGE_SIZE = int(os.getenv("WS_MAX_MESSAGE_SIZE", 1024 * 1024))  # 1MB bytes
WS_MAX_BUFFER_SIZE = int(os.getenv("WS_MAX_BUFFER_SIZE", 10_000_000))  # 10MB bytes


@dataclass
class WebSocketConfig:
    """WebSocket configuration settings"""
    
    # Connection settings
    heartbeat_interval: int = WS_HEARTBEAT_INTERVAL
    heartbeat_timeout: int = WS_HEARTBEAT_TIMEOUT
    max_message_size: int = WS_MAX_MESSAGE_SIZE
    max_buffer_size: int = WS_MAX_BUFFER_SIZE
    
    # Audio processing settings
    min_audio_size: int = 1000  # bytes
    similarity_threshold: float = 0.75
    
    # Connection limits
    max_concurrent_connections: int = 100
    max_connections_per_ip: int = 5
    
    # Timeout settings (in seconds)
    connection_timeout: int = 300  # 5 minutes
    idle_timeout: int = 600  # 10 minutes
    
    # Feature flags
    enable_compression: bool = False
    enable_keepalive: bool = True
    enable_rate_limiting: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "heartbeat_interval": self.heartbeat_interval,
            "heartbeat_timeout": self.heartbeat_timeout,
            "max_message_size": self.max_message_size,
            "max_buffer_size": self.max_buffer_size,
            "min_audio_size": self.min_audio_size,
            "similarity_threshold": self.similarity_threshold,
            "max_concurrent_connections": self.max_concurrent_connections,
            "max_connections_per_ip": self.max_connections_per_ip,
            "connection_timeout": self.connection_timeout,
            "idle_timeout": self.idle_timeout,
        }


# Global configuration instance
config = WebSocketConfig()


class MessageTypeRegistry:
    """Registry for supported WebSocket message types"""
    
    MESSAGE_TYPES = {
        # Audio processing
        "audio": {
            "description": "Send audio chunk",
            "requires": ["data"],
            "optional": []
        },
        # Verification
        "verify": {
            "description": "Verify voice against enrolled identity",
            "requires": ["phone_number"],
            "optional": []
        },
        # Enrollment
        "enroll": {
            "description": "Enroll new voice identity",
            "requires": ["phone_number"],
            "optional": []
        },
        # Keep-alive
        "ping": {
            "description": "Keep-alive ping message",
            "requires": [],
            "optional": []
        },
        # Control
        "reset": {
            "description": "Reset audio buffer",
            "requires": [],
            "optional": []
        },
        "status": {
            "description": "Get connection status",
            "requires": [],
            "optional": []
        }
    }
    
    @staticmethod
    def get_message_type(msg_type: str) -> Dict[str, Any]:
        """Get message type definition"""
        return MessageTypeRegistry.MESSAGE_TYPES.get(msg_type, None)
    
    @staticmethod
    def is_valid(msg_type: str) -> bool:
        """Check if message type is valid"""
        return msg_type in MessageTypeRegistry.MESSAGE_TYPES
    
    @staticmethod
    def get_all() -> Dict[str, Dict[str, Any]]:
        """Get all message types"""
        return MessageTypeRegistry.MESSAGE_TYPES
    
    @staticmethod
    def get_required_fields(msg_type: str) -> list:
        """Get required fields for message type"""
        msg = MessageTypeRegistry.get_message_type(msg_type)
        return msg.get("requires", []) if msg else []


class ResponseTypeRegistry:
    """Registry for WebSocket response types"""
    
    RESPONSE_TYPES = {
        # Success responses
        "audio_received": "Audio chunk received and buffered",
        "verification_result": "Verification completed with results",
        "enrollment_success": "Voice enrollment completed",
        "pong": "Keep-alive response",
        "reset_acknowledged": "Audio buffer reset",
        "status": "Connection status information",
        
        # Error responses
        "error": "General error",
        "validation_error": "Message validation failed",
        "insufficient_audio": "Audio buffer too small",
        "not_enrolled": "Phone number not enrolled",
        "no_audio": "No audio data available",
        "decode_error": "Failed to decode data",
        "buffer_overflow": "Audio buffer exceeded maximum size",
        "enrollment_error": "Enrollment process failed",
        "verification_error": "Verification process failed"
    }
    
    @staticmethod
    def get_response_type(resp_type: str) -> str:
        """Get response type description"""
        return ResponseTypeRegistry.RESPONSE_TYPES.get(resp_type, "Unknown response")
    
    @staticmethod
    def get_all() -> Dict[str, str]:
        """Get all response types"""
        return ResponseTypeRegistry.RESPONSE_TYPES


# Message limits
MESSAGE_LIMITS = {
    "audio": 1024 * 50,  # 50KB per chunk
    "standard": 1024 * 10,  # 10KB for other messages
}
