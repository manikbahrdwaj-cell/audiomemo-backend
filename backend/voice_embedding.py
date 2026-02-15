"""
Voice Embedding Module using ECAPA-TDNN
Generates 192-dimensional speaker embeddings from audio files
"""

import torch
import torchaudio
import numpy as np
import tempfile
import os
import time
from io import BytesIO
import logging
from pathlib import Path
import shutil
import stat
import platform
from scipy.spatial.distance import cosine
from scipy.spatial import distance
from audio_chunking import ChunkProcessor, ChunkConfig

# Patch os.symlink on Windows to use copy instead (avoids WinError 1314)
if platform.system() == "Windows":
    _original_symlink = os.symlink
    
    def _patched_symlink(src, dst, target_is_directory=False):
        """On Windows, copy files instead of creating symlinks"""
        try:
            # Try the original symlink first (might work in dev mode or with proper permissions)
            return _original_symlink(src, dst, target_is_directory=target_is_directory)
        except (OSError, PermissionError) as e:
            if "1314" in str(e) or "privilege" in str(e).lower():
                # Privilege error - use copy instead
                try:
                    src_path = Path(src)
                    dst_path = Path(dst)
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if src_path.is_dir() and target_is_directory:
                        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_path, dst_path)
                    return None
                except Exception as copy_err:
                    # If copy also fails, raise the original error
                    raise e from copy_err
            else:
                raise
    
    os.symlink = _patched_symlink

# Patch huggingface_hub compatibility before importing speechbrain
from huggingface_hub import hf_hub_download as _original_hf_hub_download
import functools

@functools.wraps(_original_hf_hub_download)
def _patched_hf_hub_download(*args, **kwargs):
    """Wrapper to handle both use_auth_token and token parameters"""
    if 'use_auth_token' in kwargs:
        kwargs['token'] = kwargs.pop('use_auth_token')
    
    # WORKAROUND: If trying to download custom.py, serve it from local directory
    if len(args) > 1 and args[1] == "custom.py":
        # Return local custom.py path instead of downloading
        backend_dir = Path(__file__).parent
        local_custom_py = backend_dir.parent / "pretrained_models" / "spkrec-ecapa-voxceleb" / "custom.py"
        if local_custom_py.exists():
            # Return the local path
            return str(local_custom_py)
    
    return _original_hf_hub_download(*args, **kwargs)

import huggingface_hub
huggingface_hub.hf_hub_download = _patched_hf_hub_download

# Patch torchaudio compatibility issues before importing speechbrain
if not hasattr(torchaudio, 'set_audio_backend'):
    def _dummy_set_audio_backend(backend):
        """Dummy function to satisfy speechbrain compatibility"""
        pass
    torchaudio.set_audio_backend = _dummy_set_audio_backend

if not hasattr(torchaudio, 'list_audio_backends'):
    def _dummy_list_audio_backends():
        """Dummy function to satisfy speechbrain compatibility"""
        return ['soundfile']
    torchaudio.list_audio_backends = _dummy_list_audio_backends

if not hasattr(torchaudio, 'get_audio_backend'):
    def _dummy_get_audio_backend():
        """Dummy function to satisfy speechbrain compatibility"""
        return 'soundfile'
    torchaudio.get_audio_backend = _dummy_get_audio_backend

# Now import speechbrain
from speechbrain.pretrained import EncoderClassifier

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model = None

def _copy_model_files_locally(cache_dir: Path, model_dir: Path) -> None:
    """
    Copy model files from HuggingFace cache to local directory with robust Windows support
    This avoids symlink issues and permission errors on Windows
    """
    if not cache_dir.exists():
        logger.warning(f"Cache directory not found: {cache_dir}")
        return
    
    try:
        logger.info(f"Copying model files from cache to {model_dir}")
        files_copied = 0
        files_skipped = 0
        
        for item in cache_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(cache_dir)
                target_path = model_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Skip if target already exists and has same size
                if target_path.exists() and target_path.stat().st_size == item.stat().st_size:
                    files_skipped += 1
                    continue
                
                # Attempt to copy with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Remove target if it exists and is locked
                        if target_path.exists():
                            try:
                                # Change permissions to allow overwrite
                                os.chmod(target_path, stat.S_IWRITE | stat.S_IREAD)
                            except:
                                pass
                            try:
                                target_path.unlink()
                            except:
                                pass
                        
                        # Copy with metadata preservation
                        shutil.copy2(item, target_path)
                        files_copied += 1
                        break
                    except PermissionError as e:
                        if attempt < max_retries - 1:
                            logger.debug(f"Permission denied copying {item.name}, retrying... ({attempt + 1}/{max_retries})")
                            time.sleep(0.2 * (attempt + 1))
                        else:
                            logger.debug(f"Could not copy {item.name} after {max_retries} attempts: {e}")
                            files_skipped += 1
                    except Exception as e:
                        logger.debug(f"Could not copy {item.name}: {e}")
                        files_skipped += 1
                        break
        
        logger.info(f"Copied {files_copied} files, skipped {files_skipped} files")
    except Exception as e:
        logger.warning(f"Could not copy cache files: {e}")

