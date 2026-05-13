"""数据库会话管理 —— 支持 Neon PostgreSQL 和本地 SQLite 回退。"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _build_engine():
    """构建数据库引擎：优先使用 DATABASE_URL（PostgreSQL），未配置时回退 SQLite。"""
    db_url = settings.DATABASE_URL
    if not db_url:
        # 本地开发未配置 DATABASE_URL 时使用 SQLite 回退
        return create_engine(
            "sqlite:///./lexad.db", connect_args={"check_same_thread": False}, echo=False
        )
    return create_engine(
        db_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=False,
    )


# 模块级引擎和会话工厂
engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """获取数据库会话的生成器，用于 FastAPI 依赖注入。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
