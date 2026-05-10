"""File handling utilities: upload validation, path helpers."""

import os
from pathlib import Path

from app.core.config import STATIC_DIR, get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = set(settings.ALLOWED_IMAGE_EXTENSIONS.split(","))
UPLOAD_DIR = STATIC_DIR / "uploads"


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_image_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def validate_image_size(file_path: str) -> bool:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    return os.path.getsize(file_path) <= max_bytes