def _cleanup_model_directory(model_dir: Path) -> None:
    """
    Clean up problematic files in model directory (symlinks, locked files)
    """
    if not model_dir.exists():
        return
    
    try:
        for item in model_dir.rglob("*"):
            try:
                # Remove symlinks which can cause issues on Windows
                if item.is_symlink():
                    logger.debug(f"Removing symlink: {item}")
                    item.unlink()
                # Try to fix permissions on files
                elif item.is_file():
                    try:
                        os.chmod(item, stat.S_IWRITE | stat.S_IREAD)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Could not clean {item.name}: {e}")
    except Exception as e:
        logger.debug(f"Cleanup error: {e}")

def _setup_huggingface_for_windows():
    """
    Configure HuggingFace to work on Windows without symlinks or special privileges
    Prevents WinError 1314 (insufficient privileges)
    """
    # Disable symlink creation which fails on Windows without admin privileges
    os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
    os.environ['HF_HUB_SYMLINK_MODE'] = 'copy'
    
    # Prevent checkpoint file renaming issues (copy instead)
    os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '1'
    
    # Use file system operations that don't require special privileges
    os.environ['HF_DATASETS_OFFLINE'] = '0'
    
    # Disable analytics
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    
    # Disable progress bar which can cause threading issues on Windows
    os.environ['HF_DATASETS_DISABLE_PROGRESS_BARS'] = '1'
    
    logger.info("HuggingFace configured for Windows compatibility (symlinks disabled, copy mode enabled)")

def _ensure_custom_py_exists(model_dir: Path) -> None:
    """
    Ensure custom.py exists in the model directory
    This file is required by speechbrain but can cause permission issues on Windows
    """
    custom_py_path = model_dir / "custom.py"
    
    if not custom_py_path.exists():
        logger.info("Creating minimal custom.py as fallback...")
        minimal_custom = '''"""Minimal custom.py for offline use"""
def custom_model(*args, **kwargs):
    pass
'''
        custom_py_path.write_text(minimal_custom)
        logger.info(f"✓ Minimal custom.py created at {custom_py_path}")

def get_model():
    """Load and cache the ECAPA-TDNN model with robust Windows support"""
    global _model
    if _model is None:
        logger.info("Loading ECAPA-TDNN model...")
        
        # Configure HuggingFace for Windows FIRST
        _setup_huggingface_for_windows()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        backend_dir = Path(__file__).parent
        model_dir = backend_dir / "pretrained_models" / "spkrec-ecapa-voxceleb"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Attempting to load model from: {model_dir}")
        
        # Ensure custom.py exists
        _ensure_custom_py_exists(model_dir)
        
        # Clean up any problematic files
        _cleanup_model_directory(model_dir)
        
        # Pre-copy model files from cache to avoid symlink issues
        try:
            hf_cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--speechbrain--spkrec-ecapa-voxceleb"
            snapshots_dir = hf_cache / "snapshots"
            
            if snapshots_dir.exists():
                snapshot_dirs = sorted(snapshots_dir.glob("*"), reverse=True)
                if snapshot_dirs:
                    latest_snapshot = snapshot_dirs[0]
                    logger.info(f"Pre-copying files from cache snapshot: {latest_snapshot}")
                    _copy_model_files_locally(latest_snapshot, model_dir)
                    time.sleep(0.5)  # Small delay to ensure file system is ready
        except Exception as e:
            logger.warning(f"Could not pre-copy model files: {e}")
        
        # Load the model
        try:
            logger.info("Attempting to load model...")
            _model = EncoderClassifier.from_hparams(
                source=str(model_dir),
                savedir=str(model_dir)
            )
            logger.info("✓ ECAPA-TDNN model loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load ECAPA-TDNN model. Error: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Model directory contents: {list(model_dir.glob('*')) if model_dir.exists() else 'Directory does not exist'}")
            raise RuntimeError(error_msg)
    
    return _model

