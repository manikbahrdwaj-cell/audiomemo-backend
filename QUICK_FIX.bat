#!/bin/bash
# Quick fix for WinError 1314 issues on Windows

echo "=========================================="
echo "Windows Permission Error - Quick Fix"
echo "=========================================="
echo ""
echo "Step 1: Cleaning up problematic model cache..."
python backend\cleanup_model_cache.py

echo ""
echo "Step 2: Restarting the application..."
echo "Use: python run.py"
echo ""
echo "The model will be re-downloaded with proper permissions."
echo ""
echo "=========================================="
