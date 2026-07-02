@echo off
chcp 65001 >nul
title VideoTextExtractor — Install Dependencies

:: ──────────────────────────────────────────────────────────────
::  VideoTextExtractor — Dependency Installer
::  Run this AFTER installing Python and FFmpeg (see SETUP_GUIDE.md)
:: ──────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

:: Detect Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found! Please install Python 3.11 or later first.
    echo         Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Python version
python --version 2>&1 | findstr /R "3\.1[1-9]\|3\.[2-9][0-9]\|[4-9]\." >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Python 3.11+ recommended. You have:
    python --version
    echo.
    echo           Some packages may not work on older Python versions.
    echo           Consider upgrading if you run into issues.
)

:: Detect FFmpeg
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] FFmpeg not found in PATH.
    echo           yt-dlp and audio extraction will fail without it.
    echo           See SETUP_GUIDE.md for installation steps.
    echo.
)

cd /d "%~dp0.."

echo ╔══════════════════════════════════════════════════╗
echo ║  VideoTextExtractor — Dependency Installer       ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Project root: %CD%
echo.

:: ── Step 1: Create virtual environment ──
set VENV_DIR=venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    python -m venv %VENV_DIR%
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo         Virtual environment created in .\%VENV_DIR%\
) else (
    echo [1/4] Virtual environment already exists, skipping.
)
echo.

:: ── Step 2: Upgrade pip ──
echo [2/4] Upgrading pip...
call "%VENV_DIR%\Scripts\pip.exe" install --upgrade pip setuptools wheel -q
echo.
echo         Pip version:
call "%VENV_DIR%\Scripts\pip.exe" --version
echo.

:: ── Step 3: Install PyTorch (CPU-compatible) ──
echo [3/4] Installing PyTorch (CPU-compatible version)...
echo         This may take several minutes (download size ~200 MB)...
echo.
call "%VENV_DIR%\Scripts\pip.exe" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu -q
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] PyTorch CPU install had issues, trying PyPI fallback...
    call "%VENV_DIR%\Scripts\pip.exe" install torch -q
)
echo.

:: ── Step 4: Install remaining dependencies ──
echo [4/4] Installing remaining dependencies (%VENV_DIR%)...
echo.
call "%VENV_DIR%\Scripts\pip.exe" install yt-dlp openai-whisper easyocr Pillow moviepy instaloader requests pandas openpyxl google-genai curl_cffi -q
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Failed to install some dependencies.
    echo         Check your internet connection and try again.
    pause
    exit /b 1
)
echo.

:: ── Verify ──
echo ════════════════════════════════════════════════════
echo  Verification
echo ════════════════════════════════════════════════════
echo.
call "%VENV_DIR%\Scripts\python.exe" -c "import yt_dlp, google.genai, whisper, easyocr, PIL, moviepy, instaloader, requests, pandas, openpyxl, torch, curl_cffi; print('✅ All %d packages imported successfully' % len(['yt_dlp','google.genai','whisper','easyocr','PIL','moviepy','instaloader','requests','pandas','openpyxl','torch','curl_cffi']))" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ╔══════════════════════════════════════════════════╗
    echo ║  ✅  All dependencies installed successfully!    ║
    echo ╚══════════════════════════════════════════════════╝
    echo.
    echo  To launch the app:
    echo    1. Activate the environment:
    echo       %VENV_DIR%\Scripts\activate
    echo.
    echo    2. Run the application:
    echo       python main.py
    echo.
    echo  Or use the launcher shortcut:
    echo       run_app.bat
) else (
    echo.
    echo [WARNING] Some packages failed verification. Check output above.
)
echo.

:: ── Create launcher batch file ──
if not exist "run_app.bat" (
    echo @echo off > run_app.bat
    echo title VideoTextExtractor >> run_app.bat
    echo cd /d "%%~dp0" >> run_app.bat
    echo set PYTHONUTF8=1 >> run_app.bat
    echo start "" "%%~dp0%VENV_DIR%\Scripts\pythonw.exe" "%%~dp0main.py" >> run_app.bat
    echo ✅ Created run_app.bat launcher
)

echo.
pause
