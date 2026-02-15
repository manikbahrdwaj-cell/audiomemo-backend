"""
WebSocket Audio Chunk Handler
Integrates audio chunk reception, merging, and embedding generation
with WebSocket message routing
"""

import numpy as np
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

from audio_chunk_receiver import get_chunk_receiver, ChunkReceiverStatus
from voice_embedding import generate_embedding

logger = logging.getLogger(__name__)


class WebSocketAudioChunkHandler:
    """
    Handles WebSocket messages for audio chunk transmission
    Integrates with chunk receiver for buffering and merging
    """
    
    def __init__(self):
        """Initialize handler"""
        self.chunk_receiver = get_chunk_receiver()
        logger.info("WebSocketAudioChunkHandler initialized")
    
    async def handle_audio_message(self, message: Dict[str, Any], client_connection) -> Dict[str, Any]:
        """
        Handle incoming audio chunk message
        
        Args:
            message: Message dict from WebSocket
            client_connection: ClientConnection instance
            
        Returns:
            Response dict to send back to client
        """
        try:
            action = message.get('action', 'send_chunk')
            
            if action == 'send_chunk':
                return await self._handle_send_chunk(message, client_connection)
            elif action == 'finalize_session':
                return await self._handle_finalize_session(message)
            elif action == 'cancel_session':
                return await self._handle_cancel_session(message)
            elif action == 'get_session_status':
                return await self._handle_get_session_status(message)
            else:
                return {
                    'status': 'error',
                    'error': f'Unknown audio action: {action}',
                    'type': 'audio'
                }
        
        except Exception as e:
            logger.error(f"Error handling audio message: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'type': 'audio'
            }
    
    async def _handle_send_chunk(self, message: Dict[str, Any], client_connection) -> Dict[str, Any]:
        """
        Handle incoming audio chunk
        
        Args:
            message: Audio chunk message
            client_connection: Client connection object
            
        Returns:
            Acknowledgment message
        """
        session_id = message.get('session_id')
        if not session_id:
            return {
                'status': 'error',
                'error': 'Missing session_id',
                'type': 'audio',
                'action': 'chunk_received'
            }
        
        # Get or create session if needed
        session = self.chunk_receiver.get_session(session_id)
        if session is None:
            phone_number = message.get('phone_number')
            mode = message.get('mode', 'enrollment')
            
            if not phone_number:
                return {
                    'status': 'error',
                    'error': 'Session not found, phone_number required to create new session',
                    'session_id': session_id,
                    'type': 'audio',
                    'action': 'chunk_received'
                }
            
            logger.info(f"Creating new session {session_id} for {phone_number} ({mode})")
            session = self.chunk_receiver.create_session(phone_number, mode)
            
            if session.session_id != session_id:
                logger.warning(
                    f"Session ID mismatch: expected {session_id}, got {session.session_id}"
                )
                session_id = session.session_id
        
        try:
            # Extract chunk data
            chunk_number = message.get('chunk_number', 0)
            audio_data_array = message.get('audio_data', [])
            sample_count = message.get('sample_count', 0)
            duration_ms = message.get('duration_ms', 0)
            
            if not audio_data_array:
                return {
                    'status': 'error',
                    'error': 'Missing audio_data',
                    'session_id': session_id,
                    'chunk_number': chunk_number,
                    'type': 'audio',
                    'action': 'chunk_received'
                }
            
            # Convert audio data from uint8 array back to float32
            audio_buffer = bytes(audio_data_array)
            float_array = np.frombuffer(audio_buffer, dtype=np.float32)
            
            # Validate sample count
            if sample_count != len(float_array):
                logger.warning(
                    f"Sample count mismatch: expected {sample_count}, got {len(float_array)}"
                )
            
            # Add chunk to session
            success, error = self.chunk_receiver.add_chunk(
                session_id=session_id,
                chunk_number=chunk_number,
                audio_data=float_array,
                sample_rate=16000,
                duration_ms=duration_ms
            )
            
            if not success:
                return {
                    'status': 'error',
                    'error': error,
                    'session_id': session_id,
                    'chunk_number': chunk_number,
                    'type': 'audio',
                    'action': 'chunk_received'
                }
            
            logger.debug(
                f"Received chunk #{chunk_number} for session {session_id}: "
                f"{sample_count} samples"
            )
            
            # Store client connection info for later communication
            client_connection.set_metadata('chunk_session_id', session_id)
            client_connection.set_metadata('chunk_phone_number', session.phone_number)
            
            return {
                'status': 'success',
                'type': 'audio',
                'action': 'chunk_received',
                'session_id': session_id,
                'chunk_number': chunk_number,
                'message': f'Chunk {chunk_number} received successfully'
            }
        
        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Error processing chunk: {str(e)}',
                'session_id': session_id,
                'chunk_number': message.get('chunk_number'),
                'type': 'audio',
                'action': 'chunk_received'
            }
    
    async def _handle_finalize_session(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finalize session: merge chunks and generate embedding
        
        Args:
            message: Finalize message
            
        Returns:
            Result with embedding
        """
        session_id = message.get('session_id')
        if not session_id:
            return {
                'status': 'error',
                'error': 'Missing session_id',
                'type': 'audio',
                'action': 'finalize_session'
            }
        
        try:
            logger.info(f"Finalizing session {session_id}")
            
            # Process session (merge chunks and generate embedding)
            success, embedding, error = self.chunk_receiver.process_session(session_id)
            
            if not success:
                return {
                    'status': 'error',
                    'error': error,
                    'session_id': session_id,
                    'type': 'audio',
                    'action': 'finalize_session'
                }
            
            # Get session info for response
            session_info = self.chunk_receiver.get_session_info(session_id)
            
            logger.info(
                f"Session {session_id} finalized successfully: "
                f"{session_info['chunks_received']} chunks merged, "
                f"{session_info['merged_duration_ms']:.0f}ms total duration"
            )
            
            return {
                'status': 'success',
                'type': 'audio',
                'action': 'finalize_session',
                'session_id': session_id,
                'embedding_shape': list(embedding.shape) if hasattr(embedding, 'shape') else [len(embedding)],
                'embedding_dim': len(embedding) if hasattr(embedding, '__len__') else 1,
                'session_info': session_info,
                'message': 'Session finalized and embedding generated'
            }
        
        except Exception as e:
            logger.error(f"Error finalizing session: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'type': 'audio',
                'action': 'finalize_session'
            }
    
    async def _handle_cancel_session(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cancel session and clean up
        
        Args:
            message: Cancel message
            
        Returns:
            Acknowledgment
        """
        session_id = message.get('session_id')
        if not session_id:
            return {
                'status': 'error',
                'error': 'Missing session_id',
                'type': 'audio',
                'action': 'cancel_session'
            }
        
        try:
            success = self.chunk_receiver.cleanup_session(session_id)
            
            return {
                'status': 'success' if success else 'error',
                'type': 'audio',
                'action': 'cancel_session',
                'session_id': session_id,
                'message': f'Session {session_id} cancelled'
            }
        
        except Exception as e:
            logger.error(f"Error cancelling session: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'type': 'audio',
                'action': 'cancel_session'
            }
    
    async def _handle_get_session_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get session status
        
        Args:
            message: Status request message
            
        Returns:
            Session status
        """
        session_id = message.get('session_id')
        if not session_id:
            return {
                'status': 'error',
                'error': 'Missing session_id',
                'type': 'audio',
                'action': 'get_session_status'
            }
        
        try:
            session_info = self.chunk_receiver.get_session_info(session_id)
            
            if session_info is None:
                return {
                    'status': 'error',
                    'error': f'Session {session_id} not found',
                    'type': 'audio',
                    'action': 'get_session_status'
                }
            
            return {
                'status': 'success',
                'type': 'audio',
                'action': 'get_session_status',
                'session_info': session_info
            }
        
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'type': 'audio',
                'action': 'get_session_status'
            }


# Global handler instance
_audio_chunk_handler = None


def get_audio_chunk_handler() -> WebSocketAudioChunkHandler:
    """Get or create global handler instance"""
    global _audio_chunk_handler
    if _audio_chunk_handler is None:
        _audio_chunk_handler = WebSocketAudioChunkHandler()
    return _audio_chunk_handler
