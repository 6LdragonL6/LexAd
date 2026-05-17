"""临时文件管理 —— 文件提取后即清理，不持久化。

提供临时文件写入和清理辅助函数，供 FileExtractionService 使用。
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

TEMP_ROOT = Path("/tmp/lexad")


def save_upload_temp(upload_file) -> Path:
    """Write an uploaded file to a temp directory, return the path."""
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    session_dir = TEMP_ROOT / str(uuid.uuid4())
    session_dir.mkdir(parents=True, exist_ok=True)

    file_path = session_dir / (upload_file.filename or "upload")
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    return file_path


def cleanup_temp(file_path: str | Path) -> None:
    """Remove the temp directory containing the given file."""
    path = Path(file_path)
    if path.parent.parent == TEMP_ROOT:
        shutil.rmtree(path.parent, ignore_errors=True)
