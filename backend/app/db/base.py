"""SQLAlchemy ORM 基类 —— 所有数据模型继承自此基类。"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类，所有 ORM 模型需继承此类。"""
    pass
