"""统一的数据库 URL 解析 —— 应用和 Alembic 的唯一入口。"""

from __future__ import annotations

from app.core.config import Settings


def resolve_database_url(settings: Settings) -> str:
    """根据 DATABASE_MODE 返回正确的数据库连接串。

    mode=local 始终使用 LOCAL_DATABASE_URL，忽略 DATABASE_URL。
    mode=neon  要求 DATABASE_URL 为非空 PostgreSQL URL。
    """
    if settings.DATABASE_MODE == "local":
        url = settings.LOCAL_DATABASE_URL
        if not url.startswith("sqlite"):
            raise RuntimeError("DATABASE_MODE=local 要求 LOCAL_DATABASE_URL 为 SQLite 连接串")
        return url

    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_MODE=neon 但 DATABASE_URL 未设置")
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        raise RuntimeError("DATABASE_MODE=neon 要求 DATABASE_URL 为 PostgreSQL 连接串")
    return url


def database_target_label(settings: Settings) -> str:
    """返回面向用户的数据库标签，绝不包含主机、用户名或密码。"""
    if settings.DATABASE_MODE == "local":
        return "local SQLite"
    return "Neon PostgreSQL"


def is_sqlite_url(url: str) -> bool:
    """判断 URL 是否为 SQLite 连接串。"""
    return url.startswith("sqlite")
