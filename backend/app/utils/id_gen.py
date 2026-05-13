"""ID 生成工具 —— 唯一请求 ID 和 UTC 时间戳。"""

import uuid
from datetime import datetime, timezone


def generate_request_id() -> str:
    """生成 12 位十六进制唯一请求 ID（基于 UUID4）。"""
    return uuid.uuid4().hex[:12]


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()
