# How to Fix WinError 1314 - Step by Step Guide

## What Was Fixed

Your voice enrollment system was failing with a Windows permission error when trying to load the ECAPA-TDNN speech model. This has been fixed by:

1. Disabling symlink creation (which requires admin privileges)
2. Adding intelligent retry logic for file operations
3. Automatically fixing file permissions before operations
4. Creating a cleanup utility for problematic cache files

## Quick Fix (Recommended)

### Step 1: Clean Up the Cache
Open PowerShell and run:

```powershell
# Navigate to backend directory
cd backend

# Run cleanup script
python cleanup_model_cache.py

# Wait for it to complete (should show "Cleanup complete!")
```

### Step 2: Restart the Application
```powershell
# Still in backend directory, or from root:
python run.py
```

### Step 3: Test
1. Open browser to `http://localhost:3000`
2. Try to enroll your voice
3. Should work without WinError 1314

## If You Have Multiple Terminal Windows

Some PowerShell terminals might need to be closed to fully release file locks:

```powershell
# Close all python processes
Get-Process -Name python* -ErrorAction SilentlyContinue | Stop-Process -Force

# Then run cleanup
python backend/cleanup_model_cache.py

# Wait 10 seconds
Start-Sleep -Seconds 10

# Then run the app
python run.py
```

## What Gets Cleaned Up

The cleanup script removes these directories:
- `C:\Users\<YourUsername>\.cache\huggingface\hub\models--speechbrain--spkrec-ecapa-voxceleb`
- `<ProjectRoot>\pretrained_models\spkrec-ecapa-voxceleb`

This is safe to do - the files will be automatically re-downloaded on the next run.

## Verify the Fix Worked

After starting the app, you should see this in the logs:

```
HuggingFace configured for Windows compatibility (symlinks disabled, copy mode enabled)
Copying model files from cache to ...
Copied X files, skipped Y files
✓ ECAPA-TDNN model loaded successfully
```

## Troubleshooting

### Still Getting WinError 1314?

1. **Close Everything**
   ```powershell
   # Kill all Python processes
   Get-Process -Name python* | Stop-Process -Force
   
   # Wait 5 seconds
   Start-Sleep -Seconds 5
   ```

2. **Check Antivirus**
   - Temporarily disable antivirus
   - Or add exceptions for: `C:\Users\<YourUsername>\.cache`

3. **Check Disk Space**
   ```powershell
   # Model files need ~500MB + cache space
   Get-Volume -DriveLetter C | Format-List SizeRemaining
   ```

4. **Run as Administrator** (last resort)
   - Right-click PowerShell → "Run as Administrator"
   - Then run: `python run.py`

### Files Are Still Locked

If you get "file already in use" errors:

```powershell
# Restart your computer (nuclear option)
# Or close VS Code completely and try again
```

### Permission Denied on Cleanup

If cleanup script fails:

```powershell
# Try running as Administrator
# Right-click PowerShell → Run as Administrator

# Then run cleanup
python backend/cleanup_model_cache.py
```

## What Changed in Your Code

Three files were updated to fix this issue:

1. **backend/voice_embedding.py**
   - Better model loading with automatic cleanup
   - Retry logic for file operations
   - Windows-specific environment variables

2. **backend/download_model.py**
   - Windows-friendly download configuration
   - Better error handling

3. **backend/cleanup_model_cache.py** (NEW)
   - Utility to fix locked/problematic files
   - Safe to run anytime

## Manual Cache Cleanup (If Cleanup Script Fails)

If the Python script doesn't work, manually delete:

1. `C:\Users\<YourUsername>\.cache\huggingface\hub\models--speechbrain--spkrec-ecapa-voxceleb`
   - Right-click → Delete
   - Confirm deletion (will show "Rebuilding...")

2. Then delete: `<ProjectRoot>\pretrained_models\spkrec-ecapa-voxceleb`

3. Start the app - model will re-download

## Expected Timings

- **First run after cleanup**: 2-3 minutes (downloading 400MB model)
- **Subsequent runs**: 10-20 seconds (model cached)
- **Enrollment/Verification**: 2-5 seconds per attempt

## Getting Help

If you still have issues:

1. Note the exact error message from the logs
2. Check if the logs mention "HuggingFace configured for Windows"
3. Ensure Python 3.8+ is installed
4. Make sure you're in a virtual environment

## Success Indicators

You'll know it worked when:
✓ No WinError 1314 message
✓ See "✓ ECAPA-TDNN model loaded successfully" in logs
✓ Can enroll and verify voices without errors
✓ Frontend loads without error messages

