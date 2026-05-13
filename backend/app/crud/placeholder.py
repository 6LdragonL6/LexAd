"""CRUD 基类 —— 通用可复用的数据访问模式。"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDBase(Generic[ModelT]):
    """通用 CRUD 操作基类，子类绑定具体 ORM 模型后复用增删改查逻辑。"""
    def __init__(self, model: type[ModelT]):
        self.model = model
