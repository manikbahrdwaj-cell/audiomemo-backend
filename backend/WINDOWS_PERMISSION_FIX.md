# Windows Permission Error Fix - WinError 1314

## Problem
You're getting this error:
```
Failed to process voice enrollment: Failed to load ECAPA-TDNN model. 
Error: [WinError 1314] A required privilege is not held by the client: 
'C:\Users\...\label_encoder.txt' -> '...\label_encoder.ckpt'
```

## Root Cause
This error occurs on Windows when:
1. HuggingFace tries to create symlinks (which require admin privileges)
2. File operations require special permissions during cache management
3. Files are locked or in use during copy operations

## Solution

### Option 1: Run the Cleanup Script (Recommended)
This script removes the problematic cache files and lets the system re-download them cleanly:

```powershell
# From the backend directory
python cleanup_model_cache.py
```

Then restart your application:
```powershell
python run.py
```

### Option 2: Manual Cleanup
Delete these directories manually:
1. `C:\Users\<YourUsername>\.cache\huggingface\hub\models--speechbrain--spkrec-ecapa-voxceleb`
2. `<ProjectRoot>\pretrained_models\spkrec-ecapa-voxceleb`

Then restart the application.

### Option 3: Check File Permissions
Ensure the directories have write permissions:
```powershell
# Check if your user can write to these locations
Test-Path "C:\Users\$env:USERNAME\.cache" -PathType Container
Test-Path ".\pretrained_models" -PathType Container
```

## Changes Made to Fix This

The following improvements have been made to your code:

### 1. **Enhanced Environment Configuration** (voice_embedding.py)
```python
- Added HF_HUB_ENABLE_HF_TRANSFER environment variable
- Added HF_DATASETS_DISABLE_PROGRESS_BARS to prevent threading issues
- Configured symlink mode to use copy instead of symlinks
```

### 2. **Robust File Copying** (voice_embedding.py)
```python
- Added retry logic with exponential backoff for file operations
- Added permission fixing before overwriting files
- Added file size checking to skip already-copied files
- Improved error handling for permission errors
```

### 3. **Model Directory Cleanup** (voice_embedding.py)
```python
- New _cleanup_model_directory() function removes problematic symlinks
- Fixes file permissions before model loading
- Runs automatically during model initialization
```

### 4. **Download Script Improvements** (download_model.py)
```python
- Added Windows-specific environment variables at the start
- Ensures symlinks are disabled before download
- Better error reporting
```

## Verification

After applying these fixes, you should see in the logs:
```
HuggingFace configured for Windows compatibility (symlinks disabled, copy mode enabled)
✓ ECAPA-TDNN model loaded successfully
```

## If Problem Persists

1. **Check Python Version**: Ensure you're using Python 3.8+
   ```powershell
   python --version
   ```

2. **Verify Virtual Environment**:
   ```powershell
   # On Windows
   venv\Scripts\Activate.ps1
   ```

3. **Reinstall Dependencies**:
   ```powershell
   pip install --upgrade speechbrain huggingface-hub
   ```

4. **Run Full Cleanup**:
   ```powershell
   # This clears everything
   python cleanup_model_cache.py
   
   # Then re-download
   python download_model.py
   ```

5. **Check for Antivirus**: Some antivirus software blocks file operations. Temporarily disable or add exceptions for the `.cache` and `pretrained_models` directories.

## Additional Notes

- The first run after cleanup will take longer as the model is re-downloaded
- Model files are large (~400MB), so ensure sufficient disk space
- HuggingFace cache typically uses `~500MB` of disk space
- All fixes are Windows-specific and won't affect other platforms

## Still Having Issues?

If the error persists:
1. Run: `python cleanup_model_cache.py`
2. Check the logs for specific error messages
3. Ensure the application has adequate disk space (2GB recommended)
4. Try running PowerShell as Administrator
