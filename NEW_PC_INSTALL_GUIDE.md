# 🖥️ New-PC Install Guide — VideoTextExtractor (Metadata Extractor)

Read this once, top to bottom, the first time you set up on a new machine.
It also explains **why the Case Commentary and Script Studio tabs throw
"google gemini" errors** after a fresh install, and how the fixed install
batch now prevents that.

---
## ⚡ TL;DR (the 6 steps)

1. Install **Python 3.11+** (tick *"Add python.exe to PATH"*).
2. Install **FFmpeg** and add it to PATH.
3. Get the folder onto the PC (copy the portable folder **or** `git clone`).
4. Double-click **`setup\install_dependencies.bat`** and wait.
5. Put your **Gemini credentials** in place (see Step 5 — this is the part
   that breaks the AI tabs if skipped).
6. Double-click **`run.bat`**.

---
## Step 1 — Install Python 3.11 or newer

- Download: https://www.python.org/downloads/
- During install **check ✅ "Add python.exe to PATH"** (critical — the
  batch files call `python` from PATH).
- Verify in a new terminal:
  ```
  python --version
  ```
  Should print `Python 3.11.x` or higher.

## Step 2 — Install FFmpeg (needed for downloads + audio)

- Download a Windows build: https://www.gyan.dev/ffmpeg/builds/ (get
  "release full").
- Unzip to e.g. `C:\ffmpeg`, then add `C:\ffmpeg\bin` to your PATH
  (Search → "Edit environment variables" → Path → New).
- Verify in a new terminal:
  ```
  ffmpeg -version
  ```
- Without FFmpeg, yt-dlp downloads and Whisper audio extraction fail
  (but the AI script tabs can still work).

## Step 3 — Get the project onto the PC

**Option A — Copy the portable folder (simplest).**
Copy the whole `VideoTextExtractor_PORTABLE` folder to the new PC. This
brings your `data\` folder with it — including cookies, prompts, **and
your Gemini service-account key** — so Step 5 is mostly done for you.

**Option B — `git clone` (smallest download).**
```
git clone https://github.com/mariafab20251-dot/Metadata-Extractor.git
```
⚠️ A clone does **NOT** include the `data\` folder (it is git-ignored).
That means **no Gemini credentials come with a clone** — you must do
Step 5 manually or the AI tabs will error. (See "Why the AI tabs error"
below.)

## Step 4 — Install dependencies

Double-click:
```
setup\install_dependencies.bat
```
This will:
1. Create a local `venv\` (isolated Python for this app).
2. Install PyTorch (CPU build).
3. Install everything in one shot, **including `google-genai` AND
   `google-auth`** (both are required — see below).
4. Verify every import, then run a **Gemini credentials check** that tells
   you if `data\service-account-key.json` is missing.

If it finishes with `OK: all core packages imported` you're good.

## Step 5 — Gemini credentials (THE step people skip)

The **Case Commentary** and **Script Studio** tabs call Google Gemini.
They need credentials. You have two ways to provide them:

**5A — Service-account key file (recommended, no per-key quotas):**
- Put your `service-account-key.json` into the **`data\`** folder:
  ```
  <project>\data\service-account-key.json
  ```
- That's it. On launch the app now **auto-detects** this file even if the
  saved config points at an old path from another PC (self-heal fix).

**5B — API key from the app UI:**
- Launch the app, find the Gemini/API settings row on the dashboard,
  paste a Gemini API key (or click **Browse** and pick a service-account
  JSON), then click **Save**. This writes `data\gemini_config.json`.

You can verify inside the app with the **Test Keys** button — it should
report `OK`.

## Step 6 — Run

Double-click:
```
run.bat
```
(If it says "First-time setup required", you skipped Step 4.)

---
## ❓ Why the AI tabs threw "google gemini" errors on the new PC

There were **three** separate causes. All are now fixed:

1. **Missing `google-auth` dependency.**
   `core/script_generator.py` uses `google.oauth2.service_account` and
   `google.auth.transport.requests` for service-account login. The old
   `requirements.txt` / install batch only installed `google-genai`, which
   does **not** guarantee `google-auth`. Result on a clean venv:
   `ImportError: google-auth library required for service accounts` — a
   "google…" error surfacing only in the two tabs that authenticate.
   → **Fixed:** `google-auth` + `google-auth-httplib2` are now in
   `requirements.txt` and the install batch, and are import-verified.

2. **Stale absolute service-account path in `gemini_config.json`.**
   The saved config stored an absolute path from the ORIGINAL machine
   (`D:\GitHub\pythonprojects\VideoTextExtractor\data\service-account-key.json`).
   On any other PC that path doesn't exist, so service-account auth failed
   and the app fell back to a possibly-dead API key → Gemini errors.
   → **Fixed:** on load, if the stored path is missing, the app now falls
   back to the bundled `data\service-account-key.json` automatically.

3. **A `git clone` has no `data\` folder at all.**
   `data/` is git-ignored, so a fresh clone ships with **no credentials
   and no config** → `is_configured()` is False → every Gemini call returns
   *"Gemini API not configured."* in both AI tabs.
   → **Handled:** the install batch now explicitly checks for the key and
   tells you to add it (Step 5). Folder-copy users (Option A) already have
   it.

---
## 🧠 How Script Studio actually works (plain English)

Script Studio ("Write Story from Video") and Case Commentary are both
front-ends over the **same Gemini engine** in
`core/script_generator.py`. Flow:

1. **You pick a niche/preset** (e.g. Movie Recap, Courtroom, CCTV,
   Dialogue-Only). Each preset maps to a prompt stored in
   `data\script_prompts.json` and/or a master `.txt` in
   `data\master_prompts\`. **These files must exist** — they now travel
   with git (force-added past `.gitignore`).

2. **You give it a video** (YouTube URL or a local/downloaded file).

3. **The engine authenticates to Gemini** using your credentials from
   Step 5 (service account preferred, API key fallback, with key
   rotation).

4. **The video is sent to Gemini.** For a YouTube link it first tries
   *native watch* (send the URL, no download). If that fails it downloads
   with yt-dlp and uploads via the Gemini File API (cached ~48h so a
   second language run doesn't re-upload).

5. **Gemini returns a script.** The app **cleans** it down to
   narration-only pipe lines (`[MM:SS] | text`) — stripping analysis
   reports, hashtags, sync-checklists, `//markers//`, etc. — and writes it
   into the Excel **Custom Script** column (plus Title/Thumbnail columns).

6. **Tool 2 (the video automation studio)** reads that Excel and renders
   the video, reading the Custom Script aloud as the voiceover.

So the three things a new PC needs for these tabs to work:
**(a) the packages (`google-genai` + `google-auth`),
(b) the prompt files in `data\`, and
(c) valid Gemini credentials.** Steps 4 and 5 cover all three.

---
## 🔧 Quick troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "google-auth library required" | `google-auth` not installed | Re-run `setup\install_dependencies.bat` |
| "Gemini API not configured." | No key/SA on this PC (fresh clone) | Do Step 5 |
| Works then quota errors | API key exhausted | Add more keys or use a service account (5A) |
| "Service account file not found" | Old absolute path in config | Put key at `data\service-account-key.json` (auto-detected now) |
| Presets missing / blank niches | `data\script_prompts.json` not present | `git pull` (prompts are tracked) or copy `data\` from the source PC |
| `run.bat` says setup required | `venv\` not built | Run Step 4 |
| Downloads fail | FFmpeg not in PATH | Do Step 2 |
