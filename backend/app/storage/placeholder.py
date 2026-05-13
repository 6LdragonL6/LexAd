"""文件与对象存储抽象层 —— 封装文件系统和 S3 兼容对象存储等。

提供统一的接口，屏蔽底层存储差异。
"""

from __future__ import annotations


class BaseStorage:
    """所有存储后端的基类。"""
    pass
