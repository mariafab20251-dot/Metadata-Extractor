import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
VIDEOS_DIR = DATA_DIR / "videos"
FRAMES_DIR = DATA_DIR / "frames"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = DATA_DIR / "processed.db"
CSV_PATH = DATA_DIR / "results.csv"
JSON_PATH = DATA_DIR / "results.json"
AUTH_PATH = BASE_DIR / "auth" / "credentials.json"

WHISPER_MODEL_DIR = MODELS_DIR / "whisper"
EASYOCR_MODEL_DIR = MODELS_DIR / "easyocr"

# Ensure directories exist
for dir_path in [DATA_DIR, VIDEOS_DIR, FRAMES_DIR, MODELS_DIR, WHISPER_MODEL_DIR, EASYOCR_MODEL_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Whisper settings
WHISPER_MODEL = "base"  # tiny, base, small, medium, large

# OCR settings
FRAME_INTERVAL = 10  # Extract frame every N seconds (overlay text rarely changes more often)

# Download settings
KEEP_VIDEOS = True  # Keep downloaded videos after processing (set to False to auto-delete)
MAX_RETRIES = 3

# Processing settings
SKIP_ON_ERROR = True  # Continue processing next video if current one fails
CLEANUP_TEMP_FILES = True  # Remove temporary files after processing
