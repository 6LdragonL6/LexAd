"""共享 API 依赖注入。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Session:
    """获取数据库会话的 FastAPI 依赖项，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
