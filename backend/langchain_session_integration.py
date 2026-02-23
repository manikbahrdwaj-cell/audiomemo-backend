"""
LangChain Session Integration with Voice Verification
Demonstrates creating and managing LangChain sessions after successful voice authentication

This module shows:
1. Creating a LangChain session after voice verification
2. Storing session metadata in MongoDB
3. Managing conversation history
4. Handling session lifecycle (pause, resume, terminate)
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from langchain_session_service import (
    get_langchain_session_manager,
    LangChainSession,
    LangChainSessionStatus
)
from database import (
    get_langchain_sessions_collection,
    save_langchain_session,
    get_langchain_session,
    update_langchain_session_status,
    add_conversation_turn,
    get_langchain_sessions_by_phone,
    get_langchain_session_summary,
    delete_expired_langchain_sessions
)
from session_service import (
    get_verified_session_manager,
    VerifiedSession
)

logger = logging.getLogger(__name__)


class LangChainSessionIntegration:
    """
    Integration between voice verification and LangChain sessions
    Manages the complete lifecycle of LangChain sessions for authenticated users
    """
    
    def __init__(self):
        """Initialize the integration"""
        self.session_manager = get_langchain_session_manager()
        logger.info("Initialized LangChainSessionIntegration")
    
    def create_session_on_voice_match(
        self,
        phone_number: str,
        verification_score: float,
        similarity_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a LangChain session after successful voice verification match
        
        Args:
            phone_number: The matched phone number
            verification_score: Voice similarity score (0-1)
            similarity_metrics: Dict with metrics like cosine_similarity, confidence
            
        Returns:
            Dict with session info
        """
        try:
            # Create LangChain session
            lc_session = self.session_manager.create_session(
                phone_number=phone_number,
                verification_score=verification_score,
                session_status="active",
                custom_metadata={
                    "verification_metrics": similarity_metrics,
                    "voice_verified": True,
                    "verification_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Prepare data for MongoDB storage
            session_data = {
                "metadata": lc_session.metadata.to_dict(),
                "phone_number": phone_number,
                "session_status": "active",
                "conversation_history": []
            }
            
            # If LangChain config exists, include it
            if lc_session.config:
                session_data["config"] = dict(lc_session.config)
            
            # Save to MongoDB
            db_id = save_langchain_session(session_data)
            
            logger.info(
                f"✓ Created LangChain session {lc_session.metadata.session_id[:16]} "
                f"for {phone_number} (verification_score: {verification_score:.4f})"
            )
            
            return {
                "success": True,
                "session_id": lc_session.metadata.session_id,
                "thread_id": lc_session.metadata.langgraph_thread_id,
                "phone_number": phone_number,
                "verification_score": verification_score,
                "status": "active",
                "created_at": lc_session.metadata.timestamp.isoformat(),
                "mongodb_id": db_id
            }
        
        except Exception as e:
            logger.error(f"Failed to create LangChain session: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a conversation message to a session
        
        Args:
            session_id: The LangChain session ID
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata about the message
            
        Returns:
            True if added successfully
        """
        try:
            # Update in memory
            success_memory = self.session_manager.add_conversation_turn(
                session_id=session_id,
                role=role,
                content=content,
                metadata=metadata
            )
            
            if not success_memory:
                logger.warning(f"Session {session_id[:16]} not found in memory")
                # Try to get from MongoDB and create in memory
                db_session = get_langchain_session(session_id)
                if db_session:
                    # Recreate in memory from DB
                    logger.info(f"Restored session {session_id[:16]} from MongoDB")
                else:
                    return False
            
            # Update in MongoDB
            add_conversation_turn(
                session_id=session_id,
                role=role,
                content=content,
                turn_metadata=metadata
            )
            
            logger.debug(
                f"Added {role} message to session {session_id[:16]}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error adding message to session: {str(e)}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete info about a session
        
        Args:
            session_id: The session ID
            
        Returns:
            Session info dict or None
        """
        try:
            # First try memory
            session = self.session_manager.get_session(session_id)
            if session:
                return self.session_manager.get_session_summary(session_id)
            
            # Then try MongoDB
            db_session = get_langchain_session(session_id)
            if db_session:
                return get_langchain_session_summary(session_id)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting session info: {str(e)}")
            return None
    
    def pause_session(self, session_id: str) -> bool:
        """
        Pause a session (pause conversation)
        
        Args:
            session_id: The session ID
            
        Returns:
            True if paused
        """
        try:
            # Update in memory
            success = self.session_manager.pause_session(session_id)
            
            if success:
                # Update in MongoDB
                update_langchain_session_status(
                    session_id=session_id,
                    status="paused"
                )
                
                logger.info(f"Paused session {session_id[:16]}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error pausing session: {str(e)}")
            return False
    
    def resume_session(self, session_id: str) -> bool:
        """
        Resume a paused session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if resumed
        """
        try:
            # Update in memory
            success = self.session_manager.resume_session(session_id)
            
            if success:
                # Update in MongoDB
                update_langchain_session_status(
                    session_id=session_id,
                    status="active"
                )
                
                logger.info(f"Resumed session {session_id[:16]}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error resuming session: {str(e)}")
            return False
    
    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session
        
        Args:
            session_id: The session ID
            
        Returns:
            True if terminated
        """
        try:
            # Update in memory
            success = self.session_manager.terminate_session(session_id)
            
            if success:
                # Update in MongoDB
                update_langchain_session_status(
                    session_id=session_id,
                    status="terminated"
                )
                
                # Get session summary before termination
                summary = self.get_session_info(session_id)
                
                logger.info(
                    f"Terminated session {session_id[:16]} "
                    f"(turns: {summary.get('conversation_turns', 0) if summary else 0})"
                )
            
            return success
        
        except Exception as e:
            logger.error(f"Error terminating session: {str(e)}")
            return False
    
    def get_user_sessions(
        self,
        phone_number: str,
        limit: int = 10
    ) -> list:
        """
        Get all sessions for a phone number
        
        Args:
            phone_number: The phone number
            limit: Maximum sessions to return
            
        Returns:
            List of session summaries
        """
        try:
            # Get from MongoDB
            sessions = get_langchain_sessions_by_phone(
                phone_number=phone_number,
                limit=limit
            )
            
            results = []
            for session_doc in sessions:
                summary = get_langchain_session_summary(
                    session_doc.get("session_id")
                )
                if summary:
                    results.append(summary)
            
            logger.info(
                f"Retrieved {len(results)} sessions for {phone_number}"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self, ttl_seconds: int = 86400) -> int:
        """
        Clean up expired sessions (older than TTL)
        
        Args:
            ttl_seconds: Sessions older than this are removed
            
        Returns:
            Number of sessions deleted
        """
        try:
            # Clear from MongoDB
            count = delete_expired_langchain_sessions(ttl_seconds=ttl_seconds)
            
            # Clear from memory
            self.session_manager.clear_expired_sessions()
            
            logger.info(f"Cleaned up {count} expired LangChain sessions")
            
            return count
        
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0


# Global integration instance
_integration: Optional[LangChainSessionIntegration] = None


def get_langchain_session_integration() -> LangChainSessionIntegration:
    """Get or create global LangChainSessionIntegration instance"""
    global _integration
    
    if _integration is None:
        _integration = LangChainSessionIntegration()
    
    return _integration


# ========== EXAMPLE USAGE ==========

if __name__ == "__main__":
    """
    Example showing how to use LangChain session integration
    """
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get integration instance
    integration = get_langchain_session_integration()
    
    # Example 1: Create session after voice match
    print("\n" + "="*60)
    print("Example 1: Create LangChain Session After Voice Match")
    print("="*60)
    
    session_result = integration.create_session_on_voice_match(
        phone_number="+1-555-0123",
        verification_score=0.92,
        similarity_metrics={
            "cosine_similarity": 0.92,
            "confidence": 92.0,
            "cosine_distance": 0.08
        }
    )
    
    print(f"Session Created: {session_result['success']}")
    if session_result['success']:
        session_id = session_result['session_id']
        print(f"Session ID: {session_id}")
        print(f"Thread ID: {session_result['thread_id']}")
        print(f"Status: {session_result['status']}")
        
        # Example 2: Add messages to session
        print("\n" + "="*60)
        print("Example 2: Add Messages to Session")
        print("="*60)
        
        # Add user message
        integration.add_message_to_session(
            session_id=session_id,
            role="user",
            content="Hello, I'd like to verify my account",
            metadata={"source": "voice_app"}
        )
        print("✓ Added user message")
        
        # Add assistant response
        integration.add_message_to_session(
            session_id=session_id,
            role="assistant",
            content="Welcome! Your voice has been verified. How can I help you today?",
            metadata={"source": "llm"}
        )
        print("✓ Added assistant message")
        
        # Example 3: Get session info
        print("\n" + "="*60)
        print("Example 3: Get Session Information")
        print("="*60)
        
        info = integration.get_session_info(session_id)
        if info:
            print(f"Session Status: {info['status']}")
            print(f"Phone: {info['phone_number']}")
            print(f"Verification Score: {info['verification_score']:.2f}")
            print(f"Messages: {info['messages']}")
            print(f"Duration: {info['duration_seconds']:.1f}s")
        
        # Example 4: Pause/Resume session
        print("\n" + "="*60)
        print("Example 4: Pause and Resume Session")
        print("="*60)
        
        integration.pause_session(session_id)
        print("✓ Session paused")
        
        import time
        time.sleep(1)
        
        integration.resume_session(session_id)
        print("✓ Session resumed")
        
        # Example 5: Get user sessions history
        print("\n" + "="*60)
        print("Example 5: Get User Sessions History")
        print("="*60)
        
        user_sessions = integration.get_user_sessions("+1-555-0123", limit=5)
        print(f"Found {len(user_sessions)} sessions for user")
        for sess in user_sessions:
            print(f"  - {sess['session_id'][:16]}: {sess['status']}")
        
        # Example 6: Terminate session
        print("\n" + "="*60)
        print("Example 6: Terminate Session")
        print("="*60)
        
        integration.terminate_session(session_id)
        print("✓ Session terminated")
        
        # Final info
        final_info = integration.get_session_info(session_id)
        if final_info:
            print(f"Final Status: {final_info['status']}")
    
    print("\n" + "="*60)
    print("Examples Complete!")
    print("="*60)
