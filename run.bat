@echo off
title Metadata Extractor
cd /d "%~dp0"

REM ── Force UTF-8 mode (fixes ASCII encoding on Windows) ──
set PYTHONUTF8=1

REM ── Check venv exists, if not show setup instructions ──
if not exist "%~dp0venv\Scripts\pythonw.exe" (
    echo ╔══════════════════════════════════════════════════╗
    echo ║  First-time setup required!                      ║
    echo ║                                                  ║
    echo ║  Double-click:  setup\install_dependencies.bat   ║
    echo ╚══════════════════════════════════════════════════╝
    pause
    exit /b 1
)

REM ── Use the project's own Python (venv) ──
start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0main.py"
