"""
WebSocket-based enrollment confirmation service.
"""


from typing import Optional, Dict, Any, List, Tuple
import logging
from app.services.enrollment_manager import get_enrollment_session

from datetime import datetime, timedelta
import uuid

class EnrollmentConfirmationService:
    """
    Service for managing enrollment confirmations via WebSocket
    Sends confirmation messages to clients when enrollment is completed
    """
    
    def __init__(self):
        """Initialize the confirmation service"""
        self.session_clients: Dict[str, str] = {}  # Maps session_id to client_id
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}  # Pending confirmations
        self.sent_confirmations: List[Dict[str, Any]] = []  # History of sent confirmations
        self.connection_manager = None  # Will be set by main.py
        logging.getLogger(__name__).info("Enrollment Confirmation Service initialized")
    
    def set_connection_manager(self, manager):
        """Set the WebSocket connection manager"""
        self.connection_manager = manager
        logging.getLogger(__name__).info("Connection manager set for confirmation service")
    
    def register_session_client(self, session_id: str, client_id: str) -> bool:
        """
        Register a client for an enrollment session
        When enrollment completes, confirmation will be sent to this client
        
        Args:
            session_id: The enrollment session ID
            client_id: The WebSocket client ID
        Returns:
            True if registered successfully
        """
        self.session_clients[session_id] = client_id
        logging.getLogger(__name__).info(f"Registered client {client_id} for session {session_id[:8]}")
        return True
    
    def unregister_session(self, session_id: str) -> bool:
        """Unregister a session (when it's cancelled)"""
        if session_id in self.session_clients:
            del self.session_clients[session_id]
            logging.getLogger(__name__).info(f"Unregistered session {session_id[:8]}")
            return True
        return False
    
    async def send_enrollment_confirmation(
        self, 
        session_id: str,
        phone_number: str,
        vector_id: str,
        chunks_processed: int,
        success: bool = True,
        message: str = ""
    ) -> Tuple[bool, str]:
        """
        Send enrollment confirmation to the client
        Args:
            session_id: Enrollment session ID
            phone_number: Phone number that was enrolled
            vector_id: The embedding vector ID in the database
            chunks_processed: Number of chunks processed
            success: Whether enrollment was successful
            message: Additional message
        Returns:
            Tuple of (sent_successfully, confirmation_id)
        """
        if not self.connection_manager:
            logging.getLogger(__name__).warning("Connection manager not set - cannot send confirmation")
            return False, ""
        
        client_id = self.session_clients.get(session_id)
        if not client_id:
            logging.getLogger(__name__).warning(f"No client registered for session {session_id[:8]}")
            return False, ""
        
        connection = self.connection_manager.get_connection(client_id)
        if not connection:
            logging.getLogger(__name__).warning(f"Client {client_id} not found in active connections")
            return False, ""
        
        try:
            confirmation_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            confirmation_message = {
                "type": "enrollment_confirmed",
                "status": "success" if success else "error",
                "confirmation_id": confirmation_id,
                "timestamp": timestamp,
                "data": {
                    "session_id": session_id,
                    "phone_number": phone_number,
                    "vector_id": vector_id,
                    "chunks_processed": chunks_processed,
                    "message": message or ("Enrollment completed successfully" if success else "Enrollment failed")
                }
            }
            
            # Send the confirmation
            success_sent = await connection.send_json(confirmation_message)
            
            if success_sent:
                # Record in history
                confirmation_record = {
                    "confirmation_id": confirmation_id,
                    "session_id": session_id,
                    "client_id": client_id,
                    "phone_number": phone_number,
                    "timestamp": timestamp,
                    "chunks_processed": chunks_processed
                }
                self.sent_confirmations.append(confirmation_record)
                
                # Clean up
                self.unregister_session(session_id)
                
                logging.getLogger(__name__).info(
                    f"✓ Sent enrollment confirmation {confirmation_id[:8]} "
                    f"to client {client_id[:8]} for session {session_id[:8]}"
                )
                
                return True, confirmation_id
            else:
                logging.getLogger(__name__).error(f"Failed to send confirmation to client {client_id}")
                return False, ""
        
        except Exception as e:
            logging.getLogger(__name__).error(f"Error sending confirmation: {str(e)}")
            return False, ""
    
    def get_confirmation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of sent confirmations"""
        return self.sent_confirmations[-limit:]
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get registration info for a session"""
        if session_id in self.session_clients:
            return {
                "session_id": session_id,
                "client_id": self.session_clients[session_id],
                "has_pending": session_id in self.pending_confirmations
            }
        return None
    
    def cleanup_expired_registrations(self, max_age_seconds: int = 3600) -> int:
        """Clean up old registrations"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        count = 0
        # Note: In a production system, you'd track registration times
        # For now, we just clean up sessions that no longer exist
        sessions_to_remove = []
        for session_id in list(self.session_clients):
            if get_enrollment_session(session_id) is None:
                sessions_to_remove.append(session_id)
                count += 1
        for session_id in sessions_to_remove:
            del self.session_clients[session_id]
        if count > 0:
            logging.getLogger(__name__).info(f"Cleaned up {count} expired confirmation registrations")
        return count

# Global confirmation service instance
confirmation_service = EnrollmentConfirmationService()

def get_confirmation_service() -> EnrollmentConfirmationService:
    """Get the global confirmation service"""
    return confirmation_service
