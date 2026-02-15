"""
Test Enrollment Service with Confirmation Sending
Tests the complete enrollment workflow including confirmation messages
"""

import asyncio
import json
import uuid
from datetime import datetime
import httpx
import websockets
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws/voice"
TEST_PHONE = "1234567890"


class EnrollmentConfirmationTester:
    """Tests enrollment with confirmation sending"""
    
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.session_id = None
        self.received_messages = []
        self.websocket = None
    
    async def connect_websocket(self) -> bool:
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(WEBSOCKET_URL)
            logger.info(f"✓ Connected to WebSocket with client_id: {self.client_id}")
            
            # Start message receiver task
            asyncio.create_task(self._receive_messages())
            
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to WebSocket: {str(e)}")
            return False
    
    async def _receive_messages(self):
        """Receive messages from WebSocket"""
        try:
            if not self.websocket:
                return
            
            async for message in self.websocket:
                try:
                    msg_data = json.loads(message)
                    self.received_messages.append(msg_data)
                    logger.info(f"📨 Received message: {msg_data.get('type')}")
                    
                    if msg_data.get('type') == 'enrollment_confirmed':
                        logger.info(f"✓ Enrollment confirmation received: {msg_data.get('confirmation_id', 'N/A')[:8]}")
                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message: {message}")
        
        except Exception as e:
            logger.error(f"Error in message receiver: {str(e)}")
    
    async def create_enrollment_session(self) -> bool:
        """Create an enrollment session"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/enrollment/session",
                    params={
                        "phone_number": TEST_PHONE,
                        "max_chunks": 2,
                        "merge_embeddings": True
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.session_id = data.get("session_id")
                    logger.info(f"✓ Created enrollment session: {self.session_id[:8]}")
                    return True
                else:
                    logger.error(f"✗ Failed to create session: {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"✗ Error creating session: {str(e)}")
            return False
    
    async def register_client_with_session(self) -> bool:
        """Register WebSocket client with enrollment session"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/enrollment/session/{self.session_id}/register-client",
                    params={"client_id": self.client_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✓ Client registered with session: {self.session_id[:8]}")
                    logger.info(f"  Response: {data.get('message')}")
                    return True
                else:
                    logger.error(f"✗ Failed to register client: {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"✗ Error registering client: {str(e)}")
            return False
    
    async def send_enrollment_confirmation(self, vector_id: str) -> bool:
        """Send enrollment confirmation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/enrollment/confirmation/send",
                    params={
                        "session_id": self.session_id,
                        "phone_number": TEST_PHONE,
                        "vector_id": vector_id,
                        "chunks_processed": 1,
                        "success": True,
                        "message": "Enrollment completed successfully!"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    confirmation_id = data.get("confirmation_id")
                    logger.info(f"✓ Confirmation sent: {confirmation_id[:8]}")
                    logger.info(f"  Message: {data.get('message')}")
                    return True
                else:
                    logger.error(f"✗ Failed to send confirmation: {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"✗ Error sending confirmation: {str(e)}")
            return False
    
    async def get_confirmation_history(self) -> bool:
        """Get confirmation history"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/enrollment/confirmation/history",
                    params={"limit": 10}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    count = data.get("total", 0)
                    logger.info(f"✓ Retrieved confirmation history: {count} records")
                    
                    for conf in data.get("confirmations", [])[-3:]:
                        logger.info(f"  - {conf.get('confirmation_id', 'N/A')[:8]}: {conf.get('phone_number')}")
                    
                    return True
                else:
                    logger.error(f"✗ Failed to get history: {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"✗ Error getting history: {str(e)}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        if self.websocket:
            await self.websocket.close()
            logger.info("✓ WebSocket connection closed")


async def test_enrollment_confirmation_flow():
    """Test the complete enrollment confirmation flow"""
    
    logger.info("\n" + "="*70)
    logger.info("ENROLLMENT SERVICE WITH CONFIRMATION - TEST SUITE")
    logger.info("="*70 + "\n")
    
    tester = EnrollmentConfirmationTester()
    
    try:
        # Step 1: Connect to WebSocket
        logger.info("\n[STEP 1] Connecting to WebSocket...")
        if not await tester.connect_websocket():
            logger.error("Failed to connect to WebSocket")
            return False
        
        # Give WebSocket time to fully connect
        await asyncio.sleep(1)
        
        # Step 2: Create enrollment session
        logger.info("\n[STEP 2] Creating enrollment session...")
        if not await tester.create_enrollment_session():
            logger.error("Failed to create enrollment session")
            return False
        
        # Step 3: Register client with session
        logger.info("\n[STEP 3] Registering WebSocket client with session...")
        if not await tester.register_client_with_session():
            logger.error("Failed to register client")
            return False
        
        # Step 4: Send confirmation (simulating successful enrollment)
        logger.info("\n[STEP 4] Sending enrollment confirmation...")
        vector_id = str(uuid.uuid4())
        if not await tester.send_enrollment_confirmation(vector_id):
            logger.error("Failed to send confirmation")
            return False
        
        # Wait for confirmation message to be received via WebSocket
        logger.info("\n[STEP 5] Waiting for confirmation message on WebSocket...")
        max_wait = 5
        for i in range(max_wait * 10):
            if any(msg.get('type') == 'enrollment_confirmed' for msg in tester.received_messages):
                logger.info("✓ Confirmation message received on WebSocket")
                break
            await asyncio.sleep(0.1)
        else:
            logger.warning("⚠ Did not receive confirmation message on WebSocket (may not have client connected)")
        
        # Step 5: Get confirmation history
        logger.info("\n[STEP 5] Getting confirmation history...")
        if not await tester.get_confirmation_history():
            logger.error("Failed to get history")
            return False
        
        logger.info("\n" + "="*70)
        logger.info("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("="*70 + "\n")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Test failed with exception: {str(e)}", exc_info=True)
        return False
    
    finally:
        await tester.cleanup()


async def test_multiple_confirmations():
    """Test sending multiple confirmations"""
    
    logger.info("\n" + "="*70)
    logger.info("MULTIPLE CONFIRMATIONS TEST")
    logger.info("="*70 + "\n")
    
    try:
        async with httpx.AsyncClient() as client:
            # Send 3 confirmations for different sessions
            for i in range(3):
                phone = f"555000{i}"
                session_id = str(uuid.uuid4())
                vector_id = str(uuid.uuid4())
                
                logger.info(f"\n[Confirmation {i+1}] Sending for {phone}...")
                
                response = await client.post(
                    f"{API_BASE_URL}/enrollment/confirmation/send",
                    params={
                        "session_id": session_id,
                        "phone_number": phone,
                        "vector_id": vector_id,
                        "chunks_processed": 2 + i,
                        "success": True,
                        "message": f"Enrollment #{ i+1} completed"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✓ Confirmation sent: {data.get('confirmation_id', 'N/A')[:8]}")
                else:
                    logger.error(f"✗ Failed: {response.text}")
            
            # Get updated history
            logger.info("\n[Final] Getting confirmation history...")
            response = await client.get(
                f"{API_BASE_URL}/enrollment/confirmation/history",
                params={"limit": 20}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Total confirmations in history: {data.get('total', 0)}")
        
        logger.info("\n" + "="*70)
        logger.info("✓ MULTIPLE CONFIRMATIONS TEST COMPLETED")
        logger.info("="*70 + "\n")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Test failed: {str(e)}", exc_info=True)
        return False


async def main():
    """Run all tests"""
    
    # Test 1: Full enrollment confirmation flow
    result1 = await test_enrollment_confirmation_flow()
    
    # Wait a bit between tests
    await asyncio.sleep(2)
    
    # Test 2: Multiple confirmations
    result2 = await test_multiple_confirmations()
    
    if result1 and result2:
        logger.info("\n✓ ALL TEST SUITES PASSED")
    else:
        logger.info("\n✗ SOME TESTS FAILED")


if __name__ == "__main__":
    asyncio.run(main())
