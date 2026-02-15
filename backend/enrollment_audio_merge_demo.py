"""
Enrollment Service - Audio Merging and Embedding Generation Demo
Demonstrates the new audio merging capabilities for enrollment sessions
"""

import numpy as np
import logging
from datetime import datetime
from enrollment_service import (
    create_enrollment_session,
    EnrollmentSessionConfig,
    MergeMode,
    merge_audio_chunks,
    generate_embedding_from_merged_audio,
    merge_and_generate_embedding,
    get_enrollment_session
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_audio(duration_seconds: float, sample_rate: int = 16000) -> np.ndarray:
    """Generate synthetic audio sample for testing"""
    t = np.linspace(0, duration_seconds, int(duration_seconds * sample_rate))
    # Generate a mix of frequencies (simulating voice)
    frequency1 = 200  # Hz
    frequency2 = 400  # Hz
    audio = 0.3 * np.sin(2 * np.pi * frequency1 * t) + 0.2 * np.sin(2 * np.pi * frequency2 * t)
    # Add some noise
    audio += 0.05 * np.random.randn(len(audio))
    return audio.astype(np.float32)


def demo_separate_embedding_per_chunk():
    """Demo: Generate separate embedding for each chunk, then merge embeddings"""
    print("\n" + "="*70)
    print("DEMO 1: Separate Embeddings Strategy")
    print("="*70)
    print("This approach:")
    print("  1. Collects multiple audio chunks")
    print("  2. Generates an embedding for each chunk")
    print("  3. Merges the embeddings using averaging")
    print("="*70 + "\n")
    
    # Create session with separate embedding strategy (default)
    config = EnrollmentSessionConfig(
        max_chunks=3,
        min_chunks_required=2,
        merge_embeddings=True,  # Merge embeddings
        merge_mode=MergeMode.OVERLAP,
        merge_audio=False,  # Do NOT merge audio chunks
        auto_process=True
    )
    
    session = create_enrollment_session("+1-555-0001", config)
    logger.info(f"Created session: {session.session_id[:16]}...")
    
    # Add multiple audio chunks
    for i in range(3):
        audio = generate_sample_audio(duration_seconds=2.0)
        chunk = session.add_chunk(
            audio,
            duration_seconds=2.0,
            quality_score=0.95
        )
        logger.info(f"  Added chunk {i+1}: {chunk.chunk_id[:16]}...")
    
    # Finalize - this will use embedding merge strategy
    success, message, embedding = session.finalize_enrollment()
    
    print(f"\n✓ Result: {message}")
    print(f"  - Chunks collected: {len(session.chunks)}")
    print(f"  - Embeddings generated: {len(session.embeddings)}")
    print(f"  - Final embedding shape: {session.merged_embedding.shape if session.merged_embedding is not None else 'None'}")
    print(f"  - Strategy used: Embedding merging (averaged {len(session.embeddings)} embeddings)")


def demo_merged_audio_single_embedding():
    """Demo: Merge audio chunks, then generate single embedding"""
    print("\n" + "="*70)
    print("DEMO 2: Merged Audio Strategy")
    print("="*70)
    print("This approach:")
    print("  1. Collects multiple audio chunks")
    print("  2. Merges audio chunks into one continuous audio file")
    print("  3. Generates a single embedding from merged audio")
    print("="*70 + "\n")
    
    # Create session with audio merge strategy
    config = EnrollmentSessionConfig(
        max_chunks=3,
        min_chunks_required=2,
        merge_embeddings=False,  # Do NOT merge embeddings
        merge_audio=True,  # Merge audio chunks
        audio_merge_mode=MergeMode.CROSSFADE,
        audio_merge_crossfade_ms=100.0,
        auto_process=False  # Don't auto-generate per-chunk embeddings
    )
    
    session = create_enrollment_session("+1-555-0002", config)
    logger.info(f"Created session: {session.session_id[:16]}...")
    
    # Add multiple audio chunks
    for i in range(3):
        audio = generate_sample_audio(duration_seconds=1.5)
        chunk = session.add_chunk(
            audio,
            duration_seconds=1.5,
            quality_score=0.92
        )
        logger.info(f"  Added chunk {i+1}: {chunk.chunk_id[:16]}...")
    
    # Use merged audio strategy
    logger.info("\nPerforming merge and embedding generation workflow...")
    success, message, embedding = merge_and_generate_embedding(session.session_id)
    
    if success:
        # Store the result
        session = get_enrollment_session(session.session_id)
        session.merged_audio_embedding = embedding
        session.finalize_enrollment()
        
        print(f"\n✓ Result: {message}")
        print(f"  - Chunks collected: {len(session.chunks)}")
        print(f"  - Total chunk duration: {sum(c.duration_seconds for c in session.chunks):.2f}s")
        print(f"  - Merged audio duration: {len(session.merged_audio) / 16000:.2f}s" if session.merged_audio is not None else "  - Merged audio: None")
        print(f"  - Final embedding shape: {session.merged_audio_embedding.shape if session.merged_audio_embedding is not None else 'None'}")
        print(f"  - Strategy used: Audio merging (merged {len(session.chunks)} chunks)")
    else:
        print(f"\n✗ Failed: {message}")


def demo_manual_audio_merge_workflow():
    """Demo: Manual step-by-step audio merging workflow"""
    print("\n" + "="*70)
    print("DEMO 3: Manual Step-by-Step Workflow")
    print("="*70)
    print("This approach shows fine-grained control:")
    print("  1. Create session and collect chunks")
    print("  2. Manually merge audio with custom parameters")
    print("  3. Generate embedding from merged audio")
    print("="*70 + "\n")
    
    # Create session
    config = EnrollmentSessionConfig(
        max_chunks=4,
        min_chunks_required=2,
        merge_audio=False,  # We'll do it manually
    )
    
    session = create_enrollment_session("+1-555-0003", config)
    logger.info(f"Created session: {session.session_id[:16]}...")
    
    # Add chunks
    for i in range(4):
        audio = generate_sample_audio(duration_seconds=1.0)
        chunk = session.add_chunk(
            audio,
            duration_seconds=1.0,
            quality_score=0.88 + (i * 0.02)
        )
        logger.info(f"  Added chunk {i+1}: duration={chunk.duration_seconds:.2f}s, quality={chunk.quality_score:.2f}")
    
    # Step 1: Manually merge audio
    logger.info("\nStep 1: Merging audio chunks...")
    success, message, merged_audio = merge_audio_chunks(session.session_id)
    print(f"  ✓ {message}")
    print(f"    Merged audio shape: {merged_audio.shape if merged_audio is not None else 'None'}")
    
    # Step 2: Generate embedding from merged audio
    logger.info("\nStep 2: Generating embedding from merged audio...")
    success, message, embedding = generate_embedding_from_merged_audio(session.session_id)
    print(f"  ✓ {message}")
    print(f"    Embedding shape: {embedding.shape if embedding is not None else 'None'}")
    
    # Get summary
    session = get_enrollment_session(session.session_id)
    summary = session.get_summary()
    
    print(f"\nFinal Summary:")
    print(f"  - Status: {summary['status']}")
    print(f"  - Chunks: {summary['chunks_collected']}")
    print(f"  - Merged audio: {summary['has_merged_audio']}")
    print(f"  - Merged audio duration: {summary['merged_audio_duration_seconds']:.2f}s" if summary['merged_audio_duration_seconds'] else "  - Merged audio duration: None")


def demo_comparison():
    """Demo: Compare the two strategies"""
    print("\n" + "="*70)
    print("DEMO 4: Strategy Comparison")
    print("="*70)
    print("\nStrategy 1: Separate Embeddings (Default)")
    print("  Pros:")
    print("    - More robust to variations in individual chunks")
    print("    - Better for rapid enrollment (quick feedback per chunk)")
    print("  Cons:")
    print("    - Multiple embeddings need to be merged")
    print("    - Slightly more computation")
    print("\nStrategy 2: Merged Audio (New)")
    print("  Pros:")
    print("    - Single clean embedding from continuous audio")
    print("    - More natural speech representation")
    print("    - Better for capturing speech characteristics")
    print("  Cons:")
    print("    - Depends on quality of audio merging")
    print("    - Single bad chunk can affect entire result")
    print("\nStrategy 3: Hybrid (Audio Merge + Single Embedding)")
    print("  Pros:")
    print("    - Combines benefits of both approaches")
    print("    - Can customize merge parameters")
    print("  Example Config:")
    print("    - merge_audio=True")
    print("    - audio_merge_mode=MergeMode.CROSSFADE")
    print("    - merge_embeddings=False")
    print("="*70)


if __name__ == "__main__":
    logger.info("Starting Enrollment Service Audio Merge Demonstration")
    
    try:
        # Run demos
        demo_separate_embedding_per_chunk()
        demo_merged_audio_single_embedding()
        demo_manual_audio_merge_workflow()
        demo_comparison()
        
        logger.info("\n✓ All demos completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}", exc_info=True)
