"""File handling utilities: upload validation, path helpers."""

import os
from pathlib import Path

from app.core.config import ALLOWED_IMAGE_EXTENSIONS, MAX_UPLOAD_SIZE_MB, STATIC_DIR


UPLOAD_DIR = STATIC_DIR / "uploads"


def ensure_upload_dir() -> Path:
    """Ensure the upload directory exists and return its path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_image_extension(filename: str) -> bool:
    """Check whether the file extension is in the allowed set."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def validate_image_size(file_path: str) -> bool:
    """Check whether the file size is within the allowed limit."""
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    return os.path.getsize(file_path) <= max_bytes
