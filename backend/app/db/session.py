"""数据库会话管理 —— 通过统一 URL 解析支持本地 SQLite 和 Neon PostgreSQL。"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.url import resolve_database_url, is_sqlite_url

settings = get_settings()


def _build_engine():
    """构建数据库引擎，使用统一的 URL 解析逻辑。"""
    db_url = resolve_database_url(settings)
    if is_sqlite_url(db_url):
        return create_engine(
            db_url, connect_args={"check_same_thread": False}, echo=False
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
