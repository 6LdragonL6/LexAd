"""统一日志配置模块。"""

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """初始化应用日志：设置格式、级别，并降低第三方库的日志噪音。"""
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(stream=sys.stdout, level=level, format=fmt)

    # 降低第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
