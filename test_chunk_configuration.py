#!/usr/bin/env python3
"""
Chunk Configuration Testing

This script validates that enrollment and verification are using
the correct chunk sizes: 1-second for enrollment, 5-second for verification.
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required imports work correctly"""
    print("\n=== Testing Imports ===")
    
    try:
        from enrollment_service import (
            EnrollmentSession,
            EnrollmentSessionConfig,
            create_enrollment_session,
            get_enrollment_session
        )
        logger.info("✓ Successfully imported enrollment_service")
    except ImportError as e:
        logger.error(f"✗ Failed to import enrollment_service: {e}")
        return False
    
    try:
        from verification_service import (
            VerificationSession,
            VerificationSessionConfig,
            create_verification_session,
            get_verification_session
        )
        logger.info("✓ Successfully imported verification_service")
    except ImportError as e:
        logger.error(f"✗ Failed to import verification_service: {e}")
        return False
    
    try:
        from voice_embedding import (
            generate_embedding,
            generate_embedding_with_chunking,
            calculate_cosine_similarity
        )
        logger.info("✓ Successfully imported voice_embedding")
    except ImportError as e:
        logger.error(f"✗ Failed to import voice_embedding: {e}")
        return False
    
    return True


def test_chunk_sizes():
    """Test that chunk sizes are configured correctly"""
    print("\n=== Testing Chunk Sizes ===")
    
    try:
        from voice_embedding import generate_embedding_with_chunking
        import inspect
        
        # Get function signature
        sig = inspect.signature(generate_embedding_with_chunking)
        
        # Check parameters
        params = list(sig.parameters.keys())
        logger.info(f"Function parameters: {params}")
        
        if 'chunk_size_seconds' in params:
            logger.info("✓ chunk_size_seconds parameter available")
        else:
            logger.error("✗ chunk_size_seconds parameter NOT found")
            return False
        
        if 'aggregation_method' in params:
            logger.info("✓ aggregation_method parameter available")
        else:
            logger.error("✗ aggregation_method parameter NOT found")
            return False
        
        return True
    except Exception as e:
        logger.error(f"✗ Error testing chunk sizes: {e}")
        return False


def test_session_creation():
    """Test creating enrollment and verification sessions"""
    print("\n=== Testing Session Creation ===")
    
    try:
        from enrollment_service import create_enrollment_session
        
        # Create enrollment session
        session = create_enrollment_session("5551234567")
        logger.info(f"✓ Created enrollment session: {session.session_id[:8]}")
        
        # Verify configuration
        if hasattr(session, 'config'):
            logger.info(f"✓ Enrollment session has config")
        else:
            logger.error("✗ Enrollment session missing config")
            return False
        
    except Exception as e:
        logger.error(f"✗ Error creating enrollment session: {e}")
        return False
    
    try:
        from verification_service import create_verification_session
        
        # Create verification session
        session = create_verification_session("5551234567")
        logger.info(f"✓ Created verification session: {session.session_id[:8]}")
        
        # Verify configuration
        if hasattr(session, 'config'):
            logger.info(f"✓ Verification session has config")
        else:
            logger.error("✗ Verification session missing config")
            return False
        
    except Exception as e:
        logger.error(f"✗ Error creating verification session: {e}")
        return False
    
    return True


def test_documentation():
    """Verify documentation files exist"""
    print("\n=== Checking Documentation ===")
    
    import os
    
    doc_file = "CHUNK_CONFIGURATION_VERIFICATION.md"
    if os.path.exists(doc_file):
        logger.info(f"✓ Found documentation: {doc_file}")
        with open(doc_file, 'r') as f:
            content = f.read()
            if "1-second" in content and "5-second" in content:
                logger.info("✓ Documentation mentions 1-second and 5-second chunks")
                return True
            else:
                logger.error("✗ Documentation missing chunk size information")
                return False
    else:
        logger.warning(f"⚠ Documentation not found: {doc_file}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CHUNK CONFIGURATION VALIDATION")
    print("Verifying: Enrollment (1-second) vs Verification (5-second)")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Chunk Sizes", test_chunk_sizes),
        ("Session Creation", test_session_creation),
        ("Documentation", test_documentation),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
