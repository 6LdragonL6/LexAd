"""Centralized logging configuration."""

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(stream=sys.stdout, level=level, format=fmt)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
