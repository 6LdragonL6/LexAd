"""Application configuration and environment variable handling."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


APP_ENV = _env("APP_ENV", "development")

DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
MAX_UPLOAD_SIZE_MB = 10

# TODO: Replace with real Tesseract path or discovery when Tesseract is installed
TESSERACT_AVAILABLE = False  # Set to True after installing Tesseract and verifying
