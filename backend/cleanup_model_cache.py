"""
Cleanup script to remove problematic model files and symlinks on Windows
Run this if you get WinError 1314 privilege issues
"""

import os
import shutil
import stat
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def remove_readonly(func, path, exc_info):
    """Error handler for Windows readonly file deletion"""
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR | stat.S_IREAD)
        func(path)
    else:
        raise exc_info[1]

def cleanup_directory(directory: Path, description: str) -> None:
    """Remove all files and directories in the given path"""
    if not directory.exists():
        logger.info(f"Directory does not exist: {directory}")
        return
    
    try:
        logger.info(f"Cleaning up {description}...")
        logger.info(f"Target: {directory}")
        
        # Remove symlinks first
        for item in directory.rglob("*"):
            try:
                if item.is_symlink():
                    logger.info(f"  Removing symlink: {item.name}")
                    item.unlink()
            except Exception as e:
                logger.warning(f"  Could not remove symlink {item.name}: {e}")
        
        # Remove the entire directory tree
        if directory.exists() and any(directory.iterdir()):
            shutil.rmtree(directory, onerror=remove_readonly)
            logger.info(f"✓ Successfully cleaned {description}")
        else:
            logger.info(f"  Directory is already empty")
            
    except Exception as e:
        logger.error(f"✗ Error cleaning {description}: {e}")

def main():
    """Clean up model cache and local model directories"""
    logger.info("=" * 60)
    logger.info("Model Cache Cleanup for Windows")
    logger.info("=" * 60)
    
    # Clean HuggingFace cache for speechbrain model
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--speechbrain--spkrec-ecapa-voxceleb"
    cleanup_directory(hf_cache, "HuggingFace cache for speechbrain model")
    
    # Clean local pretrained models
    backend_dir = Path(__file__).parent
    local_model_dir = backend_dir.parent / "pretrained_models" / "spkrec-ecapa-voxceleb"
    cleanup_directory(local_model_dir, "local pretrained models directory")
    
    logger.info("=" * 60)
    logger.info("Cleanup complete!")
    logger.info("You can now run the application again to re-download the model.")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
