@echo off
chcp 65001 >nul
title VideoTextExtractor - Install Dependencies

::  VideoTextExtractor - Dependency Installer
::  Run this AFTER installing Python and FFmpeg

setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo ============================================================
echo  VideoTextExtractor - Dependency Installer
echo ============================================================
echo.
echo Project root: %CD%
echo.

:: ---- Check Python ----
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Install Python 3.11+ and check 'Add to PATH'.
    pause
    exit /b 1
)

:: ---- Check Python version (must be 3.11+) ----
python -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Python 3.11+ recommended. You have:
    python --version
)

:: ---- Check FFmpeg ----
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] FFmpeg not found. yt-dlp downloads will fail.
)

:: ---- Detect offline wheelhouse ----
set OFFLINE_EXISTS=0
dir "setup\offline_wheels\*.whl" >nul 2>nul
if %ERRORLEVEL% EQU 0 set OFFLINE_EXISTS=1

if %OFFLINE_EXISTS% EQU 1 (
    echo [OK] Offline wheelhouse found: setup\offline_wheels
    echo      Installing without internet.
) else (
    echo [INFO] No offline wheelhouse. Will download from internet.
)
echo.

:: ---- Step 1: Create venv ----
set VENV_DIR=venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    python -m venv %VENV_DIR%
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo         Done.
) else (
    echo [1/4] Virtual environment already exists.
)
echo.

:: ---- Step 2: Upgrade pip ----
echo [2/4] Upgrading pip...
call "%VENV_DIR%\Scripts\pip.exe" install --upgrade pip setuptools wheel -q
echo.
call "%VENV_DIR%\Scripts\pip.exe" --version
echo.

:: ---- Step 3: Install PyTorch ----
echo [3/4] Installing PyTorch (CPU-compatible)...
if %OFFLINE_EXISTS% EQU 1 (
    call "%VENV_DIR%\Scripts\pip.exe" install --no-index --find-links setup\offline_wheels torch torchvision torchaudio -q
) else (
    call "%VENV_DIR%\Scripts\pip.exe" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --timeout 120 --retries 5 -q
)
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] PyTorch install had issues, retrying simpler install...
    if %OFFLINE_EXISTS% EQU 1 (
        call "%VENV_DIR%\Scripts\pip.exe" install --no-index --find-links setup\offline_wheels torch -q
    ) else (
        call "%VENV_DIR%\Scripts\pip.exe" install torch --timeout 120 -q
    )
)
echo.

:: ---- Step 4: Install remaining packages ----
echo [4/4] Installing remaining dependencies...
if %OFFLINE_EXISTS% EQU 1 (
    call "%VENV_DIR%\Scripts\pip.exe" install --no-index --find-links setup\offline_wheels yt-dlp openai-whisper easyocr Pillow moviepy instaloader requests pandas openpyxl google-genai google-auth google-auth-httplib2 curl_cffi -q
) else (
    call "%VENV_DIR%\Scripts\pip.exe" install yt-dlp openai-whisper easyocr Pillow moviepy instaloader requests pandas openpyxl google-genai google-auth google-auth-httplib2 curl_cffi --timeout 120 --retries 5 -q
)
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install packages.
    if %OFFLINE_EXISTS% EQU 1 (
        echo         The offline wheelhouse may be incomplete.
    ) else (
        echo         Check internet connection.
    )
    pause
    exit /b 1
)
echo.

:: ---- Verify ----
echo ============================================================
echo  Verification
echo ============================================================
call "%VENV_DIR%\Scripts\python.exe" -c "import yt_dlp, google.genai, google.auth, google.oauth2.service_account, whisper, easyocr, PIL, moviepy, instaloader, requests, pandas, openpyxl, torch, curl_cffi; print('OK: all packages imported')" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo   All dependencies installed successfully!
    echo ============================================================
    echo.
    echo  To run: double-click run.bat
) else (
    echo.
    echo [WARNING] Some packages failed verification.
)
echo.

:: ---- Check Gemini credentials ----
echo ============================================================
echo  Gemini credentials check
echo ============================================================
if exist "data\service-account-key.json" (
    echo [OK] Service-account key found.
) else (
    echo [MISSING] service-account-key.json not found.
    echo          Case Commentary and Script Studio tabs need credentials.
    echo          See NEW_PC_INSTALL_GUIDE.md Step 5.
)
if exist "data\gemini_config.json" (
    echo [OK] gemini_config.json found.
) else (
    echo [INFO] No gemini_config.json yet. Created on first save in app.
)
echo.

:: ---- Create launcher ----
if not exist "run_app.bat" (
    echo @echo off > run_app.bat
    echo title VideoTextExtractor >> run_app.bat
    echo cd /d "%%~dp0" >> run_app.bat
    echo set PYTHONUTF8=1 >> run_app.bat
    echo start "" "%%~dp0%VENV_DIR%\Scripts\pythonw.exe" "%%~dp0main.py" >> run_app.bat
    echo [OK] Created run_app.bat launcher
)

echo.
pause
