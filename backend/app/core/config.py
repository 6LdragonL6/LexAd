"""应用配置 —— 所有配置项通过环境变量或 .env 文件注入。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局应用配置，自动从 .env 文件和环境变量加载。"""

    # ── 应用基础 ────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"  # 运行环境
    APP_NAME: str = "LexAd"  # 应用名称
    APP_VERSION: str = "0.3.0"  # 应用版本
    DEBUG: bool = False  # 调试模式开关

    # ── 服务器 ─────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"  # 监听地址
    PORT: int = 8000  # 监听端口

    # ── 数据库 (Neon PostgreSQL) ──────────────────────────────────────────
    DATABASE_URL: str = ""  # 数据库连接串，为空时自动回退 SQLite
    DATABASE_POOL_SIZE: int = 10  # 连接池大小
    DATABASE_MAX_OVERFLOW: int = 20  # 连接池溢出上限
    DATABASE_SSL_MODE: str = "require"  # SSL 模式

    # ── 前端 ───────────────────────────────────────────────────────────────
    FRONTEND_ORIGIN: str = "http://localhost:5173"  # 前端开发服务器地址
    CORS_ORIGINS: str = ""  # 额外 CORS 来源，逗号分隔

    # ── 安全 ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"  # JWT 签名密钥（生产环境务必修改）
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # JWT 令牌过期时间（分钟）

    # ── DeepSeek AI ───────────────────────────────────────────────────────
    DEEPSEEK_API_KEY: str = ""  # DeepSeek API 密钥
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"  # DeepSeek 接口地址
    DEEPSEEK_MODEL: str = "deepseek-chat"  # 默认模型

    # ── 文件上传 ──────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10  # 上传文件大小上限
    ALLOWED_IMAGE_EXTENSIONS: str = ".png,.jpg,.jpeg,.bmp,.tiff,.webp"  # 允许的图片格式
    UPLOAD_DIR: str = "uploads"  # 上传文件存储目录

    # ── 日志 ────────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"  # 日志级别

    # ── OCR ────────────────────────────────────────────────────────────────
    TESSERACT_AVAILABLE: bool = True  # Tesseract OCR 开关，启动时自动检测是否可用

    # ── ChromaDB ──────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = str(PROJECT_ROOT.parent / "chroma_data")

    # ── Knowledge Base ────────────────────────────────────────────────
    KNOWLEDGE_DIR: str = str(PROJECT_ROOT.parent / "knowledge")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的全局配置单例。"""
    return Settings()


# 路径常量
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/ 目录
DATA_DIR = PROJECT_ROOT.parent / "data"  # 数据文件目录（规则、案例、模板 JSON）
STATIC_DIR = PROJECT_ROOT / "static"  # 静态资源目录
