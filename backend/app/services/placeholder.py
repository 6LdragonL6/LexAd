"""业务服务层基类 —— 领域逻辑的扩展起点。

服务层封装业务规则并编排 CRUD 操作，不包含 HTTP 相关逻辑。
"""

from __future__ import annotations


class BaseService:
    """所有业务服务的基类，子类在此之上扩展领域逻辑。"""
    pass
