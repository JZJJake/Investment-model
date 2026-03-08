@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo Phase 1: Environment Initialization
echo Target: Windows Server 2012 R2
echo ==========================================

REM Check for Python 3.11
python --version > temp_py_version.txt 2>&1
set /p PY_VERSION=<temp_py_version.txt
del temp_py_version.txt

echo Detected Python: !PY_VERSION!
echo !PY_VERSION! | findstr /C:"Python 3.11" >nul
if errorlevel 1 (
    echo [ERROR] Python 3.11 is required. Found: !PY_VERSION!
    echo Please install Python 3.11.9 and add it to system PATH.
    pause
    exit /b 1
)

echo [INFO] Python 3.11 found.

REM Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment already exists.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies forcing binary wheels
echo [INFO] Installing dependencies...
python -m pip install --upgrade pip
pip install --only-binary :all: -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [INFO] Dependencies installed successfully.

REM Start services sequentially
echo [INFO] Starting Backend API...
start "Backend API" cmd /c "venv\Scripts\activate.bat && uvicorn backend_api:app --host 127.0.0.1 --port 8000"
timeout /t 5 /nobreak >nul

echo [INFO] Starting Frontend Interface...
start "Frontend Interface" cmd /c "venv\Scripts\activate.bat && streamlit run frontend.py --server.port 8501"

echo [INFO] All services started.
pause