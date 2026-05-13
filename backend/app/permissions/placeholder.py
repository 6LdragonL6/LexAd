"""权限与授权逻辑 —— 封装基于角色的访问控制、权限检查和策略。

将授权规则与业务逻辑和 HTTP 层解耦。
"""

from __future__ import annotations


class BasePermission:
    """所有权限检查的基类。"""
    pass
