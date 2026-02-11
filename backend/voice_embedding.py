"""
Voice Embedding Module using ECAPA-TDNN
Generates 192-dimensional speaker embeddings from audio files
"""

import torch
import torchaudio
import numpy as np
import tempfile
import os
from io import BytesIO
import logging

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

def get_model():
    """Load and cache the ECAPA-TDNN model"""
    global _model
    if _model is None:
        logger.info("Loading ECAPA-TDNN model from SpeechBrain...")
        _model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
            run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"}
        )
        logger.info("ECAPA-TDNN model loaded successfully")
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
        # Load audio
        waveform, sample_rate = torchaudio.load(tmp_path)
        
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
        waveform = waveform / (torch.max(torch.abs(waveform)) + 1e-8)
        
        return waveform.squeeze(0)  # Remove batch dimension
        
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

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
