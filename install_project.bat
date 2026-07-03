@echo off
title VideoTextExtractor Installer

echo ============================================
echo Installing Python dependencies...
echo ============================================

python -m pip install --upgrade pip

pip install -r requirements.txt

echo.
echo ============================================
echo Installation Complete
echo ============================================
echo.

echo IMPORTANT:
echo You still need to install FFmpeg manually.
echo Download from:
echo https://www.gyan.dev/ffmpeg/builds/

echo.
pause