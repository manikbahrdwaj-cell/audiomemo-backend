"""
WebSocket Routing Infrastructure Test Suite
Tests message routing, validation, rate limiting, and monitoring
"""

import asyncio
import json
import base64
import logging
from typing import Dict, Any, Optional
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("ERROR: websockets library not found. Install with: pip install websockets")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
WS_URL = "ws://localhost:8000/ws/voice"
API_BASE = "http://localhost:8000"

class WebSocketRoutingTester:
    """Test WebSocket routing infrastructure"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    async def test_connection(self) -> bool:
        """Test basic WebSocket connection"""
        logger.info("TEST: Basic WebSocket Connection")
        try:
            async with websockets.connect(WS_URL) as ws:
                logger.info("✓ WebSocket connection established")
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            self.failed += 1
            return False
    
    async def test_ping_pong(self) -> bool:
        """Test ping/pong keep-alive"""
        logger.info("\nTEST: Ping/Pong Keep-Alive")
        try:
            async with websockets.connect(WS_URL) as ws:
                # Send ping
                ping_msg = {"type": "ping"}
                await ws.send(json.dumps(ping_msg))
                logger.debug(f"Sent: {ping_msg}")
                
                # Receive pong
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_json = json.loads(response)
                
                assert response_json.get("type") == "pong", "Expected pong response"
                assert response_json.get("status") == "ok", "Expected status ok"
                
                logger.info(f"✓ Ping/Pong successful")
                logger.debug(f"Response: {response_json}")
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Ping/Pong failed: {e}")
            self.failed += 1
            return False
    
    async def test_status_request(self) -> bool:
        """Test status request"""
        logger.info("\nTEST: Status Request")
        try:
            async with websockets.connect(WS_URL) as ws:
                status_msg = {"type": "status"}
                await ws.send(json.dumps(status_msg))
                logger.debug(f"Sent: {status_msg}")
                
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_json = json.loads(response)
                
                assert response_json.get("type") == "status", "Expected status response"
                assert "data" in response_json, "Expected data in response"
                
                data = response_json.get("data", {})
                logger.info(f"✓ Status request successful")
                logger.debug(f"Connection state: {data.get('state')}")
                logger.debug(f"Uptime: {data.get('uptime_seconds'):.2f}s")
                
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Status request failed: {e}")
            self.failed += 1
            return False
    
    async def test_audio_chunk(self) -> bool:
        """Test audio chunk message"""
        logger.info("\nTEST: Audio Chunk Message")
        try:
            # Create dummy audio data
            dummy_audio = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
            dummy_audio_b64 = base64.b64encode(dummy_audio).decode()
            
            async with websockets.connect(WS_URL) as ws:
                audio_msg = {
                    "type": "audio",
                    "data": dummy_audio_b64
                }
                await ws.send(json.dumps(audio_msg))
                logger.debug(f"Sent audio message ({len(dummy_audio)} bytes)")
                
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_json = json.loads(response)
                
                assert response_json.get("status") in ("ok", "error"), "Expected status"
                
                logger.info(f"✓ Audio chunk message accepted")
                logger.debug(f"Response: {response_json.get('type')}")
                
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Audio chunk message failed: {e}")
            self.failed += 1
            return False
    
    async def test_validation_error(self) -> bool:
        """Test message validation"""
        logger.info("\nTEST: Message Validation")
        try:
            async with websockets.connect(WS_URL) as ws:
                # Send invalid message (missing required field)
                invalid_msg = {"type": "verify"}  # Missing phone_number
                await ws.send(json.dumps(invalid_msg))
                logger.debug(f"Sent invalid message: {invalid_msg}")
                
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_json = json.loads(response)
                
                assert response_json.get("status") == "error", "Expected error response"
                assert "phone_number" in response_json.get("message", ""), "Expected field error"
                
                logger.info(f"✓ Validation error detected correctly")
                logger.debug(f"Error type: {response_json.get('error_type')}")
                
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Validation test failed: {e}")
            self.failed += 1
            return False
    
    async def test_unknown_message_type(self) -> bool:
        """Test unknown message type handling"""
        logger.info("\nTEST: Unknown Message Type")
        try:
            async with websockets.connect(WS_URL) as ws:
                unknown_msg = {"type": "unknown_operation"}
                await ws.send(json.dumps(unknown_msg))
                logger.debug(f"Sent unknown message type")
                
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_json = json.loads(response)
                
                assert response_json.get("status") == "error", "Expected error response"
                assert response_json.get("error_type") == "unknown_type", "Expected unknown_type error"
                
                logger.info(f"✓ Unknown message type handled correctly")
                
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Unknown message type test failed: {e}")
            self.failed += 1
            return False
    
    async def test_reset_buffer(self) -> bool:
        """Test buffer reset"""
        logger.info("\nTEST: Audio Buffer Reset")
        try:
            async with websockets.connect(WS_URL) as ws:
                # Send some audio first
                dummy_audio_b64 = base64.b64encode(b"TEST_AUDIO_DATA").decode()
                await ws.send(json.dumps({"type": "audio", "data": dummy_audio_b64}))
                response1 = await asyncio.wait_for(ws.recv(), timeout=5)
                
                # Reset buffer
                reset_msg = {"type": "reset"}
                await ws.send(json.dumps(reset_msg))
                logger.debug(f"Sent reset message")
                
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_json = json.loads(response)
                
                assert response_json.get("type") == "reset_acknowledged", "Expected reset acknowledgment"
                assert response_json.get("status") == "ok", "Expected status ok"
                
                logger.info(f"✓ Buffer reset successful")
                
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Buffer reset test failed: {e}")
            self.failed += 1
            return False
    
    async def test_rate_limiting(self) -> bool:
        """Test rate limiting (simplified)"""
        logger.info("\nTEST: Rate Limiting (Simplified)")
        try:
            async with websockets.connect(WS_URL) as ws:
                # Send multiple messages rapidly
                for i in range(5):
                    ping_msg = {"type": "ping"}
                    await ws.send(json.dumps(ping_msg))
                
                # Collect responses
                responses = []
                for i in range(5):
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    responses.append(json.loads(response))
                
                # All should succeed (within rate limit)
                successful = sum(1 for r in responses if r.get("status") == "ok")
                assert successful == 5, f"Expected 5 successful, got {successful}"
                
                logger.info(f"✓ Rate limiting test passed ({successful}/5 messages accepted)")
                
                self.passed += 1
                return True
        except Exception as e:
            logger.error(f"✗ Rate limiting test failed: {e}")
            self.failed += 1
            return False
    
    async def test_multiple_connections(self) -> bool:
        """Test multiple concurrent connections"""
        logger.info("\nTEST: Multiple Concurrent Connections")
        try:
            async def connect_and_ping(client_id: int):
                async with websockets.connect(WS_URL) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    return json.loads(response).get("status") == "ok"
            
            # Create 5 concurrent connections
            results = await asyncio.gather(*[connect_and_ping(i) for i in range(5)])
            
            successful = sum(results)
            assert all(results), f"Expected all connections to succeed, got {successful}/5"
            
            logger.info(f"✓ Multiple connections test passed ({successful}/5 succeeded)")
            
            self.passed += 1
            return True
        except Exception as e:
            logger.error(f"✗ Multiple connections test failed: {e}")
            self.failed += 1
            return False
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        logger.info("\n" + "="*60)
        logger.info(f"TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {self.passed} ✓")
        logger.info(f"Failed: {self.failed} ✗")
        logger.info(f"Success Rate: {(self.passed/total*100):.1f}%" if total > 0 else "N/A")
        logger.info("="*60)
        
        return self.failed == 0

async def main():
    """Run all tests"""
    logger.info(f"WebSocket Routing Infrastructure Test Suite")
    logger.info(f"Testing WebSocket URL: {WS_URL}")
    logger.info("="*60)
    
    # Check if server is running
    try:
        import urllib.request
        response = urllib.request.urlopen(f"{API_BASE}/", timeout=5)
        logger.info("✓ API server is running")
    except Exception as e:
        logger.error(f"✗ API server is not running: {e}")
        logger.error(f"Make sure the FastAPI server is running on {API_BASE}")
        return False
    
    tester = WebSocketRoutingTester()
    
    # Run tests
    await tester.test_connection()
    await tester.test_ping_pong()
    await tester.test_status_request()
    await tester.test_audio_chunk()
    await tester.test_validation_error()
    await tester.test_unknown_message_type()
    await tester.test_reset_buffer()
    await tester.test_rate_limiting()
    await tester.test_multiple_connections()
    
    # Print summary
    success = tester.print_summary()
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
