@echo off
title VideoTextExtractor
cd /d "%~dp0"

REM ── Force UTF-8 mode (fixes ASCII encoding on Windows) ──
set PYTHONUTF8=1

REM ── Use the project's own Python (venv) ──
"%~dp0venv\Scripts\pythonw.exe" "%~dp0main.py"
