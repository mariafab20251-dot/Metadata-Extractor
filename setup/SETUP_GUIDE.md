# VideoTextExtractor — Setup Guide

This guide walks you through installing everything needed to run the VideoTextExtractor on a **new PC**.

---

## 📦 What You Need To Manually Install

| Software | Version | Size | Purpose |
|----------|---------|------|---------|
| Python | 3.11 or later | ~150 MB | Runtime |
| FFmpeg | latest | ~70 MB | Audio/video processing |
| Visual C++ Redistributable | 2015-2022 | ~25 MB | Required by some Python packages |

The rest (yt-dlp, Whisper, EasyOCR, PyTorch, etc.) are installed automatically by the batch file.

---

## Step 1 — Install Python

1. Go to: **[https://www.python.org/downloads/](https://www.python.org/downloads/)**
2. Click the **Download Python 3.11+** button (3.11, 3.12, or 3.13 — all work)
3. Run the installer
4. **⚠️ IMPORTANT:** Check the box **"Add Python to PATH"** at the bottom of the installer
5. Click **Install Now**
6. After install, verify by opening **Command Prompt** and typing:
   ```
   python --version
   ```
   You should see: `Python 3.11.x` or later

---

## Step 2 — Install Visual C++ Redistributable

Some Python packages (especially PyTorch and EasyOCR) require the VC++ runtime.

1. Go to: **[https://aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)**
2. Download and run the installer
3. Restart your PC if prompted

---

## Step 3 — Install FFmpeg

FFmpeg is required for audio extraction and video processing.

### Option A: Download manually (recommended)

1. Go to: **[https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)**
2. Under **"release builds"**, download: `ffmpeg-release-essentials.zip`
3. Extract the ZIP file to: `C:\ffmpeg`
4. Add FFmpeg to your system PATH:
   - Open **Start** → type **"Environment Variables"** → **Edit environment variables**
   - Under **System variables**, find **Path**, click **Edit**
   - Click **New** and add: `C:\ffmpeg\bin`
   - Click **OK** on all dialogs
5. Verify by opening a **new** Command Prompt and typing:
   ```
   ffmpeg -version
   ```

### Option B: Using winget (Windows 10/11)
Open Command Prompt as Administrator and run:
```
winget install FFmpeg
```

---

## Step 4 — Install Dependencies (Automated)

1. Copy the entire **VideoTextExtractor** folder to your new PC
2. Navigate to the folder:
   ```
   cd D:\path\to\VideoTextExtractor
   ```
3. **Double-click** the file:
   ```
   setup\install_dependencies.bat
   ```
4. The script will:
   - ✅ Create a Python virtual environment (`venv\`)
   - ✅ Upgrade pip
   - ✅ Install PyTorch (CPU-compatible version, ~200 MB download)
   - ✅ Install all remaining packages (yt-dlp, Whisper, EasyOCR, etc.)
   - ✅ Verify everything works
   - ✅ Create a `run_app.bat` launcher shortcut

⏱ **Total time:** 5-15 minutes depending on internet speed

---

## Step 5 — Launch the Application

**Double-click** `run_app.bat` (created by the installer)

Or manually:
```
venv\Scripts\activate
python main.py
```

---

## 📋 First-Time Setup Notes

### Model Downloads (automatic on first use)

The first time you process a video, these models download automatically:

| Model | Size | When Downloaded |
|-------|------|-----------------|
| **Whisper (base)** | ~140 MB | First speech transcription |
| **EasyOCR** | ~100 MB | First OCR extraction |
| **PyTorch** | ~200 MB | Installed by batch file |

These are one-time downloads. Subsequent runs are instant.

### Browser Cookies (for Instagram, Facebook, Xiaohongshu)

Some platforms require authentication cookies:

1. Install the **"Get cookies.txt LOCALLY"** browser extension
   - Chrome: [Chrome Web Store](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-local/)
2. Log in to the platform in your browser
3. Click the extension icon → **Export cookies**
4. Save the file as `cookies.txt` in the project root folder

Or for Instagram specifically, you can use the **Settings → Login** button inside the app.

### Selenium (for Xiaohongshu — optional)

Xiaohongshu scanning uses Selenium as a fallback. If you need Xiaohongshu support:
```
venv\Scripts\activate
pip install selenium
```
Then download ChromeDriver matching your Chrome version from:
[https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)

---

## 🔧 Troubleshooting

### "Python not found"
→ You skipped Step 1, or didn't check **"Add Python to PATH"**. Reinstall Python and check that box.

### "FFmpeg not found"
→ Install FFmpeg (Step 3) and ensure the `bin` folder is in your system PATH.

### Batch file fails with SSL errors
→ Your antivirus or proxy may be blocking pip. Try:
```
venv\Scripts\python.exe -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org <package-name>
```

### "Could not find torch" or torch installs wrong version
→ Run the batch file again. It installs the CPU-compatible version explicitly.

### Virtual environment not activating
→ Make sure you're running from the project root folder.

### Need help?
→ Open an issue or contact the project maintainer.
