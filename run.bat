@echo off
title OLB — USGS Optics Lab Bench
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║    USGS Camera and Imaging Systems Evaluation Lab    ║
echo  ║                 Optics Lab Bench v1.0                ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Use the system Python (not a venv python)
set PYTHON=C:\Users\balth\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON%" set PYTHON=python

:: Check Python
"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found at %PYTHON%.
    pause
    exit /b 1
)

:: Install/check dependencies
echo [OLB] Checking dependencies...
"%PYTHON%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [OLB] Starting server at http://localhost:8000
echo [OLB] Opening browser...
echo.
echo  Press Ctrl+C to stop.
echo.

:: Open browser after a short delay (start is non-blocking)
start "" timeout /t 2 /nobreak >nul & start "" "http://localhost:8000"

:: Launch FastAPI server
"%PYTHON%" -m backend.main

pause
