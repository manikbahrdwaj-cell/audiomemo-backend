"""
Script to download the ECAPA-TDNN model from HuggingFace
Run this once to pre-download the model before starting the application
"""

import torch
import torchaudio
from pathlib import Path
import logging
import os

# Patch torchaudio compatibility issues BEFORE any imports
if not hasattr(torchaudio, 'set_audio_backend'):
    def _dummy_set_audio_backend(backend):
        pass
    torchaudio.set_audio_backend = _dummy_set_audio_backend

if not hasattr(torchaudio, 'list_audio_backends'):
    def _dummy_list_audio_backends():
        return ['soundfile']
    torchaudio.list_audio_backends = _dummy_list_audio_backends

if not hasattr(torchaudio, 'get_audio_backend'):
    def _dummy_get_audio_backend():
        return 'soundfile'
    torchaudio.get_audio_backend = _dummy_get_audio_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def download_model():
    """Download and cache the ECAPA-TDNN model using HuggingFace API with Windows support"""
    from huggingface_hub import snapshot_download
    
    # Set Windows-friendly environment variables FIRST
    os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
    os.environ['HF_HUB_SYMLINK_MODE'] = 'copy'
    os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_DATASETS_DISABLE_PROGRESS_BARS'] = '1'
    
    # Get the model directory
    backend_dir = Path(__file__).parent
    model_target_dir = backend_dir.parent / "pretrained_models" / "spkrec-ecapa-voxceleb"
    
    # Ensure directory exists
    model_target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Target directory: {model_target_dir}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    try:
        logger.info("Downloading ECAPA-TDNN model from HuggingFace Hub...")
        
        # Download using HuggingFace's snapshot_download
        # This handles directory structure and avoids symlink issues
        cache_dir = snapshot_download(
            repo_id="speechbrain/spkrec-ecapa-voxceleb",
            cache_dir=str(model_target_dir.parent),
            repo_type="model",
            local_dir=str(model_target_dir),
            local_dir_use_symlinks=False
        )
        
        logger.info("✓ ECAPA-TDNN model downloaded successfully!")
        logger.info(f"Model location: {model_target_dir}")
        
        # List downloaded files
        files = list(model_target_dir.glob("**/*"))
        file_count = len([f for f in files if f.is_file()])
        dir_count = len([f for f in files if f.is_dir()])
        logger.info(f"Downloaded {file_count} files in {dir_count} directories")
        
        # Verify essential files
        essential_files = ["hyperparams.yaml"]
        for essential_file in essential_files:
            matching_files = list(model_target_dir.glob(f"**/{essential_file}"))
            if matching_files:
                logger.info(f"✓ Found {essential_file}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to download model: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = download_model()
    exit(0 if success else 1)
