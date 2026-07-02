# Metadata Extractor

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A desktop GUI tool that downloads videos from social media platforms and extracts overlay text (OCR), speech transcription (Whisper), and generates AI-powered scripts using Google Gemini.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📥 Multi-platform Download** | YouTube, Instagram, TikTok, Bilibili, PornHub, Facebook, Xiaohongshu/RedNote |
| **🔍 OCR Text Extraction** | Extract on-screen overlay text from videos using EasyOCR |
| **🎤 Speech Transcription** | Transcribe spoken content using OpenAI Whisper |
| **🤖 AI Script Generation** | Generate scripts via Google Gemini (built-in prompt library) |
| **📝 Script Studio** | Write structured video scripts with CTA, hooks, and voiceover cues |
| **⚖️ Case Commentary** | Watch courtroom videos → AI summary + montage clips + commentary |
| **📊 Excel Export** | Save all results to Excel with batch processing support |
| **🖼️ Screenshot Capture** | Auto-capture key frames from video for documentation |

## 📋 Quick Start

### Prerequisites

| Software | Download |
|----------|----------|
| **Python 3.11+** | [python.org/downloads](https://www.python.org/downloads/) |
| **FFmpeg** | [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) (download `ffmpeg-release-essentials.zip`) |
| **Visual C++ Redistributable** | [aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe) |

**⚠️ Important:** When installing Python, check **"Add Python to PATH"**.
After installing FFmpeg, add `C:\ffmpeg\bin` to your system PATH.

### Installation

```batch
:: 1. Clone or download the repository
git clone https://github.com/mariafab20251-dot/Metadata-Extractor.git
cd Metadata-Extractor

:: 2. Run the automated setup (creates venv, installs everything)
setup\install_dependencies.bat

:: 3. Launch the application
run.bat
```

⏱ **Total setup time:** 5-15 minutes (depends on internet speed — PyTorch is ~200 MB).

## 🗂️ Project Structure

```
Metadata-Extractor/
├── main.py                    # Application entry point
├── config.py                  # Configuration settings
├── requirements.txt           # Python package list
├── run.bat                    # One-click launcher
├── .gitignore
├── auth/                      # Authentication modules
├── core/
│   ├── database.py            # SQLite database (processed video tracking)
│   ├── downloader.py          # yt-dlp video downloader
│   ├── exporter.py            # Excel export
│   ├── extractor.py           # OCR + speech extraction
│   ├── metadata_scanner.py    # Channel/profile metadata scanner
│   └── script_generator.py    # AI script generation (Gemini)
├── gui/
│   └── dashboard.py           # Main Tkinter GUI (4500+ lines)
├── platforms/
│   ├── instagram.py           # Instagram auth & scraping
│   ├── youtube.py             # YouTube playlist/channel scanner
│   ├── facebook.py            # Facebook scanner
│   ├── tiktok.py              # TikTok scanner
│   ├── xiaohongshu.py         # Xiaohongshu/RedNote scanner
│   └── __init__.py
├── setup/
│   ├── SETUP_GUIDE.md         # Detailed setup instructions
│   └── install_dependencies.bat  # Automated dependency installer
└── README.md
```

## 🚀 Usage

### Main Processing Tab
1. Paste one or more video URLs (one per line)
2. Select the platform from the dropdown (auto-detected from URL)
3. Choose features: Download Video, Extract Speech, Extract OCR, etc.
4. Click **Process**
5. Results are saved to `data/` directory and exportable to Excel

### Script Studio Tab
- **Browse File / From Channel** — Select local video files (supports multi-select with Ctrl+click)
- Select a prompt type and click **Generate Script**
- AI writes a structured script with hook, body, CTA, and voiceover cues
- Export results to Excel (appends to existing files)

### Case Commentary Tab
- Upload courtroom/case videos
- AI generates a summary, identifies montage-worthy clips, and suggests commentary spots
- Supports batch processing for multiple videos

### Settings Tab
- **Instagram Login** — Username/password login or extract cookies from browser
- **Gemini API Key** — Configure for script generation
- **Whisper Model** — Choose speed vs accuracy (base, small, medium, large)
- **Platform Config** — Auto-detect, quality settings, channel folders

## 🔐 Authentication

Some platforms require login:

| Platform | Method | Notes |
|----------|--------|-------|
| **Instagram** | Settings → Instagram → Login | Or extract cookies from browser |
| **Facebook** | `cookies.txt` | Export using "Get cookies.txt LOCALLY" extension |
| **Xiaohongshu** | `cookies.txt` | Export from browser after login |
| **YouTube** | Public | No auth needed |
| **TikTok** | Public | Most videos downloadable |
| **Bilibili** | Public | Most videos downloadable |
| **PornHub** | Public+curl_cffi | Requires curl_cffi for TLS impersonation (included) |

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `yt-dlp` | Video/audio download from 1000+ sites |
| `openai-whisper` | Speech-to-text transcription (runs locally) |
| `easyocr` | On-screen text/OCR extraction |
| `Pillow` | Image processing |
| `moviepy` | Video editing |
| `instaloader` | Instagram profile scraping |
| `google-genai` | Google Gemini AI for script generation |
| `requests` | HTTP requests |
| `pandas` + `openpyxl` | Excel export |
| `curl_cffi` | Browser TLS impersonation (PornHub, anti-bot sites) |
| `torch` / `torchvision` | ML backend for Whisper + EasyOCR (CPU version) |

## 📄 License

This project is for educational and authorized research purposes.
