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

:: Check Python version — must be 3.11 or higher
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not %ERRORLEVEL% EQU 0 (
    echo.
    echo [WARNING] Python 3.11+ recommended. You have:
    python --version
    echo           Consider upgrading if you run into issues.
    echo.
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

:: ── Detect offline wheelhouse (portable copy, no internet needed) ──
set OFFLINE_MODE=0
if exist "setup\offline_wheels\*.whl" set OFFLINE_MODE=1
if !OFFLINE_MODE! EQU 1 (
    echo ✅ Found offline wheelhouse: setup\offline_wheels
    echo    Will install without internet.
) else (
    echo ℹ️  No offline wheelhouse found. Will download from internet.
    echo    (For offline install, run setup\download_offline_packages.bat
    echo     on the machine that has internet, then copy the folder.)
)
echo.

:: ── Step 3: Install PyTorch (CPU-compatible) ──
echo [3/4] Installing PyTorch (CPU-compatible version)...
if !OFFLINE_MODE! EQU 1 (
    echo         Using offline wheels (no internet needed)...
    call "%VENV_DIR%\Scripts\pip.exe" install --no-index --find-links setup\offline_wheels torch torchvision torchaudio -q
) else (
    echo         This may take several minutes (download size ~200 MB)...
    call "%VENV_DIR%\Scripts\pip.exe" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --timeout 120 --retries 5 -q
)
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] PyTorch install had issues, trying fallback...
    if !OFFLINE_MODE! EQU 1 (
        call "%VENV_DIR%\Scripts\pip.exe" install --no-index --find-links setup\offline_wheels torch -q
    ) else (
        call "%VENV_DIR%\Scripts\pip.exe" install torch --timeout 120 -q
    )
)
echo.

:: ── Step 4: Install remaining dependencies ──
echo [4/4] Installing remaining dependencies...
if !OFFLINE_MODE! EQU 1 (
    echo         Using offline wheels (no internet needed)...
    call "%VENV_DIR%\Scripts\pip.exe" install --no-index --find-links setup\offline_wheels yt-dlp openai-whisper easyocr Pillow moviepy instaloader requests pandas openpyxl google-genai google-auth google-auth-httplib2 curl_cffi -q
) else (
    echo         Downloading from internet (may take several minutes)...
    call "%VENV_DIR%\Scripts\pip.exe" install yt-dlp openai-whisper easyocr Pillow moviepy instaloader requests pandas openpyxl google-genai google-auth google-auth-httplib2 curl_cffi --timeout 120 --retries 5 -q
)
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Failed to install some dependencies.
    echo.
    if !OFFLINE_MODE! EQU 1 (
        echo         The offline wheelhouse may be incomplete or corrupt.
        echo         Try deleting setup\offline_wheels and re-running
        echo         setup\download_offline_packages.bat on the source machine.
    ) else (
        echo         Check your internet connection and try again.
        echo         Or run setup\download_offline_packages.bat on a machine
        echo         with internet, then copy the folder and re-run this batch.
    )
    pause
    exit /b 1
)
echo.

:: ── Verify ──
echo ════════════════════════════════════════════════════
echo  Verification
echo ════════════════════════════════════════════════════
echo.
call "%VENV_DIR%\Scripts\python.exe" -c "import yt_dlp, google.genai, google.auth, google.oauth2.service_account, whisper, easyocr, PIL, moviepy, instaloader, requests, pandas, openpyxl, torch, curl_cffi; print('OK: all core packages imported (incl. google.genai + google.auth)')" 2>&1
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

:: ── Gemini credentials check (Case Commentary / Script Studio tabs) ──
echo ════════════════════════════════════════════════════
echo  Gemini credentials check (AI tabs)
echo ════════════════════════════════════════════════════
echo.
set "SA_KEY=%CD%\data\service-account-key.json"
set "GEM_CFG=%CD%\data\gemini_config.json"
if not exist "data" mkdir "data"
if exist "%SA_KEY%" (
    echo   [OK] Service-account key found: data\service-account-key.json
) else (
    echo   [MISSING] data\service-account-key.json  NOT found.
    echo             The Case Commentary and Script Studio tabs will NOT work
    echo             until you add Gemini credentials. Two options:
    echo               1. Copy your service-account-key.json into the .\data\ folder, OR
    echo               2. Launch the app, open the Gemini/API settings row, paste an
    echo                  API key ^(or Browse to a service-account JSON^), and Save.
)
if exist "%GEM_CFG%" (
    echo   [OK] gemini_config.json found.
) else (
    echo   [INFO] No gemini_config.json yet. It is created the first time you
    echo          save credentials in the app. This is normal on a fresh clone.
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
