"""
WebSocket Infrastructure Test Suite
Tests for WebSocket connectivity and message handling
"""

import asyncio
import json
import base64
import logging
from datetime import datetime
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test configuration
WS_URI = "ws://localhost:8000/ws/voice"
TEST_PHONE = "+1234567890"


class WebSocketTestClient:
    """Test client for WebSocket communication"""
    
    def __init__(self, uri=WS_URI):
        self.uri = uri
        self.ws = None
        self.client_id = None
    
    async def connect(self):
        """Connect to WebSocket"""
        try:
            self.ws = await websockets.connect(self.uri)
            logger.info(f"Connected to {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws:
            await self.ws.close()
            logger.info("Disconnected")
    
    async def send_message(self, message: dict) -> dict:
        """Send a message and receive response"""
        try:
            # Send message
            await self.ws.send(json.dumps(message))
            logger.info(f"Sent: {message.get('type')}")
            
            # Receive response
            response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            data = json.loads(response)
            logger.info(f"Received: {data.get('type')}")
            return data
        except asyncio.TimeoutError:
            logger.error("Response timeout")
            return None
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None
    
    async def send_ping(self) -> bool:
        """Send a ping message"""
        response = await self.send_message({"type": "ping"})
        return response is not None and response.get('type') == 'pong'
    
    async def send_audio_chunk(self, size: int = 5000) -> bool:
        """Send an audio chunk"""
        dummy_audio = b"\x00" * size
        audio_b64 = base64.b64encode(dummy_audio).decode()
        
        response = await self.send_message({
            "type": "audio",
            "data": audio_b64
        })
        return response is not None and response.get('type') == 'audio_received'
    
    async def enroll(self) -> bool:
        """Send enrollment request"""
        response = await self.send_message({
            "type": "enroll",
            "phone_number": TEST_PHONE
        })
        return response is not None and response.get('type') == 'enrollment_success'
    
    async def verify(self) -> bool:
        """Send verification request"""
        response = await self.send_message({
            "type": "verify",
            "phone_number": TEST_PHONE
        })
        return response is not None and response.get('type') == 'verification_result'
    
    async def reset(self) -> bool:
        """Send reset message"""
        response = await self.send_message({"type": "reset"})
        return response is not None and response.get('type') == 'reset_acknowledged'
    
    async def get_status(self) -> bool:
        """Get connection status"""
        response = await self.send_message({"type": "status"})
        return response is not None and response.get('type') == 'status'


class WebSocketTestSuite:
    """Test suite for WebSocket infrastructure"""
    
    def __init__(self):
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 50)
        logger.info("WebSocket Infrastructure Test Suite")
        logger.info("=" * 50)
        
        # Connection tests
        await self.test_basic_connection()
        await self.test_ping_pong()
        
        # Message tests
        await self.test_audio_chunks()
        await self.test_invalid_message()
        await self.test_missing_fields()
        await self.test_buffer_operations()
        
        # Status tests
        await self.test_status_message()
        
        # Print results
        self.print_results()
    
    async def test_basic_connection(self):
        """Test basic WebSocket connection"""
        logger.info("\n[TEST] Basic Connection")
        try:
            client = WebSocketTestClient()
            success = await client.connect()
            await client.disconnect()
            self.record_result("Basic Connection", success)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Basic Connection", False)
    
    async def test_ping_pong(self):
        """Test ping-pong keep-alive"""
        logger.info("\n[TEST] Ping-Pong")
        try:
            client = WebSocketTestClient()
            await client.connect()
            
            success = await client.send_ping()
            await client.disconnect()
            self.record_result("Ping-Pong", success)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Ping-Pong", False)
    
    async def test_audio_chunks(self):
        """Test audio chunk reception"""
        logger.info("\n[TEST] Audio Chunk Reception")
        try:
            client = WebSocketTestClient()
            await client.connect()
            
            # Send multiple chunks
            success = True
            for i in range(3):
                chunk_ok = await client.send_audio_chunk(size=5000)
                if not chunk_ok:
                    success = False
                    break
            
            await client.disconnect()
            self.record_result("Audio Chunk Reception", success)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Audio Chunk Reception", False)
    
    async def test_invalid_message(self):
        """Test handling of invalid message type"""
        logger.info("\n[TEST] Invalid Message Type")
        try:
            client = WebSocketTestClient()
            await client.connect()
            
            response = await client.send_message({"type": "invalid"})
            success = response is not None and response.get('type') == 'error'
            
            await client.disconnect()
            self.record_result("Invalid Message Type", success)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Invalid Message Type", False)
    
    async def test_missing_fields(self):
        """Test validation of missing required fields"""
        logger.info("\n[TEST] Missing Required Fields")
        try:
            client = WebSocketTestClient()
            await client.connect()
            
            # Send verify without phone_number
            response = await client.send_message({"type": "verify"})
            success = response is not None and response.get('status') == 'error'
            
            await client.disconnect()
            self.record_result("Missing Required Fields", success)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Missing Required Fields", False)
    
    async def test_buffer_operations(self):
        """Test audio buffer operations"""
        logger.info("\n[TEST] Buffer Operations")
        try:
            client = WebSocketTestClient()
            await client.connect()
            
            # Add some audio
            await client.send_audio_chunk(size=5000)
            
            # Reset buffer
            reset_ok = await client.reset()
            
            await client.disconnect()
            self.record_result("Buffer Operations", reset_ok)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Buffer Operations", False)
    
    async def test_status_message(self):
        """Test status message"""
        logger.info("\n[TEST] Status Message")
        try:
            client = WebSocketTestClient()
            await client.connect()
            
            success = await client.get_status()
            await client.disconnect()
            self.record_result("Status Message", success)
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.record_result("Status Message", False)
    
    def record_result(self, test_name: str, success: bool):
        """Record test result"""
        if success:
            self.results["passed"] += 1
            status = "✓ PASSED"
        else:
            self.results["failed"] += 1
            status = "✗ FAILED"
        
        self.results["tests"].append({
            "name": test_name,
            "status": status,
            "success": success
        })
        
        logger.info(f"{status}: {test_name}")
    
    def print_results(self):
        """Print test results summary"""
        logger.info("\n" + "=" * 50)
        logger.info("Test Results Summary")
        logger.info("=" * 50)
        
        for test in self.results["tests"]:
            logger.info(f"{test['status']}: {test['name']}")
        
        logger.info("=" * 50)
        logger.info(f"Total: {self.results['passed'] + self.results['failed']}")
        logger.info(f"Passed: {self.results['passed']}")
        logger.info(f"Failed: {self.results['failed']}")
        
        if self.results["failed"] == 0:
            logger.info("✓ All tests passed!")
        else:
            logger.info(f"✗ {self.results['failed']} test(s) failed")
        
        logger.info("=" * 50)


async def main():
    """Run test suite"""
    suite = WebSocketTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Tests interrupted")
    except Exception as e:
        logger.error(f"Test suite error: {str(e)}")
