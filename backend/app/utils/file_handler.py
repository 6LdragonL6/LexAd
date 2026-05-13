"""文件处理工具 —— 上传校验和路径管理。"""

import os
from pathlib import Path

from app.core.config import STATIC_DIR, get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = set(settings.ALLOWED_IMAGE_EXTENSIONS.split(","))  # 允许的图片扩展名集合
UPLOAD_DIR = STATIC_DIR / "uploads"  # 上传文件存储目录


def ensure_upload_dir() -> Path:
    """确保上传目录存在，不存在则创建。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_image_extension(filename: str) -> bool:
    """校验文件扩展名是否在允许列表中。"""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def validate_image_size(file_path: str) -> bool:
    """校验文件大小是否在允许上限内。"""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    return os.path.getsize(file_path) <= max_bytes
