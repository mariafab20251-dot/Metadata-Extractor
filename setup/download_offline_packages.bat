@echo off
chcp 65001 >nul
title Download Offline Packages — VideoTextExtractor

:: ──────────────────────────────────────────────────────────────
::  Download Offline Packages
::  Run this ONCE on the SOURCE machine (the one with internet)
::  to pre-download all wheels into setup\offline_wheels\
::  Then COPY the whole folder to the new PC — install_dependencies.bat
::  will use these wheels offline instead of downloading again.
:: ──────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
cd /d "%~dp0.."

set WHEEL_DIR=setup\offline_wheels

echo ╔══════════════════════════════════════════════════╗
echo ║  Download Offline Packages                        ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Project root: %CD%
echo Will save wheels to: %WHEEL_DIR%
echo.

:: ── Step 1: Check Python ──
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.11+ first.
    pause
    exit /b 1
)

:: ── Step 2: Upgrade pip ──
echo [1/4] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel -q
echo.

:: ── Step 3: Download main packages ──
if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%"

echo [2/4] Downloading core packages (yt-dlp, whisper, easyocr, etc.)...
echo         This may take a few minutes...
python -m pip download -r requirements.txt -d "%WHEEL_DIR%" --timeout 120 --retries 5
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some downloads failed. Check internet connection and try again.
) else (
    echo         ✅ Core packages downloaded.
)
echo.

:: ── Step 4: Download PyTorch (CPU) ──
echo [3/4] Downloading PyTorch (CPU-compatible version, ~200 MB)...
python -m pip download torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu -d "%WHEEL_DIR%" --timeout 120 --retries 5
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] PyTorch download had issues. It will install from internet on the target PC.
) else (
    echo         ✅ PyTorch CPU downloaded.
)
echo.

:: ── Summary ──
echo [4/4] Verifying...
set COUNT=0
for %%f in ("%WHEEL_DIR%\*.whl") do set /a COUNT+=1
echo         %COUNT% wheel files in %WHEEL_DIR%
echo.
for %%f in ("%WHEEL_DIR%\torch-*.whl") do (
    echo     ✅ PyTorch found: %%~nxf
)
echo.

echo ╔══════════════════════════════════════════════════╗
echo ║  ✅ Done!                                        ║
echo ║                                                   ║
echo ║  Now COPY the entire VideoTextExtractor_PORTABLE  ║
echo ║  folder to the new PC. The install batch there    ║
echo ║  will use these wheels automatically — no         ║
echo ║  internet needed.                                 ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Total wheel size:
du -sh "%WHEEL_DIR%" 2>nul || dir /s "%WHEEL_DIR%\*.whl" 2>nul | find "File(s)"
echo.
pause
