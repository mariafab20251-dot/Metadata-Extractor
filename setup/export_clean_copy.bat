@echo off
chcp 65001 >nul
title VideoTextExtractor — Export Clean Copy

:: ──────────────────────────────────────────────────────────────
::  VideoTextExtractor — Export Clean Portable Copy
::  Creates a zip-ready copy of the project excluding all
::  auto-generated / user-specific / downloadable files.
:: ──────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

cd /d "%~dp0.."

set SOURCE=%CD%
set DEFAULT_DEST=%CD%_PORTABLE

echo ╔══════════════════════════════════════════════════╗
echo ║  Export Clean Portable Copy                      ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Source: %SOURCE%
echo.
echo This will create a clean copy of the project WITHOUT:
echo   • venv\               (recreated by installer)
echo   • __pycache__\         (auto-generated)
echo   • .git\ .claude\       (dev/config files)
echo   • data\                (downloads, cookies, databases, results)
echo   • channels\            (downloaded channel content)
echo   • *.mp4 .mp3 .wav      (media files)
echo   • cookies.txt          (auth)
echo   • debug_* .db .rar .zip
echo.
echo INCLUDING setup\ folder with installer + guide.
echo.

set /p DEST=Destination folder [%DEFAULT_DEST%]:
if "!DEST!"=="" set DEST=%DEFAULT_DEST%

echo.
echo Exporting to: !DEST!
echo.

:: ── Robocopy: mirror with exclusions ──
robocopy "%SOURCE%" "!DEST!" /MIR /XD ^
    venv __pycache__ .git .claude data channels ^
    "__pycache__" ".pytest_cache" ^
    "Backup before v4flash 03June" ^
    "VoiceModules\New folder" ^
    /XF ^
    *.mp4 *.mp3 *.wav *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4a *.aac *.ogg ^
    *.pyc *.pyo *.pyd *.so *.dll ^
    cookies.txt ig_username.txt ig_session *.session ^
    debug_*.html debug_*.json ^
    *.db *.sqlite *.sqlite3 ^
    *.zip *.rar *.7z ^
    "*.xlsx" "*.csv" "results*.json" ^
    /NJH /NJS /NP /NDL >nul

echo.
echo ──────────────────────────────────────────────────
echo  ✅  Clean copy created at:
echo      !DEST!
echo ──────────────────────────────────────────────────
echo.
echo Size:
powershell -Command "if (Test-Path '!DEST!') { $f=Get-ChildItem '!DEST!' -Recurse -File | Measure-Object -Property Length -Sum; $mb=[math]::Round($f.Sum/1MB,1); Write-Host \"  $mb MB  ($($f.Count) files)\" }"
echo.
echo To deploy on a new PC:
echo   1. ZIP this folder and transfer to the new PC
echo   2. Install Python + FFmpeg + VC++ Redist (see SETUP_GUIDE.md)
echo   3. Double-click setup\install_dependencies.bat
echo   4. Double-click run_app.bat
echo.
pause