def preprocess_audio(audio_bytes: bytes) -> torch.Tensor:
    """
    Preprocess audio bytes for the model
    - Loads WAV file
    - Resamples to 16kHz if necessary
    - Converts to mono
    - Normalizes amplitude
    """
    # Save bytes to temp file for loading
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name
    
    try:
        # Load audio - try different backends
        try:
            # Try soundfile first (safer)
            waveform, sample_rate = torchaudio.load(tmp_path, backend='soundfile')
        except:
            # Fallback to default backend
            try:
                waveform, sample_rate = torchaudio.load(tmp_path)
            except:
                # Last resort: use scipy
                from scipy import signal
                from scipy.io import wavfile
                
                sample_rate, audio_data = wavfile.read(tmp_path)
                waveform = torch.from_numpy(audio_data.astype(np.float32))
                if len(waveform.shape) == 1:
                    waveform = waveform.unsqueeze(0)
                else:
                    waveform = waveform.t()
        
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Resample to 16kHz if necessary
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate, 
                new_freq=16000
            )
            waveform = resampler(waveform)
        
        # Normalize
        max_val = torch.max(torch.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val
        
        return waveform.squeeze(0)  # Remove batch dimension
        
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

def generate_embedding(audio_bytes: bytes) -> np.ndarray:
    """
    Generate a 192-dimensional voice embedding from audio bytes
    
    Args:
        audio_bytes: WAV file bytes (16kHz mono preferred)
        
    Returns:
        numpy array of shape (192,) containing the speaker embedding
    """
    model = get_model()
    
    # Preprocess audio
    waveform = preprocess_audio(audio_bytes)
    
    # Generate embedding
    with torch.no_grad():
        embedding = model.encode_batch(waveform.unsqueeze(0))
        embedding = embedding.squeeze().cpu().numpy()
    
    # Ensure we have a 192-dimensional vector
    assert embedding.shape == (192,), f"Expected 192-dim embedding, got {embedding.shape}"
    
    return embedding

def calculate_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings using scipy
    
    Cosine similarity measures the cosine of the angle between two vectors,
    providing a metric between -1 and 1 (normalized to 0-1).
    
    Uses scipy.spatial.distance.cosine for optimal numerical stability.
    
    Args:
        embedding1: First embedding vector (e.g., 192-dimensional)
        embedding2: Second embedding vector (e.g., 192-dimensional)
        
    Returns:
        Cosine similarity score between 0 and 1
        1.0 = identical embeddings
        0.5 = orthogonal embeddings
        0.0 = opposite embeddings
        
    Example:
        >>> emb1 = np.array([1, 0, 0])
        >>> emb2 = np.array([1, 0, 0])
        >>> similarity = calculate_cosine_similarity(emb1, emb2)
        >>> print(similarity)  # 1.0
        
        >>> emb3 = np.array([-1, 0, 0])
        >>> similarity = calculate_cosine_similarity(emb1, emb3)
        >>> print(similarity)  # 0.0
    """
    try:
        # Validate inputs
        embedding1 = np.asarray(embedding1, dtype=np.float32)
        embedding2 = np.asarray(embedding2, dtype=np.float32)
        
        if embedding1.size == 0 or embedding2.size == 0:
            return 0.0
        
        # Calculate cosine distance using scipy (returns distance, not similarity)
        # Cosine distance = 1 - cosine_similarity, so we subtract from 1
        cosine_distance = cosine(embedding1, embedding2)
        
        # Convert distance to similarity ([-1, 1] -> [0, 1])
        # scipy's cosine returns a distance in [0, 2] where:
        # 0 = identical, 1 = orthogonal, 2 = opposite
        # We want similarity in [0, 1] where:
        # 1 = identical, 0.5 = orthogonal, 0 = opposite
        similarity = 1.0 - cosine_distance
        similarity = (similarity + 1.0) / 2.0  # Normalize to [0, 1]
        
        return float(np.clip(similarity, 0.0, 1.0))
        
    except Exception as e:
        logger.warning(f"Error calculating cosine similarity: {e}")
        return 0.0

def generate_embedding_with_chunking(
    audio_bytes: bytes,
    chunk_size_seconds: float = 1.0,
    overlap_ratio: float = 0.2,
    aggregation_method: str = 'mean',
    apply_windowing: bool = True,
    normalize_chunks: bool = True
) -> np.ndarray:
    """
    Generate voice embedding with audio chunking support
    
    Useful for longer audio files (> 10 seconds) to improve stability
    and handle memory constraints.
    
    Args:
        audio_bytes: WAV file bytes
        chunk_size_seconds: Size of each chunk in seconds (default 1.0)
        overlap_ratio: Overlap between chunks 0-1 (default 0.2)
        aggregation_method: How to combine chunk embeddings:
            - 'mean': Simple average
            - 'max': Maximum across chunks
            - 'weighted_linear': Linear increasing weights
            - 'weighted_inverse': Linear decreasing weights
            - 'weighted_normalized': Higher weights on middle chunks
            - 'energy_weighted': Weight by RMS energy
        apply_windowing: Apply Hann window to chunks
        normalize_chunks: Normalize each chunk separately
        
    Returns:
        numpy array of shape (192,) containing the speaker embedding
        
    Example:
        >>> embedding = generate_embedding_with_chunking(
        ...     audio_bytes,
        ...     chunk_size_seconds=2.0,
        ...     aggregation_method='energy_weighted'
        ... )
    """
    # Validate parameters
    if not 0 < chunk_size_seconds <= 10:
        raise ValueError("chunk_size_seconds must be between 0 and 10")
    if not 0 <= overlap_ratio < 1:
        raise ValueError("overlap_ratio must be between 0 and 1")
    
    aggregation_methods = [
        'mean', 'max', 'weighted_linear', 'weighted_inverse',
        'weighted_normalized', 'energy_weighted'
    ]
    if aggregation_method not in aggregation_methods:
        raise ValueError(f"aggregation_method must be one of {aggregation_methods}")
    
    # Preprocess audio
    waveform = preprocess_audio(audio_bytes)
    
    # Create chunk configuration
    chunk_size_samples = int(chunk_size_seconds * 16000)
    config = ChunkConfig(
        chunk_size=chunk_size_samples,
        overlap_ratio=overlap_ratio,
        sample_rate=16000
    )
    
    processor = ChunkProcessor(config)
    
    # Function to generate embedding for a single chunk
    def embed_chunk(chunk: np.ndarray) -> np.ndarray:
        model = get_model()
        chunk_tensor = torch.from_numpy(chunk).float().unsqueeze(0)
        with torch.no_grad():
            embedding = model.encode_batch(chunk_tensor)
            embedding = embedding.squeeze().cpu().numpy()
        return embedding
    
    # Process chunks and aggregate embeddings
    try:
        embedding, metadata = processor.process_audio(
            audio=waveform,
            embedding_func=embed_chunk,
            aggregation_method=aggregation_method,
            apply_window=apply_windowing,
            window_type='hann',
            normalize=normalize_chunks
        )
        
        logger.info(
            f"Generated chunked embedding from {metadata['n_chunks']} chunks "
            f"({metadata['total_duration_ms']:.1f}ms total, "
            f"aggregation={aggregation_method})"
        )
        
        # Ensure we have a 192-dimensional vector
        assert embedding.shape == (192,), f"Expected 192-dim embedding, got {embedding.shape}"
        
        return embedding
        
    except Exception as e:
        logger.error(f"Error in chunked embedding generation: {e}")
        # Fallback to single embedding if chunking fails
        logger.warning("Falling back to non-chunked embedding")
        return generate_embedding(audio_bytes)

def get_embedding_with_auto_chunking(
    audio_bytes: bytes,
    auto_chunk_threshold_seconds: float = 10.0,
    **chunking_kwargs
) -> np.ndarray:
    """
    Automatically decide whether to use chunking based on audio length
    
    Args:
        audio_bytes: WAV file bytes
        auto_chunk_threshold_seconds: Use chunking if audio > this length
        **chunking_kwargs: Additional arguments passed to generate_embedding_with_chunking
        
    Returns:
        numpy array of shape (192,) containing the speaker embedding
        
    Example:
        >>> embedding = get_embedding_with_auto_chunking(audio_bytes)
    """
    # Get audio duration
    waveform = preprocess_audio(audio_bytes)
    duration_seconds = len(waveform) / 16000
    
    if duration_seconds > auto_chunk_threshold_seconds:
        logger.info(
            f"Audio duration {duration_seconds:.1f}s exceeds threshold "
            f"{auto_chunk_threshold_seconds}s, using chunking"
        )
        return generate_embedding_with_chunking(audio_bytes, **chunking_kwargs)
    else:
        logger.info(
            f"Audio duration {duration_seconds:.1f}s within threshold, "
            f"using standard embedding"
        )
        return generate_embedding(audio_bytes)

def compare_embeddings_with_chunks(
    audio_bytes: bytes,
    aggregation_methods: list = None
) -> dict:
    """
    Compare embeddings generated with different aggregation methods
    Useful for testing and selecting optimal chunking strategy
    
    Args:
        audio_bytes: WAV file bytes
        aggregation_methods: List of methods to try (default: all methods)
        
    Returns:
        Dictionary mapping method names to embeddings
        
    Example:
        >>> embeddings = compare_embeddings_with_chunks(audio_bytes)
        >>> for method, emb in embeddings.items():
        ...     print(f"{method}: shape {emb.shape}")
    """
    if aggregation_methods is None:
        aggregation_methods = [
            'mean', 'max', 'weighted_linear', 'weighted_inverse',
            'weighted_normalized', 'energy_weighted'
        ]
    
    results = {}
    
    logger.info(f"Comparing {len(aggregation_methods)} embedding methods...")
    
    for method in aggregation_methods:
        try:
            embedding = generate_embedding_with_chunking(
                audio_bytes,
                aggregation_method=method
            )
            results[method] = embedding
            logger.debug(f"✓ Generated embedding with {method}")
        except Exception as e:
            logger.warning(f"Failed to generate embedding with {method}: {e}")
            results[method] = None
    
    return results

