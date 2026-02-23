# Voice Biometric - Startup Script
# Checks prerequisites and starts both backend and frontend

param(
    [switch]$Backend = $false,
    [switch]$Frontend = $false,
    [switch]$Both = $false,
    [switch]$Check = $false
)

$ErrorActionPreference = "Continue"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "=" * 60
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "=" * 60
}

function Check-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $result = $connection.BeginConnect("localhost", $Port, $null, $null)
        $result.AsyncWaitHandle.WaitOne(1000, $false) | Out-Null
        if ($connection.Connected) {
            $connection.Close()
            return $true
        }
    }
    catch { }
    return $false
}

function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check Python
    Write-Host "`n[1] Checking Python..." -ForegroundColor Yellow
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "✓ Python installed: $pythonVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Python not found. Install Python 3.8+" -ForegroundColor Red
        return $false
    }
    
    # Check Node.js
    Write-Host "`n[2] Checking Node.js..." -ForegroundColor Yellow
    try {
        $nodeVersion = node --version
        Write-Host "✓ Node.js installed: $nodeVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Node.js not found. Install Node.js 14+" -ForegroundColor Red
        return $false
    }
    
    # Check npm
    Write-Host "`n[3] Checking npm..." -ForegroundColor Yellow
    try {
        $npmVersion = npm --version
        Write-Host "✓ npm installed: v$npmVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ npm not found" -ForegroundColor Red
        return $false
    }
    
    # Check MongoDB (optional)
    Write-Host "`n[4] Checking MongoDB..." -ForegroundColor Yellow
    if (Check-Port 27017) {
        Write-Host "✓ MongoDB is running on port 27017" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ MongoDB is not running on port 27017" -ForegroundColor Yellow
        Write-Host "  Make sure MongoDB is started or configured in .env" -ForegroundColor Gray
    }
    
    # Check Backend
    Write-Host "`n[5] Checking Backend (port 8000)..." -ForegroundColor Yellow
    if (Check-Port 8000) {
        Write-Host "✓ Backend is already running on port 8000" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Backend is not running" -ForegroundColor Red
    }
    
    # Check Frontend
    Write-Host "`n[6] Checking Frontend (port 3000)..." -ForegroundColor Yellow
    if (Check-Port 3000) {
        Write-Host "✓ Frontend is already running on port 3000" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Frontend is not running" -ForegroundColor Red
    }
    
    Write-Host "`n✓ All prerequisites checked" -ForegroundColor Green
    return $true
}

function Start-Backend {
    Write-Header "Starting Backend Server"
    
    if (-not (Test-Path "backend")) {
        Write-Host "✗ backend directory not found" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Starting backend on http://localhost:8000" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    
    Set-Location backend
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    Set-Location ..
}

function Start-Frontend {
    Write-Header "Starting Frontend Server"
    
    if (-not (Test-Path "frontend")) {
        Write-Host "✗ frontend directory not found" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Starting frontend on http://localhost:3000" -ForegroundColor Green
    Write-Host "Browser will open automatically" -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    
    Set-Location frontend
    npm start
    Set-Location ..
}

# Main logic
if ($Check) {
    Check-Prerequisites
}
elseif ($Backend) {
    Check-Prerequisites
    Start-Backend
}
elseif ($Frontend) {
    Check-Prerequisites
    Start-Frontend
}
elseif ($Both) {
    Write-Host "ℹ To run both servers, open two separate PowerShell windows:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Window 1: .\start.ps1 -Backend"
    Write-Host "Window 2: .\start.ps1 -Frontend"
    Write-Host ""
    Write-Host "Or run them separately in different terminals."
    Check-Prerequisites
}
else {
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  .\start.ps1 -Check      # Check prerequisites only"
    Write-Host "  .\start.ps1 -Backend    # Start backend server"
    Write-Host "  .\start.ps1 -Frontend   # Start frontend server"
    Write-Host "  .\start.ps1 -Both       # Show instructions for both"
    Write-Host ""
    Write-Host "Quick start - Run these in separate terminals:"
    Write-Host "  Terminal 1: .\start.ps1 -Backend"
    Write-Host "  Terminal 2: .\start.ps1 -Frontend"
}
