"""Safe JSON file reading with graceful fallback."""

import json
from pathlib import Path
from typing import Any


def read_json_safe(file_path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    try:
        if not file_path.exists():
            return default
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if data is not None else default
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return default


def read_json_list(file_path: Path) -> list:
    data = read_json_safe(file_path, {"items": []})
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []
