"""安全的 JSON 文件读取 —— 带容错回退机制。"""

import json
from pathlib import Path
from typing import Any


def read_json_safe(file_path: Path, default: Any = None) -> Any:
    """安全读取 JSON 文件，文件不存在或解析失败时返回默认值。"""
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
    """从 JSON 文件读取列表数据，支持 {"items": [...]} 包裹格式或顶层数组。"""
    data = read_json_safe(file_path, {"items": []})
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []
