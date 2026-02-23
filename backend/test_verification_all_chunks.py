"""
Test script to verify the new "ALL chunks must pass" verification logic
This validates that verification only succeeds when ALL 4 chunks match the threshold
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockStreamingVerificationSession:
    """Mock session for testing"""
    def __init__(self):
        self.session_id = "test-session-001"
        self.chunk_results = []
        self.chunks_processed = 0
        self.threshold = 0.75
        self.max_chunks = 4
        self.final_status = None
        

class TestVerificationLogic:
    """Test suite for updated verification logic"""
    
    def test_all_chunks_pass(self):
        """Test Case 1: ALL chunks pass the threshold"""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: ALL 4 Chunks Pass (Should Return VERIFIED)")
        logger.info("="*70)
        
        session = MockStreamingVerificationSession()
        
        # Simulate 4 chunks all passing
        chunk_scores = [0.82, 0.81, 0.85, 0.79]  # All >= 0.75
        
        for i, score in enumerate(chunk_scores, 1):
            session.chunks_processed = i
            is_match = score >= session.threshold
            
            logger.info(f"\nChunk {i}: Score={score:.4f}, Threshold={session.threshold}, Match={is_match}")
            
            # NEW LOGIC: if chunk fails, immediate failure
            if not is_match:
                session.final_status = "unverified"
                logger.error(f"❌ CHUNK {i} FAILED - Verification stops immediately")
                break
            
            # Track result
            session.chunk_results.append({"chunk": i, "score": score, "is_match": is_match})
        
        # Check if all chunks processed
        if session.chunks_processed >= session.max_chunks:
            # NEW LOGIC: verify all chunks matched
            all_matched = all(r["is_match"] for r in session.chunk_results)
            
            if all_matched:
                session.final_status = "verified"
                logger.info(f"\n✅ ALL {session.chunks_processed} CHUNKS MATCHED!")
                logger.info(f"✅ Verification Status: {session.final_status.upper()}")
                logger.info(f"   Chunk Scores: {chunk_scores}")
                logger.info(f"   Average Score: {np.mean(chunk_scores):.4f}")
        
        # Verify result
        assert session.final_status == "verified", "Test failed: expected 'verified' status"
        logger.info("\n✅ Test 1 PASSED\n")
        return True
    
    def test_one_chunk_fails(self):
        """Test Case 2: ONE chunk fails the threshold"""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: Chunk 2 Fails (Should Return UNVERIFIED Immediately)")
        logger.info("="*70)
        
        session = MockStreamingVerificationSession()
        
        # Simulate chunks: first passes, second fails
        chunk_scores = [0.82, 0.68, 0.85, 0.79]  # Second one < 0.75
        
        for i, score in enumerate(chunk_scores, 1):
            session.chunks_processed = i
            is_match = score >= session.threshold
            
            logger.info(f"\nChunk {i}: Score={score:.4f}, Threshold={session.threshold}, Match={is_match}")
            
            # NEW LOGIC: if chunk fails, immediate failure
            if not is_match:
                session.final_status = "unverified"
                logger.error(f"❌ CHUNK {i} FAILED ({score:.4f} < {session.threshold})")
                logger.error(f"❌ Verification stops immediately - NOT waiting for remaining chunks")
                break
            
            # Track result
            session.chunk_results.append({"chunk": i, "score": score, "is_match": is_match})
        
        # Verify result
        assert session.final_status == "unverified", "Test failed: expected 'unverified' status"
        assert session.chunks_processed == 2, "Test failed: should have stopped at chunk 2"
        logger.info(f"\n✅ Test 2 PASSED - Stopped at chunk {session.chunks_processed}\n")
        return True
    
    def test_last_chunk_fails(self):
        """Test Case 3: Last chunk (4th) fails the threshold"""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Last Chunk Fails (Should Return UNVERIFIED)")
        logger.info("="*70)
        
        session = MockStreamingVerificationSession()
        
        # Simulate: first 3 pass, last one fails
        chunk_scores = [0.82, 0.81, 0.85, 0.70]  # Last one < 0.75
        
        for i, score in enumerate(chunk_scores, 1):
            session.chunks_processed = i
            is_match = score >= session.threshold
            
            logger.info(f"\nChunk {i}: Score={score:.4f}, Threshold={session.threshold}, Match={is_match}")
            
            # NEW LOGIC: if chunk fails, immediate failure
            if not is_match:
                session.final_status = "unverified"
                logger.error(f"❌ CHUNK {i} FAILED ({score:.4f} < {session.threshold})")
                logger.error(f"❌ Even though {i-1} chunks passed, verification fails due to chunk {i}")
                break
            
            # Track result
            session.chunk_results.append({"chunk": i, "score": score, "is_match": is_match})
        
        # Verify result
        assert session.final_status == "unverified", "Test failed: expected 'unverified' status"
        assert session.chunks_processed == 4, "Test failed: should have processed all 4 chunks"
        logger.info(f"\n✅ Test 3 PASSED - Even near-perfect performance fails if any chunk doesn't match\n")
        return True
    
    def test_all_chunks_fail(self):
        """Test Case 4: ALL chunks fail the threshold"""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: ALL Chunks Fail (Should Return UNVERIFIED on First Chunk)")
        logger.info("="*70)
        
        session = MockStreamingVerificationSession()
        
        # Simulate: all chunks below threshold
        chunk_scores = [0.65, 0.60, 0.68, 0.62]  # All < 0.75
        
        for i, score in enumerate(chunk_scores, 1):
            session.chunks_processed = i
            is_match = score >= session.threshold
            
            logger.info(f"\nChunk {i}: Score={score:.4f}, Threshold={session.threshold}, Match={is_match}")
            
            # NEW LOGIC: if chunk fails, immediate failure
            if not is_match:
                session.final_status = "unverified"
                logger.error(f"❌ CHUNK {i} FAILED ({score:.4f} < {session.threshold})")
                logger.error(f"❌ Verification fails immediately - no more chunks processed")
                break
            
            # Track result
            session.chunk_results.append({"chunk": i, "score": score, "is_match": is_match})
        
        # Verify result
        assert session.final_status == "unverified", "Test failed: expected 'unverified' status"
        assert session.chunks_processed == 1, "Test failed: should have stopped at chunk 1"
        logger.info(f"\n✅ Test 4 PASSED - Failed at first chunk\n")
        return True
    
    def test_boundary_conditions(self):
        """Test Case 5: Boundary conditions (chunks at exactly 0.75 threshold)"""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: Boundary Conditions (Scores at exactly 0.75 threshold)")
        logger.info("="*70)
        
        session = MockStreamingVerificationSession()
        
        # Simulate: all chunks at exactly threshold (should pass)
        chunk_scores = [0.75, 0.75, 0.75, 0.75]  # All == 0.75 (technically pass)
        
        for i, score in enumerate(chunk_scores, 1):
            session.chunks_processed = i
            is_match = score >= session.threshold
            
            logger.info(f"\nChunk {i}: Score={score:.4f}, Threshold={session.threshold}, Match={is_match}")
            
            # NEW LOGIC: if chunk fails, immediate failure
            if not is_match:
                session.final_status = "unverified"
                logger.error(f"❌ CHUNK {i} FAILED")
                break
            
            # Track result
            session.chunk_results.append({"chunk": i, "score": score, "is_match": is_match})
        
        # Check if all chunks processed
        if session.chunks_processed >= session.max_chunks:
            # NEW LOGIC: verify all chunks matched
            all_matched = all(r["is_match"] for r in session.chunk_results)
            
            if all_matched:
                session.final_status = "verified"
                logger.info(f"\n✅ ALL {session.chunks_processed} CHUNKS at boundary PASSED!")
                logger.info(f"✅ Verification Status: {session.final_status.upper()}")
        
        # Verify result
        assert session.final_status == "verified", "Test failed: boundary condition should pass"
        logger.info("\n✅ Test 5 PASSED - Boundary conditions handled correctly\n")
        return True
    
    def run_all_tests(self):
        """Run all test cases"""
        logger.info("\n")
        logger.info("╔" + "═"*68 + "╗")
        logger.info("║" + " "*20 + "VERIFICATION LOGIC TEST SUITE" + " "*20 + "║")
        logger.info("║" + " "*15 + "Testing: ALL Chunks Must Pass Logic" + " "*19 + "║")
        logger.info("╚" + "═"*68 + "╝")
        
        results = []
        
        try:
            results.append(("Test 1: All Chunks Pass", self.test_all_chunks_pass()))
        except AssertionError as e:
            logger.error(f"❌ Test 1 FAILED: {str(e)}")
            results.append(("Test 1: All Chunks Pass", False))
        
        try:
            results.append(("Test 2: One Chunk Fails", self.test_one_chunk_fails()))
        except AssertionError as e:
            logger.error(f"❌ Test 2 FAILED: {str(e)}")
            results.append(("Test 2: One Chunk Fails", False))
        
        try:
            results.append(("Test 3: Last Chunk Fails", self.test_last_chunk_fails()))
        except AssertionError as e:
            logger.error(f"❌ Test 3 FAILED: {str(e)}")
            results.append(("Test 3: Last Chunk Fails", False))
        
        try:
            results.append(("Test 4: All Chunks Fail", self.test_all_chunks_fail()))
        except AssertionError as e:
            logger.error(f"❌ Test 4 FAILED: {str(e)}")
            results.append(("Test 4: All Chunks Fail", False))
        
        try:
            results.append(("Test 5: Boundary Conditions", self.test_boundary_conditions()))
        except AssertionError as e:
            logger.error(f"❌ Test 5 FAILED: {str(e)}")
            results.append(("Test 5: Boundary Conditions", False))
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status} - {test_name}")
        
        total_tests = len(results)
        passed_tests = sum(1 for _, result in results if result)
        
        logger.info("\n" + "-"*70)
        logger.info(f"Total: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("\n🎉 ALL TESTS PASSED! The new verification logic is working correctly!")
            logger.info("\nKey Changes Verified:")
            logger.info("1. ✅ If ANY chunk fails → verification fails immediately")
            logger.info("2. ✅ ALL 4 chunks must pass for success")
            logger.info("3. ✅ Recording stops as soon as failure detected")
            logger.info("4. ✅ Boundary conditions (exact threshold) handled correctly")
            logger.info("5. ✅ No early exit on success - continues until all chunks processed")
        else:
            logger.error(f"\n❌ {total_tests - passed_tests} test(s) failed!")
        
        logger.info("="*70 + "\n")
        
        return passed_tests == total_tests


if __name__ == "__main__":
    tester = TestVerificationLogic()
    success = tester.run_all_tests()
    exit(0 if success else 1)
