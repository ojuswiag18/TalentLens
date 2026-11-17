import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SKILLS_FILE = DATA_DIR / "skills.csv"
RESOURCES_FILE = DATA_DIR / "resources.csv"

ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is not set")

    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024
    JSON_SORT_KEYS = False
    # In-memory analysis store expiry (seconds)
    ANALYSIS_TTL = int(os.getenv("ANALYSIS_TTL", "3600"))

    # Skill / resource caches
    CACHE_ENABLED = True