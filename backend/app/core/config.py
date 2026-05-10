"""Application configuration — all settings via environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "LexAd"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False

    # ── Server ─────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database (Neon PostgreSQL) ─────────────────────────────────────────
    DATABASE_URL: str = ""
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_SSL_MODE: str = "require"

    # ── Frontend ───────────────────────────────────────────────────────────
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    CORS_ORIGINS: str = ""

    # ── Security ───────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── DeepSeek / AI ─────────────────────────────────────────────────────
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # ── Upload ─────────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: str = ".png,.jpg,.jpeg,.bmp,.tiff,.webp"
    UPLOAD_DIR: str = "uploads"

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── OCR ────────────────────────────────────────────────────────────────
    TESSERACT_AVAILABLE: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT.parent / "data"
STATIC_DIR = PROJECT_ROOT / "static"
