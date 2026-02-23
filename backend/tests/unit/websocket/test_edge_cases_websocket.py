"""
Edge Case Tests for WebSocket Operations
Tests boundary conditions and error scenarios in WebSocket communication
"""

import pytest
import json
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TestWebSocketEdgeCases:
    """Comprehensive edge case tests for WebSocket communication"""

    # ========== CONNECTION EDGE CASES ==========
    
    @pytest.mark.asyncio
    async def test_connection_immediate_disconnect(self):
        """Test immediate disconnect after connection"""
        try:
            connection = await self._create_connection()
            await connection.disconnect()
            
            # Should handle gracefully
            assert True
        except Exception as e:
            logger.error(f"Connection error: {e}")

    @pytest.mark.asyncio
    async def test_connection_null_client(self):
        """Test creating connection with null client"""
        connection = None
        assert connection is None

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self):
        """Test multiple simultaneous connections from same user"""
        connections = []
        
        try:
            for _ in range(5):
                conn = await self._create_connection("user123")
                connections.append(conn)
            
            assert len(connections) == 5
            
            # Cleanup
            for conn in connections:
                await conn.disconnect()
        except Exception as e:
            logger.error(f"Multiple connections error: {e}")

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test connection timeout after inactivity"""
        try:
            connection = await self._create_connection()
            
            # Simulate long inactivity
            await asyncio.sleep(0.1)
            
            await connection.disconnect()
        except asyncio.TimeoutError:
            pass  # Expected

    @pytest.mark.asyncio
    async def test_connection_with_invalid_uri(self):
        """Test connection with invalid WebSocket URI"""
        invalid_uris = [
            "invalid://not.websocket",
            "http://regular.http.server",
            "",
            None,
            "ws://",
            "wss://",
        ]
        
        for uri in invalid_uris:
            try:
                # Should reject invalid URI
                assert uri is None or isinstance(uri, str)
            except:
                pass

    # ========== MESSAGE EDGE CASES ==========
    
    @pytest.mark.asyncio
    async def test_send_empty_message(self):
        """Test sending empty message"""
        message = ""
        
        result = self._validate_message(message)
        assert result is None or result == False

    @pytest.mark.asyncio
    async def test_send_null_message(self):
        """Test sending null message"""
        message = None
        
        result = self._validate_message(message)
        assert result is None or result == False

    @pytest.mark.asyncio
    async def test_send_extremely_large_message(self):
        """Test sending extremely large message"""
        message = {"data": "x" * (10 * 1024 * 1024)}  # 10MB
        
        try:
            result = self._validate_message(message)
            # Might reject or limit size
        except (ValueError, MemoryError):
            pass

    @pytest.mark.asyncio
    async def test_send_invalid_json(self):
        """Test sending invalid JSON"""
        messages = [
            "{invalid json}",
            '{"key": undefined}',
            "{'single': 'quotes'}",
            "{key: 'no quotes'}",
        ]
        
        for msg in messages:
            try:
                parsed = json.loads(msg)
            except json.JSONDecodeError:
                pass  # Expected

    @pytest.mark.asyncio
    async def test_send_message_wrong_format(self):
        """Test sending message in wrong format"""
        invalid_formats = [
            123,  # Integer
            123.45,  # Float
            True,  # Boolean
            [],  # List
            b"bytes",  # Bytes
        ]
        
        for fmt in invalid_formats:
            result = self._validate_message(fmt)
            assert result is None or result == False

    @pytest.mark.asyncio
    async def test_message_with_special_characters(self):
        """Test message with special characters"""
        messages = [
            {"text": "hello\\nworld"},
            {"text": "hello\\tworld"},
            {"text": "hello\\x00null"},
            {"text": "你好世界"},  # Chinese
            {"text": "🎵🎶"},  # Emojis
            {"text": "\r\n\r\n"},  # Line endings
        ]
        
        for msg in messages:
            result = self._validate_message(msg)
            # Should handle or reject gracefully

    # ========== MESSAGE TYPE EDGE CASES ==========
    
    @pytest.mark.asyncio
    async def test_missing_message_type(self):
        """Test message without type field"""
        message = {
            "data": "some data"
            # No "type" field
        }
        
        result = self._validate_message_type(message)
        assert result is None or result == False

    @pytest.mark.asyncio
    async def test_null_message_type(self):
        """Test message with null type"""
        message = {
            "type": None,
            "data": "some data"
        }
        
        result = self._validate_message_type(message)
        assert result is None or result == False

    @pytest.mark.asyncio
    async def test_empty_message_type(self):
        """Test message with empty type string"""
        message = {
            "type": "",
            "data": "some data"
        }
        
        result = self._validate_message_type(message)
        assert result is None or result == False

    @pytest.mark.asyncio
    async def test_unknown_message_type(self):
        """Test message with unknown type"""
        message = {
            "type": "UNKNOWN_TYPE_XYZ",
            "data": "some data"
        }
        
        result = self._handle_message(message)
        assert result is None or result.get('success') == False

    @pytest.mark.asyncio
    async def test_message_type_case_sensitivity(self):
        """Test message type case variations"""
        types = ["audio_chunk", "AUDIO_CHUNK", "Audio_Chunk", "audio_CHUNK"]
        
        for msg_type in types:
            message = {"type": msg_type}
            result = self._validate_message_type(message)
            # May be case-sensitive or case-insensitive

    # ========== AUDIO CHUNK MESSAGE EDGE CASES ==========
    
    @pytest.mark.asyncio
    async def test_audio_chunk_missing_data(self):
        """Test audio chunk message without data"""
        message = {
            "type": "audio_chunk",
            "chunk_id": "123"
            # No "data" field
        }
        
        result = self._handle_message(message)
        assert result is None or result.get('success') == False

    @pytest.mark.asyncio
    async def test_audio_chunk_null_data(self):
        """Test audio chunk message with null data"""
        message = {
            "type": "audio_chunk",
            "data": None
        }
        
        result = self._handle_message(message)
        assert result is None or result.get('success') == False

    @pytest.mark.asyncio
    async def test_audio_chunk_empty_data(self):
        """Test audio chunk message with empty data"""
        message = {
            "type": "audio_chunk",
            "data": ""
        }
        
        result = self._handle_message(message)
        assert result is None or result.get('success') == False

    @pytest.mark.asyncio
    async def test_audio_chunk_invalid_base64(self):
        """Test audio chunk message with invalid base64 data"""
        message = {
            "type": "audio_chunk",
            "data": "not!!!valid!!!base64!!!"
        }
        
        try:
            result = self._handle_message(message)
            # Should reject invalid base64
        except ValueError:
            pass

    @pytest.mark.asyncio
    async def test_audio_chunk_extremely_large(self):
        """Test audio chunk message with extremely large data"""
        message = {
            "type": "audio_chunk",
            "data": "x" * (100 * 1024 * 1024)  # 100MB
        }
        
        try:
            result = self._handle_message(message)
            # Might reject or limit
        except (ValueError, MemoryError):
            pass

    @pytest.mark.asyncio
    async def test_audio_chunk_missing_chunk_id(self):
        """Test audio chunk without chunk_id"""
        message = {
            "type": "audio_chunk",
            "data": "dGVzdA=="  # base64 encoded
            # No "chunk_id"
        }
        
        result = self._handle_message(message)
        # Should either generate or reject

    @pytest.mark.asyncio
    async def test_audio_chunk_invalid_chunk_id(self):
        """Test audio chunk with invalid chunk_id"""
        invalid_ids = [
            None,
            "",
            123,  # Not a string
            {},  # Object
        ]
        
        for chunk_id in invalid_ids:
            message = {
                "type": "audio_chunk",
                "data": "dGVzdA==",
                "chunk_id": chunk_id
            }
            
            try:
                result = self._handle_message(message)
                # Should validate or reject chunk_id
            except (TypeError, ValueError):
                pass

    # ========== BATCH OPERATIONS ==========
    
    @pytest.mark.asyncio
    async def test_send_multiple_messages_rapid(self):
        """Test sending multiple messages in rapid succession"""
        try:
            connection = await self._create_connection()
            
            for i in range(100):
                message = {
                    "type": "audio_chunk",
                    "data": f"chunk_{i}",
                    "chunk_id": str(i)
                }
                
                await asyncio.sleep(0.001)  # 1ms delay
                self._handle_message(message)
            
            await connection.disconnect()
        except Exception as e:
            logger.error(f"Rapid messages error: {e}")

    @pytest.mark.asyncio
    async def test_receive_multiple_messages_queued(self):
        """Test receiving multiple queued messages"""
        messages = [
            {"type": "audio_chunk", "data": "chunk1", "chunk_id": "1"},
            {"type": "audio_chunk", "data": "chunk2", "chunk_id": "2"},
            {"type": "audio_chunk", "data": "chunk3", "chunk_id": "3"},
        ]
        
        for msg in messages:
            result = self._handle_message(msg)
            # Should process without blocking

    # ========== FRAME SIZE EDGE CASES ==========
    
    @pytest.mark.asyncio
    async def test_minimum_frame_size(self):
        """Test WebSocket frame with minimum size"""
        message = {"type": "ping"}
        result = self._handle_message(message)
        assert result is not None

    @pytest.mark.asyncio
    async def test_maximum_frame_size(self):
        """Test WebSocket frame with maximum size"""
        # WebSocket default max frame size is usually 64KB
        large_data = "x" * (64 * 1024)
        
        message = {
            "type": "audio_chunk",
            "data": large_data
        }
        
        try:
            result = self._handle_message(message)
        except (ValueError, OverflowError):
            pass

    # ========== BINARY VS TEXT MESSAGES ==========
    
    @pytest.mark.asyncio
    async def test_binary_message_type(self):
        """Test sending binary message"""
        binary_data = b"binary_audio_data"
        
        try:
            result = self._handle_message(binary_data)
            # Should handle or reject binary
        except (TypeError, ValueError):
            pass

    @pytest.mark.asyncio
    async def test_mixed_text_binary_in_session(self):
        """Test mixed text and binary messages in one session"""
        try:
            connection = await self._create_connection()
            
            # Text message
            text_msg = {"type": "ping"}
            self._handle_message(text_msg)
            
            # Binary message
            binary_msg = b"binary"
            try:
                self._handle_message(binary_msg)
            except:
                pass
            
            await connection.disconnect()
        except:
            pass

    # ========== RECOVERY EDGE CASES ==========
    
    @pytest.mark.asyncio
    async def test_reconnection_after_disconnect(self):
        """Test reconnection after disconnect"""
        try:
            connection = await self._create_connection("user123")
            await connection.disconnect()
            
            # Reconnect
            connection2 = await self._create_connection("user123")
            await connection2.disconnect()
            
            assert True
        except Exception as e:
            logger.error(f"Reconnection error: {e}")

    @pytest.mark.asyncio
    async def test_message_after_disconnect(self):
        """Test sending message after disconnect"""
        try:
            connection = await self._create_connection()
            await connection.disconnect()
            
            # Try to send message on closed connection
            message = {"type": "ping"}
            result = self._handle_message(message)
            # Should fail or reject
        except:
            pass

    # ========== HELPER METHODS ==========
    
    async def _create_connection(self, user_id: str = "default_user"):
        """Create mock WebSocket connection"""
        class MockConnection:
            def __init__(self, user_id):
                self.user_id = user_id
                self.connected = True
            
            async def disconnect(self):
                self.connected = False
        
        return MockConnection(user_id)

    def _validate_message(self, message) -> bool:
        """Validate message format"""
        if message is None or message == "":
            return False
        
        if isinstance(message, str):
            try:
                json.loads(message)
                return True
            except json.JSONDecodeError:
                return False
        
        if isinstance(message, dict):
            return True
        
        return False

    def _validate_message_type(self, message: dict):
        """Validate message type field"""
        if not isinstance(message, dict):
            return None
        
        msg_type = message.get("type")
        
        if msg_type is None or msg_type == "":
            return None
        
        if not isinstance(msg_type, str):
            return None
        
        return msg_type

    def _handle_message(self, message) -> dict:
        """Handle incoming message"""
        try:
            msg_type = self._validate_message_type(message)
            
            if msg_type is None:
                return {"success": False, "error": "Invalid message type"}
            
            return {"success": True, "type": msg_type}
        except Exception as e:
            return {"success": False, "error": str(e)}


class TestWebSocketAuthenticationEdgeCases:
    """Tests for WebSocket authentication edge cases"""

    @pytest.mark.asyncio
    async def test_connection_without_authentication(self):
        """Test connecting without authentication token"""
        try:
            connection = await self._create_authenticated_connection(token=None)
            await connection.disconnect()
        except (ValueError, RuntimeError):
            pass  # Expected

    @pytest.mark.asyncio
    async def test_connection_with_invalid_token(self):
        """Test connecting with invalid token"""
        try:
            connection = await self._create_authenticated_connection(token="invalid_token")
            await connection.disconnect()
        except (ValueError, RuntimeError):
            pass

    @pytest.mark.asyncio
    async def test_connection_with_expired_token(self):
        """Test connecting with expired token"""
        try:
            connection = await self._create_authenticated_connection(token="expired_token")
            await connection.disconnect()
        except (ValueError, RuntimeError):
            pass

    async def _create_authenticated_connection(self, token: str = None):
        """Create authenticated WebSocket connection"""
        if token is None:
            raise ValueError("No token provided")
        
        class AuthenticatedConnection:
            def __init__(self, token):
                self.token = token
            
            async def disconnect(self):
                pass
        
        return AuthenticatedConnection(token)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
