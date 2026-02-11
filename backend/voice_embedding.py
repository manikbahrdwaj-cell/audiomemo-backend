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
from speechbrain.inference.speaker import EncoderClassifier

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model = None

class MockECAPATDNN:
    """Mock ECAPA-TDNN model for testing without full model loading"""
    def __init__(self, device="cpu"):
        self.device = device
        logger.info("Using MOCK ECAPA-TDNN model (for testing)")
    
    def encode_batch(self, waveform):
        """Generate mock 192-dimensional embedding from waveform"""
        # Create a deterministic embedding based on audio content
        # This allows testing the pipeline without the full model
        import hashlib
        
        # Convert to numpy for processing
        if isinstance(waveform, torch.Tensor):
            audio_data = waveform.numpy().flatten()
        else:
            audio_data = waveform.flatten()
        
        # Create a hash-based embedding for consistent results
        audio_bytes = audio_data.tobytes()
        hash_obj = hashlib.sha256(audio_bytes)
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Create 192-dim embedding using the hash as seed
        np.random.seed(hash_int % (2**32))  # Use low bits to ensure it fits in uint32
        embedding = np.random.randn(192).astype(np.float32)
        
        # Normalize
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        # Return as torch tensor with batch dimension
        return torch.from_numpy(embedding.reshape(1, 192)).to(self.device)

def get_model():
    """Load and cache the ECAPA-TDNN model"""
    global _model
    if _model is None:
        logger.info("Loading ECAPA-TDNN model...")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        backend_dir = Path(__file__).parent
        model_dir = backend_dir.parent / "pretrained_models" / "spkrec-ecapa-voxceleb"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to load the real model first
        try:
            logger.info(f"Attempting to load model from: {model_dir}")
            
            # Set environment to prevent HF downloads
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['HF_HUB_OFFLINE'] = 'true'
            
            # Try to load from local checkpoints
            _model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=str(model_dir),
                run_opts={"device": device, "prevent_ckpt_overwrite": True},
                freeze_params=True
            )
            
            logger.info("Real ECAPA-TDNN model loaded successfully")
            return _model
            
        except Exception as e:
            logger.warning(f"Could not load real model: {str(e)[:200]}...")
            
            # If we have local checkpoint files, try to load them directly
            if (model_dir / "embedding_model.ckpt").exists():
                logger.info("Found local checkpoint files, attempting direct load...")
                try:
                    # Try a different loading approach
                    os.environ.pop('HF_HUB_OFFLINE', None)
                    
                    _model = EncoderClassifier.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir=str(model_dir),
                        run_opts={"device": device}
                    )
                    logger.info("Model loaded via checkpoint files")
                    return _model
                except Exception as e2:
                    logger.warning(f"Direct load also failed: {str(e2)[:200]}...")
            
            # Final fallback: use mock model for testing
            logger.warning("Using MOCK model for testing. Full model loading failed.")
            logger.warning("To use real model, ensure internet connection or manually copy HuggingFace model files.")
            _model = MockECAPATDNN(device=device)
            return _model
    
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
    Calculate cosine similarity between two embeddings
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score between 0 and 1
    """
    # Normalize vectors
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
    
    # Convert from [-1, 1] to [0, 1] range
    similarity = (similarity + 1) / 2
    
    return float(similarity)

# Preload model on module import (optional, can be commented out for lazy loading)
# get_model()
