"""临时文件管理 —— 文件提取后即清理，不持久化。

提供临时文件写入和清理辅助函数，供 FileExtractionService 使用。
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

TEMP_ROOT = Path(tempfile.gettempdir()) / "lexad"
ALLOWED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
    ".pdf", ".docx", ".pptx", ".xlsx", ".txt",
}


def save_upload_temp(upload_file) -> Path:
    """Write an uploaded file to a temp directory, return the path."""
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    session_dir = TEMP_ROOT / str(uuid.uuid4())
    session_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload_file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        suffix = ""
    file_path = session_dir / f"{uuid.uuid4().hex}{suffix}"
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    return file_path


def cleanup_temp(file_path: str | Path) -> None:
    """Remove the temp directory containing the given file."""
    path = Path(file_path).resolve()
    root = TEMP_ROOT.resolve()
    if path.parent.parent == root:
        shutil.rmtree(path.parent, ignore_errors=True)
